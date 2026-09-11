# Azure Cosmos DB for NoSQL

**Domain:** 02 — Develop AI solutions by using Azure data management services (25–30%)
**Maps to skill:** *Connect to Azure Cosmos DB for NoSQL by using the SDK and run queries* ·
*Optimize query performance and Request Units by using indexing policies and consistency levels* ·
*Store and retrieve embeddings and execute vector similarity search* · *Implement a change feed
processor*

## What it is

**Azure Cosmos DB for NoSQL** is a managed, partitioned document database. It stores JSON items in
containers and exposes a SQL-like query language. It can distribute a container's data and
throughput across physical partitions and replicate the account to Azure regions.

```text
account
└── database
    └── container  ← partition key, indexing policy, throughput, optional vector policy
        └── item   ← JSON object with a required id
```

The service is also an operational vector store: an item can contain its business data, metadata,
and an embedding. A query can combine ordinary filters with `VectorDistance` so a RAG application
retrieves only relevant, permitted content.

Do not confuse the product's APIs. This guide is specifically for **Azure Cosmos DB for NoSQL**,
formerly called the SQL or Core (SQL) API.

## Why it's on the exam

Expect scenarios that require you to:

- reuse a `CosmosClient`, perform point reads, and issue parameterized queries;
- choose a partition key from both data growth and request patterns;
- reduce Request Unit (RU) consumption with point reads, partition routing, projections, and indexes;
- choose a consistency level from freshness, latency, availability, and RU requirements;
- create a new container with matching vector and vector-index policies;
- choose `flat`, `quantizedFlat`, or `diskANN` for the vector workload; and
- process the change feed with leases/checkpoints or continuation tokens.

## Core concepts

### 1. Partitions and request routing

A **logical partition** contains all items with the same partition-key value. Azure maps many
logical partitions onto service-managed **physical partitions**.

A good partition key:

- has enough distinct values to spread storage and requests;
- distributes hot traffic rather than concentrating it in one value;
- appears in common query and transactional patterns; and
- will not let one value approach the 20-GB logical-partition limit.

High cardinality alone is insufficient. For example, a day-sized time bucket accumulates many
values over its lifetime, yet all of today's writes still share one current value and can become
hot. Conversely, a tenant ID routes tenant-scoped queries well but can outgrow one logical
partition for a very large tenant. Hierarchical partition keys can add levels when the data and
request pattern justify them.

The container's partition-key **path** is fixed at creation. An existing item's partition-key value
also cannot be changed in place: create a new item under the new value and delete the old item.

The cheapest read pattern is normally a **point read**, which supplies both `id` and the complete
partition-key value. A 1-KB point read costs 1 RU with session or eventual consistency; strong and
bounded-staleness reads consume twice the RUs. A query that omits partition routing can fan out to
all physical partitions; fan-out is valid when the business query requires it, but it consumes more
work than a targeted operation.

Standard stored procedures and transactional batches are scoped to one logical partition. Cosmos
DB also has a separately enabled distributed-transactions feature with different constraints; do
not assume that feature is present when a scenario asks about a normal transactional batch.

### 2. Request Units and capacity modes

An RU normalizes CPU, I/O, and memory used by a database operation. The charge depends on item size,
indexing, query shape, result count, consistency, and other work—not merely the number of calls.

| Mode | Best fit | Billing idea |
| --- | --- | --- |
| Manual provisioned throughput | Stable, known demand | Reserve a fixed RU/s amount |
| Autoscale provisioned throughput | Variable demand needing automatic scale | Configure a maximum; service scales within its range |
| Serverless | Intermittent, low-volume traffic | Pay for consumed RUs and storage |

If consumed throughput exceeds available capacity, Cosmos DB returns HTTP `429` with a retry delay.
Current SDKs retry throttled requests according to their retry policy; persistent 429s still require
capacity or query/data-model changes.

Use these optimizations in roughly this order:

