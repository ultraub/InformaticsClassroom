import { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../services/api';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription } from '../components/ui/alert';
import { CheckCircle2, Circle, AlertCircle, PlayCircle } from 'lucide-react';

interface CourseProgress {
  module: number;
  module_name: string;
  questions: QuestionStatus[];
  total_questions: number;
  answered_questions: number;
  correct_questions: number;
}

interface QuestionStatus {
  question_num: number;
  answered: boolean;
  correct: boolean;
}

interface CourseSummary {
  course: string;
  total_modules: number;
  total_questions: number;
  answered_questions: number;
  correct_questions: number;
  completion_percentage: number;
}

interface DashboardData {
  success: boolean;
  user: {
    id: string;
    email: string;
    display_name: string;
    team: string;
  };
  courses: string[];
  course_summaries: CourseSummary[];
}

interface ProgressData {
  success: boolean;
  course: string;
  progress: CourseProgress[];
}

export default function StudentCenter() {
  const [selectedCourse, setSelectedCourse] = useState<string>('');
  const navigate = useNavigate();
  const detailsSectionRef = useRef<HTMLDivElement>(null);

  // Fetch dashboard data
  const { data: dashboardData, isLoading: dashboardLoading, error: dashboardError } = useQuery({
    queryKey: ['student', 'dashboard'],
    queryFn: async () => {
      const response = await apiClient.get<DashboardData>('/api/student/dashboard');
      if (!response.success) {
        throw new Error(response.error || 'Failed to load dashboard');
      }
      return response.data || response;
    },
  });

  // Fetch course progress when course is selected
  const { data: progressData, isLoading: progressLoading } = useQuery({
    queryKey: ['student', 'progress', selectedCourse],
    queryFn: async () => {
      const response = await apiClient.get<ProgressData>(`/api/student/progress?course=${selectedCourse}`);
      if (!response.success) {
        throw new Error(response.error || 'Failed to load progress');
      }
      return response.data || response;
    },
    enabled: !!selectedCourse,
  });

  // Scroll to details section when course is selected
  useEffect(() => {
    if (selectedCourse && detailsSectionRef.current) {
      detailsSectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [selectedCourse]);

  if (dashboardLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (dashboardError) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {dashboardError instanceof Error ? dashboardError.message : 'Failed to load dashboard'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const courseSummary = (dashboardData as DashboardData | undefined)?.course_summaries.find((cs: CourseSummary) => cs.course === selectedCourse);

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Biomedical Informatics Student Center</h1>
        <p className="text-lg text-muted-foreground mt-2">
          Welcome {(dashboardData as DashboardData | undefined)?.user.display_name || (dashboardData as DashboardData | undefined)?.user.id}!
        </p>
      </div>

      {/* Course Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(dashboardData as DashboardData | undefined)?.course_summaries.map((summary: CourseSummary) => (
          <Card
            key={summary.course}
            className={`cursor-pointer transition-all hover:shadow-lg ${
              selectedCourse === summary.course ? 'ring-2 ring-primary' : ''
            }`}
            onClick={() => setSelectedCourse(summary.course)}
          >
            <CardHeader>
              <CardTitle>{summary.course}</CardTitle>
              <CardDescription>
                {summary.total_modules} modules • {summary.total_questions} questions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {/* Progress Bar */}
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="font-semibold">{summary.completion_percentage}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div
                      className="bg-blue-600 h-2.5 rounded-full transition-all"
                      style={{ width: `${summary.completion_percentage}%` }}
                    />
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {summary.answered_questions} of {summary.total_questions} questions attempted
                  </div>
                </div>

                {/* Accuracy Bar */}
                {summary.answered_questions > 0 && (
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Accuracy</span>
                      <span className="font-semibold text-green-600">
                        {Math.round((summary.correct_questions / summary.answered_questions) * 100)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div
                        className="bg-green-600 h-2.5 rounded-full transition-all"
                        style={{ width: `${(summary.correct_questions / summary.answered_questions) * 100}%` }}
                      />
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {summary.correct_questions} of {summary.answered_questions} correct
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Course Selection Dropdown */}
      <Card ref={detailsSectionRef}>
        <CardHeader>
          <CardTitle>Select Course to View Progress</CardTitle>
          <CardDescription>Choose a course to see detailed module progress</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={selectedCourse || undefined} onValueChange={setSelectedCourse}>
            <SelectTrigger className="w-full md:w-96">
              <SelectValue placeholder="Select a course" />
            </SelectTrigger>
            <SelectContent>
              {(dashboardData as DashboardData | undefined)?.courses.filter(course => course && course.trim() !== '').map((course: string) => (
                <SelectItem key={course} value={course}>
                  {course}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Course Progress Details */}
      {selectedCourse && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Course Modules for {selectedCourse}</CardTitle>
                {courseSummary && (
                  <CardDescription className="mt-2">
                    {courseSummary.answered_questions} of {courseSummary.total_questions} questions completed •{' '}
                    {courseSummary.correct_questions} correct
                  </CardDescription>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {progressLoading ? (
              <div className="text-center py-8">Loading progress...</div>
            ) : (progressData as ProgressData | undefined)?.progress && (progressData as ProgressData | undefined)!.progress.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-3 font-semibold">Module</th>
                      <th className="text-center p-3 font-semibold" colSpan={100}>
                        Questions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {(progressData as ProgressData).progress.map((module: CourseProgress) => (
                      <tr key={module.module} className="border-b hover:bg-muted/50">
                        <td className="p-3 font-medium">
                          <div className="flex items-center justify-between">
                            <div>
                              <div>{module.module_name}</div>
                              <div className="text-sm text-muted-foreground">
                                {module.correct_questions}/{module.total_questions} correct
                              </div>
                            </div>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => navigate(`/quiz?course=${selectedCourse}&module=${module.module}`)}
                              className="ml-4"
                            >
                              <PlayCircle className="w-4 h-4 mr-2" />
                              Take Quiz
                            </Button>
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="flex flex-wrap gap-2">
                            {module.questions.map((question: QuestionStatus) => (
                              <div
                                key={question.question_num}
                                className={`
                                  flex items-center justify-center w-10 h-10 rounded-md font-semibold text-sm
                                  ${
                                    question.correct
                                      ? 'bg-green-500 text-white'
                                      : question.answered
                                      ? 'bg-yellow-500 text-white'
                                      : 'bg-gray-200 text-gray-600'
                                  }
                                `}
                                title={
                                  question.correct
                                    ? 'Correct'
                                    : question.answered
                                    ? 'Attempted'
                                    : 'Not attempted'
                                }
                              >
                                {question.correct ? (
                                  <CheckCircle2 className="w-4 h-4" />
                                ) : question.answered ? (
                                  <Circle className="w-4 h-4" />
                                ) : (
                                  question.question_num
                                )}
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">No progress data available</div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Legend */}
      {selectedCourse && (progressData as ProgressData | undefined)?.progress && (progressData as ProgressData | undefined)!.progress.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Legend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                  <CheckCircle2 className="w-4 h-4 text-white" />
                </div>
                <span>Correct Answer</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                  <Circle className="w-4 h-4 text-white" />
                </div>
                <span>Attempted (Incorrect)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gray-200 rounded-md flex items-center justify-center text-gray-600 font-semibold text-sm">
                  #
                </div>
                <span>Not Attempted</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
