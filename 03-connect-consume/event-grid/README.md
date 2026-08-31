# Azure Event Grid

**Domain:** 03 — Connect to and consume Azure services (20–25%)
**Maps to skill:** *Implement event-driven workflows by using Azure Event Grid, including
filters, custom events, and retries*

---

## What it is

**Azure Event Grid** is a **pub/sub event-routing** service. A **publisher** emits small
**events** — facts about something that already happened, like *"order 12345 was created"* —
and Event Grid **pushes** each event to every **subscriber** that registered interest in it.
For the Event Grid Basic topics used in this guide, subscribers never poll; Event Grid calls them.

Three moving parts, and how they relate:

- **Topic** — the address publishers send events to. Either a **system topic** (an Event Grid
  resource associated with an Azure event source, such as a Storage account) or a **custom
  topic** (one you create, for events *your* application defines).
- **Event subscription** — a registration that says *"deliver events from this topic, matching
  this filter, to this handler."* One topic can have many subscriptions, each with its own
  filter and its own handler — that's the "**one event, many interested parties**" fan-out.
- **Handler (endpoint)** — where a matching event is delivered: a webhook (including an
  HTTP-triggered Azure Function), an Event Grid-triggered Azure Function, a Storage Queue, a
  Service Bus queue/topic, an Event Hub, Logic Apps, or a Relay hybrid connection.

> Mental model:
>
> ```
>  PUBLISHER                    TOPIC              EVENT SUBSCRIPTIONS           HANDLERS
>
>  your app / ──publish──▶  ┌──────────┐   ┌─▶ subscription A (filter: Orders.*) ──▶ Function
>  an Azure resource        │  custom  │───┤
>  (Blob created, etc.)     │ or system│   └─▶ subscription B (filter: subject   ──▶ Storage
>                           │  topic   │        starts with "inventory/")            Queue
>                           └──────────┘
> ```

**Push, not poll** — the defining difference from **Service Bus** and **Event Hubs**, which
your handler pulls messages *from*. Event Grid calls *you*.

---

## Why it's on the exam

The skill bullet is *"Implement event-driven workflows by using Azure Event Grid, including
filters, custom events, and retries."* Expect the exam to test:

- **Publishing custom events** — the two event schemas (Event Grid schema vs. **CloudEvents**
  schema) and what a well-formed event needs (`source`, `type`/`eventType`, `subject`, `data`).
- **Filters** — narrowing a subscription to a **subject prefix/suffix** or an **advanced
  filter** (matching on a data field, an operator, and a value) so a handler only receives what
  it cares about.
- **Retries and dead-lettering** — the default retry policy, how to tune it, and what happens
  to events that never get delivered.
- **Picking Event Grid vs. Service Bus vs. Event Hubs** for a given scenario — this is a
  recurring "which service" question across the whole exam.
- **The webhook validation handshake** — a classic gotcha for anyone hand-rolling a webhook
  endpoint instead of using an Event Grid trigger.

---

## Core concepts

### 1. Topics — system vs. custom

| Topic type | Who creates it | Events it carries |
| --- | --- | --- |
| **System topic** | Event Grid, explicitly or automatically when you subscribe to an Azure source | Built-in events the resource already knows how to emit — e.g. Storage `BlobCreated`, Resource Group `ResourceWriteSuccess`, Key Vault `SecretNewVersionCreated` |
| **Custom topic** | You, explicitly (`az eventgrid topic create`) | **Custom events** your application defines and publishes itself |
| **Domain** | You, when you need *many* custom topics (e.g. one per tenant) managed and secured as a unit | Same as custom topics, organized under one endpoint |

> **Exam gotcha:** when you create an event subscription scoped to an Azure resource (for example,
> `az eventgrid event-subscription create --source-resource-id <storage-account-id>`), Event Grid
> can create the associated system-topic resource automatically. The Storage account is the
> **event source**, not the system topic itself.

### 2. Event schema — CloudEvents vs. Event Grid schema

