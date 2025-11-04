import { Fragment } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Dialog, Transition } from '@headlessui/react';
import {
  HomeIcon,
  UsersIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  KeyIcon,
  XMarkIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { useUIStore } from '../../store/uiStore';
import { useAuth } from '../../hooks/useAuth';
import { Role, Permission } from '../../types';
import { classNames } from '../../utils/classNames';

interface NavItem {
  name: string;
  href: string;
  icon: any;
  requiredRole?: Role;
  requiredPermission?: Permission;
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  {
    name: 'Users',
    href: '/users',
    icon: UsersIcon,
    requiredPermission: Permission.USER_VIEW,
  },
  {
    name: 'Permissions',
    href: '/permissions',
    icon: ShieldCheckIcon,
    requiredPermission: Permission.USER_MANAGE,
  },
  {
    name: 'Role Templates',
    href: '/templates',
    icon: KeyIcon,
    requiredPermission: Permission.USER_MANAGE,
  },
  {
    name: 'Quizzes',
    href: '/quizzes',
    icon: DocumentTextIcon,
    requiredPermission: Permission.QUIZ_VIEW,
  },
  {
    name: 'Assignments',
    href: '/assignments',
    icon: ClipboardDocumentListIcon,
    requiredPermission: Permission.ASSIGNMENT_VIEW,
  },
  {
    name: 'Audit Logs',
    href: '/audit',
    icon: ChartBarIcon,
    requiredPermission: Permission.SYSTEM_VIEW_LOGS,
  },
];

function hasAccess(
  user: any,
  requiredRole?: Role,
  requiredPermission?: Permission
): boolean {
  if (!user) return false;
  if (requiredRole && !user.roles.includes(requiredRole)) return false;
  // TODO: Implement proper permission checking with backend
  return true;
}

export function Sidebar() {
  const location = useLocation();
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const { user } = useAuth();

  const filteredNavigation = navigation.filter((item) =>
    hasAccess(user, item.requiredRole, item.requiredPermission)
  );

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center h-16 flex-shrink-0 px-4 bg-primary-700">
        <h1 className="text-xl font-bold text-white">
          Informatics Classroom
        </h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {filteredNavigation.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={classNames(
                isActive
                  ? 'bg-primary-800 text-white'
                  : 'text-primary-100 hover:bg-primary-700 hover:text-white',
                'group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors'
              )}
              onClick={() => setSidebarOpen(false)}
            >
              <item.icon
                className={classNames(
                  isActive
                    ? 'text-white'
                    : 'text-primary-300 group-hover:text-white',
                  'mr-3 flex-shrink-0 h-6 w-6'
                )}
                aria-hidden="true"
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* User info */}
      {user && (
        <div className="flex-shrink-0 flex border-t border-primary-800 p-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="h-10 w-10 rounded-full bg-primary-500 flex items-center justify-center text-white font-semibold">
                {user.displayName?.charAt(0) || user.username?.charAt(0) || 'U'}
              </div>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-white">
                {user.displayName || user.username}
              </p>
              <p className="text-xs text-primary-200">
                {user.roles[0] || 'User'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Mobile sidebar */}
      <Transition.Root show={sidebarOpen} as={Fragment}>
        <Dialog
          as="div"
          className="relative z-40 lg:hidden"
          onClose={setSidebarOpen}
        >
          <Transition.Child
            as={Fragment}
            enter="transition-opacity ease-linear duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="transition-opacity ease-linear duration-300"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-gray-600 bg-opacity-75" />
          </Transition.Child>

          <div className="fixed inset-0 flex z-40">
            <Transition.Child
              as={Fragment}
              enter="transition ease-in-out duration-300 transform"
              enterFrom="-translate-x-full"
              enterTo="translate-x-0"
              leave="transition ease-in-out duration-300 transform"
              leaveFrom="translate-x-0"
              leaveTo="-translate-x-full"
            >
              <Dialog.Panel className="relative flex-1 flex flex-col max-w-xs w-full bg-primary-600">
                <Transition.Child
                  as={Fragment}
                  enter="ease-in-out duration-300"
                  enterFrom="opacity-0"
                  enterTo="opacity-100"
                  leave="ease-in-out duration-300"
                  leaveFrom="opacity-100"
                  leaveTo="opacity-0"
                >
                  <div className="absolute top-0 right-0 -mr-12 pt-2">
                    <button
                      type="button"
                      className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
                      onClick={() => setSidebarOpen(false)}
                    >
                      <span className="sr-only">Close sidebar</span>
                      <XMarkIcon
                        className="h-6 w-6 text-white"
                        aria-hidden="true"
                      />
                    </button>
                  </div>
                </Transition.Child>
                <SidebarContent />
              </Dialog.Panel>
            </Transition.Child>
            <div className="flex-shrink-0 w-14" aria-hidden="true">
              {/* Force sidebar to shrink to fit close icon */}
            </div>
          </div>
        </Dialog>
      </Transition.Root>

      {/* Static sidebar for desktop */}
      <div className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0">
        <div className="flex-1 flex flex-col min-h-0 bg-primary-600">
          <SidebarContent />
        </div>
      </div>
    </>
  );
}
