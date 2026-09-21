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

- **Registry** — the top-level resource (e.g. `ai200acr`). Its login server ends in
  **`.azurecr.io`**. With the default DNS-name-label setting it is
  `<name>.azurecr.io`; an optional DNS name label scope adds a stable hash to reduce
  subdomain-takeover risk, so query the real `loginServer` instead of constructing it.
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

- **Which SKU (tier) to pick** — Basic vs Standard vs Premium — especially that
  **geo-replication and private endpoints are Premium-only**, while availability-zone support
  and repository-scoped permissions are no longer Premium-only.
- **ACR Tasks** — building images *in the cloud* with `az acr build` (no local Docker), and the
  three **automatic triggers** (source commit, base-image update, schedule).
- **Authentication** — the registry's permission mode: legacy registry-wide roles
  (**AcrPull**, **AcrPush**, **AcrDelete**) for RBAC-only registries versus the **Container
  Registry Repository** roles for ABAC-enabled registries; plus `az acr login`, managed
  identities, and the disabled-by-default admin account.
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
| **Registry** | The Azure resource. Its queried login server normally looks like `<name>.azurecr.io` (or includes a DNS-scope hash). Holds many repositories. |
| **Repository** | A named group of image versions inside the registry (`web-api`). Created implicitly the first time you push to that name. |
| **Tag** | A **mutable** human label on an image (`v1.0`, `latest`). Re-pushing the same tag moves it to a *new* image — tags are not stable identifiers. |
| **Digest** | A **`sha256:…`** hash of the exact image content. **Immutable** — the same digest always means the same bytes. Pin by digest in prod for reproducibility. |
| **Manifest** | The metadata document describing one image (its layers + config). One manifest = one digest; it may carry zero or more tags. |
| **ACR Tasks** | ACR's built-in build service — build/push images *in the cloud* and re-build automatically on triggers (see below). |
| **Scope map / token** | A named set of per-repository permissions plus a non-Entra credential. Available in every tier; tier limits differ. |

### SKUs (tiers) — Basic · Standard · Premium

All three tiers are the *same registry service* with the same API; they differ on **included
storage, throughput, feature availability, and limits.** Premium is required for several
networking, replication, and key-management capabilities, but not every security feature.

| Feature | **Basic** | **Standard** | **Premium** |
| --- | --- | --- | --- |
| Included storage / throughput | Lowest | Higher | Highest |
| Webhooks | ✅ (few) | ✅ (more) | ✅ (most) |
| **Geo-replication** (one registry, multiple regions) | ✖ | ✖ | ✅ |
| **Private Link / private endpoints** | ✖ | ✖ | ✅ |
| **Docker Content Trust (deprecated)** | ✖ | ✖ | ✅ until its 31 March 2028 retirement |
| **Customer-managed keys (CMK)** | ✖ | ✖ | ✅ |
| **Availability zones** | ✅ in supported regions | ✅ in supported regions | ✅ in supported regions |
| **Repository-scoped tokens + scope maps** | ✅ | ✅ | ✅ (higher limits) |
| Anonymous pull | ✖ | ✅ | ✅ |
| Artifact cache rules | ✖ | ✅ | ✅ |
| ACR Tasks (build in cloud) | ✅ | ✅ | ✅ |
| Entra ID RBAC (AcrPull/AcrPush) | ✅ | ✅ | ✅ |

> **Memory hook:** **geo-replication, Private Link/private endpoints, customer-managed keys,
> dedicated data endpoints, and the untagged-manifest retention policy are Premium-only.**
> Anonymous pull and artifact cache start at Standard. Availability-zone support and
> repository-scoped permissions exist in every tier, with regional availability or tier limits.
> Docker Content Trust is deprecated; use Notary Project/Notation for new signing workflows.

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
- **Base-image update** — after the task has built at least once, ACR tracks a supported `FROM`
  dependency and can rebuild when that base image's **stable tag is updated**. A newly published
  tag such as `3.13` does not trigger a task that follows `3.12`; the tag in `FROM` must move.
- **Schedule** — a timer (cron-style) rebuilds on a cadence.

### Authentication (the most-tested part)

There are three common ways to authenticate to a registry's **data plane** (pulling/pushing
images):

1. **Entra ID + RBAC (recommended).** You run **`az acr login --name <registry>`**, which uses
   your Entra sign-in to log the local container client into the registry — no long-lived ACR
   admin password is needed. Access is granted
   through **data-plane roles**. The correct role names depend on the registry's **Role
   assignment permissions mode**:

   | Need | **RBAC Registry Permissions** | **RBAC Registry + ABAC Repository Permissions** |
   | --- | --- | --- |
   | Pull/read | **AcrPull** | **Container Registry Repository Reader** |
   | Push/read/write | **AcrPush** | **Container Registry Repository Writer** |
   | Delete artifacts | **AcrDelete** | **Container Registry Repository Contributor** |
   | List the repository catalog | Included in AcrPull | Add **Container Registry Repository Catalog Lister** |

   Control-plane roles that manage the registry resource do not automatically grant image
   pull/push/delete access; assign the least-privilege data-plane role separately. For services
   such as AKS, App Service, and Container Apps, assign the relevant pull role to the service's
   managed identity so no registry password appears in configuration.

