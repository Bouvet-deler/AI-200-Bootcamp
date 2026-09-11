# OpenTelemetry (distributed tracing)

**Domain:** 04 — Secure, monitor, troubleshoot Azure solutions (20–25%)
**Maps to skill:** *Trace distributed systems by using OpenTelemetry SDKs*

---

## What it is

**OpenTelemetry (OTel)** is a **vendor-neutral, open standard** for producing **telemetry** —
the signals a running app emits so you can see what it's doing. "Vendor-neutral" means you
instrument your code *once* against the OpenTelemetry API, then point it at *any* backend
(Azure Monitor, Jaeger, Prometheus, Datadog…) without rewriting your app. In Azure, that
backend is **Application Insights / Azure Monitor**, and you query the results with
[KQL](../kql/).

OpenTelemetry defines **three signals**:

- **Traces** — the end-to-end journey of a single request as it flows across your services.
  A trace is a tree of **spans**.
- **Metrics** — numeric measurements over time (request count, queue depth, latency).
- **Logs** — timestamped text records (your `logging.info(...)` lines).

> Mental model: your app → **OpenTelemetry SDK** (produces traces/metrics/logs) →
> **exporter** ships them → **Application Insights** (ingest) → **Log Analytics** (storage as
> tables) → you read them with **KQL**.

The key insight for the exam: OpenTelemetry is the *instrumentation layer*, and Azure Monitor
is the *destination*. Microsoft ships the **Azure Monitor OpenTelemetry Distro**
(`azure-monitor-opentelemetry`) — a pre-packaged bundle of the OTel SDK plus an Azure exporter,
wired up in **one function call**.

---

## Why it's on the exam

The skill is about **instrumenting an app so it can be monitored**. Expect the exam to test:

