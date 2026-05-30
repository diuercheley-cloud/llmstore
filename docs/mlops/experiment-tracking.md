# Experiment Tracking and Artifact Redaction

The experiment tracking system governs training runs, parameters, metrics, and output evaluation artifacts.

## Configuration & Feature Flags
Enable experiment tracking with:
* `MLOPS_ENABLED=true`
* `EXPERIMENT_TRACKING_ENABLED=true`

Optionally integrate with external tools:
* `MLFLOW_INTEGRATION_ENABLED=true`
* `WANDB_INTEGRATION_ENABLED=true`

By default, all external integrations are disabled (`false`) to ensure an airgapped posture.

## Evaluation Artifact Protection
No sensitive data is allowed to be logged inside evaluation artifacts without an explicit `redaction_policy`.
* Artifacts are scanned for patterns resembling secrets (e.g. `sk-...`).
* If secrets are found and no `redaction_policy` is defined, registration is blocked (returns `HTTP 400`).
* If a policy is defined, sensitive data is flagged and marked as `is_redacted = true`.
