import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { apiClient } from '../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Alert, AlertDescription } from '../components/ui/alert';
import { CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react';

interface Question {
  question_num: number;
  question_text: string;
  answers: string[];
  open: boolean;
  user_answer: string | null;
  is_correct: boolean | null;
}

interface Quiz {
  id: string;
  course: string;
  module: number;
  module_name: string;
  questions: Question[];
}

interface QuizDetailsResponse {
  success: boolean;
  quiz: Quiz;
  error?: string;
}

interface SubmitAnswerResponse {
  success: boolean;
  correct: boolean;
  feedback: string;
  is_open: boolean;
  error?: string;
}

export default function QuizTaking() {
  const [searchParams] = useSearchParams();
  const course = searchParams.get('course');
  const module = searchParams.get('module');
  const queryClient = useQueryClient();

  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [feedback, setFeedback] = useState<Record<number, { correct: boolean; message: string }>>({});

  // Fetch quiz details
  const { data: quizData, isLoading, error } = useQuery({
    queryKey: ['quiz', 'details', course, module],
    queryFn: async () => {
      const response = await apiClient.get<QuizDetailsResponse>(
        `/api/quiz/details?course=${course}&module=${module}`
      );
      if (!response.success) {
        throw new Error(response.error || 'Failed to load quiz');
      }

      const data = ('data' in response && response.data) ? response.data : response as QuizDetailsResponse;

      // Initialize answers with previous user answers
      const initialAnswers: Record<number, string> = {};
      data.quiz.questions.forEach((q: Question) => {
        if (q.user_answer) {
          initialAnswers[q.question_num] = q.user_answer;
        }
      });
      setAnswers(initialAnswers);

      // Initialize feedback for previously answered questions
      const initialFeedback: Record<number, { correct: boolean; message: string }> = {};
      data.quiz.questions.forEach((q: Question) => {
        if (q.is_correct !== null) {
          initialFeedback[q.question_num] = {
            correct: q.is_correct,
            message: q.is_correct ? 'Correct!' : 'Incorrect.',
          };
        }
      });
      setFeedback(initialFeedback);

      return data;
    },
    enabled: !!course && !!module,
  });

  // Submit answer mutation
  const submitMutation = useMutation({
    mutationFn: async ({ question_num, answer }: { question_num: number; answer: string }) => {
      const response = await apiClient.post<SubmitAnswerResponse>('/api/quiz/submit-answer', {
        course,
        module,
        question_num,
        answer,
      });
      if (!response.success) {
        throw new Error(response.error || 'Failed to submit answer');
      }
      return { question_num, ...response };
    },
    onSuccess: (data) => {
      // Update feedback - unwrap if needed
      const result = ('data' in data && data.data) ? data.data : data;
      const correct = 'correct' in result ? result.correct : false;
      const feedbackMsg = 'feedback' in result ? result.feedback : (correct ? 'Correct!' : 'Incorrect.');

      setFeedback((prev) => ({
        ...prev,
        [data.question_num]: {
          correct,
          message: feedbackMsg,
        },
      }));

      // Invalidate quiz details to refresh
      queryClient.invalidateQueries({ queryKey: ['quiz', 'details', course, module] });
      queryClient.invalidateQueries({ queryKey: ['student', 'progress', course] });
      queryClient.invalidateQueries({ queryKey: ['student', 'dashboard'] });
    },
  });

  const handleAnswerChange = (questionNum: number, value: string) => {
    setAnswers((prev) => ({
      ...prev,
      [questionNum]: value,
    }));
  };

  const handleSubmit = (questionNum: number) => {
    const answer = answers[questionNum];
    if (!answer || !answer.trim()) {
      setFeedback((prev) => ({
        ...prev,
        [questionNum]: {
          correct: false,
          message: 'Answer is required.',
        },
      }));
      return;
    }

    submitMutation.mutate({ question_num: questionNum, answer: answer.trim() });
  };

  if (!course || !module) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Invalid quiz parameters. Please select a quiz from the Student Center.</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2 text-lg">Loading quiz...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error instanceof Error ? error.message : 'Failed to load quiz'}</AlertDescription>
        </Alert>
      </div>
    );
  }

  const quiz = quizData as QuizDetailsResponse | undefined;
  const quizDetails = quiz?.quiz;

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">{quizDetails?.module_name || `Module ${module}`}</h1>
        <p className="text-lg text-muted-foreground mt-2">
          {quizDetails?.course} - {quizDetails?.questions.length} Questions
        </p>
      </div>

      {/* Questions */}
      <div className="space-y-4">
        {quizDetails?.questions.map((question: Question) => {
          const questionFeedback = feedback[question.question_num];
          const isSubmitting = submitMutation.isPending && submitMutation.variables?.question_num === question.question_num;

          return (
            <Card key={question.question_num} className={questionFeedback?.correct ? 'border-green-500' : ''}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Question {question.question_num}</span>
                  {questionFeedback && (
                    <span className="flex items-center gap-2">
                      {questionFeedback.correct ? (
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600" />
                      )}
                    </span>
                  )}
                </CardTitle>
                {question.question_text && <CardDescription>{question.question_text}</CardDescription>}
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Answer Input */}
                <div className="flex gap-2">
                  <Input
                    type="text"
                    value={answers[question.question_num] || ''}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleAnswerChange(question.question_num, e.target.value)}
                    placeholder="Enter your answer"
                    className={
                      questionFeedback
                        ? questionFeedback.correct
                          ? 'border-green-500'
                          : 'border-red-500'
                        : ''
                    }
                    onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                      if (e.key === 'Enter' && !isSubmitting) {
                        handleSubmit(question.question_num);
                      }
                    }}
                  />
                  <Button
                    onClick={() => handleSubmit(question.question_num)}
                    disabled={isSubmitting}
                    className="min-w-[100px]"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Submitting
                      </>
                    ) : (
                      'Submit'
                    )}
                  </Button>
                </div>

                {/* Feedback */}
                {questionFeedback && (
                  <Alert variant={questionFeedback.correct ? 'default' : 'destructive'}>
                    <AlertDescription
                      className={questionFeedback.correct ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}
                    >
                      {questionFeedback.message}
                    </AlertDescription>
                  </Alert>
                )}

                {/* Answer Choices (if provided) */}
                {question.answers && question.answers.length > 0 && (
                  <div className="mt-2">
                    <p className="text-sm font-medium text-muted-foreground mb-2">Answer Options:</p>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {question.answers.map((ans: string, idx: number) => (
                        <li key={idx}>{ans}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Open Question Indicator */}
                {question.open && (
                  <p className="text-sm text-muted-foreground italic">This is an open-ended question - all answers are accepted.</p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>Instructions</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc list-inside space-y-2 text-sm text-muted-foreground">
            <li>Enter your answer in the text field and click Submit or press Enter</li>
            <li>You can resubmit answers to any question at any time</li>
            <li>Your progress is automatically saved</li>
            <li>Green check mark indicates a correct answer</li>
            <li>Red X indicates an incorrect answer - try again!</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