1. Use a point read when `id` and partition key are known.
2. Route a query to one partition when the request is partition-scoped.
3. Return only required properties instead of `SELECT *`.
4. Parameterize queries and use pagination/continuation tokens.
5. Add the range, composite, spatial, full-text, or vector indexes the query actually needs.
6. Inspect RU charge, query metrics, and index metrics before changing capacity.

Azure Cosmos DB free tier applies the first 1,000 RU/s and 25 GB for the **lifetime** of one eligible
account per subscription. It is not a one-year benefit and is not available for serverless accounts.

### 3. Consistency levels

From strongest to weakest, the five levels are:

| Level | Guarantee to remember | Trade-off |
| --- | --- | --- |
| Strong | Linearizable; reads return the latest committed value | Highest coordination latency and lower failure availability |
| Bounded staleness | Lag is bounded by versions (`K`) and time (`T`) | Stronger guarantee with extra read cost |
| Session | Read-your-writes and monotonic guarantees within a session | Default and common application choice |
| Consistent prefix | Writes are observed in order, without gaps in the prefix | A reader may lag |
| Eventual | Replicas converge with no ordering guarantee | Lowest coordination and weakest freshness |

Strong consistency is not limited to a single region. With multiple regions it synchronously
coordinates commits, so distance between regions increases write latency. Accounts with strong or
bounded-staleness consistency read from two replicas; for the same RU budget, their read throughput
is half that of session, consistent-prefix, or eventual reads.

An SDK can relax consistency for an individual read, but a normal consistency override cannot make
a request stronger than the account default. Keep one long-lived client so session tokens and
connections are reused correctly.

### 4. Indexing policies

New containers use **consistent** indexing and range-index every string and number by default. The
supported general indexing modes are `consistent` and `none`. Lazy indexing still exists only by
exception for legacy/special cases, can return incomplete results, and cannot be selected for a
normal new container.

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [{"path": "/*"}],
  "excludedPaths": [
    {"path": "/largeUnqueriedPayload/*"},
    {"path": "/embedding/*"}
  ],
  "compositeIndexes": [
    [
      {"path": "/tenantId", "order": "ascending"},
      {"path": "/updatedAt", "order": "descending"}
    ]
  ]
}
```

Exclude paths that are written but never filtered, sorted, or projected through an index. That can
lower index storage and write RUs. Do not indiscriminately exclude the partition-key properties
used by queries. A composite index is commonly required for an `ORDER BY` over multiple properties
or to optimize particular filter-plus-sort shapes.

`id` and `_ts` are always indexed in consistent mode. A vector path should be excluded from the
ordinary range index and listed separately under `vectorIndexes`; otherwise vector writes cost more
without benefiting vector retrieval.

### 5. Vector search

Vector search in Azure Cosmos DB for NoSQL has been generally available since 2024. The account must
have the `EnableNoSQLVectorSearch` capability, and the vector container must be created **after**
that capability is enabled.

Two policies work together:

- the **vector embedding policy** defines each path's numeric type, dimensions, and distance
  function; and
- the indexing policy's **vector index** defines the search index for that path.

The vector policy and vector index cannot be added to or changed on an existing container. Create a
new container and migrate data when those settings must change.

Vector indexing is not supported on a database that uses shared throughput. Give the vector
container dedicated throughput, as the setup and Python example below do.

| Vector index | Search | Maximum dimensions | Best fit |
| --- | --- | ---: | --- |
| `flat` | Exact | 505 | Small or filtered candidate sets requiring full recall |
| `quantizedFlat` | Brute-force over quantized vectors | 4,096 | Smaller-to-medium sets needing lower RU/latency |
| `diskANN` | Approximate graph search | 4,096 | Larger sets needing scalable low-latency search |

`quantizedFlat` and `diskANN` need at least 1,000 indexed vectors to build an effective index. With
fewer than 1,000, Cosmos DB performs a full scan and RU cost can be higher.

Supported vector element types include `float32`, `float16`, `int8`, and `uint8`. Supported distance
functions include cosine, dot product, and Euclidean distance. Choose values that match the
embedding model and use the same model for stored and query vectors.

Vector queries use `VectorDistance`. Bound the result set with `TOP` or `LIMIT`; an unbounded vector
query can consume far more RUs and latency than the application needs:

```sql
SELECT TOP 5 c.id,
             c.content,
             VectorDistance(c.embedding, @queryVector) AS distance
