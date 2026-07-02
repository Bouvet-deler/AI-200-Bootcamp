// Question types for the AI-200 quiz app

// Question base type
export interface QuestionBase {
  id: string;
  domain: string; // e.g., "04-secure-monitor"
  topic: string; // e.g., "kql"
  question: string;
  choices: string[];
  answer: number[]; // array of choice indices (0-based). For single-answer, length 1.
  explanation: string;
  reference?: string; // link to topic guide
}

// Discriminated union for question types
export type QuestionType = 'single' | 'multi' | 'build-list';

export interface SingleAnswerQuestion extends QuestionBase {
  type: 'single';
}

export interface MultiAnswerQuestion extends QuestionBase {
  type: 'multi';
}

export interface BuildListQuestion extends QuestionBase {
  type: 'build-list';
  // For build-list, answer is the correct order of choice indices
}

export type Question = SingleAnswerQuestion | MultiAnswerQuestion | BuildListQuestion;

// Domain weights for full-exam sampling (mirror official AI-200 percentages)
export interface DomainWeights {
  [domain: string]: number; // e.g., "01-containers": 0.225 (22.5%)
}

// Progress tracking stored in localStorage
export interface UserProgress {
  lastAttempted: string; // ISO timestamp
  correctByTopic: Record<string, number>;
  totalByTopic: Record<string, number>;
  fullExamAttempts: number;
}
