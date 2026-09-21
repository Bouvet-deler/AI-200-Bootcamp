# Azure Service Bus

**Domain:** 03 — Connect to and consume Azure services (20–25%)
**Maps to skill:** *Queue and process back-end operations by using Azure Service Bus,
including dead-letter queue handling, messages, topics, and subscriptions*

---

## What it is

**Azure Service Bus** is an enterprise **message broker**: it accepts a message from one
application, stores it durably, and lets another application retrieve it later. That gap in
time is useful. An API can accept an order quickly, put *"charge and fulfil order 123"* on
Service Bus, and let one or more background workers process the work when they are available.
The sender and the worker do not need to be online at the same moment or run at the same speed.

Service Bus has two main delivery shapes:

- A **queue** distributes each message to **one** receiver. If several workers compete for the
  queue, only one gets a particular delivery. Use it for a command or job such as *"create this
  invoice."* Peek-Lock redelivery is possible, so the worker must be idempotent rather than assume
  exactly-once processing.
- A **topic** publishes a copy of a message to every matching **subscription**. A subscription
  is a durable, virtual queue under the topic, so each independent consumer gets its own copy.
  Use it for *"an order was placed"* when billing, shipping, and analytics should all react.

> Mental model:
>
> ```text
> QUEUE — one job, one competing worker
>
> API / producer ──send──▶ [ orders queue ] ──receive──▶ worker A
>                                              └────────▶ worker B
>                         One durable message; A OR B processes it.
>
> TOPIC — one published message, many independent subscriptions
>
> publisher ──send──▶ [ order-events topic ]
>                           ├──▶ [ shipping subscription ] ──▶ shipping worker
>                           ├──▶ [ billing subscription  ] ──▶ billing worker
>                           └──▶ [ analytics subscription] ──▶ analytics worker
> ```

Unlike Azure Event Grid, which normally **pushes** a lightweight notification to a handler,
Service Bus keeps the business message until a receiver explicitly finishes with it. Receivers
usually **pull** messages from queues or subscriptions. That durable, acknowledged processing
is why Service Bus fits important business work.

---

## Why it's on the exam

The skill bullet is *"Queue and process back-end operations by using Azure Service Bus,
including dead-letter queue handling, messages, topics, and subscriptions."* Expect questions
that ask you to:

- Pick a **queue** for one worker to process a job, or a **topic plus subscriptions** to fan the
  same message out to independent consumers.
- Choose **Peek-Lock** (the default, reliable receive mode) instead of **Receive-and-Delete**,
  and know when a message is completed, retried, or lost.
- Diagnose and drain the built-in **dead-letter queue (DLQ)** after a message repeatedly fails,
  expires, or is explicitly rejected by application code.
- Recognize that a consumer reads from a **subscription**, never directly from a topic.
- Use **sessions** when strict ordered processing matters, and understand why
  at-least-once delivery requires idempotent processing.
- Pick Service Bus over Event Grid, Event Hubs, or Storage Queues when the wording says
  *reliable business command*, *transaction*, *lock*, *dead-letter queue*, or *ordered work*.

---

## Core concepts

### 1. Namespace and messaging entities

A **namespace** is the top-level Service Bus resource. It gives your messaging entities an
address such as `your-namespace.servicebus.windows.net` and forms an administration, networking,
and authentication boundary.

```text
Service Bus namespace
├── queue: orders
├── queue: image-work
└── topic: order-events
    ├── subscription: all-orders
    └── subscription: high-priority-orders
```

| Tier | What to remember for AI-200 |
| --- | --- |
| **Basic** | Queues only. It does not support topics and subscriptions. |
| **Standard** | Supports queues, topics, subscriptions, sessions, duplicate detection, and the normal broker features used in this guide. |
| **Premium** | Uses dedicated messaging capacity and offers higher, more predictable capacity and isolation. Choose it when those production requirements justify the cost. |

> **Exam shortcut:** a scenario that needs a **topic** or **subscription** cannot use the Basic
> tier. The setup below uses **Standard** so it can demonstrate both queues and pub/sub.

### 2. Queue vs. topic and subscription

