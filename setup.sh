#!/bin/bash
# Quick setup script for ResuBoost AI

set -e  # Exit on error

echo "=========================================="
echo "ResuBoost AI - Quick Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || {
    echo "❌ Python 3 not found. Please install Python 3.7+";
    exit 1;
}
echo "✅ Python found"
echo ""

# Check if pip is installed
echo "Checking pip..."
python3 -m pip --version || {
    echo "❌ pip not found. Please install pip";
    exit 1;
}
echo "✅ pip found"
echo ""

# Install dependencies
echo "Installing dependencies..."
python3 -m pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env and add your OPENAI_API_KEY"
    echo ""
    echo "Open .env and replace 'your_openai_api_key_here' with your actual key"
    echo "Get your key from: https://platform.openai.com/api-keys"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Initialize database
echo "Initializing database..."
python3 << EOF
from models.database import init_database
init_database()
print("✅ Database initialized")
EOF
echo ""

# Run tests
echo "Running tests..."
python3 test_app.py
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Setup Complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Edit .env and add your OPENAI_API_KEY (if you haven't)"
    echo "2. Run the app: streamlit run app.py"
    echo "3. Open your browser to: http://localhost:8501"
    echo ""
    echo "Documentation:"
    echo "- README.md - User guide"
    echo "- DEPLOYMENT.md - Deployment guide"
    echo "- HONEST_ASSESSMENT.md - Code review"
    echo ""
    echo "Need help? Check the docs or run: python3 test_app.py"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "⚠️  Setup completed with issues"
    echo "=========================================="
    echo ""
    echo "Some tests failed. Please check:"
    echo "1. Your OPENAI_API_KEY in .env"
    echo "2. All dependencies installed correctly"
    echo "3. Python version is 3.7+"
    echo ""
    echo "Run 'python3 test_app.py' for details"
    echo ""
fi