2. **Admin account.** One built-in username with **two interchangeable passwords** for the whole
   registry. It is
   **DISABLED by default** and is meant for **testing/quick demos only** — Microsoft discourages
   it in production because it's a shared, non-identity credential. Enable with
   `az acr update --admin-enabled true`.

3. **Repository-scoped tokens + scope maps.** A token is a credential tied to a
   **scope map** — a named set of per-repository permissions (e.g. "pull `web-api`, push
   `internal/*`"). Use it when you need **granular, per-repo** access without an Entra
   identity. This is available in all tiers; the number of tokens/scope maps varies by tier.

**Attaching ACR to compute (AKS / App Service / Container Apps).** For an **RBAC-only** registry,
the compute identity normally gets **AcrPull**. AKS has a shortcut that assigns it to the
cluster's kubelet identity:

```bash
# Grant the AKS cluster's managed identity AcrPull on the registry (no image credentials needed).
az aks update --name <aks-cluster> --resource-group <rg> --attach-acr <registry>
```

That shortcut is **not supported for an ABAC-enabled registry**. In that mode, manually assign
**Container Registry Repository Reader** to the kubelet identity instead.

**Anonymous pull** *(Standard/Premium)* — enabling
`az acr update --anonymous-pull-enabled true` makes **every repository in the registry** publicly
readable. It is not a per-repository switch. Pushing still requires authentication.

### Tagging & versioning

- **Tags are mutable** — `latest` can silently point at a different image tomorrow. **Avoid
  `latest` in production**; use explicit version tags (`v1.4.2`) or, for guaranteed
  reproducibility, **pin by digest** (`@sha256:…`), which never changes.
- You can lock a repository, manifest, or tag against writes/deletes. Locking isn't a
  Premium-only feature. Premium additionally offers the preview retention policy that
  automatically deletes untagged Docker manifests.
- **`az acr repository`** commands list/inspect/delete repos, tags, and manifests.
- **Docker Content Trust (DCT)** is a Premium feature but has been deprecated since March 2025
  and retires on **31 March 2028**. Use **Notary Project/Notation** for new signing and
  verification workflows.

---

## Setup

Goal: create a registry, build and push a sample image with ACR Tasks, so you have repositories
and tags for `app.py` to read.

> **Two methods available:**
> - **[CLI](#cli-setup)** — Copy-paste commands below (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal (Web UI)](#portal-setup-web-ui)** — Point-and-click in your browser

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

> **Shell syntax in this walkthrough.** The CLI Setup and Cleanup blocks are **Bash** commands:
> they use Bash variable references (`"$RG"`), command substitution (`$(...)`), `printf`, and `\`
> line continuations. Run them in Azure Cloud Shell (Bash), WSL, or another Bash-compatible shell.
> Fish and PowerShell require their own variable and continuation syntax; cmd uses `%RG%`.

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first), after
[setting your variables](#set-your-variables) above.

<details open>
<summary>Bash CLI Setup</summary>

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
#    --sku Basic is enough for study. Explicit RBAC-only mode keeps the AcrPull/AcrPush
#    examples below valid; ABAC-enabled registries use the newer Repository roles.
az acr create \
  --name "$ACR" \
  --resource-group "$RG" \
  --sku Basic \
  --role-assignment-mode rbac

# 4. Build an image IN THE CLOUD with ACR Tasks (no local Docker needed).
#    'az acr build' builds a Dockerfile on ACR's builders AND pushes the result in one step,
#    streaming the build log back to you. Each '-t' sets an image name:tag.
#    'https://github.com/...' can be any build context; here's a tiny public sample:
az acr build \
  --registry "$ACR" \
  --image "web-api:v1.0" \
  --image "web-api:v1.1" \
  "https://github.com/Azure-Samples/acr-build-helloworld-node.git"

# 5. Query the authoritative login server. This is normally <name>.azurecr.io but can contain
#    a DNS-scope hash, so scripts should not construct it from the registry resource name.
LOGIN_SERVER=$(az acr show --name "$ACR" --query loginServer --output tsv)

# 6. The build applied both v1.0 and v1.1 tags, so app.py has multiple tags to list. This avoids
#    a registry-to-registry import, which can require source-registry import permissions.

# 7. Log Docker into the registry using YOUR Entra sign-in; no ACR admin password is needed.
az acr login --name "$ACR"

# 8. Print the login server captured above for ACR_ENDPOINT below.
printf '%s\n' "$LOGIN_SERVER"
```

</details>

<details>
<summary>PowerShell CLI Setup</summary>

```powershell
# 1. Create the resource group (skip if you already made one in another topic).
az group create --name $RG --location $LOCATION

# 2. One-time-per-subscription: register the Container Registry resource provider.
#    A new subscription may not have opted in; registration is safe to re-run and async.
az provider register --namespace Microsoft.ContainerRegistry
az provider show --namespace Microsoft.ContainerRegistry --query registrationState --output tsv

# 3. Create the registry. Basic is enough for study; RBAC-only mode keeps the role examples valid.
az acr create --name $ACR --resource-group $RG --sku Basic --role-assignment-mode rbac

# 4. Build two tagged images in the cloud with ACR Tasks (no local Docker needed).
az acr build --registry $ACR --image web-api:v1.0 --image web-api:v1.1 `
  https://github.com/Azure-Samples/acr-build-helloworld-node.git

# 5. Query the authoritative login server; do not construct it from the registry name.
$LOGIN_SERVER = az acr show --name $ACR --query loginServer --output tsv

# 7. Log Docker into the registry using the signed-in Entra identity.
az acr login --name $ACR

# 8. Print the login server for use as the ACR endpoint.
$LOGIN_SERVER

# The registry resource ID is the scope for the role assignment.
$ACR_ID = az acr show --name $ACR --resource-group $RG --query id --output tsv
# Grant the signed-in user AcrPull (use AcrPush when push access is required).
$SIGNED_IN_USER_ID = az ad signed-in-user show --query id --output tsv
az role assignment create --assignee $SIGNED_IN_USER_ID --role AcrPull --scope $ACR_ID
```

</details>

<details>
<summary>Command Prompt (cmd.exe) CLI Setup</summary>

```bat
:: 1. Create the resource group (skip if you already made one in another topic).
az group create --name %RG% --location %LOCATION%

:: 2. One-time-per-subscription: register the Container Registry resource provider.
::    A new subscription may not have opted in; registration is safe to re-run and async.
az provider register --namespace Microsoft.ContainerRegistry
az provider show --namespace Microsoft.ContainerRegistry --query registrationState --output tsv

:: 3. Create the registry. Basic is enough for study; RBAC-only mode keeps the role examples valid.
az acr create --name %ACR% --resource-group %RG% --sku Basic --role-assignment-mode rbac

:: 4. Build two tagged images in the cloud with ACR Tasks (no local Docker needed).
az acr build --registry %ACR% --image web-api:v1.0 --image web-api:v1.1 ^
  https://github.com/Azure-Samples/acr-build-helloworld-node.git
:: 5. Query the authoritative login server; do not construct it from the registry name.
for /f "delims=" %%I in ('az acr show --name %ACR% --query loginServer --output tsv') do set LOGIN_SERVER=%%I
:: 7. Log Docker into the registry using the signed-in Entra identity.
az acr login --name %ACR%
:: 8. Print the login server for use as the ACR endpoint.
echo %LOGIN_SERVER%

:: The registry resource ID is the scope for the role assignment.
for /f "delims=" %%I in ('az acr show --name %ACR% --resource-group %RG% --query id --output tsv') do set ACR_ID=%%I
:: Grant the signed-in user AcrPull (use AcrPush when push access is required).
for /f "delims=" %%I in ('az ad signed-in-user show --query id --output tsv') do set SIGNED_IN_USER_ID=%%I
az role assignment create --assignee %SIGNED_IN_USER_ID% --role AcrPull --scope %ACR_ID%
```

</details>

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

5. **Grant pull/push access:** first check **Settings → Properties → Role assignment
   permissions mode**. For **RBAC Registry Permissions**, assign **AcrPull/AcrPush**. For
   **RBAC Registry + ABAC Repository Permissions**, assign **Container Registry Repository
   Reader/Writer** (and Catalog Lister if catalog listing is needed).

6. **(Test only) Admin account:** **Access keys** (left menu) → toggle **Admin user** on to get a
   username/password. Off by default; avoid in production.

---

## Cleanup

Goal: delete the resources created above to avoid storage charges and free the registry name.

> **Two methods available:**
> - **[CLI](#cli-cleanup)** — Copy-paste commands below
> - **[Azure Portal (Web UI)](#portal-cleanup-web-ui)** — Point-and-click

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

> **Note:** ACR's preview soft-delete policy applies to **artifacts**, not to the registry Azure
> resource. Deleting the registry removes the registry and its contents; artifact soft delete
> cannot restore a deleted registry.

### Portal Cleanup (Web UI)

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)
2. **Delete the Resource Group** (fastest): **Resource groups** → your group → **Delete
   resource group**, type the name to confirm, **Delete**.
3. **Or delete just the registry:** open the registry → **Delete** in the toolbar.
4. **Or delete a single repository:** registry → **Repositories** → pick one → **Delete**.

---

## Hands-on (Python)

A tiny script that connects to your registry with **`DefaultAzureCredential`** (passwordless —
locally it can reuse your `az login` session), lists every **repository**, lists each repository's
**tags** and **manifests**, prints the **fully-qualified image reference**, and shows
(commented out) how you'd delete a tag or manifest.

> New to Python? [`app.py`](app.py) is **heavily commented** — every non-trivial line explains
> both the Python idiom and the Azure concept.

> **This sample uses the data-plane SDK `azure-containerregistry`** (`ContainerRegistryClient`)
> with **Entra ID** auth. The RBAC-only setup in this guide uses **AcrPull**. For an ABAC-enabled
> registry the equivalent listing sample needs **Container Registry Repository Reader** plus
> **Container Registry Repository Catalog Lister**. Run `az login` before the sample.

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
# Prefix the exact loginServer from Setup step 7 with https://.
# It can include a DNS-scope hash, so don't assume it is exactly the resource name.
export ACR_ENDPOINT="https://<login-server-from-az-acr-show>"
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

**5. Run a one-off purge command in ACR Tasks:**

```bash
# 'az acr run' executes an inline task; here a purge command deletes tags older than 30 days.
az acr run --registry "$ACR" \
  --cmd "acr purge --filter 'web-api:.*' --ago 30d --untagged" /dev/null
```

The Python SDK equivalents for listing repos/tags/manifests are shown in [`app.py`](app.py).

---

## Exam gotchas

- **Know the current SKU split.** **Geo-replication, private endpoints, customer-managed keys,
  dedicated data endpoints, and untagged-manifest retention are Premium-only.** Availability
  zones and repository-scoped permissions are available in all tiers; anonymous pull starts at
  Standard. See the [SKU table](#skus-tiers--basic--standard--premium).
- **Anonymous pull needs Standard or Premium** — it is **not** available on Basic.
- **`az acr build` = build + push in the cloud.** It replaces `docker build` **and**
  `docker push`, and needs **no local Docker daemon**. Pure `docker push` still requires you to
  `az acr login` first.
- **Three ACR Task triggers:** source-code **commit**, **base-image update**, and **schedule**.
  Base-image tracking starts after the task builds successfully and follows updates to the
  stable tag in `FROM`; publishing a different tag does not update that dependency.
- **Permission mode changes the role names.** RBAC-only: **AcrPull / AcrPush / AcrDelete**.
  ABAC-enabled: **Repository Reader / Writer / Contributor**, optionally scoped to repositories;
  add **Catalog Lister** only when catalog enumeration is needed. Control-plane access alone does
  not grant artifact access.
- **Admin account is DISABLED by default** and is **test-only** — one shared username with two
  interchangeable passwords, discouraged in production. Prefer Entra ID / managed identity.
- **Let AKS pull with a managed identity, not credentials.** On an RBAC-only registry,
  `az aks update --attach-acr <acr>` grants the kubelet identity **AcrPull**. The shortcut doesn't
  support ABAC-enabled registries; assign **Container Registry Repository Reader** manually.
- **Tags are mutable; digests are immutable.** `latest` can move to a new image; pin by
  `@sha256:` digest when a deployment must identify one exact manifest. Locks can prevent writes
  or deletes; the Premium retention policy targets untagged manifests.
- **Naming.** A login server ends in **`.azurecr.io`**, but a configured DNS name label scope can
  add a hash. Query `loginServer`. Registry resource names are globally unique and alphanumeric
  only (5–50 characters).
- **Repository-scoped tokens are available in every tier.** Premium raises token/scope-map
  limits; it is not required merely to restrict a non-Entra token to one repository.
- **Docker Content Trust is deprecated.** It retires on 31 March 2028. Prefer Notary
  Project/Notation for new image-signing workflows.

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
- ABAC repository permissions: <https://learn.microsoft.com/azure/container-registry/container-registry-rbac-abac-repository-permissions>
- Authenticate from AKS: <https://learn.microsoft.com/azure/aks/cluster-container-registry-integration>
- Repository-scoped tokens: <https://learn.microsoft.com/azure/container-registry/container-registry-repository-scoped-permissions>
- Docker Content Trust retirement / Notary migration: <https://learn.microsoft.com/azure/container-registry/container-registry-content-trust-deprecation>
- Artifact soft delete (preview): <https://learn.microsoft.com/azure/container-registry/container-registry-soft-delete-policy>
- Python `azure-containerregistry` SDK: <https://learn.microsoft.com/python/api/overview/azure/containerregistry-readme>
