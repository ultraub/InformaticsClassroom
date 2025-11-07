import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient } from '../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import { Plus, Trash2, Save, AlertCircle, Loader2 } from 'lucide-react';

interface Question {
  question_num: number;
  question_text: string;
  correct_answer: string;
  open: boolean;
  answers: string[];
}

interface Quiz {
  id: string;
  class: string;
  module: number;
  title: string;
  description: string;
  questions: Question[];
  owner: string;
}

interface ClassesResponse {
  success: boolean;
  classes: string[];
  error?: string;
}

interface QuizResponse {
  success: boolean;
  quiz?: Quiz;
  quiz_id?: string;
  error?: string;
}

export default function QuizBuilder() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const editMode = !!searchParams.get('id');
  const quizId = searchParams.get('id');

  // Form state
  const [selectedClass, setSelectedClass] = useState<string>('');
  const [module, setModule] = useState<string>('');
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [questions, setQuestions] = useState<Question[]>([
    { question_num: 1, question_text: '', correct_answer: '', open: false, answers: [] },
  ]);

  // Fetch classes for instructor
  const { data: classesData, isLoading: classesLoading } = useQuery<ClassesResponse>({
    queryKey: ['instructor', 'classes'],
    queryFn: async (): Promise<ClassesResponse> => {
      const response = await apiClient.get<ClassesResponse>('/api/instructor/classes');
      if (!response.success) {
        throw new Error(response.error || 'Failed to load classes');
      }
      // Unwrap ApiResponse if needed
      if ('data' in response && response.data) {
        return response.data;
      }
      return response as ClassesResponse;
    },
  });

  // Fetch quiz for editing
  const { data: quizData, isLoading: quizLoading } = useQuery<QuizResponse>({
    queryKey: ['quiz', 'edit', quizId],
    queryFn: async () => {
      const response = await apiClient.get<QuizResponse>(`/api/quizzes/${quizId}/edit`);
      if (!response.success) {
        throw new Error(response.error || 'Failed to load quiz');
      }
      return response;
    },
    enabled: editMode && !!quizId,
  });

  // Load quiz data when editing
  useEffect(() => {
    if (quizData?.quiz) {
      const quiz = quizData.quiz;
      setSelectedClass(quiz.class);
      setModule(quiz.module.toString());
      setTitle(quiz.title);
      setDescription(quiz.description);
      setQuestions(quiz.questions);
    }
  }, [quizData]);

  // Create quiz mutation
  const createMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<QuizResponse>('/api/quizzes/create', {
        class: selectedClass,
        module: parseInt(module),
        title,
        description,
        questions,
      });
      if (!response.success) {
        throw new Error(response.error || 'Failed to create quiz');
      }
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instructor', 'quizzes'] });
      if (selectedClass) {
        navigate(`/classes/${selectedClass}/manage?tab=assignments`);
      } else {
        navigate('/classes');
      }
    },
  });

  // Update quiz mutation
  const updateMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.put<QuizResponse>(`/api/quizzes/${quizId}/update`, {
        title,
        description,
        questions,
      });
      if (!response.success) {
        throw new Error(response.error || 'Failed to update quiz');
      }
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quiz', 'edit', quizId] });
      queryClient.invalidateQueries({ queryKey: ['instructor', 'quizzes'] });
      if (selectedClass) {
        navigate(`/classes/${selectedClass}/manage?tab=assignments`);
      } else {
        navigate('/classes');
      }
    },
  });

  const handleAddQuestion = () => {
    const newQuestionNum = questions.length + 1;
    setQuestions([
      ...questions,
      { question_num: newQuestionNum, question_text: '', correct_answer: '', open: false, answers: [] },
    ]);
  };

  const handleRemoveQuestion = (index: number) => {
    const updatedQuestions = questions.filter((_, i) => i !== index);
    // Re-number questions
    updatedQuestions.forEach((q, i) => {
      q.question_num = i + 1;
    });
    setQuestions(updatedQuestions);
  };

  const handleQuestionChange = (index: number, field: keyof Question, value: any) => {
    const updatedQuestions = [...questions];
    updatedQuestions[index] = { ...updatedQuestions[index], [field]: value };
    setQuestions(updatedQuestions);
  };

  const handleAnswerOptionsChange = (index: number, value: string) => {
    const answers = value.split('\n').filter((a) => a.trim() !== '');
    handleQuestionChange(index, 'answers', answers);
  };

  const handleSubmit = () => {
    // Validation
    if (!selectedClass || !module || !title) {
      return;
    }

    if (questions.length === 0) {
      return;
    }

    for (const q of questions) {
      if (!q.question_text || (!q.open && !q.correct_answer)) {
        return;
      }
    }

    if (editMode) {
      updateMutation.mutate();
    } else {
      createMutation.mutate();
    }
  };

  const isSubmitting = createMutation.isPending || updateMutation.isPending;
  const submitError = createMutation.error || updateMutation.error;

  if (classesLoading || quizLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2 text-lg">Loading...</span>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">{editMode ? 'Edit Quiz' : 'Create New Quiz'}</h1>
        <p className="text-lg text-muted-foreground mt-2">
          {editMode ? 'Update quiz details and questions' : 'Build a quiz for your students'}
        </p>
      </div>

      {/* Error Display */}
      {submitError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {submitError instanceof Error ? submitError.message : 'Failed to save quiz'}
          </AlertDescription>
        </Alert>
      )}

      {/* Quiz Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Quiz Information</CardTitle>
          <CardDescription>Basic details about the quiz</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="class">Class *</Label>
              <Select
                value={selectedClass || undefined}
                onValueChange={setSelectedClass}
                disabled={editMode}
              >
                <SelectTrigger id="class">
                  <SelectValue placeholder="Select a class" />
                </SelectTrigger>
                <SelectContent>
                  {classesData?.classes.filter(cls => typeof cls === 'string' && cls.trim() !== '').map((cls: string) => (
                    <SelectItem key={cls} value={cls}>
                      {cls}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="module">Module Number *</Label>
              <Input
                id="module"
                type="number"
                min="1"
                value={module}
                onChange={(e) => setModule(e.target.value)}
                placeholder="e.g., 1"
                disabled={editMode}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="title">Quiz Title *</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Introduction to Informatics"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description or instructions for students"
              rows={3}
            />
          </div>
        </CardContent>
      </Card>

      {/* Questions */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Questions</CardTitle>
              <CardDescription>Add and configure quiz questions</CardDescription>
            </div>
            <Button onClick={handleAddQuestion} variant="outline">
              <Plus className="w-4 h-4 mr-2" />
              Add Question
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {questions.map((question, index) => (
            <Card key={index} className="border-2">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Question {question.question_num}</CardTitle>
                  {questions.length > 1 && (
                    <Button
                      onClick={() => handleRemoveQuestion(index)}
                      variant="destructive"
                      size="sm"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Question Text *</Label>
                  <Textarea
                    value={question.question_text}
                    onChange={(e) => handleQuestionChange(index, 'question_text', e.target.value)}
                    placeholder="Enter the question"
                    rows={2}
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id={`open-${index}`}
                    checked={question.open}
                    onCheckedChange={(checked) => handleQuestionChange(index, 'open', checked)}
                  />
                  <Label htmlFor={`open-${index}`} className="cursor-pointer">
                    Open-ended question (all answers accepted)
                  </Label>
                </div>

                {!question.open && (
                  <div className="space-y-2">
                    <Label>Correct Answer *</Label>
                    <Input
                      value={question.correct_answer}
                      onChange={(e) => handleQuestionChange(index, 'correct_answer', e.target.value)}
                      placeholder="Enter the correct answer"
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label>Answer Options (optional, one per line)</Label>
                  <Textarea
                    value={Array.isArray(question.answers) ? question.answers.join('\n') : ''}
                    onChange={(e) => handleAnswerOptionsChange(index, e.target.value)}
                    placeholder="Option 1&#10;Option 2&#10;Option 3"
                    rows={4}
                  />
                  <p className="text-sm text-muted-foreground">
                    These will be shown to students as hints or multiple choice options
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-end gap-4">
        <Button onClick={() => navigate(selectedClass ? `/classes/${selectedClass}/manage?tab=assignments` : '/classes')} variant="outline">
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-2" />
              {editMode ? 'Update Quiz' : 'Create Quiz'}
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
