# Azure Functions

**Domain:** 03 — Connect to and consume Azure services (20–25%)
**Maps to skill:** *Build serverless APIs, including implementing triggers and bindings* ·
*Configure and deploy function apps* · *Implement input and output bindings*

---

## What it is

**Azure Functions** is Azure's **serverless compute** service — small pieces of code that run
**automatically in response to events** (triggers) and **scale dynamically** based on demand.
You pay only for the time your code executes, and Azure manages all the infrastructure.

Think of a function as a **single-purpose micro-service**: it does **one thing** when **something
happens**. That "something" is a **trigger** — an HTTP request, a message in a queue, a file
uploaded to storage, a timer firing, or dozens of other Azure events.

**Input and output bindings** connect your function to other services without boilerplate code.
A binding is a declarative connection: "when this function runs, read this queue message as input,
write results to this database as output." You focus on the business logic; Azure handles the
plumbing.

> Mental model — the function sits between **one** trigger and **any number** of bindings:
>
> ```
>          TRIGGER                                    OUTPUT BINDINGS
>      (exactly one —                              (zero or more — where
>       what starts it)                             the results are sent)
>
>   ┌──────────────┐                                  ┌──────────────┐
>   │ HTTP request │──┐                          ┌───▶│  Cosmos DB   │
>   └──────────────┘  │   ┌──────────────────┐   │    └──────────────┘
>                     ├──▶│  Azure Function  │───┤
>   ┌──────────────┐  │   │   (your code)    │   │    ┌──────────────┐
>   │ Queue message│──┘   └──────────────────┘   └───▶│    Queue     │
>   └──────────────┘               ▲                  └──────────────┘
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
- **Pay-per-use** — billed only while code runs (Consumption/Flex) or per allocated instance (Premium)
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
- "Your function must always be warm. Which plan?" → **Premium or Dedicated** (not Consumption)
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
> - Scaling — instances scale the **whole app**, not individual functions

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
| **Consumption** | 0 → 200 instances (100 on Linux) | Pay per execution | Possible | 5 min / 10 min | ✗ |
| **Flex Consumption** | 0 → many, per-instance concurrency | Pay per execution + always-ready instances | Reduced (always-ready) | 30 min / unlimited | ✓ |
| **Premium** | 1 → 100 instances, pre-warmed | Instance time + executions | Minimal | 30 min / unlimited | ✓ |
| **Dedicated (App Service Plan)** | Fixed / autoscale VMs | Pay for the VMs, always | None (with Always On) | 30 min / unlimited | ✓ |

**Key differences:**
- **Consumption** — the classic serverless plan. Scales to **zero**, so you pay nothing when idle,
  but a first request after idling pays a **cold start**. Hard **10-minute ceiling**.
- **Flex Consumption** — the newer serverless plan. Still scales to zero, but adds **VNet
  integration**, **always-ready instances** to blunt cold starts, and per-instance concurrency
  control.
- **Premium** — always at least one warm instance, so no cold starts, plus VNet and longer runs.
  You pay for that instance even when nothing is running.
- **Dedicated** — runs on an App Service Plan you already pay for. Good for reusing spare capacity
  or when you need full App Service features. Requires **Always On** to keep non-HTTP triggers alive.

> **Exam gotchas:**
> - Classic **Consumption** is the one plan with a **hard 10-minute maximum** and **no VNet**.
> - **Always On** matters only on **Dedicated** — without it the app idles out and timer/queue
>   triggers stop firing.
> - Scaling applies to the **whole Function App**, not to a single function.

### 5. Project structure — the v2 programming model

Python has **two** programming models. Since 2023 the default (and what you should learn) is **v2**.

**v2 — decorators, one file** (used by the sample in this folder):

```
azure-functions/
├── function_app.py         # ALL functions live here, registered on one `app` object
├── host.json               # Global configuration for the whole app
├── local.settings.json     # Local-only settings — NOT deployed, gitignored
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
| `function_app.py` | **v2**: every function, defined with decorators |
| `function.json` | **v1 only**: trigger and bindings for one function, as JSON |
| `host.json` | Global settings for all functions: version, extension bundle, logging, retries, timeout |
| `local.settings.json` | Local-only settings and connection strings — **never deployed**, never committed |
| `requirements.txt` | pip dependencies — anything missing here is missing in Azure |
| `.funcignore` | Excludes files from the deployment package |

