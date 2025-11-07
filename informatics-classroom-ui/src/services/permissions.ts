import { apiClient } from './api';
import type {
  Permission,
  PermissionCheck,
} from '../types';

export const permissionsService = {
  // Check if current user has permission
  checkPermission: (
    permission: Permission,
    classId?: string,
    resourceId?: string
  ) =>
    apiClient.post<PermissionCheck>('/api/permissions/check', {
      permission,
      classId,
      resourceId,
    }),

  // Get all available permissions
  getAllPermissions: () =>
    apiClient.get<Permission[]>('/api/permissions'),

  // Get permissions for a specific role
  getRolePermissions: (role: string) =>
    apiClient.get<Permission[]>(`/api/permissions/role/${role}`),

  // Get permissions for a specific class role
  getClassRolePermissions: (classRole: string) =>
    apiClient.get<Permission[]>(`/api/permissions/class-role/${classRole}`),

  // Bulk permission operations
  bulkGrantPermissions: (
    userIds: string[],
    permissions: Permission[],
    classId?: string
  ) =>
    apiClient.post<void>('/api/permissions/bulk-grant', {
      userIds,
      permissions,
      classId,
    }),

  bulkRevokePermissions: (
    userIds: string[],
    permissions: Permission[],
    classId?: string
  ) =>
    apiClient.post<void>('/api/permissions/bulk-revoke', {
      userIds,
      permissions,
      classId,
    }),

  // Permission matrix data
  getPermissionMatrix: (classId?: string) =>
    apiClient.get<{
      users: Array<{
        userId: string;
        username: string;
        permissions: Record<Permission, boolean>;
      }>;
    }>('/api/permissions/matrix', {
      params: { classId },
    }),
};
