# Azure Container Registry (ACR)

**Domain:** 01 — Develop containerized solutions on Azure (20–25%)
**Maps to skill:** *Build, store, version, and manage container images by using Azure
Container Registry* · *Build and run images by using Azure Container Registry Tasks*

> Follows [`docs/TOPIC_TEMPLATE.md`](../../docs/TOPIC_TEMPLATE.md). The fully-written
> [KQL guide](../../04-secure-monitor/kql/) is the depth/style bar this page matches.

---

## What it is

**Azure Container Registry (ACR)** is a **private, managed Docker/OCI registry** hosted in
Azure. A **registry** is a server that stores **container images** — the packaged, ready-to-run
bundles your app ships as. Think of it as **your own private Docker Hub**, living inside your
Azure subscription, with Azure identity, networking, and RBAC wrapped around it.

Three names you'll see together, and how they nest:

- **Registry** — the top-level resource (e.g. `ai200acr`). It gets a globally-unique DNS name
  ending in **`.azurecr.io`**.
- **Repository** — a named collection of related images *inside* the registry
  (e.g. `web-api`). A registry holds many repositories.
- **Image** — one build, identified by a **tag** (`v1.0`, `latest`) or an immutable
  **digest** (`sha256:…`). A repository holds many tagged versions of the same image.

> Mental model: **registry → repositories → images (by tag or digest).** The full address of
> one image — the string you `docker pull` or reference in a deployment — is:
>
> ```text
> <registry>.azurecr.io/<repository>:<tag>
> ai200acr.azurecr.io/web-api:v1.0        # registry / repo : tag
> ai200acr.azurecr.io/web-api@sha256:9f3…  # or pin an exact build by digest
> ```

Where it sits in a solution: you **build** an image, **push** it to ACR, and then some Azure
compute service — **Azure Kubernetes Service (AKS)**, **App Service**, **Container Apps**,
**Container Instances** — **pulls** it from ACR to run it. ACR is the storage-and-distribution
hub in the middle.

---

## Why it's on the exam

The skill bullets are *"Build, store, version, and manage container images by using Azure
Container Registry"* and *"Build and run images by using Azure Container Registry Tasks."*
Expect the exam to test:

- **Which SKU (tier) to pick** — Basic vs Standard vs Premium — and especially **which features
  are Premium-only** (geo-replication, private link, content trust, repo-scoped tokens). This is
  heavily tested.
- **ACR Tasks** — building images *in the cloud* with `az acr build` (no local Docker), and the
  three **automatic triggers** (source commit, base-image update, schedule).
- **Authentication** — the data-plane RBAC roles (**AcrPull**, **AcrPush**, **AcrDelete**),
  `az acr login`, the **admin account** (disabled by default, test-only), and how a compute
  service's **managed identity** gets **AcrPull** to pull images (`az aks update --attach-acr`).
- **Tag vs digest** immutability, **anonymous pull**, and the `.azurecr.io` naming.

