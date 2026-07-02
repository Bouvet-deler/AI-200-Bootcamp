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
npm audit fix        # Optional: auto-fix any dependency vulnerabilities
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
interface Question {
  id: string;           // unique identifier
  domain: string;      // e.g., "04-secure-monitor"
  topic: string;       // e.g., "kql"
  type: 'single' | 'multi' | 'build-list';  // question type
  question: string;    // the question text
  choices: string[];   // array of answer choices
  answer: number[];    // array of correct choice indices (0-based)
  explanation: string; // teaching explanation shown after answering
  reference?: string;  // link to topic guide (optional)
}
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
| 01-containers | 22.5% |
| 02-data-services | 27.5% |
| 03-connect-consume | 22.5% |
| 04-secure-monitor | 22.5% |

Weights are defined in `src/lib/examWeights.ts` and can be adjusted as needed.

## Tech Stack

- **Framework**: React 18
- **Bundler**: Vite 5
- **Language**: TypeScript 5
- **Styling**: Plain CSS (no framework)
- **Font**: Inter from Google Fonts

## Important Notice

**Background Images License**: This project currently uses background images (`background-light.jpg` and `background-dark.jpg`) from the `assets/` folder. If this project is ever going to be published to the public, **you must replace these background images with images that you own or have the proper license for**. The current images may be subject to copyright restrictions and are not guaranteed to be free for public use.

## Scripts

| Script | Description |
| --- | --- |
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
