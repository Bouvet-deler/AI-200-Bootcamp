# 01 — Develop containerized solutions on Azure (20–25%)

This domain is about **packaging your app as a container image and running it on Azure**. The
official skills-measured list splits into four topics, each with its own guide in this folder:

| Topic | What it covers |
| --- | --- |
| [`acr/`](acr/) | **Azure Container Registry** — build, store, version, and manage the container *images*. |
| [`app-service-containers/`](app-service-containers/) | Run a container on **Azure App Service** (managed web hosting). |
| [`container-apps-keda/`](container-apps-keda/) | Run containers on **Azure Container Apps** + event-driven scaling with **KEDA**. |
| [`aks/`](aks/) | Run containers on **Azure Kubernetes Service** with manifests, and troubleshoot them. |

> **The one decision this whole domain hinges on:** *which host do I run my container on —
> App Service, Container Apps, or AKS?* The exam tests this constantly as scenario questions
> ("a team needs X, which service?"). This page is the decision guide. ACR is the odd one out —
> it's not a host, it's the **registry** all three hosts pull images from.

---

## First: ACR is a registry, not a host

Before anything runs, the image has to live in a registry. **Azure Container Registry (ACR)** is
Azure's private-registry option (see [`acr/`](acr/)). All three hosts below can pull images from
ACR. The recommended pattern is a managed identity with the registry's pull role: **AcrPull** for
an RBAC-only registry, or **Container Registry Repository Reader** for an ABAC-enabled registry.
So a common pipeline is:

```text
  Your code + Dockerfile
        │  az acr build   (or docker build + docker push)
        ▼
  Azure Container Registry  ──pull (read role)──►  App Service / Container Apps / AKS
        (stores the image)                        (runs the image)
```

Everything after this page is about choosing that host on the right.

---

## The three hosts at a glance

| | **App Service (containers)** | **Container Apps (ACA)** | **AKS** |
| --- | --- | --- | --- |
| **What it is** | Managed PaaS web hosting that can run a container | Serverless containers (Kubernetes + KEDA under the hood, hidden from you) | Managed Kubernetes — you operate the workloads |
| **You manage** | Almost nothing (just the app + settings) | Almost nothing (no cluster) | The cluster's workloads, manifests, upgrades |
| **Best for** | A single web app/API, "lift a container into PaaS" | Microservices, event-driven jobs, APIs that should scale to zero | Complex platforms needing full Kubernetes control |
| **Scaling** | Scale up/out on paid plan capacity; **no scale-to-zero**\* | **Scale to zero** + HTTP/TCP and KEDA-backed event triggers | Anything Kubernetes can do (HPA, KEDA add-on, cluster autoscaler) — you configure it |
| **Scale-to-zero?** | No\* | **Yes** (min replicas 0) | Possible, but you configure it |
| **Rollout/versioning** | Deployment **slots** (staging → swap) | Immutable **revisions** + traffic splitting (canary/blue-green) | Deployment rolling updates, `kubectl rollout` |
| **Multi-container / microservices** | One main container; Linux apps can add sidecars (all scale together) | Multiple containers per app and many apps per environment (containers in one app scale together) | First-class Kubernetes orchestration |
| **Networking model** | Simple; VNet integration optional | Environment = the network + logging boundary | Full K8s networking (Services, Ingress, network policies) |
| **Learning curve / ops burden** | Lowest | Low | **Highest** (you need Kubernetes skills) |
| **Kubernetes knowledge needed** | None | None | **Yes** — pods, deployments, services, kubectl |

\* App Service can unload or stop an app, but the App Service Plan's reserved instances remain
billable. It isn't event-driven scale-to-zero in the Container Apps sense.

---

## How to choose — the decision factors

Walk these in order; the first one that clearly applies usually settles it.

### 1. Do you actually need Kubernetes? → picks AKS *out*
Choose **AKS only when you need Kubernetes itself** — fine-grained control over scheduling,
networking (network policies, service mesh), a large multi-service platform, or you're migrating
existing Kubernetes manifests. **The cost is operational burden:** you own workload manifests,
policy, troubleshooting, and many lifecycle choices; Azure manages the control plane. If nobody
on the team wants to run Kubernetes, this is
the wrong answer — and the exam often phrases the *right* answer as "…without managing
Kubernetes/infrastructure," which points you at Container Apps.

