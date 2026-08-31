# AGENTS.md — repository guidance

## Purpose

This is a personal study-and-practice workspace for **Microsoft Exam AI-200:
Developing AI Cloud Solutions on Azure**. It contains Azure topic guides,
commented Python samples, and a React/Vite/TypeScript quiz application.

## Audience and writing style

Write for an experienced **.NET developer** who is new to Python and Azure.

- Use plain English first; define Azure and Python terminology before relying on it.
- All instructional code samples must be **Python**. Do not add C#/.NET examples, including
  comparisons.
- Comment every non-trivial Python line or block. Explain both the Python idiom and the Azure
  concept; assume constructs such as `with`, comprehensions, `async`/`await`, and decorators
  are unfamiliar.
- Prefer small, runnable, readable examples over clever or production-hardened implementations.

## Topic guides and samples

- Keep one topic per folder under the numbered domain directories (`01-containers` through
  `04-secure-monitor`).
- Base new guides on `docs/TOPIC_TEMPLATE.md`; use `04-secure-monitor/kql/README.md` as the
  reference for depth and style.
- Keep material scoped to AI-200 objectives. Link to Microsoft Learn for additional depth rather
  than duplicating whole product documentation.
- Make Azure CLI setup blocks copy-pasteable. Use placeholders such as `<resource-group>` and
  state the Azure region and prerequisites when relevant.
- When adding a topic, add its guide and a matching quiz bank; discovery requires no code
  registration.

## Quiz app (`quiz/`)

- Stack: React, Vite, and TypeScript.
- Store question banks as JSON at `quiz/src/questions/<domain>/<topic>.json`.
- Banks are auto-discovered through `import.meta.glob` in `quiz/src/questions/index.ts`; never
  hand-register them.
- Follow the `Question` discriminated union in `quiz/src/types.ts`:
  - `type` must be `single`, `multi`, or `build-list`.
  - For `single` and `multi`, `answer` is an array of zero-based choice indices.
  - For `build-list`, choices use `id`/`text` objects and `answer` is the ordered array of choice
    IDs.
  - Include a teaching `explanation` and a `reference` link to the topic guide whenever one
    exists.
- Keep full-exam domain weights in `quiz/src/lib/examWeights.ts` aligned with the official exam
  percentages.

## Verification and change scope

- Make the smallest change that fulfills the request; preserve unrelated working-tree edits.
- Verify the part you changed. For quiz app code, run `npm run build` from `quiz/` when practical.
- Do not commit unless explicitly asked.

## Consistency

This guidance intentionally matches `CLAUDE.md` and `.github/copilot-instructions.md`. Update
those files too if any shared convention changes.
