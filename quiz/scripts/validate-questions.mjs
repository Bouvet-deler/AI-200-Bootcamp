import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { basename, dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

// Resolve paths from this script rather than the caller's working directory, so the validator
// behaves the same from the repository root, quiz/, or a continuous-integration runner.
const quizRoot = fileURLToPath(new URL('../', import.meta.url));
const repositoryRoot = resolve(quizRoot, '..');
const questionsRoot = join(quizRoot, 'src', 'questions');
const allowedTypes = new Set(['single', 'multi', 'build-list']);
const seenIds = new Map();
const seenPrompts = new Map();
const errors = [];
const countsByType = { single: 0, multi: 0, 'build-list': 0 };
const markdownAnchorsByFile = new Map();

// Recursively walk the auto-discovery directory because each exam domain owns a subfolder.
function findJsonFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const entryPath = join(directory, entry.name);
    if (entry.isDirectory()) return findJsonFiles(entryPath);
    return entry.isFile() && extname(entry.name) === '.json' ? [entryPath] : [];
  });
}

function report(file, questionIndex, message) {
  const location = `${relative(repositoryRoot, file)}[${questionIndex}]`;
  errors.push(`${location}: ${message}`);
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

// GitHub-style heading links lowercase text, discard formatting/punctuation, and replace spaces
// with hyphens. The guides use straightforward ATX headings, so this covers their local anchors
// while also accounting for duplicate headings with GitHub's -1, -2 suffix convention.
function markdownAnchors(file) {
  if (markdownAnchorsByFile.has(file)) return markdownAnchorsByFile.get(file);

  const anchors = new Set();
  const occurrences = new Map();
  for (const line of readFileSync(file, 'utf8').split(/\r?\n/)) {
    const match = line.match(/^#{1,6}\s+(.+?)\s*#*\s*$/);
    if (!match) continue;

    const headingText = match[1]
      .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
      .replace(/<[^>]+>/g, '')
      .replace(/[`*_~]/g, '');
    const baseSlug = headingText
      .toLowerCase()
      .replace(/[^\p{Letter}\p{Number}\s_-]/gu, '')
      .trim()
      .replace(/ /g, '-');
    const duplicateNumber = occurrences.get(baseSlug) ?? 0;
    occurrences.set(baseSlug, duplicateNumber + 1);
    anchors.add(duplicateNumber === 0 ? baseSlug : `${baseSlug}-${duplicateNumber}`);
  }

  markdownAnchorsByFile.set(file, anchors);
  return anchors;
}

function validateLocalReference(file, questionIndex, reference) {
  // The app treats leading ../ segments as a marker and then links from the repository root.
  // Mirror that behaviour here so a typo cannot become a broken "Read the topic guide" link.
  const hashPosition = reference.indexOf('#');
  const referencePath = hashPosition === -1 ? reference : reference.slice(0, hashPosition);
  const anchor = hashPosition === -1 ? '' : decodeURIComponent(reference.slice(hashPosition + 1));
  const repositoryPath = referencePath.replace(/^(?:\.\.\/)+/, '');
  const resolvedPath = resolve(repositoryRoot, repositoryPath);
  const repositoryPrefix = `${repositoryRoot}${sep}`;

  if (resolvedPath !== repositoryRoot && !resolvedPath.startsWith(repositoryPrefix)) {
    report(file, questionIndex, `reference escapes the repository: ${reference}`);
  } else if (!existsSync(resolvedPath)) {
    report(file, questionIndex, `reference target does not exist: ${reference}`);
  } else if (anchor && extname(resolvedPath).toLowerCase() === '.md' && !markdownAnchors(resolvedPath).has(anchor)) {
    report(file, questionIndex, `reference anchor does not exist: ${reference}`);
  }
}

function validateIndexedAnswer(file, questionIndex, question) {
  if (!question.choices.every(isNonEmptyString)) {
    report(file, questionIndex, `${question.type} choices must all be non-empty strings`);
  }
  if (new Set(question.choices.map(choice => choice.trim())).size !== question.choices.length) {
    report(file, questionIndex, `${question.type} choices contain duplicate text`);
  }
  if (!Array.isArray(question.answer) || question.answer.length === 0) {
    report(file, questionIndex, `${question.type} answer must be a non-empty array`);
    return;
  }
  if (question.type === 'single' && question.answer.length !== 1) {
    report(file, questionIndex, 'single answer must contain exactly one choice index');
  }

  const uniqueAnswers = new Set(question.answer);
  if (uniqueAnswers.size !== question.answer.length) {
    report(file, questionIndex, 'answer contains duplicate choice indices');
  }
  for (const answerIndex of question.answer) {
    if (!Number.isInteger(answerIndex) || answerIndex < 0 || answerIndex >= question.choices.length) {
      report(file, questionIndex, `answer index ${String(answerIndex)} is outside the choices array`);
    }
  }
}

function validateBuildList(file, questionIndex, question) {
  const choiceIds = [];
  for (const choice of question.choices) {
    if (typeof choice !== 'object' || choice === null || Array.isArray(choice)) {
      report(file, questionIndex, 'build-list choices must be id/text objects');
      continue;
    }
    if (!isNonEmptyString(choice.id) || !isNonEmptyString(choice.text)) {
      report(file, questionIndex, 'every build-list choice needs non-empty id and text strings');
      continue;
    }
    choiceIds.push(choice.id);
  }

  if (new Set(choiceIds).size !== choiceIds.length) {
    report(file, questionIndex, 'build-list choice IDs must be unique within the question');
  }
  const choiceTexts = question.choices
    .filter(choice => typeof choice === 'object' && choice !== null && isNonEmptyString(choice.text))
    .map(choice => choice.text.trim());
  if (new Set(choiceTexts).size !== choiceTexts.length) {
    report(file, questionIndex, 'build-list choices contain duplicate text');
  }
  if (!Array.isArray(question.answer) || question.answer.length === 0) {
    report(file, questionIndex, 'build-list answer must be a non-empty ordered array of choice IDs');
    return;
  }
  if (!question.answer.every(isNonEmptyString)) {
    report(file, questionIndex, 'build-list answer must contain only non-empty choice IDs');
  }
  if (new Set(question.answer).size !== question.answer.length) {
    report(file, questionIndex, 'build-list answer contains duplicate choice IDs');
  }
  for (const answerId of question.answer) {
    if (!choiceIds.includes(answerId)) {
      report(file, questionIndex, `build-list answer refers to unknown choice ID: ${answerId}`);
    }
  }
}

const questionFiles = findJsonFiles(questionsRoot).sort();
let questionCount = 0;

for (const file of questionFiles) {
  let bank;
  try {
    bank = JSON.parse(readFileSync(file, 'utf8'));
  } catch (error) {
    errors.push(`${relative(repositoryRoot, file)}: invalid JSON (${error.message})`);
    continue;
  }

  if (!Array.isArray(bank) || bank.length === 0) {
    errors.push(`${relative(repositoryRoot, file)}: a question bank must be a non-empty JSON array`);
    continue;
  }

  const expectedDomain = basename(dirname(file));
  const expectedTopic = basename(file, '.json');
  questionCount += bank.length;

  bank.forEach((question, questionIndex) => {
    if (typeof question !== 'object' || question === null || Array.isArray(question)) {
      report(file, questionIndex, 'question must be a JSON object');
      return;
    }

    for (const field of ['id', 'domain', 'topic', 'question', 'explanation', 'reference']) {
      if (!isNonEmptyString(question[field])) {
        report(file, questionIndex, `${field} must be a non-empty string`);
      }
    }

    if (isNonEmptyString(question.id)) {
      if (seenIds.has(question.id)) {
        report(file, questionIndex, `duplicate id ${question.id}; first used in ${seenIds.get(question.id)}`);
      } else {
        seenIds.set(question.id, relative(repositoryRoot, file));
      }
    }
    if (isNonEmptyString(question.question)) {
      // Collapse incidental whitespace before comparing prompts, so near-identical duplicate
      // questions cannot quietly appear in two banks under different IDs.
      const normalizedPrompt = question.question.trim().replace(/\s+/g, ' ').toLocaleLowerCase();
      if (seenPrompts.has(normalizedPrompt)) {
        report(file, questionIndex, `duplicate question prompt; first used in ${seenPrompts.get(normalizedPrompt)}`);
      } else {
        seenPrompts.set(normalizedPrompt, `${relative(repositoryRoot, file)}[${questionIndex}]`);
      }
    }
    if (question.domain !== expectedDomain) {
      report(file, questionIndex, `domain must match its folder (${expectedDomain})`);
    }
    if (question.topic !== expectedTopic) {
      report(file, questionIndex, `topic must match its filename (${expectedTopic})`);
    }
    if (!allowedTypes.has(question.type)) {
      report(file, questionIndex, `unsupported question type: ${String(question.type)}`);
      return;
    }
    countsByType[question.type] += 1;

    if (!Array.isArray(question.choices) || question.choices.length < 2) {
      report(file, questionIndex, 'choices must be an array with at least two entries');
    } else if (question.type === 'build-list') {
      validateBuildList(file, questionIndex, question);
    } else {
      validateIndexedAnswer(file, questionIndex, question);
    }

    if (isNonEmptyString(question.reference) && !/^https?:\/\//i.test(question.reference)) {
      validateLocalReference(file, questionIndex, question.reference);
    }
  });
}

if (errors.length > 0) {
  console.error(`Question validation failed with ${errors.length} error(s):`);
  for (const error of errors) console.error(`- ${error}`);
  process.exitCode = 1;
} else {
  console.log(
    `Validated ${questionCount} questions in ${questionFiles.length} banks ` +
    `(${countsByType.single} single, ${countsByType.multi} multi, ` +
    `${countsByType['build-list']} build-list).`,
  );
}