| Concept | Delivery pattern | What receives a message | Typical example |
| --- | --- | --- | --- |
| **Queue** | Point-to-point / competing consumers | One receiver per delivery; a retry can redeliver it | Send a background worker one invoice to create |
| **Topic** | Publish/subscribe | Nothing reads from the topic directly | Publish that an order was placed |
| **Subscription** | Durable copy of a topic's messages | One or more receivers of that subscription | Let shipping and billing independently process the order |

A topic can have many subscriptions. Every subscription has its **own** message store, receiver
locks, rules, metrics, and DLQ. A message that matches two subscriptions creates two independent
copies; completing one copy does not affect the other.

**Subscription rules** decide which messages are copied into a subscription. A newly created
subscription has a `$Default` rule whose `TrueFilter` accepts every topic message. If you add a
filter and want only matching messages, remove that default rule first. Service Bus supports
SQL-like filters and faster correlation filters; both inspect message properties, not the message
body.

> **Exam gotcha:** a message is sent **to a topic** but received **from a subscription**. A topic
> is not a queue with an extra name.

### 3. Message body and properties

A Service Bus message combines your payload with metadata that the broker and your application
can use:

| Part | Purpose | Examples |
| --- | --- | --- |
| **Body** | The actual work or event data | JSON describing order 123 |
| **System properties** | Standard message metadata understood by Service Bus | `MessageId`, `CorrelationId`, `SessionId`, `TimeToLive`, `Subject` |
| **Application properties** | Key/value metadata your application defines | `priority = "high"`, `tenant = "contoso"` |

The Python SDK uses snake_case names such as `message_id` and
`application_properties`. In a topic, subscription rules can match application or system
properties without parsing the body. For example, the setup filters on
`priority = 'high'`.

Use a meaningful, stable **MessageId**. It helps trace work, supports duplicate detection, and
gives an idempotent consumer something it can record after it has completed the business action.
Use **CorrelationId** to connect related requests and replies. Use **SessionId** to group work
that must be processed in order.

### 4. Receiving, locks, and settlement

When a receiver asks for a message, it chooses a **receive mode**:

| Receive mode | What happens when the receiver gets the message | Delivery guarantee / trade-off |
| --- | --- | --- |
| **Peek-Lock** (default) | Service Bus locks the message. The receiver must explicitly settle it. | At-least-once processing: safe against a worker crash, but duplicates are possible. |
| **Receive-and-Delete** | Service Bus removes the message as soon as it sends it to the receiver. | At-most-once processing: a crash after receipt loses the message. |

Peek-Lock is the normal answer for important work:

```text
active message ──receive──▶ locked message ──complete──▶ removed permanently
                                  │
                                  ├── abandon / lock expires ──▶ active again (redelivery)
                                  │
                                  └── dead-letter ──▶ built-in DLQ
```

The four important **settlement** operations are:

- **Complete** — the work succeeded; remove the message permanently.
- **Abandon** — the work failed temporarily; release the lock so it can be delivered again.
- **Dead-letter** — the work is known to be bad or needs investigation; move it to the DLQ with
  a reason and description.
- **Defer** — set the message aside temporarily. It remains in the entity but can only be
  retrieved later by its sequence number; it is not a retry or DLQ mechanism.

