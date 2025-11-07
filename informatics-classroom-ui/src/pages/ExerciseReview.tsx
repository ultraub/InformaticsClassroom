import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription } from '../components/ui/alert';
import { AlertCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react';

interface ModuleData {
  module: string | number;
  total_questions: number;
  questions_attempted: number;
  questions_correct: number;
  module_progress: number;
  module_correctness: number;
}

interface ClassData {
  class: string;
  overall_progress: number;
  overall_correctness: number;
  modules: ModuleData[];
  total_questions: number;
  questions_attempted: number;
  questions_correct: number;
}

interface ExerciseReviewResponse {
  success: boolean;
  classes: ClassData[];
  error?: string;
}

export default function ExerciseReview() {
  const [expandedClasses, setExpandedClasses] = useState<Set<string>>(new Set());

  // Fetch exercise review data
  const { data: reviewData, isLoading, error } = useQuery<ExerciseReviewResponse>({
    queryKey: ['student', 'exercise-review'],
    queryFn: async (): Promise<ExerciseReviewResponse> => {
      const response = await apiClient.get<ExerciseReviewResponse>('/api/student/exercise-review');
      if (!response.success) {
        throw new Error(response.error || 'Failed to load exercise review');
      }
      if ('data' in response && response.data) {
        return response.data;
      }
      return response as ExerciseReviewResponse;
    },
  });

  const toggleClass = (className: string) => {
    const newExpanded = new Set(expandedClasses);
    if (newExpanded.has(className)) {
      newExpanded.delete(className);
    } else {
      newExpanded.add(className);
    }
    setExpandedClasses(newExpanded);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2 text-lg">Loading...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error instanceof Error ? error.message : 'Failed to load exercise review'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const classes = reviewData?.classes || [];

  if (classes.length === 0) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold text-gray-900">No Classes Available</h2>
          <p className="text-gray-600 mt-2">You do not have access to any classes yet.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Exercise Review</h1>
        <p className="text-lg text-muted-foreground mt-2">
          Track your progress across all classes and modules
        </p>
      </div>

      {/* Classes */}
      <div className="space-y-4">
        {classes.map((classData: ClassData) => (
          <Card key={classData.class} className="overflow-hidden">
            <CardHeader className="pb-3">
              <CardTitle className="text-xl">{classData.class}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Overall Progress */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">Overall Progress:</span>
                  <span className="text-sm font-semibold">{classData.overall_progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                  <div
                    className="bg-green-500 h-4 transition-all duration-300"
                    style={{ width: `${classData.overall_progress}%` }}
                  />
                </div>
              </div>

              {/* Overall Correctness */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">Overall Correctness:</span>
                  <span className="text-sm font-semibold">{classData.overall_correctness}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                  <div
                    className="bg-blue-500 h-4 transition-all duration-300"
                    style={{ width: `${classData.overall_correctness}%` }}
                  />
                </div>
              </div>

              {/* View Modules Button */}
              <div className="pt-2">
                <Button
                  variant="outline"
                  onClick={() => toggleClass(classData.class)}
                  className="w-full justify-between"
                >
                  <span>
                    {expandedClasses.has(classData.class) ? 'Hide Modules' : 'View Modules'}
                  </span>
                  {expandedClasses.has(classData.class) ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </Button>
              </div>

              {/* Modules Breakdown */}
              {expandedClasses.has(classData.class) && (
                <div className="mt-4 space-y-3 pt-3 border-t">
                  {classData.modules
                    .sort((a: ModuleData, b: ModuleData) => {
                      const aNum = typeof a.module === 'number' ? a.module : parseInt(String(a.module));
                      const bNum = typeof b.module === 'number' ? b.module : parseInt(String(b.module));
                      return aNum - bNum;
                    })
                    .map((module: ModuleData) => (
                      <div key={module.module} className="p-3 bg-gray-50 rounded-lg space-y-3">
                        <h5 className="font-semibold text-lg">Module {module.module}</h5>

                        {/* Module Progress */}
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm">Progress:</span>
                            <span className="text-sm font-semibold">{module.module_progress}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                            <div
                              className="bg-green-500 h-3 transition-all duration-300"
                              style={{ width: `${module.module_progress}%` }}
                            />
                          </div>
                        </div>

                        {/* Module Correctness */}
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm">Correctness:</span>
                            <span className="text-sm font-semibold">{module.module_correctness}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                            <div
                              className="bg-blue-500 h-3 transition-all duration-300"
                              style={{ width: `${module.module_correctness}%` }}
                            />
                          </div>
                        </div>

                        {/* Stats */}
                        <div className="flex justify-between text-xs text-gray-600 pt-1">
                          <span>Attempted: {module.questions_attempted}/{module.total_questions}</span>
                          <span>Correct: {module.questions_correct}/{module.questions_attempted}</span>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>About Exercise Review</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc list-inside space-y-2 text-sm text-muted-foreground">
            <li>
              <strong>Progress:</strong> Shows the percentage of questions you've attempted
            </li>
            <li>
              <strong>Correctness:</strong> Shows the percentage of attempted questions you answered
              correctly
            </li>
            <li>View module details by clicking "View Modules" for each class</li>
            <li>Progress is automatically updated as you complete exercises</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
