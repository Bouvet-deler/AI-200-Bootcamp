# Azure Managed Redis (Azure Cache for Redis)

**Domain:** 02 — Develop AI solutions by using Azure data management services (25–30%)
**Maps to skill:** *Implement Azure Managed Redis data operations, including caching,
expiration, and invalidation* · *Implement vector indexing to enable similarity search*

---

## What it is

**Azure Cache for Redis** (often called Azure Managed Redis) is a **fully managed, in-memory data store**
based on the popular open-source **Redis**. It provides **microsecond-latency** access to data, making
it ideal for **caching** expensive or frequently accessed data.

Think of it as a **high-speed key/value database** that sits between your application and slower data
sources (like databases). When your app needs data, it first checks the cache — if found (a "cache hit"),
it returns instantly. If not (a "cache miss"), it fetches from the slower source, stores it in the cache,
and returns it.

> Mental model:
>
> ```
>   User Request
>        │
>        ▼
>   ┌─────────────────┐
>   │  Application     │ ◄────────────┐
>   └────────┬────────┘              │
>             │                        │
>             ▼                        │
>   ┌─────────────────┐              │
>   │  Azure Redis     │              │
>   │  (Cache)         │              │
>   └────────┬────────┘              │
>             │                        │
>             ▼                        │
>   ┌─────────────────┐              │
>   │  Primary Data    │ ◄─────────────┘
>   │  Store (DB, API)  │   (on cache miss)
>   └─────────────────┘
> ```

**Key capabilities:**
- **Caching** — store frequently accessed data for fast retrieval
- **Expiration (TTL)** — automatically remove data after a set time
- **Invalidation** — manually remove stale or changed data
- **Vector indexing** — store and search vector embeddings for similarity search (AI/ML)
- **Persistence** — optionally save data to disk for durability
- **High availability** — replicate data across multiple nodes

---

## Why it's on the exam

The AI-200 exam tests these core competencies for Azure Managed Redis:

- **Caching patterns** — read-through, write-through, cache-aside
- **Data operations** — get, set, delete, increment, expiration (TTL)
- **Cache invalidation** — when and how to remove stale data
- **Vector indexing** — storing embeddings and performing similarity searches
- **Redis data types** — strings, hashes, lists, sets, sorted sets, vectors
- **Performance tuning** — choosing the right tier, memory allocation

Expect scenario questions like:
- "How do you ensure cached data doesn't become stale?" → **TTL + invalidation**
- "Which data type is best for storing embeddings?" → **Vectors (RediSearch module)**
- "What's the difference between cache-aside and read-through?" → **Who writes to cache**

---

## Core concepts

### 1. Redis Data Types

Redis is a **key/value store**, but the values can be different data types:

| Data Type | Description | Use Cases |
| --- | --- | --- |
| **String** | Simple key-value pairs | Caching JSON, text, numbers |
| **Hash** | Field-value maps (like a dictionary) | Storing objects with multiple fields |
| **List** | Ordered collection of strings | Message queues, activity feeds |
| **Set** | Unordered collection of unique strings | Tracking unique visitors, tags |
| **Sorted Set** | Ordered collection with scores | Leaderboards, rate limiting |
| **JSON** | Native JSON support | Storing complex objects |
| **Vector** | Vector embeddings for AI | Similarity search, semantic search |

> **Exam gotcha:** For AI/ML scenarios with embeddings, use the **Vector** data type (requires
> the RediSearch module). This is a key exam topic.

### 2. Caching Patterns

| Pattern | How it works | When to use |
| --- | --- | --- |
| **Cache-Aside (Lazy Loading)** | App checks cache → miss → fetches from DB → writes to cache → returns | Most common; app controls cache |
| **Read-Through** | Cache sits between app and DB → cache checks DB automatically on miss | When you want cache to manage data loading |
| **Write-Through** | App writes to both cache and DB simultaneously | Critical data that must be consistent |
| **Write-Behind** | App writes to cache → cache writes to DB later | High-write scenarios; risk of data loss |

**Cache-Aside in code:**
```python
# Pseudocode for cache-aside
def get_data(key):
    data = cache.get(key)
    if data is None:  # cache miss
        data = database.query(key)
        cache.set(key, data, ttl=3600)  # cache for 1 hour
    return data
```

