"""
Class-level authorization module for granular permission management.

This module provides decorators and helper functions for enforcing class-specific
permissions and roles, ensuring users can only access resources in classes where
they have appropriate permissions.
"""

from functools import wraps
from flask import request, jsonify
from typing import Optional, List, Dict, Any, Union


# Permission definitions for each class-level role
ROLE_PERMISSIONS = {
    'instructor': [
        'manage_quizzes',      # Create, edit, delete quizzes
        'manage_tokens',        # Generate access tokens
        'view_analytics',       # View detailed analytics and grades
        'manage_members',       # Add/remove class members
        'take_quizzes',         # Can take quizzes (for testing)
    ],
    'ta': [
        'manage_quizzes',       # Create, edit (but not delete) quizzes
        'manage_tokens',        # Generate access tokens
        'view_analytics',       # View detailed analytics and grades
        'take_quizzes',         # Can take quizzes
    ],
    'student': [
        'take_quizzes',         # Take quizzes
        'view_progress',        # View own progress
    ],
}


def get_user_class_role(user: Dict[str, Any], class_id: str) -> Optional[str]:
    """
    Get user's role for a specific class.

    Supports both new class_memberships structure and legacy accessible_classes.

    Args:
        user: User object from request.jwt_user
        class_id: Class identifier

    Returns:
        Role string ('instructor', 'ta', 'grader', 'student') or None if no access
    """
    # Check if user is global admin
    if 'admin' in user.get('roles', []):
        return 'instructor'  # Admins have instructor-level access to all classes

    # Try new class_memberships structure first
    class_memberships = user.get('class_memberships', {})
    if isinstance(class_memberships, dict) and class_id in class_memberships:
        membership = class_memberships[class_id]
        if isinstance(membership, dict):
            return membership.get('role')
        # Handle legacy format where classRoles is just {class: role_string}
        return membership

    # Try classRoles (intermediate format)
    class_roles = user.get('classRoles', {})
    if isinstance(class_roles, dict) and class_id in class_roles:
        return class_roles[class_id]

    # Fallback to old accessible_classes structure
    accessible_classes = user.get('accessible_classes', [])
    if class_id in accessible_classes:
        # Infer role from global role
        global_role = user.get('role', '').lower()
        if global_role in ['admin', 'instructor']:
            return 'instructor'
        elif global_role in ['ta']:
            return 'ta'
        return 'student'

    return None  # No access to this class


def get_role_permissions(role: str) -> List[str]:
    """
    Get list of permissions for a given role.

    Args:
        role: Role name (instructor, ta, grader, student)

    Returns:
        List of permission strings
    """
    return ROLE_PERMISSIONS.get(role.lower(), [])


def user_has_class_permission(user: Dict[str, Any], class_id: str, permission: str) -> bool:
    """
    Check if user has a specific permission for a class.

    Args:
        user: User object from request.jwt_user
        class_id: Class identifier
        permission: Permission to check (e.g., 'manage_quizzes', 'grade')

    Returns:
        True if user has permission, False otherwise
    """
    # Global admins have all permissions
    if 'admin' in user.get('roles', []):
        return True

    # Get user's role in this class
    role = get_user_class_role(user, class_id)
    if not role:
        return False

    # Check if role has this permission
    permissions = get_role_permissions(role)
    return permission in permissions


def get_user_managed_classes(user: Dict[str, Any], min_role: str = 'student') -> List[str]:
    """
    Get all classes where user has at least the specified role level.

    Role hierarchy: instructor > ta > grader > student

    Args:
        user: User object from request.jwt_user
        min_role: Minimum role level required

    Returns:
        List of class IDs
    """
    role_hierarchy = {
        'instructor': 3,
        'ta': 2,
        'student': 1,
    }

    min_level = role_hierarchy.get(min_role.lower(), 0)
    managed_classes = []

    # Global admins manage all classes (would need to query database for full list)
    if 'admin' in user.get('roles', []):
        # For admins, we need to return their explicitly assigned classes
        # or indicate they have access to all (handled by calling code)
        pass

    # Check class_memberships
    class_memberships = user.get('class_memberships', {})
    if isinstance(class_memberships, dict):
        for class_id, membership in class_memberships.items():
            if isinstance(membership, dict):
                role = membership.get('role', '').lower()
            else:
                role = membership.lower() if membership else ''

            role_level = role_hierarchy.get(role, 0)
            if role_level >= min_level:
                managed_classes.append(class_id)
        return managed_classes

    # Fallback to classRoles
    class_roles = user.get('classRoles', {})
    if isinstance(class_roles, dict):
        for class_id, role in class_roles.items():
            role_level = role_hierarchy.get(role.lower(), 0)
            if role_level >= min_level:
                managed_classes.append(class_id)
        return managed_classes

    # No accessible_classes fallback - too insecure
    # Users must have explicit class-level roles in class_memberships or classRoles
    return []


