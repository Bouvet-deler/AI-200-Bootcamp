# AI-200 Quiz App

A React + Vite + TypeScript application for practicing AI-200 exam questions.

## Features

- **Per-topic practice**: Focus on specific topics (e.g., KQL, Cosmos DB)
- **Full-exam mode**: Randomized questions weighted by domain (matching official AI-200 percentages)
- **Question types**: Single-answer, multi-select, and build-list (ordering)
- **Progress tracking**: Score tracking during sessions
- **Explanations**: Detailed explanations with links back to topic guides
- **Auto-discovery**: Question banks are auto-loaded — just add JSON files

## Quick Start

```bash
cd quiz
npm install
npm run validate:questions
npm run build
npm run dev
```

Then open the URL printed in your terminal (typically `http://localhost:5173`).

## Project Structure

```
quiz/
├── src/
│   ├── App.tsx           # Main quiz component
│   ├── main.tsx          # Entry point
│   ├── types.ts          # TypeScript interfaces for questions
│   ├── index.css         # Styles
│   ├── lib/
│   │   └── examWeights.ts # Domain weights for full-exam sampling
│   └── questions/
│       ├── index.ts      # Auto-discovery of question banks
│       └── <domain>/
│           └── <topic>.json  # Question banks
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## Adding Questions

1. Create a JSON file at `src/questions/<domain>/<topic>.json`
2. Follow the schema defined in `src/types.ts`
3. Questions are **automatically discovered** — no code changes needed

### Question Schema

```typescript
type Question =
  | {
      type: 'single' | 'multi';
      choices: string[];
      answer: number[]; // zero-based choice indices
    }
  | {
      type: 'build-list';
      choices: { id: string; text: string }[];
      answer: string[]; // choice IDs in the correct order
    };

// Every variant also includes a unique id, domain, topic, question,
// teaching explanation, and (when a guide exists) reference.
```

### Example Question

```json
{
  "id": "kql-001",
  "domain": "04-secure-monitor",
  "topic": "kql",
  "type": "single",
  "question": "Which KQL operator filters rows based on a condition?",
  "choices": ["project", "where", "summarize", "extend"],
  "answer": [1],
  "explanation": "The `where` operator filters rows that match a condition.",
  "reference": "../../04-secure-monitor/kql/README.md"
}
```

## Domain Weights

Full-exam mode samples questions according to official AI-200 domain weights:

| Domain | Weight |
| --- | --- |
| 01-containers | 23.75% (official range 20–25%) |
| 02-data-services | 28.75% (official range 25–30%) |
| 03-connect-consume | 23.75% (official range 20–25%) |
| 04-secure-monitor | 23.75% (official range 20–25%) |

Microsoft publishes ranges, not an exact distribution. The representative values above stay
inside those ranges and add up to 100%; the app uses largest-remainder rounding to create a
whole-number question allocation.

## Tech Stack

- **Framework**: React 19
- **Bundler**: Vite 8
- **Language**: TypeScript 6
- **Styling**: Plain CSS (no framework)
- **Font**: Inter from Google Fonts

## Scripts

| Script | Description |
| --- | --- |
| `npm run dev` | Validate all banks, then start the development server |
| `npm run validate:questions` | Validate every discovered JSON question bank and local guide reference |
| `npm run build` | Validate every bank, type-check, and build for production |
| `npm run check` | Run the complete production-build check |
| `npm run preview` | Preview production build |
