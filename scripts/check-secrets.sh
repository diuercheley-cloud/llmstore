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
    "sk-image-conic-from-color"
    "sk-image-linear-from-color"
    "sk-image-linear-from-pos"
    "sk-image-linear-to-color"
    "sk-image-radial-from-color"
    "sk-image-radial-from-pos"
    "sk-image-radial-to-color"
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
CHECK_PATHS=()
EXIT_CODE=0

usage() {
    echo "Usage: $0 [--staged | --all | --install-hook | --path <path1> <path2> ...] [--verbose]"
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

# Pre-calculated base for performance
ABS_BASE_PATH=""

# Global return variables to avoid subshells in loops
__RET_REL_PATH=""
__RET_CLASSIFICATION=""

relative_to_base() {
    local file="$1"
    local base="$2"

    if [[ "$base" == "." ]] || [[ -z "$base" ]]; then
        local normalized="${file#./}"
        while [[ "$normalized" == *"//"* ]]; do
            normalized="${normalized//\/\//\/}"
        done
        __RET_REL_PATH="$normalized"
        return
    fi

    if [ -z "$ABS_BASE_PATH" ]; then
        ABS_BASE_PATH="$(realpath "$base")"
    fi
    local abs_file
    abs_file="$(realpath "$file")"
    if [[ "$abs_file" == "$ABS_BASE_PATH" ]]; then
        __RET_REL_PATH="."
        return
    fi
    if [[ "$abs_file" == "$ABS_BASE_PATH/"* ]]; then
        __RET_REL_PATH="${abs_file#"$ABS_BASE_PATH"/}"
        return
    fi

    __RET_REL_PATH="$(normalize_repo_relative_path "$file")"
}

is_text_scan_skipped() {
    case "$1" in
        ".well-known/security.txt") return 0 ;;
        *.gguf|*.bin|*.sqlite|*.db|*.bak|*.png|*.jpg|*.jpeg|*.gif|*.ico|*.pdf|*.zip|*.tar|*.gz) return 0 ;;
    esac
    return 1
}

