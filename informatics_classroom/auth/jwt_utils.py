"""
JWT Token Utilities for React SPA Authentication

This module provides JWT token generation, validation, and refresh functionality
for the React SPA migration. It integrates with the existing MSAL authentication
while adding stateless JWT tokens for API access.
"""

import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app
from informatics_classroom.config import Config


def generate_access_token(user_data):
    """
    Generate a JWT access token for authenticated user.

    Args:
        user_data (dict): User information from MSAL authentication
            Expected keys: id, email, displayName, roles

    Returns:
        str: Encoded JWT access token
    """
    payload = {
        'user_id': user_data.get('id'),
        'email': user_data.get('email') or user_data.get('preferred_username'),
        'display_name': user_data.get('displayName') or user_data.get('name'),
        'roles': user_data.get('roles', []),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(
            seconds=Config.JWT_ACCESS_TOKEN_EXPIRES
        ),
        'iat': datetime.datetime.utcnow(),
        'type': 'access'
    }

    token = jwt.encode(
        payload,
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM
    )

    return token


def generate_refresh_token(user_id):
    """
    Generate a JWT refresh token for token renewal.

    Args:
        user_id (str): User ID

    Returns:
        str: Encoded JWT refresh token
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(
            seconds=Config.JWT_REFRESH_TOKEN_EXPIRES
        ),
        'iat': datetime.datetime.utcnow(),
        'type': 'refresh'
    }

    token = jwt.encode(
        payload,
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM
    )

    return token


def decode_token(token):
    """
    Decode and validate a JWT token.

    Args:
        token (str): JWT token to decode

    Returns:
        dict: Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")


