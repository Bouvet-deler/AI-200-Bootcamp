# Azure Database for PostgreSQL flexible server with pgvector

**Domain:** 02 — Develop AI solutions by using Azure data management services (25–30%)
**Maps to skill:** *Connect and query Azure Database for PostgreSQL by using SDKs* · *Model
schemas and implement indexing strategies* · *Optimize query latency and reduce pgvector compute
overhead* · *Configure compute, memory, and storage for vector workloads* · *Run vector similarity
search and RAG with metadata filters* · *Optimize connections*

## What it is

**Azure Database for PostgreSQL flexible server** is Microsoft's managed PostgreSQL service.
Azure operates the server, backups, patching, storage, and optional high availability while the
application continues to use PostgreSQL SQL and client libraries.

**pgvector** is an open-source PostgreSQL extension. It adds vector column types, distance
operators, and exact or approximate nearest-neighbour search. The product is called pgvector, but
the extension name used by Azure and SQL is `vector`:

```sql
CREATE EXTENSION vector;
```

This combination is useful when relational metadata and embeddings belong in the same transaction.
For example, a RAG system can filter documents by tenant, security label, language, and expiry date
with SQL before ranking the remaining rows by embedding distance.

> Mental model:
>
> ```text
> question → embedding model → query vector
>                                │
>                                ▼
> PostgreSQL: metadata filter + vector distance + LIMIT top-k
>                                │
>                                ▼
> retrieved text → prompt context → language model answer
> ```

Vector search retrieves context; it does not itself generate the answer.

## Why it's on the exam

AI-200 scenarios can test whether you can:

- connect once and reuse PostgreSQL connections;
- model content, relational metadata, and a fixed-dimension vector together;
- parameterize SQL rather than concatenate user input;
- match a query distance operator to the index's operator class;
- choose an exact scan, HNSW, IVFFlat, or Azure's DiskANN option from workload requirements;
- combine vector ranking with a selective metadata filter;
- tune recall, latency, memory, storage throughput, and index-build cost; and
- choose application pooling or built-in PgBouncer for connection-heavy workloads.

The current Azure deployment model is **flexible server**. The retired Single Server commands
(`az postgres server ...`) and old `GP_Gen5_*` / `MO_Gen5_*` SKUs should not be used.

## Core concepts

### 1. Schema design

An **embedding** is a fixed-length numeric representation produced by a model. Similar inputs are
near each other according to the metric for which that model was designed.

```sql
CREATE TABLE documents (
    id text PRIMARY KEY,
    tenant_id text NOT NULL,
    category text NOT NULL,
    content text NOT NULL,
    embedding vector(1536) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
```

Important choices:

- Declare a dimension, such as `vector(1536)`, when the column will be indexed. The query vector
  must have the same length.
- Store common filter fields in typed relational columns. Use `jsonb` for genuinely flexible
  metadata, not as a substitute for every column.
- Keep the original text and source identity needed for RAG citations.
- Use the same embedding model and preprocessing for stored and query vectors. Changing models
  normally requires re-embedding the corpus and rebuilding the index.
- Do not assume one named model always has one dimension; some embedding APIs allow a requested
  output size.

pgvector also offers `halfvec`, `bit`, and sparse-vector types. `halfvec` can reduce storage and
support more dimensions at lower precision. Treat that as a measured quality/cost decision, not a
free optimization. Current pgvector HNSW and IVFFlat indexes support a `vector` column up to 2,000
dimensions and a `halfvec` column up to 4,000 dimensions. A higher-dimensional embedding therefore
needs an intentionally reduced output size, a suitable narrower type, exact search, or a different
index such as Azure's separately installed DiskANN extension. Verify the selected index's own
limits rather than assuming that a storable vector is also indexable.

### 2. Distance operators and operator classes

| Meaning | Query operator | Index operator class |
| --- | --- | --- |
| L2 / Euclidean distance | `<->` | `vector_l2_ops` |
| Negative inner product | `<#>` | `vector_ip_ops` |
| Cosine distance | `<=>` | `vector_cosine_ops` |
| L1 / taxicab distance | `<+>` | `vector_l1_ops` where supported |

Lower values sort first for the distance operators. `<#>` returns the **negative** inner product so
that PostgreSQL can use an ascending index scan.

