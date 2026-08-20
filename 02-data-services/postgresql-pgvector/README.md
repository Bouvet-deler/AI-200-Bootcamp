# Azure Database for PostgreSQL + pgvector

**Domain:** 02 — Develop AI solutions by using Azure data management services (25–30%)
**Maps to skill:** *Connect and query PostgreSQL by using SDKs* · *Model schemas and implement indexing strategies* · *Configure compute/memory/storage for vector workloads* · *Run vector similarity search, store embeddings, semantic retrieval, and implement RAG with metadata filter* · *Implement connection optimization*

---

## What it is

**Azure Database for PostgreSQL** is a **fully managed relational database service** based on the open-source PostgreSQL database engine. It provides **automated backups, high availability, security, and scaling** without the operational overhead of managing your own database servers.

**pgvector** is an **open-source extension** for PostgreSQL that adds **vector similarity search** capabilities. It introduces:
- A `vector` data type for storing **embedding vectors** (arrays of floats)
- **Index types** optimized for fast similarity search (exact and approximate)
- **Distance metrics** for comparing vectors (cosine, L2/Euclidean, inner product)

**Why this combination is powerful:**

The same PostgreSQL database that stores your **relational data** (users, products, orders) can also store **vector embeddings** and perform **blazing-fast similarity searches**. This is the foundation of **Retrieval-Augmented Generation (RAG)** — where an LLM retrieves relevant context from your data before generating a response.

> Mental model:
>
> ```
>   User Query
>        │
>        ▼
>   ┌─────────────────┐
>   │   Application    │
>   │   (LLM + RAG)   │
>   └────────┬────────┘
>             │
>             ▼
>   ┌─────────────────────────────────┐
>   │  Azure Database for PostgreSQL     │
>   │  + pgvector extension            │
>   │                                 │
>   │  ┌─────────────┐  ┌─────────────┐ │
>   │  │  Relational  │  │   Vector     │ │
>   │  │   Tables     │  │   Indexes    │ │
>   │  │ (users, etc) │  │ (embeddings) │ │
>   │  └─────────────┘  └─────────────┘ │
>   └─────────────────────────────────┘
>             │
>             ▼
>   Similarity search results (top-k nearest neighbors)
> ```

**Key capabilities:**
- **Store embeddings** — vectors from models like `text-embedding-ada-002` (1536 dimensions), `text-embedding-3-small` (1024 dim), or `text-embedding-3-large` (3072 dim)
- **Fast similarity search** — find the most similar vectors in milliseconds using specialized indexes
- **Metadata filtering** — combine vector search with SQL WHERE clauses (e.g., "find similar documents in category X")
- **Full transaction support** — ACID compliance means your vectors and metadata stay consistent
- **Hybrid workloads** — run both OLTP and vector search from the same connection

---

## Why it's on the exam

The AI-200 exam tests these core competencies for Azure Database for PostgreSQL + pgvector:

- **Connection and querying** — using SDKs (psycopg2, asyncpg) to connect and execute queries
- **Schema design** — creating tables with vector columns, choosing appropriate data types
- **Indexing strategies** — selecting the right index type (HNSW, IVF, or brute-force) for your workload
- **Vector operations** — storing embeddings, performing similarity search (KNN)
- **RAG implementation** — combining vector search with metadata filtering
- **Connection optimization** — connection pooling, prepared statements, batch operations
- **Performance tuning** — configuring compute, memory, and storage for vector workloads

Expect scenario questions like:
- "Which index type is best for approximate nearest neighbor search?" → **HNSW**
- "How do you store embeddings alongside metadata in PostgreSQL?" → **Create a table with a vector column + JSON/regular columns**
- "What distance metric is best for semantic similarity?" → **COSINE**
- "How do you implement metadata filtering with vector search?" → **Use the `<->` or `<=>` operator in a WHERE clause with additional filters**

---

## Core concepts

### 1. Vector Basics

