import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import { Modal, Button, Input, Badge } from '../common';
import { usersService } from '../../services/users';
import { permissionsService } from '../../services/permissions';
import { classesService } from '../../services/classes';
import { apiClient } from '../../services/api';
import { User, Role, ClassRole, Permission } from '../../types';
import { useUIStore } from '../../store/uiStore';

interface UserEditModalProps {
  user: User | null;
  isOpen: boolean;
  onClose: () => void;
}

export function UserEditModal({ user, isOpen, onClose }: UserEditModalProps) {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();

  const [formData, setFormData] = useState<{
    displayName: string;
    email: string;
    role: Role;
    isActive: boolean;
  }>({
    displayName: '',
    email: '',
    role: Role.STUDENT,
    isActive: true,
  });

  const [selectedPermissions, setSelectedPermissions] = useState<Permission[]>([]);
  const [showPermissions, setShowPermissions] = useState(false);
  const [showAddClassDialog, setShowAddClassDialog] = useState(false);
  const [selectedClassId, setSelectedClassId] = useState('');
  const [selectedClassRole, setSelectedClassRole] = useState<'student' | 'ta' | 'instructor'>('student');

  // Available permissions grouped by category
  const permissionCategories = {
    'Quiz Management': [
      Permission.QUIZ_VIEW,
      Permission.QUIZ_CREATE,
      Permission.QUIZ_MODIFY,
      Permission.QUIZ_DELETE,
    ],
    'User Management': [
      Permission.USER_VIEW,
      Permission.USER_MANAGE,
    ],
    'Class & System': [
      Permission.TOKEN_GENERATE,
      Permission.CLASS_ADMIN,
      Permission.CLASS_VIEW_ANALYTICS,
      Permission.SYSTEM_ADMIN,
      Permission.SYSTEM_VIEW_LOGS,
    ],
  };

  // Fetch available classes for adding membership
  const { data: classesData } = useQuery({
    queryKey: ['instructor', 'classes', 'metadata'],
    queryFn: async () => {
      const response = await apiClient.get<{success: boolean; classes: Array<{id: string; name: string}>}>('/api/instructor/classes');
      return response;
    },
    enabled: isOpen, // Only fetch when modal is open
  });

  useEffect(() => {
    if (user) {
      setFormData({
        displayName: user.displayName || '',
        email: user.email || '',
        role: user.roles[0] || Role.STUDENT,
        isActive: user.isActive,
      });
      // Set user's current direct permissions
      setSelectedPermissions(user.permissions || []);
    }
  }, [user]);

  const updateMutation = useMutation({
    mutationFn: async (data: typeof formData & { permissions?: Permission[] }) => {
      if (!user) return;
      const response = await usersService.updateUser(user.id, { ...data, permissions: selectedPermissions } as any);
      if (!response.success) {
        throw new Error(response.error || 'Failed to update user');
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      addToast('User updated successfully', 'success');
      onClose();
    },
    onError: (error: Error) => {
      addToast(error.message, 'error');
    },
  });

  // Update class role mutation
  const updateClassRoleMutation = useMutation({
    mutationFn: async ({ classId, role }: { classId: string; role: 'student' | 'ta' | 'instructor' }) => {
      if (!user) return;
      const response = await classesService.updateClassMember(classId, user.id, { role });
      if (!response.success) {
        throw new Error(response.error || 'Failed to update class role');
      }
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      addToast('Class role updated successfully', 'success');
    },
    onError: (error: Error) => {
      addToast(error.message, 'error');
    },
  });

  // Remove from class mutation
  const removeFromClassMutation = useMutation({
    mutationFn: async (classId: string) => {
      if (!user) return;
      const response = await classesService.removeClassMember(classId, user.id);
      if (!response.success) {
        throw new Error(response.error || 'Failed to remove from class');
      }
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      addToast('User removed from class successfully', 'success');
    },
    onError: (error: Error) => {
      addToast(error.message, 'error');
    },
  });

  // Add to class mutation
  const addToClassMutation = useMutation({
    mutationFn: async ({ classId, role }: { classId: string; role: 'student' | 'ta' | 'instructor' }) => {
      if (!user) return;
      const response = await classesService.addClassMember(classId, { user_id: user.id, role });
      if (!response.success) {
        throw new Error(response.error || 'Failed to add to class');
      }
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      addToast('User added to class successfully', 'success');
      setShowAddClassDialog(false);
      setSelectedClassId('');
      setSelectedClassRole('student');
    },
    onError: (error: Error) => {
      addToast(error.message, 'error');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(formData);
  };

  const togglePermission = (permission: Permission) => {
    setSelectedPermissions((prev) =>
      prev.includes(permission)
        ? prev.filter((p) => p !== permission)
        : [...prev, permission]
    );
  };

  const getRoleBadgeVariant = (role: Role) => {
    switch (role) {
      case Role.ADMIN:
        return 'danger' as const;
      case Role.INSTRUCTOR:
        return 'primary' as const;
      case Role.TA:
        return 'warning' as const;
      default:
        return 'secondary' as const;
    }
  };

  return (
    <>
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={user ? `Edit User: ${user.username}` : 'Create User'}
      size="xl"
      footer={
        <div className="flex justify-end space-x-3">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            loading={updateMutation.isPending}
          >
            Save Changes
          </Button>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Two-column layout for better organization */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Basic Info & Global Role */}
          <div className="space-y-6">
            {/* Basic Information */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-4 pb-2 border-b border-gray-200">
                Basic Information
              </h4>
              <div className="space-y-4">
                <Input
                  label="Display Name"
                  value={formData.displayName}
                  onChange={(e) =>
                    setFormData({ ...formData, displayName: e.target.value })
                  }
                  required
                />

                <Input
                  label="Email"
                  type="email"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  required
                />

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="isActive"
                    checked={formData.isActive}
                    onChange={(e) =>
                      setFormData({ ...formData, isActive: e.target.checked })
                    }
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label htmlFor="isActive" className="ml-2 text-sm text-gray-700">
                    Account is active
                  </label>
                </div>
              </div>
            </div>

            {/* Global Role & Permissions */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-4 pb-2 border-b border-gray-200">
                Global Role & Permissions
              </h4>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Global Role
                  </label>
                  <select
                    value={formData.role}
                    onChange={(e) =>
                      setFormData({ ...formData, role: e.target.value as Role })
                    }
                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  >
                    <option value={Role.STUDENT}>Student</option>
                    <option value={Role.TA}>Teaching Assistant</option>
                    <option value={Role.INSTRUCTOR}>Instructor</option>
                    <option value={Role.ADMIN}>Administrator</option>
                  </select>
                  <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant={getRoleBadgeVariant(formData.role)} size="sm">
                        {formData.role}
                      </Badge>
                      <span className="text-xs text-gray-500">Global Permissions:</span>
                    </div>
                    <p className="text-xs text-gray-600">
                      {formData.role === Role.ADMIN && '• Full system access and administration'}
                      {formData.role === Role.INSTRUCTOR && '• Create/manage quizzes\n• View analytics\n• Generate tokens\n• Manage users (view)'}
                      {formData.role === Role.TA && '• View/create/modify quizzes\n• View analytics\n• View students'}
                      {formData.role === Role.STUDENT && '• Take quizzes\n• View own data'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Class Memberships */}
          <div>
            <div>
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-gray-200">
                <div>
                  <h4 className="text-sm font-medium text-gray-900">
                    Class Memberships
                  </h4>
                  <p className="text-xs text-gray-500 mt-1">
                    {(() => {
                      const classCount = user?.class_memberships?.length ||
                                       (user?.classRoles ? Object.keys(user.classRoles).length : 0);
                      return classCount > 0
                        ? `Member of ${classCount} class${classCount !== 1 ? 'es' : ''}`
                        : 'No class memberships';
                    })()}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  icon={<PlusIcon className="h-4 w-4" />}
                  onClick={() => setShowAddClassDialog(true)}
                >
                  Add Class
                </Button>
              </div>

              {(() => {
                // Handle both new list format and old dict format
                const memberships: Array<{className: string; role: string}> = [];

                // New format: class_memberships array
                if (user?.class_memberships && user.class_memberships.length > 0) {
                  user.class_memberships.forEach(m => {
                    memberships.push({className: m.class_id, role: m.role});
                  });
                }
                // Old format: classRoles object
                else if (user?.classRoles && Object.keys(user.classRoles).length > 0) {
                  Object.entries(user.classRoles).forEach(([className, role]) => {
                    memberships.push({className, role});
                  });
                }

                return memberships.length > 0 ? (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {memberships.map(({className, role}) => (
                    <div
                      key={className}
                      className="p-4 bg-white border border-gray-200 rounded-lg hover:border-primary-300 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {className}
                            </p>
                            <Badge variant="primary" size="sm">
                              {role}
                            </Badge>
                          </div>
                          <p className="text-xs text-gray-500 mb-3">
                            {role === 'instructor' && '• Create/edit quizzes  • Manage members  • View analytics'}
                            {role === 'ta' && '• Create/edit quizzes  • View analytics'}
                            {role === 'student' && '• Take quizzes  • View own progress'}
                          </p>

                          <div className="flex items-center gap-2">
                            <label className="text-xs font-medium text-gray-700">
                              Change Role:
                            </label>
                            <select
                              value={role}
                              onChange={(e) => {
                                const newRole = e.target.value as 'student' | 'ta' | 'instructor';
                                updateClassRoleMutation.mutate({ classId: className, role: newRole });
                              }}
                              className="text-xs rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                              disabled={updateClassRoleMutation.isPending}
                            >
                              <option value="student">Student</option>
                              <option value="ta">TA</option>
                              <option value="instructor">Instructor</option>
                            </select>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => {
                            if (confirm(`Remove ${user.username} from ${className}?`)) {
                              removeFromClassMutation.mutate(className);
                            }
                          }}
                          className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                          title="Remove from class"
                          disabled={removeFromClassMutation.isPending}
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                ) : (
                  <div className="text-center py-8 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-sm text-gray-500 mb-3">
                      No class memberships yet
                    </p>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      icon={<PlusIcon className="h-4 w-4" />}
                      onClick={() => setShowAddClassDialog(true)}
                    >
                      Add to Class
                    </Button>
                  </div>
                );
              })()}
            </div>
          </div>
        </div>

        {/* Additional Permissions Section */}
        <div className="pt-6 border-t border-gray-200">
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h4 className="text-sm font-medium text-gray-900">
                  Additional Permissions
                </h4>
                <p className="text-xs text-gray-500 mt-1">
                  Grant specific permissions beyond the user's global role and class permissions
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowPermissions(!showPermissions)}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                {showPermissions ? 'Hide' : 'Show'} Details
              </button>
            </div>
          </div>

          {showPermissions && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {Object.entries(permissionCategories).map(([category, permissions]) => (
                <div key={category} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-3 pb-2 border-b border-gray-300">
                    {category}
                  </h5>
                  <div className="space-y-2">
                    {permissions.map((permission) => (
                      <label
                        key={permission}
                        className="flex items-start space-x-3 cursor-pointer hover:bg-white p-2 rounded transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={selectedPermissions.includes(permission)}
                          onChange={() => togglePermission(permission)}
                          className="h-4 w-4 mt-0.5 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        />
                        <div className="flex-1 min-w-0">
                          <span className="text-sm text-gray-700 font-medium block">
                            {permission.split('.')[1].replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs text-gray-500 truncate block">
                            {permission}
                          </span>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Selected Permissions Summary */}
          {selectedPermissions.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-300">
              <h4 className="text-sm font-medium text-gray-900 mb-2">
                Selected Permissions ({selectedPermissions.length})
              </h4>
              <div className="flex flex-wrap gap-2">
                {selectedPermissions.map((permission) => (
                  <Badge
                    key={permission}
                    variant="primary"
                    size="sm"
                    removable
                    onRemove={() => togglePermission(permission)}
                  >
                    {permission}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </form>
    </Modal>

    {/* Add Class Membership Modal */}
    <Modal
      isOpen={showAddClassDialog}
      onClose={() => {
        setShowAddClassDialog(false);
        setSelectedClassId('');
        setSelectedClassRole('student');
      }}
      title="Add to Class"
      size="md"
      footer={
        <div className="flex justify-end space-x-3">
          <Button
            variant="outline"
            onClick={() => {
              setShowAddClassDialog(false);
              setSelectedClassId('');
              setSelectedClassRole('student');
            }}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              if (selectedClassId) {
                addToClassMutation.mutate({ classId: selectedClassId, role: selectedClassRole });
              }
            }}
            loading={addToClassMutation.isPending}
            disabled={!selectedClassId}
          >
            Add to Class
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Class
          </label>
          <select
            value={selectedClassId}
            onChange={(e) => setSelectedClassId(e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          >
            <option value="">-- Select a class --</option>
            {classesData?.classes?.map((cls) => (
              <option key={cls.id} value={cls.id}>
                {cls.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Role in Class
          </label>
          <select
            value={selectedClassRole}
            onChange={(e) => setSelectedClassRole(e.target.value as 'student' | 'ta' | 'instructor')}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          >
            <option value="student">Student</option>
            <option value="ta">Teaching Assistant</option>
            <option value="instructor">Instructor</option>
          </select>
        </div>
      </div>
    </Modal>
    </>
  );
}