### 3. Expiration (TTL - Time To Live)

Every Redis key can have a **TTL** — a countdown timer after which the key is automatically deleted.

```python
# Set a key with 60-second expiration
cache.set("user:123", "data", px=60000)  # px = milliseconds

# Or with EX (seconds)
cache.set("user:123", "data", ex=60)  # ex = seconds

# Check remaining TTL
ttl = cache.ttl("user:123")  # Returns seconds until expiration, or -1 if no TTL
```

> **Exam gotcha:** TTL is **not** automatically refreshed on access. Once set, the countdown
> continues regardless of how many times the key is read.

### 4. Cache Invalidation

When data changes in the primary store, you need to **invalidate** (remove or update) the cached copy.

**Strategies:**
- **Time-based** — rely on TTL to expire old data
- **Event-based** — invalidate when source data changes
- **Write-through** — update cache and DB together

```python
# Invalidate on update
def update_user(user_id, new_data):
    database.update(user_id, new_data)
    cache.delete(f"user:{user_id}")  # Remove from cache
    # Or update in cache:
    cache.set(f"user:{user_id}", new_data, px=3600000)
```

> **Exam gotcha:** Stale cache data is a common problem. Always implement invalidation
> for data that can change.

### 5. Vector Indexing for AI

Azure Cache for Redis supports **vector similarity search** through the **RediSearch module**.
This is critical for AI/ML applications working with embeddings.

**How it works:**
1. Store vector embeddings (arrays of floats) in Redis
2. Create a vector index with dimensions matching your embeddings
3. Query the index with a vector to find similar items

```python
# Store a vector embedding (e.g., 1536-dimensional from text-embedding-ada-002)
vector = [0.1, 0.5, ..., 0.3]  # 1536 floats
cache.execute_command("FT.VECTORADD", "idx:products", "product:123", vector)

# Search for similar vectors (k=5 nearest neighbors)
results = cache.execute_command(
    "FT.VECTORSEARCH", "idx:products", "*", vector, "KNN", 5
)
```

**Vector index creation:**
```bash
# via redis-cli
FT.CREATE idx:products ON JSON PREFIX 1 "product:" SCHEMA vector VECTOR FLAT 6 
  DIM 1536 DISTANCE_METRIC COSINE
```

> **Exam gotcha:** For vector search, you need:
> - The **RediSearch module** enabled
> - A **vector index** created with the correct dimensions
> - **COSINE** distance for semantic similarity, **EUCLIDEAN** or **L2** for geometric

### 6. Tiers and Performance

| Tier | Use Case | Features |
| --- | --- | --- |
| **Basic** | Development/testing | Single node, no SLA |
| **Standard** | Production | 2-12 nodes, 99.9% SLA |
| **Premium** | Enterprise | Up to 120 nodes, 99.95% SLA, VNet, persistence |
| **Enterprise** | Large scale | Multi-region replication, active geo-replication |

** Choosing a tier:**
- **Development/testing** → Basic
- **Production with HA** → Standard (2+ nodes)
- **Enterprise with isolation** → Premium
- **Global scale** → Enterprise

> **Exam gotcha:** The **Basic** tier has **no SLA**. Always use Standard or higher for production.

### 7. Pricing Model

You pay for:
- **Memory** — GB/month (the main cost driver)
- **Throughput** — operations per second
- **Bandwidth** — data transfer in/out
- **Replication** — additional cost for HA nodes

> **Cost optimization:** Use appropriate TTLs to avoid storing unnecessary data. Monitor
> memory usage and scale as needed.

---

## Setup

