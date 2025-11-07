import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  AlertCircle,
  Loader2,
  Plus,
  Trash2,
  BookOpen,
  Users,
  Calendar,
  UserCircle,
  Shield,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

interface ClassMetadata {
  id: string;
  name: string;
  owner: string | null;
  role: string;
  quiz_count: number;
  student_count: number;
  created_at: string | null;
  can_delete: boolean;
}

interface ClassesResponse {
  success: boolean;
  classes: ClassMetadata[];
  error?: string;
}

interface CreateClassResponse {
  success: boolean;
  class?: ClassMetadata;
  error?: string;
}

interface DeleteResponse {
  success: boolean;
  error?: string;
}

export default function ClassSelector() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newClassName, setNewClassName] = useState('');
  const [deleteConfirmClass, setDeleteConfirmClass] = useState<ClassMetadata | null>(null);

  const isInstructor = user?.roles?.includes('instructor') || user?.roles?.includes('admin');

  // Fetch classes with metadata
  const {
    data: classesData,
    isLoading,
    error,
  } = useQuery<ClassesResponse>({
    queryKey: ['instructor', 'classes', 'metadata'],
    queryFn: async (): Promise<ClassesResponse> => {
      const response = await apiClient.get<ClassesResponse>('/api/instructor/classes');
      return response;
    },
  });

  // Create class mutation
  const createMutation = useMutation({
    mutationFn: async (className: string) => {
      const response = await apiClient.post<CreateClassResponse>('/api/classes', {
        name: className,
      });
      if (!response.success) {
        throw new Error(response.error || 'Failed to create class');
      }
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instructor', 'classes'] });
      setShowCreateDialog(false);
      setNewClassName('');
    },
  });

  // Delete class mutation
  const deleteMutation = useMutation({
    mutationFn: async (classId: string) => {
      const response = await apiClient.delete<DeleteResponse>(`/api/classes/${classId}`);
      if (!response.success) {
        throw new Error(response.error || 'Failed to delete class');
      }
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instructor', 'classes'] });
      setDeleteConfirmClass(null);
    },
  });

  const handleCreateClass = () => {
    if (newClassName.trim()) {
      createMutation.mutate(newClassName.trim());
    }
  };

  const handleDeleteClass = (cls: ClassMetadata) => {
    setDeleteConfirmClass(cls);
  };

  const confirmDelete = () => {
    if (deleteConfirmClass) {
      deleteMutation.mutate(deleteConfirmClass.id);
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'instructor':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'ta':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2 text-lg">Loading classes...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error instanceof Error ? error.message : 'Failed to load classes'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const classes = classesData?.classes || [];

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Class Management</h1>
          <p className="text-lg text-muted-foreground mt-2">
            Select a class to manage or create a new one
          </p>
        </div>
        {isInstructor && (
          <Button onClick={() => setShowCreateDialog(true)} size="lg">
            <Plus className="w-5 h-5 mr-2" />
            Create Class
          </Button>
        )}
      </div>

      {/* Error messages */}
      {createMutation.isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {createMutation.error instanceof Error
              ? createMutation.error.message
              : 'Failed to create class'}
          </AlertDescription>
        </Alert>
      )}

      {deleteMutation.isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {deleteMutation.error instanceof Error
              ? deleteMutation.error.message
              : 'Failed to delete class'}
          </AlertDescription>
        </Alert>
      )}

      {/* Classes Grid */}
      {classes.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <BookOpen className="w-16 h-16 text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">No Classes Found</h2>
            <p className="text-muted-foreground text-center mb-4">
              {isInstructor
                ? 'Get started by creating your first class'
                : 'You need to be assigned as an instructor or TA for at least one class'}
            </p>
            {isInstructor && (
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Create Your First Class
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {classes.map((cls) => (
            <Card
              key={cls.id}
              className="hover:shadow-lg transition-all relative group"
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-xl mb-2">{cls.name}</CardTitle>
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${getRoleBadgeColor(
                          cls.role
                        )}`}
                      >
                        <Shield className="w-3 h-3 mr-1" />
                        {cls.role.toUpperCase()}
                      </span>
                    </div>
                  </div>
                  {cls.can_delete && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteClass(cls);
                      }}
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Owner */}
                {cls.owner && (
                  <div className="flex items-center text-sm text-muted-foreground">
                    <UserCircle className="w-4 h-4 mr-2" />
                    <span>Owner: {cls.owner}</span>
                  </div>
                )}

                {/* Quiz Count */}
                <div className="flex items-center text-sm text-muted-foreground">
                  <BookOpen className="w-4 h-4 mr-2" />
                  <span>
                    {cls.quiz_count} {cls.quiz_count === 1 ? 'quiz' : 'quizzes'}
                  </span>
                </div>

                {/* Student Count */}
                <div className="flex items-center text-sm text-muted-foreground">
                  <Users className="w-4 h-4 mr-2" />
                  <span>
                    {cls.student_count} {cls.student_count === 1 ? 'student' : 'students'}
                  </span>
                </div>

                {/* Created Date */}
                {cls.created_at && (
                  <div className="flex items-center text-sm text-muted-foreground">
                    <Calendar className="w-4 h-4 mr-2" />
                    <span>Created: {new Date(cls.created_at).toLocaleDateString()}</span>
                  </div>
                )}

                {/* Manage Button */}
                <Button
                  className="w-full mt-4"
                  onClick={() => navigate(`/classes/${cls.id}/manage`)}
                >
                  Manage Class
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Class Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Class</DialogTitle>
            <DialogDescription>
              Enter a name for your new class. You'll be assigned as the instructor.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="className">Class Name *</Label>
              <Input
                id="className"
                placeholder="e.g., BMI6018_Spring2024"
                value={newClassName}
                onChange={(e) => setNewClassName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && newClassName.trim()) {
                    handleCreateClass();
                  }
                }}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowCreateDialog(false);
                setNewClassName('');
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateClass}
              disabled={!newClassName.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Class'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmClass !== null}
        onOpenChange={() => setDeleteConfirmClass(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Class</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteConfirmClass?.name}</strong>?
              This will permanently delete all quizzes and data associated with this class.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                This action cannot be undone. All quizzes, assignments, and class data will be
                permanently deleted.
              </AlertDescription>
            </Alert>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmClass(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete Class
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
