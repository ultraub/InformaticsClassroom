"""
InformaticsClassroom Permissions Module

This module implements a comprehensive RBAC (Role-Based Access Control) system
with support for:
- Granular permission definitions
- Class-specific role assignments
- Permission hierarchies
- Centralized permission management
"""

from .service import PermissionService
from .decorators import require_permission, require_role, require_class_role
from .models import Permission, Role, ClassRole

__all__ = [
    'PermissionService',
    'require_permission',
    'require_role',
    'require_class_role',
    'Permission',
    'Role',
    'ClassRole'
]