> **Exam gotcha:** exam questions still ask "which file configures a single function's trigger and
> bindings?" — the expected answer is **`function.json`**, because that question predates v2. In v2
> Python there is no `function.json`; the decorators generate it at build time. Know both.

> **Don't mix the models.** A project cannot use decorators *and* `function.json` folders. If a
> `function.json` exists alongside `function_app.py`, the host gets confused about which functions
> to index and typically loads none of them.

### 6. Key Python decorators (v2)

```python
import azure.functions as func

# ONE FunctionApp object for the whole app, at module level in function_app.py
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# HTTP trigger — the URL becomes /api/hello
@app.function_name(name="HttpExample")
@app.route(route="hello", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
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

> **Three methods — pick one:**
> - **[CLI](#cli-setup)** — copy-paste commands (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal](#portal-setup-web-ui)** — point-and-click in the browser
> - **[VS Code](#vs-code-setup)** — the Azure Functions extension

### Set your variables

The CLI commands in **Setup** and **Cleanup** reference these as **shell variables** — set them
once for your shell, then run the `az` commands as written.

- **`RG`** — resource group
- **`LOCATION`** — Azure region
- **`STORAGE`** — Storage account name (required for Functions — globally unique, 3–24 chars,
  lowercase letters and digits only)
- **`FUNCTIONAPP`** — Function App name (globally unique — it becomes `<name>.azurewebsites.net`)
- **`PYTHON_VERSION`** — Python runtime version (e.g. `3.11`)

Copy the block that matches your shell:

```bash
# bash / zsh — Linux, and macOS (its default shell)
RG="ai200-func-rg"
LOCATION="westeurope"
STORAGE="ai200funcsa$(date +%s)"   # timestamp keeps the name unique
FUNCTIONAPP="ai200-func-$(date +%s)"
PYTHON_VERSION="3.11"
```

```fish
# fish — Linux / macOS
set RG ai200-func-rg
set LOCATION westeurope
set STORAGE ai200funcsa(date +%s)
set FUNCTIONAPP ai200-func-(date +%s)
set PYTHON_VERSION 3.11
```

```powershell
# PowerShell — Windows (also cross-platform)
$RG = "ai200-func-rg"
$LOCATION = "westeurope"
$STORAGE = "ai200funcsa$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
$FUNCTIONAPP = "ai200-func-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
$PYTHON_VERSION = "3.11"
```

> **Referencing variables:** the `az` snippets use bash-style `"$RG"`, which also works in fish and
> PowerShell. In **cmd** use `%RG%` instead. The trailing `\` on long commands is a *bash*
> line-continuation — in PowerShell use a backtick `` ` ``, in cmd use `^`, or put the command on
> one line.

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first), after
[setting your variables](#set-your-variables) above.

```bash
# 1. Create the resource group
az group create --name "$RG" --location "$LOCATION"

# 2. Create a Storage account — REQUIRED for every Function App.
#    Used for trigger state, function keys, logs, and Durable Functions state.
#    The name must be globally unique across all of Azure.
az storage account create \
  --name "$STORAGE" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2

# 3. Create the Function App on the Consumption plan (serverless, pay-per-use).
#    --consumption-plan-location: this BOTH selects the Consumption plan AND sets the
#      region. `az functionapp create` has NO --location parameter: you pass either
#      --consumption-plan-location (Consumption), --flexconsumption-location (Flex),
#      or --plan (Premium / Dedicated).
#    --functions-version 4: the current runtime major version.
#    --os-type Linux: required for Python.
az functionapp create \
  --name "$FUNCTIONAPP" \
  --resource-group "$RG" \
  --consumption-plan-location "$LOCATION" \
  --storage-account "$STORAGE" \
  --functions-version 4 \
  --runtime python \
  --runtime-version "$PYTHON_VERSION" \
  --os-type Linux

# 4. Add the application settings your functions read.
#    These become environment variables inside the running function.
#    The queue binding looks for a setting NAMED "StorageConnection".
STORAGE_CONN=$(az storage account show-connection-string \
  --name "$STORAGE" --resource-group "$RG" --query connectionString --output tsv)

az functionapp config appsettings set \
  --name "$FUNCTIONAPP" \
  --resource-group "$RG" \
  --settings "StorageConnection=$STORAGE_CONN" "APP_ENVIRONMENT=azure"

# 5. Get the Function App URL
az functionapp show --name "$FUNCTIONAPP" --resource-group "$RG" \
  --query "defaultHostName" --output tsv
```

**Optional: Flex Consumption plan** (serverless *with* VNet support and always-ready instances):

```bash
az functionapp create \
  --name "$FUNCTIONAPP" \
  --resource-group "$RG" \
  --flexconsumption-location "$LOCATION" \
  --storage-account "$STORAGE" \
  --runtime python \
  --runtime-version "$PYTHON_VERSION"
```

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
     - **Consumption** — the classic pay-per-execution serverless plan (use this for learning)
     - *(Flex Consumption, Premium, App Service, and Container Apps are the other options)*
   - Click **Select** to continue to the **Basics** tab

   **Basics tab:**
   - Subscription: your subscription
   - Resource group: `ai200-func-rg`
   - Function App name: `ai200-func-<something-unique>` (becomes `<name>.azurewebsites.net`)
   - Do you want to deploy code or container image?: **Code**
   - Runtime stack: **Python**
   - Version: **3.11**
   - Region: `West Europe`
   - Operating System: **Linux** (the only option for Python)
   - Click **Next: Storage >**

   **Storage tab:**
   - Storage account: accept the auto-generated name, or **Create new** →
     `ai200funcsa<something-unique>` (lowercase letters and digits only, 3–24 chars)
   - This account is **mandatory** — Functions keeps trigger state, function keys, and logs in it
   - Click **Next: Networking >**

   **Networking tab:**
   - Enable public access: **On** (so you can call the HTTP function from your machine)
   - Enable network injection: **Off** — on the Consumption plan VNet integration isn't available
     anyway; it's offered on Flex Consumption, Premium, and Dedicated
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

4. **Add application settings** (the equivalent of CLI step 4):
   - Open your Function App → **Settings** → **Environment variables** → **App settings** tab
   - Click **+ Add**:
     - Name: `StorageConnection`
     - Value: the storage connection string — get it from your Storage account →
       **Security + networking** → **Access keys** → **key1** → **Connection string** → *Show* →
       copy
   - Click **+ Add** again: Name `APP_ENVIRONMENT`, Value `azure`
   - Click **Apply** → **Confirm**. The app restarts.

   > These app settings are exactly what `os.environ.get("APP_ENVIRONMENT")` reads in your code,
   > and what the `connection="StorageConnection"` on a binding resolves against.
   > `local.settings.json` is the **local** stand-in for this screen and is never deployed.

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

> **Portal limitation worth knowing for the exam:** for **Python** you cannot author functions in
> the portal — the in-portal code editor is unavailable, and Python apps are always deployed as a
> package. You edit and deploy from your machine (or CI); the portal is for **configuring** and
> **monitoring**.

### VS Code Setup

1. Install [VS Code](https://code.visualstudio.com/)
2. Install the [Azure Functions extension](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions)
3. Install the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
4. Sign in to Azure (Azure icon in the sidebar → **Sign in to Azure**)
5. `Ctrl+Shift+P` (`Cmd+Shift+P` on macOS) → **Azure Functions: Create New Project**
6. Choose a folder → language **Python** → **Model V2** → a template (e.g. *HTTP trigger*) →
   a function name → auth level **ANONYMOUS**
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

> **Important:** deleting a resource group is **permanent**. Everything in it is destroyed and
> cannot be recovered.

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
- Python 3.9–3.12 (the **local** version should match the Function App's runtime version)
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

A **virtual environment** is a private folder of Python packages for this project only — the
closest .NET analogy is that each project restores its own packages instead of using a machine-wide
install.

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

### 3. Check `local.settings.json`

This file already exists in the folder and is **gitignored** (it normally holds real connection
strings). It should contain:

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

`UseDevelopmentStorage=true` is the magic value that points at **Azurite** running locally. To run
against a real Storage account instead, replace both values with its connection string:

```bash
az storage account show-connection-string \
  --name "$STORAGE" --resource-group "$RG" --query connectionString --output tsv
```

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

Note the URL is `/api/hello` — the **route**, not the function name. And there is no `?code=`
because the function is `AuthLevel.ANONYMOUS`; with `FUNCTION` auth you'd append `?code=<key>` or
send an `x-functions-key` header.

Watch the *Terminal 2* logs: `HttpHello` runs, writes to `demo-queue` via its output binding, and a
second later `QueueProcessor` picks the message up. That's a trigger and an output binding working
together, with no connection code in your source.

### 6. Deploy to Azure

```bash
# Publishes the code and (with --publish-local-settings) the app settings.
# Core Tools builds the dependencies remotely for the Linux runtime.
func azure functionapp publish "$FUNCTIONAPP"
```

Then call the deployed function:

```bash
curl "https://$FUNCTIONAPP.azurewebsites.net/api/hello?name=Azure"
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
func new --name HttpHello --template "HTTP trigger" --authlevel anonymous
func new --name QueueProcessor --template "Azure Queue Storage trigger"
func new --name TimerCleanup --template "Timer trigger"
```

---

## Exam gotchas

- **One trigger per function.** Multiple input and output bindings are fine; two triggers are not.

- **Binding `connection` is a setting *name*.** `connection="StorageConnection"` means "look up the
  app setting called StorageConnection", not "connect to a service called StorageConnection".
  Putting a raw connection string there is a classic wrong answer.

- **Every Function App requires a Storage account** — even one with only HTTP triggers. It holds
  trigger state, function keys, logs, and Durable Functions state.

- **Application settings are environment variables.** Read them with `os.environ.get("Name")`.
  `local.settings.json` is the local equivalent and is **never deployed** — the deployed app reads
  the Function App's **Environment variables** blade instead.

- **Timeouts:** Consumption defaults to **5 minutes**, max **10** (`functionTimeout` in
  `host.json`). Flex Consumption, Premium, and Dedicated default to **30 minutes** and can be set
  to unlimited.

- **VNet integration:** available on **Flex Consumption, Premium, and Dedicated**. *Not* on the
  classic Consumption plan.

- **Cold starts:** Consumption scales to zero, so the first call after idle pays a cold start.
  Premium keeps pre-warmed instances; Flex Consumption offers always-ready instances; Dedicated
  with Always On never idles.

- **Always On** is a **Dedicated-plan** setting. Without it, an idle app is unloaded and timer and
  queue triggers stop firing. It doesn't exist (and isn't needed) on Consumption/Premium.

- **Scaling is per Function App**, not per function. All functions in an app share instances, the
  plan, the language, and the settings.

- **`host.json` vs `function.json`:** `host.json` configures **all** functions in the app
  (timeout, retries, logging, extension bundle). `function.json` configures **one** function
  (trigger + bindings) — and exists only in the **v1** model. In v2 Python, decorators replace it.

- **v2 model rules:** one `function_app.py`, one `FunctionApp()` object, all functions registered
  on it. Multiple `FunctionApp()` instances or leftover `function.json` folders → the host finds
  no functions and every call returns **404**.

- **Poison messages:** a queue-triggered function that keeps throwing is retried
  **`maxDequeueCount`** times (default **5**), then the message is moved to
  `<queue-name>-poison`.

- **Queue message deletion is automatic** — on success the host deletes it; on an exception it
  stays for retry. Don't write manual delete code.

- **NCRONTAB has six fields** — `{second} {minute} {hour} {day} {month} {day-of-week}` — one more
  than Linux cron. Timers run in **UTC** unless `WEBSITE_TIME_ZONE` says otherwise.

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

- **Managed identity** is the recommended way to reach other Azure services — bindings support
  identity-based connections (`StorageConnection__accountName` instead of a connection string), so
  you can drop secrets entirely.

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
- v2 programming model: <https://learn.microsoft.com/azure/azure-functions/functions-reference-python?pivots=python-mode-decorators>
- Triggers and bindings: <https://learn.microsoft.com/azure/azure-functions/functions-triggers-bindings?tabs=python>
- HTTP bindings: <https://learn.microsoft.com/azure/azure-functions/functions-bindings-http-webhook?tabs=python>
- Queue Storage bindings: <https://learn.microsoft.com/azure/azure-functions/functions-bindings-storage-queue?tabs=python>
- Timer bindings: <https://learn.microsoft.com/azure/azure-functions/functions-bindings-timer?tabs=python>
- Hosting plans compared: <https://learn.microsoft.com/azure/azure-functions/functions-scale>
- Flex Consumption plan: <https://learn.microsoft.com/azure/azure-functions/flex-consumption-plan>
- `host.json` reference: <https://learn.microsoft.com/azure/azure-functions/functions-host-json>
- Identity-based connections: <https://learn.microsoft.com/azure/azure-functions/functions-reference#configure-an-identity-based-connection>
- Durable Functions: <https://learn.microsoft.com/azure/azure-functions/durable/durable-functions-overview?tabs=python>
