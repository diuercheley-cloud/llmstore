#!/bin/bash

# scripts/fix-local-permissions.sh
# Fixes file permissions for security cleanup.

set -e

DRY_RUN=false
YES=false

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run  Show what would be done without making changes"
    echo "  --yes      Execute changes without prompting"
    echo "  --help     Show this help message"
}

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true ;;
        --yes) YES=true ;;
        --help) show_help; exit 0 ;;
        *) echo "Unknown parameter: $1"; show_help; exit 1 ;;
    esac
    shift
done

if [ "$YES" = false ] && [ "$DRY_RUN" = false ]; then
    echo "Warning: This script will modify file permissions."
    read -p "Continue? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

apply_chmod() {
    local mode=$1
    shift
    local files=("$@")
    
    for file in "${files[@]}"; do
        if [ -e "$file" ]; then
            if [ "$DRY_RUN" = true ]; then
                echo "[DRY-RUN] chmod $mode $file"
            else
                echo "chmod $mode $file"
                chmod "$mode" "$file"
            fi
        fi
    done
}

# 1. Executables
echo "Fixing executable permissions..."
apply_chmod +x scripts/*.sh
apply_chmod +x .githooks/pre-commit
if ls examples/curl/*.sh >/dev/null 2>&1; then
    apply_chmod +x examples/curl/*.sh
fi

# 2. Non-executables
echo "Removing executable bit from documentation and config files..."
# Using find to avoid "argument list too long" and to be more precise
find docs/ -maxdepth 1 -name "*.md" -type f -exec echo {} + | while read -r files; do
    [ -n "$files" ] && apply_chmod -x $files
done

apply_chmod -x *.json *.yml *.yaml *.txt

# 3. Sensitive files
echo "Restricting sensitive files..."
if [ -f ".env.local" ]; then
    apply_chmod 600 .env.local
fi

if [ -d ".local" ]; then
    apply_chmod 700 .local
fi

echo "Done."
