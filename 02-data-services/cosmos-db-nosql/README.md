# Azure Cosmos DB for NoSQL

**Domain:** 02 — Develop AI solutions by using Azure data management services (25–30%)
**Maps to skill:** *Connect to Cosmos DB for NoSQL by using the SDK and run queries* ·
*Optimize query performance and RU consumption by using indexing policies and consistency
levels* · *Store and retrieve embeddings and execute vector similarity search* · *Implement a
change feed processor*

---

## What it is

**Azure Cosmos DB for NoSQL** is a **fully managed, globally distributed, NoSQL database** service
that stores data as **JSON documents** in **containers**. It offers **single-digit millisecond
latency** at any scale, with **99.999% availability** (for multi-region configurations),
and **automatic scaling** of throughput and storage.

Think of it as a **document database** that can also function as a **vector database** for AI
workloads. Data is organized into **databases → containers → items (JSON documents)**, with
items grouped by a **partition key** that determines how data is distributed across partitions.

> Mental model:
>
> ```
>   Application
>        │
>        ▼
>   ┌─────────────────────────────────────────────────────────┐
>   │  Azure Cosmos DB for NoSQL Account                      │
>   │                                                           │
>   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
>   │  │  Database A  │  │  Database B  │  │  Database C  │   │
>   │  │              │  │              │  │              │   │
>   │  │  ┌─────────┐│  │  ┌─────────┐│  │  ┌─────────┐│   │
>   │  │  │Container││  │  │Container││  │  │Container││   │
>   │  │  │  (items) ││  │  │  (items) ││  │  │  (items) ││   │
>   │  │  └─────────┘│  │  └─────────┘│  │  └─────────┘│   │
>   │  └─────────────┘  └─────────────┘  └─────────────┘   │
>   └─────────────────────────────────────────────────────────┘
>        │
>        ▼
>   Partitioned by partition key → distributed across regions
> ```

**Key capabilities:**
- **Global distribution** — deploy to any Azure region, with multi-region writes
- **Elastic scaling** — scale throughput (RU/s) and storage independently
- **Multiple consistency models** — choose from 5 consistency levels
- **Vector search** — store embeddings and perform similarity search (preview)
- **Change feed** — listen for inserts, updates, and deletes in real-time
- **Indexing policies** — optimize query performance and RU consumption
- **Serverless or provisioned** — pay per request or reserve capacity
- **Multi-model** — NoSQL (document), MongoDB, Cassandra, Gremlin, Table APIs

---

## Why it's on the exam

The AI-200 exam tests these core competencies for Azure Cosmos DB for NoSQL:

- **SDK connectivity** — connecting and running CRUD + query operations
- **Query execution** — SQL syntax, parameterized queries, cross-partition queries
- **Partitioning strategy** — choosing partition keys, understanding physical vs logical partitions
- **Request Units (RUs)** — understanding throughput, provisioned vs serverless, cost optimization
- **Indexing policies** — included/excluded paths, composite indexes, spatial indexes
- **Consistency levels** — Strong, Bounded Staleness, Session, Consistent Prefix, Eventual
- **Vector search** — storing embeddings, creating vector indexes, similarity search
- **Change feed** — implementing processors, handling leases, checkpointing
- **Performance tuning** — query metrics, query execution stats, optimization techniques

Expect scenario questions like:
- "Which partition key should you use for even distribution?" → **High cardinality, evenly distributed property**
- "How do you reduce RU consumption for a query?" → **Add appropriate indexes, filter on partition key**
- "Which consistency level guarantees read-your-writes?" → **Session**
- "How do you implement real-time processing of data changes?" → **Change feed processor**

---

## Core concepts

### 1. Resource Hierarchy

| Level | Description | Example |
| --- | --- | --- |
| **Account** | Top-level resource, globally distributed | `my-cosmos-account` |
| **Database** | Container for containers | `products-db` |
| **Container** | Holds items (documents) and defines schema, indexing, partitioning | `products`, `orders` |
| **Item** | JSON document stored in a container | `{"id": "123", "name": "Laptop"}` |

