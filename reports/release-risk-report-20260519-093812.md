# Release Risk Report
Date: Tue May 19 09:38:12 -03 2026

## Stabilization Rules
{
  "forbid_new_domains": true,
  "forbid_new_top_level_services": true,
  "require_tests_for_api_changes": true,
  "require_docs_for_config_changes": true,
  "require_migration_for_model_changes": true
}

## Recent Changes (last 10 commits)
- acb4f86 feat platform hardening admin sales and system api improvements (diuercheley-cloud)
- 51d6f3b fix platform hardening admin tests and openrouter ui (diuercheley-cloud)
- 4b53b5d feat platform hardening rbac tokenization attestation and model hot swap (diuercheley-cloud)
- 6a024f2 feat admin v2 modular ui and frontend restructuring (diuercheley-cloud)
- 31fbacb feat frontend modularization hubs shared pages (diuercheley-cloud)
- 2ff7302 feat release v1.8.3 portal tts and transparency repair updates (diuercheley-cloud)
- 1af3356 feat admin policy controls and openrouter test improvements (diuercheley-cloud)
- b706936 feat openrouter integration and provider validation hardening (diuercheley-cloud)
- ee0e7d2 fix provider settings test secret placeholders (diuercheley-cloud)
- 7de1eb8 provider settings and function calling integration improvements (diuercheley-cloud)
## Risk Analysis
- OK: No new domains detected in recent history.
- WARNING: New files detected in app/services/. Verify if this violates 'forbid_new_top_level_services'.
