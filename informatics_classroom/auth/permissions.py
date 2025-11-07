"""
Permission Management System

Implements role-based access control (RBAC) with:
- Role hierarchy and inheritance
- Class-scoped permissions
- Global admin override
"""

from typing import Dict, List, Set, Optional
from functools import wraps
from flask import session, jsonify

# Role-Permission Mappings with Inheritance
ROLE_PERMISSIONS = {
    'admin': {
        'global': True,  # Admin has all permissions everywhere
        'permissions': ['*']  # Wildcard - everything
    },
    'instructor': {
        'inherits': ['student'],
        'permissions': [
            'quiz.view', 'quiz.create', 'quiz.modify', 'quiz.delete',
            'student.view', 'student.manage',
            'class.manage_enrollment',
            'role.grant_ta',
            'class.add_instructor'
        ]
    },
    'ta': {
        'inherits': ['student'],
        'permissions': [
            'quiz.view', 'quiz.create', 'quiz.modify',
            'student.view'
        ]
    },
    'student': {
        'permissions': [
            'quiz.view', 'quiz.attempt',
            'own_data.view'
        ]
    }
}


def get_role_permissions_with_inheritance(role: str, visited: Optional[Set[str]] = None) -> List[str]:
    """
    Get all permissions for a role, including inherited permissions

    Args:
        role: Role name (e.g., 'instructor', 'student')
        visited: Set of already visited roles (prevents circular inheritance)

    Returns:
        List of permission strings
    """
    if visited is None:
        visited = set()

    if role in visited:
        return []  # Prevent circular inheritance

    visited.add(role)

    role_config = ROLE_PERMISSIONS.get(role, {})

    # Start with this role's direct permissions
    permissions = list(role_config.get('permissions', []))

    # Add inherited permissions
    for parent_role in role_config.get('inherits', []):
        parent_permissions = get_role_permissions_with_inheritance(parent_role, visited)
        permissions.extend(parent_permissions)

    # Remove duplicates while preserving order
    seen = set()
    unique_permissions = []
    for perm in permissions:
        if perm not in seen:
            seen.add(perm)
            unique_permissions.append(perm)

    return unique_permissions


def has_permission(user: Dict, permission: str, class_id: Optional[str] = None) -> bool:
    """
    Check if user has a specific permission

    Args:
        user: User document/dict with role/roles/classRoles
        permission: Permission string (e.g., 'quiz.create', 'student.manage')
        class_id: Optional class identifier for class-scoped permissions

    Returns:
        True if user has permission, False otherwise
    """
    if not user:
        return False

    # 1. Check if user is global admin (has all permissions everywhere)
    user_roles = user.get('roles', [])
    if isinstance(user_roles, str):
        user_roles = [user_roles]

    # Normalize roles to lowercase
    user_roles = [r.lower() for r in user_roles if r]

    if 'admin' in user_roles:
        return True

    # Also check legacy 'role' field (case-insensitive)
    legacy_role = user.get('role', '').lower()
    if legacy_role == 'admin':
        return True

    # 2. If class-scoped, check classRoles
    if class_id:
        class_roles = user.get('classRoles', {})
        if isinstance(class_roles, dict):
            class_role = class_roles.get(class_id, '').lower()
            if class_role:
                # Treat 'user' as 'student'
                if class_role == 'user':
                    class_role = 'student'
                role_permissions = get_role_permissions_with_inheritance(class_role)
                if '*' in role_permissions or permission in role_permissions:
                    return True

        # Backward compatibility: if no classRole but user has access to class, default to student
        if not class_roles:
            access = user.get('access', [])
            if class_id in access:
                role_permissions = get_role_permissions_with_inheritance('student')
                if '*' in role_permissions or permission in role_permissions:
                    return True

    # 3. Check global role (backward compatibility)
    if legacy_role and legacy_role != 'user':  # 'user' is legacy default, treat as student
        role_permissions = get_role_permissions_with_inheritance(legacy_role)
        if '*' in role_permissions or permission in role_permissions:
            return True

    # 4. Check if any of user's global roles grant this permission
    for role in user_roles:
        if role != 'admin':  # Already checked admin above
            # Treat 'user' as 'student'
            if role == 'user':
                role = 'student'
            role_permissions = get_role_permissions_with_inheritance(role)
            if '*' in role_permissions or permission in role_permissions:
                return True

    return False


def get_user_classes(user: Dict) -> List[str]:
    """
    Get all classes user has access to

    Args:
        user: User document/dict

    Returns:
        List of class identifiers
    """
    if not user:
        return []

    # Combine classes from classRoles and access array
    classes = set()

    # From classRoles
    class_roles = user.get('classRoles', {})
    if isinstance(class_roles, dict):
        classes.update(class_roles.keys())

    # From access array (backward compatibility)
    access = user.get('access', [])
    if isinstance(access, list):
        classes.update(access)

    return list(classes)


def require_permission(permission: str, class_id_param: Optional[str] = None):
    """
    Decorator to require a specific permission for a route

    Args:
        permission: Required permission string
        class_id_param: Optional name of request parameter containing class_id

    Usage:
        @require_permission('quiz.create', class_id_param='class_id')
        def create_quiz():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request

            # Get user from session
            user = session.get('user')
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'Not authenticated'
                }), 401

            # Get class_id from request if specified
            class_id = None
            if class_id_param:
                class_id = request.args.get(class_id_param) or request.json.get(class_id_param) if request.is_json else None

            # Check permission
            if not has_permission(user, permission, class_id):
                return jsonify({
                    'success': False,
                    'error': f'Permission denied: {permission}'
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator
