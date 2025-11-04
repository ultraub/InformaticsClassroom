import { apiClient } from './api';
import type {
  User,
  UserFilter,
  UserFormData,
  PaginatedResponse,
  UserPermissions,
  RoleAssignmentFormData,
} from '../types';

export const usersService = {
  // Get paginated list of users with filters
  getUsers: (filters?: UserFilter) =>
    apiClient.get<PaginatedResponse<User>>('/api/users', {
      params: filters,
    }),

  // Get single user by ID
  getUser: (userId: string) =>
    apiClient.get<User>(`/api/users/${userId}`),

  // Get current authenticated user
  getCurrentUser: () =>
    apiClient.get<User>('/api/users/me'),

  // Create new user
  createUser: (userData: UserFormData) =>
    apiClient.post<User>('/api/users', userData),

  // Update user
  updateUser: (userId: string, userData: Partial<UserFormData>) =>
    apiClient.put<User>(`/api/users/${userId}`, userData),

  // Delete user
  deleteUser: (userId: string) =>
    apiClient.delete<void>(`/api/users/${userId}`),

  // Get user permissions
  getUserPermissions: (userId: string) =>
    apiClient.get<UserPermissions>(`/api/users/${userId}/permissions`),

  // Assign role to user
  assignRole: (roleData: RoleAssignmentFormData) =>
    apiClient.post<void>('/api/users/assign-role', roleData),

  // Revoke role from user
  revokeRole: (userId: string, classId?: string) =>
    apiClient.post<void>('/api/users/revoke-role', { userId, classId }),

  // Bulk operations
  bulkUpdateUsers: (userIds: string[], updates: Partial<UserFormData>) =>
    apiClient.post<void>('/api/users/bulk-update', { userIds, updates }),

  bulkDeleteUsers: (userIds: string[]) =>
    apiClient.post<void>('/api/users/bulk-delete', { userIds }),
};
