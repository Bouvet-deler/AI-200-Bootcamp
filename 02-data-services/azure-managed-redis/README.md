# Azure Managed Redis

**Domain:** 02 — Develop AI solutions by using Azure data management services (25–30%)
**Maps to skill:** *Implement Azure Managed Redis data operations, including caching,
expiration, and invalidation* · *Implement vector indexing to enable similarity search*

## What it is

**Azure Managed Redis** is Microsoft's current managed Redis service. It runs the Redis
Enterprise software and is compatible with normal Redis clients and commands. Because Redis keeps
its working data in memory, it is useful when an application needs low-latency access to cached
results, sessions, counters, rate-limit state, or vector embeddings.

Azure Managed Redis is **not another name for Azure Cache for Redis**. They are separate Azure
services:

- **Azure Managed Redis** is the current service and the one named in the AI-200 skills.
- **Azure Cache for Redis** is the older service. Its Enterprise tiers retire on March 31, 2027,
  and its Basic, Standard, and Premium tiers retire on September 30, 2028. Do not design a new
  exam solution around those old tiers.

> Mental model:
>
> ```text
> request → application → Azure Managed Redis
>                         │ hit: return cached value
>                         └ miss: read source → cache result with a TTL → return it
> ```

Redis is normally a **derived-data store**, not the system of record. A cache entry can disappear
because it expired, was evicted under memory pressure, or was explicitly invalidated. The
application must still be able to obtain the authoritative value from its primary store.

## Why it's on the exam

Expect scenario questions that ask you to:

- implement cache-aside reads with `GET`, `SET`, and an expiration;
- invalidate an entry after the underlying data changes;
- choose a Redis data structure for a key-value, object, counter, or ordered collection;
- distinguish expiration from eviction;
- provision RediSearch correctly before creating a vector index;
- choose `FLAT` for exact search or `HNSW` for approximate, lower-latency search; and
- make the vector field's type, dimensions, and distance metric match the embedding model.

The exam objective is about using Redis correctly in an AI solution. Memorizing retired Azure
Cache for Redis tier sizes or a particular embedding model's default dimensions is not useful.

## Core concepts

### 1. Data structures and atomic commands

Redis maps a string key to a value. The value can use several structures:

| Structure | Typical commands | Good fit |
| --- | --- | --- |
| String | `GET`, `SET`, `INCR` | Serialized response, token, counter |
| Hash | `HSET`, `HGET`, `HGETALL` | Object with independently addressable fields |
| List | `LPUSH`, `RPUSH`, `LPOP`, `RPOP` | Ordered work or activity items |
| Set | `SADD`, `SISMEMBER` | Unique members and membership tests |
| Sorted set | `ZADD`, `ZRANGE` | Scores, rankings, and time-ordered members |

Commands such as `INCR` and `HINCRBY` are atomic on the Redis server. Two clients therefore do not
need a read-modify-write sequence merely to increment a counter.

RedisJSON and RediSearch are **modules**, not core scalar data types. RediSearch indexes fields in
Redis hashes or JSON documents, including vector fields.

### 2. Cache-aside, expiration, and invalidation

In **cache-aside**, the application owns the cache workflow:

1. Read the cache.
2. On a miss, read the authoritative data store.
3. Cache the result with a bounded lifetime.
4. Return the result.

```python
def get_product(product_id: str) -> str:
    # Prefixes make the key's purpose clear and reduce accidental name collisions.
    cache_key = f"product:{product_id}"

    # redis-py returns None when GET does not find the key; that condition is a cache miss.
    cached_json = redis_client.get(cache_key)
    if cached_json is not None:
        return cached_json

    # The database remains authoritative, so a miss is recoverable.
    product_json = read_product_from_database(product_id)

    # ex is a TTL in seconds. SET and the expiration are applied as one Redis command.
    redis_client.set(cache_key, product_json, ex=300)
    return product_json
```

**TTL** means time to live. It is a countdown until a key expires. Reading a key does not refresh
its TTL. Use `EXPIRE` when the expiry must be changed, or write the key again with `SET ... EX`.
`TTL` returns:

- a non-negative number for the remaining seconds;
- `-1` when the key exists but has no expiry; and
- `-2` when the key does not exist.

Expiration is not the same as **eviction**. Expiration follows the TTL you set. Eviction is the
cache's response to memory pressure and depends on the configured eviction policy.

When source data changes, delete or update the related cache entry. A common safe ordering is:

1. commit the database update;
2. delete the cached value; and
3. let the next read repopulate it.

A TTL limits how long a missed invalidation can serve stale data, but it does not make invalidation
unnecessary for freshness-sensitive data. To prevent a cache stampede after a popular key expires,
consider jittered TTLs, request coalescing, or a short-lived lock.