An event is a small JSON envelope around your payload. A custom topic has one configured input
schema. The two standard schemas covered here are:

| Field (CloudEvents v1.0) | Field (Event Grid schema) | Meaning |
| --- | --- | --- |
| `source` | `topic` | Where the event came from |
| `type` | `eventType` | What kind of event this is, e.g. `Orders.OrderCreated` |
| `subject` | `subject` | A specific resource the event is about, e.g. `orders/12345` — this is what filters usually match on |
| `id` | `id` | Unique event id (you generate it, or the SDK does) |
| `time` | `eventTime` | UTC timestamp |
| `data` | `data` | Your actual payload, any JSON |

> **Exam gotcha:** **CloudEvents v1.0** is the Microsoft-recommended schema for new topics — it's
> an open, cross-cloud standard (not Azure-specific). The **Event Grid schema** is the original,
> Azure-only shape and still shows up in exam questions and older system topics. Event Grid can
> also map a custom input schema, but this guide uses CloudEvents. A CloudEvents-input topic can
> deliver only CloudEvents; an Event Grid-schema topic can deliver Event Grid schema or
> CloudEvents.

### 3. Filters — who gets which event

An event subscription can filter on:

- **Subject filters** — `subjectBeginsWith` / `subjectEndsWith`, plain string prefix/suffix
  matches against the event's `subject`. Cheap and the most common filter in exam scenarios.
- **Event type filters** — `includedEventTypes`, an allow-list of `type`/`eventType` values.
- **Advanced filters** — match supported envelope fields or fields inside `data`, with an
  **operator** (`StringIn`, `NumberGreaterThan`, `BoolEquals`, `StringContains`, …) and a value.
  Up to 25 advanced filters and 25 filter values **in total** are allowed per subscription.

> **Exam gotcha:** filters are evaluated with **AND** — an event must satisfy every filter on a
> subscription to be delivered, not just one.

### 4. Delivery, retries, and dead-lettering

Event Grid delivers **at least once**, asynchronously, and retries failures with **exponential
backoff**.

| Setting | Default | Configurable? |
| --- | --- | --- |
| Retry attempts | Up to **30** | `--max-delivery-attempts` (1–30) |
| Event time-to-live | **24 hours** | `--event-ttl` (1–1440 minutes) |
| Retry schedule | Exponential backoff, capped | Not directly tunable — governed by the two settings above |
| Dead-letter destination | None (expired events are dropped) | A **Storage Blob container**, via `--deadletter-endpoint` |

A delivery is retried on failed responses. A **200–204** response from the handler counts as
success. Once **either** the retry-attempt cap **or** the TTL is hit, the event is dropped — or,
if configured, sent to the **dead-letter** Storage container instead of being lost. Retry timing
is nondeterministic, so write handlers to be **idempotent**: safely process a duplicate event
without repeating its business effect.

> **Exam gotcha:** dead-lettering is **opt-in** and always a **Storage Blob container** — Event
> Grid has no built-in dead-letter *queue* the way Service Bus does.

### 5. Handlers — where events land

| Handler | Typical use |
| --- | --- |
| **Azure Function (Event Grid trigger)** | The easiest path — the trigger auto-handles the validation handshake for you |
| **Webhook (any HTTPS endpoint)** | Your own API; **you** must handle the validation handshake (below) |
| **Storage Queue** | Cheap, durable buffering into a queue you poll |
| **Service Bus queue/topic** | Hand off to a reliable-messaging system for ordered/transactional processing |
| **Event Hubs** | Fan events into a high-throughput streaming pipeline |
| **Logic Apps** | No-code workflow trigger |