def extract_class_from_request(class_source: str) -> Optional[str]:
    """
    Extract class ID from various request sources.

    Args:
        class_source: Source specification (e.g., 'body.class', 'args.class_id', 'quiz_id')

    Returns:
        Class ID or None if not found
    """
    parts = class_source.split('.')
    source_type = parts[0]

    if source_type == 'body':
        # Get from request body JSON
        data = request.get_json() or {}
        if len(parts) > 1:
            return data.get(parts[1])
        return data.get('class')

    elif source_type == 'args':
        # Get from query parameters
        if len(parts) > 1:
            return request.args.get(parts[1])
        return request.args.get('class')

    elif source_type == 'view_args':
        # Get from route parameters
        if len(parts) > 1:
            return request.view_args.get(parts[1])
        return request.view_args.get('class_id')

    elif source_type == 'quiz':
        # Extract from quiz lookup
        # This is handled specially in require_quiz_permission decorator
        pass

    return None


def require_class_role(required_roles: Union[str, List[str]], class_from: str = 'body.class'):
    """
    Decorator to require specific class-level role(s).

    Validates that the user has one of the required roles for the specific class
    being accessed, not just globally.

    Args:
        required_roles: Single role or list of acceptable roles (e.g., 'instructor' or ['instructor', 'ta'])
        class_from: Where to extract class ID from (e.g., 'body.class', 'args.class_id', 'view_args.class')

    Usage:
        @app.route('/api/quizzes/create', methods=['POST'])
        @require_jwt_token
        @require_class_role('instructor', class_from='body.class')
        def create_quiz():
            # Only instructors of THIS class can create
    """
    if isinstance(required_roles, str):
        required_roles = [required_roles]

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Ensure authentication
            if not hasattr(request, 'jwt_user'):
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Must use @require_jwt_token before @require_class_role'
                }), 401

            user = request.jwt_user

            # Global admins bypass class-level checks
            if 'admin' in user.get('roles', []):
                return f(*args, **kwargs)

            # Extract class from request
            class_id = extract_class_from_request(class_from)
            if not class_id:
                return jsonify({
                    'error': 'Invalid request',
                    'message': f'Could not determine class from {class_from}'
                }), 400

            # Get user's role in this class
            user_role = get_user_class_role(user, class_id)
            if not user_role:
                return jsonify({
                    'error': 'Access denied',
                    'message': f'You do not have access to class {class_id}'
                }), 403

            # Check if user's role is sufficient
            required_roles_lower = [r.lower() for r in required_roles]
            if user_role.lower() not in required_roles_lower:
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'Required role: {" or ".join(required_roles)}. Your role: {user_role}'
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_class_permission(permission: str, class_from: str = 'body.class'):
    """
    Decorator to require specific permission for a class.

    More flexible than require_class_role - checks if user has the specific
    permission regardless of their exact role.

    Args:
        permission: Permission required (e.g., 'manage_quizzes', 'grade', 'view_analytics')
        class_from: Where to extract class ID from

    Usage:
        @app.route('/api/assignments/analyze', methods=['POST'])
        @require_jwt_token
        @require_class_permission('view_analytics', class_from='body.class_name')
        def analyze_assignment():
            # Only users with analytics permission for THIS class
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Ensure authentication
            if not hasattr(request, 'jwt_user'):
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Must use @require_jwt_token before @require_class_permission'
                }), 401

            user = request.jwt_user

            # Global admins bypass permission checks
            if 'admin' in user.get('roles', []):
                return f(*args, **kwargs)

            # Extract class from request
            class_id = extract_class_from_request(class_from)
            if not class_id:
                return jsonify({
                    'error': 'Invalid request',
                    'message': f'Could not determine class from {class_from}'
                }), 400

            # Check permission
            if not user_has_class_permission(user, class_id, permission):
                user_role = get_user_class_role(user, class_id)
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'Permission "{permission}" required for class {class_id}. Your role: {user_role or "none"}'
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def assign_class_role(user_id: str, class_id: str, role: str, assigned_by: str = None) -> Dict[str, Any]:
    """
    Assign a user to a class with a specific role.

    Args:
        user_id: User identifier
        class_id: Class identifier
        role: Role to assign (instructor, ta, grader, student)
        assigned_by: User ID of person making the assignment (for audit)

    Returns:
        Result dictionary with success status

    Raises:
        ValueError: If role is invalid
    """
    # Validate role
    valid_roles = ['instructor', 'ta', 'grader', 'student']
    if role.lower() not in valid_roles:
        raise ValueError(f'Invalid role: {role}. Must be one of {valid_roles}')

    from informatics_classroom.database.factory import get_database_adapter
    import datetime

    db = get_database_adapter()

    # Get user
    user = db.get('users', user_id)
    if not user:
        raise ValueError(f'User {user_id} not found')

    # Initialize class_memberships if needed
    if 'class_memberships' not in user:
        user['class_memberships'] = {}

    # Assign role
    user['class_memberships'][class_id] = {
        'role': role.lower(),
        'assigned_at': datetime.datetime.utcnow().isoformat(),
        'assigned_by': assigned_by
    }

    # Update classRoles for backward compatibility
    if 'classRoles' not in user:
        user['classRoles'] = {}
    user['classRoles'][class_id] = role.lower()

    # Update accessible_classes for backward compatibility
    if 'accessible_classes' not in user:
        user['accessible_classes'] = []
    if class_id not in user['accessible_classes']:
        user['accessible_classes'].append(class_id)

    # Save user
    db.upsert('users', user)

    return {
        'success': True,
        'user_id': user_id,
        'class_id': class_id,
        'role': role.lower()
    }


def remove_class_role(user_id: str, class_id: str) -> Dict[str, Any]:
    """
    Remove a user from a class.

    Args:
        user_id: User identifier
        class_id: Class identifier

    Returns:
        Result dictionary with success status
    """
    from informatics_classroom.database.factory import get_database_adapter

    db = get_database_adapter()

    # Get user
    user = db.get('users', user_id)
    if not user:
        raise ValueError(f'User {user_id} not found')

    # Remove from class_memberships
    if 'class_memberships' in user and class_id in user['class_memberships']:
        del user['class_memberships'][class_id]

    # Remove from classRoles (backward compatibility)
    if 'classRoles' in user and class_id in user['classRoles']:
        del user['classRoles'][class_id]

    # Remove from accessible_classes (backward compatibility)
    if 'accessible_classes' in user and class_id in user['accessible_classes']:
        user['accessible_classes'].remove(class_id)

    # Save user
    db.upsert('users', user)

    return {
        'success': True,
        'user_id': user_id,
        'class_id': class_id,
        'action': 'removed'
    }


def update_class_role(user_id: str, class_id: str, new_role: str, updated_by: str = None) -> Dict[str, Any]:
    """
    Update a user's role in a class.

    Args:
        user_id: User identifier
        class_id: Class identifier
        new_role: New role to assign
        updated_by: User ID of person making the update (for audit)

    Returns:
        Result dictionary with success status

    Raises:
        ValueError: If role is invalid or user not in class
    """
    from informatics_classroom.database.factory import get_database_adapter
    import datetime

    # Validate role
    valid_roles = ['instructor', 'ta', 'grader', 'student']
    if new_role.lower() not in valid_roles:
        raise ValueError(f'Invalid role: {new_role}. Must be one of {valid_roles}')

    db = get_database_adapter()

    # Get user
    user = db.get('users', user_id)
    if not user:
        raise ValueError(f'User {user_id} not found')

    # Check if user is in class
    if 'class_memberships' not in user or class_id not in user['class_memberships']:
        raise ValueError(f'User {user_id} is not a member of class {class_id}')

    # Update role
    old_role = user['class_memberships'][class_id].get('role')
    user['class_memberships'][class_id]['role'] = new_role.lower()
    user['class_memberships'][class_id]['updated_at'] = datetime.datetime.utcnow().isoformat()
    user['class_memberships'][class_id]['updated_by'] = updated_by

    # Update classRoles (backward compatibility)
    if 'classRoles' in user:
        user['classRoles'][class_id] = new_role.lower()

    # Save user
    db.upsert('users', user)

    return {
        'success': True,
        'user_id': user_id,
        'class_id': class_id,
        'old_role': old_role,
        'new_role': new_role.lower()
    }


def get_class_members(class_id: str) -> List[Dict[str, Any]]:
    """
    Get all members of a class.

    Args:
        class_id: Class identifier

    Returns:
        List of member dictionaries with user info and role
    """
    from informatics_classroom.database.factory import get_database_adapter

    db = get_database_adapter()

    # Get all users
    all_users = db.query('users', filters={})

    members = []
    for user in all_users:
        # Check class_memberships (new format: list of objects)
        class_memberships = user.get('class_memberships', [])

        # Handle list format: [{"class_id": "cda", "role": "instructor"}, ...]
        if isinstance(class_memberships, list):
            for membership in class_memberships:
                if isinstance(membership, dict) and membership.get('class_id') == class_id:
                    members.append({
                        'user_id': user.get('id'),
                        'email': user.get('email'),
                        'display_name': user.get('display_name', user.get('name', user.get('id'))),
                        'role': membership.get('role'),
                        'assigned_at': membership.get('assigned_at'),
                        'assigned_by': membership.get('assigned_by')
                    })
                    break
            else:
                # Not found in list format, try classRoles fallback
                class_roles = user.get('classRoles', {})
                if class_id in class_roles:
                    members.append({
                        'user_id': user.get('id'),
                        'email': user.get('email'),
                        'display_name': user.get('display_name', user.get('name', user.get('id'))),
                        'role': class_roles[class_id],
                        'assigned_at': None,
                        'assigned_by': None
                    })

        # Handle old dict format (backward compatibility): {"cda": {"role": "instructor"}, ...}
        elif isinstance(class_memberships, dict):
            if class_id in class_memberships:
                membership = class_memberships[class_id]
                members.append({
                    'user_id': user.get('id'),
                    'email': user.get('email'),
                    'display_name': user.get('display_name', user.get('name', user.get('id'))),
                    'role': membership.get('role'),
                    'assigned_at': membership.get('assigned_at'),
                    'assigned_by': membership.get('assigned_by')
                })
            else:
                # Not found in dict format, try classRoles fallback
                class_roles = user.get('classRoles', {})
                if class_id in class_roles:
                    members.append({
                        'user_id': user.get('id'),
                        'email': user.get('email'),
                        'display_name': user.get('display_name', user.get('name', user.get('id'))),
                        'role': class_roles[class_id],
                        'assigned_at': None,
                        'assigned_by': None
                    })

        # No accessible_classes fallback - too insecure
        # Only trust class_memberships and classRoles (class-specific permissions)

    # Sort by role hierarchy then name
    role_order = {'instructor': 0, 'ta': 1, 'student': 2}
    members.sort(key=lambda m: (role_order.get(m['role'], 999), m['display_name']))

    return members


def validate_role(role: str) -> bool:
    """
    Validate that a role is valid.

    Args:
        role: Role string to validate

    Returns:
        True if valid, False otherwise
    """
    valid_roles = ['instructor', 'ta', 'student']
    return role.lower() in valid_roles


def require_quiz_permission(permission: str):
    """
    Decorator to require permission for the class that owns a quiz.

    Automatically looks up the quiz, extracts its class, and validates permission.
    Expects quiz_id in route parameters.

    Args:
        permission: Permission required (e.g., 'manage_quizzes')

    Usage:
        @app.route('/api/quizzes/<quiz_id>', methods=['PUT'])
        @require_jwt_token
        @require_quiz_permission('manage_quizzes')
        def update_quiz(quiz_id):
            # Only users with manage_quizzes permission for the quiz's class
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Ensure authentication
            if not hasattr(request, 'jwt_user'):
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Must use @require_jwt_token before @require_quiz_permission'
                }), 401

            user = request.jwt_user

            # Global admins bypass permission checks
            if 'admin' in user.get('roles', []):
                return f(*args, **kwargs)

            # Get quiz_id from route parameters
            quiz_id = kwargs.get('quiz_id') or request.view_args.get('quiz_id')
            if not quiz_id:
                return jsonify({
                    'error': 'Invalid request',
                    'message': 'quiz_id required in route'
                }), 400

            # Look up quiz to get its class
            from informatics_classroom.database.factory import get_database_adapter
            db = get_database_adapter()
            quiz = db.get('quiz', quiz_id)

            if not quiz:
                return jsonify({
                    'error': 'Quiz not found',
                    'message': f'Quiz {quiz_id} does not exist'
                }), 404

            class_id = quiz.get('class')
            if not class_id:
                return jsonify({
                    'error': 'Invalid quiz',
                    'message': 'Quiz has no associated class'
                }), 400

            # Check permission for the quiz's class
            if not user_has_class_permission(user, class_id, permission):
                user_role = get_user_class_role(user, class_id)
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'Permission "{permission}" required for class {class_id}. Your role: {user_role or "none"}'
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator
