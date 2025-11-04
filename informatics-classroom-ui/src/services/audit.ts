import { apiClient } from './api';
import type { AuditLogEntry, AuditLogFilter, PaginatedResponse } from '../types';

export const auditService = {
  // Get audit logs with filters
  getAuditLogs: (filters?: AuditLogFilter) =>
    apiClient.get<PaginatedResponse<AuditLogEntry>>('/api/audit/logs', {
      params: filters,
    }),

  // Get single audit log entry
  getAuditLogEntry: (entryId: string) =>
    apiClient.get<AuditLogEntry>(`/api/audit/logs/${entryId}`),

  // Get audit logs for specific user
  getUserAuditLogs: (userId: string, filters?: Omit<AuditLogFilter, 'userId'>) =>
    apiClient.get<PaginatedResponse<AuditLogEntry>>(
      `/api/audit/users/${userId}`,
      {
        params: filters,
      }
    ),

  // Get audit logs for specific resource
  getResourceAuditLogs: (resourceType: string, resourceId: string, filters?: AuditLogFilter) =>
    apiClient.get<PaginatedResponse<AuditLogEntry>>(
      `/api/audit/resources/${resourceType}/${resourceId}`,
      {
        params: filters,
      }
    ),

  // Export audit logs
  exportAuditLogs: (filters?: AuditLogFilter, format: 'csv' | 'json' = 'csv') =>
    apiClient.get<Blob>('/api/audit/export', {
      params: { ...filters, format },
      responseType: 'blob',
    }),

  // Get audit statistics
  getAuditStatistics: (startDate?: string, endDate?: string) =>
    apiClient.get<{
      totalActions: number;
      actionsByType: Record<string, number>;
      topUsers: Array<{ userId: string; username: string; actionCount: number }>;
      recentActivity: AuditLogEntry[];
    }>('/api/audit/statistics', {
      params: { startDate, endDate },
    }),
};