> **Webhook validation depends on the delivery schema:** an Event Grid-schema webhook receives a
> `SubscriptionValidationEvent`. It can return its `validationCode` immediately or, when present,
> open its `validationUrl` manually. A **CloudEvents v1.0** webhook receives an HTTP `OPTIONS`
> request. It can grant permission immediately with the CloudEvents `WebHook-Allowed-Origin` and
> `WebHook-Allowed-Rate` headers. For the Event Grid Basic topics used in this guide, it can
> instead use the `WebHook-Request-Callback` URL supplied in that request. This guide delivers
> CloudEvents, so see the webhook.site walkthrough below. An **Azure Function with an Event Grid
> trigger** handles the platform validation for you.

### 6. Event Grid vs. Service Bus vs. Event Hubs vs. Storage Queues

Azure has four services that all shuttle small pieces of data between applications, and at first
glance they look like the same thing four times — so here is a comparison. Two questions separate
them: **what does each one actually hold on to**, and **what does it do with that item once
somebody has read it?**

Two pieces of jargon you will meet in the Microsoft docs, in plain English first:

- **Peek-lock** (Service Bus, Storage Queues) — when a worker takes a job off the list, the job
  isn't deleted, just *hidden* from the other workers while that one works on it. Finish → it's
  deleted. Crash → it becomes visible again and another worker picks it up.
- **Pub/sub** (publish/subscribe) — the sender doesn't address anyone in particular. It announces
  *"this happened"*, and every app that registered an interest gets its own copy.

#### What each one holds, and what it does with it

| Service | What it holds | Example of one item | What it does with it |
| --- | --- | --- | --- |
| **Event Grid** | Nothing, really — it's a phone call | *"File `invoice-42.pdf` was uploaded"* | Immediately calls every interested app's URL. As soon as one answers "got it", Event Grid forgets the item |
| **Service Bus** | A to-do list of jobs | *"Charge card for order 42, 499 kr, customer 7"* | Hands a job to one worker and hides it. Deletes it when that worker says "done"; puts it back if the worker crashes |
| **Storage Queues** | The same to-do list, bare-bones | *"Resize image `cat.jpg`"* | Same idea, with none of the extras — no ordering, no dead-letter queue, no topics |
| **Event Hubs** | A long tape of readings, in order | *"Sensor 17, 21.4 °C, 12:00:03"* | Keeps everything and lets readers scroll through it. Reading does **not** remove anything |

#### How long it keeps things

| Service | Kept for                                                                                     | If the reader crashes mid-job |
| --- |----------------------------------------------------------------------------------------------| --- |
| **Event Grid** | Until a handler answers "got it" — retried for up to 24 hours, then dead-lettered or dropped | The item is already gone. Lost. |
| **Service Bus** | Until a worker says "done" (a TTL you set — days or weeks)                                   | Comes back on the list automatically |
| **Storage Queues** | Same as Service Bus                                                                          | Comes back on the list automatically |
| **Event Hubs** | A fixed number of days (1–7 on the standard tier), no matter who has read it                 | The reader restarts from its last bookmark |

#### The one-line version

- **Event Grid** — *"tell everyone this happened."* Doesn't store; it notifies.
- **Service Bus** — *"this job must get done, by the rules."* Holds the job until a worker
  confirms it finished, and can enforce order, grouping, and all-or-nothing.
- **Storage Queues** — *"this job must get done, no rules needed."* Holds it just as safely, but
  can't do order, grouping, or a problem-list. In exchange it's dirt cheap and takes enormous
  volumes.
- **Event Hubs** — *"record everything that happened."* Stores for N days; many readers can
  re-read it independently.

This is also why Event Grid is the wrong choice for orders and payments: **it drops the event the
moment your code answers the phone.** If your code then crashes, that order is gone. Service Bus
keeps the job hidden-but-alive until you explicitly confirm you have finished, so a crash costs
you nothing.

#### The exam-shorthand version

