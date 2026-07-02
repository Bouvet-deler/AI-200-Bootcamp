import { useState, useMemo, useEffect } from 'react';
import { allQuestions, questionsByDomain, questionsByTopic } from './questions';
import { EXAM_WEIGHTS } from './lib/examWeights';
import type { Question } from './types';

// Helper to shuffle an array (Fisher-Yates)
function shuffleArray<T>(array: T[]): T[] {
  const result = [...array];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

// Generate a full exam with weighted sampling
function generateFullExam(): Question[] {

  const exam: Question[] = [];
  const questionsPerDomain: Record<string, number> = {};

  // Calculate how many questions per domain based on weights
  const totalQuestions = Math.min(allQuestions.length, 50); // Cap at 50 for a full exam
  Object.entries(EXAM_WEIGHTS).forEach(([domain, weight]) => {
    questionsPerDomain[domain] = Math.round(totalQuestions * weight);
  });

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
  const [mode, setMode] = useState<QuizMode>('per-topic');
  const [selectedTopic, setSelectedTopic] = useState<string>('04-secure-monitor/kql');
  const [questionCount, setQuestionCount] = useState<number>(10);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<(number | string)[][]>([]);
  const [showAnswer, setShowAnswer] = useState(false);
  const [score, setScore] = useState(0);
  const [answeredCorrectly, setAnsweredCorrectly] = useState<Set<number>>(new Set());
  const [darkMode, setDarkMode] = useState<boolean>(false);

  // Generate questions based on mode
  const questions = useMemo(() => {
    if (mode === 'full-exam') {
      return generateFullExam();
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

  // Helper to get choice ID - handles both string[] and BuildListChoice[]
  const getChoiceId = (index: number): string => {
    if (!currentQuestion) return index.toString();
    const choice = currentQuestion.choices[index];
    // If choice is an object with id property, use it
    if (typeof choice === 'object' && choice !== null && 'id' in choice) {
      return (choice as any).id;
    }
    // Otherwise use the index as the ID
    return index.toString();
  };

  // Helper to get choice text
  const getChoiceText = (indexOrId: number | string): string => {
    if (!currentQuestion) return '';
    if (typeof indexOrId === 'number') {
      const choice = currentQuestion.choices[indexOrId];
      if (typeof choice === 'object' && choice !== null && 'text' in choice) {
        return (choice as any).text;
      }
      return choice as string;
    }
    // If it's an ID string, find the choice with that ID
    for (const choice of currentQuestion.choices) {
      if (typeof choice === 'object' && choice !== null && 'id' in choice && (choice as any).id === indexOrId) {
        return (choice as any).text;
      }
    }
    return indexOrId;
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
  }, [mode, selectedTopic, questionCount]);

  // Update theme attribute when darkMode changes
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  // Load saved theme preference from localStorage
  useEffect(() => {
    const savedTheme = localStorage.getItem('quiz-theme');
    if (savedTheme === 'dark') {
      setDarkMode(true);
    }
  }, []);

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
        <div className="theme-toggle" onClick={() => setDarkMode(!darkMode)}>
          <input
            type="checkbox"
            checked={darkMode}
            onChange={() => setDarkMode(!darkMode)}
            onClick={(e) => e.stopPropagation()}
          />
          <span>{darkMode ? 'Dark' : 'Light'}</span>
        </div>
        <div className="mode-selector">
          <label>
            <input 
              type="radio" 
              checked={mode === 'per-topic'} 
              onChange={() => setMode('per-topic')}
            />
            Per Topic
          </label>
          <label>
            <input 
              type="radio" 
              checked={mode === 'full-exam'} 
              onChange={() => setMode('full-exam')}
            />
            Full Exam
          </label>
        </div>

        {mode === 'per-topic' && (
          <div className="topic-selector">
            <label htmlFor="topic-select">Topic:</label>
            <select 
              id="topic-select" 
              value={selectedTopic} 
              onChange={(e) => setSelectedTopic(e.target.value)}
            >
              {availableTopics.map(topic => (
                <option key={topic} value={topic}>{topic}</option>
              ))}
            </select>
            
            <label htmlFor="question-count">Questions:</label>
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
        )}

        <div className="progress">
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
                      {currentQuestion.choices.map((choice, index) => {
                        const userSelections = selectedAnswers[currentQuestionIndex] || [];
                        const choiceId = getChoiceId(index);
                        const isSelected = userSelections.includes(choiceId);
                        const choiceText = getChoiceText(index);

                        return (
                          <div
                            key={choiceId}
                            className={`build-list-choice-wrapper ${
                              isSelected ? 'selected' : ''
                            }`}
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
                          </div>
                        );
                      })}
                    </div>
                  </div>
                  
                  <div className="build-list-arrow">
                    <span>&#8594;</span>
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
                    <h4>Your Order (Drag to reorder)</h4>
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
                                <button 
                                  className="build-list-remove-btn"
                                  onClick={() => handleRemoveFromList(choiceId)}
                                >
                                  &times;
                                </button>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="build-list-empty-hint">Drag items here from the left to build your ordered list</p>
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
              <div className="answer-feedback">
                <div className="explanation">{currentQuestion.explanation}</div>
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