A **vector** (or **embedding**) is an array of floating-point numbers that represents data in a high-dimensional space. In AI/ML:
- **Text embeddings** — convert text to vectors where semantically similar text has similar vectors
- **Image embeddings** — convert images to vectors capturing visual features
- **Similarity** — vectors close together in space represent similar content

**Distance metrics** (how we measure "closeness"):

| Metric | Formula | Use Case | Range |
| --- | --- | --- | --- |
| **Cosine** | 1 - cosine similarity | Semantic search (text) | 0 to 2 (lower = more similar) |
| **L2 (Euclidean)** | sqrt(sum((a-b)²)) | Geometric distance | 0 to ∞ (lower = more similar) |
| **Inner Product** | -dot(a, b) | Equivalent to cosine for normalized vectors | -∞ to ∞ (higher = more similar) |

> **Exam gotcha:** For **semantic similarity** (text, RAG), use **COSINE** distance. For geometric similarity, use **L2**. Inner product is mathematically equivalent to cosine for normalized vectors.

### 2. pgvector Data Types and Operators

**Data type:**
```sql
-- Create a vector column with 3 dimensions
ALTER TABLE items ADD COLUMN embedding vector(3);

-- Or with 1536 dimensions (for text-embedding-ada-002)
ALTER TABLE documents ADD COLUMN embedding vector(1536);
```

**Operators:**

| Operator | Description | Returns |
| --- | --- | --- |
| `<->` | L2 distance (Euclidean) | float |
| `<=>` | Cosine distance | float |
| `<#>` | Inner product (negative = more similar) | float |

```sql
-- Find items with embedding closest to query_vector using L2 distance
SELECT *, embedding <-> '[0.1, 0.2, 0.3]' AS distance
FROM items
ORDER BY distance ASC
LIMIT 5;

-- Find items using cosine distance (best for semantic similarity)
SELECT *, embedding <=> '[0.1, 0.2, 0.3]' AS cosine_distance
FROM items
ORDER BY cosine_distance ASC
LIMIT 5;
```

### 3. pgvector Index Types

| Index Type | Algorithm | Speed | Accuracy | Memory | Use Case |
| --- | --- | --- | --- | --- | --- |
| **None (brute-force)** | Linear scan | Slow | 100% | Low | Small datasets (<10K vectors) |
| **HNSW** | Hierarchical Navigable Small World | Fast | ~95-99% | Medium | General purpose, recommended default |
| **IVF (Inverted File)** | Partition vectors into clusters | Very fast | Configurable | High | Large datasets with clustering |
| **IVF + HNSW** | Hybrid of IVF and HNSW | Very fast | ~95-99% | High | Best for very large datasets |

**Creating indexes:**
```sql
-- HNSW index (recommended for most use cases)
CREATE INDEX ON items USING hnsw (embedding vector_l2_ops) WITH (m = 16, ef = 64);

-- For cosine distance
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef = 64);

-- For inner product
CREATE INDEX ON items USING hnsw (embedding vector_ip_ops) WITH (m = 16, ef = 64);

-- IVF index with 100 clusters
CREATE INDEX ON items USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- IVF + HNSW hybrid (best for large datasets)
CREATE INDEX ON items USING ivfhnsw (embedding vector_l2_ops) WITH (m = 16, ef = 64, lists = 100);
```

> **Exam gotcha:** The **operator class** in the index (`vector_l2_ops`, `vector_cosine_ops`, `vector_ip_ops`) **must match** the operator you use in queries. Using `<->` with `vector_cosine_ops` will not use the index.

**Index parameters:**
- **`m`** (HNSW) — number of bi-directional links per node (higher = more accurate, more memory)
- **`ef`** (HNSW) — search time parameter (higher = more accurate, slower)
- **`lists`** (IVF) — number of clusters/partitions (higher = faster, more memory)
- **`ef_search`** — search time parameter for IVF-HNSW

### 4. Vector Similarity Search (KNN)

**Basic KNN search:**
```sql
-- Find 5 nearest neighbors using L2 distance
SELECT id, name, embedding <-> '[0.1, 0.2, 0.3]' AS distance
FROM items
ORDER BY distance ASC
LIMIT 5;

-- Using cosine distance (better for semantic search)
SELECT id, name, embedding <=> '[0.1, 0.2, 0.3]' AS cosine_distance
FROM items
ORDER BY cosine_distance ASC
LIMIT 5;
```

**With metadata filtering (the power of RAG):**
```sql
-- Find similar documents in a specific category
SELECT id, title, content, embedding <=> '[0.1, 0.2, 0.3]' AS score
FROM documents
WHERE category = 'technology'
  AND embedding IS NOT NULL
ORDER BY score ASC
LIMIT 10;

-- Filter by multiple conditions
SELECT id, title, score
FROM (
  SELECT id, title, embedding <=> '[0.1, 0.2, 0.3]' AS score
  FROM documents
  WHERE category IN ('technology', 'science')
    AND published_date > '2023-01-01'
) AS subquery
ORDER BY score ASC
LIMIT 5;
```

**Using the `<=>` operator directly in ORDER BY:**
```sql
-- Most concise form
SELECT id, name FROM items
ORDER BY embedding <=> '[0.1, 0.2, 0.3]' ASC
LIMIT 5;
```

### 5. Index Parameters and Performance Tuning

**HNSW parameters:**
- **`m`** — controls the width of the graph (default: 16)
  - Higher = more connections, better accuracy, more memory
  - Typical range: 4-100
- **`ef`** (construction) — controls index build time and accuracy (default: 40)
  - Higher = better accuracy, slower build
- **`ef_search`** — controls query time and accuracy (default: 40)
  - Higher = better accuracy, slower queries

**IVF parameters:**
- **`lists`** — number of clusters (default: 100)
  - Higher = faster queries, more memory
  - Start with 100 and increase based on dataset size

**Index size estimation:**
```
Index size ≈ (number of vectors) × (dimensions) × 4 bytes × (index overhead)

-- For 1M vectors with 1536 dimensions:
1,000,000 × 1536 × 4 = ~6 GB (raw data)
HNSW index: ~2-4x raw data = 12-24 GB
IVF index: ~1.5-2x raw data = 9-12 GB
```

> **Exam gotcha:** Vector indexes can be **large**. For 1M embeddings at 1536 dimensions, expect **10-30 GB** of index storage. Plan your Azure PostgreSQL tier accordingly.

### 6. Azure Database for PostgreSQL Tiers

| Tier | Use Case | vCores | Memory | Storage | IOPS | Features |
| --- | --- | --- | --- | --- | --- | --- |
| **Basic** | Dev/Test | 1-2 | 2-4 GB | 100 GB-2 TB | 300-1000 | No HA, 99.9% SLA |
| **General Purpose** | Production | 2-64 | 8-256 GB | 100 GB-16 TB | Scales with storage | 99.99% SLA, HA, backups |
| **Memory Optimized** | High-performance | 2-64 | 16-432 GB | 100 GB-16 TB | 3,000-20,000 | 99.99% SLA, fastest |
| **Hyperscale** | Large scale | 2-128 | 16-576 GB | 100 GB-100 TB | Scales independently | 99.99% SLA, separate compute/storage |

**Choosing a tier for vector workloads:**
- **Development/testing** → Basic (but limited to 2 vCores, 4 GB RAM)
- **Small production (up to 100K vectors)** → General Purpose (4+ vCores, 16+ GB RAM)
- **Medium workloads (100K-1M vectors)** → Memory Optimized (16+ vCores, 64+ GB RAM)
- **Large workloads (1M+ vectors)** → Memory Optimized with Hyperscale storage or provision larger instances

**Compute sizing for pgvector:**
- **Memory** — needs to hold the **working set** (frequently accessed vectors + indexes)
- **CPU** — more vCores = faster index builds and parallel queries
- **Storage** — fast SSD storage for vector indexes