> **Exam gotcha:** A container's partition key is **immutable** after creation. Choose carefully.

### 2. Partitioning

Data is **partitioned** based on the **partition key** you choose. The partition key:
- Determines how data is **distributed** across physical partitions
- Affects **query performance** (cross-partition queries cost more RUs)
- Should have **high cardinality** (many unique values)
- Should **distribute evenly** (avoid hot partitions)

**Partition key strategies:**
- **Good:** `/partitionKey` (auto-generated), `userId`, `regionCode` (if evenly distributed)
- **Bad:** `status` (low cardinality), `country` (if most users from one country)

```python
# When querying, always filter on partition key to avoid cross-partition queries
query = "SELECT * FROM c WHERE c.partitionKey = @partitionKey"
```

**Physical vs Logical Partitions:**
- **Logical Partition:** Defined by your partition key value (e.g., all items with `userId = "123"`)
- **Physical Partition:** Internal Cosmos DB storage unit that holds multiple logical partitions

> **Exam gotcha:** A single logical partition cannot exceed **20GB** of data. If a partition grows beyond this, you must migrate to a different partition key.

### 3. Request Units (RUs)

**Throughput is measured in Request Units (RUs) per second.**

| Operation | Typical RU Cost |
| --- | --- |
| Read 1KB item (by ID) | 1 RU |
| Write 1KB item | ~5 RUs |
| Delete 1KB item | ~1 RU |
| Query (per result page) | 2-10+ RUs (depends on complexity) |

**Capacity modes:**
- **Provisioned:** Reserve RU/s capacity (e.g., 400 RU/s, 1000 RU/s). Best for predictable workloads.
- **Serverless:** Pay per request (per operation + per hour storage). Best for sporadic, unpredictable workloads.

**Provisioned throughput can be allocated at:**
- **Database level** — shared across all containers in the database
- **Container level** — dedicated to a specific container

> **Exam gotcha:** A **cross-partition query** costs more RUs than a **point read** or **single-partition query**. Always include the partition key in your WHERE clause.

### 4. Consistency Levels

Cosmos DB offers **5 consistency levels**, trading off latency, availability, and read freshness:

| Level | Latency | Availability | Read Freshness | Use Case |
| --- | --- | --- | --- | --- |
| **Strong** | High | Lower | Full consistency | Financial transactions, critical reads |
| **Bounded Staleness** | Medium | High | Reads lag by at most K versions or T ms | Retail, inventory systems |
| **Session** | Low | High | Read-your-writes within session | User sessions, collaborative apps |
| **Consistent Prefix** | Low | High | No out-of-order writes | Streaming, messaging |
| **Eventual** | Lowest | Highest | No guarantee | Analytics, non-critical data |

**Configurable parameters for Bounded Staleness:**
- `MaxStalenessPrefix` — number of versions behind
- `MaxStalenessIntervalInSeconds` — time lag in seconds

> **Exam gotchas:**
> - **Session consistency** is the **default** for new accounts
> - **Strong consistency** requires **single region** (not available with multi-region writes)
> - **Eventual consistency** offers the **lowest latency** and **highest availability**
> - **Session consistency** guarantees **read-your-writes** within the same client session

### 5. Indexing Policies

Every container has an **indexing policy** that determines what gets indexed automatically.

**Indexing modes:**
- **Consistent** (default) — indexes are updated synchronously with writes
- **Lazy** — indexes are updated asynchronously (lower write latency, stale reads possible)
- **None** — no automatic indexing

**Index kinds:**
- **Range** — for numeric values, strings (equality, range, ORDER BY)
- **Hash** — for efficient equality lookups
- **Spatial** — for geospatial queries (POINTS, POLYGONS)

