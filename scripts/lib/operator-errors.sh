#!/usr/bin/env bash
# Operator Friendly Error Library

# Standard colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Globals for next steps
NEXT_STEPS=()

operator_error() {
    local code="$1"
    local message="$2"
    local remediation="$3"
    local details="${4:-}"

    printf "\n${RED}${BOLD}[ERROR] Código: %s${NC}\n" "${code}"
    printf "${BOLD}O que aconteceu:${NC}\n%s\n" "${message}"
    printf "${BOLD}Como resolver:${NC}\n%s\n" "${remediation}"
    if [[ -n "${details}" ]]; then
        printf "${BOLD}Detalhe técnico:${NC}\n%s\n" "${details}"
    fi
    printf "\n"
}

operator_warning() {
    local code="$1"
    local message="$2"
    local remediation="$3"
    local details="${4:-}"

    printf "\n${YELLOW}${BOLD}[WARNING] Código: %s${NC}\n" "${code}"
    printf "${BOLD}O que aconteceu:${NC}\n%s\n" "${message}"
    printf "${BOLD}Como resolver:${NC}\n%s\n" "${remediation}"
    if [[ -n "${details}" ]]; then
        printf "${BOLD}Detalhe técnico:${NC}\n%s\n" "${details}"
    fi
    printf "\n"
}

operator_success() {
    local message="$1"
    printf "\n${GREEN}${BOLD}[SUCCESS]${NC} %s\n\n" "${message}"
}

print_next_steps() {
    if [[ ${#NEXT_STEPS[@]} -eq 0 ]]; then
        return
    fi

    printf "${BOLD}Próximos passos:${NC}\n"
    for step in "${NEXT_STEPS[@]}"; do
        printf "  - %s\n" "${step}"
    done
    printf "\n"
}

add_next_step() {
    NEXT_STEPS+=("$1")
}

mask_sensitive() {
    local input="$1"
    # Basic redaction for common secret patterns if found in strings
    # This is a simple helper, real redaction happens in dedicated lib/redaction.sh
    if [[ -f "$(dirname "${BASH_SOURCE[0]}")/redaction.sh" ]]; then
        source "$(dirname "${BASH_SOURCE[0]}")/redaction.sh"
        echo "$input" | redact_stream
    else
        # Fallback simple masking
        echo "$input" | sed -E 's/(api[-_]?key|secret|password|token|auth)=[^ ]+/\1=******** /gI'
    fi
}

# Export functions if sourced
export -f operator_error
export -f operator_warning
export -f operator_success
export -f print_next_steps
export -f add_next_step
export -f mask_sensitive
