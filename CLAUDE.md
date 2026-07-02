# CLAUDE.md — working conventions for this repo

This repo is a study workspace for **Microsoft Exam AI-200: Developing AI Cloud Solutions on
Azure** (Azure AI Cloud Developer Associate). It contains topic guides + a React/Vite/TS quiz
app. See `README.md` for the layout.

## Audience & tone

The reader (the repo owner) is an experienced **.NET developer** who is **new to Python and
to Azure**. Write for that reader:

- **All code samples are Python.** Do not add C#/.NET samples, even for comparison.
- **Comment generously.** Every non-trivial line or block gets a comment that explains *both*
  the Python idiom *and* the Azure concept. Assume the reader has never seen Python's
  `with`, list comprehensions, `async`/`await`, decorators, etc. — briefly explain them.
- Prefer clear, runnable, minimal scripts over clever or production-hardened code.
- Plain English first; introduce jargon only after defining it.

## Topic guides

- One topic per folder, grouped under the four numbered domain folders (`01-`…`04-`).
- Every guide follows `docs/TOPIC_TEMPLATE.md` (What it is → Why it's on the exam → Core
  concepts → Setup → Hands-on Python → Exam gotchas → Quiz yourself → Further reading).
- `04-secure-monitor/kql/README.md` is the fully-written reference — match its depth and
  style when authoring other topics.
- Keep content **scoped to AI-200 exam objectives**. Link to Microsoft Learn for depth rather
  than reproducing entire docs.
- Azure CLI setup blocks should be copy-pasteable; use placeholder names like
  `<resource-group>` and note the region.

## Quiz app (`quiz/`)

- Stack: **React + Vite + TypeScript**.
- Question banks are JSON files at `quiz/src/questions/<domain>/<topic>.json`, **auto-loaded**
  via `import.meta.glob` in `quiz/src/questions/index.ts` — never hand-register a bank.
- Question shape is defined in `quiz/src/types.ts`. Keep new questions valid against it:
  - `type`: `'single' | 'multi' | 'build-list'`
  - `answer` is always an array of choice indices (ordered, for `build-list`).
  - Always include a teaching `explanation`, and a `reference` link to the topic guide when
    one exists.
- Full-exam sampling weights live in `quiz/src/lib/examWeights.ts` and mirror the official
  domain percentages.

## When adding a new topic

1. Create `NN-domain/<topic>/README.md` from `docs/TOPIC_TEMPLATE.md`.
2. Add `quiz/src/questions/NN-domain/<topic>.json` with a few questions.
3. That's it — the quiz auto-discovers the new bank; the README links into the domain folder.

Keep this file and `.github/copilot-instructions.md` in sync — they state the same rules.