**Rule of thumb:** For **1M vectors at 1536 dimensions**, you need approximately:
- **30-50 GB RAM** for good performance
- **4+ vCores** for acceptable query latency
- **100+ GB storage** for the database + indexes

> **Exam gotcha:** pgvector indexes are **memory-mapped**. Having enough RAM to cache the index is critical for performance. The **Memory Optimized** tier is recommended for production vector workloads.

### 7. Connection String and SDKs

**Connection string format:**
```
postgresql://username:password@host:port/database?sslmode=require
```

**Python SDKs:**
- **`psycopg2`** — most popular, mature, synchronous
- **`psycopg2-binary`** — pre-built psycopg2, easier to install
- **`asyncpg`** — asynchronous, fast, modern
- **`SQLAlchemy`** — ORM support with PostgreSQL dialect

**Connection pooling:**
- Use **`psycopg2.pool.SimpleConnectionPool`** or **`psycopg2.pool.ThreadedConnectionPool`**
- Or use **`SQLAlchemy`** with connection pooling built-in
- Avoid creating a new connection for each query

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
| `PGSQL_NAME` | PostgreSQL server name |
| `ADMIN_USER` | Database administrator username |
| `ADMIN_PASSWORD` | Database administrator password |
| `PGSQL_SKU` | Pricing tier (GP_Gen5_2, MO_Gen5_4, etc.) |
| `PGSQL_STORAGE` | Storage size in GB |
| `PGSQL_VERSION` | PostgreSQL version (11, 12, 13, 14, 15, 16) |

Copy the block that matches your shell:

```bash
# bash / zsh — Linux, and macOS (its default shell)
RG="ai200-rg"
LOCATION="westeurope"
PGSQL_NAME="ai200-pgvector"
ADMIN_USER="ai200admin"
ADMIN_PASSWORD="YourSecurePassword123!"
PGSQL_SKU="GP_Gen5_4"  # General Purpose, Gen5, 4 vCores
PGSQL_STORAGE="100"  # 100 GB storage
PGSQL_VERSION="16"  # PostgreSQL 16
```

```fish
# fish — Linux / macOS
set RG ai200-rg
set LOCATION westeurope
set PGSQL_NAME ai200-pgvector
set ADMIN_USER ai200admin
set ADMIN_PASSWORD YourSecurePassword123!
set PGSQL_SKU GP_Gen5_4
set PGSQL_STORAGE 100
set PGSQL_VERSION 16
```

```powershell
# PowerShell — Windows (also cross-platform)
$RG = "ai200-rg"
$LOCATION = "westeurope"
$PGSQL_NAME = "ai200-pgvector"
$ADMIN_USER = "ai200admin"
$ADMIN_PASSWORD = "YourSecurePassword123!"
$PGSQL_SKU = "GP_Gen5_4"
$PGSQL_STORAGE = "100"
$PGSQL_VERSION = "16"
```

```bat
:: Command Prompt (cmd.exe) — Windows
set RG=ai200-rg
set LOCATION=westeurope
set PGSQL_NAME=ai200-pgvector
set ADMIN_USER=ai200admin
set ADMIN_PASSWORD=YourSecurePassword123!
set PGSQL_SKU=GP_Gen5_4
set PGSQL_STORAGE=100
set PGSQL_VERSION=16
```

### Prerequisites

