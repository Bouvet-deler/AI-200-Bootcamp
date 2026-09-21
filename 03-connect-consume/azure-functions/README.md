# Azure Functions

**Domain:** 03 — Connect to and consume Azure services (20–25%)
**Maps to skill:** *Build serverless APIs, including implementing triggers and bindings* ·
*Configure and deploy function apps*

---

## What it is

**Azure Functions** is Azure's **serverless compute** service — small pieces of code that run
**automatically in response to events** (triggers) and **scale dynamically** based on demand.
Azure manages the infrastructure. Consumption options meter on-demand executions; Premium,
Dedicated, and optional always-ready capacity also incur cost while capacity is allocated.

Think of a function as a **single-purpose micro-service**: it does **one thing** when **something
happens**. That "something" is a **trigger** — an HTTP request, a message in a queue, a file
uploaded to storage, a timer firing, or dozens of other Azure events.

**Input and output bindings** connect your function to other services without boilerplate code.
A binding is a declarative connection: "when this function runs, read this queue message as input,
write results to this database as output." You focus on the business logic; Azure handles the
plumbing.

> Mental model — each function chooses **one** trigger and can also have input/output bindings:
>
> ```
>          TRIGGER                                    OUTPUT BINDINGS
>      (exactly one —                              (zero or more — where
>       what starts it)                             the results are sent)
>
>   ┌────────────────────────┐                       ┌──────────────┐
>   │ ONE TRIGGER, for example│                  ┌───▶│  Cosmos DB   │
>   │ HTTP OR queue OR timer  │──▶┌────────────┐ │    └──────────────┘
>   └────────────────────────┘   │  Function  │─┤
>                                │ (your code)│ │    ┌──────────────┐
>                                └────────────┘ └───▶│    Queue     │
>                                       ▲            └──────────────┘
>                                  │
>                        ┌──────────────────┐
>                        │  INPUT BINDINGS  │
>                        │ (data read in —  │
>                        │  e.g. a blob,    │
>                        │  a Cosmos doc)   │
>                        └──────────────────┘
> ```

**Serverless** means:
- **No servers to manage** — Azure handles provisioning, scaling, patching
- **Consumption-based options** — on-demand executions are metered; always-ready or allocated
  instances add idle cost when you configure or choose them
- **Event-driven** — functions start automatically when triggered
- **Automatic scaling** — from zero to many instances based on workload

---

## Why it's on the exam

Azure Functions is a core service for **Connect to and consume Azure services**. The AI-200 exam
tests these competencies:

- **Building serverless APIs** — HTTP-triggered functions that act as REST endpoints
- **Implementing triggers** — HTTP, Queue, Timer, Blob, Service Bus, Event Grid, and more
- **Implementing bindings** — input/output connectors for Storage, Cosmos DB, etc.
- **Configuring and deploying function apps** — creating the Function App resource, configuring
  runtime, application settings, and deployment methods
- **Understanding hosting plans** — Consumption, Flex Consumption, Premium, Dedicated

Expect scenario questions like:
- "Which trigger should you use for processing files as they're uploaded?" → **Blob Storage trigger**
- "How do you read a queue message without writing connection code?" → **Queue trigger (binding)**
- "Your function must avoid idle cold starts. Which configuration?" → **Premium with an
  always-ready/prewarmed instance, Flex Consumption with an always-ready instance, or Dedicated
  with Always On**
- "How do you pass configuration to a deployed function?" → **Application settings** (read via
  `os.environ`)
- "Your function must reach a database behind a VNet. Which plan?" → **Flex Consumption, Premium,
  or Dedicated** (not classic Consumption)

You need to recognize Azure Functions as the answer for **event-driven, auto-scaling, pay-per-use
compute** scenarios.

---

## Core concepts

### 1. Function App — the container for your functions

A **Function App** is the Azure resource that hosts one or more **functions**. It's the deployment
unit and the thing you configure (runtime version, region, pricing plan, identity, etc.).

| Concept | What it is |
| --- | --- |
| **Function App** | The Azure resource (ARM resource) that contains your functions |
| **Function** | A single trigger + code unit (e.g., `HttpHello`, `QueueProcessor`) |
| **Host** | The runtime that loads your code, watches the triggers, and invokes your functions |

> One Function App can contain **multiple functions**, all sharing the same:
> - Runtime and language (all functions in one app must be the **same language**)
> - Application settings
> - Hosting plan
> - Region
> - Deployment unit and per-instance resources
>
> Scaling depends on the plan. Consumption and Premium add instances of the function host for the
> app (Premium capacity is allocated at the plan level). Flex Consumption uses **per-function
> scaling**: most triggers can scale independently, while all HTTP triggers form one scale group,
> all Blob (Event Grid) triggers form another, and all Durable Functions triggers form another.

### 2. Triggers — what starts your function

