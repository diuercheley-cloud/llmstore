#!/usr/bin/env bash

# lib/redaction.sh
# Centralized redaction logic for llm-inference-stack.
# Provides functions to mask sensitive information in strings and files.

# Ensure we don't leak anything if someone sources this twice or has weird env
MASK_REPLACEMENT="[REDACTED]"

# Regex patterns for sensitive data (aligned with check-secrets.sh)
REDACT_PATTERNS=(
    "sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"
    "ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}"
    "JWT_SECRET=[a-zA-Z0-9._-]{12,}"
    "ghp_[a-zA-Z0-9]{36}"
    "Bearer [a-zA-Z0-9._-]{20,}"
    "-----BEGIN [A-Z ]*PRIVATE KEY-----"
    "[a-zA-Z0-9_+.-]+:[a-zA-Z0-9_+.-]+@([a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}|localhost|127\\.0\\.0\\.1)"
    "Authorization: Bearer [a-zA-Z0-9._-]{20,}"
    "X-Admin-Token: [a-zA-Z0-9._-]{12,}"
    "API_KEY=[a-zA-Z0-9._-]{12,}"
    "DATABASE_URL=[a-z]+://[a-zA-Z0-9_+.-]+:[a-zA-Z0-9_+.-]+@[a-zA-Z0-9.-]+"
    "REDIS_URL=[a-z]+://:[a-zA-Z0-9_+.-]+@[a-zA-Z0-9.-]+"
)

# Safe patterns that should NOT be redacted (to avoid false positives)
REDACT_SAFE_PATTERNS=(
    "sk-local-example"
    "admin-token-123"
    "your-api-key"
    "changeme"
    "example"
    "localhost"
    "admin-token-example"
    "sk-example"
    "__redacted__"
    "FAKE SECRET FOR TESTS ONLY"
)

# Function to redact a string from stdin
redact_stream() {
    local input
    # Read all input
    input=$(cat)

    # Apply each pattern
    for pattern in "${REDACT_PATTERNS[@]}"; do
        # We use a trick: if it's a "SAFE" pattern, we don't want to redact it.
        # But sed doesn't easily support negative lookbehind/ahead for all patterns.
        # So we'll use python for robust redaction if available, otherwise fallback to basic sed.
        if command -v python3 >/dev/null 2>&1; then
            input=$(printf '%s' "$input" | python3 -c '
import sys
import re

content = sys.stdin.read()
patterns = [
    r"sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}",
    r"ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}",
    r"JWT_SECRET=[a-zA-Z0-9._-]{12,}",
    r"ghp_[a-zA-Z0-9]{36}",
    r"Bearer [a-zA-Z0-9._-]{20,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"[a-zA-Z0-9_+.-]+:[a-zA-Z0-9_+.-]+@(?:[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|localhost|127\.0\.0\.1)",
    r"Authorization:\s*Bearer\s+[a-zA-Z0-9._-]{20,}",
    r"X-Admin-Token:\s*[a-zA-Z0-9._-]{12,}",
    r"API_KEY=[a-zA-Z0-9._-]{12,}",
    r"DATABASE_URL=[a-z]+://[^:]+:[^@]+@[^/]+",
    r"REDIS_URL=[a-z]+://:[^@]+@[^/]+"
]

safe_patterns = [
    r"sk-local-example",
    r"admin-token-123",
    r"your-api-key",
    r"changeme",
    r"example",
    r"localhost",
    r"admin-token-example",
    r"sk-example",
    r"__redacted__",
    r"FAKE SECRET FOR TESTS ONLY"
]

def redact(match):
    val = match.group(0)
    for safe in safe_patterns:
        if re.search(safe, val):
            return val
    # If it is a key=value pair, keep the key
    if "=" in val and not val.startswith("---"):
        key, _ = val.split("=", 1)
        return f"{key}=[REDACTED]"
    if "Bearer " in val:
        return "Bearer [REDACTED]"
    if "X-Admin-Token: " in val:
        return "X-Admin-Token: [REDACTED]"
    return "[REDACTED]"

for p in patterns:
    content = re.sub(p, redact, content)

sys.stdout.write(content)
')
        else
            # Fallback to sed (less accurate with safe patterns)
            input=$(printf '%s' "$input" | sed -E 's/sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}/[REDACTED]/g')
            input=$(printf '%s' "$input" | sed -E 's/Bearer [a-zA-Z0-9._-]{20,}/Bearer [REDACTED]/g')
            # ... add more basic ones if needed ...
        fi
    done

    printf '%s' "$input"
}

# Function to redact a file in place
redact_file_inplace() {
    local file="$1"
    [[ -f "$file" ]] || return 1
    
    local tmp
    tmp=$(mktemp)
    redact_stream < "$file" > "$tmp"
    mv "$tmp" "$file"
}

# Export for use in other scripts
export -f redact_stream redact_file_inplace
