# Azure App Configuration

**Domain:** 04 — Secure, monitor, troubleshoot Azure solutions (20–25%)
**Maps to skill:** *Store and retrieve app configuration information by using Azure App
Configuration*

> Follows [`docs/TOPIC_TEMPLATE.md`](../../docs/TOPIC_TEMPLATE.md). The fully-written
> [KQL guide](../kql/) is the depth/style bar this page matches.

---

## What it is

**Azure App Configuration** is a managed service that stores your application's **settings** —
the non-secret knobs your app reads at startup or runtime: feature toggles, connection *targets*
(not passwords), timeouts, page sizes, endpoints. Instead of every service carrying its own
`appsettings.json` / `.env` file that drifts out of sync, they all read from **one central
store**.

Two names you'll see together, and how they differ:

- **App Configuration** — holds **configuration** (non-secret values) and **feature flags**.
  Think "the settings your app needs."
- **Key Vault** — holds **secrets** (passwords, API keys, certificates). Think "the credentials
  your app needs." (See the sibling topic [`../key-vault/`](../key-vault/).)

> Mental model: **config lives in App Configuration; secrets live in Key Vault.** App
> Configuration can hold a **Key Vault reference** — a pointer (URI) to a secret — so your app
> reads *one* store and App Configuration hands back the secret's location. The secret value
> itself never sits in App Configuration.

A stored item is just a **key–value pair** (like a dictionary entry). You read it back by key —
optionally narrowed by a **label** (more on that below):

```text
key:   "Ordering:MaxItemsPerPage"     # ':' is a naming convention for hierarchy, not a folder
value: "50"
label: "prod"                          # same key can have a different value per environment
```

---

## Why it's on the exam

The skill bullet is *"Store and retrieve app configuration information by using Azure App
Configuration."* Expect the exam to test:

- **Reading and writing keys** from code (the Python SDK) and CLI.
- **Labels** — the mechanism for per-environment values (`dev` / `prod`) from *one* key.
- **Feature flags / feature management** — turning features on/off without redeploying.
- **Key Vault references** — how App Configuration points at a secret, and the fact that your
  app still needs its *own* Key Vault permission to resolve it.
- **How the app authenticates** — access-key **connection string** vs **Entra ID + RBAC**
  (managed identity). The passwordless path is the recommended one.