def get_token_from_header():
    """
    Extract JWT token from Authorization header.

    Returns:
        str: JWT token or None if not found
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None

    return parts[1]


def require_jwt_token(f):
    """
    Decorator to require valid JWT token for API endpoints.

    Usage:
        @app.route('/api/protected')
        @require_jwt_token
        def protected_route():
            # Access user data via request.jwt_user
            user_id = request.jwt_user['user_id']
            return jsonify({'message': 'Protected data'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session

        token = get_token_from_header()

        # Try JWT token first
        if token:
            try:
                payload = decode_token(token)

                # Verify it's an access token
                if payload.get('type') != 'access':
                    return jsonify({
                        'error': 'Invalid token type',
                        'message': 'Expected access token'
                    }), 401

                # Attach user data to request for use in route handler
                request.jwt_user = payload

                return f(*args, **kwargs)

            except jwt.ExpiredSignatureError:
                return jsonify({
                    'error': 'Token expired',
                    'message': 'Access token has expired. Please refresh your token.'
                }), 401

            except jwt.InvalidTokenError as e:
                return jsonify({
                    'error': 'Invalid token',
                    'message': str(e)
                }), 401

        # Fallback to session-based authentication (for development mode)
        if session.get('user'):
            user_data = session['user']
            user_id = user_data.get('preferred_username', '').split('@')[0]

            # Get full user data from database to include class memberships
            from informatics_classroom.database.factory import get_database_adapter
            db = get_database_adapter()
            db_user = db.get('users', user_id)

            # Build class_memberships from database with backward compatibility
            class_memberships = {}
            class_roles = {}
            accessible_classes = []

            if db_user:
                # Try new class_memberships structure first
                class_memberships = db_user.get('class_memberships', {})

                # Fallback to classRoles (intermediate format)
                if not class_memberships:
                    class_roles = db_user.get('classRoles', {})
                    if class_roles:
                        # Convert classRoles to class_memberships format
                        for class_id, role in class_roles.items():
                            class_memberships[class_id] = {'role': role}

                # Fallback to accessible_classes (old format)
                accessible_classes = db_user.get('accessible_classes', [])
                if not class_memberships and accessible_classes:
                    db_role = db_user.get('role', '').lower()
                    if db_role in ['admin', 'instructor']:
                        inferred_role = 'instructor'
                    elif db_role == 'ta':
                        inferred_role = 'ta'
                    elif db_role == 'grader':
                        inferred_role = 'grader'
                    else:
                        inferred_role = 'student'

                    for class_id in accessible_classes:
                        class_memberships[class_id] = {'role': inferred_role}
                        class_roles[class_id] = inferred_role

            # Convert session user to JWT-compatible format
            request.jwt_user = {
                'user_id': user_id,
                'email': user_data.get('email', user_data.get('preferred_username', '')),
                'display_name': user_data.get('name', ''),
                'roles': user_data.get('roles', ['student']),
                'class_memberships': class_memberships,  # New: structured class memberships
                'classRoles': class_roles,  # Legacy: simple class->role mapping
                'accessible_classes': accessible_classes,  # Legacy: for backward compatibility
                'role': db_user.get('role', 'student') if db_user else 'student',  # Legacy global role
                'type': 'session'  # Mark as session-based for tracking
            }

            return f(*args, **kwargs)

        # No authentication found
        return jsonify({
            'error': 'Authorization required',
            'message': 'Missing Authorization header with Bearer token or valid session'
        }), 401

    return decorated_function


def require_role(required_roles):
    """
    Decorator to require specific user roles with hierarchy support.

    Args:
        required_roles (list): List of allowed roles (e.g., ['admin', 'instructor'])

    Usage:
        @app.route('/api/admin-only')
        @require_jwt_token
        @require_role(['admin'])
        def admin_route():
            return jsonify({'message': 'Admin data'})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'jwt_user'):
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Must use @require_jwt_token before @require_role'
                }), 401

            from informatics_classroom.auth.permissions import has_permission, get_role_permissions_with_inheritance

            user = request.jwt_user
            user_roles = user.get('roles', [])

            # Normalize roles to lowercase for comparison
            user_roles = [r.lower() for r in user_roles if r]

            # Admin always passes
            if 'admin' in user_roles:
                return f(*args, **kwargs)

            # Check if user has any of the required roles directly
            required_roles_lower = [r.lower() for r in required_roles]
            if any(role in user_roles for role in required_roles_lower):
                return f(*args, **kwargs)

            # Check role hierarchy - if user has a higher role that inherits the required role
            ROLE_HIERARCHY = {
                'admin': ['instructor', 'ta', 'grader', 'student'],
                'instructor': ['ta', 'grader', 'student'],
                'ta': ['student'],
                'grader': ['student'],
                'student': [],
            }

            for user_role in user_roles:
                inherited_roles = ROLE_HIERARCHY.get(user_role, [])
                if any(req_role in inherited_roles for req_role in required_roles_lower):
                    return f(*args, **kwargs)

            # Check class-specific roles
            class_roles = user.get('classRoles', {})
            if isinstance(class_roles, dict):
                for class_role in class_roles.values():
                    class_role_lower = class_role.lower() if class_role else ''
                    if class_role_lower in required_roles_lower:
                        return f(*args, **kwargs)
                    # Check if class role inherits required role
                    inherited_roles = ROLE_HIERARCHY.get(class_role_lower, [])
                    if any(req_role in inherited_roles for req_role in required_roles_lower):
                        return f(*args, **kwargs)

            return jsonify({
                'error': 'Insufficient permissions',
                'message': f'Required role: {" or ".join(required_roles)}'
            }), 403

        return decorated_function
    return decorator


def refresh_access_token(refresh_token):
    """
    Generate new access token from refresh token.

    Args:
        refresh_token (str): Valid refresh token

    Returns:
        str: New access token

    Raises:
        jwt.InvalidTokenError: If refresh token is invalid or expired
    """
    try:
        payload = decode_token(refresh_token)

        # Verify it's a refresh token
        if payload.get('type') != 'refresh':
            raise jwt.InvalidTokenError("Invalid token type")

        user_id = payload.get('user_id')

        # In a real implementation, you'd fetch fresh user data from database
        # For now, we'll create a minimal token with just the user_id
        # The client will need to fetch full user data separately
        new_token_payload = {
            'user_id': user_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(
                seconds=Config.JWT_ACCESS_TOKEN_EXPIRES
            ),
            'iat': datetime.datetime.utcnow(),
            'type': 'access'
        }

        new_token = jwt.encode(
            new_token_payload,
            Config.JWT_SECRET_KEY,
            algorithm=Config.JWT_ALGORITHM
        )

        return new_token

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        raise jwt.InvalidTokenError(f"Invalid refresh token: {str(e)}")
