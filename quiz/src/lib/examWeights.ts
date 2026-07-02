// AI-200 exam domain weights (official Microsoft percentages)
// These mirror the "Weight" column in README.md

import type { DomainWeights } from '../types';

export const EXAM_WEIGHTS: DomainWeights = {
  '01-containers': 0.225,    // 20-25% -> using midpoint 22.5%
  '02-data-services': 0.275, // 25-30% -> using midpoint 27.5%
  '03-connect-consume': 0.225, // 20-25% -> using midpoint 22.5%
  '04-secure-monitor': 0.225, // 20-25% -> using midpoint 22.5%
};

// Total should equal ~1.0 (allowing for rounding)
export const TOTAL_WEIGHT = Object.values(EXAM_WEIGHTS).reduce((a, b) => a + b, 0);

// Validate weights sum to approximately 1
export function validateWeights(): boolean {
  return Math.abs(TOTAL_WEIGHT - 1.0) < 0.02; // Allow 2% rounding error
}