For nonzero vectors, cosine similarity ranges from -1 to 1, so pgvector's cosine **distance**
(`1 - cosine similarity`) ranges from 0 to 2. Rank nearest results by distance in ascending order;
do not sort cosine distance descending as though it were a similarity score.

For cosine similarity, convert the returned distance only when a similarity value is actually
needed:

```sql
SELECT 1 - (embedding <=> $1::vector) AS cosine_similarity
FROM documents;
```

Cosine distance is common for semantic text retrieval, but select the metric recommended and
validated for the embedding model. An index built with `vector_cosine_ops` will not accelerate an
L2 query using `<->`.

### 3. Exact and approximate indexes

Without a vector index, PostgreSQL calculates the distance for candidate rows and performs an exact
nearest-neighbour search. Exact search has perfect recall and can be a good choice for a small or
highly selective candidate set.

Azure Database for PostgreSQL supports these vector-index approaches:

| Approach | Strength | Cost or constraint |
| --- | --- | --- |
| Exact scan | Perfect recall; no vector-index build | Compute grows with candidate count |
| HNSW (`vector` extension) | Strong speed/recall trade-off; no training step | Slower build and more memory than IVFFlat |
| IVFFlat (`vector` extension) | Faster build and less memory than HNSW | Needs representative data/training; recall depends on lists and probes |
| DiskANN (`pg_diskann` extension) | Azure-optimized scale with strong speed/recall | Separate Azure extension and its own tuning parameters |

Create an HNSW cosine index like this:

```sql
CREATE INDEX documents_embedding_hnsw
ON documents
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

- HNSW `m` controls graph connectivity. Increasing it can improve recall but uses more memory and
  build time.
- `ef_construction` controls how many candidates are considered while building the graph.
- `hnsw.ef_search` is a session or transaction setting for query-time recall versus latency.

Create an IVFFlat index after loading representative rows:

```sql
CREATE INDEX documents_embedding_ivfflat
ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Search more lists for better recall at the cost of more work for this transaction only.
BEGIN;
SET LOCAL ivfflat.probes = 10;
SELECT id FROM documents ORDER BY embedding <=> $1::vector LIMIT 10;
COMMIT;
```

`IVF`, `IVF + HNSW`, and an `ivfhnsw` access method are not pgvector index names. The supported
pgvector access method is `ivfflat`.

Use `EXPLAIN (ANALYZE, BUFFERS)` to see whether PostgreSQL chose an index and where time and I/O are
spent. A sequential scan is not automatically a defect: for a tiny table or a very selective
relational filter, it can be cheaper.

### 4. Metadata-filtered RAG retrieval

Parameterize both the vector and metadata. Filtering by tenant is a correctness and security
boundary, not just a performance optimization.

```sql
SELECT id,
       content,
       embedding <=> $1::vector AS distance
FROM documents
WHERE tenant_id = $2
  AND category = $3
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

A B-tree index can make the metadata predicate cheap:

```sql
CREATE INDEX documents_tenant_category
ON documents (tenant_id, category);
```

Approximate vector indexes and filtering interact. Depending on selectivity and the query plan, a
filter can leave fewer results than the requested `LIMIT`. Current pgvector versions support
iterative scans for HNSW and IVFFlat to keep scanning for qualifying rows. Other solutions include
partitioning by a stable tenant boundary, raising the search candidate setting, or using an exact
scan after a highly selective filter. Validate recall with representative data.

### 5. Compute, memory, and storage

Flexible server offers three compute tiers:

| Tier | Fit |
| --- | --- |
| Burstable | Development and low-concurrency workloads without sustained CPU demand |
| General Purpose | Most production workloads with balanced compute and memory |
| Memory Optimized | Workloads whose active indexes and queries benefit from more memory per vCore |

Built-in high availability is available on General Purpose and Memory Optimized, not Burstable.
Without high availability the service has a 99.9% uptime SLA; same-zone high availability has a
99.95% SLA, and zone-redundant high availability has a 99.99% SLA. Choose the availability design
from the application's recovery requirements rather than assuming that a compute tier alone
provides a particular SLA.