Related caching patterns differ in who owns each read or write:

- **Read-through** uses a cache library or integration that loads a missing value from the source.
  The Redis server does not automatically know how to query an arbitrary application database.
- **Write-through** synchronously updates the cache and authoritative store on the write path. The
  two writes are not automatically one atomic transaction, so partial failures still need handling.
- **Write-behind** acknowledges a cache write before asynchronously persisting it to the source. It
  can reduce write latency, but data can be lost if the pending write is not durably queued and the
  cache fails before persistence completes.

### 3. Pipelines and transactions

A redis-py **pipeline** batches commands so that fewer network round trips are needed. With the
non-cluster `redis.Redis` client used in this guide, `pipeline()` defaults to executing the queued
commands as a `MULTI`/`EXEC` transaction. Set `transaction=False` when batching is wanted without
transactional execution. Do not transfer that assumption to every Redis Cluster pipeline: cluster
clients must route commands to shards and cannot provide one transaction across hash slots.

Do not assume that every multi-key command works across shards. With an OSS cluster policy, keys in
a multi-key operation generally need the same hash slot. A shared hash tag such as
`order:{42}:header` and `order:{42}:lines` makes the text inside braces determine their slot.

### 4. Vector indexing

Azure Managed Redis uses the **RediSearch** module for vector search. Provisioning has four
important constraints:

- enable RediSearch when the instance is created; modules cannot be added later;
- use an in-memory tier: Memory Optimized, Balanced, or Compute Optimized;
- use the **Enterprise** clustering policy; and
- use the **NoEviction** eviction policy.

Flash Optimized does not support RediSearch.

A vector is stored as a field in a Redis hash or JSON document. `FT.CREATE` defines the secondary
index. `FT.SEARCH` or `FT.AGGREGATE` executes vector queries; there is no RediSearch
`FT.VECTORADD` or `FT.VECTORSEARCH` command.

| Index | Result quality | Main trade-off |
| --- | --- | --- |
| `FLAT` | Exact k-nearest neighbours | Scans more candidates; suitable for smaller sets or exact recall |
| `HNSW` | Approximate nearest neighbours | Faster at scale, with recall/memory tuning trade-offs |

The schema must match the embeddings:

- `TYPE` is commonly `FLOAT32`;
- `DIM` must equal the vector length; and
- `DISTANCE_METRIC` can be `COSINE`, `L2`, or `IP` and should match how the model is evaluated.

Cosine is common for text embeddings, but it is not universally correct. Keep the same embedding
model and preprocessing for indexed and query vectors.

Hybrid retrieval combines a metadata filter with KNN search. For example, a RAG application can
first restrict results to the current tenant and documents the caller may read, then rank the
remaining documents by vector distance.

### 5. Tiers, clustering, and security

Azure Managed Redis has four performance families:

| Tier | Resource balance | Typical reason to choose it |
| --- | --- | --- |
| Memory Optimized | More memory per vCPU | Large cache with modest throughput needs |
| Balanced | Balanced memory and compute | General-purpose starting point |
| Compute Optimized | More vCPUs per GB | Throughput-intensive workload |
| Flash Optimized | RAM plus NVMe flash | Large, read-heavy set where lower cost outweighs latency |

All tiers have an SLA when high availability is enabled. High availability is enabled by default;
disabling it removes replication and affects the SLA. Select a tier and size from measured memory,
throughput, connection, and latency requirements rather than a fixed “production tier” rule.

Azure Managed Redis supports three client-facing clustering policies:

- **OSS cluster** usually gives the best throughput, but the client must support Redis Cluster.
- **Enterprise cluster** exposes one endpoint through a proxy and is required by RediSearch.
- **Non-clustered** is available only for smaller instances and is mainly a compatibility choice.

Use TLS. Azure Managed Redis uses port `10000`, not the `6380` port associated with Azure Cache for
Redis. Microsoft Entra authentication is the default and preferred approach. A Redis client using
Entra must refresh its token before expiry; the `redis-entraid` provider handles that renewal for
redis-py. Do not disable certificate validation: Azure Managed Redis uses publicly trusted
certificates, not self-signed certificates.

## Setup

The following Bash commands target Azure Cloud Shell or Bash with Azure CLI 2.75 or later. Azure
Managed Redis is not available in every Azure region, so confirm that the chosen SKU is available in
the region. This example uses West Europe and a small Balanced instance.

### Prerequisites

- an Azure subscription and permission to create resources;
- Azure CLI signed in with `az login`; and
- permission to read your signed-in user's object ID and create a Redis access assignment.

