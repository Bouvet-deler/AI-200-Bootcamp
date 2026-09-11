import { useState, useMemo, useEffect } from 'react';
import { allQuestions, questionsByDomain, questionsByTopic } from './questions';
import { EXAM_WEIGHTS } from './lib/examWeights';
import type { Question } from './types';

// Topic-guide references in question banks are repository-relative paths. Convert those paths
// into links that work from the separately hosted Vite app, while leaving full web URLs alone.
const REPOSITORY_GUIDE_ROOT = 'https://github.com/Bouvet-deler/AI-200-Bootcamp/blob/master/';

function getReferenceUrl(reference: string): string {
  if (/^https?:\/\//.test(reference)) {
    return reference;
  }

  // The JSON files live under quiz/src/questions/, so their existing guide links begin with
  // one or more "../" segments. Strip those segments to get the path from the repository root.
  const repositoryPath = reference.replace(/^(?:\.\.\/)+/, '');
  return `${REPOSITORY_GUIDE_ROOT}${repositoryPath}`;
}

// Helper to shuffle an array (Fisher-Yates)
function shuffleArray<T>(array: T[]): T[] {
  const result = [...array];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

// Turn fractional domain weights into whole question counts without losing or inventing a
// question. The largest-remainder method floors every quota, then awards leftover slots to the
// domains with the largest fractional remainder (using the domain name as a stable tie-breaker).
function allocateQuestionsPerDomain(totalQuestions: number): Record<string, number> {
  const quotas = Object.entries(EXAM_WEIGHTS).map(([domain, weight]) => {
    const exactCount = totalQuestions * weight;
    const wholeCount = Math.floor(exactCount);
    return { domain, wholeCount, remainder: exactCount - wholeCount };
  });

  const allocation = Object.fromEntries(
    quotas.map(({ domain, wholeCount }) => [domain, wholeCount]),
  ) as Record<string, number>;
  const allocatedCount = quotas.reduce((sum, quota) => sum + quota.wholeCount, 0);
  const rankedRemainders = [...quotas].sort(
    (left, right) => right.remainder - left.remainder || left.domain.localeCompare(right.domain),
  );

  for (let slot = 0; slot < totalQuestions - allocatedCount; slot += 1) {
    allocation[rankedRemainders[slot].domain] += 1;
  }

  return allocation;
}

// Generate a full exam with weighted sampling.
// `requestedCount` is how many questions the user asked for (100 = "All").
function generateFullExam(requestedCount: number): Question[] {

  const exam: Question[] = [];
  // Calculate how many questions per domain based on the normalized representative weights.
  // "All" (100) means every question we have; otherwise honour the request,
  // never exceeding the number of questions that actually exist.
  const totalQuestions = requestedCount === 100
    ? allQuestions.length
    : Math.min(allQuestions.length, requestedCount);
  const questionsPerDomain = allocateQuestionsPerDomain(totalQuestions);

  // Sample questions from each domain
  for (const [domain, count] of Object.entries(questionsPerDomain)) {
    const domainQuestions = questionsByDomain[domain] || [];
    if (domainQuestions.length === 0) continue;

    const shuffled = shuffleArray(domainQuestions);
    exam.push(...shuffled.slice(0, Math.min(count, shuffled.length)));
  }

  // If we didn't get enough questions, fill from remaining
  if (exam.length < totalQuestions) {
    const remaining = allQuestions.filter(q => !exam.includes(q));
    const shuffledRemaining = shuffleArray(remaining);
    exam.push(...shuffledRemaining.slice(0, totalQuestions - exam.length));
  }

  return shuffleArray(exam);
}

// Quiz mode type
type QuizMode = 'per-topic' | 'full-exam';

function App() {
  const [mode, setMode] = useState<QuizMode>('full-exam');
  // Default the topic to the first entry in the sorted topic list (currently
  // "01-containers/...") rather than a hard-coded topic, so switching to
  // "Per Topic" starts at the top of the list. The arrow function passed to
  // useState is a "lazy initializer" — React runs it once on first render.
  const [selectedTopic, setSelectedTopic] = useState<string>(
    () => Object.keys(questionsByTopic).sort()[0] ?? ''
  );
  const [questionCount, setQuestionCount] = useState<number>(10);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<(number | string)[][]>([]);
  const [showAnswer, setShowAnswer] = useState(false);
  const [score, setScore] = useState(0);
  const [answeredCorrectly, setAnsweredCorrectly] = useState<Set<number>>(new Set());
  const [answerResults, setAnswerResults] = useState<Record<number, boolean>>({});
  // Read the persisted theme during the first render. This agrees with index.html's early theme
  // script and avoids briefly switching back to light mode while the component mounts.
  const [darkMode, setDarkMode] = useState<boolean>(
    () => localStorage.getItem('quiz-theme') === 'dark',
  );

  // Generate questions based on mode
  const questions = useMemo(() => {
    if (mode === 'full-exam') {
      return generateFullExam(questionCount);
    }
    // Per-topic mode - limit to selected count
    const topicQuestions = questionsByTopic[selectedTopic] || [];
    const shuffled = shuffleArray([...topicQuestions]);
    // If "All" is selected (100), use all questions
    const count = questionCount === 100 ? shuffled.length : Math.min(questionCount, shuffled.length);
    return shuffled.slice(0, count);
  }, [mode, selectedTopic, questionCount]);

  const currentQuestion = questions[currentQuestionIndex];

  // Available topics for dropdown
  const availableTopics = useMemo(() => {
    return Object.keys(questionsByTopic).sort();
  }, []);

  const handleAnswerSelect = (index: number) => {
    setSelectedAnswers(prev => {
      const newAnswers = [...prev];
      if (currentQuestion.type === 'single') {
        newAnswers[currentQuestionIndex] = [index] as number[];
      } else if (currentQuestion.type === 'multi') {
        // Toggle selection for multi-select
        const currentSelections = (newAnswers[currentQuestionIndex] || []) as number[];
        const indexInSelection = currentSelections.indexOf(index);
        if (indexInSelection === -1) {
          // Add to selection
          newAnswers[currentQuestionIndex] = [...currentSelections, index] as number[];
        } else {
          // Remove from selection
          newAnswers[currentQuestionIndex] = currentSelections.filter(i => i !== index) as number[];
        }
      } else if (currentQuestion.type === 'build-list') {
        // For build-list with drag and drop, we store choice IDs (strings)
        const currentSelections = (newAnswers[currentQuestionIndex] || []) as string[];
        // Get the choice ID - either from BuildListChoice object or use index as ID
        const choiceId = getChoiceId(index);
        if (!currentSelections.includes(choiceId)) {
          newAnswers[currentQuestionIndex] = [...currentSelections, choiceId] as string[];
        }
      }
      return newAnswers;
    });
  };

  const handleRemoveFromList = (choiceId: string) => {
    setSelectedAnswers(prev => {
      const newAnswers = [...prev];
      if (currentQuestion.type === 'build-list') {
        const currentSelections = (newAnswers[currentQuestionIndex] || []) as string[];
        newAnswers[currentQuestionIndex] = currentSelections.filter(id => id !== choiceId) as string[];
      }
      return newAnswers;
    });
  };

  const handleMoveInList = (fromIndex: number, toIndex: number) => {
    setSelectedAnswers(prev => {
      const newAnswers = [...prev];
      if (currentQuestion.type === 'build-list') {
        const currentSelections = [...(newAnswers[currentQuestionIndex] || [])] as string[];
        const [removed] = currentSelections.splice(fromIndex, 1);
        currentSelections.splice(toIndex, 0, removed);
        newAnswers[currentQuestionIndex] = currentSelections as string[];
      }
      return newAnswers;
    });
  };

  // A build-list choice always has a stable string ID; that ID is stored instead of its current
  // array index so reordering the visible list cannot change what an answer means.
  const getChoiceId = (index: number): string => {
    if (!currentQuestion) return index.toString();
    if (currentQuestion.type === 'build-list') {
      return currentQuestion.choices[index]?.id ?? index.toString();
    }
    return index.toString();
  };

  // Resolve either an available-choice index or a previously stored choice ID to display text.
  const getChoiceText = (indexOrId: number | string): string => {
    if (!currentQuestion) return '';
    if (currentQuestion.type === 'build-list') {
      const choice = typeof indexOrId === 'number'
        ? currentQuestion.choices[indexOrId]
        : currentQuestion.choices.find(candidate => candidate.id === indexOrId);
      return choice?.text ?? String(indexOrId);
    }
    return typeof indexOrId === 'number' ? currentQuestion.choices[indexOrId] ?? '' : indexOrId;
  };

  const handleSubmit = () => {
    if (!currentQuestion) return;

    const userAnswers = selectedAnswers[currentQuestionIndex] || [];

    // For single, check if the single answer matches
    // For multi, check if all selected answers are in the correct answer and vice versa
    // For build-list, check if the ordered array matches exactly
    let isCorrect = false;
    if (currentQuestion.type === 'single') {
      const userAnswersNum = userAnswers as number[];
      isCorrect = userAnswersNum.length > 0 &&
        currentQuestion.answer.length > 0 &&
        userAnswersNum[0] === currentQuestion.answer[0];
    } else if (currentQuestion.type === 'multi') {
      // Both arrays must have same length and same elements (order doesn't matter)
      const userAnswersNum = userAnswers as number[];
      const answerNum = currentQuestion.answer as number[];
      isCorrect = userAnswersNum.length === answerNum.length &&
        userAnswersNum.every(ans => answerNum.includes(ans));
    } else if (currentQuestion.type === 'build-list') {
      // For build-list with IDs, the order must match exactly
      const userAnswersStr = userAnswers as string[];
      const answerStr = currentQuestion.answer as string[];
      isCorrect = userAnswersStr.length === answerStr.length &&
        userAnswersStr.every((ans, i) => ans === answerStr[i]);
    }

    if (isCorrect && !answeredCorrectly.has(currentQuestionIndex)) {
      setScore(prev => prev + 1);
      setAnsweredCorrectly(prev => {
        const newSet = new Set(prev);
        newSet.add(currentQuestionIndex);
        return newSet;
      });
    }
    setAnswerResults(prev => ({ ...prev, [currentQuestionIndex]: isCorrect }));
    setShowAnswer(true);
  };

  const handleNext = () => {
    setShowAnswer(false);

    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    } else {
      // Quiz complete - reset
      setCurrentQuestionIndex(0);
      setScore(0);
      setSelectedAnswers([]);
      setAnsweredCorrectly(new Set());
      setAnswerResults({});
    }
  };

  const handlePrev = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
      setShowAnswer(false);
    }
  };

  const progress = questions.length > 0
    ? `${currentQuestionIndex + 1} / ${questions.length}`
    : '0 / 0';

  // Reset quiz when mode, topic, or question count changes
  useEffect(() => {
    setCurrentQuestionIndex(0);
    setScore(0);
    setSelectedAnswers([]);
    setShowAnswer(false);
    setAnsweredCorrectly(new Set());
    setAnswerResults({});
  }, [mode, selectedTopic, questionCount]);

  // Update theme attribute when darkMode changes
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  // Save theme preference to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('quiz-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  if (questions.length === 0) {
    return (
      <div className="container">
        <h1>AI-200 Quiz</h1>
        <p>No questions found. Add question banks to quiz/src/questions/&lt;domain&gt;/&lt;topic&gt;.json</p>
      </div>
    );
  }

  return (
    <div className="container">
      <header className="header">
        <h1>AI-200 Quiz</h1>
        <label className="theme-toggle">
          <input
            type="checkbox"
            checked={darkMode}
            onChange={() => setDarkMode(!darkMode)}
          />
          <span>{darkMode ? 'Dark' : 'Light'}</span>
        </label>
        <div className="mode-selector">
          <label
            className={`mode-option ${mode === 'per-topic' ? 'selected' : ''}`}
          >
            <input
              type="radio"
              name="quiz-mode"
              checked={mode === 'per-topic'}
              onChange={() => setMode('per-topic')}
            />
            <div className="custom-radio"></div>
            <span>Per Topic</span>
          </label>
          <label
            className={`mode-option ${mode === 'full-exam' ? 'selected' : ''}`}
          >
            <input
              type="radio"
              name="quiz-mode"
              checked={mode === 'full-exam'}
              onChange={() => setMode('full-exam')}
            />
            <div className="custom-radio"></div>
            <span>Full Exam</span>
          </label>
        </div>

        <div className="topic-selector">
          {mode === 'per-topic' && (
            <>
              <span className="topic-wrapper">
              <label htmlFor="topic-select">Topic:</label>
              <div className="select-wrapper">
                <select
                  id="topic-select"
                  value={selectedTopic}
                  onChange={(e) => setSelectedTopic(e.target.value)}
                >
                  {availableTopics.map(topic => (
                    <option key={topic} value={topic}>{topic}</option>
                  ))}
                </select>
              </div>
              </span>
            </>
          )}

            <span className="topic-wrapper">
          <label htmlFor="question-count">Questions:</label>
          <div className="select-wrapper">
            <select
              id="question-count"
              value={questionCount}
              onChange={(e) => setQuestionCount(Number(e.target.value))}
            >
              <option value="5">5</option>
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="30">30</option>
              <option value="50">50</option>
              <option value="100">All</option>
            </select>
          </div>
            </span>
        </div>

        <div className="progress" role="status" aria-live="polite">
          Question {progress} | Score: {score}
        </div>
      </header>

      <main className="main">
        {currentQuestion && (
          <div className="question-card">
            <div className="question-domain">
              {currentQuestion.domain} &gt; {currentQuestion.topic}
            </div>
            <h2 className="question-text">{currentQuestion.question}</h2>

            <div className="choices">
              {currentQuestion.type === 'build-list' ? (
                <div className="build-list-container">
                  <div className="build-list-available">
                    <h4>Available Choices</h4>
                    <div className="build-list-available-choices">
                      {currentQuestion.choices.map((_choice, index) => {
                        const userSelections = selectedAnswers[currentQuestionIndex] || [];
                        const choiceId = getChoiceId(index);
                        const isSelected = userSelections.includes(choiceId);
                        const choiceText = getChoiceText(index);

                        return (
                          <button
                            type="button"
                            key={choiceId}
                            className={`build-list-choice-wrapper ${
                              isSelected ? 'selected' : ''
                            }`}
                            aria-label={`Add ${choiceText} to your ordered list`}
                            aria-pressed={isSelected}
                            disabled={showAnswer || isSelected}
                            onClick={() => handleAnswerSelect(index)}
                            draggable={!showAnswer && !isSelected}
                            onDragStart={(e) => {
                              if (showAnswer) return;
                              e.dataTransfer.setData('text/plain', choiceId);
                              e.dataTransfer.effectAllowed = 'move';
                            }}
                          >
                            <div
                              className={`build-list-choice-item ${
                                isSelected ? 'selected' : ''
                              }`}
                            >
                              <span className="build-list-choice-indicator">{String.fromCharCode(65 + index)}</span>
                              <span className="build-list-choice-text">{choiceText}</span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="build-list-arrow">
                    <span>&#8595;</span>
                  </div>

                  <div
                    className="build-list-ordered"
                    onDragOver={(e) => {
                      if (showAnswer) return;
                      e.preventDefault();
                      e.dataTransfer.dropEffect = 'move';
                    }}
                    onDrop={(e) => {
                      if (showAnswer) return;
                      e.preventDefault();
                      const choiceId = e.dataTransfer.getData('text/plain');
                      const userSelections = (selectedAnswers[currentQuestionIndex] || []) as string[];
                      if (!userSelections.includes(choiceId)) {
                        setSelectedAnswers(prev => {
                          const newAnswers = [...prev];
                          newAnswers[currentQuestionIndex] = [...userSelections, choiceId] as string[];
                          return newAnswers;
                        });
                      }
                    }}
                  >
                    <h4>Your Order (drag or use the arrow buttons)</h4>
                    {selectedAnswers[currentQuestionIndex] && selectedAnswers[currentQuestionIndex].length > 0 ? (
                      <ul className="build-list-ordered-list">
                        {(selectedAnswers[currentQuestionIndex] as string[]).map((choiceId, position) => {
                          const choiceText = getChoiceText(choiceId);
                          const isCorrect = showAnswer &&
                            (currentQuestion.answer as string[])[position] === choiceId;
                          const isWrong = showAnswer &&
                            (currentQuestion.answer as string[])[position] !== choiceId;

                          return (
                            <li
                              key={choiceId}
                              draggable={!showAnswer}
                              onDragStart={(e) => {
                                if (showAnswer) return;
                                e.dataTransfer.setData('text/plain', choiceId);
                                e.dataTransfer.effectAllowed = 'move';
                              }}
                              onDragOver={(e) => {
                                if (showAnswer) return;
                                e.preventDefault();
                                e.dataTransfer.dropEffect = 'move';
                              }}
                              onDrop={(e) => {
                                if (showAnswer) return;
                                e.preventDefault();
                                const draggedId = e.dataTransfer.getData('text/plain');
                                const userSelections = (selectedAnswers[currentQuestionIndex] || []) as string[];
                                const draggedIndex = userSelections.indexOf(draggedId);
                                if (draggedIndex !== -1 && draggedIndex !== position) {
                                  handleMoveInList(draggedIndex, position);
                                }
                              }}
                              className={`build-list-ordered-item ${
                                isCorrect ? 'correct' : ''
                              } ${
                                isWrong ? 'wrong' : ''
                              }`}
                            >
                              <span className="build-list-drag-handle">&#9776;</span>
                              <span className="build-list-position">{position + 1}.</span>
                              <span className="build-list-item-text">{choiceText}</span>
                              {!showAnswer && (
                                <span className="build-list-actions">
                                  <button
                                    type="button"
                                    className="build-list-move-btn"
                                    aria-label={`Move ${choiceText} up`}
                                    disabled={position === 0}
                                    onClick={() => handleMoveInList(position, position - 1)}
                                  >
                                    &uarr;
                                  </button>
                                  <button
                                    type="button"
                                    className="build-list-move-btn"
                                    aria-label={`Move ${choiceText} down`}
                                    disabled={position === selectedAnswers[currentQuestionIndex].length - 1}
                                    onClick={() => handleMoveInList(position, position + 1)}
                                  >
                                    &darr;
                                  </button>
                                  <button
                                    type="button"
                                    className="build-list-remove-btn"
                                    aria-label={`Remove ${choiceText} from your ordered list`}
                                    onClick={() => handleRemoveFromList(choiceId)}
                                  >
                                    &times;
                                  </button>
                                </span>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="build-list-empty-hint">Select or drag choices here to build your ordered list</p>
                    )}
                    {showAnswer && currentQuestion.answer && (
                      <div className="build-list-correct-order">
                        <h5>Correct Order:</h5>
                        <ol className="build-list-correct-list">
                          {(currentQuestion.answer as string[]).map((choiceId) => (
                            <li key={choiceId}>{getChoiceText(choiceId)}</li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                currentQuestion.choices.map((choice, index) => {
                  const userSelections = (selectedAnswers[currentQuestionIndex] || []) as number[];
                  const isSelected = userSelections.includes(index);
                  const isCorrect = (currentQuestion.answer as number[]).includes(index);
                  const isWrong = showAnswer && isSelected && !isCorrect;
                  const isRight = showAnswer && isSelected && isCorrect;
                  const isMissed = showAnswer && !isSelected && isCorrect;
                  const isMultiSelect = currentQuestion.type === 'multi';

                  // For multi-select, use empty indicator (CSS handles it); for single, use letters
                  const indicator = isMultiSelect
                    ? ''
                    : String.fromCharCode(65 + index);

                  return (
                    <button
                      key={index}
                      className={`choice ${
                        isSelected ? 'selected' : ''
                      } ${
                        isWrong ? 'wrong' : ''
                      } ${
                        isRight ? 'correct' : ''
                      } ${
                        isMissed ? (isMultiSelect ? 'wrong' : 'correct-answer') : ''
                      } ${isMultiSelect ? 'multi-select' : ''}`}
                      onClick={() => handleAnswerSelect(index)}
                      disabled={showAnswer}
                    >
                      <span className="choice-indicator">{indicator}</span>
                      <span className="choice-text">{choice}</span>
                    </button>
                  );
                })
              )}
            </div>

            {!showAnswer ? (
              <button
                className="submit-btn"
                onClick={handleSubmit}
                disabled={!selectedAnswers[currentQuestionIndex] ||
                  (currentQuestion.type === 'build-list'
                    ? selectedAnswers[currentQuestionIndex].length !== currentQuestion.answer.length
                    : selectedAnswers[currentQuestionIndex].length === 0)}
              >
                {currentQuestion.type === 'build-list'
                  ? `Submit Order (${selectedAnswers[currentQuestionIndex] ? selectedAnswers[currentQuestionIndex].length : 0}/${currentQuestion.answer.length})`
                  : 'Submit Answer'}
              </button>
            ) : (
              <div className="answer-feedback" aria-live="polite">
                <div
                  className={`answer-result ${
                    answerResults[currentQuestionIndex] ? 'correct' : 'wrong'
                  }`}
                >
                  {answerResults[currentQuestionIndex] ? 'Correct' : 'Not quite'}
                </div>
                <div className="explanation">{currentQuestion.explanation}</div>
                {currentQuestion.reference && (
                  <a
                    className="reference-link"
                    href={getReferenceUrl(currentQuestion.reference)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Read the topic guide
                  </a>
                )}
                <div className="navigation">
                  <button className="nav-btn" onClick={handlePrev} disabled={currentQuestionIndex === 0}>
                    Previous
                  </button>
                  <button className="nav-btn primary" onClick={handleNext}>
                    {currentQuestionIndex < questions.length - 1 ? 'Next' : 'Restart Quiz'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
