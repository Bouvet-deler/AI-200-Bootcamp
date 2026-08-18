# Azure Container Apps + KEDA

**Domain:** 01 — Develop containerized solutions on Azure (20–25%)
**Maps to skill:** *Deploy applications to Azure Container Apps, including environment
configuration and revision management* · *Implement event-driven scaling by using KEDA in
Container Apps*

---

## What it is

**Azure Container Apps (ACA)** is a **serverless containers platform** — you run containers without
managing any infrastructure (no VMs, no clusters, no orchestration to operate). Think of it as "App
Service for containers, but with microservices support and scale-to-zero."

**KEDA** (Kubernetes Event-Driven Autoscaler) is the **engine inside ACA** that automatically scales
your containers based on events — queue length, HTTP traffic, CPU load, cron schedules, and more.
Together, they give you **event-driven, serverless containers** that can scale to zero when idle.

> Mental model:
>
> ```
>   Your app container(s)
>        │
>        ▼
>   Azure Container Apps environment  ──►  Revisions (immutable versions)
>        │
>        ▼
>   KEDA autoscaler  ──listens to──►  Event sources (queue, HTTP, timer...)
>        │
>        ▼
>   Scale containers: 0 → N  (based on event load)
> ```

Key distinctions from other hosts:
- **No Kubernetes to manage** — ACA hides K8s behind a simple YAML/JSON or CLI experience
- **Scale to zero** — unlike App Service, ACA can have 0 replicas and cost nothing when idle
- **Event-driven** — KEDA can trigger scaling based on external events (Service Bus messages,
  Storage Queue length, Event Hub, etc.)
- **Microservices-ready** — multiple containers/applications in one shared environment

---

## Why it's on the exam

The AI-200 exam tests these core competencies for Container Apps + KEDA:

- **Deploying apps** — creating environments, deploying containers, configuring ingress
- **Revision management** — understanding immutable revisions, traffic splitting, rollbacks
- **KEDA scale rules** — configuring triggers (scalers) for different event sources
- **Choosing ACA vs alternatives** — knowing when ACA is the right choice vs App Service or AKS

Expect scenario questions like:
- "A team needs a web API that scales to zero and processes messages from a queue — which service?"
  → **Container Apps + KEDA**
- "Which feature enables canary deployments?" → **Revisions + traffic splitting**
- "How do you configure scaling based on queue length?" → **KEDA scale rule with queue trigger**

---

## Core concepts

### 1. Architecture: Environments, Apps, Containers, Jobs, Revisions

Azure Container Apps is organized hierarchically:

```
Registry (ACR) ──images──►
                              ┌─────────────────────────────────────────┐
                              │         Container Apps Environment       │
                              │    (network boundary + logging shared)    │
                              │                                             │
                              │  ┌──────────────┐  ┌──────────────┐     │
                              │  │    App A      │  │    App B      │     │
                              │  │ (Containers)  │  │ (Containers)  │     │
                              │  │  └ container1 │  │  └ container1 │     │
                              │  │  └ container2 │  │  └ container2 │     │
                              │  └──────────────┘  └──────────────┘     │
                              │                                             │
                              │  ┌──────────────┐                         │
                              │  │    Job C      │                         │
                              │  │ (Event-driven │                         │
                              │  │  container)   │                         │
                              │  └──────────────┘                         │
                              └─────────────────────────────────────────┘
```

| Term | What it is | Analogy |
| --- | --- | --- |
| **Environment** | The "workspace" — a network boundary that holds apps/jobs. All apps in the same environment share a VNet, Log Analytics workspace, and can communicate via internal DNS. | Like a Kubernetes namespace, but with networking built-in |
| **Application (App)** | A long-running service. Defined in a manifest (YAML/JSON) with containers, scale rules, ingress. | Like a Deployment + Service in Kubernetes |
| **Container** | A single container image running as part of an app. An app can have 1-N containers. | Like a container in a pod |
| **Job** | An event-driven or scheduled container that runs to completion. Unlike Apps, Jobs are **not** long-running. | Like a CronJob in Kubernetes |
| **Revision** | An immutable version of an app. Created on every deployment. You can split traffic between revisions. | Like a Deployment revision in Kubernetes (but first-class in ACA) |

