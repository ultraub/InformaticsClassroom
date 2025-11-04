import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Modal, Button, Input, Badge } from '../common';
import { usersService } from '../../services/users';
import { permissionsService } from '../../services/permissions';
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

  const [formData, setFormData] = useState({
    displayName: '',
    email: '',
    role: Role.STUDENT,
    isActive: true,
  });

  const [selectedPermissions, setSelectedPermissions] = useState<Permission[]>([]);
  const [showPermissions, setShowPermissions] = useState(false);

  // Available permissions grouped by category
  const permissionCategories = {
    'Quiz Management': [
      Permission.QUIZ_VIEW,
      Permission.QUIZ_CREATE,
      Permission.QUIZ_MODIFY,
      Permission.QUIZ_DELETE,
      Permission.QUIZ_SHARE,
      Permission.QUIZ_COLLABORATE,
    ],
    'Assignment Management': [
      Permission.ASSIGNMENT_VIEW,
      Permission.ASSIGNMENT_CREATE,
      Permission.ASSIGNMENT_MANAGE,
      Permission.ASSIGNMENT_GRADE,
    ],
    'User Management': [
      Permission.USER_VIEW,
      Permission.USER_MANAGE,
    ],
    'System': [
      Permission.TOKEN_GENERATE,
      Permission.CLASS_ADMIN,
      Permission.CLASS_VIEW_ANALYTICS,
      Permission.SYSTEM_ADMIN,
      Permission.SYSTEM_VIEW_LOGS,
    ],
  };

  useEffect(() => {
    if (user) {
      setFormData({
        displayName: user.displayName || '',
        email: user.email || '',
        role: user.roles[0] || Role.STUDENT,
        isActive: user.isActive,
      });
      // TODO: Fetch user's current permissions
      setSelectedPermissions([]);
    }
  }, [user]);

  const updateMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      if (!user) return;
      const response = await usersService.updateUser(user.id, data);
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
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={user ? `Edit User: ${user.username}` : 'Create User'}
      size="lg"
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
        {/* Basic Information */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-4">
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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Role
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
              <p className="mt-1 text-xs text-gray-500">
                Current role: <Badge variant={getRoleBadgeVariant(formData.role)} size="sm">{formData.role}</Badge>
              </p>
            </div>

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

        {/* Class Roles */}
        {user?.classRoles && user.classRoles.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              Class Roles
            </h4>
            <div className="space-y-2">
              {user.classRoles.map((classRole, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {classRole.className}
                    </p>
                    <p className="text-xs text-gray-500">{classRole.role}</p>
                  </div>
                  <Badge variant="primary" size="sm">
                    {classRole.role}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Advanced Permissions */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-medium text-gray-900">
              Advanced Permissions
            </h4>
            <button
              type="button"
              onClick={() => setShowPermissions(!showPermissions)}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              {showPermissions ? 'Hide' : 'Show'} Permissions
            </button>
          </div>

          {showPermissions && (
            <div className="space-y-4 max-h-96 overflow-y-auto border border-gray-200 rounded-md p-4">
              {Object.entries(permissionCategories).map(([category, permissions]) => (
                <div key={category}>
                  <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                    {category}
                  </h5>
                  <div className="space-y-2">
                    {permissions.map((permission) => (
                      <label
                        key={permission}
                        className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-2 rounded"
                      >
                        <input
                          type="checkbox"
                          checked={selectedPermissions.includes(permission)}
                          onChange={() => togglePermission(permission)}
                          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        />
                        <span className="text-sm text-gray-700">
                          {permission.replace('.', ' - ')}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Selected Permissions Summary */}
        {selectedPermissions.length > 0 && (
          <div>
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
      </form>
    </Modal>
  );
}
