# Containers on Azure App Service

**Domain:** 01 — Develop containerized solutions on Azure (20–25%)
**Maps to skill:** *Deploy containers to Azure App Service, including configuring App Service to supply environment variables and secrets*

> Follows [`docs/TOPIC_TEMPLATE.md`](../../docs/TOPIC_TEMPLATE.md). The fully-written
> [KQL guide](../../04-secure-monitor/kql/) is the depth/style bar this page matches.

---

## What it is

**Azure App Service** is Azure's **managed web-app hosting Platform-as-a-Service (PaaS)**. Traditionally it runs apps you upload as code or packages — but it can also run a **container image** directly. When you deploy a container to App Service, Azure pulls your image from a registry (usually ACR), starts it on managed infrastructure, and gives it a public HTTPS endpoint — **all without you managing servers, scaling, or TLS certificates.**

Where it sits in the container landscape:

- **App Service (containers)** — **simplest managed web hosting**: one main container, optional
  sidecars on a sidecar-enabled Linux app, deployment slots, app settings, and Key Vault
  references. **No Kubernetes knowledge needed.**
- **Container Apps** — serverless containers with **scale-to-zero**, event-driven scaling via KEDA, microservices in shared environments, revisions for safe rollouts.
- **AKS** — **full Kubernetes control**: you operate the workloads, manifests, networking, and day-2 operations.

> Mental model: **App Service = your web app/API as a container, with Azure handling the hosting.** Think of it as "lift my Dockerfile into PaaS" — the same way you'd deploy a code-based app, but the artifact is a container image instead of a zip file or git repo.

---

## Why it's on the exam

The skill bullet is *"Deploy containers to Azure App Service, including configuring App Service to supply environment variables and secrets."* On AI-200, expect the exam to test:

- **Deploying a container** to App Service from an image in **Azure Container Registry (ACR)** or Docker Hub.
- **Configuring environment variables** (app settings) and **secrets** (Key Vault references) that get injected into the running container.
- **Understanding deployment slots** — staging environments with **swap** for zero-downtime production rollouts.
- **Scaling** — App Service uses **App Service Plans** (not Kubernetes pods); scaling is by plan tier and instance count.
- **Authentication** — how the App Service app gets the appropriate ACR pull permission through
  managed identity.
- **Networking** — custom domains, TLS/SSL, VNet integration options.
- **Logging & diagnostics** — where container logs appear (App Service Logs, Log Stream, Container console).

You need to recognize App Service as the answer for **"a single web app/API, simplest managed hosting, reserved plan capacity is acceptable"** scenarios, and know how to **configure it with containers** specifically.

---

## Core concepts

### App Service basics (what you already know from non-container apps)

| Term | What it is |
| --- | --- |
| **App Service Plan** | Defines the **compute** — region, VM size, OS (Linux/Windows), and **pricing tier** (Free, Basic, Standard, Premium). The plan is the billing/scale unit; multiple apps can share one plan. |
| **App** | Your application resource. A classic custom-container app runs one container. A sidecar-enabled Linux app has one **main** container and can add sidecars; all belong to and scale with the same app. This is not a Kubernetes pod API. |
| **Deployment Slots** | Live staging environments with their own hostname. A swap warms the source slot, then switches it into the target (often production). Settings marked **deployment slot settings** stay with their slot. |
| **App Settings** | Name/value settings exposed to the container as environment variables, accessible through `os.environ` in Python. Values are encrypted at rest, but use Key Vault references instead of placing secrets directly in settings. |
| **Key Vault References** | Special syntax (`@Microsoft.KeyVault(...)`) that pulls **secrets** from Azure Key Vault into app settings — no secrets stored in App Service config. |

### What changes with containers

When your app runs a **container** instead of code, these specifics apply:

