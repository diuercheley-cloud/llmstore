#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Patterns that indicate a potential secret
SECRET_REGEXES=(
    "sk-[a-zA-Z0-9]{20,}"
    "ADMIN_TOKEN=[a-zA-Z0-9\._\-]{12,}"
    "JWT_SECRET=[a-zA-Z0-9\._\-]{12,}"
    "ghp_[a-zA-Z0-9]{36}"
    "Bearer [a-zA-Z0-9._-]{20,}"
    "-----BEGIN [A-Z ]*PRIVATE KEY-----"
    "[a-zA-Z0-9_+.-]+:[a-zA-Z0-9_+.-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|localhost|127\.0\.0\.1)"
)

# Safe patterns to ignore (examples)
SAFE_PATTERNS=(
    "admin-token-123"
    "token_admin"
    "sk-local-example"
    "your-api-key"
    "changeme"
    "example"
    "localhost"
    "admin-token-example"
    "sk-example"
    "YOUR_SECRET"
    "your_jwt_secret"
    "ChangeMe_ProdAdminToken_2026"
    "llm_gateway_dev_password"
    "test-admin-token"
    "change-this-admin-token"
    "__redacted__"
)

mask_value() {
    local val="$1"
    local len=${#val}
    if [ $len -le 8 ]; then
        echo "********"
    else
        echo "${val:0:4}****${val:len-4}"
    fi
}

check_file() {
    local file="$1"
    local found_secret=false

    # Skip binary files and some specific extensions
    if [[ "$file" =~ \.(gguf|bin|sqlite|db|bak|png|jpg|jpeg|gif|ico|pdf|zip|tar|gz)$ ]]; then
        return 0
    fi

    # Patterns to look for in content
    for regex in "${SECRET_REGEXES[@]}"; do
        # Search for pattern but exclude safe ones
        local matches
        # We use grep -E for regex, -o to show only the match, -n for line number
        # Use -- to ensure regex starting with - is not treated as an option
        matches=$(grep -Eon -- "$regex" "$file" | grep -vE "$(IFS="|"; echo "${SAFE_PATTERNS[*]}")") || true
        
        if [ -n "$matches" ]; then
            while IFS= read -r match; do
                local line_num=$(echo "$match" | cut -d: -f1)
                local secret_val=$(echo "$match" | cut -d: -f2-)
                local masked=$(mask_value "$secret_val")
                echo -e "${RED}Potential secret in $file:$line_num -> $masked${NC}"
                found_secret=true
            done <<< "$matches"
        fi
    done

    # Check for filename itself if it looks like a private key
    if [[ "$file" == *.pem ]] || [[ "$file" == *.key ]]; then
        # Check if it's not in an ignore-able place (though git ls-files should be fine)
        echo -e "${RED}Potential secret file found by extension: $file${NC}"
        found_secret=true
    fi

    if [ "$found_secret" = true ]; then
        return 1
    else
        return 0
    fi
}

install_hook() {
    echo "Installing pre-commit hook..."
    mkdir -p .githooks
    cat <<EOF > .githooks/pre-commit
#!/bin/bash
./scripts/check-secrets.sh --staged
EOF
    chmod +x .githooks/pre-commit
    git config core.hooksPath .githooks
    echo -e "${GREEN}Pre-commit hook configured to use .githooks/${NC}"
}

STAGED=false
ALL=false
CHECK_PATH=""

if [ $# -eq 0 ]; then
    echo "Usage: $0 [--staged | --all | --install-hook | --path <dir>]"
    exit 1
fi

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --staged) STAGED=true ;;
        --all) ALL=true ;;
        --install-hook) install_hook; exit 0 ;;
        --path) CHECK_PATH="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

EXIT_CODE=0

if [[ -n "${CHECK_PATH}" ]]; then
    echo "Checking directory ${CHECK_PATH} for secrets..."
    if [[ ! -d "${CHECK_PATH}" ]]; then
        echo "Directory ${CHECK_PATH} not found"
        exit 1
    fi
    while IFS= read -r f; do
        if [ -f "$f" ]; then
            check_file "$f" || EXIT_CODE=1
        fi
    done < <(find "${CHECK_PATH}" -type f)
elif [ "$STAGED" = true ]; then
    echo "Checking staged files for secrets..."
    # Get staged files, excluding deleted ones
    FILES=$(git diff --cached --name-only --diff-filter=ACM)
    for f in $FILES; do
        if [ -f "$f" ]; then
            check_file "$f" || EXIT_CODE=1
        fi
    done
elif [ "$ALL" = true ]; then
    echo "Checking all versionable files for secrets..."
    FILES=$(git ls-files)
    for f in $FILES; do
        # Skip directories we want to ignore
        if [[ "$f" =~ ^(node_modules/|models/|.venv/|data/rag_uploads/|.git/|.pytest_cache/|.ruff_cache/) ]]; then
            continue
        fi
        
        if [ -f "$f" ]; then
            check_file "$f" || EXIT_CODE=1
        fi
    done
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}No secrets found.${NC}"
else
    echo -e "${RED}Secrets detected! Please remove them before committing.${NC}"
fi

exit $EXIT_CODE
