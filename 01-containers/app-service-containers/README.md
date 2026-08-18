# Containers on Azure App Service

**Domain:** 01 — Develop containerized solutions on Azure (20–25%)
**Maps to skill:** *Deploy containers to Azure App Service, including configuring App Service to supply environment variables and secrets*

> Follows [`docs/TOPIC_TEMPLATE.md`](../../docs/TOPIC_TEMPLATE.md). The fully-written
> [KQL guide](../../04-secure-monitor/kql/) is the depth/style bar this page matches.

---

## What it is

**Azure App Service** is Azure's **managed web-app hosting Platform-as-a-Service (PaaS)**. Traditionally it runs apps you upload as code or packages — but it can also run a **container image** directly. When you deploy a container to App Service, Azure pulls your image from a registry (usually ACR), starts it on managed infrastructure, and gives it a public HTTPS endpoint — **all without you managing servers, scaling, or TLS certificates.**

Where it sits in the container landscape:

- **App Service (containers)** — **simplest managed hosting**: one app per container, deployment slots, app settings, Key Vault references. **No Kubernetes knowledge needed.**
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
- **Authentication** — how the App Service app gets **AcrPull** permission on ACR (managed identity).
- **Networking** — custom domains, TLS/SSL, VNet integration options.
- **Logging & diagnostics** — where container logs appear (App Service Logs, Log Stream, Container console).

You need to recognize App Service as the answer for **"a single web app/API, simplest managed hosting, always-on is acceptable"** scenarios, and know how to **configure it with containers** specifically.

---

## Core concepts

### App Service basics (what you already know from non-container apps)

