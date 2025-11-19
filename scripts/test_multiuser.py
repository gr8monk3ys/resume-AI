"""
Manual test script for multi-user authentication system.

Run this script to verify all authentication functionality works correctly.
This script tests database operations, not UI interactions.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.auth_database import (
    init_auth_database,
    create_user,
    authenticate_user,
    get_user_by_username,
    change_password,
    delete_user,
    get_all_users
)
from models.database import init_database, get_or_create_profile_for_user, get_db_connection

def print_header(text):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_test(test_name, passed, details=""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"     {details}")

def cleanup_test_data():
    """Clean up test data from previous runs."""
    import sqlite3
    from models.auth_database import AUTH_DATABASE_PATH
    from models.database import DATABASE_PATH

    # Clean up test users from auth database
    try:
        conn = sqlite3.connect(AUTH_DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username LIKE 'testuser%' OR email LIKE 'test%@example.com'")
        cursor.execute("DELETE FROM login_attempts WHERE username LIKE 'testuser%'")
        cursor.execute("DELETE FROM account_lockouts WHERE username LIKE 'testuser%'")
        cursor.execute("DELETE FROM audit_logs WHERE username LIKE 'testuser%'")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Could not clean auth database: {e}")

    # Clean up test data from application database
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        # Get profile IDs for test users, then delete related data
        cursor.execute("DELETE FROM job_applications WHERE profile_id IN (SELECT id FROM profiles WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'testuser%'))")
        cursor.execute("DELETE FROM resumes WHERE profile_id IN (SELECT id FROM profiles WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'testuser%'))")
        cursor.execute("DELETE FROM cover_letters WHERE profile_id IN (SELECT id FROM profiles WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'testuser%'))")
        cursor.execute("DELETE FROM career_journal WHERE profile_id IN (SELECT id FROM profiles WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'testuser%'))")
        cursor.execute("DELETE FROM profiles WHERE name LIKE 'Test User%' OR email LIKE 'test%@example.com'")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Could not clean application database: {e}")

def main():
    """Run all multi-user tests."""
    print_header("MULTI-USER AUTHENTICATION SYSTEM TESTS")

    # Clean up any test data from previous runs
    print("\n🧹 Cleaning up test data from previous runs...")
    cleanup_test_data()
    print("✅ Cleanup complete\n")

    # Track results
    total_tests = 0
    passed_tests = 0

    # Test 1: Database Initialization
    print_header("Test 1: Database Initialization")
    total_tests += 1
    try:
        init_auth_database()
        init_database()
        print_test("Initialize databases", True)
        passed_tests += 1
    except Exception as e:
        print_test("Initialize databases", False, str(e))

    # Test 2: User Creation
    print_header("Test 2: User Creation")

    # Test 2.1: Create valid user
    total_tests += 1
    try:
        user_id = create_user("testuser1", "test1@example.com", "Test@123", "Test User 1")
        print_test("Create user with valid data", user_id > 0, f"User ID: {user_id}")
        if user_id > 0:
            passed_tests += 1
    except Exception as e:
        print_test("Create user with valid data", False, str(e))

    # Test 2.2: Duplicate username
    total_tests += 1
    try:
        create_user("testuser1", "test2@example.com", "Test@123", "Test User 2")
        print_test("Reject duplicate username", False, "Should have raised ValueError")
    except ValueError as e:
        print_test("Reject duplicate username", True, "Correctly rejected")
        passed_tests += 1
    except Exception as e:
        print_test("Reject duplicate username", False, str(e))

    # Test 2.3: Duplicate email
    total_tests += 1
    try:
        create_user("testuser2", "test1@example.com", "Test@123", "Test User 2")
        print_test("Reject duplicate email", False, "Should have raised ValueError")
    except ValueError as e:
        print_test("Reject duplicate email", True, "Correctly rejected")
        passed_tests += 1
    except Exception as e:
        print_test("Reject duplicate email", False, str(e))

    # Test 3: Authentication
    print_header("Test 3: User Authentication")

    # Test 3.1: Valid credentials
    total_tests += 1
    try:
        user = authenticate_user("testuser1", "Test@123")
        print_test("Authenticate with valid credentials", user is not None, f"User: {user['username']}")
        if user:
            passed_tests += 1
    except Exception as e:
        print_test("Authenticate with valid credentials", False, str(e))

    # Test 3.2: Invalid password
    total_tests += 1
    try:
        user = authenticate_user("testuser1", "wrongpassword")
        print_test("Reject invalid password", user is None, "Correctly rejected")
        if user is None:
            passed_tests += 1
    except Exception as e:
        print_test("Reject invalid password", False, str(e))

    # Test 3.3: Non-existent user
    total_tests += 1
    try:
        user = authenticate_user("nonexistent", "Test@123")
        print_test("Reject non-existent user", user is None, "Correctly rejected")
        if user is None:
            passed_tests += 1
    except Exception as e:
        print_test("Reject non-existent user", False, str(e))

    # Test 4: Profile Creation
    print_header("Test 4: Profile Creation for Users")

    # Test 4.1: Get/create profile for user
    total_tests += 1
    try:
        user = get_user_by_username("testuser1")
        profile = get_or_create_profile_for_user(user['id'], user['full_name'], user['email'])
        print_test("Create profile for user", profile is not None, f"Profile ID: {profile['id']}")
        if profile:
            passed_tests += 1
    except Exception as e:
        print_test("Create profile for user", False, str(e))

    # Test 4.2: Get existing profile
    total_tests += 1
    try:
        user = get_user_by_username("testuser1")
        profile1 = get_or_create_profile_for_user(user['id'])
        profile2 = get_or_create_profile_for_user(user['id'])
        same_profile = profile1['id'] == profile2['id']
        print_test("Get existing profile (no duplicate)", same_profile, f"Profile ID: {profile1['id']}")
        if same_profile:
            passed_tests += 1
    except Exception as e:
        print_test("Get existing profile (no duplicate)", False, str(e))

    # Test 5: Data Isolation
    print_header("Test 5: Data Isolation Between Users")

    # Test 5.1: Create second user
    total_tests += 1
    try:
        user2_id = create_user("testuser2", "test2@example.com", "Test@456", "Test User 2")
        print_test("Create second user", user2_id > 0, f"User ID: {user2_id}")
        if user2_id > 0:
            passed_tests += 1
    except Exception as e:
        print_test("Create second user", False, str(e))

    # Test 5.2: Create profiles for both users
    total_tests += 1
    try:
        user1 = get_user_by_username("testuser1")
        user2 = get_user_by_username("testuser2")
        profile1 = get_or_create_profile_for_user(user1['id'])
        profile2 = get_or_create_profile_for_user(user2['id'])
        different_profiles = profile1['id'] != profile2['id']
        print_test("Users have different profiles", different_profiles,
                   f"Profile1: {profile1['id']}, Profile2: {profile2['id']}")
        if different_profiles:
            passed_tests += 1
    except Exception as e:
        print_test("Users have different profiles", False, str(e))

    # Test 5.3: Add data for each user
    total_tests += 1
    try:
        user1 = get_user_by_username("testuser1")
        user2 = get_user_by_username("testuser2")
        profile1 = get_or_create_profile_for_user(user1['id'])
        profile2 = get_or_create_profile_for_user(user2['id'])

        # Add job application for user 1
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO job_applications (profile_id, company, position, status)
                VALUES (?, ?, ?, ?)
            ''', (profile1['id'], 'Company A', 'Engineer', 'Applied'))

            # Add job application for user 2
            cursor.execute('''
                INSERT INTO job_applications (profile_id, company, position, status)
                VALUES (?, ?, ?, ?)
            ''', (profile2['id'], 'Company B', 'Designer', 'Applied'))

            conn.commit()

            # Verify user 1 only sees their data
            cursor.execute('SELECT COUNT(*) as count FROM job_applications WHERE profile_id = ?',
                          (profile1['id'],))
            user1_count = cursor.fetchone()['count']

            # Verify user 2 only sees their data
            cursor.execute('SELECT COUNT(*) as count FROM job_applications WHERE profile_id = ?',
                          (profile2['id'],))
            user2_count = cursor.fetchone()['count']

            isolated = user1_count == 1 and user2_count == 1
            print_test("Data isolation works", isolated,
                      f"User1: {user1_count} app, User2: {user2_count} app")
            if isolated:
                passed_tests += 1
    except Exception as e:
        print_test("Data isolation works", False, str(e))

    # Test 6: Password Change
    print_header("Test 6: Password Management")

    # Test 6.1: Change password with correct old password
    total_tests += 1
    try:
        user = get_user_by_username("testuser1")
        success = change_password(user['id'], "Test@123", "NewTest@123")
        print_test("Change password (valid old password)", success)
        if success:
            passed_tests += 1
    except Exception as e:
        print_test("Change password (valid old password)", False, str(e))

    # Test 6.2: Verify new password works
    total_tests += 1
    try:
        user = authenticate_user("testuser1", "NewTest@123")
        print_test("Authenticate with new password", user is not None)
        if user:
            passed_tests += 1
    except Exception as e:
        print_test("Authenticate with new password", False, str(e))

    # Test 6.3: Old password no longer works
    total_tests += 1
    try:
        user = authenticate_user("testuser1", "Test@123")
        print_test("Old password rejected", user is None)
        if user is None:
            passed_tests += 1
    except Exception as e:
        print_test("Old password rejected", False, str(e))

    # Test 6.4: Change password with wrong old password
    total_tests += 1
    try:
        user = get_user_by_username("testuser1")
        success = change_password(user['id'], "WrongOld@123", "Another@123")
        print_test("Reject password change (invalid old)", not success)
        if not success:
            passed_tests += 1
    except Exception as e:
        print_test("Reject password change (invalid old)", False, str(e))

    # Test 7: User Management
    print_header("Test 7: User Management")

    # Test 7.1: Get all users
    total_tests += 1
    try:
        users = get_all_users()
        # Should have at least testuser1 and testuser2 from earlier tests
        has_users = len(users) >= 2
        print_test("Get all users", has_users, f"Found {len(users)} users")
        if has_users:
            passed_tests += 1
    except Exception as e:
        print_test("Get all users", False, str(e))

    # Test 7.2: Deactivate user
    total_tests += 1
    try:
        user = get_user_by_username("testuser2")
        success = delete_user(user['id'])  # Soft delete (deactivate)
        print_test("Deactivate user", success)
        if success:
            passed_tests += 1
    except Exception as e:
        print_test("Deactivate user", False, str(e))

    # Test 7.3: Deactivated user cannot login
    total_tests += 1
    try:
        user = authenticate_user("testuser2", "Test@456")
        print_test("Deactivated user cannot login", user is None)
        if user is None:
            passed_tests += 1
    except Exception as e:
        print_test("Deactivated user cannot login", False, str(e))

    # Final Summary
    print_header("TEST SUMMARY")
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Multi-user system is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} TEST(S) FAILED! Review failures above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