There is no universal “100,000 vectors means SKU X” rule. Dimension, data type, index, filters,
concurrency, recall target, ingestion rate, and cache hit rate all matter. Measure these layers:

- **CPU:** distance calculations, parallel queries, and index builds;
- **memory:** hot table/index pages and HNSW build workspace;
- **storage capacity:** vector columns, indexes, metadata, WAL, and growth;
- **IOPS and throughput:** index pages that are not in memory and write-heavy ingestion; and
- **connections:** each direct PostgreSQL connection consumes a server process and memory.

Use PostgreSQL's `COPY` mechanism rather than one insert-and-commit round trip per row when loading
a large corpus. Load bulk data before building an ANN index when possible. Increase
`maintenance_work_mem` only within available memory and monitor the build. Use
`pg_stat_progress_create_index` for supported index builds. Azure storage can be increased but not
later shrunk, so size with headroom and cost in mind.

### 6. Connection optimization

Creating a new database connection for every request adds authentication, TLS, and PostgreSQL
process overhead. Reuse a bounded application connection pool.

Flexible server also has optional built-in **PgBouncer** on port `6432` for General Purpose and
Memory Optimized tiers. Direct PostgreSQL remains on port `5432`. Azure's built-in PgBouncer uses
transaction pooling by default, so session state is not guaranteed to stay on one server connection
between transactions. Test features such as temporary tables, session settings, and prepared
statements against the selected pool mode.

Keep the application and database in nearby Azure regions, use TLS, use bounded exponential retry
for transient connection failures, and keep transactions short.

## Setup

These commands use Bash and the current flexible-server CLI. The example creates public access only
for one supplied client IP. Prefer private networking for a production solution.

### Prerequisites

- Azure CLI signed in with `az login`;
- permission to create a resource group and flexible server;
- a globally unique lowercase server name; and
- your public IPv4 address.

```bash
# Replace every angle-bracket placeholder. West Europe is the example Azure region.
RG="<resource-group>"
LOCATION="westeurope"
PG_SERVER="<globally-unique-postgres-server>"
PG_DATABASE="vector_db"
PG_ADMIN="ai200admin"
MY_IP="<public-ip-address>"

# `read -s` accepts the password without echoing it or placing a literal in shell history.
read -r -s -p "PostgreSQL administrator password: " PG_PASSWORD
printf '\n'

az group create --name "$RG" --location "$LOCATION"

# Create a flexible server with a current v5 SKU and a supported PostgreSQL major version.
az postgres flexible-server create \
  --resource-group "$RG" \
  --name "$PG_SERVER" \
  --location "$LOCATION" \
  --admin-user "$PG_ADMIN" \
  --admin-password "$PG_PASSWORD" \
  --version 17 \
  --tier GeneralPurpose \
  --sku-name Standard_D4ds_v5 \
  --storage-size 128 \
  --public-access "$MY_IP"

# The password is no longer needed by the provisioning commands in this shell.
unset PG_PASSWORD

# Azure must allowlist the binary before CREATE EXTENSION vector can run in a database.
az postgres flexible-server parameter set \
  --resource-group "$RG" \
  --server-name "$PG_SERVER" \
  --name azure.extensions \
  --value vector

# A PostgreSQL server contains multiple databases; install vector separately in each one that uses it.
az postgres flexible-server db create \
  --resource-group "$RG" \
  --server-name "$PG_SERVER" \
  --name "$PG_DATABASE"

# Read the fully qualified host name used by PostgreSQL clients.
PG_HOST=$(az postgres flexible-server show \
  --resource-group "$RG" \
  --name "$PG_SERVER" \
  --query fullyQualifiedDomainName \
  --output tsv)
echo "PostgreSQL host: $PG_HOST"
```

To enable built-in PgBouncer on a supported tier:

```bash
# PgBouncer is a server parameter; clients then use the same host with port 6432.
az postgres flexible-server parameter set \
  --resource-group "$RG" \
  --server-name "$PG_SERVER" \
  --name pgbouncer.enabled \
  --value true
```

## Hands-on (Python)

The current Psycopg package is imported as `psycopg` (Psycopg 3), not `psycopg2`.