1. **Azure CLI installed** and logged in (`az login`)
2. **pgvector extension** — we'll install it after server creation

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first), after [setting your variables](#set-your-variables) above.

```bash
# 1. Create the resource group
az group create --name "$RG" --location "$LOCATION"

# 2. Create the PostgreSQL server
#    GP_Gen5_2 = General Purpose, Gen5, 2 vCores
#    MO_Gen5_4 = Memory Optimized, Gen5, 4 vCores (recommended for vector workloads)
#    For vector workloads, consider MO (Memory Optimized) tier
az postgres server create \
  --name "$PGSQL_NAME" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku-name "$PGSQL_SKU" \
  --storage-size "${PGSQL_STORAGE}GB" \
  --version "$PGSQL_VERSION" \
  --admin-user "$ADMIN_USER" \
  --admin-password "$ADMIN_PASSWORD" \
  --public-network-access Enabled \
  --ssl-enforcement Enabled

# 3. Configure firewall rule to allow connections from your IP
#    Get your public IP: curl ifconfig.me (Linux/macOS) or visit https://whatismyip.com
MY_IP=$(curl -s ifconfig.me)
az postgres server firewall-rule create \
  --name "AllowMyIP" \
  --resource-group "$RG" \
  --server-name "$PGSQL_NAME" \
  --start-ip-address "$MY_IP" \
  --end-ip-address "$MY_IP"

# 4. Create a database for vector operations
az postgres database create \
  --name "vector_db" \
  --resource-group "$RG" \
  --server-name "$PGSQL_NAME"

# 5. Get connection information
PGSQL_HOST=$(az postgres server show \
  --name "$PGSQL_NAME" \
  --resource-group "$RG" \
  --query fullyQualifiedDomainName \
  --output tsv)

echo "PostgreSQL host: $PGSQL_HOST"
echo "PostgreSQL port: 5432"
echo "Admin user: $ADMIN_USER"
echo "Database: vector_db"
```

The PostgreSQL server is now ready. Next, you'll [install pgvector and test it](#hands-on-python).

### Portal Setup (Web UI)

Prefer the browser? Create the same resources in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Create Resource Group:**
   - Click **Resource groups** → **+ Create**
   - Name: `ai200-rg` (or your chosen name)
   - Region: `West Europe` (or your preference)
   - Click **Review + create** → **Create**

3. **Create PostgreSQL Server:**
   - Click **+ Create a resource** → Search for "Azure Database for PostgreSQL" → **Create**
   - **Deployment option:** Single server
   - Subscription: your subscription
   - Resource group: `ai200-rg`
   - Server name: `ai200-pgvector`
   - Region: `West Europe`
   - **Compute + storage:**
     - For vector workloads: **Memory Optimized** (MO_Gen5_4 or higher)
     - Or **General Purpose** (GP_Gen5_4) for smaller workloads
     - Storage: **100 GB** or more
   - PostgreSQL version: **16** (or latest available)
   - Admin username: `ai200admin`
   - Admin password: `YourSecurePassword123!`
   - **Networking:**
     - Connectivity method: **Public access**
     - SSL: **Enabled**
     - Firewall rules: **Add current client IP address**
   - Click **Review + create** → **Create**

4. **Create a database:**
   - Navigate to your PostgreSQL server (`ai200-pgvector`)
   - Under **Settings → Databases**, click **+ Add**
   - Database name: `vector_db`
   - Click **Save**

5. **Get connection information:**
   - On the **Overview** blade, note the **Server name** (e.g., `ai200-pgvector.postgres.database.azure.com`)
   - The **Server admin login name** is the username you created
   - The password is what you set during creation

6. **Configure firewall (if needed):**
   - Under **Settings → Connection security**, add your client IP address

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
# This removes: PostgreSQL server, database, firewall rules, and any other resources in the group.
# The '--yes' flag skips the confirmation prompt. Use '--no-wait' to not wait for completion.
az group delete --name "$RG" --yes --no-wait

# Optional: verify the resource group is gone
az group list --output table
```

> **Important:** Deleting a resource group is **permanent and immediate**. All resources in that group (PostgreSQL server, database, etc.) will be deleted and cannot be recovered. Back up your data first if needed.

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

Let's use the **`psycopg2`** library to interact with Azure Database for PostgreSQL + pgvector. We'll demonstrate:
1. Connecting to PostgreSQL
2. Installing and enabling the pgvector extension
3. Creating tables with vector columns
4. Inserting embeddings
5. Performing similarity search (KNN)
6. Implementing RAG with metadata filtering
7. Using connection pooling

> **Remember:** Run all commands below from this folder (`02-data-services/postgresql-pgvector/`).

### Project Structure

```
postgresql-pgvector/
├── pgvector_demo.py              # Main demonstration script
├── rag_demo.py                   # RAG implementation with metadata filtering
├── connection_pooling_demo.py    # Connection pooling best practices
└── requirements.txt              # Python dependencies
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
pip install psycopg2-binary==2.9.9 numpy==1.26.0 python-dotenv==1.0.0
```

**requirements.txt:**
```
psycopg2-binary==2.9.9
numpy==1.26.0
python-dotenv==1.0.0
```

### 1. Basic pgvector Operations

**pgvector_demo.py:**

```python
"""
Azure Database for PostgreSQL + pgvector - Basic Operations Demo

This script demonstrates:
- Connecting to Azure Database for PostgreSQL
- Installing and enabling the pgvector extension
- Creating tables with vector columns
- Inserting and querying vector embeddings
- Performing similarity search (KNN)
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
PGSQL_HOST = os.environ.get("PGSQL_HOST")
PGSQL_PORT = int(os.environ.get("PGSQL_PORT", 5432))
PGSQL_DATABASE = os.environ.get("PGSQL_DATABASE", "vector_db")
PGSQL_USER = os.environ.get("PGSQL_USER")
PGSQL_PASSWORD = os.environ.get("PGSQL_PASSWORD")
PGSQL_SSL_MODE = os.environ.get("PGSQL_SSL_MODE", "require")

print("=" * 60)
print("CONNECTING TO POSTGRESQL")
print("=" * 60)

try:
    conn = psycopg2.connect(
        host=PGSQL_HOST,
        port=PGSQL_PORT,
        database=PGSQL_DATABASE,
        user=PGSQL_USER,
        password=PGSQL_PASSWORD,
        sslmode=PGSQL_SSL_MODE,
    )
    cursor = conn.cursor()
    print(f"Connected to PostgreSQL at {PGSQL_HOST}")
    cursor.execute("SELECT version();")
    print(f"PostgreSQL version: {cursor.fetchone()[0]}")
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

# ============================================================================
# 1. Install pgvector Extension
# ============================================================================
print("\n" + "=" * 60)
print("INSTALLING PGVECTOR EXTENSION")
print("=" * 60)

cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
if not cursor.fetchone():
    try:
        cursor.execute("CREATE EXTENSION vector;")
        conn.commit()
        print("pgvector extension installed")
    except Exception as e:
        print(f"Note: {e}")
        print("Ensure pgvector is available for your PostgreSQL version")
else:
    print("pgvector extension already installed")

# ============================================================================
# 2. Create Table with Vector Column
# ============================================================================
print("\n" + "=" * 60)
print("CREATING TABLE WITH VECTOR COLUMN")
print("=" * 60)

cursor.execute("DROP TABLE IF EXISTS items;")
cursor.execute("""
    CREATE TABLE items (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255),
        description TEXT,
        embedding vector(3)
    );