is_allowed_fixture() {
    local path="$1"
    local file="$2"

    if [[ "$path" == control_plane/tests/* ]]; then
        if grep -qF "FAKE TEST KEY - DO NOT USE" "$file" 2>/dev/null || grep -qF "FAKE SECRET FOR TESTS ONLY" "$file" 2>/dev/null; then
            return 0
        fi
        return 1
    fi

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
        __RET_CLASSIFICATION='fixture_expected'
    elif [[ "$path" == releases/* ]]; then
        __RET_CLASSIFICATION='obsolete_release_file'
    elif [[ "$path" == artifacts/* ]]; then
        __RET_CLASSIFICATION='generated_artifact'
    elif [[ "$path" == *.env ]] || [[ "$path" == *.env.* ]] || [[ "$(basename "$path")" == ".env" ]] || [[ "$(basename "$path")" == ".env.local" ]]; then
        __RET_CLASSIFICATION='real_secret_suspected'
    else
        __RET_CLASSIFICATION='real_secret_suspected'
    fi
}

check_file() {
    local file="$1"
    local path_for_policy="$2"
    local safe_regex
    safe_regex="$(safe_pattern_regex)"
    local secret_regex
    secret_regex="$(combined_secret_regex)"

    classify_path "$path_for_policy" "$file"
    local classification="$__RET_CLASSIFICATION"

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
                    obsolete_release_file | generated_artifact)
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
            obsolete_release_file | generated_artifact)
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

# Cache for performance
CACHE_DIR=".cache"
CACHE_FILE="${CACHE_DIR}/check-secrets.cache"
declare -A FILE_CACHE
LOADED_CACHE=false

load_cache() {
    if [ "$LOADED_CACHE" = true ]; then return; fi
    mkdir -p "$CACHE_DIR"
    if [ -f "$CACHE_FILE" ]; then
        while IFS=: read -r f t s || [ -n "$f" ]; do
            FILE_CACHE["$f"]="$t:$s"
        done < "$CACHE_FILE"
    fi
    LOADED_CACHE=true
}

save_cache() {
    [ "$LOADED_CACHE" = true ] || return
    : > "$CACHE_FILE"
    for f in "${!FILE_CACHE[@]}"; do
        echo "$f:${FILE_CACHE[$f]}" >> "$CACHE_FILE"
    done
}

scan_list() {
    local mode="$1"
    local base_path="${2:-}"
    shift 2 || true
    local files=("$@")

    load_cache

    case "$mode" in
        path)
            echo "Checking path(s) for secrets..."
            ;;
        staged)
            echo "Checking staged files for secrets..."
            ;;
        all)
            echo "Checking all versionable files for secrets..."
            ;;
    esac

    local secret_regex
    secret_regex="$(combined_secret_regex)"
    local safe_regex
    safe_regex="$(safe_pattern_regex)"

    local scan_queue=()
    local new_cache_entries=()
    
    for file in "${files[@]}"; do
        [ -f "$file" ] || continue
        
        # Cache check
        local mtime size
        mtime=$(stat -c %Y "$file" 2>/dev/null || echo 0)
        size=$(stat -c %s "$file" 2>/dev/null || echo 0)
        if [[ "${FILE_CACHE[$file]:-}" == "$mtime:$size" ]]; then
            continue
        fi

        relative_to_base "$file" "$base_path"
        local rel_path="$__RET_REL_PATH"
        
        if ! is_text_scan_skipped "$rel_path"; then
            scan_queue+=("$file")
            new_cache_entries+=("$file:$mtime:$size")
        fi
        
        if [[ "$rel_path" == *.pem ]] || [[ "$rel_path" == *.key ]]; then
             check_file "$file" "$rel_path" || EXIT_CODE=1
        elif [[ "$(basename "$rel_path")" == ".env" ]] || [[ "$(basename "$rel_path")" == ".env.local" ]]; then
             check_file "$file" "$rel_path" || EXIT_CODE=1
        fi
    done

    if [ ${#scan_queue[@]} -eq 0 ]; then
        return
    fi

    printf '%s\0' "${scan_queue[@]}" | xargs -0 grep -Eon -- "$secret_regex" 2>/dev/null | grep -vE "$safe_regex" > .secrets_found.tmp || true

    if [ -s .secrets_found.tmp ]; then
        # If secrets found, we don't cache those files as "clean"
        local -A dirty_files
        while IFS= read -r match; do
            local file_path="${match%%:*}"
            dirty_files["$file_path"]=1
            
            local rest="${match#*:}"
            local line_num="${rest%%:*}"
            local secret_value="${rest#*:}"
            
            relative_to_base "$file_path" "$base_path"
            local rel_path="$__RET_REL_PATH"
            
            classify_path "$rel_path" "$file_path"
            local classification="$__RET_CLASSIFICATION"
            
            case "$classification" in
                fixture_expected)
                    if [ "$VERBOSE" = true ]; then
                        log_classification "$classification" "$YELLOW" "Safe fixture in" "$rel_path" "$line_num" "$secret_value"
                    fi
                    ;;
                obsolete_release_file | generated_artifact)
                    log_classification "$classification" "$YELLOW" "Potential secret in" "$rel_path" "$line_num" "$secret_value"
                    EXIT_CODE=1
                    ;;
                *)
                    log_classification "$classification" "$RED" "Potential secret in" "$rel_path" "$line_num" "$secret_value"
                    EXIT_CODE=1
                    ;;
            esac
        done < .secrets_found.tmp
        
        # Update cache only for clean files
        for entry in "${new_cache_entries[@]}"; do
            local f="${entry%%:*}"
            local ts="${entry#*:}"
            if [[ -z "${dirty_files[$f]:-}" ]]; then
                FILE_CACHE["$f"]="$ts"
            fi
        done
    else
        # All files in scan_queue are clean
        for entry in "${new_cache_entries[@]}"; do
            local f="${entry%%:*}"
            local ts="${entry#*:}"
            FILE_CACHE["$f"]="$ts"
        done
    fi
    rm -f .secrets_found.tmp
    save_cache
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
            shift
            while [[ "$#" -gt 0 ]] && [[ "$1" != --* ]]; do
                CHECK_PATHS+=("$1")
                shift
            done
            continue
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

if [ "$STAGED" = true ] && [ ${#CHECK_PATHS[@]} -gt 0 ]; then
    echo "Use either --staged or --path, not both."
    exit 1
fi

if [ "$ALL" = true ] && [ ${#CHECK_PATHS[@]} -gt 0 ]; then
    echo "Use either --all or --path, not both."
    exit 1
fi

if [ "$STAGED" = true ]; then
    mapfile -t files < <(git diff --cached --name-only --diff-filter=ACM)
    scan_list "staged" "." "${files[@]}"
elif [ ${#CHECK_PATHS[@]} -gt 0 ]; then
    all_files=()
    for p in "${CHECK_PATHS[@]}"; do
        if [ ! -e "$p" ]; then
            echo "Path ${p} not found"
            exit 1
        fi
        if [ -f "$p" ]; then
            all_files+=("$p")
        else
            mapfile -t -O "${#all_files[@]}" all_files < <(find "$p" -type d \( -name ".git" -o -name ".venv" -o -name "venv" -o -name "__pycache__" -o -name ".pytest_cache" -o -name ".ruff_cache" -o -name ".cache" -o -name ".tmp-llm-harness-cli-*" -o -name "node_modules" -o -name "dist" -o -name "build" \) -prune -o -type f ! -name "*.gguf" ! -name "*.bin" ! -name "*.sqlite" ! -name "*.db" ! -name "*.bak" ! -name "*.png" ! -name "*.jpg" ! -name "*.jpeg" ! -name "*.gif" ! -name "*.ico" ! -name "*.pdf" ! -name "*.zip" ! -name "*.tar" ! -name "*.gz" -print | sort)
        fi
    done
    scan_list "path" "." "${all_files[@]}"
elif [ "$ALL" = true ]; then
    mapfile -t files < <(git ls-files | grep -vE '^(node_modules/|models/|\.venv/|data/rag_uploads/|\.git/|\.pytest_cache/|\.ruff_cache/|\.cache/|\.tmp-llm-harness-cli-|scripts/)' || true)
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