**Indexing policy example:**
```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    {"path": "/*"}
  ],
  "excludedPaths": [
    {"path": "/\"_ts\"/?"}
  ]
}
```

**Composite indexes** — improve performance for queries with multiple conditions:
```json
{
  "compositeIndexes": [
    [{"path": "/name", "order": "ascending"}, {"path": "/price", "order": "descending"}]
  ]
}
```

> **Exam gotcha:**
> - **Wildcard paths** (`/*`) index all fields (highest RU cost)
> - **Excluding fields** reduces RU consumption for writes
> - **Spatial indexes** are needed for geospatial queries (ST_DISTANCE, ST_WITHIN)
> - **Composite indexes** can dramatically improve query performance for specific query patterns

### 6. Vector Search (Preview)

Cosmos DB for NoSQL supports **vector similarity search** for AI workloads, allowing you to:
- Store **vector embeddings** alongside your JSON documents
- Create **vector indexes** for efficient similarity search
- Perform **k-nearest neighbor (KNN)** queries

**How it works:**
1. Store documents with vector embeddings (float arrays)
2. Create a vector index on the embedding field
3. Query with a vector to find similar documents

**Vector index types:**
- **Flat** — exact search, higher storage, faster for small datasets
- **IVF (Inverted File)** — approximate search, lower storage, faster for large datasets
- **HNSW (Hierarchical Navigable Small World)** — approximate, good balance of speed and accuracy

> **Exam gotcha:**
> - Vector search is in **preview** (as of 2024)
> - Requires **enabled vector indexing** on the container
> - Vector dimensions must be **between 2 and 2048**
> - **COSINE** distance for semantic similarity, **EUCLIDEAN** for geometric

### 7. Change Feed

The **change feed** is a **sorted, persisted log** of all changes (inserts, updates, deletes) to a container. It:
- Is **automatically enabled** for all containers
- Is **persisted** (stored for the lifetime of the container)
- Can be **processed incrementally** (checkpointing)
- Supports **parallel processing** (multiple consumers)

**Change feed processor patterns:**
- **Pull model** — client polls for new changes
- **Push model** — Cosmos DB pushes changes to a handler (via Azure Functions)

**Use cases:**
- Real-time data processing and analytics
- Materialized views and caches
- Event-driven architectures
- Data synchronization across systems

> **Exam gotcha:**
> - Change feed includes **all operations** (create, update, delete)
> - Each change includes **metadata** (operation type, timestamp, resource ID)
> - **Checkpointing** tracks which changes have been processed
> - **Lease management** coordinates parallel processors

### 8. Data Model

**Items (Documents):**
- Are **JSON documents** with a required `id` field
- Can be **any valid JSON** (nested objects, arrays, etc.)
- Have **system-generated** `_rid`, `_self`, `_ts` (timestamp), `_etag` (version) fields
- Maximum size: **2MB** per item

**Schema-flexible:** No fixed schema — each document can have different fields. But **indexing policy** determines what's queryable.

---

## Setup