""")
conn.commit()
print("Created items table with vector(3) column")

# ============================================================================
# 3. Insert Sample Data
# ============================================================================
print("\n" + "=" * 60)
print("INSERTING SAMPLE DATA")
print("=" * 60)

items = [
    ("Laptop", "Portable computer", [0.8, 0.2, 0.1]),
    ("Phone", "Mobile device", [0.7, 0.3, 0.2]),
    ("Tablet", "Touchscreen device", [0.75, 0.25, 0.15]),
    ("Monitor", "Display screen", [0.9, 0.1, 0.05]),
    ("Mouse", "Pointing device", [0.3, 0.6, 0.5]),
]

for name, desc, embedding in items:
    cursor.execute(
        "INSERT INTO items (name, description, embedding) VALUES (%s, %s, %s);",
        (name, desc, embedding)
    )
conn.commit()
print(f"Inserted {len(items)} items")

# ============================================================================
# 4. Create Vector Index
# ============================================================================
print("\n" + "=" * 60)
print("CREATING VECTOR INDEX")
print("=" * 60)

cursor.execute("""
    CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef = 64);
""")
conn.commit()
print("Created HNSW index with cosine distance")

# ============================================================================
# 5. Vector Similarity Search
# ============================================================================
print("\n" + "=" * 60)
print("VECTOR SIMILARITY SEARCH")
print("=" * 60)

query_vector = [0.78, 0.22, 0.12]
cursor.execute("""
    SELECT id, name, embedding <=> %s AS distance
    FROM items
    ORDER BY distance ASC
    LIMIT 5;
