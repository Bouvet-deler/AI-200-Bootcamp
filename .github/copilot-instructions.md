# GitHub Copilot instructions

This repo is a study workspace for **Microsoft Exam AI-200: Developing AI Cloud Solutions on
Azure**. It has topic guides (Markdown) + a React/Vite/TypeScript quiz app. These rules mirror
`CLAUDE.md` — keep them in sync.

## Audience

The reader is a .NET developer who is **new to Python and Azure**. Write for that reader.

## Code samples

- Use **Python only** — never C#/.NET, even for comparison.
- Comment generously: explain both the **Python idiom** and the **Azure concept** on each
  non-trivial line/block. Assume Python basics (`with`, comprehensions, `async`/`await`,
  decorators) are unfamiliar and briefly explain them.
- Prefer minimal, runnable scripts over production-hardened code.

## Topic guides

- One topic per folder under the numbered domain folders (`01-`…`04-`).
- Follow `docs/TOPIC_TEMPLATE.md`. Use `04-secure-monitor/kql/README.md` as the quality bar.
- Stay scoped to AI-200 objectives; link to Microsoft Learn for depth.
- Make Azure CLI setup blocks copy-pasteable with placeholder names.

## Quiz app

- Question banks: JSON at `quiz/src/questions/<domain>/<topic>.json`, **auto-discovered** via
  `import.meta.glob` — do not hand-register banks.
- Conform to the `Question` type in `quiz/src/types.ts`: `type` is `single | multi |
  build-list`; `answer` is always an array of choice indices; always add an `explanation` and
  a `reference` to the topic guide when it exists.
- Full-exam weights live in `quiz/src/lib/examWeights.ts` (mirror official domain %).
