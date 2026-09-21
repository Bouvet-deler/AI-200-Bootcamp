# Azure Kubernetes Service (AKS)

**Domain:** 01 — Develop containerized solutions on Azure (20–25%)
**Maps to skill:** *Deploy and manage applications to AKS by using manifest files* · *Monitor
and troubleshoot solutions on AKS and Container Apps by inspecting logs, events, and
end-to-end connectivity*

> Follows [`docs/TOPIC_TEMPLATE.md`](../../docs/TOPIC_TEMPLATE.md). The fully-written
> [KQL guide](../../04-secure-monitor/kql/) is the depth/style bar this page matches.

---

## What it is

**Azure Kubernetes Service (AKS)** is Azure's *managed* **Kubernetes**. Kubernetes ("k8s") is
the open-source system for running **containers** across a fleet of machines — it decides which
machine runs each container, restarts containers that crash, and scales them up and down.

Running Kubernetes yourself means operating the **control plane** (the brain: the API server,
scheduler, etc.) — patching it, making it highly available, securing it. AKS takes that off your
plate: **Azure operates the control plane**. You pay for node compute and related Azure resources.
The AKS **Free** management tier has no cluster-management fee and no uptime SLA; **Standard** and
**Premium** add a management charge and a financially backed uptime SLA, and Premium adds
long-term Kubernetes support.

Two names you'll see together, and how they differ:

- **AKS** — runs your containers at scale on a cluster. Use it when you need full Kubernetes:
  fine-grained networking, many services talking to each other, custom controllers, portability.
- **Azure Container Apps** — a *simpler*, serverless container platform built on top of
  Kubernetes that hides the cluster. Use it when you just want to run containers without managing
  Kubernetes objects. (Sibling topic — the exam contrasts the two.)

> Mental model: you hand AKS **manifest files** (YAML that *describes* what you want running),
> and Kubernetes continuously works to make reality match that description. You declare the
> destination; Kubernetes drives.

---

## Why it's on the exam

The two skill bullets are literally *"Deploy and manage applications to AKS by using manifest
files"* and *"Monitor and troubleshoot solutions on AKS … by inspecting logs, events, and
end-to-end connectivity."* So on AI-200, AKS is **deploy-with-YAML + troubleshoot** — not cluster
architecture trivia. Expect the exam to:

- Give you a **manifest** and ask what it creates, or which object you need (Deployment vs Pod vs
  Service).
- Ask which **`kubectl`** command applies a manifest (`apply -f`) or connects you to the cluster
  (`az aks get-credentials`).
- Show a broken pod (**ImagePullBackOff**, **CrashLoopBackOff**, **Pending**) and ask **what it
  means** or **which command diagnoses it** (`kubectl describe` / `logs` / `get events`).
- Test **how AKS pulls images from ACR**: `--attach-acr` grants `AcrPull` for an RBAC-only
  registry; an ABAC-enabled registry instead requires a manual **Container Registry Repository
  Reader** assignment. Missing access commonly appears as `ImagePullBackOff`.
- Connect to monitoring: **Container Insights** + **Log Analytics/KQL** for cluster logs (see
  [`../../04-secure-monitor/kql/`](../../04-secure-monitor/kql/)).

You don't need to administer Kubernetes — you need to *read* manifests and *diagnose* a broken
workload confidently.

---

## Core concepts

