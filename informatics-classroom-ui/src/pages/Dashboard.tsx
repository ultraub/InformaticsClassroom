import { useAuth } from '../hooks/useAuth';
import { Card } from '../components/common';
import {
  UsersIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/react/24/outline';
import { classNames } from '../utils/classNames';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: any;
  change?: string;
  changeType?: 'increase' | 'decrease';
}

function StatCard({ title, value, icon: Icon, change, changeType }: StatCardProps) {
  return (
    <Card padding="md" hover>
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <div className="p-3 bg-primary-100 rounded-lg">
            <Icon className="h-6 w-6 text-primary-600" aria-hidden="true" />
          </div>
        </div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
            <dd className="flex items-baseline">
              <div className="text-2xl font-semibold text-gray-900">{value}</div>
              {change && (
                <div
                  className={classNames(
                    changeType === 'increase' ? 'text-green-600' : 'text-red-600',
                    'ml-2 flex items-baseline text-sm font-semibold'
                  )}
                >
                  {change}
                </div>
              )}
            </dd>
          </dl>
        </div>
      </div>
    </Card>
  );
}

export function Dashboard() {
  const { user } = useAuth();

  // Fetch real stats from API
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => {
      const response = await apiClient.get<{
        totalUsers: number;
        activeQuizzes: number;
        tokensGenerated: number;
        totalAnswers: number;
      }>('/api/dashboard/stats');
      return response.data;
    },
    staleTime: 60000, // Refetch after 1 minute
  });

  // Use real data from API
  const stats = [
    {
      title: 'Total Users',
      value: statsData?.totalUsers || 0,
      icon: UsersIcon,
    },
    {
      title: 'Active Quizzes',
      value: statsData?.activeQuizzes || 0,
      icon: DocumentTextIcon,
    },
    {
      title: 'Tokens Generated',
      value: statsData?.tokensGenerated || 0,
      icon: ShieldCheckIcon,
    },
    {
      title: 'Total Answers',
      value: statsData?.totalAnswers?.toLocaleString() || 0,
      icon: ClipboardDocumentListIcon,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.displayName || user?.username}!
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Here's what's happening with your classroom today.
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} />
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 gap-5">
        {/* Quick Actions */}
        <Card title="Quick Actions" padding="md">
          <div className="grid grid-cols-2 gap-4">
            <a
              href="/users"
              className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:shadow-sm transition-all"
            >
              <UsersIcon className="h-8 w-8 text-primary-600 mb-2" />
              <span className="text-sm font-medium text-gray-900">
                Manage Users
              </span>
            </a>
            <a
              href="/permissions"
              className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:shadow-sm transition-all"
            >
              <ShieldCheckIcon className="h-8 w-8 text-primary-600 mb-2" />
              <span className="text-sm font-medium text-gray-900">
                Set Permissions
              </span>
            </a>
            <a
              href="/quiz/create"
              className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:shadow-sm transition-all"
            >
              <DocumentTextIcon className="h-8 w-8 text-primary-600 mb-2" />
              <span className="text-sm font-medium text-gray-900">
                Create Quiz
              </span>
            </a>
          </div>
        </Card>
      </div>

      {/* System Status */}
      <Card title="System Status" padding="md">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="h-2 w-2 bg-green-500 rounded-full mr-3"></div>
              <span className="text-sm text-gray-700">Database Connection</span>
            </div>
            <span className="text-sm font-medium text-green-600">Healthy</span>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="h-2 w-2 bg-green-500 rounded-full mr-3"></div>
              <span className="text-sm text-gray-700">API Services</span>
            </div>
            <span className="text-sm font-medium text-green-600">Online</span>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="h-2 w-2 bg-yellow-500 rounded-full mr-3"></div>
              <span className="text-sm text-gray-700">Background Jobs</span>
            </div>
            <span className="text-sm font-medium text-yellow-600">2 Running</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