| Concept | How it works with containers |
| --- | --- |
| **Image source** | Pulls from **Azure Container Registry (ACR)** or Docker Hub. For an ACR using **RBAC Registry Permissions**, the app's managed identity needs **AcrPull**. For **RBAC Registry + ABAC Repository Permissions**, use **Container Registry Repository Reader** instead. |
| **Container configuration** | Configure the image, startup command, and registry authentication. Classic Linux custom containers use `linuxFxVersion`; sidecar-enabled apps store each container as a site-container resource. |
| **Port mapping** | App Service assumes a classic custom container listens on port 80. Set the `WEBSITES_PORT` app setting when it listens elsewhere. In a sidecar-enabled app, exactly one **main** container receives external HTTP traffic; sidecars share its network namespace and are reached on `localhost:<port>`. The sidecar `Port`/`targetPort` field is metadata, not an App Service routing switch. |
| **Continuous Deployment** | Can auto-pull a new image on **tag update** (e.g. `latest`) from ACR, or use **webhooks** for custom triggers. |
| **Scaling** | Controlled by the **App Service Plan** — you scale the *plan's* instances, not the container itself. There is **no scale-to-zero**; paid plan capacity remains allocated. **Always On** is a separate setting that keeps an app loaded and is off by default. |
| **Storage** | Image-layer writes outside the App Service persistent path are **ephemeral** and can disappear on restart or instance replacement. Enable App Service storage where appropriate or mount supported Azure Storage for persistent data. |
| **Logging** | Container stdout/stderr appears in **App Service Logs** (filesystem) and **Log Stream** (live). You can also get a **console** into the running container for debugging. |

### App Service Plans — the compute behind your container

The **plan** is the billing and scale unit. Linux custom containers require a paid plan; the
quickstart uses **Basic B1**. Choose **Standard or higher when you need deployment slots**.
Feature availability and instance limits change over time and also differ for Linux and Windows
containers, so avoid memorizing a broad SKU matrix that mixes the two operating systems. For the
exam, keep these design facts straight:

- **Basic** can host a Linux custom container, but has no deployment slots or Azure Monitor
  autoscale.
- **Standard, Premium, and Isolated** support deployment slots; the number of slots depends on
  the tier.
- **Windows custom containers have different plan requirements** from Linux containers. Check the
  current Windows-container documentation instead of applying the Linux B1 minimum to them.
- App Service scales the plan's workers. It does not provide the event-driven scale-to-zero model
  of Container Apps.

### Container-specific settings

When you deploy a container to App Service, you configure it with these key settings:

| Setting | Purpose | Example |
| --- | --- | --- |
| **Image and tag** | The container image to run | ai200acr.azurecr.io/web-api:v1.0 |
| **Startup Command** | (Optional) overrides the image's ENTRYPOINT | gunicorn --bind 0.0.0.0:80 app:app |
| **Startup File** | (Optional) overrides the image's CMD | Not used if Startup Command is set |
| **Classic-container HTTP port** | App setting used when the main container listens somewhere other than the assumed port 80 | WEBSITES_PORT=8080 |
| **Sidecar `Port` / `targetPort`** | Metadata describing the container port; it does not configure public App Service routing | 8080 |
| **App Settings** | Environment variables available to the container | DB_HOST=server.database.azure.com |
| **Key Vault References** | Secure way to inject secrets as environment variables | DB_PASSWORD=@Microsoft.KeyVault(SecretUri=https://<vault-name>.vault.azure.net/...) |
| **Continuous Deployment** | Auto-update container when image tag changes | On with tag latest |

> **Critical:** For a classic custom container listening on 8080, set
> `WEBSITES_PORT=8080`; `EXPOSE` alone does not configure classic-container routing. In a
> sidecar-enabled app, designate the externally reachable container as the **main** container
> (`isMain: true`). Do not use its `Port`/`targetPort` field as a routing fix: App Service treats
> that field as metadata. The main container reaches a sidecar over `localhost:<sidecar-port>`.

### Managed identity and ACR pull permissions

For an ACR using **RBAC Registry Permissions**, the App Service identity used for image pull needs
the **AcrPull** role on the registry. The app must also be told to use managed-identity registry
credentials. Portal workflows can perform some of this wiring, but automation should make all
three steps explicit: enable/attach an identity, grant its data-plane role, and enable managed
identity for ACR pulls.

```bash
# Get the app's principal ID
APP_PRINCIPAL_ID=$(az webapp show --resource-group <rg> --name <app> --query identity.principalId --output tsv)

# Get the ACR resource ID
ACR_ID=$(az acr show --name <acr> --resource-group <rg> --query id --output tsv)

# Grant AcrPull to the app's identity on the registry
az role assignment create \
  --assignee "$APP_PRINCIPAL_ID" \
  --role "AcrPull" \
  --scope "$ACR_ID"

# Tell a classic container app to use its managed identity for ACR authentication.
az webapp config set \
  --resource-group <rg> \
  --name <app> \
  --generic-configurations '{"acrUseManagedIdentityCreds": true}'
```

An ACR using **RBAC Registry + ABAC Repository Permissions** uses **Container Registry Repository
Reader**, normally with a repository-name condition, instead of `AcrPull`.

> **Exam tip:** This is a common scenario. When an App Service container can't pull from ACR, the
> symptom is **"Image pull failed"** or **"Unauthorized"** in the logs. On an ACR using **RBAC
> Registry Permissions**, ensure the app's managed identity has **AcrPull**; on an ABAC-enabled
> registry, use **Container Registry Repository Reader** instead.

### Deployment slots for containers

**Deployment slots** are live environments with their own hostname (e.g., myapp-staging.azurewebsites.net) that runs a different version of your app. For containers, this means:

- Each slot can point to a **different image/tag** (e.g., staging uses web-api:dev, production uses web-api:v1.0).
- **Manual swap** — App Service applies the target slot's sticky configuration to the source,
  restarts and warms the source, then switches routing/content between the slots.
- **Swap with preview** — pauses after applying the target configuration to the source. Validate
  the source slot, then complete or cancel the swap.
- **Rollback** — swap the same two slots again; the previous production workload moved to the
  source slot during the first swap.

> **Key point:** Not every setting moves. App settings and connection strings normally swap, but
> any value marked as a **deployment slot setting** stays with its slot. Managed identities,
> custom domains, scale settings, VNet integration, and several platform settings also stay with
> the slot. This is how a staging slot can keep a staging database while its tested image is
> promoted. Auto swap is **not supported** for Linux web apps or Web App for Containers.

### Logging and diagnostics for containers

| Tool | What it shows | Access |
| --- | --- | --- |
| **Log Stream** | Live stdout/stderr from the running container | Portal: App Service -> Log stream or CLI: az webapp log tail --name <app> --resource-group <rg> |
| **App Service Logs** | Persisted logs (stdout/stderr) + web server logs | Portal: App Service -> App Service logs (turn on Application Logging (Filesystem) and Detailed error messages) |
| **SSH/console** | Interactive diagnosis when the custom image has the required SSH support | Portal development tools; availability depends on the image configuration |
| **Diagnose and solve problems** | Guided troubleshooting for common issues | Portal: App Service -> Diagnose and solve problems |

> **Note:** Treat local container logs as short-lived. For retained, queryable telemetry, export
> logs to Azure Monitor/Application Insights or another external sink rather than relying on the
> writable container layer.

---

## Setup

Goal: create an App Service Plan, deploy a containerized app from a sample image, configure environment variables and secrets, and enable deployment slots.

> **Prerequisites:** [Azure CLI](https://learn.microsoft.com/cli/azure/) (az login first).

> **Two methods available:**
> - **[CLI](#cli-setup)** — Copy-paste commands below
> - **[Azure Portal (Web UI)](#portal-setup-web-ui)** — Point-and-click in your browser

### Set your variables

The CLI commands in **Setup** and **Cleanup** reference these as **shell variables** — set them once for your shell, then run the az commands as written. (The Portal method does not use these.)

- **RG** — resource group: the folder that holds your related Azure resources.
- **LOCATION** — the Azure region to deploy into.
- **PLAN** — the App Service Plan name (the compute resource).
- **APP** — the App Service app name (must be globally unique — the URL will be <app>.azurewebsites.net).
- **ACR** — the Azure Container Registry name (must be globally unique, alphanumeric only).

The variable names are identical everywhere; only the assignment syntax differs by shell:

```bash
# bash / zsh — Linux, and macOS
RG="ai200-rg"
LOCATION="westeurope"
PLAN="ai200-asp"
APP="ai200-app-${RANDOM}"
ACR="ai200acr${RANDOM}"
```

```fish
# fish — Linux / macOS
set RG ai200-rg
set LOCATION westeurope
set PLAN ai200-asp
set APP ai200-app(random)
set ACR ai200acr(random)
```

```powershell
# PowerShell — Windows
$RG = "ai200-rg"
$LOCATION = "westeurope"
$PLAN = "ai200-asp"
$APP = "ai200-app-$(Get-Random)"
$ACR = "ai200acr$(Get-Random)"
```

```bat
:: Command Prompt (cmd.exe) — Windows
set RG=ai200-rg
set LOCATION=westeurope
set PLAN=ai200-asp
set APP=ai200-app%RANDOM%
set ACR=ai200acr%RANDOM%
```

> **Shell note.** The full command walk-through below uses **Bash** syntax, including `export`,
> `read`, `unset`, `$RANDOM`, and command substitution. Run it in Azure Cloud Shell (Bash), bash,
> or zsh. The alternative blocks above only show how to define the initial variables; do not mix
> them with Bash-specific commands. In Command Prompt, use `%RG%`-style variables.

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (az login first), after setting your variables above.

<details open>
<summary>Bash CLI Setup</summary>

```bash
# 1. Create the resource group (skip if you already made one in another topic).
az group create --name "$RG" --location "$LOCATION"

# 2. Register the App Service and Container Registry resource providers.
#    These are one-time-per-subscription. Safe to re-run.
az provider register --namespace Microsoft.Web --wait
az provider register --namespace Microsoft.ContainerRegistry --wait

# 3. Create an Azure Container Registry to hold your images.
az acr create \
  --name "$ACR" \
  --resource-group "$RG" \
  --sku Basic \
  --admin-enabled false \
  --role-assignment-mode rbac

# 4. Build a sample image IN THE CLOUD with ACR Tasks.
#    This builds a tiny public Node.js hello-world image on ACR's builders
#    and pushes it as web-api:v1.0 into your registry.
az acr build \
  --registry "$ACR" \
  --image "web-api:v1.0" \
  "https://github.com/Azure-Samples/acr-build-helloworld-node"

# Query the actual login server instead of constructing it; a DNS-name scope can add a hash.
LOGIN_SERVER=$(az acr show --name "$ACR" --resource-group "$RG" --query loginServer --output tsv)

# 5. Create the App Service Plan (Standard S1 tier supports Linux containers + slots).
#    --is-linux ensures a Linux container (required for most images).
az appservice plan create \
  --name "$PLAN" \
  --resource-group "$RG" \
  --sku S1 \
  --is-linux \
  --location "$LOCATION"

# 6. Create the app, attach a system-assigned identity, and select that identity for ACR auth.
#    Role assignment is a separate authorization step below; creation does not make the app's
#    identity an ACR reader by itself.
az webapp create \
  --name "$APP" \
  --resource-group "$RG" \
  --plan "$PLAN" \
  --container-image-name "$LOGIN_SERVER/web-api:v1.0" \
  --assign-identity "[system]" \
  --acr-use-identity \
  --acr-identity "[system]"

# 7. Grant the identity permission to pull artifacts from this RBAC-only registry.
APP_PRINCIPAL_ID=$(az webapp identity show \
  --name "$APP" \
  --resource-group "$RG" \
  --query principalId \
  --output tsv)
ACR_ID=$(az acr show --name "$ACR" --resource-group "$RG" --query id --output tsv)
az role assignment create \
  --assignee-object-id "$APP_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "AcrPull" \
  --scope "$ACR_ID"

# 8. Configure environment variables (app settings).
#    These are injected into the container as environment variables.
az webapp config appsettings set \
  --name "$APP" \
  --resource-group "$RG" \
  --settings "APP_ENV=production" "LOG_LEVEL=info"

# 9. Print the app's URL. A new role assignment can take a few minutes to propagate; App Service
#    retries the image pull, so inspect Log Stream if the first startup reports Unauthorized.
az webapp show --name "$APP" --resource-group "$RG" --query defaultHostName --output tsv
# Then browse to https://<url> to see the running app.

# 10. Optional: create/configure the ACR webhook used for continuous deployment of this tag.
az webapp deployment container config \
  --name "$APP" \
  --resource-group "$RG" \
  --enable-cd true
```

**If an existing app still uses registry credentials**, switch it to managed-identity ACR auth:

```bash
az webapp config set \
  --resource-group "$RG" \
  --name "$APP" \
  --generic-configurations '{"acrUseManagedIdentityCreds": true}'
```

</details>

<details>
<summary>PowerShell CLI Setup</summary>

```powershell
az group create --name $RG --location $LOCATION
az provider register --namespace Microsoft.Web --wait
az provider register --namespace Microsoft.ContainerRegistry --wait
az acr create --name $ACR --resource-group $RG --sku Basic --admin-enabled false `
  --role-assignment-mode rbac
az acr build --registry $ACR --image web-api:v1.0 `
  https://github.com/Azure-Samples/acr-build-helloworld-node
$LOGIN_SERVER = az acr show --name $ACR --resource-group $RG --query loginServer --output tsv
az appservice plan create --name $PLAN --resource-group $RG --sku S1 --is-linux `
  --location $LOCATION
az webapp create --name $APP --resource-group $RG --plan $PLAN `
  --container-image-name "$LOGIN_SERVER/web-api:v1.0" --assign-identity "[system]" `
  --acr-use-identity --acr-identity "[system]"
$APP_PRINCIPAL_ID = az webapp identity show --name $APP --resource-group $RG `
  --query principalId --output tsv
$ACR_ID = az acr show --name $ACR --resource-group $RG --query id --output tsv
az role assignment create --assignee-object-id $APP_PRINCIPAL_ID `
  --assignee-principal-type ServicePrincipal --role AcrPull --scope $ACR_ID
az webapp config appsettings set --name $APP --resource-group $RG `
  --settings "APP_ENV=production" "LOG_LEVEL=info"
az webapp show --name $APP --resource-group $RG --query defaultHostName --output tsv
az webapp deployment container config --name $APP --resource-group $RG --enable-cd true
az webapp config set --resource-group $RG --name $APP `
  --generic-configurations '{"acrUseManagedIdentityCreds": true}'
```

</details>

<details>
<summary>Command Prompt (cmd.exe) CLI Setup</summary>

```bat
az group create --name %RG% --location %LOCATION%
az provider register --namespace Microsoft.Web --wait
az provider register --namespace Microsoft.ContainerRegistry --wait
az acr create --name %ACR% --resource-group %RG% --sku Basic --admin-enabled false ^
  --role-assignment-mode rbac
az acr build --registry %ACR% --image web-api:v1.0 ^
  https://github.com/Azure-Samples/acr-build-helloworld-node
for /f "delims=" %%I in ('az acr show --name %ACR% --resource-group %RG% --query loginServer --output tsv') do set LOGIN_SERVER=%%I
az appservice plan create --name %PLAN% --resource-group %RG% --sku S1 --is-linux ^
  --location %LOCATION%
az webapp create --name %APP% --resource-group %RG% --plan %PLAN% ^
  --container-image-name "%LOGIN_SERVER%/web-api:v1.0" --assign-identity "[system]" ^
  --acr-use-identity --acr-identity "[system]"
for /f "delims=" %%I in ('az webapp identity show --name %APP% --resource-group %RG% --query principalId --output tsv') do set APP_PRINCIPAL_ID=%%I
for /f "delims=" %%I in ('az acr show --name %ACR% --resource-group %RG% --query id --output tsv') do set ACR_ID=%%I
az role assignment create --assignee-object-id %APP_PRINCIPAL_ID% ^
  --assignee-principal-type ServicePrincipal --role AcrPull --scope %ACR_ID%
az webapp config appsettings set --name %APP% --resource-group %RG% ^
  --settings "APP_ENV=production" "LOG_LEVEL=info"
az webapp show --name %APP% --resource-group %RG% --query defaultHostName --output tsv
az webapp deployment container config --name %APP% --resource-group %RG% --enable-cd true
az webapp config set --resource-group %RG% --name %APP% ^
  --generic-configurations "{\"acrUseManagedIdentityCreds\": true}"
```

</details>

### Portal Setup (Web UI)

Prefer the browser? Create the same resources in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Create the Azure Container Registry:**
   - Click + Create a resource -> search "Container Registry" -> Create
   - Subscription + Resource group: your ai200-rg
   - Registry name: ai200acr... (globally unique, alphanumeric only)
   - Location: West Europe
   - Pricing plan (SKU): Basic
   - Click Review + create -> Create

3. **Build and push a sample image:**
   - Open the registry -> Tasks -> Quick tasks -> Build
   - Source: Public repository
   - Repository URL: https://github.com/Azure-Samples/acr-build-helloworld-node
   - Image name: web-api
   - Image tag: v1.0
   - Click Run

4. **Create the App Service Plan:**
   - + Create a resource -> search "App Service plan" -> Create
   - Subscription + Resource group: your ai200-rg
   - Name: ai200-asp
   - Operating System: Linux
   - Region: West Europe
   - Pricing plan: Standard S1 (supports containers + slots)
   - Click Review + create -> Create

5. **Create the Web App:**
   - + Create a resource -> search "Web App" -> Create
   - Subscription + Resource group: your ai200-rg
   - Name: ai200-app... (globally unique)
   - Publish: Docker Container
   - Operating System: Linux
   - Region: West Europe
   - App Service Plan: ai200-asp (select existing)
   - Click Next: Docker
   - Image Source: Azure Container Registry
   - Registry: select your ai200acr... registry
   - Image: web-api
   - Tag: v1.0
   - Click Review + create -> Create
   - Check "Enable continuous deployment" to auto-pull on new image tags.

6. **Configure environment variables:**
   - Open the web app -> Settings -> Configuration -> Application settings
   - Add new application settings: APP_ENV=production, LOG_LEVEL=info
   - Click Save

7. **Browse to the app:**
   - Open the web app -> Overview -> click the URL

---

## Hands-on (Python)

A read-only Python inspector that uses the Azure Resource Management SDK (`azure-mgmt-web`). It
can:

- List all web apps in a resource group.
- Inspect classic and sidecar-enabled container metadata.
- List app-setting **names** while redacting all values.
- List deployment slots without changing or swapping them.

> New to Python? [app.py](app.py) is heavily commented — every non-trivial line explains both the Python idiom and the Azure concept.

> This sample uses the management-plane SDK azure-mgmt-web with Entra ID auth. You need Contributor (or higher) role on the resource group. Run az login first.

> Remember: Run all commands below from this folder (01-containers/app-service-containers/).

### Setup a virtual environment

```bash
python -m venv venv
```

### Activate the virtual environment

```bash
# bash/zsh (macOS/Linux)
source venv/bin/activate

# fish (macOS/Linux)
source venv/bin/activate.fish

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows cmd
venv\Scripts\activate.bat
```

### Install dependencies

```bash
pip install azure-mgmt-web azure-identity
```

### Set your Azure subscription and resource group

```bash
export AZURE_SUBSCRIPTION_ID=$(az account show --query id --output tsv)
export AZURE_RESOURCE_GROUP="ai200-rg"
export AZURE_APP_NAME="ai200-app..."
```

### Run the sample

```bash
# List apps in the configured resource group (the default operation is "list").
python app.py list

# Inspect one app's container metadata and redacted setting names.
python app.py inspect --app-name "$AZURE_APP_NAME"

# List that app's deployment slots.
python app.py slots --app-name "$AZURE_APP_NAME"
```

> Tip: To deactivate the virtual environment when done: deactivate

---

## Worked examples

Copy-paste Azure CLI snippets to manage your container app and diagnose common issues.

### 1. Update the container image

```bash
az webapp config container set \
  --name "$APP" \
  --resource-group "$RG" \
  --container-image-name "$LOGIN_SERVER/web-api:v2.0"
```

### 2. Add/change environment variables

```bash
az webapp config appsettings set \
  --name "$APP" \
  --resource-group "$RG" \
  --settings "DB_HOST=my-server.database.azure.com" "DB_NAME=mydb"
```

### 3. Add a Key Vault secret reference

```bash
# Create an RBAC-enabled study vault. Its name must be globally unique.
KEYVAULT_NAME="ai200kv${RANDOM}"
SECRET_NAME="db-password"
az keyvault create \
  --name "$KEYVAULT_NAME" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --enable-rbac-authorization true

# Bash/zsh: read the study value without placing it literally in shell history, then create a
# secret version.
read -rsp "Temporary database password: " DB_PASSWORD
printf '\n'
az keyvault secret set \
  --vault-name "$KEYVAULT_NAME" \
  --name "$SECRET_NAME" \
  --value "$DB_PASSWORD"
unset DB_PASSWORD

# A Key Vault reference is resolved with the app's managed identity. AcrPull does not grant secret
# access, so assign the separate least-privilege Key Vault Secrets User role at the vault scope.
KEYVAULT_ID=$(az keyvault show --name "$KEYVAULT_NAME" --query id --output tsv)
az role assignment create \
  --assignee-object-id "$APP_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope "$KEYVAULT_ID"

# Use a versionless URI so App Service can pick up newer secret versions after its cache refresh.
SECRET_URI="https://${KEYVAULT_NAME}.vault.azure.net/secrets/${SECRET_NAME}"
az webapp config appsettings set \
  --name "$APP" \
  --resource-group "$RG" \
  --settings "DB_PASSWORD=@Microsoft.KeyVault(SecretUri=$SECRET_URI)"
```

### 4. Create a deployment slot

```bash
# Create a staging slot
az webapp deployment slot create \
  --name "$APP" \
  --resource-group "$RG" \
  --slot "staging"

# Deploy a different image to the staging slot
az webapp config container set \
  --name "$APP" \
  --resource-group "$RG" \
  --slot "staging" \
  --container-image-name "$LOGIN_SERVER/web-api:dev"

# Swap staging to production (zero-downtime deployment)
az webapp deployment slot swap \
  --name "$APP" \
  --resource-group "$RG" \
  --slot "staging" \
  --target-slot "production"
```

### 5. View container logs

```bash
# Enable short-lived filesystem capture of container stdout and stderr before tailing it.
az webapp log config \
  --name "$APP" \
  --resource-group "$RG" \
  --docker-container-logging filesystem

# Stream live logs from the container (stdout + stderr)
az webapp log tail \
  --name "$APP" \
  --resource-group "$RG"

# Download the log files
az webapp log download \
  --name "$APP" \
  --resource-group "$RG" \
  --log-file "app-service-logs.zip"
```

### 6. Diagnose common container issues

**Symptom: startup/availability failure**
- Cause: The classic container isn't listening on its configured port, the intended main
  sidecar-enabled container is not configured as `isMain: true`, a startup check failed, or the
  process crashed.
- Fix: For a classic custom container, check `WEBSITES_PORT`. For a sidecar-enabled app, confirm
  the intended container is the main one and inspect Log Stream; changing `targetPort` does not
  change App Service routing.

**Symptom: Image pull failed / Unauthorized**
- Cause: The app's managed identity lacks the ACR data-plane permission for the registry mode.
- Fix: Grant **AcrPull** on an RBAC-only registry, or **Container Registry Repository Reader** on
  an ABAC-enabled registry, as shown in Setup.

**Symptom: Container won't start / exits immediately**
- Cause: Missing environment variable, bad config, or app error.
- Fix: Check logs (az webapp log tail) and verify app settings are correct.

**Symptom: Changes not appearing**
- Cause: App Service caches the container image. Continuous Deployment may not be enabled.
- Fix: Enable CI/CD (`az webapp deployment container config --enable-cd true`) or manually restart the app.

---

## Exam gotchas

- **Classic versus sidecar-enabled.** A classic app runs one custom container. A sidecar-enabled
  Linux app runs one main container plus optional sidecars; they share the app lifecycle and scale.
- **Ports and sidecars differ.** Classic custom containers assume port 80 unless `WEBSITES_PORT`
  is set. A sidecar-enabled app sends external traffic only to its main container; its
  `Port`/`targetPort` field is metadata, and sidecars are reached over `localhost`. `EXPOSE` alone
  does not configure classic-container routing.
- **Know what the tier buys.** Basic B1 supports a Linux custom container. Standard or higher is
  required for deployment slots; use current documentation for Windows-container plan support.
- Managed identity + ACR permission. For **RBAC Registry Permissions**, App Service uses its
  selected managed identity with **AcrPull**. An ABAC-enabled registry instead uses **Container
  Registry Repository Reader**. Know which registry mode the scenario specifies.
- App Settings = environment variables. App Services App Settings become environment variables inside the container. Key Vault references let you inject secrets the same way.
- No scale-to-zero. Paid App Service plans retain allocated capacity. **Always On** is a separate,
  off-by-default setting that keeps an app loaded; for demand-driven scale-to-zero, use Container
  Apps + KEDA.
- **Slot settings stay put.** Values marked as deployment slot settings don't swap. Managed
  identities, custom domains, scale settings, and VNet integration also remain with the slot.
- **No auto swap for containers.** Auto swap isn't supported for Web App for Containers or other
  Linux web apps; use an explicit, warmed slot swap.
- Logs are ephemeral. Container stdout/stderr are not persisted by default. Use Application Insights or Azure Files mount for persistent logging.
- `az webapp create --container-image-name` is the current CLI pattern; the older
  `--deployment-container-image-name` flag is deprecated.
- Continuous Deployment from ACR. Enable it to auto-pull new image tags (e.g., latest). Without it, you must manually redeploy after pushing a new image.

---

## Quiz yourself

Take the App Service (containers) quiz in the [quiz app](../../quiz/)
(bank: [quiz/src/questions/01-containers/app-service-containers.json](../../quiz/src/questions/01-containers/app-service-containers.json)).

## Further reading

- App Service overview: https://learn.microsoft.com/azure/app-service/overview
- Deploy a container to App Service: https://learn.microsoft.com/azure/app-service/quickstart-custom-container
- Configure container apps: https://learn.microsoft.com/azure/app-service/configure-custom-container
- Deployment slots: https://learn.microsoft.com/azure/app-service/deploy-staging-slots
- App Service managed identity: https://learn.microsoft.com/azure/app-service/overview-managed-identity
- Key Vault references in App Service: https://learn.microsoft.com/azure/app-service/app-service-key-vault-references
- Azure Resource Management `azure-mgmt-web` SDK: https://learn.microsoft.com/python/api/overview/azure/mgmt-web-readme
