#!/bin/bash
# Test runner script for ResuBoost AI Backend
#
# This script sets up the test environment and runs pytest with proper
# configuration. It ensures tests run in isolation without external services.
#
# Usage:
#   ./run_tests.sh              # Run all tests
#   ./run_tests.sh -v           # Run with verbose output
#   ./run_tests.sh tests/test_auth.py  # Run specific test file
#   ./run_tests.sh -k "test_login"     # Run tests matching pattern
#   ./run_tests.sh --cov=app    # Run with coverage

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set test environment variables
export DATABASE_URL="sqlite:///:memory:"
export LLM_PROVIDER="mock"
export SECRET_KEY="test-secret-key-for-testing-only"
export ENABLE_RATE_LIMITING="false"
export ENABLE_AUDIT_LOGGING="false"
export ENABLE_SECURITY_HEADERS="false"
export ENABLE_INPUT_SANITIZATION="false"
export ENABLE_SCHEDULER="false"
export DEBUG="false"

# Add backend directory to PYTHONPATH
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Print environment info
echo "========================================"
echo "ResuBoost AI Backend Test Runner"
echo "========================================"
echo "Working directory: $SCRIPT_DIR"
echo "Python: $(python --version 2>&1)"
echo "LLM_PROVIDER: $LLM_PROVIDER"
echo "DATABASE_URL: $DATABASE_URL"
echo "========================================"
echo ""

# Run pytest with all arguments passed to this script
python -m pytest tests/ "$@"
