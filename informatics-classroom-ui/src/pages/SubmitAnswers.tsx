import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircleIcon,
  XCircleIcon,
  AcademicCapIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Input } from '../components/common';
import api from '../services/api';
import { classNames } from '../utils/classNames';
import { useUIStore } from '../store/uiStore';

interface Quiz {
  class: string;
  module: string;
  title: string;
}

interface Question {
  question_num: number;
}

interface RecentAnswer {
  answer: string;
  correct: boolean;
}

interface QuizContent {
  title: string;
  questions: Question[];
  recent_answers: Record<string, RecentAnswer>;
}

interface SubmitAnswerData {
  class_val: string;
  module_val: string;
  question_num: number;
  answer_num: string;
}

export function SubmitAnswers() {
  const [selectedClass, setSelectedClass] = useState('');
  const [selectedModule, setSelectedModule] = useState('');
  const [quizLoaded, setQuizLoaded] = useState(false);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submittedQuestions, setSubmittedQuestions] = useState<Set<number>>(new Set());
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();

  // Fetch available quizzes
  const { data: quizzesData, isLoading: quizzesLoading } = useQuery({
    queryKey: ['session-quizzes'],
    queryFn: async () => {
      const response = await api.get<{ quizzes: Quiz[] }>('/api/get-session-quizzes');
      return response.data;
    },
  });

  // Fetch quiz content when class and module are selected
  const { data: quizContent, isLoading: quizLoading } = useQuery({
    queryKey: ['quiz-content', selectedClass, selectedModule],
    queryFn: async () => {
      const response = await api.get<QuizContent>(
        `/api/get-quiz-content?class_val=${selectedClass}&module_val=${selectedModule}`
      );
      return response.data;
    },
    enabled: quizLoaded && !!selectedClass && !!selectedModule,
  });

  // Submit answer mutation
  const submitAnswerMutation = useMutation({
    mutationFn: async (data: SubmitAnswerData) => {
      const formData = new URLSearchParams();
      formData.append('class_val', data.class_val);
      formData.append('module_val', data.module_val);
      formData.append('question_num', data.question_num.toString());
      formData.append('answer_num', data.answer_num);

      const response = await api.post<{ correct: boolean; message: string; success: boolean }>(
        '/submit-answer',
        formData.toString(),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );
      return response.data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['quiz-content', selectedClass, selectedModule] });
      setSubmittedQuestions((prev) => new Set(prev).add(variables.question_num));

      if (data.correct) {
        addToast('Correct answer!', 'success');
      } else {
        addToast('Incorrect answer. Try again!', 'error');
      }
    },
    onError: () => {
      addToast('Error submitting answer', 'error');
    },
  });

  // Group quizzes by class
  const quizzesByClass = quizzesData?.quizzes.reduce((acc, quiz) => {
    if (!acc[quiz.class]) {
      acc[quiz.class] = [];
    }
    acc[quiz.class].push(quiz);
    return acc;
  }, {} as Record<string, Quiz[]>) || {};

  // Get modules for selected class and sort numerically
  const modulesForClass = selectedClass
    ? (quizzesByClass[selectedClass] || []).sort((a, b) => {
        const numA = parseInt(a.module);
        const numB = parseInt(b.module);
        return numA - numB;
      })
    : [];

  // Initialize answers from recent answers
  useEffect(() => {
    if (quizContent?.recent_answers) {
      const initialAnswers: Record<number, string> = {};
      Object.entries(quizContent.recent_answers).forEach(([questionNum, answer]) => {
        initialAnswers[parseInt(questionNum)] = answer.answer;
      });
      setAnswers(initialAnswers);
    }
  }, [quizContent]);

  const handleLoadQuiz = () => {
    if (selectedClass && selectedModule) {
      setQuizLoaded(true);
      setSubmittedQuestions(new Set());
    }
  };

  const handleSubmitAnswer = (questionNum: number) => {
    const answer = answers[questionNum];
    if (!answer || !answer.trim()) {
      addToast('Please enter an answer', 'error');
      return;
    }

    submitAnswerMutation.mutate({
      class_val: selectedClass,
      module_val: selectedModule,
      question_num: questionNum,
      answer_num: answer.trim(),
    });
  };

  const handleAnswerChange = (questionNum: number, value: string) => {
    setAnswers((prev) => ({
      ...prev,
      [questionNum]: value,
    }));
  };

  const handleKeyPress = (questionNum: number, e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmitAnswer(questionNum);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Submit Answers</h1>
          <p className="mt-1 text-sm text-gray-500">
            Select a class and module to answer quiz questions
          </p>
        </div>
      </div>

      {/* Quiz Selection */}
      <Card>
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-gray-900 flex items-center">
            <AcademicCapIcon className="h-5 w-5 mr-2 text-primary-600" />
            Select Quiz
          </h2>

          {quizzesLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-600">Loading quizzes...</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* Class Selection */}
              <div>
                <label htmlFor="class-select" className="block text-sm font-medium text-gray-700 mb-2">
                  Class
                </label>
                <select
                  id="class-select"
                  value={selectedClass}
                  onChange={(e) => {
                    setSelectedClass(e.target.value);
                    setSelectedModule('');
                    setQuizLoaded(false);
                  }}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                >
                  <option value="">Select a class</option>
                  {Object.keys(quizzesByClass).map((className) => (
                    <option key={className} value={className}>
                      {className}
                    </option>
                  ))}
                </select>
              </div>

              {/* Module Selection */}
              <div>
                <label htmlFor="module-select" className="block text-sm font-medium text-gray-700 mb-2">
                  Module
                </label>
                <select
                  id="module-select"
                  value={selectedModule}
                  onChange={(e) => {
                    setSelectedModule(e.target.value);
                    setQuizLoaded(false);
                  }}
                  disabled={!selectedClass}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  <option value="">Select a module</option>
                  {modulesForClass.map((quiz) => (
                    <option key={quiz.module} value={quiz.module}>
                      Module {quiz.module}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Load Quiz Button */}
          {selectedClass && selectedModule && !quizLoaded && (
            <div className="flex justify-end">
              <Button
                variant="primary"
                onClick={handleLoadQuiz}
                icon={<ChevronRightIcon className="h-5 w-5" />}
              >
                Load Quiz
              </Button>
            </div>
          )}
        </div>
      </Card>

      {/* Quiz Questions */}
      {quizLoaded && (
        <Card>
          {quizLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading quiz...</p>
            </div>
          ) : quizContent ? (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">{quizContent.title || `Module ${selectedModule}`}</h2>
                <p className="mt-1 text-sm text-gray-500">
                  {selectedClass} - Module {selectedModule}
                </p>
              </div>

              <div className="space-y-4">
                {quizContent.questions.map((question) => {
                  const questionNum = question.question_num;
                  const recentAnswer = quizContent.recent_answers[questionNum.toString()];
                  const currentAnswer = answers[questionNum] || '';
                  const isCorrect = recentAnswer?.correct;
                  const isSubmitting = submitAnswerMutation.isPending && submittedQuestions.has(questionNum);

                  return (
                    <div
                      key={questionNum}
                      className={classNames(
                        'p-4 rounded-lg border-2 transition-colors',
                        isCorrect
                          ? 'border-green-300 bg-green-50'
                          : recentAnswer
                          ? 'border-red-300 bg-red-50'
                          : 'border-gray-200 bg-white'
                      )}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <label htmlFor={`question-${questionNum}`} className="text-sm font-medium text-gray-900">
                          Question {questionNum}
                        </label>
                        {recentAnswer && (
                          <div className="flex items-center">
                            {isCorrect ? (
                              <div className="flex items-center text-green-700">
                                <CheckCircleIcon className="h-5 w-5 mr-1" />
                                <span className="text-sm font-medium">Correct</span>
                              </div>
                            ) : (
                              <div className="flex items-center text-red-700">
                                <XCircleIcon className="h-5 w-5 mr-1" />
                                <span className="text-sm font-medium">Incorrect</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      <div className="flex gap-2">
                        <Input
                          id={`question-${questionNum}`}
                          value={currentAnswer}
                          onChange={(e) => handleAnswerChange(questionNum, e.target.value)}
                          onKeyPress={(e) => handleKeyPress(questionNum, e)}
                          placeholder="Enter your answer"
                          className="flex-1"
                          disabled={isSubmitting}
                        />
                        <Button
                          variant={isCorrect ? 'success' : 'primary'}
                          onClick={() => handleSubmitAnswer(questionNum)}
                          disabled={!currentAnswer.trim() || isSubmitting}
                          loading={isSubmitting}
                        >
                          Submit
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Summary */}
              {quizContent.questions.length > 0 && (
                <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">Progress</span>
                    <span className="text-sm text-gray-600">
                      {Object.values(quizContent.recent_answers).filter((a) => a.correct).length} /{' '}
                      {quizContent.questions.length} correct
                    </span>
                  </div>
                  <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-600 h-2 rounded-full transition-all"
                      style={{
                        width: `${
                          (Object.values(quizContent.recent_answers).filter((a) => a.correct).length /
                            quizContent.questions.length) *
                          100
                        }%`,
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500">Quiz not found</p>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
