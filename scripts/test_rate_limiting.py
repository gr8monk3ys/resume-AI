"""
Test script for login rate limiting functionality.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.rate_limiter_auth import (
    init_rate_limiting_table,
    record_failed_login,
    get_recent_failed_attempts,
    get_total_failed_attempts,
    check_login_allowed,
    lock_account,
    unlock_account,
    is_account_locked,
    clear_failed_attempts
)

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

def main():
    """Run rate limiting tests."""
    print_header("LOGIN RATE LIMITING TESTS")

    total_tests = 0
    passed_tests = 0

    # Test 1: Initialize rate limiting table
    print_header("Test 1: Initialize Rate Limiting")
    total_tests += 1
    try:
        init_rate_limiting_table()
        print_test("Initialize rate limiting table", True)
        passed_tests += 1
    except Exception as e:
        print_test("Initialize rate limiting table", False, str(e))

    # Test 2: Record failed attempts
    print_header("Test 2: Record Failed Login Attempts")
    test_user = "ratelimit_test_user"

    # Clear any existing attempts
    clear_failed_attempts(test_user)

    total_tests += 1
    try:
        record_failed_login(test_user, "127.0.0.1", "Test User Agent")
        attempts = get_recent_failed_attempts(test_user)
        print_test("Record single failed attempt", attempts == 1, f"Attempts: {attempts}")
        if attempts == 1:
            passed_tests += 1
    except Exception as e:
        print_test("Record single failed attempt", False, str(e))

    # Test 3: Multiple failed attempts
    total_tests += 1
    try:
        # Add 3 more attempts (total should be 4)
        for i in range(3):
            record_failed_login(test_user)

        attempts = get_recent_failed_attempts(test_user)
        print_test("Record multiple failed attempts", attempts == 4, f"Attempts: {attempts}")
        if attempts == 4:
            passed_tests += 1
    except Exception as e:
        print_test("Record multiple failed attempts", False, str(e))

    # Test 4: Rate limiting kicks in at 5 attempts
    total_tests += 1
    try:
        # Add 1 more attempt (total = 5)
        record_failed_login(test_user)

        allowed, reason, wait_seconds = check_login_allowed(test_user)
        print_test("Rate limiting at 5 attempts", not allowed,
                  f"Allowed: {allowed}, Reason: {reason}")
        if not allowed:
            passed_tests += 1
    except Exception as e:
        print_test("Rate limiting at 5 attempts", False, str(e))

    # Test 5: Different user not affected
    test_user2 = "ratelimit_test_user2"
    total_tests += 1
    try:
        clear_failed_attempts(test_user2)
        allowed, reason, wait_seconds = check_login_allowed(test_user2)
        print_test("Different user not affected", allowed,
                  f"User2 allowed: {allowed}")
        if allowed:
            passed_tests += 1
    except Exception as e:
        print_test("Different user not affected", False, str(e))

    # Test 6: Account lockout at 10 attempts
    test_user3 = "ratelimit_test_user3"
    total_tests += 1
    try:
        clear_failed_attempts(test_user3)

        # Add 10 failed attempts
        for i in range(10):
            record_failed_login(test_user3)

        # Check if locked
        allowed, reason, wait_seconds = check_login_allowed(test_user3)
        is_locked, lock_reason, _ = is_account_locked(test_user3)

        print_test("Account locked at 10 attempts", not allowed and is_locked,
                  f"Locked: {is_locked}, Reason: {lock_reason}")
        if not allowed and is_locked:
            passed_tests += 1
    except Exception as e:
        print_test("Account locked at 10 attempts", False, str(e))

    # Test 7: Unlock account
    total_tests += 1
    try:
        unlock_account(test_user3)
        is_locked, lock_reason, _ = is_account_locked(test_user3)
        print_test("Unlock account", not is_locked, f"Still locked: {is_locked}")
        if not is_locked:
            passed_tests += 1
    except Exception as e:
        print_test("Unlock account", False, str(e))

    # Test 8: Clear failed attempts
    total_tests += 1
    try:
        clear_failed_attempts(test_user)
        attempts = get_recent_failed_attempts(test_user)
        print_test("Clear failed attempts", attempts == 0, f"Attempts after clear: {attempts}")
        if attempts == 0:
            passed_tests += 1
    except Exception as e:
        print_test("Clear failed attempts", False, str(e))

    # Final Summary
    print_header("TEST SUMMARY")
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Rate limiting is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} TEST(S) FAILED! Review failures above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
