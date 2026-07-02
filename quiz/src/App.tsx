import { useState, useMemo } from 'react';
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
  const domainTopics: Record<string, string[]> = {
    '01-containers': ['acr', 'app-service-containers', 'container-apps-keda', 'aks'],
    '02-data-services': ['cosmos-db-nosql', 'postgresql-pgvector', 'azure-managed-redis'],
    '03-connect-consume': ['service-bus', 'event-grid', 'azure-functions'],
    '04-secure-monitor': ['key-vault', 'app-configuration', 'opentelemetry', 'kql'],
  };

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
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<number[]>([]);
  const [showAnswer, setShowAnswer] = useState(false);
  const [score, setScore] = useState(0);

  // Generate questions based on mode
  const questions = useMemo(() => {
    if (mode === 'full-exam') {
      return generateFullExam();
    }
    // Per-topic mode
    const topicQuestions = questionsByTopic[selectedTopic] || [];
    return shuffleArray([...topicQuestions]);
  }, [mode, selectedTopic]);

  const currentQuestion = questions[currentQuestionIndex];

  // Available topics for dropdown
  const availableTopics = useMemo(() => {
    return Object.keys(questionsByTopic).sort();
  }, []);

  const handleAnswerSelect = (index: number) => {
    setSelectedAnswers(prev => {
      const newAnswers = [...prev];
      if (currentQuestion.type === 'single') {
        newAnswers[currentQuestionIndex] = index;
      } else if (currentQuestion.type === 'multi') {
        if (newAnswers[currentQuestionIndex] === undefined) {
          newAnswers[currentQuestionIndex] = index;
        } else {
          // Toggle selection for multi-select
          const current = newAnswers[currentQuestionIndex];
          if (current === index) {
            newAnswers[currentQuestionIndex] = -1; // Deselect
          } else {
            newAnswers[currentQuestionIndex] = index;
          }
        }
      } else if (currentQuestion.type === 'build-list') {
        // For build-list, track the order
        newAnswers[currentQuestionIndex] = index;
      }
      return newAnswers;
    });
  };

  const handleSubmit = () => {
    if (!currentQuestion) return;

    const userAnswer = selectedAnswers[currentQuestionIndex];
    const isCorrect = userAnswer !== undefined && 
      currentQuestion.answer.includes(userAnswer);

    if (isCorrect) {
      setScore(prev => prev + 1);
    }
    setShowAnswer(true);
  };

  const handleNext = () => {
    setShowAnswer(false);
    setSelectedAnswers(prev => {
      const newAnswers = [...prev];
      newAnswers[currentQuestionIndex] = -1;
      return newAnswers;
    });

    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    } else {
      // Quiz complete - reset
      setCurrentQuestionIndex(0);
      setScore(0);
      setSelectedAnswers([]);
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

  // Reset quiz when mode or topic changes
  useMemo(() => {
    setCurrentQuestionIndex(0);
    setScore(0);
    setSelectedAnswers([]);
    setShowAnswer(false);
  }, [mode, selectedTopic]);

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
              {currentQuestion.choices.map((choice, index) => {
                const isSelected = selectedAnswers[currentQuestionIndex] === index;
                const isCorrect = currentQuestion.answer.includes(index);
                const isWrong = showAnswer && isSelected && !isCorrect;
                const isRight = showAnswer && isSelected && isCorrect;

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
                      showAnswer && isCorrect ? 'correct-answer' : ''
                    }`}
                    onClick={() => handleAnswerSelect(index)}
                    disabled={showAnswer}
                  >
                    <span className="choice-letter">{String.fromCharCode(65 + index)}</span>
                    <span className="choice-text">{choice}</span>
                  </button>
                );
              })}
            </div>

            {!showAnswer ? (
              <button 
                className="submit-btn" 
                onClick={handleSubmit}
                disabled={selectedAnswers[currentQuestionIndex] === undefined}
              >
                Submit Answer
              </button>
            ) : (
              <div className="answer-feedback">
                <div className="explanation">{currentQuestion.explanation}</div>
                {currentQuestion.reference && (
                  <div className="reference">
                    <a href={currentQuestion.reference} target="_blank" rel="noopener noreferrer">
                      View in Topic Guide
                    </a>
                  </div>
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
