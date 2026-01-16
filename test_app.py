#!/usr/bin/env python3
"""
Comprehensive test script for ResuBoost AI
Tests core functionality without requiring Streamlit
"""

import os
import sys


def test_imports():
    """Test all critical imports."""
    print("Testing imports...")
    errors = []

    try:
        from models.database import get_db_connection, get_or_create_default_profile, init_database

        print("  ✓ Database models")
    except Exception as e:
        errors.append(f"Database models: {e}")

    try:
        from services.llm_service import LLMService, get_llm_service

        print("  ✓ LLM service")
    except Exception as e:
        errors.append(f"LLM service: {e}")

    try:
        from services.resume_analyzer import ATSAnalyzer, extract_keywords

        print("  ✓ Resume analyzer")
    except Exception as e:
        errors.append(f"Resume analyzer: {e}")

    try:
        from utils.file_parser import extract_text_from_upload, parse_file

        print("  ✓ File parser")
    except Exception as e:
        errors.append(f"File parser: {e}")

    try:
        from utils.validators import (
            validate_email,
            validate_github_url,
            validate_linkedin_url,
            validate_phone,
            validate_url,
        )

        print("  ✓ Validators")
    except Exception as e:
        errors.append(f"Validators: {e}")

    try:
        from utils.ui_helpers import confirm_delete, show_error_with_suggestion

        print("  ✓ UI helpers")
    except Exception as e:
        errors.append(f"UI helpers: {e}")

    try:
        import config

        print(f"  ✓ Config (v{config.APP_VERSION})")
    except Exception as e:
        errors.append(f"Config: {e}")

    return errors


def test_database():
    """Test database initialization."""
    print("\nTesting database...")
    errors = []

    try:
        from models.database import get_db_connection, get_or_create_default_profile, init_database

        # Initialize
        init_database()
        print("  ✓ Database initialized")

        # Test connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row["name"] for row in cursor.fetchall()]

        expected_tables = [
            "profiles",
            "resumes",
            "job_applications",
            "cover_letters",
            "career_journal",
        ]
        for table in expected_tables:
            if table in tables:
                print(f"  ✓ Table '{table}' exists")
            else:
                errors.append(f"Table '{table}' missing")

        # Test profile creation
        profile = get_or_create_default_profile()
        if profile and profile.get("id"):
            print(f"  ✓ Profile created (ID: {profile['id']})")
        else:
            errors.append("Profile creation failed")

    except Exception as e:
        errors.append(f"Database test failed: {e}")

    return errors


def test_validators():
    """Test validation functions."""
    print("\nTesting validators...")
    errors = []

    from utils.validators import (
        validate_email,
        validate_github_url,
        validate_linkedin_url,
        validate_phone,
        validate_url,
    )

    # Test email validation
    test_cases = [
        (validate_email, "test@example.com", True, "Valid email"),
        (validate_email, "invalid-email", False, "Invalid email"),
        (validate_url, "https://example.com", True, "Valid URL"),
        (validate_url, "not-a-url", False, "Invalid URL"),
        (validate_phone, "+1 (555) 123-4567", True, "Valid phone"),
        (validate_phone, "abc", False, "Invalid phone"),
        (validate_linkedin_url, "https://linkedin.com/in/user", True, "Valid LinkedIn"),
        (validate_github_url, "https://github.com/user", True, "Valid GitHub"),
    ]

    for validator, input_val, expected_valid, desc in test_cases:
        is_valid, _ = validator(input_val)
        if is_valid == expected_valid:
            print(f"  ✓ {desc}")
        else:
            errors.append(f"{desc}: expected {expected_valid}, got {is_valid}")

    return errors


def test_ats_analyzer():
    """Test ATS scoring."""
    print("\nTesting ATS analyzer...")
    errors = []

    try:
        from services.resume_analyzer import ATSAnalyzer

        analyzer = ATSAnalyzer()

        # Test resume
        test_resume = """
        Software Engineer with 5 years of experience in Python and JavaScript.

        EXPERIENCE:
        - Developed REST APIs using Python and Flask
        - Led team of 3 engineers
        - Improved system performance by 40%

        SKILLS:
        Python, JavaScript, React, Docker, AWS

        EDUCATION:
        BS in Computer Science
        """

        test_job_desc = """
        Looking for a Software Engineer with Python and JavaScript experience.
        Must have REST API development skills and AWS knowledge.
        """

        result = analyzer.analyze_resume(test_resume, test_job_desc)

        if "ats_score" in result:
            score = result["ats_score"]
            print(f"  ✓ ATS score calculated: {score}/100")

            if score >= 0 and score <= 100:
                print(f"  ✓ Score in valid range")
            else:
                errors.append(f"Score out of range: {score}")
        else:
            errors.append("No ATS score returned")

        if "suggestions" in result and len(result["suggestions"]) > 0:
            print(f"  ✓ Generated {len(result['suggestions'])} suggestions")
        else:
            errors.append("No suggestions generated")

    except Exception as e:
        errors.append(f"ATS analyzer test failed: {e}")

    return errors


def test_file_parser():
    """Test file parsing."""
    print("\nTesting file parser...")
    errors = []

    try:
        from utils.file_parser import parse_file

        # Test text parsing
        test_text = b"This is a test resume"
        result = parse_file(test_text, "txt")

        if result == "This is a test resume":
            print("  ✓ Text parsing works")
        else:
            errors.append(f"Text parsing failed: got '{result}'")

    except Exception as e:
        errors.append(f"File parser test failed: {e}")

    return errors


def test_config():
    """Test configuration."""
    print("\nTesting configuration...")
    errors = []

    try:
        import config

        required_settings = [
            "MAX_FILE_SIZE_MB",
            "OPENAI_MODEL",
            "APP_VERSION",
            "APP_NAME",
        ]

        for setting in required_settings:
            if hasattr(config, setting):
                value = getattr(config, setting)
                print(f"  ✓ {setting}: {value}")
            else:
                errors.append(f"Missing config: {setting}")

    except Exception as e:
        errors.append(f"Config test failed: {e}")

    return errors


def main():
    """Run all tests."""
    print("=" * 60)
    print("ResuBoost AI - Comprehensive Test Suite")
    print("=" * 60)

    all_errors = []

    # Run all tests
    all_errors.extend(test_imports())
    all_errors.extend(test_database())
    all_errors.extend(test_validators())
    all_errors.extend(test_ats_analyzer())
    all_errors.extend(test_file_parser())
    all_errors.extend(test_config())

    # Summary
    print("\n" + "=" * 60)
    if not all_errors:
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nYour ResuBoost AI installation is working correctly.")
        print("\nTo start the app:")
        print("  streamlit run app.py")
        return 0
    else:
        print(f"❌ {len(all_errors)} TEST(S) FAILED")
        print("=" * 60)
        print("\nErrors:")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
        print("\nPlease fix these issues before running the app.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