```bash
# Create and activate an isolated environment for the sample packages.
python -m venv .venv
source .venv/bin/activate

# binary installs a prebuilt local driver; pool adds Psycopg's connection-pool package.
python -m pip install "psycopg[binary,pool]"

# Set connection data without placing it in the Python source file.
export PGHOST="<server>.postgres.database.azure.com"
export PGPORT="5432"
export PGDATABASE="vector_db"
export PGUSER="ai200admin"

# Export only while running this learning sample, so Python can read the value from its environment.
read -r -s -p "PostgreSQL administrator password: " PGPASSWORD
printf '\n'
export PGPASSWORD
```

### Create, store, filter, and search

```python
"""Store toy embeddings and run a tenant-filtered pgvector cosine search."""

import os

import psycopg


def vector_text(values: list[float]) -> str:
    """Convert a Python list to pgvector's text input form without building SQL text."""
    # str(value) formats each float; join combines them with the commas pgvector expects.
    return "[" + ",".join(str(value) for value in values) + "]"


# Keyword arguments keep each setting separate, so special characters in a password are not parsed
# as connection-string syntax. The values still come from environment variables, not source code.
connection_settings = {
    "host": os.environ["PGHOST"],
    "port": os.environ.get("PGPORT", "5432"),
    "dbname": os.environ["PGDATABASE"],
    "user": os.environ["PGUSER"],
    "password": os.environ["PGPASSWORD"],
    "sslmode": "require",
}

# with closes the connection and commits on success; an exception causes the transaction to roll back.
with psycopg.connect(**connection_settings) as connection:
    # A cursor sends SQL to PostgreSQL and exposes returned rows to Python.
    with connection.cursor() as cursor:
        # Azure first allowlists the extension at server level; SQL installs it in this database.
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # The toy vector has three dimensions. A real column must match the embedding model's output.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ai200_documents (
                id text PRIMARY KEY,
                tenant_id text NOT NULL,
                category text NOT NULL,
                content text NOT NULL,
                embedding vector(3) NOT NULL
            )
            """
        )

        documents = [
            ("doc-1", "contoso", "azure", "Cache data with a bounded TTL.", [0.90, 0.10, 0.05]),
            ("doc-2", "contoso", "azure", "Use vectors for semantic retrieval.", [0.82, 0.18, 0.08]),
            ("doc-3", "fabrikam", "hr", "Submit travel expenses monthly.", [0.05, 0.10, 0.95]),
        ]

        for document_id, tenant_id, category, content, embedding in documents:
            # %s placeholders keep values separate from SQL and prevent SQL-injection quoting bugs.
            cursor.execute(
                """
                INSERT INTO ai200_documents (id, tenant_id, category, content, embedding)
                VALUES (%s, %s, %s, %s, %s::vector)
                ON CONFLICT (id) DO UPDATE
                SET tenant_id = EXCLUDED.tenant_id,
                    category = EXCLUDED.category,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding
                """,
                (document_id, tenant_id, category, content, vector_text(embedding)),
            )

        # The relational index supports the tenant/category predicate used by retrieval queries.
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS ai200_documents_tenant_category
            ON ai200_documents (tenant_id, category)
            """
        )

        # ef_construction is the valid HNSW build option; "ef" is not a pgvector index option.
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS ai200_documents_embedding_hnsw
            ON ai200_documents
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        )

        query_vector = vector_text([0.88, 0.12, 0.06])

        # The WHERE clause enforces the tenant boundary before returning RAG context.
        cursor.execute(
            """
            SELECT id, content, embedding <=> %s::vector AS cosine_distance
            FROM ai200_documents
            WHERE tenant_id = %s AND category = %s
            ORDER BY embedding <=> %s::vector
            LIMIT 2
            """,
            (query_vector, "contoso", "azure", query_vector),
        )

        for document_id, content, distance in cursor.fetchall():
            print(document_id, round(distance, 4), content)
```

`sslmode=require` matches the simple Microsoft quickstart and encrypts the connection. For stronger
server identity validation, deploy the appropriate trusted root certificate and use
`sslmode=verify-full`.

### Reuse connections with a pool

