# <Topic name>

> Copy this file to `NN-domain/<topic>/README.md` and fill in each section.
> Delete these quote blocks as you go. See `04-secure-monitor/kql/README.md` for a fully
> worked example of the depth/style to aim for.

**Domain:** <e.g. 04 — Secure, monitor, troubleshoot (20–25%)>
**Maps to skill:** <the exact skill bullet(s) from the AI-200 study guide>

## What it is

> Plain-English explanation. No jargon until you've defined it. What problem does this Azure
> service/feature solve, and where does it sit in a solution?

## Why it's on the exam

> Which skill-measured bullet(s) this covers, and what the exam actually tests you on
> (concepts, "which service do I pick", CLI/SDK usage, gotchas).

## Core concepts

> The mental model. Key terms, how the pieces relate, a small diagram in text if useful.

## Setup

> Copy-pasteable Azure CLI to create the resource(s). Use placeholders like `<resource-group>`
> and state the region. Note any prerequisites (`az login`, extensions, roles).
> 
> Consider providing multiple setup methods:
> - CLI Setup — Copy-paste commands
> - Portal Setup — Point-and-click in browser

```bash
# example
az group create --name <resource-group> --location westeurope
```

## Hands-on (Python)

> A minimal, runnable, **heavily commented** script. Explain both the Python idiom and the
> Azure concept on each non-trivial line. Assume the reader is new to Python and Azure.
> 
> Reference the full source file (e.g., `app.py`) and include:
> - Virtual environment setup
> - Dependency installation
> - Environment variable configuration
> - Running the sample

```python
# what this script does, in one line

# pip install <the azure sdk package(s)>
```

## Worked examples

> Practical examples showing how to use the service. For query languages (KQL), show
> actual queries. For services, show common operations and their results.

## Cleanup

> Instructions to delete resources created during setup to avoid unnecessary Azure charges.
> Provide both CLI and Portal methods where applicable.
> 
> **Important:** Clearly warn about permanent deletion.

## Exam gotchas

> The traps, the "which one do you pick" distinctions, defaults people forget, limits.
> Bullet list.

## Test yourself

> Practical exercises with click-to-reveal solutions. Use `<details><summary>` blocks
> for collapsible questions and answers.

## Quiz yourself

Take the **<topic>** quiz in the [quiz app](../../quiz/) (bank:
`quiz/src/questions/<domain>/<topic>.json`).

## Further reading

- <Microsoft Learn links>
