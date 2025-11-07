import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription } from '../ui/alert';
import { AlertCircle, Loader2, Plus, BookOpen, Edit, Trash2 } from 'lucide-react';

interface Assignment {
  id: string;
  class: string;
  module: number;
  title: string;
  description: string;
  question_count: number;
  owner: string;
  created_at: string;
  updated_at: string;
}

interface AssignmentsResponse {
  success: boolean;
  quizzes: Assignment[];
  error?: string;
}

interface AssignmentsTabProps {
  classId: string;
}

export default function AssignmentsTab({ classId }: AssignmentsTabProps) {
  const navigate = useNavigate();
  const [selectedModule, setSelectedModule] = useState<number | 'all'>('all');

  // Fetch assignments for this class
  const {
    data: assignmentsData,
    isLoading: loadingAssignments,
    error: assignmentsError,
  } = useQuery<AssignmentsResponse>({
    queryKey: ['class', 'assignments', classId],
    queryFn: async (): Promise<AssignmentsResponse> => {
      if (!classId) return { success: false, quizzes: [], error: 'No class selected' };
      const response = await apiClient.get<AssignmentsResponse>(
        `/api/instructor/quizzes?class=${classId}`
      );
      return response;
    },
    enabled: !!classId,
  });

  const assignments = assignmentsData?.quizzes || [];

  // Get unique modules for filtering
  const modules = Array.from(new Set(assignments.map((a) => a.module).filter((m) => m != null))).sort(
    (a, b) => a - b
  );

  // Filter assignments by selected module
  const filteredAssignments =
    selectedModule === 'all'
      ? assignments
      : assignments.filter((a) => a.module === selectedModule);

  // Group by module for display
  const assignmentsByModule = filteredAssignments.reduce((acc, assignment) => {
    const module = assignment.module ?? 0;
    if (!acc[module]) {
      acc[module] = [];
    }
    acc[module].push(assignment);
    return acc;
  }, {} as Record<number, Assignment[]>);

  const handleCreateQuiz = () => {
    navigate('/quiz/create');
  };

  const handleEditQuiz = (quizId: string) => {
    navigate(`/quiz/edit?id=${quizId}`);
  };

  const handleDeleteQuiz = async (quizId: string) => {
    if (window.confirm('Are you sure you want to delete this quiz?')) {
      // TODO: Implement delete functionality
      console.log('Delete quiz:', quizId);
    }
  };

  return (
    <>
      {/* Error Display */}
      {assignmentsError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {assignmentsError instanceof Error
              ? assignmentsError.message
              : 'Failed to load assignments'}
          </AlertDescription>
        </Alert>
      )}

      {/* Header with Actions */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="w-5 h-5" />
                Assignments
              </CardTitle>
              <CardDescription>
                {loadingAssignments
                  ? 'Loading...'
                  : `${assignments.length} assignment(s) in ${classId}`}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {/* Module Filter */}
              {modules.length > 0 && (
                <select
                  value={selectedModule}
                  onChange={(e) =>
                    setSelectedModule(e.target.value === 'all' ? 'all' : parseInt(e.target.value))
                  }
                  className="border rounded-md px-3 py-2 text-sm"
                >
                  <option value="all">All Modules</option>
                  {modules.map((module) => (
                    <option key={module} value={module}>
                      Module {module}
                    </option>
                  ))}
                </select>
              )}
              <Button onClick={handleCreateQuiz}>
                <Plus className="w-4 h-4 mr-2" />
                Create Quiz
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loadingAssignments ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin" />
              <span className="ml-2 text-lg">Loading assignments...</span>
            </div>
          ) : assignments.length === 0 ? (
            <div className="text-center py-12">
              <BookOpen className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground text-lg mb-4">
                No assignments found in this class. Create your first quiz to get started!
              </p>
              <Button onClick={handleCreateQuiz}>
                <Plus className="w-4 h-4 mr-2" />
                Create Quiz
              </Button>
            </div>
          ) : (
            <div className="space-y-6">
              {Object.entries(assignmentsByModule)
                .sort(([a], [b]) => parseInt(a) - parseInt(b))
                .map(([module, moduleAssignments]) => (
                  <div key={module}>
                    <h3 className="text-lg font-semibold mb-3">Module {module}</h3>
                    <div className="space-y-2">
                      {moduleAssignments.map((assignment) => (
                        <div
                          key={assignment.id}
                          className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <h4 className="font-medium text-base">{assignment.title}</h4>
                              {assignment.description && (
                                <p className="text-sm text-muted-foreground mt-1">
                                  {assignment.description}
                                </p>
                              )}
                              <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                                <span>{assignment.question_count} questions</span>
                                {assignment.updated_at && (
                                  <span>
                                    Updated: {new Date(assignment.updated_at).toLocaleDateString()}
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-2 ml-4">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleEditQuiz(assignment.id)}
                              >
                                <Edit className="w-4 h-4 mr-1" />
                                Edit
                              </Button>
                              <Button
                                size="sm"
                                variant="destructive"
                                onClick={() => handleDeleteQuiz(assignment.id)}
                              >
                                <Trash2 className="w-4 h-4 mr-1" />
                                Delete
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}