- **Traces vs spans vs metrics vs logs** — which signal answers which question.
- **Distributed tracing & correlation** — how one request is stitched together across
  services (the `trace ID`, and Application Insights' `operation_Id`).
- **Which package / which call** — recognizing `configure_azure_monitor(...)` and the
  `azure-monitor-opentelemetry` distro as the Azure-recommended way to onboard.
- **Auto-instrumentation vs manual spans** — what you get for free vs what you add by hand.
- **Connection string vs instrumentation key** — the connection string is current; the bare
  instrumentation key is legacy.
- **Sampling** — reducing telemetry volume/cost without losing the signal.

You do **not** need to memorize every OTel class name. You need the mental model, the Azure
onboarding path, and the correlation/sampling gotchas.

---

## Core concepts

### The trace / span tree

A **trace** represents one logical operation (e.g. "checkout"). It is made of **spans** — each
span is a single unit of work with a **name**, a **start/end time** (so, a duration), and
optional **attributes** (key/value tags) and **events**.

```
Trace: "POST /checkout"                 ← the whole request (root span)
├─ span: "validate cart"                ← child span, 12 ms
├─ span: "charge payment"               ← child span, 210 ms
│  └─ span: "HTTP POST payments-api"    ← nested child (an outbound dependency)
└─ span: "write order to DB"            ← child span, 34 ms
```

Every span carries a **trace ID** (shared by all spans in the trace) and a **span ID** (unique
to that span), plus its **parent span ID**. That parent/child chain is what lets a tool
reconstruct the tree. A span that has no parent is the **root span**.

In Application Insights, each kind of span (and the other signals) lands in a specific table —
these are the same tables you query with [KQL](../kql/):

| OTel concept | Application Insights table | Example |
| --- | --- | --- |
| Server span (incoming request) | `requests` | A user calls your API: `POST /checkout` arrives at your app. |
| Client span (outbound call) | `dependencies` | Your app calls *out* to something else: a **database query** (SQL, Cosmos DB), a **REST/HTTP call** to another API, a read from **Blob Storage**, or a message put on a **queue**. |
| Exception recorded on a span | `exceptions` | Your code throws a `ValueError`, or a downstream call times out and raises. |
| Log record | `traces` | A `logger.info("Processing order 42")` line from your code. |
| Metric | `customMetrics` / `AppMetrics` | A counter like `orders.processed`, or a latency measurement. |

> **"Client" vs "server" span** is about *direction*, from your app's point of view. A **server
> span** is work your app does in response to a request coming *in*. A **client span** is a call
> your app makes *out* to a dependency (a DB or API). One incoming request often creates several
> outbound dependency calls — that's why a single `requests` row typically links to several
> `dependencies` rows (all sharing its `operation_Id`).

The OTel **trace ID** surfaces as the `operation_Id` correlation column in KQL — that's the key
you `join` on to trace one request end-to-end.

### Context propagation (how distributed tracing actually works)

When Service A calls Service B over HTTP, A injects the trace context into a request header
(the W3C **`traceparent`** header). B reads that header and continues the *same* trace instead
of starting a new one. This **context propagation** is what makes tracing "distributed" — it's
automatic for instrumented HTTP libraries, and it's the single most important idea behind the
"one request across many services" story.

### The pipeline: API → SDK → exporter

- **API** — the interface your code calls (`tracer.start_as_current_span(...)`). Stable and
  backend-agnostic.
- **SDK** — the implementation that actually records spans, batches them, and applies sampling.
- **Exporter** — translates and ships the batched telemetry to a backend. The **Azure Monitor
  exporter** sends to Application Insights.

Between the SDK and exporter sits a **processor** (usually the **BatchSpanProcessor**, which
buffers spans and flushes them in the background — why telemetry appears a minute or two later,
and why a short script must pause before exiting so the buffer flushes).

### Auto-instrumentation vs manual instrumentation

- **Auto-instrumentation** — libraries (Flask, Django, requests, psycopg, etc.) are
  instrumented *for you*; you get request and dependency spans without touching that code. The
  Azure distro turns much of this on automatically.
- **Manual instrumentation** — you create your *own* spans for business logic OTel can't see
  (`with tracer.start_as_current_span("reprice basket"):`), add attributes, and record
  exceptions. If you catch an exception, `record_exception(...)` preserves its details while
  `set_status(StatusCode.ERROR)` separately marks the span outcome as failed.

Real apps use both: auto for the plumbing, manual for the domain-specific work you care about.

### Sampling

**Sampling** reduces the number of traces exported, which controls ingestion volume and cost.
Current versions of the Azure Monitor Python distro use a **rate-limited sampler** by default
(five traces per second when you do not configure sampling). You can instead provide a
`sampling_ratio` for fixed-percentage sampling, such as `0.05` for roughly 5%.

The sampling decision is carried in the W3C trace context. With the normal parent-aware setup,
child spans honour their parent's decision, which keeps a distributed trace coherent. Do not
interpret that as an unconditional guarantee: missing propagation, independently configured
services, or a custom sampler can still produce incomplete traces.

---

## Setup

You send OpenTelemetry data to an **Application Insights** resource backed by a **Log Analytics
workspace** — the *exact same resources* as the [KQL topic](../kql/#setup). If you already
created them there, reuse them and skip to [Hands-on](#hands-on-python).

> **Two methods available:**
> - **[CLI](#cli-setup)** — Copy-paste commands below (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal (Web UI)](#portal-setup-web-ui)** — Point-and-click in your browser

### Set your variables

The CLI commands below reference these as **shell variables** — set them once for your shell,
then run the `az` commands as written. (The Portal method doesn't use these.) What each one is:

- **`RG`** — resource group: the folder that holds your related Azure resources.
- **`LOCATION`** — the Azure region to deploy into.
- **`WORKSPACE`** — name for the Log Analytics workspace (the store that holds the telemetry).
- **`APPINSIGHTS`** — name for the Application Insights resource.

The variable *names* are identical everywhere; only the **assignment syntax** differs by shell,
so copy the block that matches yours:

```bash
# bash / zsh — Linux, and macOS (its default shell)
RG="ai200-rg"
LOCATION="westeurope"
WORKSPACE="ai200-logs"
APPINSIGHTS="ai200-appinsights"
```

```fish
# fish — Linux / macOS
set RG ai200-rg
set LOCATION westeurope
set WORKSPACE ai200-logs
set APPINSIGHTS ai200-appinsights
```

```powershell
# PowerShell — Windows (also cross-platform)
$RG = "ai200-rg"
$LOCATION = "westeurope"
$WORKSPACE = "ai200-logs"
$APPINSIGHTS = "ai200-appinsights"
```

```bat
:: Command Prompt (cmd.exe) — Windows
set RG=ai200-rg
set LOCATION=westeurope
set WORKSPACE=ai200-logs
set APPINSIGHTS=ai200-appinsights
```

> **Referencing the variables in the commands below.** The `az` snippets are written bash-style
> (`"$RG"`) and work unchanged in **bash/zsh, fish, and PowerShell** (all expand `$RG`). In
> **cmd**, write **`%RG%`** instead. The `\` at the end of long commands is a *bash*
> line-continuation — in PowerShell use a backtick `` ` ``, in cmd use `^`, or just put the whole
> command on one line.

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first), after
[setting your variables](#set-your-variables) above.

```bash
# 1. Create the resource group (the container for everything below).
az group create --name "$RG" --location "$LOCATION"

# 2. One-time-per-machine: add the 'application-insights' CLI extension
#    (adds the 'az monitor app-insights' commands; safe to re-run).
az extension add --name application-insights --only-show-errors

# 3. Create the Log Analytics workspace — the store that holds the telemetry tables.
az monitor log-analytics workspace create \
  --resource-group "$RG" \
  --workspace-name "$WORKSPACE" \
  --location "$LOCATION"

# 4. Create Application Insights and connect it to that workspace.
#    This prints a 'connectionString' — copy it; your app needs it to know where to send data.
az monitor app-insights component create \
  --app "$APPINSIGHTS" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --application-type web \
  --workspace "$WORKSPACE"

# 5. Fetch the connection string at any time:
az monitor app-insights component show \
  --app "$APPINSIGHTS" --resource-group "$RG" \
  --query connectionString --output tsv
```

### Portal Setup (Web UI)

Prefer the browser? Create the same resources in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)
2. **Create Resource Group:** **Resource groups** → **+ Create** → name `ai200-rg`, region
   `West Europe` → **Review + create** → **Create**
3. **Create Log Analytics workspace:** **+ Create a resource** → search "Log Analytics
   workspace" → **Create** → resource group `ai200-rg`, name `ai200-logs` → **Review + create**
4. **Create Application Insights:** **+ Create a resource** → search "Application Insights" →
   **Create** → resource group `ai200-rg`, name `ai200-appinsights`, **Resource Mode:
   Workspace-based**, and under "Workspace" select `ai200-logs` → **Review + create**
5. **Get the connection string:** open `ai200-appinsights` → **Overview** blade → copy the
   **Connection String** (the older *Instrumentation Key* is deprecated — use the connection
   string).
6. **Set it as an environment variable:**
   ```bash
   export APPLICATIONINSIGHTS_CONNECTION_STRING="<paste-the-copied-string>"
   ```

---

## Hands-on (Python)

A tiny app that emits **all three signals** — a manual **trace/span**, a **metric**, an
**auto-instrumented dependency** call, and **logs** — so you can see each show up in a different
Application Insights table. It uses the **Azure Monitor OpenTelemetry Distro**, which wires the
whole OTel pipeline to Application Insights in **one call**.

> New to Python? The script is **heavily commented** — every non-trivial line explains both the
> Python idiom and the Azure/OTel concept. See [`app.py`](app.py) for the full source.

> **Remember:** run all commands below from this folder (`04-secure-monitor/opentelemetry/`).

### Set up a virtual environment

```bash
# A virtual environment isolates this project's dependencies from the system Python.
python -m venv venv
```

### Activate the virtual environment

```bash
# --- bash/zsh (macOS/Linux) ---
source venv/bin/activate

# --- fish (macOS/Linux) ---
source venv/bin/activate.fish

# --- Windows PowerShell ---
.\venv\Scripts\Activate.ps1

# --- Windows cmd ---
venv\Scripts\activate.bat
```

### Install dependencies

```bash
# The Azure Monitor OpenTelemetry Distro bundles the OTel SDK + the Azure exporter.
# 'requests' is a popular HTTP library; the distro auto-instruments it, so the outbound
# call in app.py shows up as a 'dependency' with no extra code.
pip install azure-monitor-opentelemetry requests
```

### Set your connection string

```bash
export APPLICATIONINSIGHTS_CONNECTION_STRING="<paste the connectionString from setup>"
```

### Run the sample

```bash
python app.py
```

Telemetry is buffered and takes **1–3 minutes** to appear. Then open **Application Insights →
Logs** in the portal and query it.

> **Tip:** deactivate the virtual environment when done with `deactivate`.

### What to look for

After a couple of minutes, run these in **Application Insights → Logs**:

```kusto
// 1. The SERVER-kind manual span shows up as a request (the root operation).
requests
| where timestamp > ago(15m)
| project timestamp, name, duration, operation_Id
```

```kusto
// 2. The auto-instrumented outbound HTTP call shows up as a dependency,
//    sharing the SAME operation_Id as the request above — that's the correlation.
dependencies
| where timestamp > ago(15m)
| project timestamp, name, target, success, operation_Id
```

```kusto
// 3. Your custom metric.
customMetrics
| where timestamp > ago(15m)
| project timestamp, name, value
```

```kusto
// 4. Trace one operation end-to-end by its correlation id.
union requests, dependencies, traces, exceptions
| where timestamp > ago(15m)
| project timestamp, itemType, name, message, operation_Id
| order by timestamp asc
```

---

## Interactive playground

Once the concepts click, [`interactive.py`](interactive.py) lets you **experiment**: a menu-driven
CLI where you pick a telemetry type, type your own message, and send it — then read the last 5
minutes of any table back out, so you can watch a signal you just emitted land in its table.
The query SDK uses the Log Analytics schema (`AppRequests`, `TimeGenerated`, and so on), even
when its `query_resource(...)` call is scoped to the Application Insights resource; the menu
keeps the familiar application-scope labels alongside those queries.

```
================= OpenTelemetry Playground =================
SEND telemetry:
  1) Send a log (traces)
  2) Send a request (requests)
  3) Send a dependency / outbound call (dependencies)
  4) Send an exception (exceptions)
  5) Send a metric (customMetrics)

QUERY last 5 minutes:
  6) Show recent logs (traces)      ...   10) Show recent metrics
  0) Quit
===========================================================
```

**Sending** only needs the connection string (same as `app.py`). **Querying** additionally needs
the SDK, a sign-in, and the resource id:

```bash
# One extra install for the query side (the Azure Monitor Query SDK + credential helper).
pip install azure-monitor-query azure-identity

# Sign in so the app can authenticate to read your data (picked up automatically).
az login

# Tell it WHICH Application Insights resource to query (copy the printed id).
# Optional — if you skip this, the app prompts you to paste the id the first time you query.
export APPLICATIONINSIGHTS_RESOURCE_ID="$(az monitor app-insights component show \
  --app ai200-appinsights --resource-group ai200-rg --query id -o tsv)"

python interactive.py
```

> The **send** and **query** halves map one-to-one to the two skills this domain tests:
> *instrument an app to produce telemetry* (OpenTelemetry) and *analyze it* ([KQL](../kql/), which
> is exactly what option 6–10 run under the hood). Telemetry still takes **1–3 minutes** to become
> queryable, so send a few items, then query a minute later.

---

## Exam gotchas

- **Connection string, not instrumentation key.** The **connection string** is the current way
  to point telemetry at Application Insights. The bare **instrumentation key** is legacy /
  deprecated — a classic "which is right" distractor.
- **`configure_azure_monitor(...)` is the one call to know.** The Azure Monitor OpenTelemetry
  *Distro* (`azure-monitor-opentelemetry`) is Microsoft's recommended onboarding. Older
  material references `opencensus-ext-azure` — **OpenCensus is retired; OpenTelemetry replaced
  it.** Pick the OTel/distro answer.
- **Traces vs metrics vs logs.** *Traces* answer "what happened during this one request and how
  long did each step take?"; *metrics* answer "how many / how much, over time?"; *logs* are
  free-text records. Questions hinge on picking the signal that fits the question.
- **A span is a unit of work; a trace is the whole tree.** Don't swap them. The root span has no
  parent.
- **Correlation = trace ID = `operation_Id`.** In KQL you `join` telemetry on `operation_Id` to
  follow one request across `requests`, `dependencies`, `exceptions`, and `traces`.
- **Context propagation via the `traceparent` (W3C) header** is what makes tracing
  *distributed*. If a downstream service starts a *new* trace, propagation is broken (wrong
  header, or an uninstrumented hop).
- **Know both sampling modes.** Current Azure Monitor Python distro versions default to
  rate-limited sampling (five traces per second); `sampling_ratio` selects fixed-percentage
  sampling. Parent-aware sampling normally preserves one decision across a propagated trace,
  but broken context propagation or different service configurations can still create gaps.
- **Span kind controls the Application Insights table.** An explicitly created span defaults to
  `INTERNAL`, which maps to `dependencies` (`InProc`). Use `SpanKind.SERVER` for incoming request
  handling—or for a top-level background operation that you deliberately model as a request—not
  for every internal method merely to change its table.
- **Auto-instrumentation covers frameworks/libraries; manual spans cover your business logic.**
  You won't get a span for a pure in-process calculation unless you create it yourself.
- **Buffered export.** Telemetry flushes in the background (BatchSpanProcessor), so a
  short-lived script must sleep (or flush) before exiting or you lose the tail — and data takes
  1–3 minutes to appear regardless.

---

## Quiz yourself

Take the **OpenTelemetry** quiz in the [quiz app](../../quiz/)
(bank: [`quiz/src/questions/04-secure-monitor/opentelemetry.json`](../../quiz/src/questions/04-secure-monitor/opentelemetry.json)).

## Further reading

- Azure Monitor OpenTelemetry for Python: <https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable?tabs=python>
- Add & customize OpenTelemetry (Python): <https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-add-modify?tabs=python>
- Configure sampling & other settings: <https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-configuration?tabs=python>
- Data correlation in Application Insights: <https://learn.microsoft.com/azure/azure-monitor/app/distributed-trace-data>
- OpenTelemetry project docs (concepts, signals, spans): <https://opentelemetry.io/docs/concepts/>
- W3C Trace Context (the `traceparent` header): <https://www.w3.org/TR/trace-context/>
