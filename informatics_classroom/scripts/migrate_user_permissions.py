#!/usr/bin/env python3
"""
Migration script to convert user permissions from old schema to new class_memberships.

OLD SCHEMA:
{
    "id": "user123",
    "role": "instructor",  # Global role
    "accessible_classes": ["BIO101", "CS201"]
}

NEW SCHEMA:
{
    "id": "user123",
    "global_role": "user",
    "class_memberships": {
        "BIO101": {
            "role": "instructor",
            "assigned_at": "2025-01-15T10:00:00Z",
            "migrated_from": "accessible_classes"
        }
    },
    # Keep old fields for rollback
    "_legacy_role": "instructor",
    "_legacy_accessible_classes": ["BIO101", "CS201"]
}
"""

import sys
import os
import datetime
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.factory import get_database_adapter


def determine_role_for_class(global_role: str, class_id: str) -> str:
    """
    Determine appropriate role for a class based on global role.

    Args:
        global_role: User's global role (admin, instructor, ta, student)
        class_id: Class identifier (not used currently, but available for custom logic)

    Returns:
        Role string appropriate for class membership
    """
    global_role_lower = global_role.lower()

    # Admin becomes instructor in all classes
    if global_role_lower == 'admin':
        return 'instructor'

    # Map other roles directly
    if global_role_lower in ['instructor', 'ta']:
        return global_role_lower

    # Default to student
    return 'student'


