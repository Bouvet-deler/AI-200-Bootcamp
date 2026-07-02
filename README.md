# AI-200 Bootcamp

> **AI-Generated Content Warning:** This project and its information were created by AI. There is no guarantee that all information is correct at this time. Please verify critical details independently.

A personal study-and-practice workspace for **Microsoft Exam AI-200: Developing AI Cloud
Solutions on Azure** (the *Azure AI Cloud Developer Associate* certification).

AI-200 is a **Python-focused, back-end developer** exam. It is *not* about training models —
it is about wiring AI capabilities into a production application on Azure: containers, data
services with vector search, event/message plumbing, and the security + observability around
it all.

> **How this repo teaches:** every code sample is **Python**, and every sample is
> **heavily commented** so it's readable even if you know neither Python nor Azure. Read a
> topic guide, run the sample, then quiz yourself in the web app.

---

## The four exam domains

The folders map 1:1 to the official skills-measured domains (and their weightings):

| Folder | Domain | Weight |
| --- | --- | --- |
| [`01-containers/`](01-containers/) | Develop containerized solutions on Azure | 20–25% |
| [`02-data-services/`](02-data-services/) | Develop AI solutions by using Azure data management services | 25–30% |
| [`03-connect-consume/`](03-connect-consume/) | Connect to and consume Azure services | 20–25% |
| [`04-secure-monitor/`](04-secure-monitor/) | Secure, monitor, troubleshoot Azure solutions | 20–25% |

A score of **700** (out of 1000) is required to pass.
Official study guide: <https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-200>

## Topics

```
01-containers/            acr · app-service-containers · container-apps-keda · aks
02-data-services/         cosmos-db-nosql · postgresql-pgvector · azure-managed-redis
03-connect-consume/       service-bus · event-grid · azure-functions
04-secure-monitor/        key-vault · app-configuration · opentelemetry · kql
```

Each topic folder has a `README.md` guide. **[`04-secure-monitor/kql/`](04-secure-monitor/kql/)
is fully written** as the reference model — the other topics are stubs to fill in as you
study, using the KQL guide (and [`docs/TOPIC_TEMPLATE.md`](docs/TOPIC_TEMPLATE.md)) as the
pattern.

## The quiz app

A React + Vite + TypeScript app in [`quiz/`](quiz/):

- **Per-topic** practice or a **full-exam** run (sampled to match domain weights).
- **Single-answer, multi-select, and build-list** (ordering) question types.
- **Explanations** shown after you answer, linking back to the topic guide.
- **Progress tracking** in your browser's `localStorage` so you can spot weak areas.

```bash
cd quiz
npm install
npm run dev      # open the printed local URL
```

### Adding questions

Question banks are plain JSON files under `quiz/src/questions/<domain>/<topic>.json` and are
**auto-discovered** — no code wiring. Add a question by editing an existing file, or add a
whole topic by dropping a new `<topic>.json`. See `quiz/src/types.ts` for the schema.

## Suggested workflow

1. Pick a topic folder and read its guide.
2. Run the (commented) Python sample against your own Azure subscription.
3. Take that topic's quiz; review the explanations on anything you miss.
4. Periodically run a **full-exam** session to gauge readiness.