> **Exam gotcha:** A **Job** is for batch/triggered work (runs once, exits). An **App** is for long-running
> services (APIs, web apps). Pick the right one.

### 2. Revisions — Immutable Deployments

Every time you deploy an app (change the manifest or image), Container Apps creates a new **revision**.
Revisions are **immutable** — they never change. This enables:

- **Rollbacks** — instantly revert to a previous revision
- **Canary deployments** — send 5% of traffic to the new revision, monitor, then ramp up
- **Blue-green** — switch all traffic from old to new revision at once
- **A/B testing** — route traffic based on headers or other rules

```
Old Revision (v1)       New Revision (v2)
      │                       │
      ▼                       ▼
   ┌──────────┐           ┌──────────┐
   │  App v1   │           │  App v2   │
   └──────────┘           └──────────┘
         ▲                         ▲
         │ 95% traffic             │ 5% traffic (canary)
         └──────────┬──────────────┘
                      │
                 Traffic split
```

### 3. KEDA — Event-Driven Autoscaling

KEDA (Kubernetes-based Event Driven Autoscaler) is built into Container Apps. It scales your app
**based on events**, not just CPU/memory.

**How KEDA works:**
1. You define **scale rules** (triggers) in your app manifest
2. KEDA **polling** the event source (e.g., "how many messages in the queue?")
3. When the event metric crosses your threshold, KEDA **scales out** your containers
4. When traffic subsides, KEDA **scales in** — even to **zero**

**Supported KEDA Scalers in ACA:**

| Scaler Type | Event Source | Use Case |
| --- | --- | --- |
| `http` | Incoming HTTP requests | Scale on web traffic |
| `cpu` | CPU usage | Scale when CPU > threshold |
| `memory` | Memory usage | Scale when memory > threshold |
| `azure-queue` | Azure Storage Queue | Scale based on queue length |
| `azure-servicebus` | Service Bus queue/topic | Scale on message count |
| `azure-eventhub` | Event Hub | Scale on event throughput |
| `azure-blob-storage` | Blob Storage | Scale based on blob count |
| `azure-cosmosdb` | Cosmos DB | Scale based on RU/s or collection size |
| `cron` | Scheduled timer | Scale up/down on a schedule |
| `rabbitmq` | RabbitMQ queue | Scale on queue length |
| `redis` | Redis lists/streams | Scale based on Redis data |

> **Exam gotcha:** The `http` scaler is **automatically added** for every app with ingress enabled.
> You get HTTP-based scaling out of the box.

### 4. Ingress and Networking

**Ingress** — Controls how external traffic reaches your app. Options:

| Type | Behavior | Use Case |
| --- | --- | --- |
| `external` | Publicly accessible via a FQDN (`<app>.<environment>.<region>.azurecontainerapps.io`) | Public web APIs |
| `internal` | Only accessible within the environment's VNet | Microservices talking to each other |
| `none` | No external access | Background workers, jobs |

**Custom domains and TLS** are supported via Azure-managed certificates or your own.

### 5. Managed Identity

Container Apps supports **system-assigned** and **user-assigned** managed identities. These are used
to grant your app access to other Azure resources (Key Vault, Storage, Service Bus, etc.).

> **Exam gotcha:** When your app needs to pull from ACR, grant the managed identity **AcrPull** role
> on the registry.

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
| `CONTAINERAPPS_ENV` | Container Apps environment name |
| `LOG_ANALYTICS` | Log Analytics workspace name (for logs) |

Copy the block that matches your shell:

```bash
# bash / zsh — Linux, and macOS (its default shell)
RG="ai200-rg"
LOCATION="westeurope"
CONTAINERAPPS_ENV="ai200-aca-env"
LOG_ANALYTICS="ai200-logs"
```

