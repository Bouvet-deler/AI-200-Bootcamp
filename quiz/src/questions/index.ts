// Auto-discover and load all question banks
// Uses Vite's import.meta.glob to find all JSON files in this directory

import type { Question } from '../types';

// Import all JSON files matching the pattern
const questionModules = import.meta.glob('/src/questions/**/*.json', {
  eager: true,
  as: 'raw',
});

// Extract questions from all loaded modules
const allQuestions: Question[] = [];

for (const [path, content] of Object.entries(questionModules)) {
  try {
    const questions = JSON.parse(content as string) as Question[];
    allQuestions.push(...questions);
  } catch (error) {
    console.error(`Failed to load questions from ${path}:`, error);
  }
}

// Group questions by domain and topic for easier access
export const questionsByDomain: Record<string, Question[]> = {};
export const questionsByTopic: Record<string, Question[]> = {};

for (const question of allQuestions) {
  // Group by domain
  if (!questionsByDomain[question.domain]) {
    questionsByDomain[question.domain] = [];
  }
  questionsByDomain[question.domain].push(question);

  // Group by topic (domain/topic)
  const topicKey = `${question.domain}/${question.topic}`;
  if (!questionsByTopic[topicKey]) {
    questionsByTopic[topicKey] = [];
  }
  questionsByTopic[topicKey].push(question);
}

export { allQuestions };
export default allQuestions;
