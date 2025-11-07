import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { classesService, type ClassMember, type ClassMembersResponse } from '../../services/classes';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription } from '../ui/alert';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Plus, Trash2, AlertCircle, Loader2, Users } from 'lucide-react';

interface StudentsTabProps {
  classId: string;
}

interface AddMemberFormData {
  user_id: string;
  email: string;
  role: 'instructor' | 'ta' | 'student';
}

export default function StudentsTab({ classId }: StudentsTabProps) {
  const queryClient = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);
  const [addMemberForm, setAddMemberForm] = useState<AddMemberFormData>({
    user_id: '',
    email: '',
    role: 'student',
  });
  const [editingMember, setEditingMember] = useState<string | null>(null);
  const [editRole, setEditRole] = useState<'instructor' | 'ta' | 'student'>('student');

  // Fetch class members
  const {
    data: membersData,
    isLoading: loadingMembers,
    error: membersError,
  } = useQuery<ClassMembersResponse | null>({
    queryKey: ['class', 'members', classId],
    queryFn: async (): Promise<ClassMembersResponse | null> => {
      if (!classId) return null;
      const response = await classesService.getClassMembers(classId);
      if (!response.success) {
        throw new Error(response.error || 'Failed to load members');
      }
      // Unwrap ApiResponse if needed
      if ('data' in response && response.data) {
        return response.data as ClassMembersResponse;
      }
      return response as ClassMembersResponse;
    },
    enabled: !!classId,
  });

  // Add member mutation
  const addMemberMutation = useMutation({
    mutationFn: async (data: AddMemberFormData) => {
      if (!classId) throw new Error('No class selected');
      const response = await classesService.addClassMember(classId, {
        user_id: data.user_id || data.email,
        role: data.role,
      });
      if (!response.success) {
        throw new Error(response.error || 'Failed to add member');
      }
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['class', 'members', classId] });
      setShowAddForm(false);
      setAddMemberForm({ user_id: '', email: '', role: 'student' });
    },
  });

  // Update member mutation
  const updateMemberMutation = useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: 'instructor' | 'ta' | 'student' }) => {
      if (!classId) throw new Error('No class selected');
      const response = await classesService.updateClassMember(classId, userId, { role });
      if (!response.success) {
        throw new Error(response.error || 'Failed to update member');
      }
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['class', 'members', classId] });
      setEditingMember(null);
    },
  });

  // Remove member mutation
  const removeMemberMutation = useMutation({
    mutationFn: async (userId: string) => {
      if (!classId) throw new Error('No class selected');
      const response = await classesService.removeClassMember(classId, userId);
      if (!response.success) {
        throw new Error(response.error || 'Failed to remove member');
      }
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['class', 'members', classId] });
    },
  });

  const handleAddMember = () => {
    if (!addMemberForm.email && !addMemberForm.user_id) {
      return;
    }
    addMemberMutation.mutate(addMemberForm);
  };

  const handleUpdateRole = (userId: string, role: 'instructor' | 'ta' | 'student') => {
    updateMemberMutation.mutate({ userId, role });
  };

  const handleRemoveMember = (member: ClassMember) => {
    if (
      window.confirm(
        `Are you sure you want to remove ${member.display_name || member.email} from ${classId}?`
      )
    ) {
      removeMemberMutation.mutate(member.user_id);
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'instructor':
        return 'bg-blue-100 text-blue-800';
      case 'ta':
        return 'bg-yellow-100 text-yellow-800';
      case 'student':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const members = membersData?.members || [];

  return (
    <>
      {/* Error Display */}
      {(membersError || addMemberMutation.error || updateMemberMutation.error || removeMemberMutation.error) && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {membersError instanceof Error
              ? membersError.message
              : addMemberMutation.error instanceof Error
              ? addMemberMutation.error.message
              : updateMemberMutation.error instanceof Error
              ? updateMemberMutation.error.message
              : removeMemberMutation.error instanceof Error
              ? removeMemberMutation.error.message
              : 'An error occurred'}
          </AlertDescription>
        </Alert>
      )}

      {/* Add Member Form */}
      {showAddForm && (
        <Card>
          <CardHeader>
            <CardTitle>Add Member to {classId}</CardTitle>
            <CardDescription>Assign a user to this class with a specific role</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Label htmlFor="email">User Email or ID</Label>
                <Input
                  id="email"
                  type="text"
                  placeholder="user@example.com or user_id"
                  value={addMemberForm.email || addMemberForm.user_id}
                  onChange={(e) =>
                    setAddMemberForm({
                      ...addMemberForm,
                      email: e.target.value,
                      user_id: e.target.value,
                    })
                  }
                />
              </div>
              <div>
                <Label htmlFor="role">Role</Label>
                <Select
                  value={addMemberForm.role}
                  onValueChange={(value: 'instructor' | 'ta' | 'student') =>
                    setAddMemberForm({ ...addMemberForm, role: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="instructor">Instructor</SelectItem>
                    <SelectItem value="ta">TA</SelectItem>
                    <SelectItem value="student">Student</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={handleAddMember}
                  disabled={addMemberMutation.isPending || !addMemberForm.email}
                >
                  {addMemberMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    'Add Member'
                  )}
                </Button>
                <Button variant="outline" onClick={() => setShowAddForm(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Members Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                Students
              </CardTitle>
              <CardDescription>
                {loadingMembers ? 'Loading...' : `${members.length} member(s)`}
              </CardDescription>
            </div>
            {!showAddForm && (
              <Button onClick={() => setShowAddForm(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Add Member
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {loadingMembers ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin" />
              <span className="ml-2 text-lg">Loading members...</span>
            </div>
          ) : members.length === 0 ? (
            <div className="text-center py-12">
              <Users className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground text-lg mb-4">
                No members found in this class. Add your first member to get started!
              </p>
              <Button onClick={() => setShowAddForm(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Add Member
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3 font-semibold">Name</th>
                    <th className="text-left p-3 font-semibold">Email</th>
                    <th className="text-left p-3 font-semibold">User ID</th>
                    <th className="text-left p-3 font-semibold">Role</th>
                    <th className="text-right p-3 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member: ClassMember) => (
                    <tr key={member.user_id} className="border-b hover:bg-muted/50">
                      <td className="p-3">{member.display_name || '-'}</td>
                      <td className="p-3">{member.email}</td>
                      <td className="p-3 text-sm text-muted-foreground">{member.user_id}</td>
                      <td className="p-3">
                        {editingMember === member.user_id ? (
                          <div className="flex items-center gap-2">
                            <Select
                              value={editRole}
                              onValueChange={(value: 'instructor' | 'ta' | 'student') =>
                                setEditRole(value)
                              }
                            >
                              <SelectTrigger className="w-32">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="instructor">Instructor</SelectItem>
                                <SelectItem value="ta">TA</SelectItem>
                                <SelectItem value="student">Student</SelectItem>
                              </SelectContent>
                            </Select>
                            <Button
                              size="sm"
                              onClick={() => handleUpdateRole(member.user_id, editRole)}
                              disabled={updateMemberMutation.isPending}
                            >
                              {updateMemberMutation.isPending ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                'Save'
                              )}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setEditingMember(null)}
                            >
                              Cancel
                            </Button>
                          </div>
                        ) : (
                          <button
                            onClick={() => {
                              setEditingMember(member.user_id);
                              setEditRole(member.role);
                            }}
                            className={`px-3 py-1 rounded-full text-sm font-medium ${getRoleBadgeColor(
                              member.role
                            )} hover:opacity-80 cursor-pointer`}
                          >
                            {member.role}
                          </button>
                        )}
                      </td>
                      <td className="p-3">
                        <div className="flex justify-end gap-2">
                          <Button
                            onClick={() => handleRemoveMember(member)}
                            variant="destructive"
                            size="sm"
                            disabled={removeMemberMutation.isPending}
                          >
                            {removeMemberMutation.isPending ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <>
                                <Trash2 className="w-4 h-4 mr-1" />
                                Remove
                              </>
                            )}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}