You mostly need to *recognize* which feature solves a scenario ("different value per
environment" → labels; "toggle a feature off in prod" → feature flag; "keep the DB password out
of config" → Key Vault reference).

---

## Core concepts

App Configuration data is a flat list of **key–value pairs**. A few ideas turn that flat list
into something usable:

| Term | What it is |
| --- | --- |
| **Key–value** | The unit of storage: a `key`, its `value`, and optional `label`/`content-type`. |
| **Key namespacing** | By convention keys use `:` to imply hierarchy, e.g. `App:Api:Timeout`. It's just a naming style — App Configuration doesn't have real folders. |
| **Label** | An optional second axis on a key. The *same* key can hold a different value per label (`dev`, `prod`, `""`). This is how you get per-environment config from one key. |
| **Content type** | A free-form tag on a value. Feature flags and Key Vault references use special content types. Only feature flags also require the reserved `.appconfig.featureflag/` key prefix; a Key Vault reference can use an ordinary key such as `Database:ConnectionString`. |
| **Feature flag** | A specially-namespaced key (prefix `.appconfig.featureflag/`) whose JSON value describes whether a feature is on — optionally via **filters** (percentage, targeting, time window). See [Feature flags in depth](#feature-flags-in-depth). |
| **Key Vault reference** | A key whose value is a **URI pointing at a Key Vault secret** (not the secret itself). The app resolves the real value from Key Vault at read time. |
| **Snapshot** | An **immutable, named, point-in-time** set of key-values. Good for pinning a known-good config or rolling back. |
| **Soft delete** | *(Standard/Premium only)* A deleted store is retained for a recovery window; the *name* stays reserved until you **purge** it. |

**Access to the data — two ways to authenticate:**

- **Connection string (access key).** A single string containing an endpoint + secret key.
  Simplest to start with; what this topic's sample uses. Downside: it's a shared secret you
  must protect and rotate.
- **Entra ID + RBAC (recommended).** Your app's **managed identity** (or your `az login`
  identity in dev) is granted a **data-plane role** on the store, and the SDK authenticates with
  a token — **no secret to store**. The two roles you must know:
  - **App Configuration Data Reader** — read key-values.
  - **App Configuration Data Owner** — read *and* write key-values.

  > Gotcha: the older **Contributor** role manages the *resource* (create/delete the store) but
  > does **not** grant data-plane read/write. You need the **Data Reader/Owner** roles to touch
  > the key-values.

**Two client libraries (know both names):**

- **`azure-appconfiguration`** — the raw SDK. You call `get_configuration_setting(...)` /
  `set_configuration_setting(...)` explicitly. This topic's `app.py` uses it.
- **`azure-appconfiguration-provider`** — a higher-level *provider* that **loads settings into a
  dict-like object** in one call (`load(...)`), supports refresh, and integrates feature
  management. It resolves Key Vault references when you also configure a Key Vault credential,
  client, or resolver. This is the pattern Azure recommends for application consumption.

### Provider loading and refresh

The Python provider loads settings with **no label** by default. Use ordered
`SettingSelector` entries to load a base set and then an environment override; when two selectors
return the same key, the later selector wins. Labels organize values, but they are not separate
security boundaries. Use separate stores when development and production require different access
permissions.

Refresh is activity-driven. Setting `refresh_enabled=True` allows the provider to check for
changes, but your application still calls `config.refresh()` (for example, before handling a web
request). The provider does not run a background refresh loop while the app is idle. Key Vault
secret refresh is configured independently because the reference URI can remain unchanged when
the underlying secret gains a new version.

### Feature flags in depth

A fair question: *a feature flag is stored like any other key and the app still has to re-read
it to see a change — so how is it different from a plain `UseBetaCheckout = "true"` key?*

**Mechanically, it barely is.** "Change it without redeploying" is true of *every* App
Configuration key, not just flags — so that's **not** the real reason to use one. The actual
payoff is **feature filters: the flag can be *conditionally* on.**

A plain key stores a bare string you interpret yourself. A feature flag stores a **structured
JSON** that a **feature-management library** knows how to evaluate:

```json
{
  "id": "BetaCheckout",
  "enabled": true,
  "conditions": {
    "client_filters": [
      { "name": "Microsoft.Targeting",
        "parameters": { "Audience": { "DefaultRolloutPercentage": 10 } } }
    ]
  }
}
```

The two built-in filters in the current Python `featuremanagement` package are:

- **Targeting** (`Microsoft.Targeting`) — on for a **stable** share of users, plus explicit
  include/exclude lists for users or groups. This is the filter for a gradual rollout (details
  below).
- **Time window** (`Microsoft.TimeWindow`) — on between configured start and end times, with
  recurrence support for scheduled releases.

The service can also store custom filter definitions. Your application must register code that
implements a custom filter before evaluating a flag that uses it. Do not assume that a filter
available in another language's feature-management package is built into the Python package.

#### Where does the rollout logic actually run?

This is the key mental model, and it's the part that's easy to get backwards:

> **App Configuration only *stores* the rule (the JSON above). It never evaluates it.**
> The **feature-management library running inside your app** does the math, at the moment you
> ask `is_enabled(...)`.

```text
  App Configuration            Your application
  ┌────────────────┐           ┌───────────────────────────────────────────┐
  │ BetaCheckout   │  load()   │ feature-management library                 │
  │  enabled: true │ ────────▶ │  is_enabled("BetaCheckout", user="alice")  │
  │  rollout: 10%  │           │   → hashes alice+feature → 37 → 37 < 10? no │
  └────────────────┘           │   → returns False for alice                │
                               └───────────────────────────────────────────┘
```

So the "10%" is just a *number* App Configuration holds. Your app supplies **who** the current
user is; the library decides whether that user falls in the 10%.

#### How "10% of users" works (the Targeting filter)

You might expect it to keep a counter ("have I let in 10% yet?") — it doesn't. That would need
shared state and wouldn't be stable. Instead it's **deterministic hashing**:

1. For the current user, the Python library computes a SHA-256 hash of
   `userId + "\n" + featureName` and maps part of that hash to a percentage from 0 to 100.
2. If that value is **below the rollout percentage**, the feature is **on** for this user.

Because the hash is deterministic, the properties you want fall out for free:

- **Sticky per user** — Alice hashes to the same bucket every request, so she doesn't see the
  feature flicker on and off between page loads.
- **~10% of the user base** — buckets are evenly spread, so ~10 of every 100 users land below 10.
- **Monotonic rollout** — bumping 10% → 20% *keeps* everyone already in the first 10% and adds
  the next slice; nobody who had the feature loses it. (The feature name is part of the hash, so
  two different features at 10% enable *different* 10% slices, not the same users.)

You never write this hashing yourself — set the percentage in the flag and pass the **user
identity** in a `TargetingContext`. This minimal Python shape uses the provider plus the
`featuremanagement` library:

```python
# pip install azure-appconfiguration-provider featuremanagement
import os  # Read the App Configuration connection string from an environment variable.

# The provider loads settings and feature flags into a dictionary-like object.
from azure.appconfiguration.provider import load

# FeatureManager evaluates flags; TargetingContext supplies the current user's identity.
from featuremanagement import FeatureManager, TargetingContext

# 1. Load config incl. feature flags from the store (connection string or Entra ID).
config = load(
    connection_string=os.environ["APPCONFIG_CONNECTION_STRING"],
    feature_flag_enabled=True,
)

# 2. Hand the loaded flags to the feature manager (this is what runs the rollout math).
manager = FeatureManager(config)

# 3. Pass a targeting context so the library can make a stable decision for this user.
context = TargetingContext(user_id="alice@example.com", groups=[])
beta_enabled = manager.is_enabled("BetaCheckout", context)
print(f"Beta checkout enabled: {beta_enabled}")
```

**Bottom line:** reach for a feature flag when you want to *turn a capability on/off —
especially gradually, for a subset of users, or on a schedule*. If it's a simple always-on /
always-off boolean with no rollout logic, a plain key works just as well.

### Pricing tiers

There are **four** tiers — **Free**, **Developer**, **Standard**, **Premium** (Developer and
Premium are newer; older material often shows only Free vs Standard). Every tier includes the
core features you actually study here: config settings, feature flags, Key Vault references,
snapshots, RBAC, managed identity, and availability-zone redundancy. The tiers differ on
**scale and enterprise features**, and — to answer the common question — that's **both storage
*and* requests (transactions)**, not just one:

| | **Free** | **Developer** | **Standard** | **Premium** |
| --- | --- | --- | --- | --- |
| Stores per subscription | 3 per region | Unlimited | Unlimited | Unlimited |
| Storage (regular + snapshot) | 10 MB + 10 MB | 500 MB + 500 MB | 1 GB + 1 GB | 4 GB + 4 GB |
| **Requests quota** | **1,000 / day** then 429 until midnight UTC | 6,000 / hour | 30,000 / hour | No request limit |
| Guaranteed throughput | None | None | 300 RPS read / 60 RPS write | 450 RPS read / 100 RPS write |
| Revision history | 7 days | 7 days | 30 days | 30 days |
| SLA | None | None | 99.9% (99.95% w/ geo-replication) | 99.9% (99.99% w/ geo-replication) |
| Geo-replication (replicas) | ✖ | ✖ | ✅ | ✅ |
| Private Link | ✖ | ✅ | ✅ | ✅ |
| Customer-managed keys | ✖ | ✖ | ✅ | ✅ |
| Soft-delete protection | ✖ | ✖ | ✅ (auto, can't disable) | ✅ (auto, can't disable) |

Things worth committing to memory:

- **The Free cap is two-dimensional.** You can run out of **storage** (10 MB) *or* out of
  **requests** (1,000/day → HTTP **429** until midnight UTC). Every `get`/`list`/`set` counts,
  and the provider's config-refresh polling counts too — a running app can burn the Free daily
  quota fast. Standard raises the ceiling to 30,000/hour; Premium removes it.
- **A single key-value is capped at 10 KB** (including its label, content-type, tags, metadata)
  — on **every** tier. Bigger data → store it elsewhere and keep a reference.
- **Soft-delete only exists on Standard/Premium.** On Free/Developer a deleted store is gone
  immediately (no purge step, no name reservation).
- **Upgrades are easy, downgrades are limited.** You can upgrade any time; you can downgrade
  Premium→Standard, but **not** down to Free/Developer (recreate + import instead).

> Exact figures change over time — the [App Configuration pricing page](https://azure.microsoft.com/pricing/details/app-configuration/)
> and [FAQ](https://learn.microsoft.com/azure/azure-app-configuration/faq) are the source of
> truth. (Verified against the FAQ on 2026-08-31.)

---

## Setup

Goal: create an App Configuration store and seed a few keys, so you have something to read from
`app.py`.

> **Two methods available:**
> - **[CLI](#cli-setup)** — Copy-paste commands below (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal (Web UI)](#portal-setup-web-ui)** — Point-and-click in your browser

### Set your variables

The CLI commands in **Setup** and **Cleanup** reference these as **shell variables** — set them
once for your shell, then run the `az` commands as written. (The Portal method doesn't use
these.) What each one is:

- **`RG`** — resource group: the folder that holds your related Azure resources.
- **`LOCATION`** — the Azure region to deploy into.
- **`APPCONFIG`** — the App Configuration store name; must be **globally unique**.

The variable *names* are identical everywhere; only the **assignment syntax** differs by shell,
so copy the block that matches yours:

```bash
# bash / zsh — Linux, and macOS (its default shell)
RG="ai200-rg"
LOCATION="westeurope"
APPCONFIG="ai200-appconfig"
```

```fish
# fish — Linux / macOS
set RG ai200-rg
set LOCATION westeurope
set APPCONFIG ai200-appconfig
```

```powershell
# PowerShell — Windows (also cross-platform)
$RG = "ai200-rg"
$LOCATION = "westeurope"
$APPCONFIG = "ai200-appconfig"
```

```bat
:: Command Prompt (cmd.exe) — Windows
set RG=ai200-rg
set LOCATION=westeurope
set APPCONFIG=ai200-appconfig
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
# 1. Create the resource group (skip if you already made one in another topic).
az group create --name "$RG" --location "$LOCATION"

# 2. One-time-per-subscription: register the App Configuration resource provider.
#    A "resource provider" is the Azure service that supplies a resource type. A brand-new
#    subscription hasn't opted in to every provider, so the first 'az appconfig create' can
#    fail with 'MissingSubscriptionRegistration'. This registers it (safe to re-run; it's a
#    no-op once registered). Registration is async — poll until it prints 'Registered'.
az provider register --namespace Microsoft.AppConfiguration
az provider show --namespace Microsoft.AppConfiguration --query registrationState --output tsv
#    ^ wait until this shows 'Registered' (usually ~1-2 min) before the next step.

# 3. Create the App Configuration store.
#    --sku Free is enough for study (tight store/request limits, no replicas/SLA).
#    Use --sku Standard for replicas, geo-replication, higher limits, and an SLA.
az appconfig create \
  --name "$APPCONFIG" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Free

# 4. Seed a plain key-value. The ':' in the key is just a naming convention for hierarchy.
#    '--yes' skips the interactive confirmation prompt.
az appconfig kv set \
  --name "$APPCONFIG" \
  --key "Ordering:MaxItemsPerPage" \
  --value "50" \
  --yes

# 5. Seed the SAME key under two labels — this is how you get per-environment values.
az appconfig kv set --name "$APPCONFIG" --key "App:Greeting" --label "dev"  --value "Hello from DEV"  --yes
az appconfig kv set --name "$APPCONFIG" --key "App:Greeting" --label "prod" --value "Hello from PROD" --yes

# 6. Create a feature flag (on/off toggle). 'set-kv' with the feature-flag content type also
#    works, but 'feature set' is the purpose-built command.
az appconfig feature set \
  --name "$APPCONFIG" \
  --feature "BetaCheckout" \
  --yes

# 7. (Optional) Store a Key Vault REFERENCE — a pointer to a secret, not the secret itself.
#    Needs an existing Key Vault + secret; --secret-identifier is that secret's URI.
#    See ../key-vault/ for creating the vault + secret.
az appconfig kv set-keyvault \
  --name "$APPCONFIG" \
  --key "App:DbPassword" \
  --secret-identifier "https://<your-vault>.vault.azure.net/secrets/db-password" \
  --yes

# 8. Fetch the connection string your app will use (access-key auth).
#    'query' uses JMESPath to pull just the Primary read-write connection string.
az appconfig credential list \
  --name "$APPCONFIG" \
  --resource-group "$RG" \
  --query "[?name=='Primary'].connectionString" \
  --output tsv
```

**RBAC alternative (recommended, passwordless).** Instead of the connection string, grant your
identity a data-plane role and let the SDK use a token:

```bash
# Get the App Configuration store's resource ID (the scope for the role assignment).
APPCONFIG_ID=$(az appconfig show --name "$APPCONFIG" --resource-group "$RG" --query id --output tsv)

# Grant YOUR signed-in user read access to the data (use Data Owner to also write).
# 'signed-in-user' resolves to whoever ran 'az login'.
az role assignment create \
  --assignee "$(az ad signed-in-user show --query id --output tsv)" \
  --role "App Configuration Data Reader" \
  --scope "$APPCONFIG_ID"
```

### Portal Setup (Web UI)

Prefer the browser? Create the same store in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Create the store:**
   - Click **+ Create a resource** → search "App Configuration" → **Create**
   - Subscription + Resource group: your `ai200-rg`
   - Resource name: `ai200-appconfig` (globally unique)
   - Location: `West Europe`
   - Pricing tier: **Free** (or **Standard** for replicas/SLA)
   - Click **Review + create** → **Create**

3. **Add a key-value:**
   - Open the store → **Configuration explorer** (left menu) → **+ Create** → **Key-value**
   - Key: `Ordering:MaxItemsPerPage`, Value: `50` → **Apply**

4. **Add a labeled key-value (per-environment):**
   - **+ Create** → **Key-value** → Key: `App:Greeting`, Label: `prod`, Value: `Hello from PROD`
   - Repeat with Label `dev` and a different value.

5. **Add a feature flag:**
   - **Feature manager** (left menu) → **+ Create** → name it `BetaCheckout` → **Apply**

6. **Add a Key Vault reference** (needs an existing vault + secret):
   - **Configuration explorer** → **+ Create** → **Key Vault reference**
   - Key: `App:DbPassword`, pick your vault + secret → **Apply**

7. **Get the connection string:**
   - **Settings → Access keys** (left menu) → copy the **Primary** connection string.
   - Or, under **Access control (IAM)**, assign yourself **App Configuration Data Reader** to
     use the passwordless path instead.

---

## Cleanup

Goal: delete the resources created above to avoid charges (Standard tier) and free the store
name.

> **Two methods available:**
> - **[CLI](#cli-cleanup)** — Copy-paste commands below
> - **[Azure Portal (Web UI)](#portal-cleanup-web-ui)** — Point-and-click

### CLI Cleanup

Set `RG` and `APPCONFIG` as shown in [Set your variables](#set-your-variables), then:

```bash
# Delete just the App Configuration store...
az appconfig delete --name "$APPCONFIG" --resource-group "$RG" --yes

# ...or delete the whole resource group and everything in it.
# '--yes' skips confirmation; '--no-wait' returns without waiting for completion.
az group delete --name "$RG" --yes --no-wait

# NOTE: soft-delete only applies to STANDARD/PREMIUM stores. On those, a deleted store
# (and its name) is retained for a recovery window; to reuse the name immediately, PURGE it:
az appconfig purge --name "$APPCONFIG" --yes
```

> **Soft-delete gotcha (Standard/Premium only):** on those tiers a deleted store's *name* stays
> reserved until the retention window elapses or you **purge** it, so recreating with the same
> name before purging fails. **The Free tier has no soft-delete** — the `--sku Free` store from
> Setup is gone immediately on delete and the `purge` step above doesn't apply to it.

### Portal Cleanup (Web UI)

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)
2. **Delete the Resource Group** (fastest): **Resource groups** → your group → **Delete
   resource group**, type the name to confirm, **Delete**.
3. **Or delete just the store:** open `ai200-appconfig` → **Delete** in the toolbar.
4. **Purge if reusing the name:** search **App Configuration** → **Manage deleted stores** →
   select yours → **Purge**.

---

## Hands-on (Python)

A tiny script that writes and reads back key-values, shows a per-environment **label**, creates
a **feature flag**, and stores a **Key Vault reference** — so you see every exam-relevant feature
in one run.

> New to Python? [`app.py`](app.py) is **heavily commented** — every non-trivial line explains
> both the Python idiom and the Azure concept.

> **This sample picks one path of several.** It authenticates with a **connection string** and
> uses the raw **`azure-appconfiguration`** SDK because that's the simplest thing to run. Two
> alternatives worth knowing (both shown/noted in `app.py`):
> - **Entra ID (passwordless):** swap the connection string for `DefaultAzureCredential()` + the
>   store's `endpoint` and a **Data Reader/Owner** role. Recommended for production.
> - **Provider library:** `azure-appconfiguration-provider`'s `load(...)` reads selected settings
>   into a dict-like object and supports refresh. Configure `keyvault_credential` (or a client /
>   resolver) when the provider must resolve Key Vault references.

> **Remember:** Run all commands below from this folder (`04-secure-monitor/app-configuration/`).

### Setup a virtual environment

```bash
# Create a virtual environment (isolates dependencies from your system Python)
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
# The raw SDK used by app.py. (azure-identity is only needed for the Entra ID variant.)
pip install azure-appconfiguration
```

### Set your connection string

```bash
export APPCONFIG_CONNECTION_STRING="<paste the connectionString from CLI setup step 8>"

# Optional: set this only if you created the Key Vault reference from setup step 7.
export KEY_VAULT_SECRET_URI="https://<your-vault>.vault.azure.net/secrets/db-password"
```

### Run the sample

```bash
python app.py
```

You'll see each step print what it wrote and read back. Then open **App Configuration →
Configuration explorer** in the portal to see the same keys.

> **Tip:** To deactivate the virtual environment when done: `deactivate`

---

## Worked examples

Small snippets you can run against your store (CLI) once it's seeded.

**1. Read one key's value:**

```bash
az appconfig kv show --name "$APPCONFIG" --key "Ordering:MaxItemsPerPage" \
  --query value --output tsv
```

**2. Read a key for a specific environment (label):**

```bash
# Same key, different label -> different value.
az appconfig kv show --name "$APPCONFIG" --key "App:Greeting" --label "prod" \
  --query value --output tsv
```

**3. List all feature flags:**

```bash
az appconfig feature list --name "$APPCONFIG" --output table
```

**4. List everything with a key-name filter** (`*` is a wildcard):

```bash
az appconfig kv list --name "$APPCONFIG" --key "App:*" --output table
```

The SDK equivalents (`get_configuration_setting`, `list_configuration_settings`) are shown in
[`app.py`](app.py).

### Filtering server-side (labels & feature flags)

**App Configuration filters on the server** — you do *not* fetch everything and filter in your
app. `list_configuration_settings` takes a `key_filter` and a `label_filter`, both applied
before the data is returned.

```python
# Everything with a specific label (per-environment) — server-side, only 'prod' comes back.
for setting in client.list_configuration_settings(label_filter="prod"):
    print(setting.key, "=", setting.value)

# Combine key + label filters (both server-side).
client.list_configuration_settings(key_filter="App:*", label_filter="prod")

# Feature flags are just keys under the reserved prefix — filter by key prefix.
for flag in client.list_configuration_settings(key_filter=".appconfig.featureflag/*"):
    print(flag.key, "->", flag.value)   # .value is the on/off JSON
```

```bash
# CLI equivalents:
az appconfig kv list      --name "$APPCONFIG" --label "prod"          --output table  # by label
az appconfig kv list      --name "$APPCONFIG" --key "App:*" --label "prod"            # key + label
az appconfig feature list --name "$APPCONFIG" --output table                          # all feature flags
az appconfig feature show --name "$APPCONFIG" --feature "BetaCheckout" --label "prod" # one flag, one label
```

Two gotchas:

- **Filter wildcards are limited.** `key_filter`/`label_filter` support exact match, `*` (any),
  a trailing wildcard (`dev*`), and comma-separated OR lists (`dev,prod`) — **not** arbitrary
  substrings or regex. Anything fancier you filter in code after fetching.
- **The "no label" case is special.** Omitting `label_filter` returns **every** label. To get
  only settings that have *no* label, pass the reserved null filter `label_filter="\0"`
  (CLI: `--label '\0'`).

---

## Exam gotchas

- **App Configuration ≠ Key Vault.** Non-secret settings go in App Configuration; **secrets stay
  in Key Vault**. App Configuration only stores a **reference** (a secret URI), never the secret
  value — and your app needs its **own** Key Vault permission to resolve it.
- **Labels are the per-environment mechanism.** One key, different value per label
  (`dev`/`prod`). Don't invent separate keys per environment.
- **Feature flags are just keys** with the reserved prefix `.appconfig.featureflag/`. But "no
  redeploy" isn't what makes them special (every setting can change independently of a deploy) —
  it is the feature-management convention and **filters** such as targeting and time window that
  let a flag be conditionally on. Evaluation runs in the app's library, not in the store.
- **Data-plane roles vs Contributor.** **App Configuration Data Reader** (read) and **Data
  Owner** (read/write) grant access to the *key-values*. **Contributor** manages the *resource*
  and does **not** let you read/write data.
- **Connection string vs Entra ID.** Both work; **Entra ID + managed identity** (no stored
  secret) is the recommended, most-tested pattern.
- **Tiers gate scale *and* features.** Four tiers (Free · Developer · Standard · Premium). Free
  = 3 stores/region, **10 MB**, **1,000 requests/day** (then HTTP **429**), no replicas/SLA.
  Standard adds geo-replication, an SLA, customer-managed keys, soft-delete, and a far higher
  request/storage ceiling. "Higher limits" means **both storage and transactions** — see the
  [Pricing tiers](#pricing-tiers) table.
- **Soft-delete (Standard/Premium only).** On those tiers a deleted store's name is reserved
  until the retention window passes or you **purge** it. **Free/Developer have no soft-delete** —
  deletion is immediate.
- **`:` is convention, not folders.** Key hierarchy via `:` is a naming style; App Configuration
  stores a flat list of keys.

---

## Quiz yourself

Take the **App Configuration** quiz in the [quiz app](../../quiz/)
(bank: [`quiz/src/questions/04-secure-monitor/app-configuration.json`](../../quiz/src/questions/04-secure-monitor/app-configuration.json)).

## Further reading

- App Configuration overview: <https://learn.microsoft.com/azure/azure-app-configuration/overview>
- Python quickstart: <https://learn.microsoft.com/azure/azure-app-configuration/quickstart-python-provider>
- `azure-appconfiguration` SDK: <https://learn.microsoft.com/python/api/overview/azure/appconfiguration-readme>
- Feature management: <https://learn.microsoft.com/azure/azure-app-configuration/concept-feature-management>
- Key Vault references with the Python provider: <https://learn.microsoft.com/azure/azure-app-configuration/use-key-vault-references-python-provider>
- RBAC / data-plane roles: <https://learn.microsoft.com/azure/azure-app-configuration/concept-enable-rbac>
- Labels & point-in-time snapshots: <https://learn.microsoft.com/azure/azure-app-configuration/concept-point-time-snapshot>
