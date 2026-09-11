// Microsoft publishes ranges rather than one exact percentage per AI-200 domain. These
// representative values sit inside every official range and add up to 100%, so they can be
// used as an actual probability distribution by the full-exam generator.

import type { DomainWeights } from '../types';

export const EXAM_WEIGHTS: DomainWeights = {
  '01-containers': 0.2375,      // Official range: 20-25%.
  '02-data-services': 0.2875,   // Official range: 25-30%.
  '03-connect-consume': 0.2375, // Official range: 20-25%.
  '04-secure-monitor': 0.2375,  // Official range: 20-25%.
};

// A sum of 1 means the weights account for exactly 100% of a generated exam.
export const TOTAL_WEIGHT = Object.values(EXAM_WEIGHTS).reduce((a, b) => a + b, 0);

// Floating-point arithmetic can introduce microscopic rounding differences, so use a tiny
// tolerance rather than comparing decimal values with ===.
export function validateWeights(): boolean {
  return Math.abs(TOTAL_WEIGHT - 1.0) < 1e-10;
}
