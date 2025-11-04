"""
Permission Decorators

Provides decorator functions for route protection based on permissions
"""

from functools import wraps
from flask import session, redirect, url_for, jsonify, flash, request
from typing import Optional, List, Callable
from .models import Permission, Role, ClassRole
from .service import permission_service


def require_permission(
    permission: Permission,
    class_param: Optional[str] = None,
    resource_param: Optional[str] = None,
    json_error: bool = False
):
    """
    Decorator to require a specific permission for a route

    Args:
        permission: The permission required
        class_param: Name of the parameter (query/form/json) containing class name
        resource_param: Name of the parameter containing resource ID
        json_error: If True, return JSON error instead of redirect

    Usage:
        @require_permission(Permission.QUIZ_MODIFY, resource_param='quiz_id')
        def modify_quiz(quiz_id):
            # Only users with QUIZ_MODIFY permission can access
            pass

        @require_permission(Permission.ASSIGNMENT_ANALYZE, class_param='class_name')
        def analyze_assignment():
            # Checks class-specific permission
            pass
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get class context if specified
            class_name = None
            if class_param:
                class_name = (
                    request.args.get(class_param) or
                    request.form.get(class_param) or
                    (request.json or {}).get(class_param) if request.is_json else None
                )

            # Get resource ID if specified
            resource_id = None
            if resource_param:
                resource_id = (
                    request.args.get(resource_param) or
                    request.form.get(resource_param) or
                    (request.json or {}).get(resource_param) if request.is_json else None or
                    kwargs.get(resource_param)
                )

            # Check permission
            check = permission_service.has_permission(
                permission=permission,
                class_name=class_name,
                resource_id=resource_id
            )

            if not check.has_permission:
                if json_error:
                    return jsonify({
                        "message": "Unauthorized",
                        "reason": check.reason,
                        "required_permission": permission.value
                    }), 403
                else:
                    flash(f"You do not have permission to access this page. ({check.reason})", "error")
                    return redirect(url_for("classroom_bp.landingpage"))

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_role(role: Role, json_error: bool = False):
    """
    Decorator to require a specific global role

    Usage:
        @require_role(Role.ADMIN)
        def admin_dashboard():
            # Only admins can access
            pass
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not permission_service.has_role(role):
                if json_error:
                    return jsonify({
                        "message": "Unauthorized",
                        "required_role": role.value
                    }), 403
                else:
                    flash(f"You must be a {role.value} to access this page.", "error")
                    return redirect(url_for("classroom_bp.landingpage"))

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_any_role(roles: List[Role], json_error: bool = False):
    """
    Decorator to require any of the specified global roles

    Usage:
        @require_any_role([Role.ADMIN, Role.INSTRUCTOR])
        def instructor_dashboard():
            # Admins or instructors can access
            pass
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            has_role = any(permission_service.has_role(role) for role in roles)

            if not has_role:
                role_names = " or ".join(r.value for r in roles)
                if json_error:
                    return jsonify({
                        "message": "Unauthorized",
                        "required_roles": [r.value for r in roles]
                    }), 403
                else:
                    flash(f"You must be a {role_names} to access this page.", "error")
                    return redirect(url_for("classroom_bp.landingpage"))

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_class_role(
    role: ClassRole,
    class_param: str = 'class_name',
    json_error: bool = False
):
    """
    Decorator to require a specific class role

    Usage:
        @require_class_role(ClassRole.CLASS_INSTRUCTOR, class_param='class_name')
        def manage_class():
            # Only instructors of the specified class can access
            pass
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get class context
            class_name = (
                request.args.get(class_param) or
                request.form.get(class_param) or
                (request.json or {}).get(class_param) if request.is_json else None or
                kwargs.get(class_param)
            )

            if not class_name:
                if json_error:
                    return jsonify({
                        "message": "Bad Request",
                        "reason": f"Missing required parameter: {class_param}"
                    }), 400
                else:
                    flash("Class context is required.", "error")
                    return redirect(url_for("classroom_bp.landingpage"))

            # Check if user has required role in this class
            if not permission_service.has_class_role(class_name, role):
                if json_error:
                    return jsonify({
                        "message": "Unauthorized",
                        "required_class_role": role.value,
                        "class": class_name
                    }), 403
                else:
                    flash(f"You must be a {role.value} in {class_name} to access this.", "error")
                    return redirect(url_for("classroom_bp.landingpage"))

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_any_class_role(
    roles: List[ClassRole],
    class_param: str = 'class_name',
    json_error: bool = False
):
    """
    Decorator to require any of the specified class roles

    Usage:
        @require_any_class_role([ClassRole.CLASS_INSTRUCTOR, ClassRole.CLASS_TA])
        def view_grades():
            # Instructors or TAs can access
            pass
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get class context
            class_name = (
                request.args.get(class_param) or
                request.form.get(class_param) or
                (request.json or {}).get(class_param) if request.is_json else None or
                kwargs.get(class_param)
            )

            if not class_name:
                if json_error:
                    return jsonify({
                        "message": "Bad Request",
                        "reason": f"Missing required parameter: {class_param}"
                    }), 400
                else:
                    flash("Class context is required.", "error")
                    return redirect(url_for("classroom_bp.landingpage"))

            # Check if user has any of the required roles
            if not permission_service.has_any_class_role(class_name, roles):
                role_names = " or ".join(r.value for r in roles)
                if json_error:
                    return jsonify({
                        "message": "Unauthorized",
                        "required_class_roles": [r.value for r in roles],
                        "class": class_name
                    }), 403
                else:
                    flash(f"You must be a {role_names} in {class_name} to access this.", "error")
                    return redirect(url_for("classroom_bp.landingpage"))

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_authenticated(json_error: bool = False):
    """
    Decorator to require authentication (any logged-in user)

    Usage:
        @require_authenticated()
        def profile():
            # Any logged-in user can access
            pass
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = permission_service._get_current_user_id()

            if not user_id:
                if json_error:
                    return jsonify({"message": "Unauthorized - Authentication required"}), 401
                else:
                    return redirect(url_for("auth_bp.login"))

            return f(*args, **kwargs)

        return decorated_function
    return decorator
