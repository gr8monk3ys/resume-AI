"""
Setup script for multi-user mode.

This script:
1. Initializes the authentication database
2. Creates demo users for testing
3. Migrates existing data (if any) to default user
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from models.auth_database import init_auth_database, create_user, get_user_by_username
from models.database import init_database

def setup_multi_user():
    """Set up multi-user authentication system."""
    print("=" * 70)
    print(" " * 20 + "MULTI-USER SETUP")
    print("=" * 70)
    print()

    # 1. Initialize auth database
    print("1. Initializing authentication database...")
    init_auth_database()
    print("   ✅ Auth database initialized")

    # 2. Initialize main database (with updated schema)
    print("\n2. Initializing main database...")
    init_database()
    print("   ✅ Main database initialized")

    # 3. Create demo user
    print("\n3. Creating demo user...")
    try:
        demo_user_id = create_user(
            username="demo",
            email="demo@resuboost.ai",
            password="demo123",
            full_name="Demo User"
        )
        print(f"   ✅ Demo user created (ID: {demo_user_id})")
        print("      Username: demo")
        print("      Password: demo123")
    except ValueError:
        print("   ⚠️  Demo user already exists")

    # 4. Create admin user with random password
    print("\n4. Creating admin user...")
    try:
        import secrets
        import string

        # Generate secure random password
        alphabet = string.ascii_letters + string.digits + string.punctuation
        admin_password = ''.join(secrets.choice(alphabet) for i in range(16))

        admin_user_id = create_user(
            username="admin",
            email="admin@resuboost.ai",
            password=admin_password,
            full_name="Administrator",
            is_admin=True
        )
        print(f"   ✅ Admin user created (ID: {admin_user_id})")
        print("      Username: admin")
        print(f"      Password: {admin_password}")
        print()
        print("      ⚠️  IMPORTANT: SAVE THIS PASSWORD NOW!")
        print("      This password will NOT be shown again.")
        print("      Write it down or store it in a password manager.")
    except ValueError:
        print("   ⚠️  Admin user already exists")

    # 5. Create test users
    print("\n5. Creating test users...")
    test_users = [
        ("alice", "alice@example.com", "alice123", "Alice Johnson"),
        ("bob", "bob@example.com", "bob123", "Bob Smith"),
    ]

    for username, email, password, full_name in test_users:
        try:
            user_id = create_user(username, email, password, full_name)
            print(f"   ✅ User '{username}' created (ID: {user_id})")
        except ValueError:
            print(f"   ⚠️  User '{username}' already exists")

    print("\n" + "=" * 70)
    print("SETUP COMPLETE!")
    print("=" * 70)
    print()
    print("🎉 Multi-user authentication is now enabled!")
    print()
    print("Test Accounts:")
    print("  1. Demo User:  username=demo,  password=demo123")
    print("  2. Admin:      username=admin, password=[SHOWN DURING SETUP]")
    print("  3. Alice:      username=alice, password=alice123")
    print("  4. Bob:        username=bob,   password=bob123")
    print()
    print("Next Steps:")
    print("  1. Run: streamlit run app.py")
    print("  2. Go to the Login page")
    print("  3. Log in with one of the test accounts")
    print("  4. Start using ResuBoost AI!")
    print()
    print("⚠️  IMPORTANT:")
    print("  - Admin password was randomly generated - save it securely")
    print("  - Create your own account for production use")
    print("  - Delete demo/test accounts before production deployment")
    print("=" * 70)

if __name__ == "__main__":
    setup_multi_user()