```python
"""Borrow and return PostgreSQL connections from a bounded Psycopg pool."""

import os

from psycopg_pool import ConnectionPool

# The pool opens only a bounded number of expensive server connections and reuses them.
# Keep connection values separate so passwords containing spaces or punctuation remain valid.
connection_settings = {
    "host": os.environ["PGHOST"],
    "port": os.environ.get("PGPORT", "5432"),
    "dbname": os.environ["PGDATABASE"],
    "user": os.environ["PGUSER"],
    "password": os.environ["PGPASSWORD"],
    "sslmode": "require",
}

# The outer context starts the pool and closes every pooled connection when the app shuts down.
with ConnectionPool(kwargs=connection_settings, min_size=1, max_size=10) as pool:
    # pool.connection returns a connection for this block and automatically returns it afterward.
    with pool.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            print(cursor.fetchone())
```

When you finish running the samples, remove the password from the shell and from child-process
environments:

```bash
unset PGPASSWORD
```

For a real long-running service, create one pool during application startup, share it, and close it
during shutdown. Do not create a new pool inside every request. Avoid long-lived password
environment variables in production: use Microsoft Entra authentication/managed identity where it
fits the workload, or retrieve an approved secret from Key Vault at startup.

## Exam gotchas

- Use `az postgres flexible-server`, not retired Single Server commands.
- Allowlist `vector` at server level, then run `CREATE EXTENSION vector` in every database that
  needs pgvector.
- A query vector must match the column dimension and embedding model.
- A `vector` column indexed by pgvector HNSW or IVFFlat is limited to 2,000 dimensions; merely being
  able to store a larger vector does not make it indexable by those access methods.
- `<->` pairs with `vector_l2_ops`; `<=>` pairs with `vector_cosine_ops`; `<#>` pairs with
  `vector_ip_ops`.
- Exact scan has perfect recall. HNSW and IVFFlat are approximate and require recall/latency tuning.
- HNSW uses `ef_construction` at build time and `hnsw.ef_search` at query time; `ef` is not a valid
  HNSW index option.
- Build IVFFlat after loading representative data. HNSW has no training step.
- DiskANN is a separate Azure `pg_diskann` extension, not a pgvector `ivfhnsw` index.
- Put common metadata filters in typed columns and index them. Always enforce tenant/access filters
  in retrieval queries.
- Size from measurements. Memory Optimized can help a large hot index, but it is not mandatory for
  every production vector workload.
- Burstable does not support built-in high availability. Availability SLAs depend on whether the
  server uses no HA, same-zone HA, or zone-redundant HA—not just on its compute tier.
- Direct PostgreSQL uses port `5432`; built-in PgBouncer uses `6432` and transaction pooling by
  default.
- Reuse a bounded pool, keep transactions short, and retry only transient failures with backoff.

## Cleanup

Delete only the dedicated practice resource group after checking its contents:

```bash
# This irreversible operation deletes the flexible server and every other resource in the group.
az group delete --name "$RG" --yes --no-wait
```

## Quiz yourself

Take the **postgresql-pgvector** quiz in the [quiz app](../../quiz/) (bank:
[`postgresql-pgvector.json`](../../quiz/src/questions/02-data-services/postgresql-pgvector.json)).

## Further reading

- [Azure Database for PostgreSQL flexible server overview](https://learn.microsoft.com/azure/postgresql/flexible-server/overview)
- [Create a flexible server](https://learn.microsoft.com/azure/postgresql/configure-maintain/quickstart-create-server)
- [Enable and use pgvector](https://learn.microsoft.com/azure/postgresql/extensions/how-to-use-pgvector)
- [Optimize pgvector performance](https://learn.microsoft.com/azure/postgresql/extensions/how-to-optimize-performance-pgvector)
- [Enable and use the Azure DiskANN extension](https://learn.microsoft.com/azure/postgresql/extensions/how-to-use-pgdiskann)
- [Allowlist PostgreSQL extensions](https://learn.microsoft.com/azure/postgresql/extensions/how-to-allow-extensions)
- [Compute options](https://learn.microsoft.com/azure/postgresql/compute-storage/concepts-compute)
- [Built-in PgBouncer](https://learn.microsoft.com/azure/postgresql/connectivity/concepts-pgbouncer)
- [Python connection quickstart](https://learn.microsoft.com/azure/postgresql/connectivity/connect-python)
- [pgvector project documentation](https://github.com/pgvector/pgvector)