The default lock duration is one minute and an entity can set it up to five minutes. If normal
processing exceeds the lock, renew it (or use the SDK's automatic lock renewal helper). Never
complete a message before its business work is safely finished.

> **Exam gotcha:** Peek-Lock prevents silent message loss, not duplicate delivery. A worker can
> finish its database update and then lose its connection before `complete` reaches Service Bus.
> Service Bus redelivers the message, so make the worker **idempotent** — processing the same
> `MessageId` or business key twice has the same effect as processing it once.

### 5. Dead-letter queues (DLQs)

Every **queue** and every **subscription** has its own built-in **dead-letter subqueue**. You do
not create, name, or delete it separately. A topic itself does not have a receiver or DLQ; its
subscriptions do.

Messages reach a DLQ when:

- Their delivery count exceeds the entity's `MaxDeliveryCount` after repeated abandons or
  expired locks (default: 10).
- They expire **and** the entity is configured to dead-letter expired messages.
- Your receiver explicitly calls the dead-letter operation with a reason and description.
- A subscription rule evaluation fails because of an error **and** the subscription's
  dead-letter-on-filter-evaluation-exceptions option is enabled. A message that simply does
  **not** match a rule is not a failure and is not dead-lettered; it is just not copied to that
  subscription.

The DLQ has no automatic cleanup and does not observe normal message TTL. Messages stay there
until a receiver deliberately completes them. A practical repair flow is:

1. **Receive and inspect** the DLQ message, including its body, `dead_letter_reason`, and
   `dead_letter_error_description`.
2. **Fix the underlying problem** — for example, correct invalid data or deploy a consumer fix.
3. **Create a new corrected message** and send it to the original queue or topic.
4. **Complete the DLQ copy** only after the corrected message has been accepted.

> **Exam gotcha:** completing a DLQ message deletes that DLQ copy. It does not automatically
> return it to the main queue. Reprocessing is an explicit application decision.

### 6. Sessions, duplicate detection, and transactions

These Service Bus features make a brokered workflow more controlled:

- **Sessions** provide FIFO **processing within one related group**. Enable sessions when you
  create the queue or subscription, set the same `SessionId` on related messages (for example,
  one order ID), and use a session-aware receiver. Different session IDs can be processed in
  parallel. A plain queue's enqueue order alone is not a guarantee of processing order when
  multiple workers run at different speeds.
- **Duplicate detection** keeps a history of `MessageId` values for a configured time window and
  discards a repeated send with the same ID during that window. It is supported in Standard and
  Premium. It protects a sender retry; it does **not** remove the need for idempotent receivers.
- **Transactions** group supported Service Bus operations so they either all commit or all roll
  back. A common pattern is to complete an input message and send its next-step message as one
  all-or-nothing broker operation. It is not an end-to-end transaction with your database, and
  transaction APIs vary by client library; the Python walkthrough below does not demonstrate one.

### 7. Choosing the messaging service

| Need | Best fit | Why |
| --- | --- | --- |
| Reliably process a business command; use locks, DLQ, sessions, or transactions | **Service Bus** | Durable brokered messages and explicit settlement |
| Notify many handlers that something happened; do not poll | **Event Grid** | Push-based event routing |
| Ingest and replay a high-volume telemetry stream | **Event Hubs** | Partitioned event stream, not per-message work completion |
| Use a simple, low-cost work queue without Service Bus features | **Azure Storage Queues** | Basic durable queueing |

---

## Setup

Goal: create a **Standard** Service Bus namespace, a queue configured for dead-lettering, and a
topic with both an all-orders and a high-priority subscription.

**Prerequisites:** an Azure subscription, permission to create resources and role assignments, the
[Azure CLI](https://learn.microsoft.com/cli/azure/) installed, and `az login` completed.

**Region:** this walkthrough uses `westeurope`. Use a region that is appropriate for your
workload and supports the chosen Service Bus tier.

**Shell:** the CLI blocks use **bash** syntax. Azure Cloud Shell's Bash mode is the simplest
copy-paste environment.

> **Two methods available:**
>
> - [CLI](#cli-setup) — copy-paste commands
> - [Azure Portal](#portal-setup-web-ui) — point and click in the browser

### Set your variables

- `RG` — resource group
- `LOCATION` — Azure region
- `NAMESPACE` — globally unique Service Bus namespace name; the timestamp supplies a likely-unique
  suffix
- `QUEUE` — queue used by the Python sample
- `TOPIC` — topic used to show fan-out and filtering

```bash
# bash / zsh, including Azure Cloud Shell in Bash mode
RG="ai200-servicebus-rg"
LOCATION="westeurope"
NAMESPACE="ai200-sb-$(date +%s)"
QUEUE="orders"
TOPIC="order-events"
ALL_SUBSCRIPTION="all-orders"
PRIORITY_SUBSCRIPTION="high-priority-orders"
```

```powershell
# PowerShell - Windows (also cross-platform)
$RG = "ai200-servicebus-rg"
$LOCATION = "westeurope"
$NAMESPACE = "ai200-sb-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
$QUEUE = "orders"
$TOPIC = "order-events"
$ALL_SUBSCRIPTION = "all-orders"
$PRIORITY_SUBSCRIPTION = "high-priority-orders"
```

```bat
:: Command Prompt (cmd.exe) - Windows
set RG=ai200-servicebus-rg
set LOCATION=westeurope
set NAMESPACE=ai200-sb-%RANDOM%%RANDOM%
set QUEUE=orders
set TOPIC=order-events
set ALL_SUBSCRIPTION=all-orders
set PRIORITY_SUBSCRIPTION=high-priority-orders
```

### CLI Setup

Run these commands after [setting the variables](#set-your-variables). `az group create` is
safe to re-run; resource creation commands are idempotent when their properties do not conflict.

<details open>
<summary>Bash CLI Setup</summary>

```bash
# 1. Create the resource group — a logical container for the namespace and its entities.
az group create --name "$RG" --location "$LOCATION"

# 2. Create the namespace. Standard is required because this walkthrough creates a topic and
#    subscriptions; Basic supports queues only.
az servicebus namespace create \
  --resource-group "$RG" \
  --name "$NAMESPACE" \
  --location "$LOCATION" \
  --sku Standard

# 3. Create the queue used by the Python walkthrough.
#    --max-delivery-count 3 makes a repeated failure reach the DLQ quickly in a lab.
#    --enable-dead-lettering-on-message-expiration means expired messages are retained in the
#    DLQ rather than silently discarded.
az servicebus queue create \
  --resource-group "$RG" \
  --namespace-name "$NAMESPACE" \
  --name "$QUEUE" \
  --max-delivery-count 3 \
  --enable-dead-lettering-on-message-expiration true

# 4. Create a topic and an all-orders subscription. Every topic subscription begins with a
#    $Default TrueFilter, so this subscription receives every message sent to the topic.
az servicebus topic create \
  --resource-group "$RG" \
  --namespace-name "$NAMESPACE" \
  --name "$TOPIC"

az servicebus topic subscription create \
  --resource-group "$RG" \
  --namespace-name "$NAMESPACE" \
  --topic-name "$TOPIC" \
  --name "$ALL_SUBSCRIPTION"

# 5. Create a second subscription, then replace its default "accept everything" rule with a
#    SQL filter. This subscription receives only messages whose application property named
#    priority equals the string "high".
az servicebus topic subscription create \
  --resource-group "$RG" \
  --namespace-name "$NAMESPACE" \
  --topic-name "$TOPIC" \
  --name "$PRIORITY_SUBSCRIPTION" \
  --enable-dead-lettering-on-message-expiration true

# Single quotes stop bash from expanding $Default as a shell variable.
az servicebus topic subscription rule delete \
  --resource-group "$RG" \
  --namespace-name "$NAMESPACE" \
  --topic-name "$TOPIC" \
  --subscription-name "$PRIORITY_SUBSCRIPTION" \
  --name '$Default'

az servicebus topic subscription rule create \
  --resource-group "$RG" \
  --namespace-name "$NAMESPACE" \
  --topic-name "$TOPIC" \
  --subscription-name "$PRIORITY_SUBSCRIPTION" \
  --name "high-priority-only" \
  --filter-sql-expression "priority = 'high'"

# 6. Authorize the signed-in Microsoft Entra user for only the data operations this script needs.
#    The sample touches several entities, so these two roles are scoped to the lab namespace. A
#    production sender-only or receiver-only app should receive only its role at entity scope.
SIGNED_IN_USER_ID=$(az ad signed-in-user show --query id --output tsv)
NAMESPACE_ID=$(az servicebus namespace show \
  --resource-group "$RG" \
  --name "$NAMESPACE" \
  --query id \
  --output tsv)

az role assignment create \
  --assignee-object-id "$SIGNED_IN_USER_ID" \
  --assignee-principal-type User \
  --role "69a216fc-b8fb-44d8-bc22-1f3c2cd27a39" \
  --scope "$NAMESPACE_ID"

az role assignment create \
  --assignee-object-id "$SIGNED_IN_USER_ID" \
  --assignee-principal-type User \
  --role "4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0" \
  --scope "$NAMESPACE_ID"

# Require Microsoft Entra ID by disabling Shared Access Signature (local) authentication.
az servicebus namespace update \
  --resource-group "$RG" \
  --name "$NAMESPACE" \
  --disable-local-auth true
```

</details>

<details>
<summary>PowerShell CLI Setup</summary>

```powershell
az group create --name $RG --location $LOCATION

az servicebus namespace create `
  --resource-group $RG --name $NAMESPACE --location $LOCATION --sku Standard

az servicebus queue create `
  --resource-group $RG --namespace-name $NAMESPACE --name $QUEUE `
  --max-delivery-count 3 --enable-dead-lettering-on-message-expiration true

az servicebus topic create `
  --resource-group $RG --namespace-name $NAMESPACE --name $TOPIC

az servicebus topic subscription create `
  --resource-group $RG --namespace-name $NAMESPACE --topic-name $TOPIC `
  --name $ALL_SUBSCRIPTION

az servicebus topic subscription create `
  --resource-group $RG --namespace-name $NAMESPACE --topic-name $TOPIC `
  --name $PRIORITY_SUBSCRIPTION --enable-dead-lettering-on-message-expiration true

az servicebus topic subscription rule delete `
  --resource-group $RG --namespace-name $NAMESPACE --topic-name $TOPIC `
  --subscription-name $PRIORITY_SUBSCRIPTION --name '$Default'

az servicebus topic subscription rule create `
  --resource-group $RG --namespace-name $NAMESPACE --topic-name $TOPIC `
  --subscription-name $PRIORITY_SUBSCRIPTION --name high-priority-only `
  --filter-sql-expression "priority = 'high'"

$SIGNED_IN_USER_ID = az ad signed-in-user show --query id --output tsv
$NAMESPACE_ID = az servicebus namespace show `
  --resource-group $RG --name $NAMESPACE --query id --output tsv

az role assignment create `
  --assignee-object-id $SIGNED_IN_USER_ID --assignee-principal-type User `
  --role "69a216fc-b8fb-44d8-bc22-1f3c2cd27a39" --scope $NAMESPACE_ID
az role assignment create `
  --assignee-object-id $SIGNED_IN_USER_ID --assignee-principal-type User `
  --role "4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0" --scope $NAMESPACE_ID

az servicebus namespace update `
  --resource-group $RG --name $NAMESPACE --disable-local-auth true
```

</details>

<details>
<summary>Command Prompt (cmd.exe) CLI Setup</summary>

```bat
az group create --name %RG% --location %LOCATION%

az servicebus namespace create ^
  --resource-group %RG% --name %NAMESPACE% --location %LOCATION% --sku Standard

az servicebus queue create ^
  --resource-group %RG% --namespace-name %NAMESPACE% --name %QUEUE% ^
  --max-delivery-count 3 --enable-dead-lettering-on-message-expiration true

az servicebus topic create ^
  --resource-group %RG% --namespace-name %NAMESPACE% --name %TOPIC%

az servicebus topic subscription create ^
  --resource-group %RG% --namespace-name %NAMESPACE% --topic-name %TOPIC% ^
  --name %ALL_SUBSCRIPTION%

az servicebus topic subscription create ^
  --resource-group %RG% --namespace-name %NAMESPACE% --topic-name %TOPIC% ^
  --name %PRIORITY_SUBSCRIPTION% --enable-dead-lettering-on-message-expiration true

az servicebus topic subscription rule delete ^
  --resource-group %RG% --namespace-name %NAMESPACE% --topic-name %TOPIC% ^
  --subscription-name %PRIORITY_SUBSCRIPTION% --name $Default

az servicebus topic subscription rule create ^
  --resource-group %RG% --namespace-name %NAMESPACE% --topic-name %TOPIC% ^
  --subscription-name %PRIORITY_SUBSCRIPTION% --name high-priority-only ^
  --filter-sql-expression "priority = 'high'"

for /f "delims=" %%I in ('az ad signed-in-user show --query id --output tsv') do set SIGNED_IN_USER_ID=%%I
for /f "delims=" %%I in ('az servicebus namespace show --resource-group %RG% --name %NAMESPACE% --query id --output tsv') do set NAMESPACE_ID=%%I

az role assignment create ^
  --assignee-object-id %SIGNED_IN_USER_ID% --assignee-principal-type User ^
  --role "69a216fc-b8fb-44d8-bc22-1f3c2cd27a39" --scope %NAMESPACE_ID%
az role assignment create ^
  --assignee-object-id %SIGNED_IN_USER_ID% --assignee-principal-type User ^
  --role "4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0" --scope %NAMESPACE_ID%

az servicebus namespace update ^
  --resource-group %RG% --name %NAMESPACE% --disable-local-auth true
```

</details>

> The `$Default` deletion matters. If it remains alongside `high-priority-only`, the default
> true rule accepts every topic message and the high-priority subscription is not filtered.

### Portal Setup (Web UI)

Prefer the browser? Create the same resources in the
[Azure portal](https://portal.azure.com):

1. Create a **Resource group** named `ai200-servicebus-rg` in **West Europe**.
2. Select **Create a resource** → search for **Service Bus** → **Create**.
   - Choose the resource group.
   - Enter a globally unique namespace name.
   - Select **Standard** pricing tier. Basic cannot create topics/subscriptions.
   - Select **Review + create** → **Create**.
3. Open the new namespace. Under **Entities** → **Queues**, create `orders`.
   - Set **Max delivery count** to `3` for the lab.
   - Enable **dead lettering on message expiration**.
   - Leave sessions disabled; this particular sample does not use them.
4. Under **Entities** → **Topics**, create `order-events`. Open it and create two
   subscriptions: `all-orders` and `high-priority-orders`.
5. Open **high-priority-orders**. On its **Overview** page, select **Filters** — the portal
   label; Azure CLI and the Service Bus API call the underlying objects **rules**.
   - Delete the `$Default` filter.
   - Add a filter named `high-priority-only` with **SQL filter**:
     `priority = 'high'`.
   - Leave `all-orders` with its `$Default` rule.
6. Open **Access control (IAM)** and assign your signed-in developer account both **Azure Service
   Bus Data Sender** and **Azure Service Bus Data Receiver** for this lab namespace. Role
   assignments can take several minutes to become effective.
7. On the namespace **Overview** page, select the current **Local Authentication** value, choose
   **Disabled**, and confirm. The Python walkthrough uses Microsoft Entra ID, not a connection
   string. In a deployed application, assign these same narrowly scoped roles to its managed
   identity instead of a developer account.

---

## Cleanup

```bash
# Delete the whole resource group, including the namespace, its entities, and messages.
az group delete --name "$RG" --yes --no-wait
```

> **Important:** resource-group deletion is permanent. All messages in the queues, subscriptions,
> and DLQs are destroyed.

---

## Hands-on (Python)

The small runnable script [send_receive_deadletter.py](./send_receive_deadletter.py) does four
things against the resources above:

1. Sends a valid and an intentionally invalid message to the queue.
2. Receives the queue messages in Peek-Lock mode, completes the valid one, and explicitly
   dead-letters the invalid one.
3. Reads the DLQ, prints the recorded reason, and completes the DLQ copy so the lab is clean.
4. Publishes one high- and one normal-priority message to the topic, then shows that
   `all-orders` gets both while `high-priority-orders` gets only the high-priority copy.

> **Use a dedicated lab namespace.** The script intentionally settles every message it receives,
> so do not point it at a shared production queue or subscription.

> **Remember:** run the commands below from the Service Bus topic folder.

### 1. Create and activate a virtual environment

```bash
# Create .venv, an isolated folder for this topic's Python packages.
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

### 2. Install the dependency

```bash
pip install -r requirements.txt
```

### 3. Configure the environment

The script reads the namespace host and entity names from environment variables. Authentication is
passwordless: `DefaultAzureCredential` reuses the developer identity from `az login` locally and
can use a managed identity when the same code runs in Azure.

```bash
# DefaultAzureCredential can reuse this Azure CLI developer login.
az login
export SERVICEBUS_FULLY_QUALIFIED_NAMESPACE="${NAMESPACE}.servicebus.windows.net"
export SERVICEBUS_QUEUE_NAME="$QUEUE"
export SERVICEBUS_TOPIC_NAME="$TOPIC"
export SERVICEBUS_ALL_SUBSCRIPTION_NAME="$ALL_SUBSCRIPTION"
export SERVICEBUS_PRIORITY_SUBSCRIPTION_NAME="$PRIORITY_SUBSCRIPTION"
```

If you followed the portal path, use the namespace hostname shown on **Overview** and the entity
names you chose:

```bash
az login
export SERVICEBUS_FULLY_QUALIFIED_NAMESPACE="<namespace>.servicebus.windows.net"
export SERVICEBUS_QUEUE_NAME="orders"
export SERVICEBUS_TOPIC_NAME="order-events"
export SERVICEBUS_ALL_SUBSCRIPTION_NAME="all-orders"
export SERVICEBUS_PRIORITY_SUBSCRIPTION_NAME="high-priority-orders"
```

Replace `<namespace>` with the namespace name. Do not include `sb://` or a path. The signed-in
identity must have both data roles from setup; Contributor alone does not grant data-plane access.

### 4. Run it

```bash
python send_receive_deadletter.py
```

On an empty lab namespace, the output shows one normal queue message completed, one moved to and
then removed from the DLQ, two topic messages read from `all-orders`, and only the high-priority
message read from `high-priority-orders`.

---

## Exam gotchas

- **Queue vs. topic:** a queue gives one message to one competing consumer. A topic makes a
  separate durable copy for each matching subscription.

- **Receive from a subscription, not a topic.** Senders target a topic; consumers target one of
  its subscriptions.

- **Every new subscription starts with `$Default` / `TrueFilter`.** To make a subscription
  selective, delete that rule and add a SQL or correlation rule. A nonmatching message is not a
  DLQ failure; it simply never enters that subscription.

- **Peek-Lock is the default.** Complete only after successful processing. If the lock expires
  or the message is abandoned, Service Bus can redeliver it — design for duplicates.

- **Receive-and-Delete trades reliability for speed.** Service Bus removes the message before
  your code processes it, so a crash loses the work. Do not choose it for an important order,
  payment, or command.

- **A DLQ is built in per queue and per subscription.** It is not the Event Grid Blob
  dead-letter destination, and it is not shared by a topic's subscriptions.

- **Max delivery count and expiration are different triggers.** Exceeding max delivery moves a
  repeatedly failed message to the DLQ. Expiration only moves a message there when
  dead-letter-on-expiration is enabled; otherwise the expired message is discarded.

- **DLQs do not clean themselves.** Inspect, correct/recreate, resubmit, then complete the DLQ
  copy. Completing it first loses that copy.

- **FIFO processing needs sessions.** Normal enqueue sequence is not enough when multiple
  workers process at different speeds. Enable sessions and use a common `SessionId` for related
  messages.

- **Duplicate detection is sender-side protection, not end-to-end exactly once.** It discards a
  repeated `MessageId` within its configured window; a Peek-Lock consumer can still receive a
  message again after a failed settlement.

- **Service Bus vs. Event Grid:** choose Service Bus for reliable, durable work that needs an
  explicit completion; choose Event Grid to push a small notification that something happened.

- **Prefer Microsoft Entra ID and managed identity.** Grant a sender only **Azure Service Bus Data
  Sender** and a receiver only **Azure Service Bus Data Receiver**, scoped to the smallest entity.
  Management-plane Contributor does not grant send/receive permission. Disable local/SAS
  authentication after clients are migrated.

---

## Quiz yourself

Take the **Azure Service Bus** quiz in the [quiz app](../../quiz/) (bank:
[quiz/src/questions/03-connect-consume/service-bus.json](../../quiz/src/questions/03-connect-consume/service-bus.json)).

---

## Further reading

- [Azure Service Bus overview](https://learn.microsoft.com/azure/service-bus-messaging/service-bus-messaging-overview)
- [Queues, topics, and subscriptions](https://learn.microsoft.com/azure/service-bus-messaging/service-bus-queues-topics-subscriptions)
- [Message transfers, locks, and settlement](https://learn.microsoft.com/azure/service-bus-messaging/message-transfers-locks-settlement)
- [Dead-letter queues](https://learn.microsoft.com/azure/service-bus-messaging/service-bus-dead-letter-queues)
- [Message sessions and FIFO processing](https://learn.microsoft.com/azure/service-bus-messaging/message-sessions)
- [Duplicate detection](https://learn.microsoft.com/azure/service-bus-messaging/duplicate-detection)
- [Topic filters and rules](https://learn.microsoft.com/azure/service-bus-messaging/topic-filters)
- [Service Bus authentication and authorization](https://learn.microsoft.com/azure/service-bus-messaging/service-bus-authentication-and-authorization)
- [Disable local authentication](https://learn.microsoft.com/azure/service-bus-messaging/disable-local-authentication)
- [Azure Service Bus client library for Python](https://learn.microsoft.com/python/api/overview/azure/servicebus-readme)
