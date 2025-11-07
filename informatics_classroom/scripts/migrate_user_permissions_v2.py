#!/usr/bin/env python3
"""
Conservative user permission migration script with quiz modification analysis.

Strategy:
1. Analyze quiz change_logs to identify who actually managed each class
2. Only promote to instructor/ta if they modified quizzes for that class
3. Default everyone else to student (safe default)
4. Ignore global roles to prevent privilege escalation

This ensures only actual course managers get elevated permissions.
"""
import sys
import os
import datetime
from typing import Dict, Set, Any, List
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.factory import get_database_adapter


def build_quiz_modification_map() -> Dict[str, Set[str]]:
    """
    Build a map of which users modified quizzes for which classes.

    Returns:
        Dict mapping user_id -> set of class_ids they modified quizzes for
    """
    db = get_database_adapter()
    all_quizzes = db.query('quiz', filters={})

    # Map: user_id -> set(class_ids)
    user_modifications: Dict[str, Set[str]] = defaultdict(set)

    for quiz in all_quizzes:
        class_id = quiz.get('class')
        if not class_id:
            continue

        questions = quiz.get('questions', [])
        for question in questions:
            change_log = question.get('change_log', [])
            for change in change_log:
                updated_by = change.get('updated_by')
                if updated_by:
                    user_modifications[updated_by].add(class_id)

    return user_modifications


def determine_role_for_class(
    user: Dict[str, Any],
    class_id: str,
    user_modifications: Dict[str, Set[str]]
) -> str:
    """
    Determine role for a class based on classRoles and quiz modifications.

    Conservative approach:
    - If user has classRoles AND modified quizzes -> keep instructor/ta role
    - If user has classRoles but NEVER modified -> student (they only took the class)
    - If user modified quizzes but no classRoles -> instructor (they managed it)
    - Everyone else -> student

    Args:
        user: User document
        class_id: Class identifier
        user_modifications: Map of user_id -> classes they modified

    Returns:
        Role string: 'instructor', 'ta', or 'student'
    """
    user_id = user.get('id')
    modified_classes = user_modifications.get(user_id, set())

    # Check if user modified quizzes for this class
    modified_this_class = class_id in modified_classes

    # Get classRoles if exists
    class_roles = user.get('classRoles', {})

    if class_id in class_roles:
        # User has explicit class role
        role = class_roles[class_id].lower()

        # If they modified quizzes, trust their role
        if modified_this_class:
            if role in ['instructor', 'ta']:
                return role
            elif role == 'grader':
                return 'ta'  # Upgrade grader to ta if they modified
            else:
                return 'instructor'  # They managed it, must be instructor
        else:
            # They have a role but never modified - they only took the class
            return 'student'

    # No classRoles - check if they modified quizzes
    if modified_this_class:
        # They modified quizzes but weren't in classRoles
        # They must have been managing this class
        return 'instructor'

    # Default to student (safe default)
    return 'student'


def get_all_user_classes(user: Dict[str, Any]) -> Set[str]:
    """
    Get all classes a user had any access to.

    Args:
        user: User document

    Returns:
        Set of class IDs
    """
    classes = set()

    # From classRoles
    class_roles = user.get('classRoles', {})
    classes.update(class_roles.keys())

    # From accessible_classes
    accessible_classes = user.get('accessible_classes', [])
    classes.update(accessible_classes)

    return classes


