#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SECRET_REGEXES=(
    "sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"
    "ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}"
    "JWT_SECRET=[a-zA-Z0-9._-]{12,}"
    "ghp_[a-zA-Z0-9]{36}"
    "Bearer [a-zA-Z0-9._-]{20,}"
    "-----BEGIN [A-Z ]*PRIVATE KEY-----"
    "[a-zA-Z0-9_+.-]+:[a-zA-Z0-9_+.-]+@([a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}|localhost|127\\.0\\.0\\.1)"
)

SAFE_PATTERNS=(
    "admin-token-123"
    "token_admin"
    "sk-local-example"
    "sk-demo-"
    "sk-demo-example"
    "sk-demo-xxxx"
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
    "BEGIN.PRIVATE.KEY"
    "hardcoded = "
    "os.environ.get"
    "os.getenv"
    "\\*\\*\\*REDACTED\\*\\*\\*"
    "\\*\\*\\*masked\\*\\*\\*"
    "sk-\\*\\*\\*masked\\*\\*\\*"
    "Bearer \\*\\*\\*masked\\*\\*\\*"
    "ADMIN_TOKEN=\\*\\*\\*masked\\*\\*\\*"
    "\\*\\*\\*masked\\*\\*\\*"
)

VERBOSE=false
STAGED=false
ALL=false
CHECK_PATH=""
EXIT_CODE=0

usage() {
    echo "Usage: $0 [--staged | --all | --install-hook | --path <path>] [--verbose]"
}