A **trigger** defines **when** your function runs. Every function has exactly **one trigger**.

| Trigger | When it fires | Common use cases |
| --- | --- | --- |
| **HTTP** | HTTP request (GET, POST, etc.) | REST APIs, webhooks, serverless backends |
| **Queue Storage** | New message in Azure Queue Storage | Background processing, decoupled tasks |
| **Blob Storage** | New or updated blob/file | File processing, image resizing, data import |
| **Timer** | Schedule (NCRONTAB expression) | Cleanup jobs, reports, periodic tasks |
| **Service Bus** | New message in Service Bus queue/topic | Enterprise messaging, reliable processing |
| **Event Grid** | Event Grid event | React to Azure service events (blob created, VM started) |
| **Event Hubs** | New events in Event Hubs | Stream processing, telemetry ingestion |
| **Cosmos DB** | Document changes (change feed) | Real-time database processing |
| **SignalR** | SignalR messages | Real-time communication |
| **IoT Hub** | IoT device messages | IoT data processing |

> **Exam gotcha:** A function has **exactly one trigger**, but may have **many input and output
> bindings**.

### 3. Bindings — declarative connections

A **binding** is a declarative connection to another service. Bindings **read input** or **write
output** without you writing connection code.

| Binding Type | Direction | Purpose | Example |
| --- | --- | --- | --- |
| **Trigger** | In (special) | Starts the function *and* supplies its data | Queue message → parameter |
| **Input binding** | In | Reads extra data into the function | Blob contents → parameter |
| **Output binding** | Out | Writes data out of the function | Return value → Cosmos DB document |

**Common bindings:**
- **Storage Blob** — read/write blobs
- **Storage Queue** — read/write queue messages
- **Storage Table** — read/write table entities
- **Cosmos DB** — read/write documents (NoSQL API)
- **Service Bus** — send messages to queues/topics (output only)
- **Event Hubs** — send events (output only)
- **SendGrid / Twilio** — send email / SMS
- **SignalR** — send real-time messages

> **Mental model for bindings:** instead of writing
> `client = QueueClient.from_connection_string(...)` followed by `client.send_message(...)`, you
> declare `@app.queue_output(...)` and the host does the connecting for you. Trigger and binding
> **connection settings are the *name* of an application setting**, never the connection string
> itself.

> **When you still need an SDK:** bindings cover the common "read one thing / write one thing"
> cases. Anything more (querying, transactions, listing blobs) needs the real SDK plus a client
> you construct yourself.

### 4. Hosting Plans — how your functions run

The **hosting plan** determines performance, scaling behavior, and cost.

| Plan | Scaling | Cost | Cold start | Timeout (default / max) | VNet |
| --- | --- | --- | --- | --- | --- |
| **Consumption (legacy)** | App-level, 0 → 200 Windows / 100 Linux instances | Execution-time metering | Possible | 5 min / 10 min | ✗ |
| **Flex Consumption** | Per-function groups, 0 → 1,000 on-demand instances per group | On-demand execution + optional always-ready instances | Improved; always-ready reduces it further | 30 min / unbounded | ✓ |
| **Premium** | Event-driven; capacity belongs to the plan | Allocated instances + executions | Avoided for covered workloads by prewarmed/always-ready instances | 30 min / unbounded | ✓ |
| **Dedicated (App Service Plan)** | Manual/App Service autoscale | Pay for allocated App Service instances | Not normally an issue with Always On | 30 min / unbounded with Always On | ✓ |

**Key differences:**
- **Consumption (legacy)** — scales to **zero**, so there is no function execution charge while
  idle, but the first request after idling can pay a **cold-start** delay. It has a hard
  **10-minute function timeout**. Linux Consumption is receiving no new features or language
  versions and retires on **30 September 2028**; use Flex Consumption for new Linux apps.
- **Flex Consumption** — the newer serverless plan. Still scales to zero, but adds **VNet
  integration**, optional **always-ready instances** to reduce cold starts, configurable
  per-instance concurrency, and per-function scaling groups.
- **Premium** — keeps prewarmed capacity and supports always-ready instances, VNet integration,
  and longer runs. At least one Premium instance is billed for the plan.
- **Dedicated** — runs on an App Service Plan you already pay for. Good for reusing spare capacity
  or when you need full App Service features. Requires **Always On** to keep non-HTTP triggers alive.

> **Exam gotchas:**
> - Classic **Consumption** is the one plan with a **hard 10-minute maximum** and **no VNet**.
> - **Always On** matters only on **Dedicated** — without it the app idles out and timer/queue
>   triggers stop firing.
> - Flex Consumption is the scaling exception: most triggers scale independently in function
>   groups. HTTP, Blob (Event Grid), and Durable Functions triggers each scale with their own
>   respective group.
> - Even on a plan with an unbounded function timeout, an HTTP-triggered response is still
>   limited to about **230 seconds** by the Azure Load Balancer idle timeout. Return quickly and
>   move longer work behind a queue or use the Durable Functions asynchronous pattern.

