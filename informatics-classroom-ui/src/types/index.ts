// User types
export interface User {
  id: string;
  username: string;
  email: string;
  displayName: string;
  roles: Role[];
  classRoles?: Record<string, string>; // Old format: Map of class_id -> role (e.g., {"pmap": "instructor", "omop": "student"})
  class_memberships?: Array<{class_id: string; role: string; assigned_at?: string; assigned_by?: string}>; // New format
  permissions?: Permission[]; // Direct permissions assigned to user
  isActive: boolean;
  lastLogin?: string;
  createdAt: string;
}

// Role types matching backend enums with inheritance
export const Role = {
  ADMIN: 'admin',
  INSTRUCTOR: 'instructor',
  TA: 'ta',
  STUDENT: 'student'
} as const;
export type Role = typeof Role[keyof typeof Role];

export const ClassRole = {
  CLASS_ADMIN: 'class_admin',
  CLASS_INSTRUCTOR: 'class_instructor',
  CLASS_TA: 'class_ta',
  CLASS_STUDENT: 'class_student',
  CLASS_VIEWER: 'class_viewer'
} as const;
export type ClassRole = typeof ClassRole[keyof typeof ClassRole];

// Permission types
export const Permission = {
  // Quiz Management (quizzes and assignments are the same thing)
  QUIZ_VIEW: 'quiz.view',
  QUIZ_CREATE: 'quiz.create',
  QUIZ_MODIFY: 'quiz.modify',
  QUIZ_DELETE: 'quiz.delete',

  // User Management
  USER_MANAGE: 'user.manage',
  USER_VIEW: 'user.view',

  // Class Management
  TOKEN_GENERATE: 'token.generate',
  CLASS_ADMIN: 'class.admin',
  CLASS_VIEW_ANALYTICS: 'class.view_analytics',

  // System Administration
  SYSTEM_ADMIN: 'system.admin',
  SYSTEM_VIEW_LOGS: 'system.view_logs'
} as const;
export type Permission = typeof Permission[keyof typeof Permission];

export interface PermissionCheck {
  allowed: boolean;
  reason?: string;
  requiredRole?: string;
}

// Class types
export interface Class {
  id: string;
  name: string;
  description?: string;
  instructors: string[];
  students: string[];
  tas: string[];
  createdAt: string;
  isActive: boolean;
}

export interface ClassMembership {
  classId: string;
  className: string;
  role: ClassRole;
  joinedAt: string;
}

// Permission assignment types
export interface UserPermissions {
  userId: string;
  username: string;
  globalRole: Role;
  classPermissions: ClassPermission[];
  allPermissions: Permission[];
}

export interface ClassPermission {
  classId: string;
  className: string;
  role: ClassRole;
  permissions: Permission[];
}

// Role template types
export interface RoleTemplate {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
  isSystem: boolean;
  createdBy?: string;
  createdAt: string;
}

// Audit log types
export interface AuditLogEntry {
  id: string;
  timestamp: string;
  userId: string;
  username: string;
  action: AuditAction;
  resourceType: string;
  resourceId?: string;
  details: Record<string, any>;
  ipAddress?: string;
  userAgent?: string;
}

export const AuditAction = {
  USER_CREATED: 'user.created',
  USER_UPDATED: 'user.updated',
  USER_DELETED: 'user.deleted',
  ROLE_ASSIGNED: 'role.assigned',
  ROLE_REVOKED: 'role.revoked',
  PERMISSION_GRANTED: 'permission.granted',
  PERMISSION_REVOKED: 'permission.revoked',
  CLASS_CREATED: 'class.created',
  CLASS_UPDATED: 'class.updated',
  CLASS_DELETED: 'class.deleted',
  QUIZ_CREATED: 'quiz.created',
  QUIZ_MODIFIED: 'quiz.modified',
  QUIZ_DELETED: 'quiz.deleted',
  LOGIN_SUCCESS: 'login.success',
  LOGIN_FAILED: 'login.failed',
  LOGOUT: 'logout'
} as const;
export type AuditAction = typeof AuditAction[keyof typeof AuditAction];

// API response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Form types
export interface UserFormData {
  username: string;
  email: string;
  displayName: string;
  role: Role;
  isActive: boolean;
}

export interface RoleAssignmentFormData {
  userId: string;
  classId?: string;
  role: Role | ClassRole;
  permissions?: Permission[];
}

// Filter and search types
export interface UserFilter {
  search?: string;
  role?: Role;
  classId?: string;
  isActive?: boolean;
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface AuditLogFilter {
  userId?: string;
  action?: AuditAction;
  resourceType?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  pageSize?: number;
}
