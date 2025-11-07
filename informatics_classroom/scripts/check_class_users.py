#!/usr/bin/env python3
"""
Check which users have access to a specific class.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.factory import get_database_adapter


def check_class_users(class_id: str):
    """Check which users have access to a class."""
    db = get_database_adapter()

    print(f"Checking users with access to class: {class_id}")
    print("-" * 80)

    users = db.query('users', filters={})
    print(f"Total users in database: {len(users)}")
    print()

    users_with_access = []

    for user in users:
        user_id = user.get('id')
        has_access = False
        access_type = None

        # Check class_memberships (new format)
        class_memberships = user.get('class_memberships', {})
        if isinstance(class_memberships, dict) and class_id in class_memberships:
            has_access = True
            membership = class_memberships[class_id]
            role = membership.get('role') if isinstance(membership, dict) else membership
            access_type = f"class_memberships (role: {role})"

        # Check classRoles (intermediate format)
        elif class_id in user.get('classRoles', {}):
            has_access = True
            role = user['classRoles'][class_id]
            access_type = f"classRoles (role: {role})"

        # Check accessible_classes (old format)
        elif class_id in user.get('accessible_classes', []):
            has_access = True
            global_role = user.get('role', 'student')
            access_type = f"accessible_classes (global role: {global_role})"

        if has_access:
            users_with_access.append({
                'user_id': user_id,
                'email': user.get('email'),
                'access_type': access_type,
                'global_roles': user.get('roles', [])
            })

    if users_with_access:
        print(f"Found {len(users_with_access)} user(s) with access to {class_id}:")
        print()
        for u in users_with_access:
            print(f"  User: {u['user_id']} ({u['email']})")
            print(f"    Access via: {u['access_type']}")
            print(f"    Global roles: {u['global_roles']}")
            print()
    else:
        print(f"No users found with access to {class_id}")
        print()
        print("This could mean:")
        print("  1. No users have been assigned to this class yet")
        print("  2. The migration script hasn't been run")
        print("  3. Users have access via old schema (accessible_classes) but with wrong global role")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_class_users.py <class_id>")
        print("Example: python check_class_users.py cda")
        sys.exit(1)

    class_id = sys.argv[1]
    check_class_users(class_id)
