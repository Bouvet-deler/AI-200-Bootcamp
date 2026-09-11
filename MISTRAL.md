# MISTRAL.md — working conventions for this repo (Mistral Vibe)

This file documents how **Mistral Vibe** (the CLI agent) will continue the work started with Claude on this AI-200 Bootcamp repository.

## Continuity with CLAUDE.md

**All conventions in [`CLAUDE.md`](CLAUDE.md) remain in effect.** This file supplements rather than replaces it.

Specifically, I will:
- Follow the same **audience & tone** (experienced .NET dev, new to Python and Azure)
- Write **Python-only** code samples with generous comments explaining both Python idioms and Azure concepts
- Structure all new topic guides using [`docs/TOPIC_TEMPLATE.md`](docs/TOPIC_TEMPLATE.md)
- Match the depth and style of the reference topic at [`04-secure-monitor/kql/README.md`](04-secure-monitor/kql/README.md)
- Use the same quiz app architecture (React + Vite + TypeScript) with auto-discovered question banks

## Working practices

- **Git safety**: Do not commit unless the user explicitly asks for a commit. Preserve unrelated
  working-tree changes.
- **Verification first**: I will prove code works before marking tasks complete (tests pass, code runs, expected output produced)
- **Minimal changes**: I will only modify what is necessary to complete your requested tasks

## Current project status

| Area | Status | Next Steps |
| --- | --- | --- |
| Topic guides | Fourteen guides across all four AI-200 domains | Keep facts aligned with the current Microsoft study guide |
| Quiz app | React/Vite/TypeScript app with per-topic and weighted full-exam modes | Build and validate after app changes |
| Question banks | One auto-discovered bank for every current topic | Add scenario questions as exam objectives evolve |

## How to request work

Tell me:
1. **What to build** — e.g., "complete the cosmos-db-nosql topic guide"
2. **Any preferences** — e.g., "focus on the Python sample and exam gotchas"
3. **Acceptance criteria** — e.g., "I want to be able to run the sample against my Azure subscription"

I will track complex work in a todo list and report progress at phase transitions.

---

*This file will be updated as conventions evolve. Keep it in sync with CLAUDE.md and .github/copilot-instructions.md.*
