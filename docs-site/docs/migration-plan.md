# Docs Migration Plan

## Goal

Replace the scattered documentation model with a single portal built on `MkDocs Material`.

## Target State

- one canonical docs portal under `docs-site/`;
- generated reference pages for API, configuration, feature flags and profiles;
- release versioning via `mike`;
- CI validation using `mkdocs build --strict`;
- release automation publishing versioned docs from tags.

## Phases

1. Portal bootstrap
   - add `mkdocs.yml`
   - add `docs-site/`
   - define top-level navigation

2. Generated reference migration
   - reuse `scripts/docs/generate_reference_docs.py`
   - generate portal copies for:
     - API docs
     - config docs
     - feature flags
     - profiles

3. Curated content migration
   - sync selected canonical docs into the portal by section
   - keep original source docs as migration inputs until ownership is consolidated

4. CI and release integration
   - build portal on CI
   - validate generated portal content with `--check`
   - publish versioned docs per release tag

5. Cleanup
   - progressively retire duplicate navigation from the legacy `docs/` tree
   - convert remaining sections from sync mode to portal-native ownership

## Ownership Model

- generated reference pages remain code/config-driven;
- landing pages become portal-native editorial entry points;
- section documents are migrated in batches, not with a single destructive rewrite.

## Immediate Deliverables

- `docs-site/`
- `mkdocs.yml`
- generator script for portal sync
- CI docs build
- release versioning workflow hooks