| | **Event Grid Basic** | **Service Bus** | **Event Hubs** |
| --- | --- | --- | --- |
| Model | Push, pub/sub | Pull, queue/topic | Pull, stream (partitioned log) |
| Payload | Small **notifications** ("this happened") | Business **messages** (needs to be processed, possibly transactionally) | High-volume **telemetry/event streams** |
| Ordering | Not guaranteed | FIFO available (sessions) | Guaranteed **within a partition** |
| Retention | Until delivered or TTL expires | Until consumed (or a queue TTL) | Fixed retention window (hours–days), replayable |
| Typical use | *"A blob was created — go react to it"* | *"Process this order reliably"* | *"Ingest 100k device telemetry events/sec"* |

> **Exam gotcha:** if the scenario says **"react to something that happened"** with low volume
> and fan-out to multiple subscribers → **Event Grid**. **"Reliably process a business
> transaction, possibly with ordering/locks"** → **Service Bus**. **"Ingest a firehose of
> telemetry for analytics"** → **Event Hubs**.

---

## Setup

Goal: create a CloudEvents custom topic and an event subscription with a **subject filter** and a
**custom retry policy**, delivering to an Azure Function or a CloudEvents-capable webhook.

> **Two methods available:**
> - **[CLI](#cli-setup)** — copy-paste commands (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal](#portal-setup-web-ui)** — point-and-click in the browser

### Set your variables

- **`RG`** — resource group
- **`LOCATION`** — Azure region
- **`TOPIC`** — Event Grid custom topic name (globally unique per region)
- **`ENDPOINT`** — the public HTTPS URL of a webhook. A production endpoint normally implements
  the CloudEvents `OPTIONS` validation handshake; for a first run, you can instead use
  webhook.site and complete its manual callback in the walkthrough below. An Azure Function with
  an Event Grid trigger handles the platform validation automatically.

```bash
# bash / zsh — Linux, and macOS (its default shell)
RG="ai200-eg-rg"
LOCATION="westeurope"
TOPIC="ai200-orders-topic"
ENDPOINT="<your-webhook-url>"
```

```fish
# fish — Linux / macOS
set RG ai200-eg-rg
set LOCATION westeurope
set TOPIC ai200-orders-topic
set ENDPOINT "<your-webhook-url>"
```

```powershell
# PowerShell — Windows (also cross-platform)
$RG = "ai200-eg-rg"
$LOCATION = "westeurope"
$TOPIC = "ai200-orders-topic"
$ENDPOINT = "<your-webhook-url>"
```

```bat
:: Command Prompt (cmd.exe) — Windows
set RG=ai200-eg-rg
set LOCATION=westeurope
set TOPIC=ai200-orders-topic
set ENDPOINT=<your-webhook-url>
```

> **Referencing variables:** the `az` snippets use bash-style `"$RG"`, which also works in fish
> and PowerShell. In **cmd** use `%RG%` instead. The trailing `\` on long commands is a *bash*
> line-continuation — in PowerShell use a backtick `` ` ``, in cmd use `^`, or put the command on
> one line.

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first), after
[setting your variables](#set-your-variables) above.

```bash
# 1. Create the resource group
az group create --name "$RG" --location "$LOCATION"

# 2. Current Azure CLI versions include `az eventgrid`. If an older CLI says the command is
#    missing, install its Event Grid extension once, then rerun the command:
# az extension add --name eventgrid --only-show-errors

# 3. Create a custom topic using the CloudEvents schema (Microsoft-recommended for new topics).
az eventgrid topic create \
  --name "$TOPIC" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --input-schema cloudeventschemav1_0
```

> **Step 4 assigns shell variables** — this is the one place in CLI Setup where bash, fish,
> PowerShell, and cmd syntax actually diverges. Steps 1–3 and 5 only *read* `$VAR`/`%VAR%`
> inside `az` calls, which works the same across shells (see
> [referencing variables](#set-your-variables) above) — it's assignment that differs per shell.

```bash
# 4. Fetch the topic's endpoint, access key, and resource ID (bash / zsh)
TOPIC_ENDPOINT=$(az eventgrid topic show \
  --name "$TOPIC" --resource-group "$RG" --query endpoint --output tsv)
TOPIC_KEY=$(az eventgrid topic key list \
  --name "$TOPIC" --resource-group "$RG" --query key1 --output tsv)
TOPIC_ID=$(az eventgrid topic show \
  --name "$TOPIC" --resource-group "$RG" --query id --output tsv)
echo "Endpoint: $TOPIC_ENDPOINT"
```

```fish
# 4. Fetch the topic's endpoint, access key, and resource ID (fish)
set TOPIC_ENDPOINT (az eventgrid topic show --name $TOPIC --resource-group $RG --query endpoint --output tsv)
set TOPIC_KEY (az eventgrid topic key list --name $TOPIC --resource-group $RG --query key1 --output tsv)
set TOPIC_ID (az eventgrid topic show --name $TOPIC --resource-group $RG --query id --output tsv)
echo "Endpoint: $TOPIC_ENDPOINT"
```

```powershell
# 4. Fetch the topic's endpoint, access key, and resource ID (PowerShell)
$TOPIC_ENDPOINT = az eventgrid topic show --name $TOPIC --resource-group $RG --query endpoint --output tsv
$TOPIC_KEY = az eventgrid topic key list --name $TOPIC --resource-group $RG --query key1 --output tsv
$TOPIC_ID = az eventgrid topic show --name $TOPIC --resource-group $RG --query id --output tsv
Write-Host "Endpoint: $TOPIC_ENDPOINT"
```

```bat
:: 4. Fetch the topic's endpoint, access key, and resource ID (cmd)
for /f "delims=" %%i in ('az eventgrid topic show --name %TOPIC% --resource-group %RG% --query endpoint --output tsv') do set TOPIC_ENDPOINT=%%i
for /f "delims=" %%i in ('az eventgrid topic key list --name %TOPIC% --resource-group %RG% --query key1 --output tsv') do set TOPIC_KEY=%%i
for /f "delims=" %%i in ('az eventgrid topic show --name %TOPIC% --resource-group %RG% --query id --output tsv') do set TOPIC_ID=%%i
echo Endpoint: %TOPIC_ENDPOINT%
```

```bash
# 5. Create an event subscription with:
#    --subject-begins-with     a SUBJECT FILTER — only "orders/" events reach this handler
#    --max-delivery-attempts / --event-ttl   a custom RETRY POLICY
#    --event-delivery-schema   the schema DELIVERED to the handler. This CloudEvents-input
#    topic can deliver CloudEvents only, so this explicit value documents the contract.
# (cmd users: use %TOPIC_ID%/%ENDPOINT% instead of $TOPIC_ID/$ENDPOINT below.)
az eventgrid event-subscription create \
  --name "orders-webhook-sub" \
  --source-resource-id "$TOPIC_ID" \
  --endpoint "$ENDPOINT" \
  --subject-begins-with "orders/" \
  --max-delivery-attempts 10 \
  --event-ttl 60 \
  --event-delivery-schema cloudeventschemav1_0
```

> The default endpoint type here is a raw **Web Hook**. Because this subscription delivers
> CloudEvents, Event Grid validates it with an HTTP `OPTIONS` request, not a
> `SubscriptionValidationEvent` or a `validationUrl`. A production endpoint grants permission
> with the CloudEvents headers described in [Core concepts §5](#5-handlers--where-events-land).
> For this Event Grid Basic topic, the request also supplies `WebHook-Request-Callback`, which a
> request-capture service such as webhook.site can use for manual approval. See the walkthrough
> below. For a no-custom-webhook route, use the Azure Function option in the portal steps below.

### Portal Setup (Web UI)

Prefer the browser? Create the same resources in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Create the Resource Group:**
   - Click **Resource groups** → **+ Create**
   - Name: `ai200-eg-rg`, Region: `West Europe`
   - Click **Review + create** → **Create**

3. **Create the custom topic:**
   - Click **+ Create a resource** → search "Event Grid Topic" → **Create**
   - Resource group: `ai200-eg-rg`
   - Name: `ai200-orders-topic` (must be globally unique per region)
   - Region: `West Europe`
   - **Event Schema**: **Cloud Event Schema v1.0** (recommended for new topics)
   - **Networking** and **Security** tabs: leave at defaults (public access, key-based auth) —
     see the callout below
   - Click **Review + create** → **Create**

> **Networking / Security tabs:** left at defaults (public access, key-based auth) in this
> guide — they're not part of the AI-200 skill bullet for Event Grid (filters, custom events,
> retries). In production you'd typically restrict access with a **private endpoint** or **IP
> firewall rules** (Networking tab), and prefer **Microsoft Entra ID (managed identity)** over
> the access key this guide's Python sample uses (Security tab → **Local Authentication**).

4. **Get the endpoint and key:**
   - Open the topic resource → **Overview** for the **Topic Endpoint**
   - **Settings** → **Access keys** for **Key 1**

5. **Create an event subscription with a filter and retry policy:**
   - For the simplest endpoint, deploy an **Azure Function with an Event Grid trigger** (see the
     [Azure Functions guide](../azure-functions/)). This endpoint type handles Event Grid's
     validation automatically.
   - Use **Web Hook** when you own a public HTTPS endpoint that implements the CloudEvents
     `OPTIONS` validation handshake, or when you want to use webhook.site for the manual
     callback walkthrough below.
   - On the topic → **+ Event Subscription**
   - Name: `orders-webhook-sub`
   - **Event Schema**: **Cloud Event Schema v1.0** — this is the *delivery* schema sent to your
     handler. It matches the topic's CloudEvents input schema; CloudEvents-input topics cannot be
     delivered as Event Grid schema.
   - Endpoint type: **Azure Function** (recommended) or **Web Hook**, then configure the
     endpoint Azure asks for. If you select **Web Hook** and use webhook.site, follow the
     walkthrough below after clicking **Create**.
   - **Filters tab** → **Subject Begins With**: `orders/`
   - **Additional Features tab** → **Max event delivery attempts**: `10`, **Event
     time-to-live**: `60` minutes
   - Click **Create**

> **Webhook validation failed?** Check the selected delivery schema first. This guide uses
> CloudEvents, so a raw webhook receives HTTP `OPTIONS` and either returns permission headers or
> uses `WebHook-Request-Callback` for manual approval. The Event Grid-schema
> `SubscriptionValidationEvent` and `validationUrl` flow does not apply here.

### Optional: use webhook.site with the CloudEvents walkthrough

Most people learning Event Grid want to *see* an event arrive without building an endpoint first.
[webhook.site](https://webhook.site) works with this guide's existing **Event Grid Basic
CloudEvents topic** — do not create a second topic or change the event schema.

1. Open [webhook.site](https://webhook.site) in a browser tab and copy **Your unique URL**.

2. In [Portal Setup step 5](#portal-setup-web-ui), select **Web Hook** as the endpoint type and
   paste that unique URL as the endpoint. Keep **Event Schema** set to **Cloud Event Schema
   v1.0**, then click **Create**.

3. Return to webhook.site. It receives an HTTP `OPTIONS` validation request. Open that request,
   find its **Headers**, and copy the complete value of `webhook-request-callback`. HTTP header
   names are case-insensitive, so the site might display it as `WebHook-Request-Callback` instead.

4. Paste that exact callback URL into a browser address bar and open it promptly. The portal can
   show **AwaitingManualAction** while it waits. Event Grid then completes validation and the
   subscription succeeds. Treat this one-time URL as a secret and preserve its full query string.

> **Why it pauses:** webhook.site records the CloudEvents `OPTIONS` request, but it does not send
> the `WebHook-Allowed-Origin` and `WebHook-Allowed-Rate` headers that would approve delivery
> immediately. The `WebHook-Request-Callback` header provides the manual alternative. For a
> production webhook, implement the `OPTIONS` response; for the least setup, use an Event
> Grid-triggered Azure Function.

---

## Cleanup

```bash
# Delete the entire resource group and everything in it: topic, subscriptions.
az group delete --name "$RG" --yes --no-wait
```

> **Important:** deleting a resource group is **permanent**. Everything in it is destroyed and
> cannot be recovered.

---

## Hands-on (Python)

A small script that **publishes** custom CloudEvents to the topic created above — enough events,
with different `subject`s and `type`s, to see filtering in action if you point a subscription at
it. The code is in [`publish_events.py`](./publish_events.py) and every non-trivial line is
commented, explaining both the Python idiom and the Azure concept.

> **Remember:** run all commands below from this folder (`03-connect-consume/event-grid/`).

### 1. Create and activate a virtual environment

```bash
python -m venv .venv

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
pip install -r requirements.txt
```

### 3. Set your topic endpoint and key

> **Use a fresh `az` query here, in *this* shell session — don't reuse `$TOPIC_ENDPOINT`/
> `$TOPIC_KEY` from [CLI Setup](#cli-setup) step 4.** Those variables only exist in the shell
> they were assigned in; if step 4 and this step run in different terminals (or even just
> different `bash -c` calls), `$TOPIC_ENDPOINT` silently expands to an **empty string** and you
> get a confusing SDK error (`ValueError: ... url part topicHostname was incorrect ...`) instead
> of a clear "variable not set" message. Querying Azure directly below sidesteps that — fill in
> `$RG`/`$TOPIC` (or the resource group/topic name from the [Portal Setup](#portal-setup-web-ui))
> if you don't already have them set.

```bash
# bash / zsh
export EVENTGRID_TOPIC_ENDPOINT=$(az eventgrid topic show \
  --name "$TOPIC" --resource-group "$RG" --query endpoint --output tsv)
export EVENTGRID_TOPIC_KEY=$(az eventgrid topic key list \
  --name "$TOPIC" --resource-group "$RG" --query key1 --output tsv)
```

```fish
# fish — `set -x` is fish's equivalent of `export`
set -x EVENTGRID_TOPIC_ENDPOINT (az eventgrid topic show --name $TOPIC --resource-group $RG --query endpoint --output tsv)
set -x EVENTGRID_TOPIC_KEY (az eventgrid topic key list --name $TOPIC --resource-group $RG --query key1 --output tsv)
```

```powershell
# PowerShell
$env:EVENTGRID_TOPIC_ENDPOINT = az eventgrid topic show --name $TOPIC --resource-group $RG --query endpoint --output tsv
$env:EVENTGRID_TOPIC_KEY = az eventgrid topic key list --name $TOPIC --resource-group $RG --query key1 --output tsv
```

```bat
:: cmd
for /f "delims=" %%i in ('az eventgrid topic show --name %TOPIC% --resource-group %RG% --query endpoint --output tsv') do set EVENTGRID_TOPIC_ENDPOINT=%%i
for /f "delims=" %%i in ('az eventgrid topic key list --name %TOPIC% --resource-group %RG% --query key1 --output tsv') do set EVENTGRID_TOPIC_KEY=%%i
```

If you followed [Portal Setup](#portal-setup-web-ui) instead of the CLI, there's no `az` session
to query — paste the endpoint and key from the portal (Overview → Topic Endpoint, Settings →
Access keys) directly in place of the `EVENTGRID_TOPIC_ENDPOINT`/`EVENTGRID_TOPIC_KEY` values
above.

### 4. Run it

```bash
python publish_events.py
```

If you created an event subscription connected to an Azure Function, a CloudEvents-compatible
webhook, or webhook.site after manual validation, you'll see the `orders/12345` events arrive.
The `inventory/sku-998` event is filtered out by the `subject-begins-with "orders/"` filter from
setup step 5, and never reaches that handler.

---

## Exam gotchas

- **Push, not poll (Event Grid Basic).** Event Grid Basic calls your handler; Service Bus and
  Event Hubs are pulled from. If a scenario says "the handler must not run a polling loop," that
  is an Event Grid Basic signal.

- **Webhook validation depends on the delivery schema.** Event Grid-schema delivery uses a
  `SubscriptionValidationEvent` and `validationCode` (or its `validationUrl`); CloudEvents
  delivery uses an HTTP `OPTIONS` request, approved either by permission headers or the
  `WebHook-Request-Callback` URL. An **Event Grid-triggered Azure Function** handles the
  platform validation automatically — pick it over a raw webhook when the exam scenario wants the
  least code.

- **System topics are associated with the source, not identical to it.** You can subscribe to a
  Storage account's events via `--source-resource-id <storage-account-id>`; Event Grid can create
  the separate system-topic resource automatically.

- **CloudEvents vs. Event Grid schema** are not fully interchangeable. A CloudEvents-input topic
  can deliver only CloudEvents; an Event Grid-schema topic can deliver Event Grid schema or
  CloudEvents. Microsoft recommends CloudEvents for new work; expect the Event Grid schema in
  questions about older/system topics.

- **Topic (input) schema vs. subscription (delivery) schema are two separate settings.** A topic
  is created with one input schema (`--input-schema`, step 3); each event subscription can also
  pick a delivery schema (`--event-delivery-schema`, step 5), subject to the compatibility rules
  above.

- **Filters are ANDed.** A subject filter and an advanced filter on the same subscription must
  **both** match — they don't OR together.

- **Retry cap OR TTL, whichever comes first.** An event stops being retried at **30 delivery
  attempts or 24 hours (defaults)**, whichever happens first. Retry timing is nondeterministic,
  and expiration is evaluated at a scheduled delivery attempt.

- **At least once means duplicates are possible.** Make the handler idempotent so processing an
  already-seen event does not repeat its business effect.

- **Dead-lettering is opt-in and Blob-only.** Without a configured dead-letter endpoint, an event
  that exhausts retries is simply **dropped**, not queued anywhere for later inspection.

- **Only 200–204 = success.** Other status codes, a timeout, or an unreachable endpoint are
  failed deliveries and follow Event Grid's retry/dead-letter behavior.

- **Event Grid vs. Service Bus vs. Event Hubs** is a recurring "pick the service" question — see
  [Core concepts §6](#6-event-grid-vs-service-bus-vs-event-hubs-vs-storage-queues) for the
  distinction in plain English and in exam shorthand.

- **`subject` is what filters usually match, not `type`.** `subjectBeginsWith`/`EndsWith` filter
  on the resource path (`orders/12345`); `includedEventTypes` filters on the *kind* of event
  (`Orders.OrderCreated`). Know which one a scenario is describing.

---

## Quiz yourself

Take the **Event Grid** quiz in the [quiz app](../../quiz/)
(bank: [`quiz/src/questions/03-connect-consume/event-grid.json`](../../quiz/src/questions/03-connect-consume/event-grid.json)).

---

## Further reading

- Event Grid overview: <https://learn.microsoft.com/azure/event-grid/overview>
- Event schemas (Event Grid vs. CloudEvents): <https://learn.microsoft.com/azure/event-grid/event-schema>
- Event filtering: <https://learn.microsoft.com/azure/event-grid/event-filtering>
- Delivery and retry: <https://learn.microsoft.com/azure/event-grid/delivery-and-retry>
- Endpoint validation (CloudEvents schema): <https://learn.microsoft.com/azure/event-grid/end-point-validation-cloud-events-schema>
- Endpoint validation (Event Grid schema): <https://learn.microsoft.com/azure/event-grid/end-point-validation-event-grid-events-schema>
- CloudEvents webhook callback specification: <https://github.com/cloudevents/spec/blob/v1.0/http-webhook.md>
- System topics: <https://learn.microsoft.com/azure/event-grid/system-topics>
- Compare messaging services: <https://learn.microsoft.com/azure/event-grid/compare-messaging-services>
- Python SDK reference: <https://learn.microsoft.com/python/api/overview/azure/eventgrid-readme>
