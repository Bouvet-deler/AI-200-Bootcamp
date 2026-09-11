# KQL — Kusto Query Language

**Domain:** 04 — Secure, monitor, troubleshoot Azure solutions (20–25%)
**Maps to skill:** *Write KQL queries to analyze logs and metrics*

> This is the **fully-written reference topic** for the repo. Other topic guides should match
> its depth, structure, and comment style. See [`docs/TOPIC_TEMPLATE.md`](../../docs/TOPIC_TEMPLATE.md).

---

## What it is

**KQL (Kusto Query Language)** is a **read-only query language** for searching and analyzing
large volumes of log and telemetry data. You use it to answer questions like *"which requests
failed in the last hour, and why?"*

Three names you'll see together, and how they relate:

- **Application Insights** — the service your app *sends* telemetry to (requests, traces,
  exceptions, custom logs). Think "where the data comes from."
- **Log Analytics workspace** — the store that *holds* the telemetry as tables. Application
  Insights data lands here.
- **KQL** — the language you *query* those tables with, in the Azure portal's "Logs" blade (or
  via SDK/CLI).

> Mental model: your app → **Application Insights** (ingest) → **Log Analytics** (storage as
> tables) → you run **KQL** to read it.

A KQL query reads like a **pipeline**: start with a table, then pipe (`|`) it through
operators that filter, reshape, and aggregate the rows. Data flows left-to-right, top-to-bottom.

```kusto
requests                       // 1. start from the 'requests' table
| where timestamp > ago(1h)    // 2. keep only the last hour
| where success == false       // 3. keep only failures
| summarize count() by name    // 4. count failures per request name
| order by count_ desc         // 5. worst offenders first
```

---

## Why it's on the exam

The skill bullet is literally *"Write KQL queries to analyze logs and metrics."* Expect the
exam to:

- Show you a KQL snippet and ask **what it returns** (or what's wrong with it).
- Ask you to **pick the operator** for a goal (filter rows → `where`; pick columns →
  `project`; aggregate → `summarize`).
- Test **pipe order** and **time filtering** (`ago()`, `between`).
- Combine with **OpenTelemetry / Application Insights** — you instrument the app (see
  [`../opentelemetry/`](../opentelemetry/)), then query the results with KQL.

You don't need to be a KQL wizard — you need to *read* queries confidently and know the core
operators cold.

---

## Core concepts

KQL data is organized into **tables** (rows and columns, like SQL). Application Insights exposes
two naming schemas depending on query scope. This guide opens **Application Insights → Logs**, so
its worked queries use the application-scoped names on the left:

| Telemetry | Application Insights scope | Log Analytics workspace scope |
| --- | --- | --- |
| Incoming requests | `requests` | `AppRequests` |
| Outbound calls | `dependencies` | `AppDependencies` |
| Exceptions | `exceptions` | `AppExceptions` |
| Application logs | `traces` | `AppTraces` |
| Custom events | `customEvents` | `AppEvents` |
| Custom metrics | `customMetrics` | `AppMetrics` |

Column names and types change too: application scope uses `timestamp`, `operation_Id`, and a
timespan-valued `duration`, while workspace scope uses `TimeGenerated`, `OperationId`, and the
numeric millisecond value `DurationMs`. For example, compare `duration > 1s` in application
scope but `DurationMs > 1000` in workspace scope. Use the schema shown by the portal's current
query scope rather than mixing the two forms.

**The pipeline model.** A query is a table name followed by `|`-separated operators. Each
operator takes the table on its left and produces a new table on its right. **Order matters** —
`where` then `summarize` is not the same as `summarize` then `where`.

**Case sensitivity (a classic gotcha):**
- KQL is case-sensitive for table names, column names, operators, and functions. `Requests`,
  `Timestamp`, or `WHERE` are not substitutes for `requests`, `timestamp`, or `where`.
- **String equality is also case-sensitive** by default: `==` is exact/case-sensitive; use
  `=~` for case-*insensitive* equality, and `has` (case-insensitive term) vs `contains`
  (case-insensitive substring, slower).

The operators you must know:

| Operator | Does | SQL-ish analogy |
| --- | --- | --- |
| `where` | Keep rows matching a condition (**filter**) | `WHERE` |
| `project` | Choose/rename/compute **columns** | `SELECT` |
| `project-away` | Drop specific columns | — |
| `project-rename` | Rename columns while retaining the others | — |
| `extend` | Add a computed column (keep the rest) | `SELECT *, expr AS x` |
| `summarize` | **Aggregate** (count, avg…) grouped `by` columns | `GROUP BY` |
| `count` | Count all rows (shortcut) | `COUNT(*)` |
| `top N by col` | Top N rows by a column | `ORDER BY … LIMIT N` |
| `order by` / `sort by` | Sort rows | `ORDER BY` |
| `take` / `limit` | Return *some* rows (no ordering guarantee) | `LIMIT` |
| `distinct` | Unique values | `DISTINCT` |
| `union` | Combine rows from multiple tables | `UNION` |
| `join` | Combine columns from two tables on a key | `JOIN` |
| `render` | Draw a chart (timechart, barchart…) | — |
| `parse` | Extract fields out of a string column | — |

**Time.** Telemetry is time-series data, so almost every real query filters on time:
- `ago(1h)` = "one hour ago" (also `5m`, `7d`, `30d`).
- `where timestamp > ago(1h)` = last hour.
- `where timestamp between (ago(1d) .. ago(1h))` = a window.
- `bin(timestamp, 5m)` rounds each timestamp down to a 5-minute boundary. It groups rows only
  when used as a `summarize ... by` expression.

---

## Setup

Goal: create a Log Analytics workspace + Application Insights, so you have somewhere to send
telemetry and something to query.

> **Two methods available:**
> - **[CLI](#cli-setup)** — Copy-paste commands below (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal (Web UI)](#portal-setup-web-ui)** — Point-and-click in your browser

### Set your variables

The CLI commands in **Setup** and **Cleanup** reference these as **shell variables** — set them
once for your shell, then run the `az` commands as written. (The Portal method doesn't use
these.) What each one is:

- **`RG`** — resource group: the folder that holds your related Azure resources.
- **`LOCATION`** — the Azure region to deploy into.
- **`WORKSPACE`** — name for the Log Analytics workspace (the store that holds the log tables).
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
#    (provides the 'az monitor app-insights' commands; it's a client-side add-on,
#    not something tied to your Azure account — safe to re-run, it's a no-op if present).
az extension add --name application-insights --only-show-errors

# 3. Create the Log Analytics workspace — the store that holds the log tables.
az monitor log-analytics workspace create \
  --resource-group "$RG" \
  --workspace-name "$WORKSPACE" \
  --location "$LOCATION"

# 4. Create Application Insights and connect it to that workspace.
#    'web' = a web/service app. This prints a 'connectionString' — copy it; your app needs it.
az monitor app-insights component create \
  --app "$APPINSIGHTS" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --application-type web \
  --workspace "$WORKSPACE"

# 5. Fetch the connection string later at any time:
az monitor app-insights component show \
  --app "$APPINSIGHTS" --resource-group "$RG" \
  --query connectionString --output tsv
```

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
   - Resource group: `ai200-rg` (the one you just created)
   - Name: `ai200-logs` (or your chosen name)
   - Region: `West Europe` (match your resource group)
   - Click **Review + create** → **Create**

4. **Create Application Insights:**
   - Click **+ Create a resource** → Search for "Application Insights" → **Create**
   - Subscription: your subscription
   - Resource group: `ai200-rg`
   - Name: `ai200-appinsights`
   - Region: `West Europe`
   - Resource Mode: **Workspace-based** (Classic mode was retired in Feb 2024 — new resources must be workspace-based)
   - **Important:** Under "Workspace", select your `ai200-logs` Log Analytics workspace
   - Click **Review + create** → **Create**

5. **Get the connection string:**
   - Navigate to your Application Insights resource (`ai200-appinsights`)
   - On the **Overview** blade, copy the **Connection String** value shown near the top
     (the older *Instrumentation Key* is deprecated — use the connection string)

6. **Set it as environment variable:**
   ```bash
   export APPLICATIONINSIGHTS_CONNECTION_STRING="<paste-the-copied-string>"
   ```

---

## Cleanup

Goal: delete all resources created during setup to avoid unnecessary Azure charges.
Run this when you're done experimenting, or whenever you want to start fresh.

> **Two methods available:**
> - **[CLI](#cli-cleanup)** — Copy-paste commands below (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal (Web UI)](#portal-cleanup-web-ui)** — Point-and-click in your browser

### CLI Cleanup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first). Set `RG`
as shown in [Set your variables](#set-your-variables), then:

```bash
# Delete the entire resource group and everything in it.
# This removes: Log Analytics workspace, Application Insights, and any other resources in the group.
# The '--yes' flag skips the confirmation prompt. Use '--no-wait' to not wait for completion.
az group delete --name "$RG" --yes --no-wait

# Optional: verify the resource group is gone
az group list --output table
```

> **Important:** Resource-group deletion is destructive and can continue asynchronously. Azure
> recovery behavior varies by resource type, so do not treat it as an application backup or rely
> on recovery. Verify the group name and contents before running the command.

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

3. **OR: Delete individual resources:**
   - Navigate to **Application Insights** (`ai200-appinsights`)
   - Click **Delete** in the top toolbar, confirm the name, and click **Delete**
   - Navigate to **Log Analytics workspace** (`ai200-logs`)
   - Click **Delete** in the top toolbar, confirm the name, and click **Delete**
   - Finally, delete the **Resource group** (now empty) if desired

> **Tip:** Deleting the resource group is faster and ensures you don't miss anything. Individual resource deletion is useful if you want to keep some resources while removing others.

---

## Hands-on (Python)

A tiny app that emits log lines **and** a handled error, so you have real data to query.
It uses the **Azure Monitor OpenTelemetry** package, which auto-wires Python's standard
`logging` (and traces) to Application Insights.

> New to Python? The script is **heavily commented** — every non-trivial line explains both the Python idiom and the Azure concept. See [`app.py`](app.py) for the full source.

> **Remember:** Run all commands below from this folder (`04-secure-monitor/kql/`).

### Setup a virtual environment

```bash
# Create a virtual environment (isolates dependencies)
python -m venv venv
```

### Activate the virtual environment

The activation command depends on your shell and operating system:

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
pip install azure-monitor-opentelemetry
```

### Set your connection string

```bash
export APPLICATIONINSIGHTS_CONNECTION_STRING="<paste the connectionString from CLI setup>"
```

### Run the sample

```bash
python app.py
```

Telemetry takes **1–3 minutes** to appear. Then open **Application Insights → Logs** in the
portal and query it.

> **Tip:** To deactivate the virtual environment when done: `deactivate`

---

## Worked queries

After running `app.py` and waiting 1–3 minutes for telemetry to appear, you can execute these queries
in two places:

**Azure Portal (recommended for learning):**
1. Go to [https://portal.azure.com](https://portal.azure.com)
2. Navigate to your Application Insights resource (`ai200-appinsights` or your chosen name)
3. In the left menu, select **Logs** (under "Monitoring" section)
4. Paste any query below into the editor and click **Run**

These queries use the application-scoped schema (`requests`, `timestamp`, and so on). If you open
the associated **Log Analytics workspace → Logs** instead, translate them to the workspace schema,
such as `AppRequests` and `TimeGenerated`.

**Azure CLI (for automation):**
```bash
# Query via CLI using az monitor app-insights query
az monitor app-insights query \
  --app "ai200-appinsights" \
  --analytics-query "traces | where timestamp > ago(30m) | project timestamp, message, severityLevel | order by timestamp desc" \
  --resource-group "ai200-rg"
```

**1. See your recent log lines** (from `logger.info(...)`):

```kusto
traces                              // your app's log lines land here
| where timestamp > ago(30m)        // only the last 30 minutes
| project timestamp, message, severityLevel   // keep just the useful columns
| order by timestamp desc           // newest first
```

**2. Find all failures in the last hour:**

```kusto
requests
| where timestamp > ago(1h)
| where success == false            // '==' is case-sensitive exact match; false = failed request
| project timestamp, name, resultCode, duration
| order by timestamp desc
```

**3. Count errors by type** (which exception is most common?):

```kusto
exceptions
| where timestamp > ago(1d)         // last 24 hours
| summarize failures = count() by type   // GROUP BY 'type', naming the count column 'failures'
| top 5 by failures                 // the 5 most frequent exception types
```

**4. Error trend over time** (a chart):

```kusto
exceptions
| where timestamp > ago(1d)
| summarize count() by bin(timestamp, 1h)  // bucket into 1-hour intervals
| render timechart                          // draw it as a line chart over time
```

**5. Trace one request end-to-end** — join a request to the dependencies it triggered, using
the shared `operation_Id` (Application Insights' correlation id):

```kusto
requests
| where timestamp > ago(1h) and success == false
| project operation_Id, requestName = name, resultCode   // rename 'name' to avoid a clash
| join kind=inner (                        // inner join = only rows with a match on both sides
    dependencies
    | project operation_Id, dependencyName = name, target, dependencySuccess = success
  ) on operation_Id                        // match rows where operation_Id is equal
```

**6. Pull a value out of a message string** with `parse`:

```kusto
traces
| where message startswith "Processing order"
| parse message with "Processing order " orderId:long   // extract the number after the prefix
| project timestamp, orderId
```

**7. Find the named custom event emitted by the sample:**

```kusto
customEvents
| where timestamp > ago(30m)
| where name == "InventoryValidationFailed"
| project timestamp, name, customDimensions
| order by timestamp desc
```

---

## Exam gotchas

- **`where` vs `project` vs `summarize`.** `where` filters *rows*; `project` chooses *columns*;
  `summarize` *aggregates*. Exam questions hinge on picking the right one.
- **KQL names are case-sensitive.** Use the table, column, operator, and function casing shown in
  the schema. Case-insensitive string operators do not make identifiers case-insensitive.
- **Query scope changes the schema.** Application Insights scope uses names such as `requests`
  and `timestamp`; Log Analytics workspace scope uses `AppRequests` and `TimeGenerated`.
- **Pipe order matters.** `summarize` collapses rows into aggregates — any column you didn't
  aggregate or group `by` is *gone* afterward, so `project`/`where` on those must come *before*
  the `summarize`.
- **String comparison is case-sensitive.** `Name == "get"` won't match `"GET"`. Use `=~` for
  case-insensitive equality, `has` for a case-insensitive term, and `contains` for a substring.
- **`take`/`limit` are not sorted.** They return *arbitrary* rows for a quick peek. Use
  `top N by col` (or `order by … | take N`) when you need the *biggest/newest*.
- **`ago()` uses UTC**, and telemetry timestamps are UTC — don't get caught by local time.
- **`count()` vs `count`.** `count` (operator) counts all rows: `T | count`. `count()`
  (aggregation function) is used inside `summarize`: `T | summarize count() by x`.
- **`join kind=`.** Default join is `innerunique` (dedups the left key) — not the same as
  `inner`. Know `inner`, `leftouter`, and the surprising default.
- **Case-study framing.** KQL questions often sit inside a monitoring scenario — the "app"
  emitting the data is instrumented with OpenTelemetry (see [`../opentelemetry/`](../opentelemetry/)).

---

## Test yourself

Try these queries against your live data. Click to reveal the solution and explanation.

<details>
<summary>Show all log lines from the last 10 minutes</summary>

```kusto
traces
| where timestamp > ago(10m)
| project timestamp, message, severityLevel
| order by timestamp desc
```

**Why it works:** Your `app.py` emits INFO-level traces to the `traces` table. This query filters to the last 10 minutes and shows the message content.
</details>

<details>
<summary>Show only ERROR-level entries</summary>

```kusto
traces
| where timestamp > ago(10m)
| where severityLevel == 3  // 3 = ERROR in Application Insights
| project timestamp, message
| order by timestamp desc
```

**Tip:** Severity levels: 0=Verbose, 1=Info, 2=Warning, 3=Error, 4=Critical
</details>

<details>
<summary>Count log entries by severity level</summary>

```kusto
traces
| where timestamp > ago(10m)
| summarize count() by severityLevel
| order by count_ desc
```

**What you'll see:** A breakdown of how many logs you have at each severity level.
</details>

<details>
<summary>Find the most recent exception</summary>

```kusto
exceptions
| where timestamp > ago(10m)
| top 1 by timestamp desc
| project timestamp, type, outerMessage, operation_Id
```

**Note:** Your `app.py` throws a `ValueError` for negative order IDs — this appears in the `exceptions` table.
</details>

<details>
<summary>Show me logs containing the word "order"</summary>

```kusto
traces
| where timestamp > ago(10m)
| where message contains "order"
| project timestamp, message
| order by timestamp desc
```

**Tip:** `contains` is case-insensitive substring matching. For exact case-sensitive matching, use `==`.
</details>

<details>
<summary>List all distinct log messages</summary>

```kusto
traces
| where timestamp > ago(10m)
| distinct message
```

**What you'll see:** The unique log messages emitted by your application.
</details>

<details>
<summary>Show only WARNING-level entries</summary>

```kusto
traces
| where timestamp > ago(10m)
| where severityLevel == 2  // 2 = WARNING in Application Insights
| project timestamp, message
| order by timestamp desc
```

**What you'll see:** Your `app.py` now emits WARNING logs for large order IDs (> 100) and invalid inventory quantities.
</details>

<details>
<summary>Count logs by message, sorted by frequency</summary>

```kusto
traces
| where timestamp > ago(10m)
| summarize count() by message
| order by count_ desc
```

**What you'll see:** Which log messages appear most frequently in your telemetry.
</details>

<details>
<summary>Find all logs from the last 5 minutes, newest first</summary>

```kusto
traces
| where timestamp > ago(5m)
| project timestamp, message, severityLevel
| order by timestamp desc
```

**Tip:** Use `ago()` with different time units: `5m`, `1h`, `1d`, `7d`
</details>

## Quiz yourself

Take the **KQL** quiz in the [quiz app](../../quiz/)
(bank: [`quiz/src/questions/04-secure-monitor/kql.json`](../../quiz/src/questions/04-secure-monitor/kql.json)).

## Further reading

- KQL overview: <https://learn.microsoft.com/azure/data-explorer/kusto/query/>
- KQL quick reference: <https://learn.microsoft.com/azure/data-explorer/kql-quick-reference>
- Log queries in Azure Monitor: <https://learn.microsoft.com/azure/azure-monitor/logs/log-query-overview>
- Azure Monitor OpenTelemetry for Python: <https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable?tabs=python>
- Application Insights telemetry data model: <https://learn.microsoft.com/azure/azure-monitor/app/data-model-complete>