```bash
# Replace the placeholders before running the block.
RG="<resource-group>"
LOCATION="westeurope"
REDIS_NAME="<regionally-unique-redis-name>"

# Create the resource group in the same region as the consuming application when practical.
az group create --name "$RG" --location "$LOCATION"

# Create Azure Managed Redis, not the retiring Azure Cache for Redis service.
# RediSearch requires EnterpriseCluster and NoEviction, and modules are fixed at creation time.
az redisenterprise create \
  --cluster-name "$REDIS_NAME" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Balanced_B1 \
  --clustering-policy EnterpriseCluster \
  --eviction-policy NoEviction \
  --modules name=RediSearch \
  --access-keys-authentication Disabled \
  --public-network-access Enabled \
  --minimum-tls-version 1.2

# Grant the signed-in developer the default Redis data access policy.
# For an Azure-hosted app, assign its managed identity object ID instead.
PRINCIPAL_ID=$(az ad signed-in-user show --query id --output tsv)
az redisenterprise database access-policy-assignment create \
  --resource-group "$RG" \
  --cluster-name "$REDIS_NAME" \
  --database-name default \
  --access-policy-assignment-name "ai200-developer" \
  --access-policy-name default \
  --object-id "$PRINCIPAL_ID"

# Read the generated endpoint. Every Azure Managed Redis instance uses port 10000.
REDIS_HOST=$(az redisenterprise show \
  --cluster-name "$REDIS_NAME" \
  --resource-group "$RG" \
  --query hostName \
  --output tsv)
echo "Redis host: $REDIS_HOST"
echo "Redis TLS port: 10000"

# Test end-to-end connectivity with the identity established by az login.
az redisenterprise test-connection \
  --name "$REDIS_NAME" \
  --resource-group "$RG" \
  --auth entra
```

The access-policy-assignment CLI group is currently marked preview even though Entra data access is
the normal service authentication path. You can make the same assignment under **Authentication →
Microsoft Entra Authentication** in the portal.

## Hands-on (Python)

Create a virtual environment and install the current clients:

```bash
# A virtual environment isolates this sample's packages from the system Python installation.
python -m venv .venv
source .venv/bin/activate

# redis-entraid depends on redis-py and renews Entra tokens for long-lived connections.
python -m pip install redis-entraid azure-identity

# DefaultAzureCredential can use the identity established by Azure CLI during local development.
export REDIS_HOST="<name>.<region>.redis.azure.net"
```

### Cache operations

```python
"""Run basic Azure Managed Redis cache operations with Microsoft Entra authentication."""

import json
import os

import redis
from redis_entraid.cred_provider import create_from_default_azure_credential

# The provider obtains and renews tokens for the Azure Redis resource scope.
credential_provider = create_from_default_azure_credential(
    ("https://redis.azure.com/.default",),
)

# decode_responses converts Redis byte strings to Python str values for this text-only sample.
client = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=10000,
    ssl=True,
    decode_responses=True,
    credential_provider=credential_provider,
    socket_connect_timeout=10,
)

# PING confirms that DNS, networking, TLS, authentication, and Redis are all working.
print("PING:", client.ping())

product = {"id": "42", "name": "Vector handbook", "price": 24.0}

# json.dumps serializes the Python dictionary to text; ex sets a 300-second TTL atomically.
client.set("product:42", json.dumps(product), ex=300)

# json.loads converts the cached JSON string back to a Python dictionary.
cached_product = json.loads(client.get("product:42"))
print("Cached product:", cached_product)
print("Remaining TTL:", client.ttl("product:42"))

# HSET mapping writes all hash fields with one command; HINCRBY updates a field atomically.
client.hset("usage:contoso", mapping={"requests": 0, "tokens": 0})
client.hincrby("usage:contoso", "requests", 1)

# DELETE explicitly invalidates the cached product after its source record changes.
client.delete("product:42")

# Close returns sockets held by the client/pool when this short-lived script is finished.
client.close()
```

### Vector index and KNN query

This deliberately uses three-dimensional toy vectors so the storage format is visible. Real
embeddings must use the dimensions produced by the selected model.

