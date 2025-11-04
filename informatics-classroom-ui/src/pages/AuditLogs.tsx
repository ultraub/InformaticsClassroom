import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FunnelIcon,
  ArrowDownTrayIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Input, Badge } from '../components/common';
import { auditService } from '../services/audit';
import { AuditAction, AuditLogFilter } from '../types';
import { classNames } from '../utils/classNames';

export function AuditLogs() {
  const [filters, setFilters] = useState<AuditLogFilter>({
    page: 1,
    pageSize: 25,
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAction, setSelectedAction] = useState<AuditAction | ''>('');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });

  // Fetch audit logs
  const { data, isLoading } = useQuery({
    queryKey: ['auditLogs', filters, searchTerm, selectedAction, dateRange],
    queryFn: async () => {
      const queryFilters: AuditLogFilter = {
        ...filters,
        action: selectedAction || undefined,
        startDate: dateRange.start || undefined,
        endDate: dateRange.end || undefined,
      };
      const response = await auditService.getAuditLogs(queryFilters);
      return response.data;
    },
  });

  const getActionBadgeVariant = (action: AuditAction) => {
    if (action.includes('created')) return 'success' as const;
    if (action.includes('deleted')) return 'danger' as const;
    if (action.includes('updated') || action.includes('modified'))
      return 'warning' as const;
    if (action.includes('login')) return 'info' as const;
    return 'secondary' as const;
  };

  const handleExport = async () => {
    try {
      const response = await auditService.exportAuditLogs(
        {
          ...filters,
          action: selectedAction || undefined,
          startDate: dateRange.start || undefined,
          endDate: dateRange.end || undefined,
        },
        'csv'
      );

      if (response.success && response.data) {
        // Create download link
        const blob = response.data as Blob;
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-logs-${new Date().toISOString()}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Trail</h1>
          <p className="mt-1 text-sm text-gray-500">
            Complete history of system actions and permission changes
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <Button
            variant="outline"
            icon={<ArrowDownTrayIcon className="h-5 w-5" />}
            onClick={handleExport}
          >
            Export CSV
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <div className="sm:col-span-2">
            <Input
              placeholder="Search by user or resource..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              icon={<MagnifyingGlassIcon className="h-5 w-5" />}
              iconPosition="left"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Action Type
            </label>
            <select
              value={selectedAction}
              onChange={(e) => setSelectedAction(e.target.value as AuditAction | '')}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            >
              <option value="">All Actions</option>
              <option value={AuditAction.USER_CREATED}>User Created</option>
              <option value={AuditAction.USER_UPDATED}>User Updated</option>
              <option value={AuditAction.USER_DELETED}>User Deleted</option>
              <option value={AuditAction.ROLE_ASSIGNED}>Role Assigned</option>
              <option value={AuditAction.ROLE_REVOKED}>Role Revoked</option>
              <option value={AuditAction.PERMISSION_GRANTED}>Permission Granted</option>
              <option value={AuditAction.PERMISSION_REVOKED}>Permission Revoked</option>
              <option value={AuditAction.LOGIN_SUCCESS}>Login Success</option>
              <option value={AuditAction.LOGIN_FAILED}>Login Failed</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date Range
            </label>
            <div className="flex space-x-2">
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) =>
                  setDateRange({ ...dateRange, start: e.target.value })
                }
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) =>
                  setDateRange({ ...dateRange, end: e.target.value })
                }
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Audit Log Table */}
      <Card padding="none">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading audit logs...</p>
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500">No audit logs found</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Timestamp
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      User
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Action
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Resource
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Details
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      IP Address
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {data.items.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {log.username}
                        </div>
                        <div className="text-sm text-gray-500">{log.userId}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Badge
                          variant={getActionBadgeVariant(log.action)}
                          size="sm"
                        >
                          {log.action.replace('.', ' ')}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {log.resourceType}
                        </div>
                        {log.resourceId && (
                          <div className="text-sm text-gray-500">
                            ID: {log.resourceId}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 max-w-xs">
                        <div className="text-sm text-gray-900 truncate">
                          {JSON.stringify(log.details)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {log.ipAddress || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {data.totalPages > 1 && (
              <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
                <div className="flex-1 flex justify-between sm:hidden">
                  <Button
                    variant="outline"
                    onClick={() =>
                      setFilters((prev) => ({
                        ...prev,
                        page: Math.max(1, (prev.page || 1) - 1),
                      }))
                    }
                    disabled={filters.page === 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() =>
                      setFilters((prev) => ({
                        ...prev,
                        page: Math.min(data.totalPages, (prev.page || 1) + 1),
                      }))
                    }
                    disabled={filters.page === data.totalPages}
                  >
                    Next
                  </Button>
                </div>
                <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm text-gray-700">
                      Showing{' '}
                      <span className="font-medium">
                        {((filters.page || 1) - 1) * (filters.pageSize || 25) + 1}
                      </span>{' '}
                      to{' '}
                      <span className="font-medium">
                        {Math.min(
                          (filters.page || 1) * (filters.pageSize || 25),
                          data.total
                        )}
                      </span>{' '}
                      of <span className="font-medium">{data.total}</span> results
                    </p>
                  </div>
                  <div>
                    <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                      <button
                        onClick={() =>
                          setFilters((prev) => ({
                            ...prev,
                            page: Math.max(1, (prev.page || 1) - 1),
                          }))
                        }
                        disabled={filters.page === 1}
                        className={classNames(
                          'relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium',
                          filters.page === 1
                            ? 'text-gray-300 cursor-not-allowed'
                            : 'text-gray-500 hover:bg-gray-50'
                        )}
                      >
                        Previous
                      </button>
                      <button
                        onClick={() =>
                          setFilters((prev) => ({
                            ...prev,
                            page: Math.min(data.totalPages, (prev.page || 1) + 1),
                          }))
                        }
                        disabled={filters.page === data.totalPages}
                        className={classNames(
                          'relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium',
                          filters.page === data.totalPages
                            ? 'text-gray-300 cursor-not-allowed'
                            : 'text-gray-500 hover:bg-gray-50'
                        )}
                      >
                        Next
                      </button>
                    </nav>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
