#!/usr/bin/env bash
# Safely list and remove stale local git branches.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="${PROJECT_ROOT}/artifacts/repo-cleanup/${TIMESTAMP}"

DRY_RUN=true
CONFIRMED=false
MERGED_ONLY=false
INCLUDE_FEATURE=false
INCLUDE_STABLE=false
KEEP_PATTERNS=()
CURRENT_BRANCH=""

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --dry-run              Show candidates without deleting (default)
  --yes                  Apply deletion for safe branches
  --merged-only          Only consider branches merged into HEAD
  --include-feature      Include feature/* branches
  --include-stable       Include stable/* branches
  --keep-pattern REGEX   Regex pattern for branches to always keep
  --help                 Show this help
EOF
  exit 0
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --dry-run)       DRY_RUN=true; shift ;;
    --yes)           DRY_RUN=false; CONFIRMED=true; shift ;;
    --merged-only)   MERGED_ONLY=true; shift ;;
    --include-feature) INCLUDE_FEATURE=true; shift ;;
    --include-stable) INCLUDE_STABLE=true; shift ;;
    --keep-pattern)  KEEP_PATTERNS+=("$2"); shift 2 ;;
    --help)          usage ;;
    *)               echo "Unknown: $1"; usage ;;
  esac
done

mkdir -p "${REPORT_DIR}"

# --- Helpers ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { printf "${GREEN}%s${NC}\n" "$1"; }
warn() { printf "${YELLOW}%s${NC}\n" "$1"; }
err()  { printf "${RED}%s${NC}\n" "$1"; }
info() { printf "${CYAN}%s${NC}\n" "$1"; }

# --- Gather context ---
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
PROTECTED_BRANCHES=("main" "master" "${CURRENT_BRANCH}")

# Load configurable keep patterns from command line
CONFIG_KEEP_PATTERNS=("${KEEP_PATTERNS[@]}")

# Also protect all stable/* branches by default unless --include-stable
if [[ "$INCLUDE_STABLE" != "true" ]]; then
  mapfile -t STABLE_BRANCHES < <(git branch --format='%(refname:short)' | grep '^stable/' || true)
  for sb in "${STABLE_BRANCHES[@]}"; do
    PROTECTED_BRANCHES+=("$sb")
  done
fi

is_protected() {
  local branch="$1"
  for p in "${PROTECTED_BRANCHES[@]}"; do
    [[ "$branch" == "$p" ]] && return 0
  done
  for pat in "${CONFIG_KEEP_PATTERNS[@]}"; do
    echo "$branch" | grep -qE "$pat" && return 0
  done
  return 1
}

has_uncommitted_changes() {
  local branch="$1"
  # Check if the branch has uncommitted changes by diffing against its merge-base
  local merge_base
  merge_base=$(git merge-base HEAD "$branch" 2>/dev/null || true)
  [[ -z "$merge_base" ]] && return 1
  git diff --quiet "$merge_base".."$branch" 2>/dev/null && return 1 || return 0
}

find_corresponding_tag() {
  local branch="$1"
  # Strip prefix: feature/v1.2.3-name -> v1.2.3-name
  local stem="${branch#feature/}"
  stem="${stem#stable/}"
  # Try exact match
  if git tag -l "$stem" 2>/dev/null | grep -q .; then
    echo "$stem"
    return
  fi
  # Try v-prefixed match (feature/v1.2.3-name -> v1.2.3-name)
  local vtag="v${stem#v}"
  if [[ "$vtag" != "$stem" ]] && git tag -l "$vtag" 2>/dev/null | grep -q .; then
    echo "$vtag"
    return
  fi
  # Try to find any tag pointing to the same commit as branch HEAD
  local branch_commit
  branch_commit=$(git rev-parse "$branch" 2>/dev/null || true)
  if [[ -n "$branch_commit" ]]; then
    local matching_tag
    matching_tag=$(git tag --points-at "$branch_commit" 2>/dev/null | head -1 || true)
    if [[ -n "$matching_tag" ]]; then
      echo "$matching_tag"
      return
    fi
  fi
  echo ""
}

has_upstream() {
  local branch="$1"
  git rev-parse --abbrev-ref "${branch}@{upstream}" &>/dev/null
}

is_merged() {
  local branch="$1"
  git branch --merged HEAD 2>/dev/null | grep -qE "^\s+${branch}$"
}

# --- Collect all local branches ---
mapfile -t ALL_BRANCHES < <(git branch --format='%(refname:short)' | sort)

BRANCHES_DATA=()
echo ""
echo "=== Local Branch Cleanup Report ==="
echo "Timestamp: ${TIMESTAMP}"
echo "Current branch: ${CURRENT_BRANCH}"
echo "Mode: $($DRY_RUN && echo 'DRY-RUN' || echo 'APPLY')"
echo ""

printf "%-45s %-12s %-10s %-25s %-10s %s\n" "Branch" "Merged" "Remote" "Tag" "Status" "Recommend"
printf -- "%s\n" "------------------------------------------------------------------------------------------------------------------------"

for branch in "${ALL_BRANCHES[@]}"; do
  # Filter by prefix
  if [[ "$INCLUDE_STABLE" != "true" && "$branch" != stable/* ]]; then
    : # not stable, ok
  fi
  if [[ "$INCLUDE_FEATURE" != "true" && "$branch" == feature/* ]]; then
    : # not feature, ok
  fi

  merged="?"
  if is_merged "$branch"; then
    merged="true"
  else
    merged="false"
  fi

  if has_upstream "$branch"; then
    upstream="yes"
  else
    upstream="no"
  fi

  tag=$(find_corresponding_tag "$branch")
  tag_display="${tag:-none}"

  last_commit=$(git log -1 --format="%h %s" "$branch" 2>/dev/null | cut -c1-50 || echo "?")
  last_date=$(git log -1 --format="%cs" "$branch" 2>/dev/null || echo "?")

  # Determine recommendation
  rec=""
  status_label=""

  if is_protected "$branch"; then
    rec="keep"
    status_label="protected"
  elif has_uncommitted_changes "$branch"; then
    rec="review"
    status_label="has_uncommitted"
  elif [[ "$merged" == "false" ]] && [[ "$MERGED_ONLY" == "true" ]]; then
    rec="keep"
    status_label="not_merged"
  elif [[ "$merged" == "false" ]]; then
    rec="review"
    status_label="unmerged"
  elif [[ "$upstream" == "no" ]]; then
    rec="review"
    status_label="no_remote"
  elif [[ -n "$tag" ]]; then
    rec="delete_safe"
    status_label="tagged"
  else
    rec="review"
    status_label="no_tag"
  fi

  # Color based on recommendation
  case "$rec" in
    keep)       col="" ;;
    delete_safe) col="${GREEN}" ;;
    review)     col="${YELLOW}" ;;
  esac

  printf "${col}%-45s %-12s %-10s %-25s %-10s %s${NC}\n" \
    "$branch" "$merged" "$upstream" "${tag_display:0:24}" "$status_label" "$rec"

  BRANCHES_DATA+=("$(cat <<EOF
{"branch":"${branch}","merged":${merged},"upstream":"${upstream}","tag":"${tag}","status":"${status_label}","recommendation":"${rec}","last_commit":"${last_commit}","last_date":"${last_date}"}
EOF
)")
done

echo ""

# --- Deletion phase ---
if [[ "$DRY_RUN" == "false" ]] && [[ "$CONFIRMED" == "true" ]]; then
  echo "=== Applying deletions (--yes) ==="
  DELETED=0
  SKIPPED=0
  for entry in "${BRANCHES_DATA[@]}"; do
    branch=$(echo "$entry" | python3 -c 'import json,sys; print(json.load(sys.stdin)["branch"])' 2>/dev/null || echo "")
    rec=$(echo "$entry" | python3 -c 'import json,sys; print(json.load(sys.stdin)["recommendation"])' 2>/dev/null || echo "")
    [[ -z "$branch" || -z "$rec" ]] && continue
    if [[ "$rec" == "delete_safe" ]]; then
      if is_protected "$branch"; then
        warn "  SKIP (protected): $branch"
        SKIPPED=$((SKIPPED + 1))
        continue
      fi
      ok "  Deleting: $branch"
      git branch -d "$branch" 2>/dev/null && DELETED=$((DELETED + 1)) || warn "  FAILED: $branch"
    fi
  done
  echo ""
  info "Deleted: $DELETED | Skipped: $SKIPPED"
else
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "Dry-run mode. No branches deleted."
    echo "To delete safe candidates: $0 --yes --merged-only"
  fi
fi

# --- Reports ---
{
  echo "# Local Branch Cleanup Report"
  echo "**Timestamp:** ${TIMESTAMP}"
  echo "**Current branch:** ${CURRENT_BRANCH}"
  echo "**Mode:** $($DRY_RUN && echo 'dry-run' || echo 'applied')"
  echo ""
  echo "## Summary"
  echo "- **Total branches:** ${#ALL_BRANCHES[@]}"
  echo "- **Protected:** $(printf '%s\n' "${PROTECTED_BRANCHES[@]}" | wc -l)"
  echo "- **delete_safe:** $(printf '%s\n' "${BRANCHES_DATA[@]}" | grep -c '"delete_safe"' || true)"
  echo "- **review:** $(printf '%s\n' "${BRANCHES_DATA[@]}" | grep -c '"review"' || true)"
  echo "- **keep:** $(printf '%s\n' "${BRANCHES_DATA[@]}" | grep -c '"keep"' || true)"
  echo ""
  echo "## Candidate Branches"
  echo ""
  echo "| Branch | Merged | Remote | Tag | Status | Recommendation |"
  echo "|--------|--------|--------|-----|--------|---------------|"
} > "${REPORT_DIR}/branches-cleanup-report.md"

for entry in "${BRANCHES_DATA[@]}"; do
  branch=$(echo "$entry" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["branch"])' 2>/dev/null || echo "")
  merged=$(echo "$entry" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["merged"])' 2>/dev/null || echo "?")
  upstream=$(echo "$entry" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["upstream"])' 2>/dev/null || echo "?")
  tag=$(echo "$entry" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["tag"])' 2>/dev/null || echo "")
  status=$(echo "$entry" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["status"])' 2>/dev/null || echo "?")
  rec=$(echo "$entry" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["recommendation"])' 2>/dev/null || echo "?")

  tag_display="${tag:-none}"
  printf "| %s | %s | %s | %s | %s | %s |\n" \
    "$branch" "$merged" "$upstream" "$tag_display" "$status" "$rec" >> "${REPORT_DIR}/branches-cleanup-report.md"
done

# JSON report
{
  echo "["
  first=true
  for entry in "${BRANCHES_DATA[@]}"; do
    $first || echo ","
    first=false
    echo "$entry"
  done
  echo "]"
} > "${REPORT_DIR}/branches-cleanup-report.json"

echo ""
echo "Report: ${REPORT_DIR}/branches-cleanup-report.md"
echo "JSON:   ${REPORT_DIR}/branches-cleanup-report.json"