mask_value() {
    local value="$1"
    local len=${#value}
    if [ "$len" -le 8 ]; then
        printf '********\n'
        return
    fi
    printf '%s****%s\n' "${value:0:4}" "${value:len-4}"
}

safe_pattern_regex() {
    local joined=""
    local item
    for item in "${SAFE_PATTERNS[@]}"; do
        if [ -n "$joined" ]; then
            joined="${joined}|"
        fi
        joined="${joined}${item}"
    done
    printf '%s\n' "$joined"
}

combined_secret_regex() {
    local joined=""
    local item
    for item in "${SECRET_REGEXES[@]}"; do
        if [ -n "$joined" ]; then
            joined="${joined}|"
        fi
        joined="${joined}${item}"
    done
    printf '%s\n' "$joined"
}

log_classification() {
    local classification="$1"
    local color="$2"
    local label="$3"
    local path="$4"
    local line_num="$5"
    local value="$6"

    local location="$path"
    if [ -n "$line_num" ]; then
        location="${location}:${line_num}"
    fi

    if [ -n "$value" ]; then
        printf '%b[%s] %s %s -> %s%b\n' "$color" "$classification" "$label" "$location" "$(mask_value "$value")" "$NC"
    else
        printf '%b[%s] %s %s%b\n' "$color" "$classification" "$label" "$location" "$NC"
    fi
}

normalize_repo_relative_path() {
    local input_path="$1"
    local normalized="${input_path#./}"
    while [[ "$normalized" == *"//"* ]]; do
        normalized="${normalized//\/\//\/}"
    done
    printf '%s\n' "$normalized"
}

relative_to_base() {
    local file="$1"
    local base="$2"

    if [ -n "$base" ] && [ "$base" != "." ]; then
        local abs_file
        local abs_base
        abs_file="$(realpath "$file")"
        abs_base="$(realpath "$base")"
        if [[ "$abs_file" == "$abs_base" ]]; then
            printf '.\n'
            return
        fi
        if [[ "$abs_file" == "$abs_base/"* ]]; then
            printf '%s\n' "${abs_file#"$abs_base"/}"
            return
        fi
    fi

    normalize_repo_relative_path "$file"
}

is_text_scan_skipped() {
    local path="$1"
    [[ "$path" =~ \.(gguf|bin|sqlite|db|bak|png|jpg|jpeg|gif|ico|pdf|zip|tar|gz)$ ]]
}

is_allowed_fixture() {
    local path="$1"
    local file="$2"

    if [[ "$path" == releases/* ]] || [[ "$path" == docs/* ]] || [[ "$path" == control_plane/* ]]; then
        return 1
    fi
    if [[ "$path" != tests/fixtures/* ]] && [[ "$path" != *scripts/validate-* ]] && [[ "$path" != tests/test_* ]]; then
        return 1
    fi
    if [[ "$path" != *fake_* ]] && [[ "$path" != *fixture_* ]] && [[ "$path" != *validate-* ]] && [[ "$path" != *test_* ]]; then
        return 1
    fi
    if grep -qF "FAKE SECRET FOR TESTS ONLY" "$file" 2>/dev/null; then
        return 0
    fi
    if grep -qF "FAKE TEST KEY - DO NOT USE" "$file" 2>/dev/null; then
        return 0
    fi
    return 1
}

classify_path() {
    local path="$1"
    local file="$2"

    if is_allowed_fixture "$path" "$file"; then
        printf 'fixture_expected\n'
    elif [[ "$path" == releases/* ]]; then
        printf 'obsolete_release_file\n'
    elif [[ "$path" == artifacts/* ]]; then
        printf 'generated_artifact\n'
    elif [[ "$path" == *.env ]] || [[ "$path" == *.env.* ]] || [[ "$(basename "$path")" == ".env" ]] || [[ "$(basename "$path")" == ".env.local" ]]; then
        printf 'real_secret_suspected\n'
    else
        printf 'real_secret_suspected\n'
    fi
}

check_file() {
    local file="$1"
    local path_for_policy="$2"
    local safe_regex
    safe_regex="$(safe_pattern_regex)"
    local secret_regex
    secret_regex="$(combined_secret_regex)"

    local classification
    classification="$(classify_path "$path_for_policy" "$file")"

    local found_blocking=false
    local found_match=false

    if ! is_text_scan_skipped "$path_for_policy"; then
        local matches
        matches="$(grep -Eon -- "$secret_regex" "$file" 2>/dev/null | grep -vE "$safe_regex" || true)"

        if [ -n "$matches" ]; then
            while IFS= read -r match; do
                [ -z "$match" ] && continue
                found_match=true
                local line_num="${match%%:*}"
                local secret_value="${match#*:}"

                case "$classification" in
                    fixture_expected)
                        if [ "$VERBOSE" = true ]; then
                            log_classification "$classification" "$YELLOW" "Safe fixture in" "$path_for_policy" "$line_num" "$secret_value"
                        fi
                        ;;
                    obsolete_release_file)
                        log_classification "$classification" "$YELLOW" "Potential secret in" "$path_for_policy" "$line_num" "$secret_value"
                        found_blocking=true
                        ;;
                    generated_artifact)
                        log_classification "$classification" "$YELLOW" "Potential secret in" "$path_for_policy" "$line_num" "$secret_value"
                        found_blocking=true
                        ;;
                    *)
                        log_classification "$classification" "$RED" "Potential secret in" "$path_for_policy" "$line_num" "$secret_value"
                        found_blocking=true
                        ;;
                esac
            done <<< "$matches"
        fi
    fi

    if [[ "$path_for_policy" == *.pem ]] || [[ "$path_for_policy" == *.key ]]; then
        found_match=true
        case "$classification" in
            fixture_expected)
                if [ "$VERBOSE" = true ]; then
                    log_classification "$classification" "$YELLOW" "Safe fixture file by extension:" "$path_for_policy" "" ""
                fi
                ;;
            obsolete_release_file)
                    log_classification "$classification" "$YELLOW" "Potential secret file found by extension" "$path_for_policy" "" ""
                    found_blocking=true
                ;;
            generated_artifact)
                log_classification "$classification" "$YELLOW" "Potential secret file found by extension" "$path_for_policy" "" ""
                found_blocking=true
                ;;
            *)
                log_classification "$classification" "$RED" "Potential secret file found by extension" "$path_for_policy" "" ""
                found_blocking=true
                ;;
        esac
    fi

    if [[ "$(basename "$path_for_policy")" == ".env" ]] || [[ "$(basename "$path_for_policy")" == ".env.local" ]]; then
        found_match=true
        log_classification "$classification" "$RED" "Potential environment file" "$path_for_policy" "" ""
        found_blocking=true
    fi

    if [ "$VERBOSE" = true ] && [ "$found_match" = false ]; then
        printf '[clear] %s\n' "$path_for_policy"
    fi

    if [ "$found_blocking" = true ]; then
        return 1
    fi
    return 0
}

install_hook() {
    echo "Installing pre-commit hook..."
    mkdir -p .githooks
    cat <<'EOF' > .githooks/pre-commit
#!/bin/bash
./scripts/check-secrets.sh --staged
EOF
    chmod +x .githooks/pre-commit
    git config core.hooksPath .githooks
    echo -e "${GREEN}Pre-commit hook configured to use .githooks/${NC}"
}

scan_list() {
    local mode="$1"
    local base_path="${2:-}"
    shift 2 || true
    local files=("$@")

    case "$mode" in
        path)
            echo "Checking path ${base_path} for secrets..."
            ;;
        staged)
            echo "Checking staged files for secrets..."
            ;;
        all)
            echo "Checking all versionable files for secrets..."
            ;;
    esac

    local file
    for file in "${files[@]}"; do
        [ -f "$file" ] || continue
        local path_for_policy
        path_for_policy="$(relative_to_base "$file" "$base_path")"
        check_file "$file" "$path_for_policy" || EXIT_CODE=1
    done
}

if [ $# -eq 0 ]; then
    usage
    exit 1
fi

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --staged)
            STAGED=true
            ;;
        --all)
            ALL=true
            ;;
        --install-hook)
            install_hook
            exit 0
            ;;
        --path)
            if [ $# -lt 2 ]; then
                usage
                exit 1
            fi
            CHECK_PATH="$2"
            shift
            ;;
        --verbose)
            VERBOSE=true
            ;;
        *)
            echo "Unknown parameter: $1"
            usage
            exit 1
            ;;
    esac
    shift
done

if [ "$STAGED" = true ] && [ -n "$CHECK_PATH" ]; then
    echo "Use either --staged or --path, not both."
    exit 1
fi

if [ "$ALL" = true ] && [ -n "$CHECK_PATH" ]; then
    echo "Use either --all or --path, not both."
    exit 1
fi

if [ "$STAGED" = true ]; then
    mapfile -t files < <(git diff --cached --name-only --diff-filter=ACM)
    scan_list "staged" "." "${files[@]}"
elif [ -n "$CHECK_PATH" ]; then
    if [ ! -e "$CHECK_PATH" ]; then
        echo "Path ${CHECK_PATH} not found"
        exit 1
    fi

    if [ -f "$CHECK_PATH" ]; then
        if [[ "$CHECK_PATH" = /* ]]; then
            scan_list "path" "$(dirname "$CHECK_PATH")" "$CHECK_PATH"
        else
            scan_list "path" "." "$CHECK_PATH"
        fi
    else
        mapfile -t files < <(find "$CHECK_PATH" -type f | sort)
        if [[ "$CHECK_PATH" = /* ]]; then
            scan_list "path" "$CHECK_PATH" "${files[@]}"
        else
            scan_list "path" "." "${files[@]}"
        fi
    fi
elif [ "$ALL" = true ]; then
    mapfile -t files < <(git ls-files | grep -vE '^(node_modules/|models/|\.venv/|data/rag_uploads/|\.git/|\.pytest_cache/|\.ruff_cache/|scripts/)' || true)
    scan_list "all" "." "${files[@]}"
else
    usage
    exit 1
fi

if [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "${GREEN}No secrets found.${NC}"
else
    echo -e "${RED}Secrets detected! Please remove them before committing.${NC}"
fi

exit "$EXIT_CODE"
