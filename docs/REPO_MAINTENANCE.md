# Repository Maintenance

## Release History

The consolidated release history is maintained in [docs/RELEASE_HISTORY.md](RELEASE_HISTORY.md).
Generate or update it with:

```bash
./scripts/generate-release-history.sh
```

Validate the generated document with:

```bash
./scripts/validate-release-history.sh
```

## Local Branch Cleanup

Old feature branches accumulate locally after they have been stabilized. Use the cleanup tool to safely identify and remove them.

### Quick start
```bash
# List stale branches (dry-run, no deletion)
make cleanup-branches

# Or directly
./scripts/cleanup-local-branches.sh --dry-run --merged-only
```

### Options
| Flag | Description |
|------|-------------|
| `--dry-run` | Default — show candidates without deleting |
| `--yes` | Apply deletion for safe candidates |
| `--merged-only` | Only consider branches merged into HEAD |
| `--include-feature` | Include `feature/*` branches |
| `--include-stable` | Include `stable/*` branches |
| `--keep-pattern REGEX` | Protect branches matching a regex |

### Protected branches (never deleted)
- `main`, `master`
- Current branch
- All `stable/*` branches (unless `--include-stable`)
- Branches with uncommitted changes
- Branches matching `--keep-pattern`

### Deletion safety
- Default is `--dry-run` — nothing is deleted
- `--yes` only deletes branches classified as `delete_safe`
- Uses `git branch -d` (safe delete), never `-D` (force)
- Never touches remote branches
- Generates a report in `artifacts/repo-cleanup/<timestamp>/`

### How `delete_safe` is determined
A branch is classified as `delete_safe` when ALL apply:
1. Merged into HEAD
2. Has a remote tracking branch
3. Has a corresponding tag (release)

Otherwise the branch gets `review` or `keep`.

## Release Line Audit

A release line audit verifies consistency of tags, stable branches, VERSION, CHANGELOG,
release manifests, docs and scripts for a given release line.

### Running the audit

```bash
# Run the full v1.6.x audit
./scripts/audit-v1.6-release-line.sh
```

Output is written to `artifacts/final-qa/v1.6-audit/<timestamp>/`.

### Validating the audit

```bash
# Validate audit artifacts
./scripts/validate-v1.6-release-line-audit.sh
```

### Running audit tests

```bash
.venv/bin/python -m pytest tests/test_v1_6_release_line_audit.py \
  tests/test_v1_6_release_history_consistency.py \
  tests/test_v1_6_release_artifacts_security.py -q
```

### Audit summary

The consolidated audit summary for the v1.6.x line is maintained at
[docs/V1_6_AUDIT_SUMMARY.md](V1_6_AUDIT_SUMMARY.md).