```python
"""Create a RediSearch HNSW index over Redis hashes and execute a filtered KNN query."""

import os
import struct

import redis
from redis_entraid.cred_provider import create_from_default_azure_credential


def float32_bytes(values: list[float]) -> bytes:
    """Encode Python floats as the FLOAT32 byte layout declared in the index schema."""
    # Redis expects little-endian 32-bit floats. The '<' prefix makes byte order explicit on every CPU.
    return struct.pack(f"<{len(values)}f", *values)


# The credential provider refreshes Entra tokens instead of keeping a static password in code.
credential_provider = create_from_default_azure_credential(
    ("https://redis.azure.com/.default",),
)

# Keep binary responses enabled because vector fields contain arbitrary bytes, not UTF-8 text.
client = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=10000,
    ssl=True,
    credential_provider=credential_provider,
)

# FT.CREATE builds a secondary index over hashes whose keys begin with "doc:".
# HNSW provides approximate nearest-neighbour search; the attribute count is six name/value tokens.
try:
    client.execute_command(
        "FT.CREATE",
        "idx:documents",
        "ON",
        "HASH",
        "PREFIX",
        1,
        "doc:",
        "SCHEMA",
        "title",
        "TEXT",
        "category",
        "TAG",
        "embedding",
        "VECTOR",
        "HNSW",
        6,
        "TYPE",
        "FLOAT32",
        "DIM",
        3,
        "DISTANCE_METRIC",
        "COSINE",
    )
except redis.ResponseError as error:
    # Re-running the sample is safe only when the existing index has the same intended schema.
    if "Index already exists" not in str(error):
        raise

documents = [
    ("doc:1", "Caching guide", "ai", [0.90, 0.10, 0.05]),
    ("doc:2", "Vector retrieval", "ai", [0.82, 0.18, 0.08]),
    ("doc:3", "Travel policy", "hr", [0.05, 0.10, 0.95]),
]

for key, title, category, embedding in documents:
    # HSET stores searchable metadata and the binary vector together under one Redis key.
    client.hset(
        key,
        mapping={
            "title": title,
            "category": category,
            "embedding": float32_bytes(embedding),
        },
    )

query_blob = float32_bytes([0.88, 0.12, 0.06])

# The TAG filter limits candidates to category "ai" before KNN ranking.
# DIALECT 2 is required for this RediSearch vector-query syntax.
result = client.execute_command(
    "FT.SEARCH",
    "idx:documents",
    "(@category:{ai})=>[KNN 2 @embedding $query AS distance]",
    "PARAMS",
    2,
    "query",
    query_blob,
    "SORTBY",
    "distance",
    "RETURN",
    2,
    "title",
    "distance",
    "DIALECT",
    2,
)

print(result)
client.close()
```

## Exam gotchas

- Azure Managed Redis and Azure Cache for Redis are different services; use `az redisenterprise`
  for Azure Managed Redis.
- Azure Managed Redis uses TLS port `10000`.
- Microsoft Entra authentication is the default; an identity still needs a Redis data access policy.
- A TTL does not refresh on `GET`, and expiration is different from memory-pressure eviction.
- Pipelines reduce round trips; they do not automatically solve cross-slot restrictions.
- Enable modules at creation. RediSearch cannot be added later.
- RediSearch requires Enterprise clustering, `NoEviction`, and a supported in-memory tier.
- Vectors are fields in hashes or JSON documents. RediSearch indexes them; “Vector” is not a
  normal core Redis value type.
- Use `FT.CREATE` plus `FT.SEARCH`; `FT.VECTORADD` and `FT.VECTORSEARCH` are not RediSearch commands.
- `DIM`, numeric type, distance metric, and the query vector must agree with the indexed embeddings.
- `FLAT` is exact; `HNSW` trades a small amount of recall and more memory for faster ANN search.
- Keep certificate verification enabled. `ssl_cert_reqs=None` weakens TLS and is unnecessary for
  Azure Managed Redis.

## Cleanup

Delete only the practice resource group after confirming it contains no resources you need:

```bash
# Resource-group deletion is irreversible and deletes every resource inside the named group.
az group delete --name "$RG" --yes --no-wait
```

## Quiz yourself

Take the **azure-managed-redis** quiz in the [quiz app](../../quiz/) (bank:
[`azure-managed-redis.json`](../../quiz/src/questions/02-data-services/azure-managed-redis.json)).

## Further reading

- [Azure Managed Redis overview](https://learn.microsoft.com/azure/redis/overview)
- [Create an Azure Managed Redis instance](https://learn.microsoft.com/azure/redis/quickstart-create-managed-redis)
- [Connect from Python with Microsoft Entra ID](https://learn.microsoft.com/azure/redis/python-get-started)
- [Azure Managed Redis architecture and cluster policies](https://learn.microsoft.com/azure/redis/architecture)
- [Microsoft Entra authentication](https://learn.microsoft.com/azure/redis/entra-for-authentication)
- [Redis modules in Azure Managed Redis](https://learn.microsoft.com/azure/redis/redis-modules)
- [Vector search in Azure Managed Redis](https://learn.microsoft.com/azure/redis/overview-vector-similarity)
- [Redis vector search syntax](https://redis.io/docs/latest/develop/ai/search-and-query/vectors/)
- [Azure Cache for Redis retirement FAQ](https://learn.microsoft.com/azure/azure-cache-for-redis/retirement-faq)