> **Two methods available:**
> - **[CLI](#cli-setup)** — Copy-paste commands below (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal (Web UI)](#portal-setup)** — Point-and-click in your browser

### Set your variables

The CLI commands in **Setup** and **Cleanup** reference these as **shell variables** — set them once
for your shell, then run the `az` commands as written.

| Variable | What it is |
| --- | --- |
| `RG` | Resource group |
| `LOCATION` | Azure region |
| `REDIS_NAME` | Redis cache name |
| `SKU` | Pricing tier (Basic, Standard, Premium) |
| `SIZE` | Cache size in GB (e.g., C0=256MB, C1=1GB, C2=2.5GB, C3=6GB, C4=13GB, C5=50GB) |
| `FAMILY` | Cache family (C=Basic/Standard, P=Premium) |
| `ENABLE_NON_SSL` | Allow non-SSL connections (false recommended) |

Copy the block that matches your shell:

```bash
# bash / zsh — Linux, and macOS (its default shell)
RG="ai200-rg"
LOCATION="westeurope"
REDIS_NAME="ai200-redis"
SKU="Standard"
SIZE="C1"  # 1GB
FAMILY="C"
ENABLE_NON_SSL="false"
```

```fish
# fish — Linux / macOS
set RG ai200-rg
set LOCATION westeurope
set REDIS_NAME ai200-redis
set SKU Standard
set SIZE C1
set FAMILY C
set ENABLE_NON_SSL false
```

```powershell
# PowerShell — Windows (also cross-platform)
$RG = "ai200-rg"
$LOCATION = "westeurope"
$REDIS_NAME = "ai200-redis"
$SKU = "Standard"
$SIZE = "C1"
$FAMILY = "C"
$ENABLE_NON_SSL = "false"
```

```bat
:: Command Prompt (cmd.exe) — Windows
set RG=ai200-rg
set LOCATION=westeurope
set REDIS_NAME=ai200-redis
set SKU=Standard
set SIZE=C1
set FAMILY=C
set ENABLE_NON_SSL=false
```

### Prerequisites

1. **Azure CLI installed** and logged in (`az login`)

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first), after
[setting your variables](#set-your-variables) above.

```bash
# 1. Create the resource group
az group create --name "$RG" --location "$LOCATION"

# 2. Create the Redis cache
#    For Basic/Standard: --family C --sku-name $SKU --vm-size $SIZE
#    For Premium: --family P --sku-name Premium --vm-size P1 (6GB minimum)
az redis create \
  --name "$REDIS_NAME" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --family "$FAMILY" \
  --sku "$SKU" \
  --vm-size "$SIZE" \
  --enable-non-ssl-port "$ENABLE_NON_SSL"

# 3. Enable the RediSearch module (required for vector indexing)
#    This is only available on Premium tier with clustering enabled
#    For Basic/Standard, use a separate Redis Stack instance
az redis update \
  --name "$REDIS_NAME" \
  --resource-group "$RG" \
  --enable-redis-search true

# 4. Get the connection string (host, port, primary key)
HOST=$(az redis show \
  --name "$REDIS_NAME" \
  --resource-group "$RG" \
  --query hostName \
  --output tsv)

PRIMARY_KEY=$(az redis list-keys \
  --name "$REDIS_NAME" \
  --resource-group "$RG" \
  --query primaryKey \
  --output tsv)

echo "Redis host: $HOST"
echo "Redis port: 6380 (TLS) or 6379 (non-TLS)"
echo "Primary key: $PRIMARY_KEY"

# 5. Test connection with redis-cli
#    Install redis-cli: apt-get install redis-tools (Linux) or brew install redis (macOS)
#    Then connect: redis-cli -h $HOST -p 6380 -a $PRIMARY_KEY --tls
```

The Redis cache is now ready. Next, you'll [test it](#hands-on-python).

### Portal Setup (Web UI)

Prefer the browser? Create the same resources in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Create Resource Group:**
   - Click **Resource groups** → **+ Create**
   - Name: `ai200-rg` (or your chosen name)
   - Region: `West Europe` (or your preference)
   - Click **Review + create** → **Create**

3. **Create Redis Cache:**
   - Click **+ Create a resource** → Search for "Azure Cache for Redis" → **Create**
   - Subscription: your subscription
   - Resource group: `ai200-rg`
   - Cache name: `ai200-redis`
   - Region: `West Europe`
   - Pricing tier: **Standard** (for production) or **Basic** (for testing)
   - Cache size: **C1 (1 GB)**
   - For vector indexing: Check **Enable Redis modules** and select **RediSearch**
   - Click **Review + create** → **Create**

4. **Get connection information:**
   - Navigate to your Redis cache (`ai200-redis`)
   - On the **Overview** blade, note the **Hostname** and **SSL Port** (6380)
   - Under **Settings → Access keys**, copy the **Primary access key**

5. **Configure firewall (if needed):**
   - Under **Settings → Networking**, add your client IP address to the firewall rules
   - Or select **Public network access** → **Enabled** and **All networks** (for testing only)

---

## Cleanup

Goal: delete all resources created during setup to avoid unnecessary Azure charges.
Run this when you're done experimenting, or whenever you want to start fresh.

> **Two methods available:**
> - **[CLI](#cli-cleanup)** — Copy-paste commands below
> - **[Azure Portal (Web UI)](#portal-cleanup)** — Point-and-click in your browser

### CLI Cleanup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/). Set `RG` as shown in
[Set your variables](#set-your-variables), then:

```bash
# Delete the entire resource group and everything in it.
# This removes: Redis cache and any other resources in the group.
# The '--yes' flag skips the confirmation prompt. Use '--no-wait' to not wait for completion.
az group delete --name "$RG" --yes --no-wait

# Optional: verify the resource group is gone
az group list --output table
```

> **Important:** Deleting a resource group is **permanent and immediate**. All resources in that
group (Redis cache, etc.) will be deleted and cannot be recovered.

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

Let's use the **`redis-py`** library to interact with Azure Cache for Redis. We'll demonstrate:
1. Basic cache operations (get, set, delete)
2. TTL expiration
3. Hash operations
4. Vector similarity search (if RediSearch module is enabled)

> **Remember:** Run all commands below from this folder (`02-data-services/azure-managed-redis/`).

### Project Structure

```
ai200-redis/
├── redis_demo.py              # Main demonstration script
├── vector_demo.py             # Vector similarity search demo
└── requirements.txt           # Python dependencies
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
pip install redis==5.0.0 numpy==1.26.0
```

### 1. Basic Cache Operations

**requirements.txt:**
```
redis==5.0.0
numpy==1.26.0
```

**redis_demo.py:**

```python
"""
Azure Cache for Redis - Basic Operations Demo

This script demonstrates:
- Connecting to Azure Managed Redis
- Basic GET/SET/DELETE operations
- TTL (expiration)
- Hash operations
- List operations
- Increment operations
"""

import os
import redis
import time
import json

# Configuration - set these from environment variables or replace with your values
REDIS_HOST = os.environ.get("REDIS_HOST", "your-redis-host.azurecache.windows.net")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6380))  # 6380 for TLS, 6379 for non-TLS
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "your-primary-key")
REDIS_TLS = os.environ.get("REDIS_TLS", "true").lower() == "true"

# Connect to Redis
# For Azure Managed Redis, SSL/TLS is required for the default port (6380)
if REDIS_TLS:
    connection_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        ssl=True,
        ssl_cert_reqs=None,  # Azure uses self-signed certs
    )
else:
    connection_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
    )

r = redis.Redis(connection_pool=connection_pool)

# Test the connection
try:
    pong = r.ping()
    print(f"✓ Connected to Redis! PING returned: {pong}")
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print("\nTroubleshooting:")
    print(f"  Host: {REDIS_HOST}")
    print(f"  Port: {REDIS_PORT}")
    print(f"  TLS: {REDIS_TLS}")
    exit(1)

# ============================================================================
# 1. Basic String Operations
# ============================================================================
print("\n" + "=" * 60)
print("1. BASIC STRING OPERATIONS")
print("=" * 60)

# Set a key-value pair
r.set("greeting", "Hello, Azure Redis!")
print(f"SET greeting = 'Hello, Azure Redis!'")

# Get the value
value = r.get("greeting")
print(f"GET greeting = {value.decode('utf-8')}")

# Set with expiration (10 seconds)
r.setex("temp_greeting", 10, "This will expire in 10 seconds")
print(f"SETEX temp_greeting (10s TTL) = 'This will expire in 10 seconds'")

# Check TTL
ttl = r.ttl("temp_greeting")
print(f"TTL for temp_greeting: {ttl} seconds")

# Wait and check if it expires
time.sleep(11)
value = r.get("temp_greeting")
print(f"After 11 seconds, GET temp_greeting = {value}")  # Should be None

# ============================================================================
# 2. Hash Operations (for storing objects)
# ============================================================================
print("\n" + "=" * 60)
print("2. HASH OPERATIONS")
print("=" * 60)

# Store a user object as a hash
user = {
    "name": "Alice",
    "email": "alice@example.com",
    "age": "30",
    "city": "Seattle"
}

# Set hash fields
for field, value in user.items():
    r.hset("user:123", field, value)
print("HSET user:123 with fields: name, email, age, city")

# Get all fields
user_data = r.hgetall("user:123")
print(f"HGETALL user:123 = {user_data}")

# Get a specific field
name = r.hget("user:123", "name")
print(f"HGET user:123 name = {name.decode('utf-8')}")

# Increment a numeric field
r.hincrby("user:123", "age", 1)
age = r.hget("user:123", "age")
print(f"HINCRBY user:123 age +1 = {age.decode('utf-8')}")

# ============================================================================
# 3. List Operations (FIFO queue)
# ============================================================================
print("\n" + "=" * 60)
print("3. LIST OPERATIONS")
print("=" * 60)

# Push items to a list (LPUSH = left push, RPUSH = right push)
r.lpush("tasks", "Task 3")
r.lpush("tasks", "Task 2")
r.lpush("tasks", "Task 1")
print("LPUSH tasks: Task 3, Task 2, Task 1")

# Get list length
length = r.llen("tasks")
print(f"LLEN tasks = {length}")

# Pop items (LPOP = left pop, RPOP = right pop)
task1 = r.lpop("tasks")
task2 = r.lpop("tasks")
task3 = r.lpop("tasks")
print(f"LPOP tasks = {task1.decode('utf-8')}, {task2.decode('utf-8')}, {task3.decode('utf-8')}")

# ============================================================================
# 4. Set Operations (unique values)
# ============================================================================
print("\n" + "=" * 60)
print("4. SET OPERATIONS")
print("=" * 60)

# Add unique values to a set
r.sadd("users:online", "alice", "bob", "carol")
print("SADD users:online: alice, bob, carol")

# Check if a value exists
is_online = r.sismember("users:online", "bob")
print(f"SISMEMBER users:online bob = {is_online}")

# Get all members
members = r.smembers("users:online")
print(f"SMEMBERS users:online = {sorted([m.decode('utf-8') for m in members])}")

# Add a duplicate (will be ignored)
r.sadd("users:online", "alice")
members = r.smembers("users:online")
print(f"After adding duplicate alice: {sorted([m.decode('utf-8') for m in members])}")

# ============================================================================
# 5. Counter Operations
# ============================================================================
print("\n" + "=" * 60)
print("5. COUNTER OPERATIONS")
print("=" * 60)

# Increment a counter
r.set("page:views", 0)
r.incr("page:views")  # +1
r.incr("page:views")  # +1
r.incrby("page:views", 10)  # +10
views = r.get("page:views")
print(f"INCR/INCRBY page:views = {views.decode('utf-8')}")

# Decrement
r.decr("page:views")  # -1
r.decrby("page:views", 5)  # -5
views = r.get("page:views")
print(f"DECR/DECRBY page:views = {views.decode('utf-8')}")

# ============================================================================
# 6. Expiration and Invalidation
# ============================================================================
print("\n" + "=" * 60)
print("6. EXPIRATION AND INVALIDATION")
print("=" * 60)

# Set a key with TTL
r.set("session:abc123", "user_data", ex=30)  # Expires in 30 seconds
print("SET session:abc123 with TTL=30 seconds")

# Check remaining TTL
ttl = r.ttl("session:abc123")
print(f"TTL for session:abc123: {ttl} seconds")

# Manually delete (invalidate)
r.delete("session:abc123")
value = r.get("session:abc123")
print(f"After DELETE, GET session:abc123 = {value}")

# ============================================================================
# 7. Cache Statistics
# ============================================================================
print("\n" + "=" * 60)
print("7. CACHE STATISTICS")
print("=" * 60)

# Get info about the Redis server
info = r.info()
print(f"Redis version: {info.get('redis_version')}")
print(f"Connected clients: {info.get('connected_clients')}")
print(f"Used memory: {info.get('used_memory_human')}")

# Count keys
key_count = len(r.keys("*"))
print(f"Total keys in cache: {key_count}")

print("\n" + "=" * 60)
print("Demo complete!")
print("=" * 60)
```

### 2. Vector Similarity Search (RediSearch Module)

**vector_demo.py:**

```python
"""
Azure Cache for Redis - Vector Similarity Search Demo

This script demonstrates:
- Creating a vector index
- Storing vector embeddings
- Performing similarity search (KNN)
- Using cosine similarity for semantic search

Requires: RediSearch module enabled on Premium tier
"""

import os
import redis
import numpy as np

# Configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "your-redis-host.azurecache.windows.net")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6380))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "your-primary-key")

# Connect to Redis with SSL
connection_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    ssl=True,
    ssl_cert_reqs=None,
)
r = redis.Redis(connection_pool=connection_pool)

# Check if RediSearch module is available
try:
    module_list = r.execute_command("MODULE LIST")
    print("Redis modules:", module_list)
    has_redisearch = any(b"RediSearch" in str(m) for m in module_list)
    if not has_redisearch:
        print("ERROR: RediSearch module is not enabled!")
        print("For vector indexing, you need:")
        print("  - Premium tier")
        print("  - RediSearch module enabled")
        print("  - Or use Redis Stack (separate instance)")
        exit(1)
except Exception as e:
    print(f"Error checking modules: {e}")
    exit(1)

# ============================================================================
# Vector Similarity Search Demo
# ============================================================================
print("\n" + "=" * 60)
print("VECTOR SIMILARITY SEARCH DEMO")
print("=" * 60)

# Sample product embeddings (3-dimensional for demo, real embeddings are 1536+ dim)
# In production, use embeddings from models like text-embedding-ada-002 (1536 dim)
embeddings = {
    "laptop": [0.8, 0.2, 0.1],
    "phone": [0.7, 0.3, 0.2],
    "tablet": [0.75, 0.25, 0.15],
    "monitor": [0.9, 0.1, 0.05],
    "mouse": [0.3, 0.6, 0.5],
}

# Create a vector index
# FT.CREATE <index_name> ON JSON PREFIX 1 "product:" SCHEMA vector VECTOR FLAT 6 DIM 3 DISTANCE_METRIC COSINE
# - FLAT: Index type (exact search)
# - 6: Number of initial vectors (can grow)
# - DIM 3: Dimension of vectors
# - COSINE: Distance metric for similarity
print("\nCreating vector index...")
index_name = "idx:products"
try:
    # Delete index if it already exists
    r.execute_command("FT.DROPINDEX", index_name, "DD")
except:
    pass

# Create the index
result = r.execute_command(
    "FT.CREATE", index_name,
    "ON", "JSON",  # Store vectors in JSON documents
    "PREFIX", "1", "product:",  # Keys with prefix "product:"
    "SCHEMA",
    "vector", "VECTOR", "FLAT", "10",  # FLAT index, initial 10 vectors
    "DIM", "3",  # 3 dimensions (use 1536 for real embeddings)
    "DISTANCE_METRIC", "COSINE"  # Cosine similarity for semantic search
)
print(f"Index created: {result}")

# Store vectors as JSON documents with vector fields
print("\nStoring product vectors...")
for product_id, vector in embeddings.items():
    # Store as JSON with a vector field
    # Format: product:<id> with fields: name, vector
    doc = {
        "name": product_id,
        "vector": vector
    }
    # Use JSON.SET to store the document
    r.execute_command("JSON.SET", f"product:{product_id}", "$", json.dumps(doc))
    print(f"  Stored: product:{product_id}")

# Verify documents
print("\nVerifying stored documents:")
for product_id in embeddings.keys():
    doc = r.execute_command("JSON.GET", f"product:{product_id}")
    print(f"  product:{product_id}: {doc}")

# Perform a similarity search
print("\n" + "=" * 60)
print("SIMILARITY SEARCH")
print("=" * 60)

# Query vector (similar to "laptop")
query_vector = [0.78, 0.22, 0.12]

# Search for top 3 similar products
# FT.VECTORSEARCH <index> <query> <vector> KNN <k> DIALECT 2
results = r.execute_command(
    "FT.VECTORSEARCH",
    index_name,
    "*",  # Search all documents in index
    query_vector,
    "KNN", "3",  # Top 3 results
    "DIALECT", "2",  # Use dialect 2 for vector search
    "RETURN", "2", "name", "vector"  # Return name and vector
)

print(f"\nQuery vector: {query_vector}")
print(f"\nTop 3 similar products:")
for i, item in enumerate(results[1:]):  # Skip the first item (count)
    if isinstance(item, list):
        name = item[1][1].decode('utf-8') if len(item) > 1 else "unknown"
        score = item[0]  # Similarity score (lower = more similar for COSINE)
        print(f"  {i+1}. {name} (score: {score:.4f})")

# Test with different query (similar to "mouse")
print("\n" + "-" * 60)
query_vector = [0.32, 0.58, 0.48]
results = r.execute_command(
    "FT.VECTORSEARCH",
    index_name,
    "*",
    query_vector,
    "KNN", "3",
    "DIALECT", "2",
    "RETURN", "2", "name", "vector"
)

print(f"\nQuery vector: {query_vector}")
print(f"\nTop 3 similar products:")
for i, item in enumerate(results[1:]):
    if isinstance(item, list):
        name = item[1][1].decode('utf-8') if len(item) > 1 else "unknown"
        score = item[0]
        print(f"  {i+1}. {name} (score: {score:.4f})")

print("\n" + "=" * 60)
print("Vector search demo complete!")
print("=" * 60)
```

### Run the Demos

```bash
# Set environment variables with your Redis connection info
export REDIS_HOST="your-redis-host.azurecache.windows.net"
export REDIS_PORT=6380
export REDIS_PASSWORD="your-primary-key"
export REDIS_TLS=true

# Run basic cache operations demo
python redis_demo.py

# Run vector search demo (requires RediSearch module)
# Note: RediSearch is only available on Premium tier with clustering
python vector_demo.py
```

---

## Exam gotchas

- **Basic tier has no SLA** — always use Standard or Premium for production workloads
- **TTL is not refreshed on access** — once set, the countdown continues regardless of reads
- **SSL/TLS is required** — port 6380 (TLS) is default; port 6379 is non-TLS (not recommended)
- **Stale cache is a real problem** — always implement TTL or invalidation for changing data
- **Vector indexing requires RediSearch module** — available on Premium tier or separate Redis Stack
- **COSINE vs L2 distance** — COSINE for semantic similarity (AI), L2 (EUCLIDEAN) for geometric distance
- **Memory is the main cost driver** — monitor memory usage; scale up/down as needed
- **RediSearch index must match embedding dimensions** — 1536 for text-embedding-ada-002, 3072 for text-embedding-3-large
- **JSON module required for vector storage** — vectors are stored as JSON documents with vector fields
- **Premium tier minimum is 6GB** — P1 is the smallest Premium size
- **Connection strings use password, not key** — the "primary access key" is used as the password
- **Non-TLS connections are insecure** — only use for testing; never in production
- **Keys are case-sensitive** — "User:123" and "user:123" are different keys
- **Maximum value size is 512MB** — per key (strings, hashes, etc.)
- **Pipeline for batch operations** — use `r.pipeline()` to reduce round-trips for multiple commands

---

## Quiz yourself

Take the **azure-managed-redis** quiz in the [quiz app](../../quiz/)
(bank: [`quiz/src/questions/02-data-services/azure-managed-redis.json`](../../quiz/src/questions/02-data-services/azure-managed-redis.json)).

---

## Further reading

- Azure Cache for Redis documentation: <https://learn.microsoft.com/azure/azure-cache-for-redis/>
- Redis documentation: <https://redis.io/docs/>
- Redis commands reference: <https://redis.io/commands/>
- RediSearch module: <https://redis.io/docs/stack/search/>
- Vector similarity search with Redis: <https://redis.io/docs/stack/search/vectors/>
- Azure Cache for Redis pricing: <https://azure.microsoft.com/pricing/details/cache/redis/>
- Redis Python client (redis-py): <https://redis-py.readthedocs.io/>
- Vector indexing tutorial: <https://learn.microsoft.com/azure/architecture/ai-ml/guide/technology-choices/vector-databases>
