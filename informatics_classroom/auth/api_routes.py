"""
API Authentication Routes for React SPA

These routes provide JWT-based authentication for the React SPA,
integrating with the existing MSAL authentication flow.
"""

from flask import jsonify, request, session, url_for
from informatics_classroom.auth import auth_bp
from informatics_classroom.auth.jwt_utils import (
    generate_access_token,
    generate_refresh_token,
    refresh_access_token,
    require_jwt_token
)
import jwt as pyjwt


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    """
    Initiate MSAL login flow for React SPA.

    Returns:
        JSON with auth_url to redirect user to Microsoft login
    """
    from informatics_classroom.auth.routes import _build_auth_code_flow
    from informatics_classroom.config import Config

    # Build MSAL auth code flow
    flow = _build_auth_code_flow(scopes=Config.SCOPE)
    session["flow"] = flow

    return jsonify({
        "auth_url": flow["auth_uri"],
        "message": "Redirect user to auth_url for Microsoft login"
    }), 200


@auth_bp.route("/api/auth/callback", methods=["GET"])
def api_callback():
    """
    MSAL callback endpoint that issues JWT tokens for React SPA.

    This endpoint:
    1. Completes the MSAL authentication flow
    2. Extracts user information
    3. Issues JWT access and refresh tokens
    4. Returns tokens to React for storage

    Query Parameters:
        code: Authorization code from Microsoft
        state: State parameter for CSRF protection

    Returns:
        JSON with JWT tokens and user information
    """
    from informatics_classroom.auth.routes import _build_msal_app, _load_cache, _save_cache

    try:
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_auth_code_flow(
            session.get("flow", {}),
            request.args
        )

        if "error" in result:
            return jsonify({
                "error": result.get("error"),
                "error_description": result.get("error_description")
            }), 400

        # Extract user information from ID token
        user_data = result.get("id_token_claims")
        session["user"] = user_data
        _save_cache(cache)

        # Generate JWT tokens
        access_token = generate_access_token(user_data)
        refresh_token = generate_refresh_token(user_data.get("oid") or user_data.get("sub"))

        # Return tokens and user info to React
        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 3600,  # 1 hour
            "user": {
                "id": user_data.get("oid") or user_data.get("sub"),
                "email": user_data.get("email") or user_data.get("preferred_username"),
                "displayName": user_data.get("name"),
                "roles": user_data.get("roles", [])
            }
        }), 200

    except ValueError as e:
        # Usually caused by CSRF or invalid flow
        return jsonify({
            "error": "Authentication failed",
            "message": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@auth_bp.route("/api/auth/refresh", methods=["POST"])
def api_refresh():
    """
    Refresh access token using refresh token.

    Request Body:
        {
            "refresh_token": "..."
        }

    Returns:
        JSON with new access token
    """
    data = request.get_json()
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({
            "error": "Refresh token required",
            "message": "Missing refresh_token in request body"
        }), 400

    try:
        new_access_token = refresh_access_token(refresh_token)

        return jsonify({
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": 3600
        }), 200

    except pyjwt.InvalidTokenError as e:
        return jsonify({
            "error": "Invalid refresh token",
            "message": str(e)
        }), 401


@auth_bp.route("/api/auth/session", methods=["GET"])
@require_jwt_token
def api_get_session():
    """
    Get current user session information.

    Requires valid JWT token in Authorization header.

    Returns:
        JSON with current user information
    """
    user_data = request.jwt_user

    return jsonify({
        "user": {
            "id": user_data.get("user_id"),
            "email": user_data.get("email"),
            "displayName": user_data.get("display_name"),
            "roles": user_data.get("roles", [])
        },
        "isAuthenticated": True
    }), 200


@auth_bp.route("/api/auth/logout", methods=["POST"])
@require_jwt_token
def api_logout():
    """
    Logout user (client-side token cleanup).

    For React SPA, logout is primarily client-side (delete tokens from localStorage).
    This endpoint clears server-side session if present.

    Returns:
        JSON confirmation
    """
    session.clear()

    from informatics_classroom.config import Config

    return jsonify({
        "message": "Logged out successfully",
        "logout_url": Config.AUTHORITY + "/oauth2/v2.0/logout"
    }), 200


@auth_bp.route("/api/auth/validate", methods=["POST"])
def api_validate_token():
    """
    Validate a JWT token without requiring authentication decorator.

    Useful for client-side token validation.

    Request Body:
        {
            "token": "..."
        }

    Returns:
        JSON with validation result
    """
    from informatics_classroom.auth.jwt_utils import decode_token

    data = request.get_json()
    token = data.get("token")

    if not token:
        return jsonify({
            "valid": False,
            "error": "Token required"
        }), 400

    try:
        payload = decode_token(token)
        return jsonify({
            "valid": True,
            "payload": {
                "user_id": payload.get("user_id"),
                "email": payload.get("email"),
                "expires": payload.get("exp")
            }
        }), 200

    except pyjwt.ExpiredSignatureError:
        return jsonify({
            "valid": False,
            "error": "Token expired"
        }), 200  # Return 200 with error info, not 401

    except pyjwt.InvalidTokenError as e:
        return jsonify({
            "valid": False,
            "error": str(e)
        }), 200  # Return 200 with error info, not 401
