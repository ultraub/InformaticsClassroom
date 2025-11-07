import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { Card, Button, Badge } from '../components/common';
import { permissionsService } from '../services/permissions';
import { Permission, Role } from '../types';
import { useUIStore } from '../store/uiStore';
import { classNames } from '../utils/classNames';

export function PermissionMatrix() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();
  const [selectedClass, setSelectedClass] = useState<string | undefined>(undefined);

  // Fetch permission matrix data
  const { data, isLoading } = useQuery({
    queryKey: ['permissionMatrix', selectedClass],
    queryFn: async () => {
      const response = await permissionsService.getPermissionMatrix(selectedClass);
      return response.data;
    },
  });

  // Permission categories for organization
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
    'Class & System Administration': [
      Permission.TOKEN_GENERATE,
      Permission.CLASS_ADMIN,
      Permission.CLASS_VIEW_ANALYTICS,
      Permission.SYSTEM_ADMIN,
      Permission.SYSTEM_VIEW_LOGS,
    ],
  };

  // Flatten all permissions in order
  const allPermissions = Object.values(permissionCategories).flat();

  const togglePermissionMutation = useMutation({
    mutationFn: async ({
      userId,
      permission,
      grant,
    }: {
      userId: string;
      permission: Permission;
      grant: boolean;
    }) => {
      if (grant) {
        const response = await permissionsService.bulkGrantPermissions(
          [userId],
          [permission],
          selectedClass
        );
        if (!response.success) {
          throw new Error(response.error || 'Failed to grant permission');
        }
      } else {
        const response = await permissionsService.bulkRevokePermissions(
          [userId],
          [permission],
          selectedClass
        );
        if (!response.success) {
          throw new Error(response.error || 'Failed to revoke permission');
        }
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['permissionMatrix'] });
      addToast('Permission updated successfully', 'success');
    },
    onError: (error: Error) => {
      addToast(error.message, 'error');
    },
  });

  const handleTogglePermission = (
    userId: string,
    permission: Permission,
    currentValue: boolean
  ) => {
    togglePermissionMutation.mutate({
      userId,
      permission,
      grant: !currentValue,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Permission Matrix</h1>
          <p className="mt-1 text-sm text-gray-500">
            Visual overview of user permissions across the system
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <select
            value={selectedClass || ''}
            onChange={(e) => setSelectedClass(e.target.value || undefined)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          >
            <option value="">All Classes</option>
            <option value="class-1">Class 1</option>
            <option value="class-2">Class 2</option>
          </select>
        </div>
      </div>

      {/* Legend */}
      <Card padding="sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              <div className="h-4 w-4 bg-green-100 border border-green-300 rounded flex items-center justify-center">
                <CheckIcon className="h-3 w-3 text-green-600" />
              </div>
              <span className="text-sm text-gray-600">Granted</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="h-4 w-4 bg-red-100 border border-red-300 rounded flex items-center justify-center">
                <XMarkIcon className="h-3 w-3 text-red-600" />
              </div>
              <span className="text-sm text-gray-600">Denied</span>
            </div>
          </div>
          <span className="text-sm text-gray-500">
            Click cells to toggle permissions
          </span>
        </div>
      </Card>

      {/* Permission Matrix */}
      <Card padding="none">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading permission matrix...</p>
          </div>
        ) : !data || data.users.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500">No users found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th
                    scope="col"
                    className="sticky left-0 z-20 px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-200"
                    style={{ minWidth: '200px' }}
                  >
                    User
                  </th>
                  {Object.entries(permissionCategories).map(([category, permissions]) => (
                    <th
                      key={category}
                      scope="col"
                      colSpan={permissions.length}
                      className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider border-l border-gray-300"
                    >
                      {category}
                    </th>
                  ))}
                </tr>
                <tr className="bg-gray-50">
                  <th className="sticky left-0 z-20 bg-gray-50 border-r border-gray-200"></th>
                  {allPermissions.map((permission) => (
                    <th
                      key={permission}
                      scope="col"
                      className="px-1 py-2 text-center"
                      style={{ minWidth: '60px' }}
                    >
                      <div
                        className="text-[10px] font-medium text-gray-500 transform -rotate-45 origin-center whitespace-nowrap"
                        title={permission}
                      >
                        {permission.split('.')[1]}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.users.map((user) => (
                  <tr key={user.userId} className="hover:bg-gray-50">
                    <td className="sticky left-0 z-10 px-6 py-4 whitespace-nowrap bg-white border-r border-gray-200">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {user.username}
                        </div>
                      </div>
                    </td>
                    {allPermissions.map((permission) => {
                      const hasPermission = user.permissions[permission];
                      return (
                        <td
                          key={permission}
                          className="px-1 py-4 text-center cursor-pointer hover:bg-gray-100"
                          onClick={() =>
                            handleTogglePermission(
                              user.userId,
                              permission,
                              hasPermission
                            )
                          }
                        >
                          <div
                            className={classNames(
                              'h-8 w-8 mx-auto rounded flex items-center justify-center border transition-colors',
                              hasPermission
                                ? 'bg-green-100 border-green-300 hover:bg-green-200'
                                : 'bg-red-100 border-red-300 hover:bg-red-200'
                            )}
                          >
                            {hasPermission ? (
                              <CheckIcon className="h-5 w-5 text-green-600" />
                            ) : (
                              <XMarkIcon className="h-5 w-5 text-red-600" />
                            )}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Statistics */}
      {data && data.users.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card padding="md">
            <h3 className="text-sm font-medium text-gray-500">Total Users</h3>
            <p className="mt-2 text-3xl font-semibold text-gray-900">
              {data.users.length}
            </p>
          </Card>
          <Card padding="md">
            <h3 className="text-sm font-medium text-gray-500">
              Total Permissions
            </h3>
            <p className="mt-2 text-3xl font-semibold text-gray-900">
              {allPermissions.length}
            </p>
          </Card>
          <Card padding="md">
            <h3 className="text-sm font-medium text-gray-500">
              Granted Permissions
            </h3>
            <p className="mt-2 text-3xl font-semibold text-gray-900">
              {data.users.reduce(
                (sum, user) =>
                  sum +
                  Object.values(user.permissions).filter((p) => p).length,
                0
              )}
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}
