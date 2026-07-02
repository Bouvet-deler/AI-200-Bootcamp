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

```bash
# example
az group create --name <resource-group> --location westeurope
```

## Hands-on (Python)

> A minimal, runnable, **heavily commented** script. Explain both the Python idiom and the
> Azure concept on each non-trivial line. Assume the reader is new to Python and Azure.

```python
# what this script does, in one line

# pip install <the azure sdk package(s)>
```

## Exam gotchas

> The traps, the "which one do you pick" distinctions, defaults people forget, limits.
> Bullet list.

## Quiz yourself

Take the **<topic>** quiz in the [quiz app](../../quiz/) (bank:
`quiz/src/questions/<domain>/<topic>.json`).

## Further reading

- <Microsoft Learn links>
