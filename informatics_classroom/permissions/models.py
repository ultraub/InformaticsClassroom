"""
Permission System Data Models

Defines the core data structures for the RBAC system including:
- Permission definitions
- Role definitions
- Class-specific role mappings
"""

from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass


class PermissionLevel(Enum):
    """Permission hierarchy levels"""
    READ = 1
    WRITE = 2
    DELETE = 3
    ADMIN = 4


class Permission(Enum):
    """
    Granular permission definitions for the system

    Format: RESOURCE_ACTION
    Examples: QUIZ_CREATE, USER_MANAGE, CLASS_ADMIN
    """

    # Quiz permissions
    QUIZ_VIEW = "quiz.view"
    QUIZ_CREATE = "quiz.create"
    QUIZ_MODIFY = "quiz.modify"
    QUIZ_DELETE = "quiz.delete"
    QUIZ_ADMIN = "quiz.admin"

    # User management permissions
    USER_VIEW = "user.view"
    USER_MANAGE = "user.manage"
    USER_ASSIGN_ROLE = "user.assign_role"
    USER_ADMIN = "user.admin"

    # Class permissions
    CLASS_VIEW = "class.view"
    CLASS_MANAGE = "class.manage"
    CLASS_ENROLL = "class.enroll"
    CLASS_ADMIN = "class.admin"

    # Token permissions
    TOKEN_GENERATE = "token.generate"
    TOKEN_MANAGE = "token.manage"

    # Analytics permissions
    ANALYTICS_VIEW = "analytics.view"
    ANALYTICS_EXPORT = "analytics.export"

    # System permissions
    SYSTEM_ADMIN = "system.admin"
    SYSTEM_AUDIT = "system.audit"


class Role(Enum):
    """
    Global role definitions

    Each role has a set of default permissions
    """
    ADMIN = "Admin"
    INSTRUCTOR = "Instructor"
    STUDENT = "Student"
    GUEST = "Guest"


class ClassRole(Enum):
    """
    Class-specific role definitions

    These roles are assigned per class, allowing users to have
    different roles in different classes
    """
    CLASS_ADMIN = "class_admin"
    CLASS_INSTRUCTOR = "class_instructor"
    CLASS_TA = "class_ta"  # Teaching Assistant
    CLASS_STUDENT = "class_student"
    CLASS_AUDITOR = "class_auditor"  # View-only access


@dataclass
class RolePermissions:
    """Maps roles to their default permissions"""
    role: Role
    permissions: List[Permission]
    inherits_from: Optional[Role] = None


# Define default permission mappings for each role
ROLE_PERMISSIONS_MAP = {
    Role.ADMIN: RolePermissions(
        role=Role.ADMIN,
        permissions=[
            Permission.SYSTEM_ADMIN,
            Permission.SYSTEM_AUDIT,
            Permission.USER_ADMIN,
            Permission.CLASS_ADMIN,
            Permission.QUIZ_ADMIN,
            Permission.TOKEN_MANAGE,
            Permission.ASSIGNMENT_EXPORT,
        ],
        inherits_from=None  # Admins have all permissions
    ),

    Role.INSTRUCTOR: RolePermissions(
        role=Role.INSTRUCTOR,
        permissions=[
            Permission.QUIZ_VIEW,
            Permission.QUIZ_CREATE,
            Permission.QUIZ_MODIFY,  # Own quizzes only
            Permission.QUIZ_DELETE,
            Permission.CLASS_VIEW,
            Permission.TOKEN_GENERATE,
            Permission.ANALYTICS_VIEW,
        ],
        inherits_from=None
    ),

    Role.STUDENT: RolePermissions(
        role=Role.STUDENT,
        permissions=[
            Permission.QUIZ_VIEW,  # Assigned quizzes only
            Permission.CLASS_VIEW,  # Enrolled classes only
        ],
        inherits_from=None
    ),

    Role.GUEST: RolePermissions(
        role=Role.GUEST,
        permissions=[],
        inherits_from=None
    ),
}


# Define class-specific role permission mappings
CLASS_ROLE_PERMISSIONS_MAP = {
    ClassRole.CLASS_ADMIN: [
        Permission.CLASS_ADMIN,
        Permission.CLASS_MANAGE,
        Permission.CLASS_ENROLL,
        Permission.QUIZ_ADMIN,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
    ],

    ClassRole.CLASS_INSTRUCTOR: [
        Permission.CLASS_VIEW,
        Permission.QUIZ_VIEW,
        Permission.QUIZ_CREATE,
        Permission.QUIZ_MODIFY,
        Permission.QUIZ_DELETE,
        Permission.ANALYTICS_VIEW,
        Permission.TOKEN_GENERATE,
    ],

    ClassRole.CLASS_TA: [
        Permission.CLASS_VIEW,
        Permission.QUIZ_VIEW,
        Permission.QUIZ_CREATE,
        Permission.QUIZ_MODIFY,
        Permission.ANALYTICS_VIEW,
    ],

    ClassRole.CLASS_STUDENT: [
        Permission.CLASS_VIEW,
        Permission.QUIZ_VIEW,  # Assigned quizzes only
    ],

    ClassRole.CLASS_AUDITOR: [
        Permission.CLASS_VIEW,
    ],
}


@dataclass
class PermissionCheck:
    """
    Result of a permission check

    Includes detailed information about why a permission was granted or denied
    """
    has_permission: bool
    reason: str
    granted_by: Optional[str] = None  # "global_role", "class_role", "direct_permission"
    role: Optional[str] = None
    class_context: Optional[str] = None


def get_permissions_for_role(role: Role) -> List[Permission]:
    """Get all permissions for a given role"""
    if role not in ROLE_PERMISSIONS_MAP:
        return []

    role_perms = ROLE_PERMISSIONS_MAP[role]
    permissions = list(role_perms.permissions)

    # If role inherits from another, include those permissions
    if role_perms.inherits_from:
        parent_perms = get_permissions_for_role(role_perms.inherits_from)
        permissions.extend(parent_perms)

    return permissions


def get_permissions_for_class_role(class_role: ClassRole) -> List[Permission]:
    """Get all permissions for a given class role"""
    return CLASS_ROLE_PERMISSIONS_MAP.get(class_role, [])


def permission_implies(permission: Permission, required: Permission) -> bool:
    """
    Check if one permission implies another

    For example, QUIZ_ADMIN implies QUIZ_MODIFY, QUIZ_CREATE, etc.
    """

    # Admin permissions imply all related permissions
    if permission == Permission.SYSTEM_ADMIN:
        return True

    if permission == Permission.QUIZ_ADMIN:
        return required in [
            Permission.QUIZ_VIEW,
            Permission.QUIZ_CREATE,
            Permission.QUIZ_MODIFY,
            Permission.QUIZ_DELETE,
        ]

    if permission == Permission.CLASS_ADMIN:
        return required in [
            Permission.CLASS_VIEW,
            Permission.CLASS_MANAGE,
            Permission.CLASS_ENROLL,
        ]

    if permission == Permission.USER_ADMIN:
        return required in [
            Permission.USER_VIEW,
            Permission.USER_MANAGE,
            Permission.USER_ASSIGN_ROLE,
        ]

    # Direct match
    return permission == required
