#!/usr/bin/env python3
"""
Quick script to update a user's global role to admin.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.factory import get_database_adapter


def update_user_to_admin(user_id: str):
    """Update a user's global role to admin."""
    db = get_database_adapter()

    # Get the user
    user = db.get('users', user_id)
    if not user:
        print(f"Error: User {user_id} not found")
        return False

    print(f"Current user data:")
    print(f"  ID: {user.get('id')}")
    print(f"  Email: {user.get('email')}")
    print(f"  Current roles: {user.get('roles', [])}")

    # Update to admin
    user['roles'] = ['admin']

    # Save
    db.upsert('users', user)

    print(f"\nUpdated user {user_id} to admin role!")

    # Verify
    updated_user = db.get('users', user_id)
    print(f"New roles: {updated_user.get('roles', [])}")

    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python update_user_role.py <user_id>")
        print("Example: python update_user_role.py rbarre16")
        sys.exit(1)

    user_id = sys.argv[1]
    success = update_user_to_admin(user_id)

    sys.exit(0 if success else 1)