**The cluster hierarchy** (memorize the nesting — it's how you reason about scale and failure):

```text
Cluster                      # the whole AKS resource; Azure runs its control plane
└── Node pool                # a group of identical VMs (system pool and/or user pool)
    └── Node                 # one worker VM in the pool
        └── Pod              # the smallest deployable unit — usually ONE container
            └── Container    # your image (e.g. from ACR) actually running
```

- **Control plane** — the managed "brain" (API server, scheduler, etcd). Azure runs it; you
  never SSH into it. `kubectl` talks to the API server.
- **Node pool** — a set of same-sized VMs. A **system** node pool runs cluster add-ons; **user**
  node pools run your apps. The **cluster autoscaler** adds/removes nodes as demand changes.
- **Pod** — one (occasionally more) container plus its shared network identity. Pods are
  **cattle, not pets**: they're disposable and get replaced, each getting a new IP.

**The Kubernetes objects for the exam** (these are what your manifests declare):

| Object | What it is / does |
| --- | --- |
| **Pod** | The smallest unit — a running container. You rarely create pods directly; a Deployment makes them for you. |
| **Deployment** | Declares **desired state**: "run N replicas of this image." Manages a **ReplicaSet** that keeps N pods alive, and does **rolling updates** (replace pods gradually) and rollbacks. This is what you deploy 95% of the time. |
| **ReplicaSet** | The controller a Deployment creates to guarantee the replica count. You usually don't touch it directly. |
| **Service** | A **stable** network endpoint (name + virtual IP) in front of a changing set of pods. Pods come and go; the Service name stays. Load-balances across the pods it selects. |
| **Ingress** | HTTP(S) routing (host/path → Service) with one entry point + TLS. Needs an ingress controller. Think "layer-7 reverse proxy" in front of Services. |
| **ConfigMap** | **Non-secret** configuration as key-values, injected into pods as env vars or files. |
| **Secret** | Kubernetes object for sensitive values. Manifest/API values are base64-encoded, which is not confidentiality. AKS storage is platform-encrypted at rest; optional Key Vault KMS adds Kubernetes-layer encryption with customer-controlled keys. Restrict Secret access with RBAC and avoid committing Secret manifests. |
| **Namespace** | A logical partition of the cluster (e.g. `dev`, `prod`) for scoping names and access. |
| **Probes** | Health checks Kubernetes runs on a container: **liveness** (restart it if this fails) and **readiness** (only send traffic when this passes). |
| **Requests / limits** | Per-container resource **request** (used by the scheduler and for resource reservation) and **limit** (CPU is throttled; exceeding the memory limit can cause **OOMKilled**). |

**Service types** — this is a classic exam distinction:

| Type | Reachable from | Use for |
| --- | --- | --- |
| **ClusterIP** (default) | *Inside* the cluster only | Internal service-to-service traffic. |
| **NodePort** | Each node's IP on a high port | Basic external access; rarely used directly. |
| **LoadBalancer** | The public internet, via an **Azure Load Balancer** with a real **external IP** | Exposing an app publicly. On AKS this provisions an Azure LB automatically. |

> **Manifests: declarative vs imperative.** A **manifest** is a YAML file describing *desired
> state*. `kubectl apply -f file.yaml` is **declarative** — "make the cluster match this file"
> (re-runnable; it computes the diff). `kubectl create ...` / `kubectl run ...` are
> **imperative** — "do this one action now." The exam (and real GitOps) favors **`apply`**.

**Connecting to the cluster.** `kubectl` reads a config file called **kubeconfig**
(`~/.kube/config`) to know *which* cluster to talk to and how to authenticate.
`az aks get-credentials` **merges your AKS cluster's connection info + credentials into
kubeconfig**, after which plain `kubectl` commands hit that cluster.

**Pulling images from ACR.** Your container images live in **Azure Container Registry (ACR)**.
For an ACR in **RBAC Registry Permissions** mode, the AKS kubelet managed identity needs
**`AcrPull`**. `az aks update --attach-acr <acr>` grants it — no `imagePullSecrets` needed in
manifests. The shortcut is unsupported for an ACR in **RBAC Registry + ABAC Repository
Permissions** mode; manually grant **Container Registry Repository Reader** instead. Missing
access can produce **ImagePullBackOff / ErrImagePull**.

**Identity & security (brief).** AKS integrates with **Microsoft Entra ID** for cluster
authentication. The control plane and kubelet use distinct managed identities; the **kubelet
identity** pulls images from ACR. **Workload identity** lets a *pod* get an Entra token to call
Azure services such as Key Vault or Storage without storing credentials.

**Monitoring.** **Container Insights** collects node/pod telemetry and can collect container
**stdout/stderr logs** into a **Log Analytics workspace**, which you query with **KQL** (see
[`../../04-secure-monitor/kql/`](../../04-secure-monitor/kql/)). `kubectl logs` reads the current
container log (or one previous instance with `--previous`); collected `ContainerLogV2` records
remain queryable according to the workspace's retention settings.

---

## Setup

Goal: create an AKS cluster, connect `kubectl` to it, and attach an ACR so it can pull images —
so you have somewhere to `kubectl apply` a workload.

> **Prerequisites:** [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first) and
> **`kubectl`** (the Kubernetes CLI). If you don't have `kubectl`, install it via the official
> [Install and Set Up kubectl](https://kubernetes.io/docs/tasks/tools/) guide.

> **Two methods available:**
> - **[CLI](#cli-setup)** — Copy-paste commands below (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal (Web UI)](#portal-setup-web-ui)** — Point-and-click in your browser

### Set your variables

The CLI commands in **Setup** and **Cleanup** reference these as **shell variables** — set them
once for your shell, then run the `az`/`kubectl` commands as written. (The Portal method doesn't
use these.) What each one is:

- **`RG`** — resource group: the folder that holds your related Azure resources.
- **`LOCATION`** — the Azure region to deploy into.
- **`CLUSTER`** — name for the AKS cluster.
- **`ACR`** — the container registry name; must be **globally unique** and alphanumeric. The
  random suffix helps keep it unique.

The variable *names* are identical everywhere; only the **assignment syntax** differs by shell,
so copy the block that matches yours:

```bash
# bash / zsh — Linux, and macOS (its default shell)
RG="ai200-rg"
LOCATION="westeurope"
CLUSTER="ai200-aks"
ACR="ai200acr$RANDOM"
```

```fish
# fish — Linux / macOS
set RG ai200-rg
set LOCATION westeurope
set CLUSTER ai200-aks
set ACR ai200acr(random)
```

```powershell
# PowerShell — Windows (also cross-platform)
$RG = "ai200-rg"
$LOCATION = "westeurope"
$CLUSTER = "ai200-aks"
$ACR = "ai200acr$(Get-Random)"
```

```bat
:: Command Prompt (cmd.exe) — Windows
set RG=ai200-rg
set LOCATION=westeurope
set CLUSTER=ai200-aks
set ACR=ai200acr%RANDOM%
```

> **Referencing the variables in the commands below.** The `az`/`kubectl` snippets are written
> bash-style (`"$RG"`) and work unchanged in **bash/zsh, fish, and PowerShell** (all expand
> `$RG`). In **cmd**, write **`%RG%`** instead. The `\` at the end of long commands is a *bash*
> line-continuation — in PowerShell use a backtick `` ` ``, in cmd use `^`, or just put the whole
> command on one line.

### CLI Setup

First, install **`kubectl`** if you don't have it (check with `kubectl version --client`) —
follow the official [Install and Set Up kubectl](https://kubernetes.io/docs/tasks/tools/) guide
for macOS / Linux / Windows.

Then run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first).
Replace the `<placeholders>`.

> **First time in a subscription? Register the resource providers.** Azure doesn't enable every
> service ("**resource provider**", a namespace like `Microsoft.ContainerService`) on a
> subscription by default. If a provider AKS needs isn't registered, `az aks create` fails with
> **`MissingSubscriptionRegistration`**. Registration is **per-subscription and one-time**
> (requires Contributor/Owner). Do it once, up front:
>
> ```bash
> # --wait blocks until each provider flips to "Registered" (1–5 min); safe to re-run if already done.
> az provider register --namespace Microsoft.ContainerService --wait   # AKS itself
> az provider register --namespace Microsoft.OperationsManagement --wait # needed by --enable-addons monitoring
> az provider register --namespace Microsoft.OperationalInsights --wait  # Log Analytics (Container Insights)
>
> # Verify (each should print "Registered"):
> az provider show --namespace Microsoft.ContainerService --query registrationState -o tsv
> ```
>
> If `az provider register` returns an authorization error, you lack subscription rights — ask an
> Azure admin to register the namespaces above.

<details open>
<summary>Bash CLI Setup</summary>

```bash
# 1. Create the resource group (skip if you already made one in another topic).
az group create --name "$RG" --location "$LOCATION"

# 2. Create an Azure Container Registry to hold your images (Basic tier is fine for study).
#    Explicit RBAC-only permission mode makes --attach-acr/AcrPull valid; ABAC-enabled
#    registries require a manual Container Registry Repository Reader assignment instead.
az acr create \
  --resource-group "$RG" \
  --name "$ACR" \
  --sku Basic \
  --role-assignment-mode rbac

# 3. Create the AKS cluster.
#    --node-count 2         -> two worker VMs in the default node pool
#    --generate-ssh-keys    -> make SSH keys for the nodes if you don't have them
#    --attach-acr "$ACR"    -> grant the kubelet managed identity AcrPull on that registry NOW
#                              (so image pulls work without imagePullSecrets)
#    --enable-addons monitoring -> turn on Container Insights (logs/metrics to Log Analytics)
#    This takes a few minutes — Azure is provisioning VMs + wiring the control plane.
az aks create \
  --resource-group "$RG" \
  --name "$CLUSTER" \
  --node-count 2 \
  --generate-ssh-keys \
  --attach-acr "$ACR" \
  --enable-addons monitoring \
  --location "$LOCATION"

# 4. Merge the cluster's credentials into your local kubeconfig (~/.kube/config).
#    After this, plain 'kubectl' commands talk to THIS cluster.
#    '--overwrite-existing' replaces a stale entry with the same name.
az aks get-credentials --resource-group "$RG" --name "$CLUSTER" --overwrite-existing

# 5. Sanity check: list the nodes. You should see 2 nodes in 'Ready' state.
kubectl get nodes

# --- Attaching ACR AFTER the cluster already exists (the fix for ImagePullBackOff) ---
# If you forgot --attach-acr at create time, grant AcrPull now with a single command:
az aks update --resource-group "$RG" --name "$CLUSTER" --attach-acr "$ACR"
```

</details>

<details>
<summary>PowerShell CLI Setup</summary>

```powershell
az provider register --namespace Microsoft.ContainerService --wait
az provider register --namespace Microsoft.OperationsManagement --wait
az provider register --namespace Microsoft.OperationalInsights --wait
az provider show --namespace Microsoft.ContainerService --query registrationState -o tsv

az group create --name $RG --location $LOCATION
az acr create --resource-group $RG --name $ACR --sku Basic --role-assignment-mode rbac
az aks create --resource-group $RG --name $CLUSTER --node-count 2 `
  --generate-ssh-keys --attach-acr $ACR --enable-addons monitoring --location $LOCATION
az aks get-credentials --resource-group $RG --name $CLUSTER --overwrite-existing
kubectl get nodes
az aks update --resource-group $RG --name $CLUSTER --attach-acr $ACR
```

</details>

<details>
<summary>Command Prompt (cmd.exe) CLI Setup</summary>

```bat
az provider register --namespace Microsoft.ContainerService --wait
az provider register --namespace Microsoft.OperationsManagement --wait
az provider register --namespace Microsoft.OperationalInsights --wait
az provider show --namespace Microsoft.ContainerService --query registrationState -o tsv

az group create --name %RG% --location %LOCATION%
az acr create --resource-group %RG% --name %ACR% --sku Basic --role-assignment-mode rbac
az aks create --resource-group %RG% --name %CLUSTER% --node-count 2 ^
  --generate-ssh-keys --attach-acr %ACR% --enable-addons monitoring --location %LOCATION%
az aks get-credentials --resource-group %RG% --name %CLUSTER% --overwrite-existing
kubectl get nodes
az aks update --resource-group %RG% --name %CLUSTER% --attach-acr %ACR%
```

</details>

> **"Why do I suddenly have 4 resource groups?"** Creating one cluster spreads resources across
> **several** resource groups — most of them made **automatically**. This surprises everyone the
> first time. After `az aks create --enable-addons monitoring` you'll typically see:
>
> | Resource group | Created by | Holds |
> | --- | --- | --- |
> | **your RG** (e.g. `ai200-rg`) | **you** (`az group create`) | The **managed cluster** resource — the handle `kubectl` and `az aks` talk to. Put *your own* resources (ACR, Key Vault) here too. |
> | **`MC_<rg>_<cluster>_<region>`** | AKS, automatically | The cluster's **infrastructure**: node VMs (a VM Scale Set), disks, load balancer, public IP, and supporting identities. Azure owns this — **don't hand-edit or add to it**. |
> | **Log Analytics workspace RG** | the `--enable-addons monitoring` flag, when you don't supply a workspace | A default **Log Analytics workspace** that Container Insights ships logs/metrics to. Generated resource-group and workspace names can vary; query the cluster instead of hard-coding them. |
> | **Network Watcher resource group** | Azure, automatically when Network Watcher is enabled | Regional `NetworkWatcher` resources used by Azure networking. This group is shared and not AKS-specific. |
>
> The key split to understand (and a common exam-adjacent fact): your cluster's *object* lives in
> **your** RG, but the *machines that run your pods* live in the separate **`MC_…` node resource
> group** — its `nodeResourceGroup` field points at it. Deleting the cluster (or your RG) deletes
> the `MC_…` group automatically, so you never clean it up by hand (see [Cleanup](#cleanup)).

### Portal Setup (Web UI)

Prefer the browser? Create the same cluster in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Create the cluster:**
   - Click **+ Create a resource** → search "Kubernetes Service" → **Create** → **Kubernetes cluster**
   - Subscription + Resource group: your `ai200-rg`
   - Cluster preset: **Dev/Test** (cheapest for learning)
   - Kubernetes cluster name: `ai200-aks`
   - Region: `West Europe`
   - Node size / count: leave defaults (or 2 nodes) for study
   - Click **Next** through the tabs; on **Integrations**, pick your **Container registry**
     (`ai200acr…`) so AKS gets **AcrPull**, and enable **Container Insights** (Log Analytics)
   - Click **Review + create** → **Create** (provisioning takes a few minutes)

3. **Connect `kubectl`:**
   - Open the cluster → click **Connect** at the top → copy the shown `az aks get-credentials`
     command and run it locally (the portal can't populate *your* kubeconfig for you).

4. **Attach ACR later (if you skipped it):**
   - Cluster → **Settings → Container registry** → select your ACR → **Save** (grants AcrPull).

---

## Deploy with manifests

A **Deployment** manages your app's pods; a **Service** of type **LoadBalancer** gives it a
public IP. The complete manifest for a tiny web app lives next to this guide in
[`webapp.yaml`](./webapp.yaml). It bundles four objects (Namespace, ConfigMap, Deployment,
Service) separated by `---`, and matches the workload `app.py` later inspects
(namespace `demo`, deployment `webapp`, container port `8080`).

The manifest's `image:` line is a placeholder (`<acr-login-server>/webapp:v1`) — Kubernetes can't
pull a placeholder, so **build and push the image first**, then point the manifest at it.

**1. Build the `webapp:v1` image and push it to your ACR.** The build context lives next to this
guide in [`webapp-src/`](./webapp-src/) — a tiny **nginx** image reconfigured to listen on
**8080** (to match the manifest). `az acr build` builds it **in the cloud** and pushes it in one
step, so you don't need Docker installed locally:

```bash
# Uses the $ACR variable from "Set your variables". Builds ./webapp-src on ACR's builders,
# tags the result 'webapp:v1', and pushes it into your registry.
az acr build --registry "$ACR" --image webapp:v1 ./webapp-src

# Sanity check: the tag should now exist in the registry.
az acr repository show-tags --name "$ACR" --repository webapp --output table
```

**2. Point the manifest at your image.** In [`webapp.yaml`](./webapp.yaml), replace the
`<acr-login-server>` placeholder on the `image:` line with your registry's login server
(`<name>.azurecr.io`):

```bash
# Prints your registry's login server, e.g. ai200acr123.azurecr.io — paste it into webapp.yaml
# so the image line reads:  image: ai200acr123.azurecr.io/webapp:v1
az acr show --name "$ACR" --query loginServer --output tsv
```

> **Prefer not to build anything?** Swap the `image:` line for the public image
> `mcr.microsoft.com/azuredocs/aks-helloworld:v1` instead — but it listens on port **80**, so
> also change `containerPort`, `targetPort`, and **both** probe ports from `8080` to `80`.

**3. Apply the manifest and watch it roll out:**

```bash
# Apply the manifest DECLARATIVELY: "make the cluster match this file."
# 'apply -f' creates what's missing and updates what changed. Re-runnable.
kubectl apply -f webapp.yaml

# Watch the rollout complete (all 3 replicas updated & ready).
kubectl rollout status deployment/webapp -n demo

# Get the public IP the LoadBalancer Service was assigned (shows <pending> until provisioned).
kubectl get service webapp -n demo --watch

# Made a bad change? Roll back to the previous revision:
kubectl rollout undo deployment/webapp -n demo
```

---

## Cleanup

Goal: delete the resources created above to stop paying for node VMs and networking. The
**Free management tier** has no cluster-management charge; Standard and Premium do. Worker VMs
and other Azure resources are billed on every tier.

> **Two methods available:**
> - **[CLI](#cli-cleanup)** — Copy-paste commands below
> - **[Azure Portal (Web UI)](#portal-cleanup-web-ui)** — Point-and-click

### CLI Cleanup

Set `RG` and `CLUSTER` as shown in [Set your variables](#set-your-variables), then:

```bash
# Optional: remove the in-cluster objects first (frees the public LoadBalancer IP promptly).
kubectl delete -f webapp.yaml     # deletes exactly what the manifest created
# ...or just the namespace, which takes everything in it:
kubectl delete namespace demo

# Delete just the AKS cluster (leaves the resource group + ACR)...
az aks delete --resource-group "$RG" --name "$CLUSTER" --yes --no-wait

# ...or delete the whole resource group and everything in it (cluster and ACR).
# '--yes' skips confirmation; '--no-wait' returns without waiting for completion.
az group delete --name "$RG" --yes --no-wait
```

> If AKS created a default Log Analytics workspace in a separate resource group, deleting
> `"$RG"` does **not** delete that workspace. In the portal, open the cluster's **Insights**
> settings first (or query its monitoring add-on profile) to identify and remove a study-only
> workspace separately. Do not blindly delete shared monitoring or Network Watcher resources.

> **Note:** A `LoadBalancer` Service creates an **Azure Load Balancer + public IP** that bill
> separately. Deleting the Service (or the namespace/cluster) releases them — don't leave an
> orphaned cluster running just to keep an IP.

### Portal Cleanup (Web UI)

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)
2. **Delete the Resource Group** (fastest): **Resource groups** → your group → **Delete
   resource group**, type the name to confirm, **Delete**.
3. **Or delete just the cluster:** open `ai200-aks` → **Delete** in the toolbar.

> **Tip:** AKS also creates a hidden **node resource group** (named `MC_<rg>_<cluster>_<region>`)
> holding the node VMs, disks, and load balancer. Deleting the *cluster* (or its resource group)
> removes that automatically — don't delete the `MC_…` group by hand.

---

## Hands-on (Python)

`app.py` is a **programmatic troubleshooting tool** built on the official **`kubernetes`** Python
client. It's the SDK mirror of the `kubectl get pods` → `describe` → `logs` loop you'd run by
hand: it lists pods in a namespace, flags the unhealthy ones, and for each prints its **recent
events** and **last log lines** — then lists **Services and their EndpointSlices** to sanity-check
connectivity. In other words, it automates "why is this pod broken?"

> New to Python? [`app.py`](app.py) is **heavily commented** — every non-trivial line explains
> both the Python idiom and the Kubernetes/Azure concept.

> **Prerequisite:** run `az login` and `az aks get-credentials …` first (Setup step 4). The
> script reads the **same kubeconfig** that `get-credentials` populated — no connection string.

> **Remember:** Run all commands below from this folder (`01-containers/aks/`).

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
# The official Kubernetes client for Python.
pip install kubernetes
```

### Run the sample

```bash
# Inspect the 'demo' namespace you deployed above (default is 'default').
K8S_NAMESPACE=demo python app.py
```

You'll see each pod's phase, restart count, and node; for any unhealthy pod, its recent events
and last log lines; then each Service and its backing endpoints.

> **Tip:** To deactivate the virtual environment when done: `deactivate`

---

## Worked examples

The tested skill is **troubleshooting by inspecting logs, events, and end-to-end connectivity**.
These are the copy-paste `kubectl` snippets to reach for. (`-n demo` targets the namespace;
drop it for `default`.)

**1. See pod status — the first thing you always run:**

```bash
kubectl get pods -n demo                 # STATUS column tells you a lot at a glance
kubectl get pods -n demo -o wide         # adds NODE + pod IP columns
kubectl get pods -n demo --watch         # live-update as states change
```

**2. Read cluster events — why something failed to schedule / pull / start:**

```bash
kubectl get events -n demo --sort-by=.lastTimestamp   # newest at the bottom
```

**3. Describe a pod — the single most useful troubleshooting command.** Shows the pod's events,
image, probe config, and the exact reason a container is stuck:

```bash
kubectl describe pod <pod-name> -n demo
# Look at the 'Events' section AND each container's 'State'/'Last State' + 'Reason'.
```

**4. Read logs — what the app itself printed (stdout/stderr):**

```bash
kubectl logs <pod-name> -n demo                 # current container's logs
kubectl logs <pod-name> -n demo -f              # -f = follow (stream live)
kubectl logs <pod-name> -n demo -p              # -p = PREVIOUS container (vital for CrashLoopBackOff)
kubectl logs <pod-name> -n demo -c <container>  # -c = pick a container in a multi-container pod
```

**5. Check connectivity — Service, its EndpointSlices, and a request from inside a pod:**

```bash
# Does the Service exist and have an external IP (LoadBalancer)?
kubectl get service webapp -n demo

# EndpointSlices contain the healthy pod IPs behind the Service.
# EMPTY endpoints = the selector matches no READY pods (bad label or failing readiness probe)
# -> this is the classic "Service returns nothing" cause.
kubectl get endpointslices -n demo -l kubernetes.io/service-name=webapp

# Exec INTO a demo pod and use BusyBox wget to call the Service by NAME.
# This tests in-cluster DNS + routing; the nginx:alpine image doesn't include curl.
# 'webapp.demo.svc.cluster.local' is the Service's DNS name; 'webapp' works within the namespace.
kubectl exec <pod-name> -n demo -- wget -qO- http://webapp.demo:80/
```

**6. Common pod states and what they mean** (know these cold — the exam asks by symptom):

| STATUS | Meaning | First thing to check |
| --- | --- | --- |
| **Pending** | Can't be **scheduled** — no node has enough CPU/memory, or a constraint can't be met | `kubectl describe pod` → Events (FailedScheduling); node capacity / requests |
| **ImagePullBackOff** / **ErrImagePull** | Can't **pull the image** — wrong name/tag, network failure, or registry authorization missing | Check image/tag and network; for RBAC-only ACR, verify kubelet `AcrPull`; for ABAC ACR, verify Repository Reader. |
| **CrashLoopBackOff** | Container **starts then exits repeatedly** — app crashes on boot, bad config, failing liveness probe | `kubectl logs <pod> -p` (previous run); env/ConfigMap/Secret |
| **OOMKilled** | Container exceeded its **memory `limit`** and was killed | Raise the memory limit or fix the leak; `describe` → Last State |
| **Running** but not **Ready** | Container is up but its **readiness probe** fails → excluded from the Service | Probe path/port; the app's health endpoint |

**7. `az aks` equivalents / cluster-level checks:**

```bash
# Confirm nodes are healthy (a NotReady node can strand pods in Pending).
kubectl get nodes

# For an RBAC-only ACR, grant the kubelet identity AcrPull if it wasn't attached:
az aks update --resource-group ai200-rg --name ai200-aks --attach-acr ai200acr123

# Re-pull cluster credentials if kubectl auth is stale/expired.
az aks get-credentials --resource-group ai200-rg --name ai200-aks --overwrite-existing

# Show the cluster's provisioning/power state and version.
az aks show --resource-group ai200-rg --name ai200-aks --query "{state:provisioningState,version:kubernetesVersion}" -o table
```

**8. Query retained logs with KQL (Container Insights).** `kubectl logs` reads a current
container, or one terminated instance with `--previous`; **Container Insights** ships
stdout/stderr to Log Analytics where records can remain searchable across restarts.
In **Log Analytics → Logs**, run KQL (see [`../../04-secure-monitor/kql/`](../../04-secure-monitor/kql/)):

```kusto
ContainerLogV2
| where TimeGenerated > ago(30m)
| where PodNamespace == "demo"
| project TimeGenerated, PodName, LogMessage
| order by TimeGenerated desc
```

---

## Exam gotchas

- **`kubectl apply -f` (declarative) vs `kubectl create`/`run` (imperative).** `apply` reconciles
  the cluster to a manifest and is re-runnable — the deploy-with-manifests answer. `create`/`run`
  are one-shot imperative actions.
- **Deployment vs Pod vs Service.** A **Pod** is one running instance (disposable); a
  **Deployment** keeps N pods alive and does rolling updates; a **Service** is the *stable*
  network endpoint in front of them. You almost never create bare Pods.
- **LoadBalancer = external IP.** Only a **`LoadBalancer`** (or an Ingress) exposes an app to the
  internet with a public IP. **ClusterIP** (the default) is *internal-only*; **NodePort** is
  rarely the intended answer.
- **ImagePullBackOff → grant registry read access.** For an RBAC-only ACR, the kubelet managed
  identity needs **`AcrPull`** and `az aks update --attach-acr <acr>` assigns it. For an
  ABAC-enabled ACR, manually grant **Container Registry Repository Reader** because
  `--attach-acr` is unsupported. No `imagePullSecrets` are needed in either managed-identity
  path. Also check the image name/tag.
- **CrashLoopBackOff ≠ ImagePullBackOff.** CrashLoop = the image pulled fine but the **container
  keeps exiting** (app error / bad config / failing liveness probe) → read logs with **`-p`**.
  ImagePull = it never started because the **image couldn't be fetched**.
- **Pending = scheduling.** The pod can't be placed — usually **insufficient CPU/memory** or a
  `NotReady` node. `describe` shows `FailedScheduling`.
- **Readiness vs liveness probe.** **Readiness** gates *traffic* (fail → removed from the
  Service's endpoints, pod keeps running). **Liveness** gates *life* (fail → container
  **restarted**). Empty Service endpoints often mean readiness is failing.
- **ConfigMap vs Secret.** Non-secret config → **ConfigMap**. Sensitive values → **Secret**.
  Base64 in the Kubernetes API is only an encoding, while AKS also applies Azure platform
  encryption at rest. Restrict Secret access with Kubernetes RBAC; use Key Vault and workload
  identity when the design calls for centrally managed secrets.
- **`get-credentials` is what makes `kubectl` work.** Without `az aks get-credentials`, your
  kubeconfig doesn't know the cluster. It *merges* creds — it doesn't create the cluster.
- **`kubectl logs` is short-lived.** It reads the current container, and `-p` can read one
  previous terminated instance. For retained/searchable logs use **Container Insights + KQL**
  in Log Analytics.
- **Only the Free management tier has no management fee.** Standard and Premium add a
  cluster-management charge and uptime SLA. Node-pool VMs and related Azure resources are billed
  on every tier.

---

## Quiz yourself

Take the **AKS** quiz in the [quiz app](../../quiz/)
(bank: [`quiz/src/questions/01-containers/aks.json`](../../quiz/src/questions/01-containers/aks.json)).

## Further reading

- AKS overview: <https://learn.microsoft.com/azure/aks/what-is-aks>
- Deploy an app with manifests (quickstart): <https://learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-cli>
- Authenticate AKS with ACR (`--attach-acr`): <https://learn.microsoft.com/azure/aks/cluster-container-registry-integration>
- Kubernetes objects (Deployment, Service, ConfigMap, Secret): <https://kubernetes.io/docs/concepts/>
- `kubectl` cheat sheet: <https://kubernetes.io/docs/reference/kubectl/cheatsheet/>
- Container Insights for AKS: <https://learn.microsoft.com/azure/azure-monitor/containers/container-insights-overview>
- Kubernetes Python client: <https://github.com/kubernetes-client/python>
