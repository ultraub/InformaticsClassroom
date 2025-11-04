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
        token = get_token_from_header()

        if not token:
            return jsonify({
                'error': 'Authorization token required',
                'message': 'Missing Authorization header with Bearer token'
            }), 401

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

    return decorated_function


def require_role(required_roles):
    """
    Decorator to require specific user roles.

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

            user_roles = request.jwt_user.get('roles', [])

            # Check if user has any of the required roles
            if not any(role in user_roles for role in required_roles):
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'Required role: {" or ".join(required_roles)}'
                }), 403

            return f(*args, **kwargs)

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