FROM c
WHERE c.tenantId = @tenantId
ORDER BY VectorDistance(c.embedding, @queryVector)
```

### 6. Change feed

The change feed is a persistent, incremental record of container changes. Ordering is guaranteed
within a logical partition, not as one global order across every partition.

There are two modes:

| Mode | Captures | Retention |
| --- | --- | --- |
| Latest version | Latest create/update state; no deletes or operation type | Available while the item exists, for container lifetime |
| All versions and deletes | Every create, update, and delete plus metadata | Within the account's continuous-backup retention window |

For latest-version mode, use a soft-delete marker when consumers must see deletions. All-versions-
and-deletes requires continuous backup **and** enabling the account's **All versions and deletes
change feed mode** feature. It can start from `Now` or a continuation token, not from the beginning
or an arbitrary time.

A production **change feed processor** distributes feed ranges among workers by using a lease
container. The lease records ownership and checkpoints so processing can resume. An Azure Functions
Cosmos DB trigger provides this push-style processor model. The Python SDK also supports the pull
model with `query_items_change_feed`; the application must persist continuation tokens and
coordinate feed ranges itself.

Handlers should be idempotent because a failure after side effects but before checkpointing can
cause a change to be delivered again.

### 7. Item model and concurrency

Every item needs a string `id` that is unique within its logical partition. An item is limited to
2 MB. Cosmos DB adds system properties including:

- `_etag` for optimistic concurrency;
- `_ts` for the last-modified Unix timestamp;
- `_rid` for the internal resource identifier; and
- `_self` for the resource address.

Use `_etag` with an `If-Match` condition when an update must fail rather than overwrite a concurrent
change. Use PATCH when only a few properties change; it avoids sending an entire replacement item,
although the actual RU saving depends on the operation and indexed paths.

## Setup

These Bash commands create a single-region, manually provisioned learning account in West Europe.
The account name must be globally unique and lowercase. Remove `--enable-free-tier true` when the
subscription already has its free-tier account.

### Prerequisites

- Azure CLI signed in with `az login`;
- permission to create Cosmos DB resources and native Cosmos DB data-role assignments; and
- permission to read the signed-in Microsoft Entra user object ID.

```bash
# Replace the placeholders before running the block.
RG="<resource-group>"
LOCATION="westeurope"
ACCOUNT_NAME="<globally-unique-cosmos-account>"
DATABASE_NAME="products-db"
CONTAINER_NAME="products"

az group create --name "$RG" --location "$LOCATION"

# Session is the normal default; the option is explicit here so the learning setup is visible.
az cosmosdb create \
  --resource-group "$RG" \
  --name "$ACCOUNT_NAME" \
  --locations regionName="$LOCATION" failoverPriority=0 isZoneRedundant=false \
  --default-consistency-level Session \
  --enable-free-tier true

# Vector search is GA but still requires enabling this account capability.
az cosmosdb update \
  --resource-group "$RG" \
  --name "$ACCOUNT_NAME" \
  --capabilities EnableNoSQLVectorSearch

# Create a database without shared throughput; the container receives dedicated throughput below.
az cosmosdb sql database create \
  --resource-group "$RG" \
  --account-name "$ACCOUNT_NAME" \
  --name "$DATABASE_NAME"

# A normal container is useful for CRUD practice. Vector policy is demonstrated separately in Python.
az cosmosdb sql container create \
  --resource-group "$RG" \
  --account-name "$ACCOUNT_NAME" \
  --database-name "$DATABASE_NAME" \
  --name "$CONTAINER_NAME" \
  --partition-key-path /tenantId \
  --throughput 400