You mostly need to *recognize* which capability solves a scenario ("build without a Docker
host" → ACR Tasks; "let AKS pull images" → attach-acr / AcrPull; "replicate images near users
in 3 regions" → Premium geo-replication).

---

## Core concepts

ACR is a flat set of **repositories**, each holding **tagged images**. A handful of ideas turn
that into something you can secure and automate:

| Term | What it is |
| --- | --- |
| **Registry** | The Azure resource. Globally-unique name → `<name>.azurecr.io`. Holds many repositories. |
| **Repository** | A named group of image versions inside the registry (`web-api`). Created implicitly the first time you push to that name. |
| **Tag** | A **mutable** human label on an image (`v1.0`, `latest`). Re-pushing the same tag moves it to a *new* image — tags are not stable identifiers. |
| **Digest** | A **`sha256:…`** hash of the exact image content. **Immutable** — the same digest always means the same bytes. Pin by digest in prod for reproducibility. |
| **Manifest** | The metadata document describing one image (its layers + config). One manifest = one digest; it may carry zero or more tags. |
| **ACR Tasks** | ACR's built-in build service — build/push images *in the cloud* and re-build automatically on triggers (see below). |
| **Scope map / token** | *(Premium)* A named set of per-repository permissions + a credential, for granular, repo-scoped access without an Entra identity. |

### SKUs (tiers) — Basic · Standard · Premium

All three tiers are the *same registry service* with the same API; they differ on **included
storage, throughput, and — most testable — which enterprise features are unlocked.** Premium is
where the security/scale features live.

| Feature | **Basic** | **Standard** | **Premium** |
| --- | --- | --- | --- |
| Included storage / throughput | Lowest | Higher | Highest |
| Webhooks | ✅ (few) | ✅ (more) | ✅ (most) |
| **Geo-replication** (one registry, multiple regions) | ✖ | ✖ | ✅ |
| **Private Link / private endpoints** | ✖ | ✖ | ✅ |
| **Content trust / image signing** | ✖ | ✖ | ✅ |
| **Customer-managed keys (CMK)** | ✖ | ✖ | ✅ |
| **Availability zones** | ✖ | ✖ | ✅ |
| **Repository-scoped tokens + scope maps** | ✖ | ✖ | ✅ |
| Anonymous pull | ✖ | ✅ | ✅ |
| ACR Tasks (build in cloud) | ✅ | ✅ | ✅ |
| Entra ID RBAC (AcrPull/AcrPush) | ✅ | ✅ | ✅ |

> **Memory hook:** the "enterprise-grade" features are all **Premium** — **geo-replication,
> private link, content trust/signing, customer-managed keys, availability zones, and
> repo-scoped tokens**. Basic/Standard differ mostly on *scale* (storage/throughput), not
> features. Anonymous pull needs **Standard or Premium** (not Basic). You can **change tier**
> (up or down) at any time.

### ACR Tasks — build in the cloud, rebuild on triggers

**ACR Tasks** lets ACR build your image **server-side** — you don't need Docker installed
locally. Two forms:

- **Quick Task** — `az acr build`. You point it at a folder with a **Dockerfile**, and ACR
  builds the image on a managed builder and pushes it into the registry, **streaming the logs
  back to your terminal**. It's the cloud equivalent of `docker build` **+** `docker push` in a
  single command.
- **Multi-step task** — an `acb.yaml` file describing several steps (build, run, push multiple
  images) for more complex pipelines.

`az acr build` vs `docker build` + `docker push`:

| | `docker build` + `docker push` | `az acr build` |
| --- | --- | --- |
| Where it runs | Your local machine (needs Docker) | ACR's cloud builders (no local Docker) |
| Steps | Two commands | One command (builds *and* pushes) |
| Auth to push | You must `az acr login` / `docker login` first | Handled by the task |

**Automatic triggers** — a *task* (created with `az acr task create`) can rebuild by itself when:

- **Source-code commit** — a git push to the linked repo (e.g. GitHub) kicks off a build.
- **Base-image update** — when the `FROM` base image gets a new version/patch, ACR rebuilds your
  image so it picks up the fix. This is the one people forget — it keeps images patched.
- **Schedule** — a timer (cron-style) rebuilds on a cadence.

### Authentication (the most-tested part)

There are three ways to authenticate to a registry's **data plane** (pulling/pushing images):

1. **Entra ID + RBAC (recommended).** You run **`az acr login --name <registry>`**, which uses
   your Entra token to log Docker into the registry — **no password stored**. Access is granted
   through **data-plane roles**:

   | Role | Grants |
   | --- | --- |
   | **AcrPull** | Pull images (read). This is what a running service needs. |
   | **AcrPush** | Pull **and** push images (read/write). |
   | **AcrDelete** | Delete images/manifests. |
   | **Owner / Contributor** | Manage the *registry resource* + full data access. |

   For services (AKS, App Service, Container Apps), you give the service's **managed identity**
   the **AcrPull** role so it can pull images with no credentials in config.

2. **Admin account.** A single built-in **username/password** for the whole registry. It is
   **DISABLED by default** and is meant for **testing/quick demos only** — Microsoft discourages
   it in production because it's a shared, non-identity credential. Enable with
   `az acr update --admin-enabled true`.

3. **Repository-scoped tokens + scope maps (Premium).** A token is a credential tied to a
   **scope map** — a named set of per-repository permissions (e.g. "pull `web-api`, push
   `internal/*`"). Use it when you need **granular, per-repo** access without minting an Entra
   identity. Premium-only.

**Attaching ACR to compute (AKS / App Service / Container Apps).** So the compute can pull
images, its **managed identity** needs **AcrPull** on the registry. For AKS there's a shortcut
that does the role assignment for you:

```bash
# Grant the AKS cluster's managed identity AcrPull on the registry (no image credentials needed).
az aks update --name <aks-cluster> --resource-group <rg> --attach-acr <registry>
```

**Anonymous pull** *(Standard/Premium)* — you can make repositories **publicly readable** with
no auth at all (`az acr update --anonymous-pull-enabled true`), for distributing public images.
Pushing still requires authentication.

### Tagging & versioning

- **Tags are mutable** — `latest` can silently point at a different image tomorrow. **Avoid
  `latest` in production**; use explicit version tags (`v1.4.2`) or, for guaranteed
  reproducibility, **pin by digest** (`@sha256:…`), which never changes.
- You can enable **lock/immutability** and **retention** policies (Premium) so tags can't be
  overwritten and untagged manifests get auto-purged.
- **`az acr repository`** commands list/inspect/delete repos, tags, and manifests.
- **Content trust / image signing** and **quarantine** (hold new images until scanned) are
  **Premium** features for supply-chain integrity.

---

## Setup

Goal: create a registry, build and push a sample image with ACR Tasks, so you have repositories
and tags for `app.py` to read.

> **Two methods available:**
> - **[CLI](#cli-setup)** — Copy-paste commands below (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal (Web UI)](#portal-setup)** — Point-and-click in your browser

### Set your variables

The CLI commands in **Setup** and **Cleanup** reference these as **shell variables** — set them
once for your shell, then run the `az` commands as written. (The Portal method doesn't use
these.) What each one is:

- **`RG`** — resource group: the folder that holds your related Azure resources.
- **`LOCATION`** — the Azure region to deploy into.
- **`ACR`** — the registry name; must be **globally unique**, letters + digits only (no dashes).
  The random suffix helps keep it unique.

The variable *names* are identical everywhere; only the **assignment syntax** differs by shell,
so copy the block that matches yours:

```bash
# bash / zsh — Linux, and macOS (its default shell)
RG="ai200-rg"
LOCATION="westeurope"
ACR="ai200acr$RANDOM"
```

```fish
# fish — Linux / macOS
set RG ai200-rg
set LOCATION westeurope
set ACR ai200acr(random)
```

```powershell
# PowerShell — Windows (also cross-platform)
$RG = "ai200-rg"
$LOCATION = "westeurope"
$ACR = "ai200acr$(Get-Random)"
```

```bat
:: Command Prompt (cmd.exe) — Windows
set RG=ai200-rg
set LOCATION=westeurope
set ACR=ai200acr%RANDOM%
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

# 2. One-time-per-subscription: register the Container Registry resource provider.
#    A "resource provider" is the Azure service behind a resource type. A brand-new subscription
#    may not have opted in, so the first create can fail with 'MissingSubscriptionRegistration'.
#    This registers it (safe to re-run; no-op once registered). Registration is async.
az provider register --namespace Microsoft.ContainerRegistry
az provider show --namespace Microsoft.ContainerRegistry --query registrationState --output tsv
#    ^ wait until this shows 'Registered' before the next step.

# 3. Create the registry.
#    --sku Basic is enough for study. Use Standard for anonymous pull / more throughput,
#    or Premium for geo-replication, private link, content trust, tokens, and CMK.
az acr create \
  --name "$ACR" \
  --resource-group "$RG" \
  --sku Basic

# 4. Build an image IN THE CLOUD with ACR Tasks (no local Docker needed).
#    'az acr build' builds a Dockerfile on ACR's builders AND pushes the result in one step,
#    streaming the build log back to you. '-t' sets the image name:tag.
#    'https://github.com/...' can be any build context; here's a tiny public sample:
az acr build \
  --registry "$ACR" \
  --image "web-api:v1.0" \
  "https://github.com/Azure-Samples/acr-build-helloworld-node.git"

# 5. (Optional) Also tag it as v1.1 so app.py has more than one tag to list.
#    'az acr import' copies an existing image into a new tag without rebuilding.
az acr import \
  --name "$ACR" \
  --source "$ACR.azurecr.io/web-api:v1.0" \
  --image "web-api:v1.1"

# 6. Log Docker into the registry using YOUR Entra token (no password stored).
az acr login --name "$ACR"

# 7. Print the registry's login server (the '<name>.azurecr.io' host) for ACR_ENDPOINT below.
az acr show --name "$ACR" --query loginServer --output tsv
```

**RBAC — grant a service (or user) pull access (recommended, passwordless).** A running app
needs **AcrPull**; a CI pipeline that pushes needs **AcrPush**:

```bash
# The registry's resource ID is the scope for the role assignment.
ACR_ID=$(az acr show --name "$ACR" --resource-group "$RG" --query id --output tsv)

# Grant YOUR signed-in user AcrPull (swap for AcrPush to also push).
az role assignment create \
  --assignee "$(az ad signed-in-user show --query id --output tsv)" \
  --role "AcrPull" \
  --scope "$ACR_ID"

# Let an AKS cluster pull from this registry (does the AcrPull assignment for its identity):
# az aks update --name <aks-cluster> --resource-group "$RG" --attach-acr "$ACR"
```

### Portal Setup (Web UI)

Prefer the browser? Create the same registry in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Create the registry:**
   - Click **+ Create a resource** → search "Container Registry" → **Create**
   - Subscription + Resource group: your `ai200-rg`
   - Registry name: `ai200acr…` (globally unique, letters+digits only)
   - Location: `West Europe`
   - Pricing plan (SKU): **Basic** (or **Standard**/**Premium** for more features)
   - Click **Review + create** → **Create**

3. **Build/push an image:** the portal doesn't build for you — from your terminal run
   `az acr build` (CLI step 4) or `docker push`. To use `docker push`, first
   `az acr login --name <registry>`.

4. **See your repositories:** open the registry → **Repositories** (left menu) → click a repo to
   see its **Tags** and **manifests**.

5. **Grant pull/push access:** **Access control (IAM)** → **+ Add role assignment** → pick
   **AcrPull** (or **AcrPush**) → assign to your user or a managed identity.

6. **(Test only) Admin account:** **Access keys** (left menu) → toggle **Admin user** on to get a
   username/password. Off by default; avoid in production.

---

## Cleanup

Goal: delete the resources created above to avoid storage charges and free the registry name.

> **Two methods available:**
> - **[CLI](#cli-cleanup)** — Copy-paste commands below
> - **[Azure Portal (Web UI)](#portal-cleanup)** — Point-and-click

### CLI Cleanup

Set `RG` and `ACR` (to the **exact** registry name you created) as shown in
[Set your variables](#set-your-variables), then:

```bash
# Delete just the registry (and all its images)...
az acr delete --name "$ACR" --resource-group "$RG" --yes

# ...or delete the whole resource group and everything in it.
# '--yes' skips confirmation; '--no-wait' returns without waiting for completion.
az group delete --name "$RG" --yes --no-wait
```

> **Note:** ACR has **no soft-delete** for the registry resource — deletion is immediate and the
> name frees up right away. (Individual *images* can be protected by retention/lock policies, but
> deleting the registry removes everything.)

### Portal Cleanup (Web UI)

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)
2. **Delete the Resource Group** (fastest): **Resource groups** → your group → **Delete
   resource group**, type the name to confirm, **Delete**.
3. **Or delete just the registry:** open the registry → **Delete** in the toolbar.
4. **Or delete a single repository:** registry → **Repositories** → pick one → **Delete**.

---

## Hands-on (Python)

A tiny script that connects to your registry with **`DefaultAzureCredential`** (passwordless —
it reuses your `az login` / `az acr login`), lists every **repository**, lists each repository's
**tags** and **manifests**, prints the **fully-qualified image reference**, and shows
(commented out) how you'd delete a tag or manifest.

> New to Python? [`app.py`](app.py) is **heavily commented** — every non-trivial line explains
> both the Python idiom and the Azure concept.

> **This sample uses the data-plane SDK `azure-containerregistry`** (`ContainerRegistryClient`)
> with **Entra ID** auth. You need at least the **AcrPull** role on the registry (granted in
> Setup) and to have run `az login`.

> **Remember:** Run all commands below from this folder (`01-containers/acr/`).

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
# The data-plane registry SDK + the identity library for passwordless auth.
pip install azure-containerregistry azure-identity
```

### Set your registry endpoint

```bash
# The login server from Setup step 7, as an https:// URL.
export ACR_ENDPOINT="https://<your-registry-name>.azurecr.io"
```

### Run the sample

```bash
python app.py
```

You'll see each repository printed with its tags, digests, and full pull references. Compare it
against **Repositories** in the portal.

> **Tip:** To deactivate the virtual environment when done: `deactivate`

### What `app.py` does

- Creates a **`ContainerRegistryClient`** pointed at `ACR_ENDPOINT`, authenticated by
  `DefaultAzureCredential` (your `az login` token — no password).
- Calls **`list_repository_names()`** to enumerate the repositories in the registry.
- For each repo, calls **`list_tag_properties()`** (tag name + the digest it points to) and
  **`list_manifest_properties()`** (each image build by digest, with any tags on it).
- Prints the **fully-qualified reference** for each — both `…:tag` and `…@sha256:digest`.
- Includes a **commented-out** `delete_tag(...)` / `delete_manifest(...)` block so you can see
  the delete API without accidentally removing images.

---

## Worked examples

Small `az acr` snippets you can run once the registry is seeded.

**1. Build an image in the cloud (no local Docker) and push it:**

```bash
# Builds the Dockerfile in the given context on ACR's builders and pushes 'web-api:v2.0'.
az acr build --registry "$ACR" --image "web-api:v2.0" .
```

**2. List repositories, then a repo's tags:**

```bash
az acr repository list --name "$ACR" --output table                 # all repositories
az acr repository show-tags --name "$ACR" --repository web-api --output table   # tags in one repo
```

**3. Show a specific image's manifest (incl. its digest):**

```bash
az acr manifest show --registry "$ACR" --name "web-api:v1.0"
# or list every manifest (by digest) in a repo:
az acr manifest list-metadata --registry "$ACR" --name "web-api"
```

**4. Import an image from another registry (e.g. Docker Hub) without a local pull/push:**

```bash
# Copies an upstream image straight into your ACR. Great for mirroring public base images.
az acr import --name "$ACR" --source "docker.io/library/nginx:latest" --image "nginx:latest"
```

**5. Run a one-off command in the cloud / purge old tags (Premium retention):**

```bash
# 'az acr run' executes an inline task; here a purge command deletes tags older than 30 days.
az acr run --registry "$ACR" \
  --cmd "acr purge --filter 'web-api:.*' --ago 30d --untagged" /dev/null
```

The Python SDK equivalents for listing repos/tags/manifests are shown in [`app.py`](app.py).

---

## Exam gotchas

- **Premium is where the enterprise features live.** **Geo-replication, private link/private
  endpoints, content trust (image signing), customer-managed keys, availability zones, and
  repository-scoped tokens/scope maps are ALL Premium-only.** Basic vs Standard differ mainly on
  **scale** (storage/throughput), not features. See the [SKU table](#skus-tiers--basic--standard--premium).
- **Anonymous pull needs Standard or Premium** — it is **not** available on Basic.
- **`az acr build` = build + push in the cloud.** It replaces `docker build` **and**
  `docker push`, and needs **no local Docker daemon**. Pure `docker push` still requires you to
  `az acr login` first.
- **Three ACR Task triggers:** source-code **commit**, **base-image update**, and **schedule**.
  Base-image-update triggers are the "keep images patched automatically" answer.
- **AcrPull vs AcrPush.** **AcrPull** = read/pull (what a running service needs); **AcrPush** =
  pull **+** push (what a build pipeline needs); **AcrDelete** = delete. Owner/Contributor manage
  the resource. Don't hand a runtime service AcrPush "just in case."
- **Admin account is DISABLED by default** and is **test-only** — a single shared
  username/password, discouraged in production. Prefer Entra ID / managed identity.
- **Let AKS pull with a managed identity, not credentials.** `az aks update --attach-acr <acr>`
  grants the cluster's identity **AcrPull** — no image pull secrets in YAML.
- **Tags are mutable; digests are immutable.** `latest` can move to a new image; **pin by
  `@sha256:` digest** in production for reproducibility. Immutability/retention policies are
  Premium.
- **Naming.** The registry's login server is always **`<name>.azurecr.io`**, and a full image
  reference is `<name>.azurecr.io/<repository>:<tag>`. The registry name is **globally unique**
  and **alphanumeric only** (no dashes).
- **Repository-scoped tokens are Premium** — the answer for "grant access to *one* repo without
  an Entra identity."

---

## Quiz yourself

Take the **ACR** quiz in the [quiz app](../../quiz/)
(bank: [`quiz/src/questions/01-containers/acr.json`](../../quiz/src/questions/01-containers/acr.json)).

## Further reading

- ACR overview: <https://learn.microsoft.com/azure/container-registry/container-registry-intro>
- SKUs / service tiers: <https://learn.microsoft.com/azure/container-registry/container-registry-skus>
- ACR Tasks overview: <https://learn.microsoft.com/azure/container-registry/container-registry-tasks-overview>
- Authentication overview: <https://learn.microsoft.com/azure/container-registry/container-registry-authentication>
- RBAC roles (AcrPull/AcrPush): <https://learn.microsoft.com/azure/container-registry/container-registry-roles>
- Authenticate from AKS: <https://learn.microsoft.com/azure/aks/cluster-container-registry-integration>
- Repository-scoped tokens: <https://learn.microsoft.com/azure/container-registry/container-registry-repository-scoped-permissions>
- Python `azure-containerregistry` SDK: <https://learn.microsoft.com/python/api/overview/azure/containerregistry-readme>