```fish
# fish — Linux / macOS
set RG ai200-rg
set LOCATION westeurope
set CONTAINERAPPS_ENV ai200-aca-env
set LOG_ANALYTICS ai200-logs
```

```powershell
# PowerShell — Windows (also cross-platform)
$RG = "ai200-rg"
$LOCATION = "westeurope"
$CONTAINERAPPS_ENV = "ai200-aca-env"
$LOG_ANALYTICS = "ai200-logs"
```

```bat
:: Command Prompt (cmd.exe) — Windows
set RG=ai200-rg
set LOCATION=westeurope
set CONTAINERAPPS_ENV=ai200-aca-env
set LOG_ANALYTICS=ai200-logs
```

### Prerequisites

1. **Azure CLI installed** and logged in (`az login`)
2. **Extensions** — run these once per machine:

```bash
# Add the containerapp extension (for az containerapp commands)
az extension add --name containerapp --only-show-errors

# Add the monitor extension (for Log Analytics)
az extension add --name monitor --only-show-errors
```

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first), after
[setting your variables](#set-your-variables) above.

```bash
# 1. Create the resource group
az group create --name "$RG" --location "$LOCATION"

# 2. Create a Log Analytics workspace (for storing Container Apps logs)
az monitor log-analytics workspace create \
  --resource-group "$RG" \
  --workspace-name "$LOG_ANALYTICS" \
  --location "$LOCATION"

# 3. Create the Container Apps environment
#    This is the shared network/logging boundary for your apps
az containerapp env create \
  --name "$CONTAINERAPPS_ENV" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --logs-workspace-id "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG/providers/Microsoft.OperationalInsights/workspaces/$LOG_ANALYTICS" \
  --logs-workspace-key "$(az monitor log-analytics workspace get-shared-keys --resource-group $RG --workspace-name $LOG_ANALYTICS --query primarySharedKey -o tsv)"

# 4. Verify the environment was created
az containerapp env list --resource-group "$RG" --output table
```

The environment is now ready. Next, you'll [deploy an app](#hands-on-python).

### Portal Setup (Web UI)

Prefer the browser? Create the same resources in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Create Resource Group:**
   - Click **Resource groups** → **+ Create**
   - Name: `ai200-rg` (or your chosen name)
   - Region: `West Europe` (or your preference)
   - Click **Review + create** → **Create**

3. **Create Log Analytics workspace:**
   - Click **+ Create a resource** → Search for "Log Analytics workspace" → **Create**
   - Subscription: your subscription
   - Resource group: `ai200-rg`
   - Name: `ai200-logs`
   - Region: `West Europe`
   - Click **Review + create** → **Create**

4. **Create Container Apps Environment:**
   - Click **+ Create a resource** → Search for "Container Apps Environment" → **Create**
   - Subscription: your subscription
   - Resource group: `ai200-rg`
   - Environment name: `ai200-aca-env`
   - Region: `West Europe`
   - Under **Application Logging**, enable **Log Analytics**
   - Log Analytics workspace: select `ai200-logs`
   - Click **Review + create** → **Create**

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
# This removes: Container Apps environment, Log Analytics workspace, and all apps.
# The '--yes' flag skips the confirmation prompt. Use '--no-wait' to not wait for completion.
az group delete --name "$RG" --yes --no-wait

# Optional: verify the resource group is gone
az group list --output table
```

> **Important:** Deleting a resource group is **permanent and immediate**. All resources in that
group (Container Apps environment, Log Analytics workspace, all apps) will be deleted and cannot
be recovered.

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

## Hands-on (Python) — Simple Web API with Queue-Based Scaling

Let's build a **Flask web API** that:
1. Serves HTTP requests (auto-scaled by KEDA's `http` scaler)
2. Processes messages from an Azure Storage Queue (auto-scaled by KEDA's `azure-queue` scaler)

The app demonstrates **dual scaling**: it scales based on both HTTP traffic AND queue length.

> **Remember:** Run all commands below from this folder (`01-containers/container-apps-keda/`).

### Project Structure

```
ai200-container-apps-keda/
├── app/                          # Your application code
│   ├── main.py                   # Flask app with queue processing
│   ├── requirements.txt          # Python dependencies
│   └── Dockerfile                # Container image definition
├── container-app.yaml            # Container Apps manifest
└── README.md                     # This file
```

### 1. Create the Flask Application

**app/main.py:**

```python
# A simple Flask API that also processes messages from an Azure Storage Queue
# This demonstrates both HTTP-based and queue-based scaling with KEDA

from flask import Flask, jsonify, request
import os
import time
import logging
from azure.storage.queue import QueueClient
from threading import Thread

app = Flask(__name__)

# Configure logging to see output in Container Apps logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get queue connection string from environment variable
QUEUE_CONNECTION_STRING = os.environ.get("QUEUE_CONNECTION_STRING", "")
QUEUE_NAME = os.environ.get("QUEUE_NAME", "orders")

@app.route("/")
def home():
    """Health check endpoint — returns 200 OK"""
    logger.info("Home endpoint called")
    return jsonify({"status": "ok", "message": "Container Apps + KEDA Demo"})

@app.route("/orders", methods=["GET"])
def get_orders():
    """Return a list of sample orders"""
    logger.info("GET /orders called")
    return jsonify([
        {"id": 1, "product": "Widget A", "quantity": 5},
        {"id": 2, "product": "Widget B", "quantity": 3},
    ])

@app.route("/orders", methods=["POST"])
def create_order():
    """Create a new order and add it to the queue for processing"""
    order = request.json
    logger.info(f"POST /orders called with order: {order}")
    
    # Add the order to the queue
    if QUEUE_CONNECTION_STRING:
        queue_client = QueueClient.from_connection_string(
            QUEUE_CONNECTION_STRING, QUEUE_NAME
        )
        queue_client.send_message(str(order))
        logger.info(f"Added order to queue: {order}")
    
    return jsonify({"status": "created", "order": order}), 201

def process_queue_messages():
    """Background thread that processes messages from the queue"""
    if not QUEUE_CONNECTION_STRING:
        logger.warning("No QUEUE_CONNECTION_STRING set, skipping queue processing")
        return
    
    queue_client = QueueClient.from_connection_string(
        QUEUE_CONNECTION_STRING, QUEUE_NAME
    )
    
    logger.info("Starting queue message processor...")
    while True:
        try:
            # Get a message from the queue (visibility timeout of 30 seconds)
            message = queue_client.get_message(visibility_timeout=30)
            if message:
                logger.info(f"Processing queue message: {message.content}")
                # Simulate processing
                time.sleep(1)
                # Delete the message after processing
                queue_client.delete_message(message)
                logger.info(f"Finished processing: {message.content}")
        except Exception as e:
            logger.error(f"Error processing queue message: {e}")
        
        # Poll every 5 seconds
        time.sleep(5)

# Start the queue processor in a background thread when the app starts
if QUEUE_CONNECTION_STRING:
    queue_thread = Thread(target=process_queue_messages, daemon=True)
    queue_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
```

**app/requirements.txt:**

```
Flask==3.0.0
azure-storage-queue==12.1.0
```

**app/Dockerfile:**

```dockerfile
# Use the official Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Run the Flask app
CMD ["python", "main.py"]
```

### 2. Build and Push to ACR

First, create an Azure Container Registry and build/push your image:

```bash
# Create ACR (if you haven't already)
az acr create --name ai200acr --resource-group "$RG" --sku Basic --location "$LOCATION"

# Build and push the image using ACR Tasks (no local Docker required!)
az acr build --registry ai200acr --image ai200-container-apps-demo:v1.0 ./app

# Verify the image exists
az acr repository list --name ai200acr --output table
az acr repository show-tags --name ai200acr --repository ai200-container-apps-demo --output table
```

### 3. Create a Storage Account and Queue

```bash
# Create a storage account
STORAGE_ACCOUNT="ai200storage$(date +%s)"
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Standard_LRS

# Get the connection string
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RG" \
  --query connectionString \
  --output tsv)

# Create a queue
az storage queue create --name orders --account-name "$STORAGE_ACCOUNT" --connection-string "$STORAGE_CONNECTION_STRING"

echo "Storage connection string: $STORAGE_CONNECTION_STRING"
```

**Save the connection string** — you'll need it for the app configuration.

### 4. Create the Container Apps Manifest

**container-app.yaml:**

```yaml
# Container Apps manifest for our demo app
# Deploy with: az containerapp create --resource-group $RG --name ai200-demo --yaml container-app.yaml

location: westeurope
kind: Deployment
metadata:
  name: ai200-demo
properties:
  environmentId: "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG/providers/Microsoft.App/containerAppsEnvironments/$CONTAINERAPPS_ENV"
  
  # The containers that make up this app
  containers:
    - name: web-api
      image: ai200acr.azurecr.io/ai200-container-apps-demo:v1.0
      resources:
        cpu: 0.25
        memory: 0.5Gi
      env:
        - name: PORT
          value: "8000"
        - name: QUEUE_CONNECTION_STRING
          value: "$STORAGE_CONNECTION_STRING"  # Replace with your actual connection string
        - name: QUEUE_NAME
          value: "orders"
  
  # Ingress configuration - makes the app publicly accessible
  ingress:
    external: true
    targetPort: 8000
    transport: auto
    traffic:
      - weight: 100
        revisionSuffix: latest
  
  # Scale rules for KEDA
  scale:
    minReplicas: 0  # Scale to zero when idle
    maxReplicas: 5
    rules:
      # Scale based on HTTP traffic (auto-added for ingress, but we can customize)
      - name: http-scaler
        custom:
          type: http
          metadata:
            concurrentRequests: "50"  # Scale out when > 50 concurrent requests
      
      # Scale based on Azure Storage Queue length
      - name: queue-scaler
        custom:
          type: azure-queue
          metadata:
            queueName: "orders"
            connection: "$STORAGE_CONNECTION_STRING"  # Same connection string as above
            queueLength: "5"  # Scale out when > 5 messages in queue
```

> **Important:** Replace `$STORAGE_CONNECTION_STRING` with the actual connection string from step 3.
> For CLI deployment, you can set it as an environment variable and use `"${STORAGE_CONNECTION_STRING}"` in
> the YAML.

### 5. Deploy the Application

```bash
# Deploy using the manifest
az containerapp create \
  --resource-group "$RG" \
  --name ai200-demo \
  --environment "$CONTAINERAPPS_ENV" \
  --image ai200acr.azurecr.io/ai200-container-apps-demo:v1.0 \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 5 \
  --scale-rule-name http-scaler \
  --scale-rule-type http \
  --scale-rule-metadata concurrentRequests=50 \
  --scale-rule-name queue-scaler \
  --scale-rule-type azure-queue \
  --scale-rule-metadata queueName=orders connection="$STORAGE_CONNECTION_STRING" queueLength=5 \
  --env-vars PORT=8000 QUEUE_CONNECTION_STRING="$STORAGE_CONNECTION_STRING" QUEUE_NAME=orders \
  --registry-server ai200acr.azurecr.io \
  --registry-identity system

# Alternatively, deploy from the YAML manifest:
# az containerapp create --resource-group $RG --name ai200-demo --yaml container-app.yaml
```

The deployment will:
1. Pull the image from ACR
2. Create the app with HTTP ingress
3. Configure KEDA with HTTP and queue-based scaling
4. Set the environment variables for queue processing

### 6. Test the Application

```bash
# Get the app's URL
APP_URL=$(az containerapp show \
  --name ai200-demo \
  --resource-group "$RG" \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

echo "Application URL: https://$APP_URL"

# Test the health endpoint
curl "https://$APP_URL/"

# Test creating an order (which adds to the queue)
curl -X POST "https://$APP_URL/orders" \
  -H "Content-Type: application/json" \
  -d '{"product": "Test Product", "quantity": 1}'

# View the app's logs
az containerapp logs show \
  --name ai200-demo \
  --resource-group "$RG" \
  --follow
```

### 7. Test Scaling Behavior

```bash
# Add multiple messages to the queue to trigger scaling
for i in {1..10}; do
  az storage message put \
    --content "Order $i" \
    --queue-name orders \
    --connection-string "$STORAGE_CONNECTION_STRING"
done

# Watch the app scale up (may take 30-60 seconds)
az containerapp revision list \
  --name ai200-demo \
  --resource-group "$RG" \
  --output table \
  --watch

# Check the current scale
az containerapp show \
  --name ai200-demo \
  --resource-group "$RG" \
  --query properties.template.scale.minReplicas \
  --query properties.template.scale.maxReplicas \
  --query properties.template.scale.rules
```

### 8. Update and Create a New Revision

```bash
# Update the app by changing the image tag or configuration
# This creates a new revision
az containerapp update \
  --name ai200-demo \
  --resource-group "$RG" \
  --image ai200acr.azurecr.io/ai200-container-apps-demo:v2.0 \
  --revision-suffix v2

# List all revisions
az containerapp revision list \
  --name ai200-demo \
  --resource-group "$RG" \
  --output table

# Split traffic between revisions (canary deployment)
az containerapp update \
  --name ai200-demo \
  --resource-group "$RG" \
  --traffic-split latest=75,v2=25

# Roll back to the previous revision
az containerapp update \
  --name ai200-demo \
  --resource-group "$RG" \
  --revision-suffix latest
```

---

## Exam gotchas

- **Scale to zero is NOT available on App Service** — only Container Apps and Functions support
  true scale-to-zero. App Service can stop/start but bills for reserved capacity.
- **KEDA is built into Container Apps** — you don't need to install it. It's automatic.
- **Every app with ingress gets HTTP scaling by default** — the `http` scaler is auto-added.
- **Jobs vs Apps** — Jobs run to completion; Apps are long-running. Don't confuse them.
- **Revisions are immutable** — you can't change a revision. Update the app to create a new revision.
- **Traffic splitting requires unique revision suffixes** — use `--revision-suffix` when deploying
  to enable traffic splitting later.
- **Managed identity for ACR** — grant the Container App's managed identity **AcrPull** on ACR.
  Use `--registry-identity system` for system-assigned identity.
- **Environment is the network boundary** — all apps in an environment share networking and can
  communicate via internal DNS (`<app-name>.<environment-name>.internal`).
- **Custom domains require TLS** — you can't have a custom domain without HTTPS.
- **KEDA poller is every 30 seconds by default** — scaling is not instant; expect 30-60 second delay
  for scale out/in.
- **Concurrency vs queue length** — the `http` scaler uses `concurrentRequests` (default 1); the
  `azure-queue` scaler uses `queueLength`. Know which applies to which trigger.
- **Maximum replicas is 30 by default** — can be increased to 100 per app.

---

## Quiz yourself

Take the **container-apps-keda** quiz in the [quiz app](../../quiz/)
(bank: [`quiz/src/questions/01-containers/container-apps-keda.json`](../../quiz/src/questions/01-containers/container-apps-keda.json)).

---

## Further reading

- Azure Container Apps overview: <https://learn.microsoft.com/azure/container-apps/>
- Container Apps vs other Azure container options: <https://learn.microsoft.com/azure/container-apps/compare-options>
- KEDA documentation: <https://keda.sh/docs/>
- KEDA scalers reference: <https://keda.sh/scalers/>
- Azure Container Apps YAML reference: <https://learn.microsoft.com/azure/container-apps/container-app-version-yaml>
- Container Apps networking: <https://learn.microsoft.com/azure/container-apps/networking>
- Container Apps authentication: <https://learn.microsoft.com/azure/container-apps/managed-identities>
