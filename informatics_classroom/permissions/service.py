"""
PermissionService - Centralized Permission Management

This service provides a unified interface for all permission checks and
management operations in the InformaticsClassroom system.
"""

from typing import Optional, List, Dict, Set
from flask import session
from informatics_classroom.azure_func import init_cosmos
from informatics_classroom.config import Config
from .models import (
    Permission,
    Role,
    ClassRole,
    PermissionCheck,
    get_permissions_for_role,
    get_permissions_for_class_role,
    permission_implies,
)


class PermissionService:
    """
    Centralized service for permission management

    Provides methods for:
    - Checking user permissions (global and class-specific)
    - Retrieving user roles and permissions
    - Managing permission assignments
    - Validating access to resources
    """

    def __init__(self, database: str = None):
        """Initialize the permission service"""
        self.database = database or Config.DATABASE
        self._cache = {}  # Simple in-memory cache for permission checks

    def _get_user_container(self):
        """Get Cosmos DB container for users"""
        return init_cosmos('users', self.database)

    def _get_class_container(self):
        """Get Cosmos DB container for classes"""
        return init_cosmos('classes', self.database)

    def _get_quiz_container(self):
        """Get Cosmos DB container for quizzes"""
        return init_cosmos('quiz', self.database)

    def _get_current_user_id(self) -> Optional[str]:
        """Get current user ID from session"""
        if Config.TESTING:
            return 'rbarre16'  # Test user

        if session.get('user'):
            return session['user'].get('preferred_username', '').split('@')[0]

        return None

    def _get_user_document(self, user_id: Optional[str] = None) -> Optional[Dict]:
        """Retrieve user document from database"""
        user_id = user_id or self._get_current_user_id()
        if not user_id:
            return None

        # Check cache first
        cache_key = f"user:{user_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            container = self._get_user_container()
            user = container.read_item(item=user_id, partition_key=user_id)
            self._cache[cache_key] = user
            return user
        except Exception:
            return None

    def clear_cache(self, user_id: Optional[str] = None):
        """Clear permission cache for a user or all users"""
        if user_id:
            cache_key = f"user:{user_id}"
            if cache_key in self._cache:
                del self._cache[cache_key]
        else:
            self._cache.clear()

    # ========== Role Retrieval ==========

    def get_user_role(self, user_id: Optional[str] = None) -> Optional[Role]:
        """Get the global role for a user"""
        user = self._get_user_document(user_id)
        if not user:
            return None

        role_str = user.get('role')
        if not role_str:
            return None

        try:
            return Role(role_str)
        except ValueError:
            return None

    def get_user_class_roles(self, user_id: Optional[str] = None) -> Dict[str, ClassRole]:
        """
        Get class-specific roles for a user

        Returns: Dict mapping class name to ClassRole
        Example: {"PMAP": ClassRole.CLASS_INSTRUCTOR, "CDA": ClassRole.CLASS_STUDENT}
        """
        user = self._get_user_document(user_id)
        if not user:
            return {}

        class_roles = user.get('class_roles', {})
        result = {}

        for class_name, role_str in class_roles.items():
            try:
                result[class_name] = ClassRole(role_str)
            except ValueError:
                continue

        return result

    def get_class_role(self, class_name: str, user_id: Optional[str] = None) -> Optional[ClassRole]:
        """Get the role for a user in a specific class"""
        class_roles = self.get_user_class_roles(user_id)
        return class_roles.get(class_name)

    # ========== Permission Checks ==========

    def has_permission(
        self,
        permission: Permission,
        user_id: Optional[str] = None,
        class_name: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> PermissionCheck:
        """
        Comprehensive permission check

        Args:
            permission: The permission to check
            user_id: User ID (uses current session user if None)
            class_name: Class context for class-specific permissions
            resource_id: Specific resource (e.g., quiz_id) for ownership checks

        Returns:
            PermissionCheck with details about the permission decision
        """
        user_id = user_id or self._get_current_user_id()
        if not user_id:
            return PermissionCheck(
                has_permission=False,
                reason="No authenticated user"
            )

        user = self._get_user_document(user_id)
        if not user:
            return PermissionCheck(
                has_permission=False,
                reason="User not found"
            )

        # Check 1: System admin has all permissions
        global_role = self.get_user_role(user_id)
        if global_role == Role.ADMIN:
            return PermissionCheck(
                has_permission=True,
                reason="System administrator has all permissions",
                granted_by="global_role",
                role=global_role.value
            )

        # Check 2: Direct global permissions
        global_permissions = user.get('global_permissions', [])
        for perm_str in global_permissions:
            try:
                user_perm = Permission(perm_str)
                if permission_implies(user_perm, permission):
                    return PermissionCheck(
                        has_permission=True,
                        reason=f"Global permission granted: {user_perm.value}",
                        granted_by="direct_permission",
                        role=None
                    )
            except ValueError:
                continue

        # Check 3: Global role permissions
        if global_role:
            role_permissions = get_permissions_for_role(global_role)
            for role_perm in role_permissions:
                if permission_implies(role_perm, permission):
                    return PermissionCheck(
                        has_permission=True,
                        reason=f"Permission from global role: {global_role.value}",
                        granted_by="global_role",
                        role=global_role.value
                    )

        # Check 4: Class-specific permissions
        if class_name:
            class_role = self.get_class_role(class_name, user_id)
            if class_role:
                class_permissions = get_permissions_for_class_role(class_role)
                for class_perm in class_permissions:
                    if permission_implies(class_perm, permission):
                        return PermissionCheck(
                            has_permission=True,
                            reason=f"Permission from class role: {class_role.value}",
                            granted_by="class_role",
                            role=class_role.value,
                            class_context=class_name
                        )

        # Check 5: Resource-specific permissions (e.g., quiz ownership)
        if resource_id and permission in [Permission.QUIZ_MODIFY, Permission.QUIZ_DELETE]:
            if self._owns_resource(user_id, resource_id, 'quiz'):
                return PermissionCheck(
                    has_permission=True,
                    reason=f"User owns resource: {resource_id}",
                    granted_by="resource_ownership",
                    role=None
                )

        return PermissionCheck(
            has_permission=False,
            reason="No matching permissions found"
        )

    def _owns_resource(self, user_id: str, resource_id: str, resource_type: str) -> bool:
        """Check if user owns a specific resource"""
        if resource_type == 'quiz':
            try:
                container = self._get_quiz_container()
                query = "SELECT * FROM c WHERE c.id = @quiz_id"
                parameters = [{"name": "@quiz_id", "value": resource_id}]
                results = list(container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))

                if results:
                    quiz = results[0]
                    return quiz.get('owner') == user_id

            except Exception:
                pass

        return False

    def has_role(self, role: Role, user_id: Optional[str] = None) -> bool:
        """Check if user has a specific global role"""
        user_role = self.get_user_role(user_id)
        return user_role == role

    def has_class_role(
        self,
        class_name: str,
        role: ClassRole,
        user_id: Optional[str] = None
    ) -> bool:
        """Check if user has a specific role in a class"""
        class_role = self.get_class_role(class_name, user_id)
        return class_role == role

    def has_any_class_role(
        self,
        class_name: str,
        roles: List[ClassRole],
        user_id: Optional[str] = None
    ) -> bool:
        """Check if user has any of the specified roles in a class"""
        class_role = self.get_class_role(class_name, user_id)
        return class_role in roles

    # ========== Permission Management ==========

    def assign_global_role(self, user_id: str, role: Role) -> bool:
        """Assign a global role to a user"""
        try:
            user = self._get_user_document(user_id)
            if not user:
                # Create new user
                user = {
                    'id': user_id,
                    'role': role.value,
                    'class_roles': {},
                    'global_permissions': []
                }
            else:
                user['role'] = role.value

            container = self._get_user_container()
            container.upsert_item(user)
            self.clear_cache(user_id)
            return True

        except Exception as e:
            print(f"Error assigning role: {e}")
            return False

    def assign_class_role(
        self,
        user_id: str,
        class_name: str,
        role: ClassRole
    ) -> bool:
        """Assign a class-specific role to a user"""
        try:
            user = self._get_user_document(user_id)
            if not user:
                # Create new user
                user = {
                    'id': user_id,
                    'role': Role.STUDENT.value,  # Default global role
                    'class_roles': {class_name: role.value},
                    'global_permissions': []
                }
            else:
                if 'class_roles' not in user:
                    user['class_roles'] = {}
                user['class_roles'][class_name] = role.value

            container = self._get_user_container()
            container.upsert_item(user)
            self.clear_cache(user_id)
            return True

        except Exception as e:
            print(f"Error assigning class role: {e}")
            return False

    def remove_class_role(self, user_id: str, class_name: str) -> bool:
        """Remove a user's role from a specific class"""
        try:
            user = self._get_user_document(user_id)
            if not user or 'class_roles' not in user:
                return False

            if class_name in user['class_roles']:
                del user['class_roles'][class_name]

                container = self._get_user_container()
                container.upsert_item(user)
                self.clear_cache(user_id)
                return True

            return False

        except Exception as e:
            print(f"Error removing class role: {e}")
            return False

    def grant_permission(
        self,
        user_id: str,
        permission: Permission
    ) -> bool:
        """Grant a specific permission directly to a user"""
        try:
            user = self._get_user_document(user_id)
            if not user:
                return False

            if 'global_permissions' not in user:
                user['global_permissions'] = []

            if permission.value not in user['global_permissions']:
                user['global_permissions'].append(permission.value)

                container = self._get_user_container()
                container.upsert_item(user)
                self.clear_cache(user_id)

            return True

        except Exception as e:
            print(f"Error granting permission: {e}")
            return False

    def revoke_permission(
        self,
        user_id: str,
        permission: Permission
    ) -> bool:
        """Revoke a specific permission from a user"""
        try:
            user = self._get_user_document(user_id)
            if not user or 'global_permissions' not in user:
                return False

            if permission.value in user['global_permissions']:
                user['global_permissions'].remove(permission.value)

                container = self._get_user_container()
                container.upsert_item(user)
                self.clear_cache(user_id)

            return True

        except Exception as e:
            print(f"Error revoking permission: {e}")
            return False

    # ========== Utility Methods ==========

    def get_user_permissions(
        self,
        user_id: Optional[str] = None,
        class_name: Optional[str] = None
    ) -> Set[Permission]:
        """
        Get all permissions for a user

        Args:
            user_id: User ID (uses current session user if None)
            class_name: If provided, includes class-specific permissions

        Returns:
            Set of all permissions the user has
        """
        user_id = user_id or self._get_current_user_id()
        if not user_id:
            return set()

        permissions = set()

        # Global role permissions
        global_role = self.get_user_role(user_id)
        if global_role:
            permissions.update(get_permissions_for_role(global_role))

        # Direct global permissions
        user = self._get_user_document(user_id)
        if user and 'global_permissions' in user:
            for perm_str in user['global_permissions']:
                try:
                    permissions.add(Permission(perm_str))
                except ValueError:
                    continue

        # Class-specific permissions
        if class_name:
            class_role = self.get_class_role(class_name, user_id)
            if class_role:
                permissions.update(get_permissions_for_class_role(class_role))

        return permissions

    def get_accessible_classes(self, user_id: Optional[str] = None) -> List[str]:
        """Get list of classes the user has access to"""
        user_id = user_id or self._get_current_user_id()
        if not user_id:
            return []

        # Admins have access to all classes
        if self.has_role(Role.ADMIN, user_id):
            # Return all classes from database
            # TODO: Implement when classes collection is populated
            pass

        class_roles = self.get_user_class_roles(user_id)
        return list(class_roles.keys())


# Global instance
permission_service = PermissionService()