# Grant the current developer native Cosmos DB data-plane access without exposing account keys.
PRINCIPAL_ID=$(az ad signed-in-user show --query id --output tsv)
DATA_CONTRIBUTOR_ID=$(az cosmosdb sql role definition list \
  --resource-group "$RG" \
  --account-name "$ACCOUNT_NAME" \
  --query "[?roleName=='Cosmos DB Built-in Data Contributor'].name | [0]" \
  --output tsv)

az cosmosdb sql role assignment create \
  --resource-group "$RG" \
  --account-name "$ACCOUNT_NAME" \
  --role-definition-id "$DATA_CONTRIBUTOR_ID" \
  --principal-id "$PRINCIPAL_ID" \
  --scope "/"

# DefaultAzureCredential uses this endpoint with the identity established by az login.
COSMOS_ENDPOINT=$(az cosmosdb show \
  --resource-group "$RG" \
  --name "$ACCOUNT_NAME" \
  --query documentEndpoint \
  --output tsv)
echo "Cosmos DB endpoint: $COSMOS_ENDPOINT"
```

Capability registration and role propagation can take several minutes. For an Azure-hosted
application, assign the data role to its managed identity rather than the developer identity.

## Hands-on (Python)

```bash
# Isolate this sample's Python packages from the system installation.
python -m venv .venv
source .venv/bin/activate

# Install the current data client and the credential chain used for passwordless authentication.
python -m pip install azure-cosmos azure-identity

export COSMOS_ENDPOINT="https://<account>.documents.azure.com:443/"
export COSMOS_DATABASE="products-db"
export COSMOS_CONTAINER="products"
```

### CRUD, point reads, queries, and RU charge

```python
"""Use one CosmosClient for item operations and a partition-routed query."""

import os
from collections.abc import Mapping
from typing import Any

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential


# A response hook runs for every response page, so the list can capture each page's RU charge.
request_charges: list[float] = []


def capture_charge(headers: Mapping[str, str], _: dict[str, Any]) -> None:
    """Record a response page's request charge when Cosmos DB returns one."""
    # get returns None if a response lacks the header; most data operations include it.
    charge = headers.get("x-ms-request-charge")
    if charge is not None:
        # HTTP headers are strings, so float converts the charge before it is summed.
        request_charges.append(float(charge))


# Reuse this client for the application's lifetime so connections and session tokens are reused.
client = CosmosClient(
    url=os.environ["COSMOS_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

database = client.get_database_client(os.environ["COSMOS_DATABASE"])
container = database.get_container_client(os.environ["COSMOS_CONTAINER"])

product = {
    "id": "product-42",
    "tenantId": "contoso",
    "name": "Vector handbook",
    "category": "books",
    "price": 24.0,
}

# Upsert creates the item or replaces the matching id/partition-key item.
request_charges.clear()
container.upsert_item(body=product, response_hook=capture_charge)
print("Upsert RUs:", sum(request_charges))

# A point read supplies both identity components and avoids running a query.
request_charges.clear()
found = container.read_item(
    item="product-42",
    partition_key="contoso",
    response_hook=capture_charge,
)
print("Point-read RUs:", sum(request_charges))
print(found["name"])

# Query parameters keep values separate from query syntax.
query = """
SELECT c.id, c.name, c.price
FROM c
WHERE c.tenantId = @tenantId AND c.category = @category
"""
parameters = [
    {"name": "@tenantId", "value": "contoso"},
    {"name": "@category", "value": "books"},
]

# partition_key routes this query to one logical partition rather than fanning out.
request_charges.clear()
results = container.query_items(
    query=query,
    parameters=parameters,
    partition_key="contoso",
    populate_query_metrics=True,
    response_hook=capture_charge,
)

# Iterating executes all required result pages; large applications should expose pagination.
for item in results:
    print(item)

print("Query RUs across all pages:", sum(request_charges))

# PATCH changes one property while preserving the rest of the item.
container.patch_item(
    item="product-42",
    partition_key="contoso",
    patch_operations=[{"op": "set", "path": "/price", "value": 22.0}],
)

client.close()
```

The SDK operation result is the item body; it does not contain a `request_charge` property. Read
the `x-ms-request-charge` response header, as the sample does. A paged query can receive several
charges, so add the response-page charges instead of reporting only the last page.

### Create a vector container and query it

This small example uses a `flat` exact index because it contains only toy vectors. A production
container with a larger corpus would usually evaluate `quantizedFlat` and `diskANN`.

```python
"""Create an immutable vector policy, store toy embeddings, and run a filtered query."""

import os

from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential

# Reuse one authenticated client across setup and data operations.
client = CosmosClient(
    url=os.environ["COSMOS_ENDPOINT"],
    credential=DefaultAzureCredential(),
)
database = client.get_database_client(os.environ.get("COSMOS_DATABASE", "products-db"))

# The embedding policy tells Cosmos DB how to interpret values at /embedding.
vector_embedding_policy = {
    "vectorEmbeddings": [
        {
            "path": "/embedding",
            "dataType": "float32",
            "dimensions": 3,
            "distanceFunction": "cosine",
        }
    ]
}

# Exclude the vector from the ordinary range index and add a dedicated exact vector index.
indexing_policy = {
    "indexingMode": "consistent",
    "automatic": True,
    "includedPaths": [{"path": "/*"}],
    "excludedPaths": [
        {"path": "/\"_etag\"/?"},
        {"path": "/embedding/*"},
    ],
    "vectorIndexes": [{"path": "/embedding", "type": "flat"}],
}

# create_container_if_not_exists does not retrofit a policy onto an incompatible existing container.
container = database.create_container_if_not_exists(
    id="documents-vectors",
    partition_key=PartitionKey(path="/tenantId"),
    indexing_policy=indexing_policy,
    vector_embedding_policy=vector_embedding_policy,
    offer_throughput=400,
)

documents = [
    {"id": "doc-1", "tenantId": "contoso", "content": "Cache with a TTL.", "embedding": [0.90, 0.10, 0.05]},
    {"id": "doc-2", "tenantId": "contoso", "content": "Search vector data.", "embedding": [0.82, 0.18, 0.08]},
    {"id": "doc-3", "tenantId": "fabrikam", "content": "Travel policy.", "embedding": [0.05, 0.10, 0.95]},
]

for document in documents:
    container.upsert_item(document)

query_vector = [0.88, 0.12, 0.06]
query = """
SELECT TOP 2 c.id,
             c.content,
             VectorDistance(c.embedding, @queryVector) AS distance
FROM c
WHERE c.tenantId = @tenantId
ORDER BY VectorDistance(c.embedding, @queryVector)
"""

# Routing to contoso is both cheaper and prevents another tenant from entering the candidate set.
matches = container.query_items(
    query=query,
    parameters=[
        {"name": "@queryVector", "value": query_vector},
        {"name": "@tenantId", "value": "contoso"},
    ],
    partition_key="contoso",
)

for match in matches:
    print(match)

client.close()
```

### Pull and checkpoint the latest-version change feed

```python
"""Read a page of latest-version changes and persist its continuation position."""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

client = CosmosClient(
    url=os.environ["COSMOS_ENDPOINT"],
    credential=DefaultAzureCredential(),
)
database = client.get_database_client(os.environ["COSMOS_DATABASE"])
container = database.get_container_client(os.environ["COSMOS_CONTAINER"])

# This local file is only a learning checkpoint and is ignored by this repository. A distributed
# worker needs durable shared state.
checkpoint_path = Path("change-feed.continuation")
continuation = (
    checkpoint_path.read_text(encoding="utf-8").strip()
    if checkpoint_path.exists()
    else None
)

# The response hook avoids relying on the SDK client's shared last_response_headers state.
feed_headers: dict[str, str] = {}


def capture_feed_headers(headers: Mapping[str, str], _: dict[str, Any]) -> None:
    """Keep the most recent change-feed page headers, including its continuation ETag."""
    feed_headers.clear()
    feed_headers.update(headers)


if continuation:
    # A continuation token resumes after changes the previous run observed.
    changes = container.query_items_change_feed(
        continuation=continuation,
        response_hook=capture_feed_headers,
    )
else:
    # Beginning reads current item versions from the start of the container's retained feed.
    changes = container.query_items_change_feed(
        start_time="Beginning",
        response_hook=capture_feed_headers,
    )

for changed_item in changes:
    # Make real side effects idempotent because processing can repeat before a checkpoint is saved.
    print(changed_item["id"], changed_item.get("_ts"))

# The SDK returns the next continuation position in the latest response page's ETag header.
next_continuation = feed_headers.get("etag")
if next_continuation:
    checkpoint_path.write_text(next_continuation, encoding="utf-8")

client.close()
```

For production, prefer a change feed processor or Azure Functions trigger when you want automatic
lease balancing and checkpointing. The Python pull API method is `query_items_change_feed`, not
`query_change_feed`.

## Exam gotchas

- The partition-key path is fixed at container creation, and an item's partition-key value cannot be
  updated in place.
- A point read needs both `id` and partition key and is normally cheaper than a query.
- Session is the default consistency level. Strong consistency can span regions but adds synchronous
  coordination; it is not “single-region only.”
- New containers use consistent range indexing for strings and numbers. Lazy is not a normal choice
  for a new container.
- Excluding unused paths can reduce write RUs; add required composite or specialized indexes based
  on measured query shapes.
- Vector search is GA, but the account capability must be enabled and policies are fixed when the
  vector container is created.
- `flat` is exact and limited to 505 dimensions; `quantizedFlat` and `diskANN` support up to 4,096.
- `quantizedFlat` and `diskANN` fall back to a full scan below 1,000 indexed vectors.
- Vector indexing does not support shared database throughput; use dedicated container throughput.
- Latest-version change feed does not expose deletes or every intermediate version. Use a soft
  delete or all-versions-and-deletes as requirements dictate.
- Change feed ordering is per logical partition. Leases distribute work; checkpoints record progress.
- A transactional batch cannot span logical partitions.
- HTTP 429 means throughput was exhausted, not that the item or query is invalid.

## Cleanup

Delete only the dedicated practice resource group after checking its contents:

```bash
# This irreversible operation deletes the Cosmos DB account and every other resource in the group.
az group delete --name "$RG" --yes --no-wait
```

## Quiz yourself

Take the **cosmos-db-nosql** quiz in the [quiz app](../../quiz/) (bank:
[`cosmos-db-nosql.json`](../../quiz/src/questions/02-data-services/cosmos-db-nosql.json)).

## Further reading

- [Azure Cosmos DB for NoSQL documentation](https://learn.microsoft.com/azure/cosmos-db/nosql/)
- [Python SDK quickstart](https://learn.microsoft.com/azure/cosmos-db/quickstart-python)
- [Partitioning overview](https://learn.microsoft.com/azure/cosmos-db/partitioning-overview)
- [Request Units](https://learn.microsoft.com/azure/cosmos-db/request-units)
- [Consistency levels](https://learn.microsoft.com/azure/cosmos-db/consistency-levels)
- [Indexing policies](https://learn.microsoft.com/azure/cosmos-db/index-policy)
- [Vector search](https://learn.microsoft.com/azure/cosmos-db/vector-search)
- [Python vector index and query sample](https://learn.microsoft.com/azure/cosmos-db/how-to-python-vector-index-query)
- [Change feed overview](https://learn.microsoft.com/azure/cosmos-db/change-feed)
- [Change feed modes and account enablement](https://learn.microsoft.com/azure/cosmos-db/change-feed-modes)
- [Change feed pull model](https://learn.microsoft.com/azure/cosmos-db/change-feed-pull-model)
- [Microsoft Entra data-plane RBAC](https://learn.microsoft.com/azure/cosmos-db/how-to-connect-role-based-access-control)
