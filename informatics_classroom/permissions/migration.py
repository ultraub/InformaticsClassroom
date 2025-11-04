"""
Database Migration Utilities

Provides tools for migrating existing user data to the new RBAC schema
"""

import datetime as dt
from typing import Dict, List, Optional
from informatics_classroom.azure_func import init_cosmos
from informatics_classroom.config import Config
from .models import Role, ClassRole


class PermissionMigration:
    """
    Handles migration of user data from old schema to new RBAC schema

    Old Schema:
    {
        "id": "user_id",
        "role": "Admin|Instructor|Student",
        "accessible_classes": ["PMAP", "CDA"]
    }

    New Schema:
    {
        "id": "user_id",
        "role": "Admin|Instructor|Student",  # Global role (backward compatible)
        "class_roles": {
            "PMAP": "class_instructor",
            "CDA": "class_student"
        },
        "global_permissions": [],
        "accessible_classes": ["PMAP", "CDA"],  # Kept for backward compatibility
        "migration_info": {
            "migrated": true,
            "migration_date": "2025-01-04T...",
            "migration_version": "2.0"
        }
    }
    """

    def __init__(self, database: str = None, dry_run: bool = False):
        """
        Initialize migration utility

        Args:
            database: Database name (defaults to Config.DATABASE)
            dry_run: If True, only simulate migration without making changes
        """
        self.database = database or Config.DATABASE
        self.dry_run = dry_run
        self.stats = {
            'total_users': 0,
            'migrated': 0,
            'already_migrated': 0,
            'errors': 0,
            'skipped': 0
        }

    def _get_user_container(self):
        """Get Cosmos DB container for users"""
        return init_cosmos('users', self.database)

    def _get_quiz_container(self):
        """Get Cosmos DB container for quizzes"""
        return init_cosmos('quiz', self.database)

    def _infer_class_role(self, user: Dict, class_name: str) -> ClassRole:
        """
        Infer the appropriate class role based on user's global role and quiz ownership

        Logic:
        - Admin → CLASS_ADMIN
        - Instructor who owns quizzes in class → CLASS_INSTRUCTOR
        - Instructor without owned quizzes → CLASS_INSTRUCTOR (default)
        - Student → CLASS_STUDENT
        """
        global_role = user.get('role')

        # Admins become class admins
        if global_role == 'Admin':
            return ClassRole.CLASS_ADMIN

        # Students remain students
        if global_role == 'Student':
            return ClassRole.CLASS_STUDENT

        # Instructors: check if they own any quizzes in this class
        if global_role == 'Instructor':
            user_id = user.get('id')
            if self._owns_quizzes_in_class(user_id, class_name):
                return ClassRole.CLASS_INSTRUCTOR
            else:
                # Instructor with access but no owned quizzes
                # Could be TA or co-instructor
                return ClassRole.CLASS_INSTRUCTOR  # Default to instructor

        # Default to student if role is unclear
        return ClassRole.CLASS_STUDENT

    def _owns_quizzes_in_class(self, user_id: str, class_name: str) -> bool:
        """Check if user owns any quizzes in the specified class"""
        try:
            container = self._get_quiz_container()
            query = """
                SELECT VALUE COUNT(1) FROM c
                WHERE c.owner = @user_id AND c.class = @class_name
            """
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@class_name", "value": class_name}
            ]

            results = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))

            return results[0] > 0 if results else False

        except Exception as e:
            print(f"Error checking quiz ownership: {e}")
            return False

    def migrate_user(self, user: Dict) -> Dict:
        """
        Migrate a single user to the new schema

        Returns the updated user document
        """
        user_id = user.get('id')
        print(f"Migrating user: {user_id}")

        # Check if already migrated
        if user.get('migration_info', {}).get('migrated'):
            print(f"  User {user_id} already migrated, skipping")
            self.stats['already_migrated'] += 1
            return user

        # Get accessible classes
        accessible_classes = user.get('accessible_classes', [])

        # Build class_roles mapping
        class_roles = {}
        for class_name in accessible_classes:
            class_role = self._infer_class_role(user, class_name)
            class_roles[class_name] = class_role.value
            print(f"  Class {class_name}: {class_role.value}")

        # Update user document
        user['class_roles'] = class_roles
        user['global_permissions'] = user.get('global_permissions', [])
        user['migration_info'] = {
            'migrated': True,
            'migration_date': dt.datetime.now(dt.timezone.utc).isoformat(),
            'migration_version': '2.0',
            'original_role': user.get('role'),
            'original_accessible_classes': accessible_classes
        }

        # Keep accessible_classes for backward compatibility
        # (Can be removed in future version once all code is updated)

        return user

    def migrate_all_users(self) -> Dict:
        """
        Migrate all users in the database

        Returns migration statistics
        """
        print(f"Starting migration (dry_run={self.dry_run})...")
        print(f"Database: {self.database}")
        print("-" * 50)

        container = self._get_user_container()

        # Query all users
        query = "SELECT * FROM c"
        users = list(container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))

        self.stats['total_users'] = len(users)
        print(f"Found {len(users)} users to process\n")

        # Migrate each user
        for user in users:
            try:
                updated_user = self.migrate_user(user)

                if not self.dry_run:
                    container.upsert_item(updated_user)
                    print(f"  ✓ Saved to database")
                else:
                    print(f"  [DRY RUN] Would save to database")

                if not user.get('migration_info', {}).get('migrated'):
                    self.stats['migrated'] += 1

                print()

            except Exception as e:
                print(f"  ✗ Error migrating user {user.get('id')}: {e}\n")
                self.stats['errors'] += 1

        # Print summary
        print("-" * 50)
        print("Migration Summary:")
        print(f"  Total users: {self.stats['total_users']}")
        print(f"  Newly migrated: {self.stats['migrated']}")
        print(f"  Already migrated: {self.stats['already_migrated']}")
        print(f"  Errors: {self.stats['errors']}")
        print(f"  Skipped: {self.stats['skipped']}")

        if self.dry_run:
            print("\n[DRY RUN] No changes were made to the database")

        return self.stats

    def rollback_user(self, user_id: str) -> bool:
        """
        Rollback a migrated user to the original schema

        This removes the new fields added during migration
        """
        try:
            container = self._get_user_container()
            user = container.read_item(item=user_id, partition_key=user_id)

            if not user.get('migration_info', {}).get('migrated'):
                print(f"User {user_id} was not migrated, nothing to rollback")
                return False

            # Restore original values
            migration_info = user.get('migration_info', {})
            if 'original_role' in migration_info:
                user['role'] = migration_info['original_role']
            if 'original_accessible_classes' in migration_info:
                user['accessible_classes'] = migration_info['original_accessible_classes']

            # Remove new fields
            if 'class_roles' in user:
                del user['class_roles']
            if 'global_permissions' in user:
                del user['global_permissions']
            if 'migration_info' in user:
                del user['migration_info']

            if not self.dry_run:
                container.upsert_item(user)
                print(f"✓ Rolled back user {user_id}")
            else:
                print(f"[DRY RUN] Would rollback user {user_id}")

            return True

        except Exception as e:
            print(f"Error rolling back user {user_id}: {e}")
            return False

    def validate_migration(self) -> Dict:
        """
        Validate that migration was successful

        Checks:
        - All users have been migrated
        - class_roles contains all accessible_classes
        - No data loss occurred
        """
        print("Validating migration...")
        print("-" * 50)

        container = self._get_user_container()
        query = "SELECT * FROM c"
        users = list(container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))

        validation = {
            'total_users': len(users),
            'migrated_users': 0,
            'unmigrated_users': 0,
            'validation_errors': [],
            'warnings': []
        }

        for user in users:
            user_id = user.get('id')

            # Check if migrated
            if not user.get('migration_info', {}).get('migrated'):
                validation['unmigrated_users'] += 1
                validation['validation_errors'].append(
                    f"User {user_id} not migrated"
                )
                continue

            validation['migrated_users'] += 1

            # Validate class_roles
            accessible_classes = user.get('accessible_classes', [])
            class_roles = user.get('class_roles', {})

            for class_name in accessible_classes:
                if class_name not in class_roles:
                    validation['validation_errors'].append(
                        f"User {user_id}: class {class_name} in accessible_classes but not in class_roles"
                    )

            # Check for orphaned class_roles
            for class_name in class_roles.keys():
                if class_name not in accessible_classes:
                    validation['warnings'].append(
                        f"User {user_id}: class {class_name} in class_roles but not in accessible_classes"
                    )

        # Print results
        print(f"Total users: {validation['total_users']}")
        print(f"Migrated: {validation['migrated_users']}")
        print(f"Unmigrated: {validation['unmigrated_users']}")
        print(f"Errors: {len(validation['validation_errors'])}")
        print(f"Warnings: {len(validation['warnings'])}")

        if validation['validation_errors']:
            print("\nValidation Errors:")
            for error in validation['validation_errors']:
                print(f"  ✗ {error}")

        if validation['warnings']:
            print("\nWarnings:")
            for warning in validation['warnings']:
                print(f"  ⚠ {warning}")

        if not validation['validation_errors'] and validation['unmigrated_users'] == 0:
            print("\n✓ Migration validation passed!")

        return validation


def run_migration(database: str = None, dry_run: bool = True):
    """
    Convenience function to run the migration

    Usage:
        # Test migration without making changes
        python -c "from informatics_classroom.permissions.migration import run_migration; run_migration(dry_run=True)"

        # Actually run the migration
        python -c "from informatics_classroom.permissions.migration import run_migration; run_migration(dry_run=False)"
    """
    migration = PermissionMigration(database=database, dry_run=dry_run)
    stats = migration.migrate_all_users()
    return stats


def validate_migration_status(database: str = None):
    """
    Validate the current migration status

    Usage:
        python -c "from informatics_classroom.permissions.migration import validate_migration_status; validate_migration_status()"
    """
    migration = PermissionMigration(database=database)
    validation = migration.validate_migration()
    return validation
