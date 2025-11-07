import { Role, Permission } from '../types';

// Role hierarchy with inheritance
const ROLE_HIERARCHY: Record<string, string[]> = {
  admin: ['instructor', 'ta', 'student'],
  instructor: ['ta', 'student'],
  ta: ['student'],
  student: [],
};

// Permission mappings for roles
const ROLE_PERMISSIONS: Record<string, string[]> = {
  admin: ['*'], // Wildcard - all permissions
  instructor: [
    'quiz.view', 'quiz.create', 'quiz.modify', 'quiz.delete',
    'user.view', 'user.manage',
    'student.view', 'student.manage',
    'class.view_analytics', 'token.generate'
  ],
  ta: [
    'quiz.view', 'quiz.create', 'quiz.modify',
    'student.view',
    'class.view_analytics', 'token.generate'
  ],
  student: ['quiz.view', 'own_data.view'],
};

/**
 * Check if user has required role (with inheritance support)
 */
export function hasRole(user: any, requiredRole: Role): boolean {
  if (!user) return false;

  const userRoles = user.roles || [];

  // Admin always has all roles
  if (userRoles.includes(Role.ADMIN) || userRoles.includes('admin')) return true;

  // Check if user has the required role directly
  if (userRoles.includes(requiredRole)) return true;

  // Check if user has a role that inherits the required role
  for (const userRole of userRoles) {
    const inheritedRoles = ROLE_HIERARCHY[userRole] || [];
    if (inheritedRoles.includes(requiredRole)) return true;
  }

  // Check class-specific roles
  if (user.classRoles && typeof user.classRoles === 'object') {
    for (const classRole of Object.values(user.classRoles)) {
      if (classRole === requiredRole) return true;
      const inheritedRoles = ROLE_HIERARCHY[classRole as string] || [];
      if (inheritedRoles.includes(requiredRole)) return true;
    }
  }

  return false;
}

/**
 * Check if user has required permission
 */
export function hasPermission(user: any, requiredPermission: Permission): boolean {
  if (!user) return false;

  const userRoles = user.roles || [];

  // Check if any user role grants this permission
  for (const userRole of userRoles) {
    const rolePerms = ROLE_PERMISSIONS[userRole] || [];
    if (rolePerms.includes('*') || rolePerms.includes(requiredPermission)) {
      return true;
    }
  }

  // Check class-specific roles for permissions
  if (user.classRoles && typeof user.classRoles === 'object') {
    for (const classRole of Object.values(user.classRoles)) {
      const rolePerms = ROLE_PERMISSIONS[classRole as string] || [];
      if (rolePerms.includes('*') || rolePerms.includes(requiredPermission)) {
        return true;
      }
    }
  }

  return false;
}

/**
 * Check if user has access (role or permission)
 */
export function hasAccess(
  user: any,
  requiredRole?: Role,
  requiredPermission?: Permission
): boolean {
  if (!user) return false;

  // Check role if specified
  if (requiredRole && !hasRole(user, requiredRole)) {
    return false;
  }

  // Check permission if specified
  if (requiredPermission && !hasPermission(user, requiredPermission)) {
    return false;
  }

  return true;
}