### 5. Project structure — the v2 programming model

Python has **two** programming models. Since 2023 the default (and what you should learn) is **v2**.

**v2 — decorators, with an app entry point** (used by the sample in this folder):

```
azure-functions/
├── function_app.py         # Creates `app`; functions may live here or in registered blueprints
├── feature_blueprint.py    # Optional: decorators registered on a Blueprint for modular apps
├── host.json               # Global configuration for the whole app
├── local.settings.example.json # Safe committed template; copy it to the ignored local.settings.json
├── requirements.txt        # Python dependencies
└── .funcignore             # Files to exclude from deployment
```

**v1 — a folder per function** (legacy; you'll still meet it in older code and exam questions):

```
azure-functions/
├── host.json
├── local.settings.json
├── requirements.txt
├── HttpExample/
│   ├── __init__.py         # must expose a function called `main`
│   └── function.json       # trigger + bindings, declared as JSON
└── QueueExample/
    ├── __init__.py
    └── function.json
```

| File | Purpose |
| --- | --- |
| `function_app.py` | **v2**: creates the app and defines functions and/or registers blueprints |
| Blueprint module | **v2, optional**: groups decorated functions in another Python file |
| `function.json` | **v1 only**: trigger and bindings for one function, as JSON |
| `host.json` | Global settings for all functions: version, extension bundle, logging, retries, timeout |
| `local.settings.example.json` | Safe committed template for local settings; it contains emulator-only values |
| `local.settings.json` | Local-only settings derived from the template; ignored by Git and excluded from normal deployment |
| `requirements.txt` | pip dependencies — anything missing here is missing in Azure |
| `.funcignore` | Excludes files from the deployment package |

> **Exam gotcha:** pay attention to the programming model named in the question. In Python v1,
> **`function.json`** configures one function. In Python v2, decorators in `function_app.py` or a
> registered blueprint provide the binding metadata; you don't author a `function.json` file.

> Keep one programming model per project. For a v1-to-v2 migration, convert each function's
> `function.json` metadata to decorators and test function discovery before removing the old
> layout. Avoid relying on undocumented behavior from a mixed layout.

### 6. Key Python decorators (v2)

```python
import azure.functions as func

# ONE FunctionApp object for the whole app, at module level in function_app.py
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# HTTP trigger — the URL becomes /api/hello
@app.function_name(name="HttpExample")
@app.route(route="hello", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def http_example(req: func.HttpRequest) -> func.HttpResponse: ...

# Queue trigger — `connection` is the NAME of an app setting
@app.function_name(name="QueueExample")
@app.queue_trigger(arg_name="msg", queue_name="myqueue", connection="StorageConnection")
def queue_example(msg: func.QueueMessage) -> None: ...

# Timer trigger — six-field NCRONTAB: {sec} {min} {hour} {day} {month} {day-of-week}
@app.function_name(name="TimerExample")
@app.timer_trigger(arg_name="timer", schedule="0 */5 * * * *")
def timer_example(timer: func.TimerRequest) -> None: ...

# Blob trigger
@app.function_name(name="BlobExample")
@app.blob_trigger(arg_name="blob", path="uploads/{name}", connection="StorageConnection")
def blob_example(blob: func.InputStream) -> None: ...

# Output binding — added on top of any trigger
@app.queue_output(arg_name="out", queue_name="results", connection="StorageConnection")
```

> There is **no** `@app.authorization_level(...)` decorator. Auth level is a **parameter**:
> either `func.FunctionApp(http_auth_level=...)` for the app-wide default, or `auth_level=...` on
> the individual `@app.route(...)`.

---

## Setup

Goal: create a Function App (plus the Storage account it requires) and deploy a Python function to
it.

**Prerequisites:** an Azure subscription, Azure CLI, `az login`, and permission to create resources
and role assignments. The role assignment in this walkthrough can take several minutes to become
effective.

**Region and shell:** the examples use `westeurope` and **bash** syntax. Azure Cloud Shell's Bash
mode is the simplest copy-paste environment. Choose another region only after confirming that it
supports the selected plan and Python version.

> **Three methods — pick one:**
> - **[CLI](#cli-setup)** — copy-paste commands (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal](#portal-setup-web-ui)** — point-and-click in the browser
> - **[VS Code](#vs-code-setup)** — the Azure Functions extension

### Set your variables

The CLI commands in **Setup** and **Cleanup** reference these as bash variables — set them once,
then run the `az` commands in the same shell session.

- **`RG`** — resource group
- **`LOCATION`** — Azure region
- **`STORAGE`** — Storage account name (required for Functions — globally unique, 3–24 chars,
  lowercase letters and digits only)
- **`FUNCTIONAPP`** — Function App name (globally unique — it becomes `<name>.azurewebsites.net`)
- **`PYTHON_VERSION`** — Python runtime version (this guide uses `3.12`)

```bash
# bash / zsh, including Azure Cloud Shell in Bash mode
RG="ai200-func-rg"
LOCATION="westeurope"
STORAGE="ai200funcsa$(date +%s)"   # timestamp keeps the name unique
FUNCTIONAPP="ai200-func-$(date +%s)"
PYTHON_VERSION="3.12"
```

```powershell
# PowerShell - Windows (also cross-platform)
$timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$RG = "ai200-func-rg"
$LOCATION = "westeurope"
$STORAGE = "ai200funcsa$timestamp"
$FUNCTIONAPP = "ai200-func-$timestamp"
$PYTHON_VERSION = "3.12"
```

```bat
:: Command Prompt (cmd.exe) - Windows
set RG=ai200-func-rg
set LOCATION=westeurope
set STORAGE=ai200funcsa%RANDOM%%RANDOM%
set FUNCTIONAPP=ai200-func-%RANDOM%%RANDOM%
set PYTHON_VERSION=3.12
```

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first), after
[setting your variables](#set-your-variables) above.

```bash
# 1. Create the resource group
az group create --name "$RG" --location "$LOCATION"

# 2. Create a Storage account — REQUIRED for every Function App.
#    Functions uses it for host state and keys, and some plans/features also use it for
#    deployment artifacts, diagnostic data, or Durable Functions state.
#    The name must be globally unique across all of Azure.
az storage account create \
  --name "$STORAGE" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2

# 3. Create the Function App on Flex Consumption, the recommended serverless plan for new
#    Linux apps. --flexconsumption-location both selects the plan and sets its region.
#    `az functionapp create` has no general --location parameter: use
#    --flexconsumption-location (Flex), --consumption-plan-location (legacy Consumption),
#    or --plan (Premium / Dedicated).
#    --functions-version 4: the current runtime major version.
#    Flex Consumption is Linux-only, and Python Functions run on Linux.
az functionapp create \
  --name "$FUNCTIONAPP" \
  --resource-group "$RG" \
  --flexconsumption-location "$LOCATION" \
  --storage-account "$STORAGE" \
  --functions-version 4 \
  --runtime python \
  --runtime-version "$PYTHON_VERSION"

# 4. Give the Function App a system-assigned managed identity, then authorize that identity to
#    send, receive, and delete queue messages for this two-way queue-binding demo.
#    The role ID is Storage Queue Data Contributor. Scope it to the one Storage account.
FUNCTION_PRINCIPAL_ID=$(az functionapp identity assign \
  --name "$FUNCTIONAPP" \
  --resource-group "$RG" \
  --query principalId \
  --output tsv)
STORAGE_ID=$(az storage account show \
  --name "$STORAGE" \
  --resource-group "$RG" \
  --query id \
  --output tsv)

az role assignment create \
  --assignee-object-id "$FUNCTION_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "974c5e8b-45b9-4653-ba55-5f855dd0fb88" \
  --scope "$STORAGE_ID"

# 5. Configure an identity-based binding connection. `StorageConnection` in the decorator is a
#    setting PREFIX, so the host combines the double-underscore settings below. `queueServiceUri`
#    is valid for any named Queue Storage connection; `accountName` is a special shortcut only for
#    AzureWebJobsStorage and must not be used here.
STORAGE_QUEUE_URI="https://${STORAGE}.queue.core.windows.net"

az functionapp config appsettings set \
  --name "$FUNCTIONAPP" \
  --resource-group "$RG" \
  --settings \
    "StorageConnection__queueServiceUri=$STORAGE_QUEUE_URI" \
    "StorageConnection__credential=managedidentity" \
    "APP_ENVIRONMENT=azure"

# 6. Get the Function App URL
az functionapp show --name "$FUNCTIONAPP" --resource-group "$RG" \
  --query "defaultHostName" --output tsv
```

**Legacy Consumption plan** (shown because it still appears in existing deployments and exam
questions; don't choose it for a new Linux app):

```bash
az functionapp create \
  --name "$FUNCTIONAPP" \
  --resource-group "$RG" \
  --consumption-plan-location "$LOCATION" \
  --storage-account "$STORAGE" \
  --functions-version 4 \
  --runtime python \
  --runtime-version "$PYTHON_VERSION" \
  --os-type Linux
```

> Linux Consumption supports Python only through 3.12 and retires on 30 September 2028. The
> `3.12` value used here is compatible, but Flex Consumption is the current choice for new apps.

**Optional: Premium plan** (pre-warmed instances, VNet, longer timeouts):

```bash
# Create the Premium plan (EP1/EP2/EP3 are the Elastic Premium SKUs)
az functionapp plan create \
  --name "ai200-premium-plan" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku EP1 \
  --is-linux

# Create the Function App on that plan — note --plan replaces --consumption-plan-location
az functionapp create \
  --name "$FUNCTIONAPP" \
  --resource-group "$RG" \
  --plan "ai200-premium-plan" \
  --storage-account "$STORAGE" \
  --functions-version 4 \
  --runtime python \
  --runtime-version "$PYTHON_VERSION"
```

**Optional: Dedicated plan** (an ordinary App Service Plan):

```bash
az appservice plan create \
  --name "ai200-asp" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku S1 \
  --is-linux

az functionapp create \
  --name "$FUNCTIONAPP" \
  --resource-group "$RG" \
  --plan "ai200-asp" \
  --storage-account "$STORAGE" \
  --functions-version 4 \
  --runtime python \
  --runtime-version "$PYTHON_VERSION"

# On Dedicated, turn on Always On so timer and queue triggers keep firing when idle
az functionapp config set --name "$FUNCTIONAPP" --resource-group "$RG" --always-on true
```

### Portal Setup (Web UI)

Prefer the browser? Create the same resources in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Create the Resource Group:**
   - Click **Resource groups** → **+ Create**
   - Subscription: your subscription
   - Resource group: `ai200-func-rg`
   - Region: `West Europe` (or your preference)
   - Click **Review + create** → **Create**

3. **Create the Function App:**
   - Click **+ Create a resource** → search for "Function App" → **Create**
   - You are first asked to **select a hosting plan**. Pick:
     - **Flex Consumption** — the recommended serverless plan for a new Linux/Python app
     - *(Premium, App Service, Container Apps, and legacy Consumption are the other options)*
   - Click **Select** to continue to the **Basics** tab

   **Basics tab:**
   - Subscription: your subscription
   - Resource group: `ai200-func-rg`
   - Function App name: `ai200-func-<something-unique>` (becomes `<name>.azurewebsites.net`)
   - Do you want to deploy code or container image?: **Code**
   - Runtime stack: **Python**
   - Version: **3.12**
   - Region: `West Europe`
   - Operating System: **Linux** (the only option for Python)
   - Click **Next: Storage >**

   **Storage tab:**
   - Storage account: accept the auto-generated name, or **Create new** →
     `ai200funcsa<something-unique>` (lowercase letters and digits only, 3–24 chars)
   - This account is **mandatory** — Functions keeps host state and keys there; selected plans and
     features also use it for deployment artifacts, diagnostic data, or Durable Functions state
   - Click **Next: Networking >**

   **Networking tab:**
   - Enable public access: **On** (so you can call the HTTP function from your machine)
   - Enable virtual network integration: **Off** for this public learning sample. Flex Consumption
     supports VNet integration when the connected resources require private access.
   - Click **Next: Monitoring >**

   **Monitoring tab:**
   - Enable Application Insights: **Yes** (recommended — this is what makes the *Logs*/KQL
     experience work later; see the [KQL topic](../../04-secure-monitor/kql/README.md))
   - Application Insights: accept the new resource it offers to create
   - Click **Next: Deployment >**

   **Deployment tab:**
   - Continuous deployment: **Disable** (we deploy from the CLI in the hands-on below)
   - Click **Review + create** → **Create**
   - Deployment takes 1–3 minutes. Click **Go to resource** when it finishes.

4. **Enable passwordless access for the queue bindings** (the equivalent of CLI steps 4–5):
   - Open the Function App → **Settings** → **Identity** → **System assigned** → set **Status** to
     **On** → **Save**
   - Open the Storage account → **Access control (IAM)** → **Add role assignment**
   - Select **Storage Queue Data Contributor**, choose **Managed identity**, and select this
     Function App. This lab role covers both the output binding and trigger; a production app should
     use narrower sender/processor roles when its functions do not need both directions.
   - Open your Function App → **Settings** → **Environment variables** → **App settings** tab
   - Add `StorageConnection__queueServiceUri` with value
     `https://<storage-account>.queue.core.windows.net`
   - Add `StorageConnection__credential` with value `managedidentity`
   - Add `APP_ENVIRONMENT` with value `azure`
   - Click **Apply** → **Confirm**. The app restarts.

   > The binding treats `StorageConnection` as the prefix of this identity-based setting
   > collection. It does not need a Storage access key. `APP_ENVIRONMENT` is the ordinary value
   > read by `os.environ.get("APP_ENVIRONMENT")`.
   > `local.settings.json` is the **local** stand-in for this screen and is never deployed.
   > Role assignments can take several minutes to propagate; retry after a short wait if the host
   > initially reports authorization failure.

5. **Find things later, in your Function App:**

   | You want to… | Go to |
   | --- | --- |
   | See the deployed functions | **Overview** → *Functions* tab |
   | Get a function's URL and keys | Click the function → **Get Function Url** |
   | Read/write app settings | **Settings** → **Environment variables** |
   | Watch live logs | Click the function → **Monitor** → *Logs* (or **Log stream**) |
   | Query telemetry with KQL | **Application Insights** → **Logs** |
   | Change the hosting plan | **Settings** → **Scale up (App Service plan)** |
   | Enable managed identity | **Settings** → **Identity** |

> **Portal limitation worth knowing:** in-portal editing is unavailable on Flex Consumption and
> becomes read-only after you deploy this project from Core Tools or another external source.
> Python portal editing exists only for supported plan/app combinations created and kept in the
> portal, and it doesn't support custom packages. Local development plus deployment is the
> recommended path for this sample.

### VS Code Setup

1. Install [VS Code](https://code.visualstudio.com/)
2. Install the [Azure Functions extension](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions)
3. Install the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
4. Sign in to Azure (Azure icon in the sidebar → **Sign in to Azure**)
5. `Ctrl+Shift+P` (`Cmd+Shift+P` on macOS) → **Azure Functions: Create New Project**
6. Choose a folder → language **Python** → **Model V2** → a template (e.g. *HTTP trigger*) →
   a function name → auth level **FUNCTION**
7. To deploy: `Ctrl+Shift+P` → **Azure Functions: Deploy to Function App**

---

## Cleanup

Goal: delete everything created during setup so you stop paying for it.

### CLI Cleanup

```bash
# Delete the entire resource group and everything in it:
# Function App, Storage account, App Service Plan, Application Insights.
az group delete --name "$RG" --yes --no-wait

# Verify it is gone (it disappears from the list once deletion completes)
az group list --output table
```

> **Important:** resource-group deletion is destructive and has no general undo. Review the
> resource list before confirming; any service-specific recovery depends on protections that were
> configured for that individual resource.

### Portal Cleanup (Web UI)

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)
2. Click **Resource groups** in the left menu
3. Click your resource group (`ai200-func-rg`)
4. Click **Delete resource group** at the top
5. Type the resource group name to confirm → **Delete**

   This deletes **all resources** in the group in one operation.

---

## Hands-on (Python)

This folder is a **complete, runnable** function app using the **v2 programming model**, with three
functions that form a chain:

```
POST /api/hello ──▶ HttpHello ──(queue output binding)──▶ "demo-queue" ──▶ QueueProcessor
                                 TimerCleanup fires every 5 minutes on its own
```

The code is in [`function_app.py`](./function_app.py) and every non-trivial line is commented —
explaining both the Python idiom and the Azure concept.

> **Remember:** run all commands below from this folder
> (`03-connect-consume/azure-functions/`).

### Prerequisites

- [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local?tabs=v4)
  (use a current 4.x release; current Microsoft quickstarts require 4.12 or later)
- A currently supported Python version, **3.10–3.14** as of August 2026. The local version must
  match the Function App runtime; this walkthrough uses 3.12. Linux Consumption stops at 3.12,
  while Flex Consumption supports newer versions.
- [Azurite](https://learn.microsoft.com/azure/storage/common/storage-use-azurite) — the local
  Storage emulator, so you can run the queue functions without touching Azure

```bash
# Core Tools (cross-platform, via npm)
npm install -g azure-functions-core-tools@4 --unsafe-perm true
func --version           # expect 4.x

# Azurite, the local Storage emulator
npm install -g azurite
```

### 1. Create the virtual environment

A **virtual environment** is a private folder of Python packages for this project only. Activating
it makes `python` and `pip` use that folder instead of packages installed for the whole machine.

```bash
# Create it (the folder is named .venv and is gitignored)
python -m venv .venv

# Activate it — the prompt changes to show (.venv)
# --- bash / zsh (Linux, macOS) ---
source .venv/bin/activate
# --- fish ---
source .venv/bin/activate.fish
# --- Windows PowerShell ---
.\.venv\Scripts\Activate.ps1
# --- Windows cmd ---
.venv\Scripts\activate.bat
```

### 2. Install dependencies

```bash
# -r reads the package list from the file, rather than naming one package
pip install -r requirements.txt
```

### 3. Create `local.settings.json` from the safe template

`local.settings.json` can hold secrets, so Git ignores it. Create your local copy from the
committed emulator-only template:

```bash
cp local.settings.example.json local.settings.json
```

The template contains:

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "StorageConnection": "UseDevelopmentStorage=true",
    "APP_ENVIRONMENT": "local"
  }
}
```

`UseDevelopmentStorage=true` is the magic value that points at **Azurite** running locally. If you
intentionally test against a real Storage account, inject its connection string only into the
current shell rather than editing the template or local file:

```bash
export AzureWebJobsStorage="$(az storage account show-connection-string \
  --name "$STORAGE" --resource-group "$RG" --query connectionString --output tsv)"
export StorageConnection="$AzureWebJobsStorage"
```

Those values are secrets and disappear when that shell closes. Prefer Azurite for this walkthrough.

### 4. Run locally

```bash
# Terminal 1 — start the storage emulator
azurite --silent --location ./.azurite

# Terminal 2 — start the Functions host (with .venv activated)
func start
```

`func start` prints the functions it found. You should see all three:

```
Functions:
        HttpHello: [GET,POST] http://localhost:7071/api/hello
        QueueProcessor: queueTrigger
        TimerCleanup: timerTrigger
```

> If the list is **empty**, the host failed to index `function_app.py` — almost always an import
> error or a syntax error in that file. Scroll up in the output for the Python traceback.

### 5. Call it

```bash
# GET with a query-string parameter.
# Quote the URL — an unquoted & would background the command in bash.
curl "http://localhost:7071/api/hello?name=Azure"

# POST with a JSON body
curl -X POST "http://localhost:7071/api/hello" \
  -H "Content-Type: application/json" \
  -d '{"name": "Frank"}'
```

Note the URL is `/api/hello` — the **route**, not the function name. Core Tools disables key
enforcement locally unless you start it with `--enableAuth`, so these local calls don't need
`?code=` even though the route uses `AuthLevel.FUNCTION`. Azure enforces the key after deployment.

Watch the *Terminal 2* logs: `HttpHello` runs, writes to `demo-queue` via its output binding, and a
second later `QueueProcessor` picks the message up. That's a trigger and an output binding working
together, with no connection code in your source.

### 6. Deploy to Azure

```bash
# Publishes the code. It does NOT publish local.settings.json by default; the Azure settings were
# created in CLI Setup step 4. Only opt in to --publish-local-settings after checking for secrets.
# Core Tools builds the dependencies remotely for the Linux runtime.
func azure functionapp publish "$FUNCTIONAPP"
```

Then call the deployed function:

```bash
# Read the function-specific key without printing it, then send it in a header. Keep the value
# secret: a function key authorizes calls but does not identify the caller.
FUNCTION_KEY=$(az functionapp function keys list \
  --name "$FUNCTIONAPP" \
  --resource-group "$RG" \
  --function-name "HttpHello" \
  --query default \
  --output tsv)

curl "https://$FUNCTIONAPP.azurewebsites.net/api/hello?name=Azure" \
  --header "x-functions-key: $FUNCTION_KEY"
```

> If the deployed app returns 404, check the **Overview → Functions** tab in the portal. An empty
> list means indexing failed in Azure — usually a package in `requirements.txt` that didn't install.
> Check **Log stream** or the deployment logs.

### Starting a project from scratch

For reference, this is how the folder was created (you don't need to run it — the files are
already here):

```bash
# --model V2 selects the decorator-based programming model
func init --worker-runtime python --model V2

# Add functions to function_app.py (it appends, it does not create folders)
func new --name HttpHello --template "HTTP trigger" --authlevel function
func new --name QueueProcessor --template "Azure Queue Storage trigger"
func new --name TimerCleanup --template "Timer trigger"
```

---

## Exam gotchas

- **One trigger per function.** Multiple input and output bindings are fine; two triggers are not.

- **Binding `connection` is a setting *name*.** `connection="StorageConnection"` means "look up the
  app setting called StorageConnection", not "connect to a service called StorageConnection".
  Putting a raw connection string there is a classic wrong answer.

- **Every Function App requires a Storage account** — even one with only HTTP triggers. The host
  uses it for state and keys; plans and extensions can additionally use it for deployment content,
  diagnostic data, or Durable Functions state. Application telemetry belongs in Application
  Insights, not generically in this account.

- **Application settings are environment variables.** Read them with `os.environ.get("Name")`.
  `local.settings.json` is the local equivalent and is excluded from normal deployment. Core Tools
  can publish its values only when you explicitly request that behavior. This repository tracks
  only an emulator-only `.example` template; never place a real secret in any tracked file.

- **Timeouts:** Consumption defaults to **5 minutes**, max **10** (`functionTimeout` in
  `host.json`). Flex Consumption and Premium default to **30 minutes** and are unbounded; Dedicated
  is unbounded only with Always On. HTTP responses still face the platform's roughly **230-second**
  load-balancer timeout, independent of `functionTimeout`.

- **VNet integration:** available on **Flex Consumption, Premium, and Dedicated**. *Not* on the
  classic Consumption plan.

- **Cold starts:** Consumption scales to zero, so the first call after idle pays a cold start.
  Premium keeps pre-warmed instances; Flex Consumption offers always-ready instances; Dedicated
  with Always On never idles.

- **Always On** is a **Dedicated-plan** setting. Without it, an idle app is unloaded and timer and
  queue triggers stop firing. It doesn't exist (and isn't needed) on Consumption/Premium.

- **Scaling depends on the plan.** Consumption scales a function app; Premium capacity is managed
  at the plan level. Flex Consumption uses per-function scale groups, with HTTP, Blob (Event Grid),
  and Durable triggers grouped as described above. Functions in one app still deploy together and
  share language and settings.

- **`host.json` vs `function.json`:** `host.json` configures **all** functions in the app
  (timeout, retries, logging, extension bundle). `function.json` configures **one** function
  (trigger + bindings) — and exists only in the **v1** model. In v2 Python, decorators replace it.

- **v2 model rules:** `function_app.py` exposes the app entry point. Small apps can define every
  decorated function there; larger apps can register `Blueprint` objects from other modules.
  Import/indexing errors can leave the app with no discovered functions and make HTTP routes return
  **404**, so inspect host logs when the function list is empty.

- **Poison messages:** a queue-triggered function that keeps throwing is retried
  **`maxDequeueCount`** times (default **5**), then the message is moved to
  `<queue-name>-poison`.

- **Queue message deletion is automatic** — on success the host deletes it; on an exception it
  stays for retry. Don't write manual delete code.

- **NCRONTAB accepts five or six fields.** This guide uses the six-field form
  `{second} {minute} {hour} {day} {month} {day-of-week}` when it needs to name a second. A five-field
  expression omits seconds, so `*/5 * * * *` and `0 */5 * * * *` both run every five minutes.
  Timers use **UTC** by default. `WEBSITE_TIME_ZONE` is supported on Windows plans and Linux
  Premium/Dedicated, but **not** on Linux Flex Consumption or Linux Consumption; write this
  walkthrough's schedule in UTC.

- **HTTP auth levels:** `anonymous` (no key), `function` (function or host key), `admin` (master
  key). Keys go in `?code=` or the `x-functions-key` header. Keys are **not** identity — use
  Microsoft Entra ID / managed identity for real authentication.

- **Route ≠ function name.** `@app.route(route="hello")` is reachable at `/api/hello` regardless of
  what the function or the Python method is called. The `/api` prefix is configurable via
  `extensions.http.routePrefix` in `host.json`.

- **Dependencies:** anything not in `requirements.txt` is missing in Azure, and the app usually
  fails to index rather than failing loudly at the call site.

- **Durable Functions** is the answer for stateful, multi-step orchestration (fan-out/fan-in,
  human approval, long-running workflows). It requires the Storage account.

- **Managed identity** is the recommended way to reach other Azure services. For this named Queue
  Storage binding, `connection="StorageConnection"` resolves the prefix
  `StorageConnection__queueServiceUri` plus `StorageConnection__credential`. The
  `__accountName` shortcut applies only to `AzureWebJobsStorage`, not arbitrary named binding
  connections. Grant the function identity the required Storage data role as well.

- **Application Insights** must be connected for the *Monitor* blade and KQL queries to show
  anything.

---

## Quiz yourself

Take the **Azure Functions** quiz in the [quiz app](../../quiz/)
(bank: [`quiz/src/questions/03-connect-consume/azure-functions.json`](../../quiz/src/questions/03-connect-consume/azure-functions.json)).

---

## Further reading

- Azure Functions overview: <https://learn.microsoft.com/azure/azure-functions/functions-overview>
- Python developer guide: <https://learn.microsoft.com/azure/azure-functions/functions-reference-python>
- Supported runtime and Python versions: <https://learn.microsoft.com/azure/azure-functions/functions-versions>
- v2 programming model: <https://learn.microsoft.com/azure/azure-functions/functions-reference-python?pivots=python-mode-decorators>
- Triggers and bindings: <https://learn.microsoft.com/azure/azure-functions/functions-triggers-bindings?tabs=python>
- HTTP bindings: <https://learn.microsoft.com/azure/azure-functions/functions-bindings-http-webhook?tabs=python>
- Queue Storage bindings: <https://learn.microsoft.com/azure/azure-functions/functions-bindings-storage-queue?tabs=python>
- Timer bindings: <https://learn.microsoft.com/azure/azure-functions/functions-bindings-timer?tabs=python>
- Hosting plans compared: <https://learn.microsoft.com/azure/azure-functions/functions-scale>
- Flex Consumption plan: <https://learn.microsoft.com/azure/azure-functions/flex-consumption-plan>
- Portal development limitations: <https://learn.microsoft.com/azure/azure-functions/functions-how-to-use-azure-function-app-settings#development-limitations-in-the-azure-portal>
- `host.json` reference: <https://learn.microsoft.com/azure/azure-functions/functions-host-json>
- Identity-based connections: <https://learn.microsoft.com/azure/azure-functions/functions-reference#configure-an-identity-based-connection>
- Durable Functions: <https://learn.microsoft.com/azure/azure-functions/durable/durable-functions-overview?tabs=python>