def migrate_user(
    user: Dict[str, Any],
    user_modifications: Dict[str, Set[str]],
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Migrate a single user from old schema to new schema.

    Args:
        user: User document to migrate
        user_modifications: Map of user_id -> classes they modified
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

    # Get all classes user had access to
    user_classes = get_all_user_classes(user)

    if not user_classes:
        return {
            'user_id': user_id,
            'status': 'skipped',
            'reason': 'No classes to migrate'
        }

    # Build class_memberships
    class_memberships = {}
    migration_time = datetime.datetime.utcnow().isoformat()
    role_assignments = []

    for class_id in user_classes:
        role = determine_role_for_class(user, class_id, user_modifications)

        class_memberships[class_id] = {
            'role': role,
            'assigned_at': migration_time,
            'assigned_by': 'migration_script_v2',
            'migrated_from': 'quiz_modification_analysis',
            'modified_quizzes': class_id in user_modifications.get(user_id, set())
        }

        role_assignments.append(f"{class_id}:{role}")

    # Build updated user document
    updated_user = {**user}
    updated_user['class_memberships'] = class_memberships

    # Save to database if not dry run
    if not dry_run:
        db = get_database_adapter()
        db.upsert('users', updated_user)

    return {
        'user_id': user_id,
        'status': 'migrated',
        'classes_migrated': len(class_memberships),
        'role_assignments': role_assignments,
        'modified_classes': list(user_modifications.get(user_id, set()))
    }


def validate_migration(user: Dict[str, Any]) -> List[str]:
    """
    Validate that a migrated user has valid class_memberships.

    Args:
        user: User document to validate

    Returns:
        List of validation issues (empty if valid)
    """
    issues = []
    user_id = user.get('id')

    class_memberships = user.get('class_memberships')
    if not class_memberships:
        issues.append(f"No class_memberships found")
        return issues

    if not isinstance(class_memberships, dict):
        issues.append(f"class_memberships is not a dict")
        return issues

    for class_id, membership in class_memberships.items():
        if not isinstance(membership, dict):
            issues.append(f"Membership for {class_id} is not a dict")
            continue

        role = membership.get('role')
        if role not in ['instructor', 'ta', 'student']:
            issues.append(f"Invalid role for {class_id}: {role}")

        if not membership.get('assigned_at'):
            issues.append(f"Missing assigned_at for {class_id}")

    return issues


def migrate_all_users(dry_run: bool = True, verbose: bool = True):
    """
    Migrate all users from old schema to new schema.

    Args:
        dry_run: If True, don't save changes, just report what would happen
        verbose: If True, print detailed progress
    """
    db = get_database_adapter()

    print("=" * 80)
    print("CONSERVATIVE USER PERMISSION MIGRATION (Quiz Modification Analysis)")
    print("=" * 80)
    print()

    if dry_run:
        print("DRY RUN MODE - No changes will be saved")
    else:
        print("LIVE MODE - Changes will be saved to database")
    print()

    # Step 1: Build quiz modification map
    print("Step 1: Analyzing quiz modifications...")
    user_modifications = build_quiz_modification_map()
    print(f"  Found {len(user_modifications)} users who modified quizzes")
    print(f"  Total modifications tracked across all classes")
    print()

    if verbose:
        print("  Top quiz modifiers:")
        sorted_modifiers = sorted(
            user_modifications.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:10]
        for user_id, classes in sorted_modifiers:
            print(f"    {user_id}: {len(classes)} classes - {', '.join(sorted(classes))}")
        print()

    # Step 2: Get all users
    print("Step 2: Loading users...")
    all_users = db.query('users', filters={})
    print(f"  Found {len(all_users)} users")
    print()

    # Step 3: Migrate users
    print("Step 3: Migrating users...")
    results = {
        'migrated': [],
        'skipped': [],
        'errors': []
    }

    for user in all_users:
        try:
            result = migrate_user(user, user_modifications, dry_run=dry_run)
            status = result['status']
            results[status].append(result)

            if verbose and status == 'migrated':
                user_id = result['user_id']
                classes = result['classes_migrated']
                assignments = ', '.join(result['role_assignments'])
                print(f"  ✓ {user_id}: {classes} classes - {assignments}")

        except Exception as e:
            results['errors'].append({
                'user_id': user.get('id'),
                'error': str(e)
            })
            print(f"  ✗ {user.get('id')}: ERROR - {e}")

    print()
    print("=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Migrated: {len(results['migrated'])}")
    print(f"Skipped:  {len(results['skipped'])}")
    print(f"Errors:   {len(results['errors'])}")
    print()

    # Step 4: Validate migrations
    if results['migrated']:
        print("Step 4: Validating migrations...")
        validation_issues = []

        for result in results['migrated']:
            user_id = result['user_id']
            user = db.get('users', user_id)
            issues = validate_migration(user)
            if issues:
                validation_issues.append({'user_id': user_id, 'issues': issues})

        if validation_issues:
            print(f"  ⚠️  Found {len(validation_issues)} users with validation issues:")
            for item in validation_issues:
                print(f"    {item['user_id']}:")
                for issue in item['issues']:
                    print(f"      - {issue}")
        else:
            print("  ✓ All migrations valid!")
        print()

    # Show detailed statistics
    if results['migrated']:
        print("ROLE DISTRIBUTION:")
        role_counts = defaultdict(int)
        for result in results['migrated']:
            for assignment in result['role_assignments']:
                role = assignment.split(':')[1]
                role_counts[role] += 1

        for role in ['instructor', 'ta', 'student']:
            count = role_counts[role]
            print(f"  {role}: {count}")
        print()

    if dry_run:
        print("=" * 80)
        print("DRY RUN COMPLETE - No changes were saved")
        print("Run with --execute to apply these changes")
        print("=" * 80)
    else:
        print("=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Migrate users to class_memberships with quiz modification analysis'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute migration (default is dry-run)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce verbosity'
    )

    args = parser.parse_args()

    migrate_all_users(
        dry_run=not args.execute,
        verbose=not args.quiet
    )