""", (query_vector,))

print(f"\nQuery vector: {query_vector}")
print("\nTop matches:")
for i, row in enumerate(cursor.fetchall()):
    print(f"  {i+1}. {row[1]} (distance: {row[2]:.4f})")

# ============================================================================
# 6. Cleanup
# ============================================================================
cursor.close()
conn.close()
print("\nConnection closed. Demo complete!")
```

### 2. RAG Implementation with Metadata Filtering

**rag_demo.py:**

```python
"""
Azure Database for PostgreSQL + pgvector - RAG Implementation

This script demonstrates:
- Creating a documents table with metadata
- Performing similarity search with metadata filtering
- Implementing Retrieval-Augmented Generation (RAG) pattern
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

PGSQL_HOST = os.environ.get("PGSQL_HOST")
PGSQL_DATABASE = os.environ.get("PGSQL_DATABASE", "vector_db")
PGSQL_USER = os.environ.get("PGSQL_USER")
PGSQL_PASSWORD = os.environ.get("PGSQL_PASSWORD")
PGSQL_SSL_MODE = os.environ.get("PGSQL_SSL_MODE", "require")

conn = psycopg2.connect(
    host=PGSQL_HOST, database=PGSQL_DATABASE,
    user=PGSQL_USER, password=PGSQL_PASSWORD, sslmode=PGSQL_SSL_MODE
)
cursor = conn.cursor()

# Create documents table
cursor.execute("DROP TABLE IF EXISTS documents;")
cursor.execute("""
    CREATE TABLE documents (
        id SERIAL PRIMARY KEY,
        title VARCHAR(500),
        content TEXT,
        category VARCHAR(100),
        embedding vector(3)
    );
""")
conn.commit()

# Insert sample documents
docs = [
    ("AI in Healthcare", "AI is transforming healthcare...", "healthcare", [0.85, 0.1, 0.05]),
    ("AI in Finance", "Financial institutions use AI...", "finance", [0.82, 0.12, 0.06]),
    ("AI in Education", "Education sector adopts AI...", "education", [0.8, 0.15, 0.08]),
    ("Python Programming", "Python is popular for...", "programming", [0.15, 0.8, 0.1]),
    ("JavaScript Guide", "JavaScript is essential for...", "programming", [0.18, 0.75, 0.07]),
]

for title, content, category, embedding in docs:
    cursor.execute(
        "INSERT INTO documents (title, content, category, embedding) VALUES (%s, %s, %s, %s);",
        (title, content, category, embedding)
    )
conn.commit()

# Create index
cursor.execute("""
    CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef = 64);
""")
conn.commit()

# RAG: Find similar documents in specific category
query_vector = [0.83, 0.11, 0.06]
category = "healthcare"

print("=" * 60)
print("RAG DEMO: Similarity Search with Metadata Filtering")
print("=" * 60)
print(f"\nQuery vector: {query_vector}")
print(f"Category filter: {category}\n")

cursor.execute("""
    SELECT id, title, category, embedding <=> %s AS score
    FROM documents
    WHERE category = %s
    ORDER BY score ASC
    LIMIT 3;
""", (query_vector, category))

print("Retrieved documents (context for LLM):")
for i, row in enumerate(cursor.fetchall()):
    print(f"  {i+1}. {row[1]} (category: {row[2]}, score: {row[3]:.4f})")

