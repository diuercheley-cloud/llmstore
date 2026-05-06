#!/bin/bash

# Load environment variables if .env exists
if [ -f ".env" ]; then
  source .env
elif [ -f "../.env" ]; then
  source ../.env
fi

# Configuration
PORT="${PORT:-${HOST_PORT:-8000}}"
URL="http://localhost:$PORT/developer-docs"

echo "========================================"
echo "Validating Local Developer Documentation"
echo "========================================"

# Fetch documentation
echo "Fetching $URL..."
CONTENT=$(curl -s -f "$URL")

if [ $? -ne 0 ]; then
  echo "❌ Failed to fetch developer docs at $URL. Is the server running?"
  exit 1
fi

echo "✅ Successfully fetched developer docs."

# Initialize validation flag
ALL_PASSED=true

# Validation checks
check_content() {
  local pattern="$1"
  local description="$2"
  
  if echo "$CONTENT" | grep -qiE "$pattern"; then
    echo "✅ Found $description"
  else
    echo "❌ Missing $description"
    ALL_PASSED=false
  fi
}

check_not_content() {
  local pattern="$1"
  local description="$2"
  
  if echo "$CONTENT" | grep -qiE "$pattern"; then
    echo "❌ Found forbidden $description"
    ALL_PASSED=false
  else
    echo "✅ No $description found"
  fi
}

echo ""
echo "Running validation checks..."

check_content "localhost|127\.0\.0\.1" "localhost reference"
check_content "curl\s" "cURL example"
check_content "import requests" "Python example"
check_content "fetch" "Node.js example"
check_content "/v1/chat/completions" "/v1/chat/completions endpoint"

# Check for external mandatory domains like 'api.openai.com' or other external ones if used as mandatory in examples
check_not_content "api\.openai\.com" "mandatory external domain (api.openai.com)"

echo ""
if [ "$ALL_PASSED" = true ]; then
  echo "✅ All validations passed!"
  exit 0
else
  echo "❌ Validations failed!"
  exit 1
fi