### 2. Is it a single, mostly always-on web app or API? → leans App Service
**App Service** is the simplest managed host. Reach for it when it's one web app/API, you want
the least to manage, and features like **deployment slots** (staging → swap), easy custom
domains/TLS, and **app settings + Key Vault references** matter. Weak spots: it is web-centric,
and its plan capacity doesn't do true event-driven **scale-to-zero**.

### 3. Do you need scale-to-zero, event-driven scaling, or microservices — but not Kubernetes? → picks Container Apps
**Container Apps** is the middle ground and, for modern container workloads, often the default.
Choose it when you want:
- **Scale to zero** when idle (no replica usage charge while at zero; networking, logging, or
  dedicated-profile resources can still cost money), and
- **Event-driven scaling** — scale on queue length, HTTP concurrency, CPU, cron, etc. via
  **KEDA** (e.g. a worker that scales out with a Service Bus / Storage Queue backlog), and/or
- **Microservices** in a shared **environment**, with **revisions** for canary/blue-green
  rollouts — all **without** operating a Kubernetes cluster.

### 4. What's the scaling *trigger*?
- Scale on **HTTP traffic** only → App Service or Container Apps both do this.
- Scale on **events/messages** (queue depth, Event Hub, etc.) or **to zero** → **Container Apps
  + KEDA**. This is the signature scenario for that topic.
- Scale in **arbitrary, cluster-wide, custom ways** → **AKS**.

### 5. Cost model
- **App Service** — you pay for the **plan** (reserved compute), running whether busy or idle.
- **Container Apps** — Consumption workloads are usage-based; scale-to-zero removes replica usage
  charges, but associated services and non-consumption resources can still be billed. Good for
  spiky or low-traffic workloads.
- **AKS** — you pay for **node compute** and related resources. The Free management tier has no
  cluster-management charge; Standard and Premium tiers add a management fee and an uptime SLA
  (Premium also adds long-term support). Nodes remain billable unless you scale eligible pools down.

### 6. Team skills & operational appetite
Be honest about who operates it. App Service and Container Apps are near-zero ops. AKS demands
real Kubernetes expertise for day-2 (upgrades, node pools, networking, incident response).

---

## Quick decision guide

- **One web app/API, keep it simple, always-on is fine** → **App Service**
- **Containerized microservices, scale-to-zero, event/queue-driven, canary rollouts, no K8s** → **Container Apps + KEDA**
- **You need full Kubernetes control / a big multi-service platform / existing manifests** → **AKS**
- **Wherever you land, images can live in** → **ACR** (grant the host identity the pull role that
  matches the registry's RBAC/ABAC permission mode)

---

## Where the "other" Azure hosts fit (context, not in this domain)

You'll hear these names; they're **out of scope for AI-200's container domain** but worth
placing so you don't confuse them with the three above:

- **Azure Functions** — serverless, event/HTTP-*triggered* functions; scales to zero. Great for
  small/spiky APIs and glue code. (It *can* run in a container, but it's a different programming
  model.)
- **Azure Container Instances (ACI)** — a single container with **no orchestrator**. Good for a
  quick one-off container or a burst job; **not** a typical production API host. (Container Apps
  superseded most ACI-for-apps scenarios.)
- **Azure API Management (APIM)** — **not a host**; a **gateway** you put *in front of* any of
  the above for auth, rate limiting, versioning, and a developer portal.
- **Virtual Machines** — raw IaaS; full control, most work. The escape hatch when nothing managed
  fits.

---

## Exam framing — the tells to listen for

Scenario questions rarely say "use Container Apps." They describe a need and expect you to map it:

| The scenario says… | …it's pointing at |
| --- | --- |
| "…without managing Kubernetes / infrastructure" | **Container Apps** (or App Service) |
| "scale to zero" / "pay nothing when idle" / "event-driven scaling on queue length" | **Container Apps + KEDA** |
| "full control over the Kubernetes cluster" / "deploy with manifest files" / "network policies" | **AKS** |
| "a single web app" / "deployment slots" / "simplest managed hosting" | **App Service** |
| "build/store/version container images" / "pull images from a private registry" | **ACR** |
| "grant the service permission to pull the image" | **managed identity + AcrPull** (RBAC-only ACR) or **Container Registry Repository Reader** (ABAC-enabled ACR) |

Pick each topic folder above and read its guide, then take the topic quizzes — the full-exam run
weights this domain at **20–25%**.

## Further reading

- Comparing Azure compute options: <https://learn.microsoft.com/azure/architecture/guide/technology-choices/compute-decision-tree>
- Container Apps vs other Azure container options: <https://learn.microsoft.com/azure/container-apps/compare-options>
- AI-200 study guide: <https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-200>