cursor.close()
conn.close()
```

### 3. Connection Pooling

**connection_pooling_demo.py:**

```python
"""
Connection Pooling Best Practices for PostgreSQL
"""

import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

PGSQL_HOST = os.environ.get("PGSQL_HOST")
PGSQL_DATABASE = os.environ.get("PGSQL_DATABASE", "vector_db")
PGSQL_USER = os.environ.get("PGSQL_USER")
PGSQL_PASSWORD = os.environ.get("PGSQL_PASSWORD")

# Create connection pool
connection_pool = pool.ThreadedConnectionPool(
    minconn=2, maxconn=10,
    host=PGSQL_HOST, database=PGSQL_DATABASE,
    user=PGSQL_USER, password=PGSQL_PASSWORD, sslmode="require"
)

print("Connection pool created with 2-10 connections")

# Use connection from pool
conn = connection_pool.getconn()
cursor = conn.cursor()
cursor.execute("SELECT version();")
print(f"PostgreSQL version: {cursor.fetchone()[0]}")
cursor.close()
connection_pool.putconn(conn)

# Always return connections to pool
print("Connection returned to pool. Pool is ready for production use.")

# Close pool when done
# connection_pool.closeall()
```

### Run the Demos

```bash
# Set environment variables (create .env file or export)
export PGSQL_HOST="your-host.postgres.database.azure.com"
export PGSQL_DATABASE="vector_db"
export PGSQL_USER="ai200admin"
export PGSQL_PASSWORD="your-password"

# Or create .env file:
echo "PGSQL_HOST=your-host.postgres.database.azure.com" > .env
echo "PGSQL_DATABASE=vector_db" >> .env
echo "PGSQL_USER=ai200admin" >> .env
echo "PGSQL_PASSWORD=your-password" >> .env
echo "PGSQL_SSL_MODE=require" >> .env

# Install dependencies
pip install -r requirements.txt

# Run demos
python pgvector_demo.py
python rag_demo.py
python connection_pooling_demo.py
```

---

## Exam gotchas

- **pgvector requires PostgreSQL 11+** — Azure Database for PostgreSQL supports this, but verify your version
- **Vector index operator must match query operator** — `vector_l2_ops` with `<->`, `vector_cosine_ops` with `<=>`
- **Memory Optimized tier recommended** — vector indexes are memory-mapped; sufficient RAM is critical
- **HNSW is the recommended index type** — good balance of speed and accuracy for most use cases
- **Cosine distance for semantic similarity** — use `<=>` operator and `vector_cosine_ops` index
- **Connection pooling is essential** — creating a new connection for each query adds significant overhead
- **SSL is required for Azure Database for PostgreSQL** — always use `sslmode=require`
- **Storage requirements** — vector indexes can be 2-4x the size of the raw vector data
- **Index build time** — building indexes on large datasets can take significant time and resources
- **Batch inserts** — use `executemany()` or `COPY` for bulk inserts to improve performance

---

## Quiz yourself

Take the **postgresql-pgvector** quiz in the [quiz app](../../quiz/) (bank: [`quiz/src/questions/02-data-services/postgresql-pgvector.json`](../../quiz/src/questions/02-data-services/postgresql-pgvector.json)).

---

## Further reading

- Azure Database for PostgreSQL documentation: <https://learn.microsoft.com/azure/postgresql/>
- pgvector extension: <https://github.com/pgvector/pgvector>
- pgvector documentation: <https://github.com/pgvector/pgvector#readme>
- PostgreSQL documentation: <https://www.postgresql.org/docs/>
- psycopg2 documentation: <https://www.psycopg.org/docs/>
- RAG implementation guide: <https://learn.microsoft.com/azure/architecture/ai-ml/guide/rag>
- Embedding models (Azure OpenAI): <https://learn.microsoft.com/azure/ai-services/openai/concepts/models>
- Vector database comparison: <https://learn.microsoft.com/azure/architecture/ai-ml/guide/technology-choices/vector-databases>