> **Two methods available:**
> - **[CLI](#cli-setup)** — Copy-paste commands below (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal (Web UI)](#portal-setup)** — Point-and-click in your browser

### Set your variables

The CLI commands in **Setup** and **Cleanup** reference these as **shell variables** — set them once for your shell, then run the `az` commands as written.

| Variable | What it is |
| --- | --- |
| `RG` | Resource group |
| `LOCATION` | Azure region |
| `ACCOUNT_NAME` | Cosmos DB account name |
| `DATABASE_NAME` | Database name |
| `CONTAINER_NAME` | Container name |
| `PARTITION_KEY` | Partition key path (e.g., `/partitionKey`) |
| `RU` | Throughput in RU/s (e.g., 400) |

Copy the block that matches your shell:

```bash
# bash / zsh — Linux, and macOS (its default shell)
RG="ai200-rg"
LOCATION="westeurope"
ACCOUNT_NAME="ai200-cosmos"
DATABASE_NAME="products-db"
CONTAINER_NAME="products"
PARTITION_KEY="/partitionKey"
RU=400
```

```fish
# fish — Linux / macOS
set RG ai200-rg
set LOCATION westeurope
set ACCOUNT_NAME ai200-cosmos
set DATABASE_NAME products-db
set CONTAINER_NAME products
set PARTITION_KEY /partitionKey
set RU 400
```

```powershell
# PowerShell — Windows (also cross-platform)
$RG = "ai200-rg"
$LOCATION = "westeurope"
$ACCOUNT_NAME = "ai200-cosmos"
$DATABASE_NAME = "products-db"
$CONTAINER_NAME = "products"
$PARTITION_KEY = "/partitionKey"
$RU = 400
```

```bat
:: Command Prompt (cmd.exe) — Windows
set RG=ai200-rg
set LOCATION=westeurope
set ACCOUNT_NAME=ai200-cosmos
set DATABASE_NAME=products-db
set CONTAINER_NAME=products
set PARTITION_KEY=/partitionKey
set RU=400
```

### Prerequisites

1. **Azure CLI installed** and logged in (`az login`)
2. **Cosmos DB extension** (usually pre-installed, but if not: `az extension add --name cosmosdb`)

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first), after [setting your variables](#set-your-variables) above.

```bash
# 1. Create the resource group
az group create --name "$RG" --location "$LOCATION"

# 2. Create the Cosmos DB account
#    --enable-free-tier true for Free Tier (25GB free, 1000 RU/s free for 1 year)
#    --kind GlobalDocumentDB for multi-region support
#    --locations for additional regions (for global distribution)
#    --default-consistency-level for setting default consistency
az cosmosdb create \
  --name "$ACCOUNT_NAME" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --kind GlobalDocumentDB \
  --enable-free-tier true \
  --default-consistency-level Session \
  --enable-automatic-failover true

# 3. Create the database (with shared throughput)
#    --max-throughput for provisioned RU/s at database level
az cosmosdb sql database create \
  --name "$DATABASE_NAME" \
  --resource-group "$RG" \
  --account-name "$ACCOUNT_NAME" \
  --max-throughput "$RU"

# 4. Create the container with a partition key
#    --partition-key-path for the partition key
#    --indexing-policy for custom indexing (optional)
#    --unique-key-policy for unique constraints (optional)
#    --default-ttl for automatic expiration (optional, in seconds)
#    --throughput for dedicated container throughput (optional)
az cosmosdb sql container create \
  --name "$CONTAINER_NAME" \
  --resource-group "$RG" \
  --account-name "$ACCOUNT_NAME" \
  --database-name "$DATABASE_NAME" \
  --partition-key-path "$PARTITION_KEY"

# 5. Get the connection string and keys
#    Primary master key (for SDK connection)
PRIMARY_KEY=$(az cosmosdb list-keys \
  --name "$ACCOUNT_NAME" \
  --resource-group "$RG" \
  --query primaryMasterKey \
  --output tsv)

#    Connection string (for SDKs that use connection strings)
CONNECTION_STRING=$(az cosmosdb list-connection-strings \
  --name "$ACCOUNT_NAME" \
  --resource-group "$RG" \
  --query connectionStrings[0].connectionString \
  --output tsv)

#    Endpoint URI
ENDPOINT=$(az cosmosdb show \
  --name "$ACCOUNT_NAME" \
  --resource-group "$RG" \
  --query documentEndpoint \
  --output tsv)

echo "Cosmos DB account created!"
echo "Endpoint: $ENDPOINT"
echo "Primary key: $PRIMARY_KEY"
echo "Connection string: $CONNECTION_STRING"

# 6. Test connection with Azure CLI
#    Get account information
az cosmosdb show --name "$ACCOUNT_NAME" --resource-group "$RG"
```

The Cosmos DB account, database, and container are now ready. Next, you'll [test it](#hands-on-python).

### Enable Vector Indexing (Preview)

To enable vector search capabilities (when available):

```bash
# Note: Vector indexing configuration is typically done through the indexing policy
# when creating the container. See the indexing policy section for details.
```

### Portal Setup (Web UI)

Prefer the browser? Create the same resources in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Create Resource Group:**
   - Click **Resource groups** → **+ Create**
   - Name: `ai200-rg` (or your chosen name)
   - Region: `West Europe` (or your preference)
   - Click **Review + create** → **Create**

3. **Create Cosmos DB Account:**
   - Click **+ Create a resource** → Search for "Azure Cosmos DB" → **Create**
   - Subscription: your subscription
   - Resource group: `ai200-rg`
   - Account name: `ai200-cosmos` (must be globally unique, lowercase, no special chars except `-`)
   - Location: `West Europe`
   - Capacity mode: **Provisioned** (or Serverless for unpredictable workloads)
   - Account type: **Non-production** (or Production for real workloads)
   - API: **Core (SQL)**
   - Free Tier: **Apply Free Tier Discount** (for testing)
   - Multi-region writes: **Disable** (or Enable for global distribution)
   - Default consistency level: **Session**
   - Click **Review + create** → **Create**

4. **Get connection information:**
   - Navigate to your Cosmos DB account (`ai200-cosmos`)
   - On the **Overview** blade, note the **URI** (endpoint)
   - Under **Settings → Keys**, copy the **PRIMARY KEY**

5. **Create Database:**
   - In your Cosmos DB account, click **Data Explorer**
   - Click **New Database**
   - Database ID: `products-db`
   - Provision throughput: **Yes** (for provisioned mode)
   - Throughput: `400` RU/s
   - Click **OK**

6. **Create Container:**
   - In Data Explorer, expand your database (`products-db`)
   - Click **New Container**
   - Container ID: `products`
   - Partition key: `/partitionKey` (or your chosen partition key)
   - Throughput: **Use database level** (to share database throughput)
   - Indexing: **Automatic** (default)
   - Click **OK**

---

## Cleanup

Goal: delete all resources created during setup to avoid unnecessary Azure charges. Run this when you're done experimenting, or whenever you want to start fresh.

> **Two methods available:**
> - **[CLI](#cli-cleanup)** — Copy-paste commands below
> - **[Azure Portal (Web UI)](#portal-cleanup)** — Point-and-click in your browser

### CLI Cleanup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/). Set `RG` as shown in [Set your variables](#set-your-variables), then:

```bash
# Delete the entire resource group and everything in it.
# This removes: Cosmos DB account, database, containers, and any other resources in the group.
# The '--yes' flag skips the confirmation prompt. Use '--no-wait' to not wait for completion.
az group delete --name "$RG" --yes --no-wait

# Optional: verify the resource group is gone
az group list --output table
```

> **Important:** Deleting a resource group is **permanent and immediate**. All resources in that group (Cosmos DB account, etc.) will be deleted and cannot be recovered. Cosmos DB accounts can take 30-60 minutes to fully delete.

### Portal Cleanup (Web UI)

Prefer the browser? Delete resources in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Delete the Resource Group (recommended):**
   - Click **Resource groups** in the left menu
   - Find and click on your resource group (`ai200-rg` or your chosen name)
   - Click **Delete resource group** at the top
   - In the confirmation blade, type the resource group name to confirm
   - Click **Delete**

   This deletes **all resources** in the group in one operation.

---

## Hands-on (Python)

Let's use the **`azure-cosmos`** Python SDK to interact with Azure Cosmos DB for NoSQL. We'll demonstrate:
1. Connecting to Cosmos DB
2. Basic CRUD operations (Create, Read, Update, Delete)
3. Querying with SQL
4. Working with partitioning
5. Vector search (preview)
6. Change feed processing

> **Remember:** Run all commands below from this folder (`02-data-services/cosmos-db-nosql/`).

### Project Structure

```
cosmos-db-nosql/
├── cosmos_demo.py              # Main CRUD and query demonstration script
├── vector_demo.py              # Vector similarity search demo
├── change_feed_demo.py         # Change feed processor demo
└── requirements.txt            # Python dependencies
```

### Setup Python Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# --- bash/zsh (macOS/Linux) ---
source venv/bin/activate

# --- fish (macOS/Linux) ---
source venv/bin/activate.fish

# --- Windows PowerShell ---
.\venv\Scripts\Activate.ps1

# --- Windows cmd ---
venv\Scripts\activate.bat

# Install dependencies
pip install azure-cosmos==4.4.0
```

### 1. Basic CRUD Operations and Queries

**requirements.txt:**
```
azure-cosmos==4.4.0
```

**cosmos_demo.py:**

```python
"""
Azure Cosmos DB for NoSQL - Basic CRUD and Query Operations Demo

This script demonstrates:
- Connecting to Azure Cosmos DB
- Basic CRUD operations (Create, Read, Update, Delete)
- SQL queries with parameters
- Partition key usage
- Query metrics and optimization
"""

import os
import json
from azure.cosmos import CosmosClient, exceptions

# Configuration - set these from environment variables or replace with your values
ENDPOINT = os.environ.get("COSMOS_ENDPOINT", "https://your-cosmos-account.documents.azure.com:443/")
PRIMARY_KEY = os.environ.get("COSMOS_PRIMARY_KEY", "your-primary-key")
DATABASE_NAME = os.environ.get("COSMOS_DATABASE", "products-db")
CONTAINER_NAME = os.environ.get("COSMOS_CONTAINER", "products")

print("=" * 60)
print("1. CONNECTING TO COSMOS DB")
print("=" * 60)

# Create a CosmosClient
client = CosmosClient(ENDPOINT, credential=PRIMARY_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

print(f"Connected to: {ENDPOINT}")
print(f"Database: {DATABASE_NAME}, Container: {CONTAINER_NAME}")

try:
    account = client.get_database_account()
    print(f"Account: {account['name']} (ID: {account['_rid']})")
except exceptions.CosmosHttpResponseError as e:
    print(f"Connection failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("2. CREATE ITEMS (INSERT)")
print("=" * 60)

products = [
    {"id": "laptop-001", "name": "Gaming Laptop", "category": "Electronics",
     "price": 1299.99, "brand": "MSI", "partitionKey": "electronics"},
    {"id": "phone-001", "name": "Smartphone X", "category": "Electronics",
     "price": 799.99, "brand": "Samsung", "partitionKey": "electronics"},
    {"id": "shirt-001", "name": "Cotton T-Shirt", "category": "Clothing",
     "price": 19.99, "brand": "Generic", "partitionKey": "clothing"}
]

for product in products:
    item = container.upsert_item(product)
    print(f"  Inserted: {product['id']} (RU: {item['request_charge']})")

print("\n" + "=" * 60)
print("3. READ ITEMS")
print("=" * 60)

# Point read
item = container.read_item("laptop-001", partition_key="electronics")
print(f"  Point read: {item['name']} (${item['price']})")

print("\n" + "=" * 60)
print("4. QUERY ITEMS WITH SQL")
print("=" * 60)

# Query with partition key filter
query = "SELECT * FROM c WHERE c.partitionKey = @partitionKey"
params = [{"name": "@partitionKey", "value": "electronics"}]
items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=False))
print(f"  Electronics: {len(items)} items")
for it in items:
    print(f"    - {it['name']} (${it['price']})")

# Cross-partition query
query = "SELECT c.id, c.name FROM c"
items = list(container.query_items(query=query, enable_cross_partition_query=True))
print(f"\n  All products: {len(items)} items")

print("\n" + "=" * 60)
print("5. UPDATE ITEMS")
print("=" * 60)

# Full replacement
item = container.read_item("laptop-001", partition_key="electronics")
item['price'] = 1199.99
updated = container.upsert_item(item)
print(f"  Updated price to ${item['price']} (RU: {updated['request_charge']})")

# PATCH for partial update
patch_ops = [{"op": "set", "path": "/rating", "value": 4.8}]
patched = container.patch_item("laptop-001", partition_key="electronics", patch_operations=patch_ops)
print(f"  Patched rating (RU: {patched['request_charge']})")

print("\n" + "=" * 60)
print("6. DELETE ITEMS")
print("=" * 60)

container.delete_item("shirt-001", partition_key="clothing")
print("  Deleted: shirt-001")

print("\n" + "=" * 60)
print("7. BULK OPERATIONS")
print("=" * 60)

operations = [
    {"operation": "Create", "resourceBody": {"id": "monitor-001", "name": "4K Monitor",
     "category": "Electronics", "price": 399.99, "partitionKey": "electronics"}}
]
results = container.execute_item_batch(operations, partition_key="electronics")
print(f"  Batch created {len(results)} item(s)")

print("\n" + "=" * 60)
print("Demo complete!")
print("=" * 60)
```

### 2. Vector Similarity Search (Preview)

**vector_demo.py:**

```python
"""
Azure Cosmos DB for NoSQL - Vector Similarity Search Demo
Note: Vector indexing is in preview. Check Microsoft docs for current status.
"""

import os
from azure.cosmos import CosmosClient

ENDPOINT = os.environ.get("COSMOS_ENDPOINT", "https://your-cosmos-account.documents.azure.com:443/")
PRIMARY_KEY = os.environ.get("COSMOS_PRIMARY_KEY", "your-primary-key")
DATABASE_NAME = os.environ.get("COSMOS_DATABASE", "products-db")
CONTAINER_NAME = os.environ.get("COSMOS_CONTAINER", "products-vectors")

print("=" * 60)
print("VECTOR SEARCH DEMO")
print("=" * 60)

client = CosmosClient(ENDPOINT, credential=PRIMARY_KEY)
database = client.get_database_client(DATABASE_NAME)

# Products with embeddings (simplified 5-dim for demo)
products_with_vectors = [
    {"id": "laptop-001", "name": "Gaming Laptop", "partitionKey": "electronics",
     "embedding": [0.8, 0.2, 0.1, 0.05, 0.05]},
    {"id": "phone-001", "name": "Smartphone X", "partitionKey": "electronics",
     "embedding": [0.7, 0.3, 0.2, 0.1, 0.05]},
    {"id": "mouse-001", "name": "Wireless Mouse", "partitionKey": "electronics",
     "embedding": [0.3, 0.6, 0.5, 0.2, 0.1]}
]

print("\nStoring products with vector embeddings...")
for p in products_with_vectors:
    container = database.get_container_client(CONTAINER_NAME)
    try:
        container.upsert_item(p)
        print(f"  Stored: {p['name']}")
    except Exception as e:
        print(f"  Note: Container may need vector indexing policy. Error: {e}")
        break

print("\nVector search requires vector indexing policy on container.")
print("See README for indexing policy configuration with vectorIndexes.")
print("\nDemo complete!")
```

### 3. Change Feed Processor

**change_feed_demo.py:**

```python
"""
Azure Cosmos DB for NoSQL - Change Feed Demo
"""

import os
from datetime import datetime, timedelta
from azure.cosmos import CosmosClient

ENDPOINT = os.environ.get("COSMOS_ENDPOINT")
PRIMARY_KEY = os.environ.get("COSMOS_PRIMARY_KEY")
DATABASE_NAME = os.environ.get("COSMOS_DATABASE")
CONTAINER_NAME = os.environ.get("COSMOS_CONTAINER")

print("=" * 60)
print("CHANGE FEED DEMO")
print("=" * 60)

client = CosmosClient(ENDPOINT, credential=PRIMARY_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Get changes from last 5 minutes
five_min_ago = datetime.utcnow() - timedelta(minutes=5)

print("\nReading change feed from last 5 minutes...")
change_feed = container.query_change_feed(
    start_time=five_min_ago,
    max_item_count=10
)

count = 0
for change in change_feed:
    count += 1
    op = change.get('operation')
    item = change.get('resource', {})
    print(f"  {op}: {item.get('id')} at {change.get('_ts')}")
    if count >= 5:
        break

if count == 0:
    print("  No changes found in last 5 minutes.")

print("\nChange feed is persisted and can be read from any point in time.")
print("Use ChangeFeedProcessor for production scenarios with checkpointing.")
print("\nDemo complete!")
```

### Run the Demos

```bash
# Set environment variables
export COSMOS_ENDPOINT="https://your-cosmos-account.documents.azure.com:443/"
export COSMOS_PRIMARY_KEY="your-primary-key"
export COSMOS_DATABASE="products-db"
export COSMOS_CONTAINER="products"

python cosmos_demo.py
python vector_demo.py
python change_feed_demo.py
```

---

## Exam gotchas

- **Partition key is immutable** — cannot be changed after container creation
- **Cross-partition queries cost more** — always filter on partition key when possible
- **Default consistency is Session** — not Strong. Strong requires single region
- **Eventual consistency has no guarantees** — lowest latency, highest availability
- **Item size limit is 2MB** — per document
- **Logical partition limit is 20GB** — per partition key value
- **RU/s is provisioned per second** — exceeding causes rate limiting (HTTP 429)
- **Indexing is automatic by default** — exclude unnecessary paths to reduce write RU costs
- **Change feed is enabled by default** — persisted, sorted by _ts, includes all operations
- **Vector search requires indexing** — vector fields must have vector index, dimensions must match
- **COSINE for semantic, EUCLIDEAN for geometric** — similarity distance metrics
- **Point reads cost 1 RU** — for 1KB item by ID + partition key
- **Avoid SELECT *** — specify only needed fields
- **ORDER BY without filter is expensive** — can scan entire container
- **TTL auto-deletes items** — set defaultTtl on container for expiration
- **Bulk operations limited to same partition** — transactional batch requires same logical partition

---

## Quiz yourself

Take the **cosmos-db-nosql** quiz in the [quiz app](../../quiz/) 
(bank: [`quiz/src/questions/02-data-services/cosmos-db-nosql.json`](../../quiz/src/questions/02-data-services/cosmos-db-nosql.json)).

---

## Further reading

- Azure Cosmos DB for NoSQL documentation: <https://learn.microsoft.com/azure/cosmos-db/nosql/>
- Cosmos DB Python SDK: <https://learn.microsoft.com/python/api/azure-cosmos/>
- SQL query reference: <https://learn.microsoft.com/azure/cosmos-db/nosql/query/sql-query>
- Partitioning: <https://learn.microsoft.com/azure/cosmos-db/nosql/partitioning-overview>
- Request Units: <https://learn.microsoft.com/azure/cosmos-db/nosql/request-units>
- Consistency levels: <https://learn.microsoft.com/azure/cosmos-db/nosql/consistency-levels>
- Indexing: <https://learn.microsoft.com/azure/cosmos-db/nosql/index-policy>
- Change feed: <https://learn.microsoft.com/azure/cosmos-db/nosql/change-feed-overview>
- Vector search (preview): <https://learn.microsoft.com/azure/cosmos-db/nosql/how-to-vector-search>
- Pricing: <https://azure.microsoft.com/pricing/details/cosmos-db/>
- Performance tips: <https://learn.microsoft.com/azure/cosmos-db/nosql/performance-tips>