def migrate_user(user: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """
    Migrate a single user from old schema to new schema.

    Args:
        user: User document to migrate
        dry_run: If True, don't save changes, just return what would be changed

    Returns:
        Result dictionary with status and changes
    """
    user_id = user.get('id')

    # Check if already migrated
    if user.get('class_memberships'):
        return {
            'user_id': user_id,
            'status': 'skipped',
            'reason': 'Already has class_memberships'
        }

    # Get old schema fields
    global_role = user.get('role', 'student')
    accessible_classes = user.get('accessible_classes', [])

    # If no accessible classes, skip (unless they're admin)
    if not accessible_classes and global_role.lower() != 'admin':
        return {
            'user_id': user_id,
            'status': 'skipped',
            'reason': 'No accessible_classes to migrate'
        }

    # Build class_memberships
    class_memberships = {}
    migration_time = datetime.datetime.utcnow().isoformat()

    for class_id in accessible_classes:
        role = determine_role_for_class(global_role, class_id)
        class_memberships[class_id] = {
            'role': role,
            'assigned_at': migration_time,
            'migrated_from': 'accessible_classes',
            'original_global_role': global_role
        }

    # Build updated user document
    updated_user = {**user}
    updated_user['class_memberships'] = class_memberships

    # Preserve legacy fields for rollback
    updated_user['_legacy_role'] = global_role
    updated_user['_legacy_accessible_classes'] = accessible_classes
    updated_user['_migrated_at'] = migration_time

    # Determine global_role for new schema
    if global_role.lower() == 'admin':
        updated_user['global_role'] = 'admin'
    else:
        updated_user['global_role'] = 'user'

    # Save if not dry run
    if not dry_run:
        db = get_database_adapter()
        db.upsert('users', updated_user)

    return {
        'user_id': user_id,
        'status': 'migrated',
        'classes_migrated': len(class_memberships),
        'old_role': global_role,
        'new_global_role': updated_user['global_role'],
        'class_memberships': class_memberships
    }


def migrate_all_users(dry_run: bool = True, verbose: bool = True) -> Dict[str, Any]:
    """
    Migrate all users in the database.

    Args:
        dry_run: If True, don't actually save changes
        verbose: If True, print progress

    Returns:
        Summary dictionary with migration results
    """
    db = get_database_adapter()

    # Get all users
    if verbose:
        print("Fetching all users from database...")
    users = db.query('users', filters={})

    if verbose:
        print(f"Found {len(users)} users to process")
        print(f"Mode: {'DRY RUN (no changes will be saved)' if dry_run else 'LIVE MIGRATION'}")
        print("-" * 80)

    results = {
        'total': len(users),
        'migrated': 0,
        'skipped': 0,
        'errors': 0,
        'details': []
    }

    for i, user in enumerate(users, 1):
        user_id = user.get('id', f'unknown_{i}')

        try:
            result = migrate_user(user, dry_run=dry_run)
            results['details'].append(result)

            if result['status'] == 'migrated':
                results['migrated'] += 1
                if verbose:
                    print(f"[{i}/{len(users)}] MIGRATED: {user_id}")
                    print(f"  Old role: {result['old_role']}")
                    print(f"  Classes: {result['classes_migrated']}")
                    for class_id, membership in result['class_memberships'].items():
                        print(f"    - {class_id}: {membership['role']}")

            elif result['status'] == 'skipped':
                results['skipped'] += 1
                if verbose:
                    print(f"[{i}/{len(users)}] SKIPPED: {user_id} - {result['reason']}")

        except Exception as e:
            results['errors'] += 1
            error_detail = {
                'user_id': user_id,
                'status': 'error',
                'error': str(e)
            }
            results['details'].append(error_detail)

            if verbose:
                print(f"[{i}/{len(users)}] ERROR: {user_id} - {str(e)}")

    if verbose:
        print("-" * 80)
        print("Migration Summary:")
        print(f"  Total users: {results['total']}")
        print(f"  Migrated: {results['migrated']}")
        print(f"  Skipped: {results['skipped']}")
        print(f"  Errors: {results['errors']}")

        if dry_run:
            print("\n⚠️  This was a DRY RUN - no changes were saved to the database")
            print("Run with --live flag to perform actual migration")

    return results


def rollback_migration(user_id: str = None, dry_run: bool = True, verbose: bool = True) -> Dict[str, Any]:
    """
    Rollback migration for one or all users.

    Args:
        user_id: If provided, rollback only this user. Otherwise rollback all.
        dry_run: If True, don't actually save changes
        verbose: If True, print progress

    Returns:
        Summary dictionary with rollback results
    """
    db = get_database_adapter()

    # Get users to rollback
    if user_id:
        users = [db.get('users', user_id)]
        if not users[0]:
            return {'error': f'User {user_id} not found'}
    else:
        users = db.query('users', filters={})

    if verbose:
        print(f"Rolling back {len(users)} user(s)...")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE ROLLBACK'}")
        print("-" * 80)

    results = {
        'total': len(users),
        'rolled_back': 0,
        'skipped': 0,
        'errors': 0
    }

    for user in users:
        uid = user.get('id')

        try:
            # Check if user was migrated
            if not user.get('_migrated_at'):
                results['skipped'] += 1
                if verbose:
                    print(f"SKIPPED: {uid} - Not migrated")
                continue

            # Restore legacy fields
            if '_legacy_role' in user:
                user['role'] = user['_legacy_role']
                del user['_legacy_role']

            if '_legacy_accessible_classes' in user:
                user['accessible_classes'] = user['_legacy_accessible_classes']
                del user['_legacy_accessible_classes']

            # Remove new fields
            if 'class_memberships' in user:
                del user['class_memberships']
            if 'global_role' in user:
                del user['global_role']
            if '_migrated_at' in user:
                del user['_migrated_at']

            # Save if not dry run
            if not dry_run:
                db.upsert('users', user)

            results['rolled_back'] += 1
            if verbose:
                print(f"ROLLED BACK: {uid}")

        except Exception as e:
            results['errors'] += 1
            if verbose:
                print(f"ERROR: {uid} - {str(e)}")

    if verbose:
        print("-" * 80)
        print("Rollback Summary:")
        print(f"  Total: {results['total']}")
        print(f"  Rolled back: {results['rolled_back']}")
        print(f"  Skipped: {results['skipped']}")
        print(f"  Errors: {results['errors']}")

    return results


def validate_migration(verbose: bool = True) -> Dict[str, Any]:
    """
    Validate migration by checking all users have correct structure.

    Args:
        verbose: If True, print detailed validation results

    Returns:
        Validation summary
    """
    db = get_database_adapter()
    users = db.query('users', filters={})

    if verbose:
        print(f"Validating {len(users)} users...")
        print("-" * 80)

    results = {
        'total': len(users),
        'valid': 0,
        'issues': []
    }

    for user in users:
        user_id = user.get('id')
        user_issues = []

        # Check if migrated
        if not user.get('class_memberships'):
            # If has accessible_classes, should be migrated
            if user.get('accessible_classes'):
                user_issues.append('Has accessible_classes but no class_memberships')
        else:
            # Validate class_memberships structure
            class_memberships = user['class_memberships']

            if not isinstance(class_memberships, dict):
                user_issues.append('class_memberships is not a dictionary')
            else:
                for class_id, membership in class_memberships.items():
                    if not isinstance(membership, dict):
                        user_issues.append(f'Membership for {class_id} is not a dictionary')
                    else:
                        if 'role' not in membership:
                            user_issues.append(f'Membership for {class_id} missing role')
                        elif membership['role'] not in ['instructor', 'ta', 'student']:
                            user_issues.append(f'Invalid role for {class_id}: {membership["role"]}')

        if user_issues:
            results['issues'].append({
                'user_id': user_id,
                'issues': user_issues
            })
            if verbose:
                print(f"⚠️  {user_id}:")
                for issue in user_issues:
                    print(f"    - {issue}")
        else:
            results['valid'] += 1

    if verbose:
        print("-" * 80)
        print("Validation Summary:")
        print(f"  Total: {results['total']}")
        print(f"  Valid: {results['valid']}")
        print(f"  Issues: {len(results['issues'])}")

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate user permissions to class_memberships')
    parser.add_argument('command', choices=['migrate', 'rollback', 'validate'],
                       help='Command to execute')
    parser.add_argument('--live', action='store_true',
                       help='Perform actual migration (default is dry run)')
    parser.add_argument('--user', type=str,
                       help='User ID to migrate/rollback (default: all users)')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress verbose output')

    args = parser.parse_args()

    dry_run = not args.live
    verbose = not args.quiet

    if args.command == 'migrate':
        results = migrate_all_users(dry_run=dry_run, verbose=verbose)
    elif args.command == 'rollback':
        results = rollback_migration(user_id=args.user, dry_run=dry_run, verbose=verbose)
    elif args.command == 'validate':
        results = validate_migration(verbose=verbose)

    # Exit with error code if there were errors
    if results.get('errors', 0) > 0:
        sys.exit(1)
