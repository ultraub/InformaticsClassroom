import { useAuth } from '../hooks/useAuth';
import { Card } from '../components/common';
import {
  UsersIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/react/24/outline';
import { classNames } from '../utils/classNames';

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

  // Mock data - will be replaced with real API calls
  const stats = [
    {
      title: 'Total Users',
      value: 127,
      icon: UsersIcon,
      change: '+12%',
      changeType: 'increase' as const,
    },
    {
      title: 'Active Permissions',
      value: 45,
      icon: ShieldCheckIcon,
      change: '+5%',
      changeType: 'increase' as const,
    },
    {
      title: 'Quizzes',
      value: 23,
      icon: DocumentTextIcon,
      change: '+3%',
      changeType: 'increase' as const,
    },
    {
      title: 'Assignments',
      value: 18,
      icon: ClipboardDocumentListIcon,
      change: '-2%',
      changeType: 'decrease' as const,
    },
  ];

  const recentActivity = [
    {
      id: 1,
      user: 'John Doe',
      action: 'Updated permissions',
      target: 'User: jane.smith',
      time: '2 minutes ago',
    },
    {
      id: 2,
      user: 'Jane Smith',
      action: 'Created quiz',
      target: 'Quiz: Introduction to Python',
      time: '15 minutes ago',
    },
    {
      id: 3,
      user: 'Admin User',
      action: 'Assigned role',
      target: 'User: mike.johnson → Instructor',
      time: '1 hour ago',
    },
    {
      id: 4,
      user: 'Sarah Wilson',
      action: 'Modified assignment',
      target: 'Assignment: Week 1 Homework',
      time: '2 hours ago',
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

      {/* Two column layout */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Recent Activity */}
        <Card title="Recent Activity" padding="none">
          <div className="divide-y divide-gray-200">
            {recentActivity.map((activity) => (
              <div key={activity.id} className="px-6 py-4 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {activity.user}
                    </p>
                    <p className="text-sm text-gray-500">
                      {activity.action} • {activity.target}
                    </p>
                  </div>
                  <div className="ml-4 flex-shrink-0">
                    <span className="text-xs text-gray-400">{activity.time}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
            <a
              href="/audit"
              className="text-sm font-medium text-primary-600 hover:text-primary-500"
            >
              View all activity →
            </a>
          </div>
        </Card>

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
              href="/quizzes"
              className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:shadow-sm transition-all"
            >
              <DocumentTextIcon className="h-8 w-8 text-primary-600 mb-2" />
              <span className="text-sm font-medium text-gray-900">
                Create Quiz
              </span>
            </a>
            <a
              href="/templates"
              className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:shadow-sm transition-all"
            >
              <ShieldCheckIcon className="h-8 w-8 text-primary-600 mb-2" />
              <span className="text-sm font-medium text-gray-900">
                Role Templates
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