| Term | What it is |
| --- | --- |
| **App Service Plan** | Defines the **compute** — region, VM size, OS (Linux/Windows), and **pricing tier** (Free, Basic, Standard, Premium). The plan is the billing/scale unit; multiple apps can share one plan. |
| **App** | Your application resource. One app = one **container** (App Service doesn't do multi-container pods like Container Apps or AKS). |
| **Deployment Slots** | Live staging environments with their own hostname. **Swap** moves a slot's config + container to production instantly (zero downtime). |
| **App Settings** | Environment variables injected into your app at runtime (non-secret config). Accessible via `os.environ` in Python, `process.env` in Node, etc. |
| **Key Vault References** | Special syntax (`@Microsoft.KeyVault(...)`) that pulls **secrets** from Azure Key Vault into app settings — no secrets stored in App Service config. |

### What changes with containers

When your app runs a **container** instead of code, these specifics apply:

| Concept | How it works with containers |
| --- | --- |
| **Image source** | Pulls from **Azure Container Registry (ACR)** or Docker Hub. Images from ACR require the app's **managed identity** to have the **AcrPull** role. |
| **Container configuration** | Specified in the **Container Settings** blade: image name, tag, startup command, ports, environment variables. |
| **Port mapping** | Your container must listen on the **port you declare** (default 80). App Service **does not** auto-detect the port from the image. |
| **Continuous Deployment** | Can auto-pull a new image on **tag update** (e.g. `latest`) from ACR, or use **webhooks** for custom triggers. |
| **Scaling** | Controlled by the **App Service Plan** — you scale the *plan's* instances, not the container itself. **No scale-to-zero** (always-on by default). |
| **Storage** | By default, the container's filesystem is **ephemeral** — it resets on restart. Use **Azure Files** or **Azure Blob Storage** via mount paths for persistent data. |
| **Logging** | Container stdout/stderr appears in **App Service Logs** (filesystem) and **Log Stream** (live). You can also get a **console** into the running container for debugging. |

### App Service Plans — the compute behind your container

All tiers support containers, but **Linux containers** (the common choice) are **not available on Free or Shared tiers**. The tier determines scaling, features, and cost:

| Feature | **Free (F1)** | **Basic (B1-B3)** | **Standard (S1-S3)** | **Premium (P1-P3)** | **PremiumV2 (PV2)** | **PremiumV3 (PV3)** |
| --- | --- | --- | --- | --- | --- | --- |
| Linux containers | no | yes | yes | yes | yes | yes |
| Windows containers | no | yes | yes | yes | yes | yes |
| **Custom domains + TLS** | Limited (1) | yes | yes | yes | yes | yes |
| **Deployment slots** | no | no | yes | yes | yes | yes |
| **Auto-scale** (instance count) | no | no | yes (manual) | yes | yes | yes |
| **Always On** | no | yes | yes | yes | yes | yes |
| **VNet integration** | no | no | yes | yes | yes | yes |
| **Private Endpoint** | no | no | no | no | yes | yes |
| **Multiple instances** | 1 | Up to 3 | Up to 10 | Up to 20 | Up to 30 | Up to 50 |
| **ACU (CPU + memory)** | 60 | 200-800 | 200-1600 | 200-3200 | 420-8400 | 420-16800 |

> **Memory hook:** **Standard (S1) is the minimum viable tier for production containers** — it adds deployment slots, auto-scale, and VNet integration. Free and Basic tiers are for **evaluation only**.

### Container-specific settings

When you deploy a container to App Service, you configure it with these key settings:

| Setting | Purpose | Example |
| --- | --- | --- |
| **Image and tag** | The container image to run | ai200acr.azurecr.io/web-api:v1.0 |
| **Startup Command** | (Optional) overrides the image's ENTRYPOINT | gunicorn --bind 0.0.0.0:80 app:app |
| **Startup File** | (Optional) overrides the image's CMD | Not used if Startup Command is set |
| **Port** | **The port your container listens on** — must match what the app expects | 80 or 8080 |
| **App Settings** | Environment variables available to the container | DB_HOST=server.database.azure.com |
| **Key Vault References** | Secure way to inject secrets as environment variables | DB_PASSWORD=@Microsoft.KeyVault(SecretUri=https://kv.vault.azure.net/...) |
| **Continuous Deployment** | Auto-update container when image tag changes | On with tag latest |

> **Critical:** The **Port** setting **must match** the port your container actually listens on. If your app listens on 8080, set the App Service port to 8080. App Service **does not** introspect the image to auto-discover this. Wrong port = **502 Bad Gateway** errors.

### Managed identity and ACR pull permissions

For your App Service app to pull an image from **Azure Container Registry (ACR)**, its **system-assigned managed identity** needs the **AcrPull** role on the registry. This is handled automatically in two ways:

1. **During app creation** — if you create the App Service app **from the Azure portal**, there's a checkbox to "Pull image from Azure Container Registry" — selecting it and choosing your ACR grants the identity **AcrPull** automatically.
2. **Manual grant** — if you create the app first, you can grant the role manually:

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
```

> **Exam tip:** This is a common scenario. When an App Service container can't pull from ACR, the symptom is **"Image pull failed"** or **"Unauthorized"** in the logs — and the fix is ensuring the app's managed identity has **AcrPull** on the registry.

### Deployment slots for containers

**Deployment slots** are live environments with their own hostname (e.g., myapp-staging.azurewebsites.net) that runs a different version of your app. For containers, this means:

- Each slot can point to a **different image/tag** (e.g., staging uses web-api:dev, production uses web-api:v1.0).
- **Auto swap** — automatically swap slots when a condition is met (e.g., after a warm-up period).
- **Manual swap** — instantly move the container + configuration from a slot to production.
- **Swap with preview** — temporarily swap to test, then swap back to undo.

> **Key point:** When you **swap**, App Service moves the **entire configuration** (app settings, connection strings, container image reference) from the source slot to the target. The old production container is **not restarted** — a new one is started from the new image. This means **zero downtime** for the swap itself, but your app's startup time still applies.

### Logging and diagnostics for containers

| Tool | What it shows | Access |
| --- | --- | --- |
| **Log Stream** | Live stdout/stderr from the running container | Portal: App Service -> Log stream or CLI: az webapp log tail --name <app> --resource-group <rg> |
| **App Service Logs** | Persisted logs (stdout/stderr) + web server logs | Portal: App Service -> App Service logs (turn on Application Logging (Filesystem) and Detailed error messages) |
| **Container console** | Shell into the running container (for debugging) | Portal: App Service -> Development Tools -> Console -> Container console |
| **Diagnose and solve problems** | Guided troubleshooting for common issues | Portal: App Service -> Diagnose and solve problems |

> **Note:** Container logs are **ephemeral** by default — they live only as long as the container instance. For persistent logging, **mount Azure Files** or stream to **Application Insights**.

---

## Setup

Goal: create an App Service Plan, deploy a containerized app from a sample image, configure environment variables and secrets, and enable deployment slots.

> **Prerequisites:** [Azure CLI](https://learn.microsoft.com/cli/azure/) (az login first).

> **Two methods available:**
> - **[CLI](#cli-setup)** — Copy-paste commands below
> - **[Azure Portal (Web UI)](#portal-setup)** — Point-and-click in your browser

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

> **Referencing the variables in the commands below.** The az snippets are written bash-style ("$RG") and work unchanged in bash/zsh, fish, and PowerShell (all expand $RG). In cmd, write %RG% instead.

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (az login first), after setting your variables above.

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
  --admin-enabled false

# 4. Build a sample image IN THE CLOUD with ACR Tasks.
#    This builds a tiny public Node.js hello-world image on ACR's builders
#    and pushes it as web-api:v1.0 into your registry.
az acr build \
  --registry "$ACR" \
  --image "web-api:v1.0" \
  "https://github.com/Azure-Samples/acr-build-helloworld-node.git"

# 5. Create the App Service Plan (Standard S1 tier supports Linux containers + slots).
#    --is-linux ensures a Linux container (required for most images).
az appservice plan create \
  --name "$PLAN" \
  --resource-group "$RG" \
  --sku S1 \
  --is-linux \
  --location "$LOCATION"

# 6. Create the App Service app running the container.
#    --deploy-container-image-name points at the image in your ACR.
#    App Service will automatically grant the app's identity AcrPull on the registry.
az webapp create \
  --name "$APP" \
  --resource-group "$RG" \
  --plan "$PLAN" \
  --deploy-container-image-name "${ACR}.azurecr.io/web-api:v1.0"

# 7. Configure environment variables (app settings).
#    These are injected into the container as environment variables.
az webapp config appsettings set \
  --name "$APP" \
  --resource-group "$RG" \
  --settings "APP_ENV=production" "LOG_LEVEL=info"

# 8. Print the app's URL — it may take a minute to start the container.
az webapp show --name "$APP" --resource-group "$RG" --query defaultHostName --output tsv
# Then browse to https://<url> to see the running app.

# 9. Enable Continuous Deployment from ACR (auto-update on new tag).
az webapp deployment container config \
  --name "$APP" \
  --resource-group "$RG" \
  --enable-ci true \
  --docker-registry-server-url "https://${ACR}.azurecr.io"
```

**RBAC — grant the apps identity AcrPull (if not auto-granted).** The app creation above should auto-grant AcrPull. If you see pull errors, grant it manually:

```bash
# Get the apps principal ID
APP_PRINCIPAL_ID=$(az webapp show --resource-group "$RG" --name "$APP" --query identity.principalId --output tsv)

# Get the ACR resource ID
ACR_ID=$(az acr show --name "$ACR" --resource-group "$RG" --query id --output tsv)

# Grant AcrPull
az role assignment create \
  --assignee "$APP_PRINCIPAL_ID" \
  --role "AcrPull" \
  --scope "$ACR_ID"
```

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
   - Repository URL: https://github.com/Azure-Samples/acr-build-helloworld-node.git
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

A Python script that manages your App Service container app programmatically using the Azure Resource Management SDK (azure-mgmt-web). It can:

- List all web apps in a resource group
- Get and update app settings (environment variables)
- Get the container configuration (image, port, startup command)
- List and swap deployment slots

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
# List your apps and their container configs in the resource group.
python app.py

# Or pass specific commands (see app.py --help for options):
python app.py --list-apps
python app.py --get-settings
python app.py --get-container-config
```

> Tip: To deactivate the virtual environment when done: deactivate

---

## Worked examples

Copy-paste Azure CLI snippets to manage your container app and diagnose common issues.

### 1. Update the container image

```bash
az webapp deployment container update \
  --name "$APP" \
  --resource-group "$RG" \
  --docker-image-name "${ACR}.azurecr.io/web-api:v2.0"
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
# Store a secret in Key Vault
KEYVAULT_NAME="ai200-kv"
SECRET_NAME="db-password"
az keyvault secret set \
  --vault-name "$KEYVAULT_NAME" \
  --name "$SECRET_NAME" \
  --value "SuperSecret123!"

# Reference the secret in App Service
SECRET_URI=$(az keyvault secret show --name "$SECRET_NAME" --vault-name "$KEYVAULT_NAME" --query id --output tsv)
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
az webapp deployment container update \
  --name "$APP" \
  --resource-group "$RG" \
  --slot "staging" \
  --docker-image-name "${ACR}.azurecr.io/web-api:dev"

# Swap staging to production (zero-downtime deployment)
az webapp deployment slot swap \
  --name "$APP" \
  --resource-group "$RG" \
  --slot "staging" \
  --target-slot "production"
```

### 5. View container logs

```bash
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

**Symptom: 502 Bad Gateway**
- Cause: Container is not listening on the Port configured in App Service, or the app crashed.
- Fix: Check the Port setting matches your containers listen port. View logs with az webapp log tail.

**Symptom: Image pull failed / Unauthorized**
- Cause: Apps managed identity lacks AcrPull on the ACR.
- Fix: Grant the role as shown in Setup.

**Symptom: Container won't start / exits immediately**
- Cause: Missing environment variable, bad config, or app error.
- Fix: Check logs (az webapp log tail) and verify app settings are correct.

**Symptom: Changes not appearing**
- Cause: App Service caches the container image. Continuous Deployment may not be enabled.
- Fix: Enable CI/CD (az webapp deployment container config --enable-ci true) or manually restart the app.

---

## Exam gotchas

- One container per app. App Service runs a single container per web app. If you need multi-container pods or microservices, use Container Apps or AKS.
- Port must match. The Port setting in App Service must match the port your container listens on. Default is 80. Wrong port = 502 Bad Gateway.
- Always On is required for containers. Unlike code-based apps, containers must have Always On enabled (included in Standard tier and above). Free/Basic tiers do not support Linux containers at all.
- Standard (S1) minimum for production. Free/Basic tiers lack deployment slots, auto-scale, VNet integration. Standard S1 is the practical minimum for containerized apps.
- Managed identity + AcrPull. App Service uses its system-assigned managed identity to pull from ACR. It needs the AcrPull role. This is often auto-configured, but know how to grant it manually.
- App Settings = environment variables. App Services App Settings become environment variables inside the container. Key Vault references let you inject secrets the same way.
- No scale-to-zero. App Service containers are always-on (on paid tiers). For scale-to-zero, use Container Apps + KEDA.
- Deployment slots move the whole config. Swapping slots moves the container image + all app settings. The old production container is stopped and replaced (not restarted).
- Logs are ephemeral. Container stdout/stderr are not persisted by default. Use Application Insights or Azure Files mount for persistent logging.
- az webapp create with --deploy-container-image-name is the CLI pattern for container deployments.
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
- Azure Resource Management azure-mgmt-web SDK: https://learn.microsoft.com/python/api/overview/azure/web-readme
