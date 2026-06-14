# Frontend/Backend Surface Alignment Report
Generated on: 2026-06-13T14:37:10.017912

| Method | Backend Path | Status | Frontend Coverage | File |
|--------|--------------|--------|-------------------|------|
| GET | `/` | has_frontend | Route Only | control_plane/app/api/operations_remediation_execution_admin.py |
| GET | `/account` | has_frontend | Exempted: Legacy account path, redirecting to /portal/me. | control_plane/app/api/portal.py |
| GET | `/actions` | no_frontend | None | control_plane/app/api/commercial_governance_supervisor_admin.py |
| GET | `/admin-dashboard` | intentionally_hidden | Exempted: Legacy admin redirect. | control_plane/app/api/system.py |
| GET | `/admin-dashboard/{rest:path}` | intentionally_hidden | Exempted: Legacy admin redirect. | control_plane/app/api/system.py |
| GET | `/admin-lab` | intentionally_hidden | Exempted: Internal developer lab. | control_plane/app/api/system.py |
| GET | `/admin-tests` | intentionally_hidden | Exempted: E2E test dashboard. | control_plane/app/api/system.py |
| GET | `/admin-v2` | intentionally_hidden | Exempted: Static files for the admin dashboard itself. | control_plane/app/api/system.py |
| GET | `/admin-v2/{rest:path}` | intentionally_hidden | Exempted: Static files for the admin dashboard itself. | control_plane/app/api/system.py |
| GET | `/admin/agent-approvals` | api_client_only | API Client Only | control_plane/app/api/agent_approvals_admin.py |
| GET | `/admin/agent-approvals/inbox` | api_client_only | API Client Only | control_plane/app/api/agent_approvals_admin.py |
| GET | `/admin/agent-approvals/{id}` | api_client_only | API Client Only | control_plane/app/api/agent_approvals_admin.py |
| POST | `/admin/agent-approvals/{id}/approve` | api_client_only | API Client Only | control_plane/app/api/agent_approvals_admin.py |
| POST | `/admin/agent-approvals/{id}/reject` | api_client_only | API Client Only | control_plane/app/api/agent_approvals_admin.py |
| POST | `/admin/agent-approvals/{id}/request-changes` | api_client_only | API Client Only | control_plane/app/api/agent_approvals_admin.py |
| POST | `/admin/agent-evals/datasets` | api_client_only | API Client Only | control_plane/app/api/agent_evals_admin.py |
| POST | `/admin/agent-evals/datasets/{id}/versions` | api_client_only | API Client Only | control_plane/app/api/agent_evals_admin.py |
| POST | `/admin/agent-evals/promotion-check/{agent_id}` | api_client_only | API Client Only | control_plane/app/api/agent_evals_admin.py |
| GET | `/admin/agent-evals/reports/{agent_id}` | api_client_only | API Client Only | control_plane/app/api/agent_evals_admin.py |
| POST | `/admin/agent-evals/run` | api_client_only | API Client Only | control_plane/app/api/agent_evals_admin.py |
| GET | `/admin/agent-marketplace` | api_client_only | API Client Only | control_plane/app/api/agent_marketplace_admin.py |
| POST | `/admin/agent-marketplace/bundles/verify` | api_client_only | API Client Only | control_plane/app/api/agent_marketplace_admin.py |
| POST | `/admin/agent-marketplace/bundles/{id}/publish` | api_client_only | API Client Only | control_plane/app/api/agent_marketplace_admin.py |
| POST | `/admin/agent-marketplace/bundles/{id}/review` | api_client_only | API Client Only | control_plane/app/api/agent_marketplace_admin.py |
| POST | `/admin/agent-marketplace/install` | api_client_only | API Client Only | control_plane/app/api/agent_marketplace_admin.py |
| GET | `/admin/agent-marketplace/versions/{version_id}/trust-report` | api_client_only | API Client Only | control_plane/app/api/agent_marketplace_admin.py |
| POST | `/admin/agent-marketplace/{install_id}/disable` | api_client_only | API Client Only | control_plane/app/api/agent_marketplace_admin.py |
| POST | `/admin/agent-marketplace/{install_id}/enable` | api_client_only | API Client Only | control_plane/app/api/agent_marketplace_admin.py |
| GET | `/admin/agent-registry` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| POST | `/admin/agent-registry` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| GET | `/admin/agent-registry/{id}` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| PATCH | `/admin/agent-registry/{id}` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| POST | `/admin/agent-registry/{id}/activate` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| POST | `/admin/agent-registry/{id}/approve` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| POST | `/admin/agent-registry/{id}/archive` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| POST | `/admin/agent-registry/{id}/deprecate` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| GET | `/admin/agent-registry/{id}/lineage` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| POST | `/admin/agent-registry/{id}/pause` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| GET | `/admin/agent-registry/{id}/policy-diff` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| POST | `/admin/agent-registry/{id}/promote` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| POST | `/admin/agent-registry/{id}/submit-review` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| GET | `/admin/agent-registry/{id}/versions` | api_client_only | API Client Only | control_plane/app/api/agent_registry_admin.py |
| POST | `/admin/agent-tasks/plans` | no_frontend | None | control_plane/app/api/agent_tasks_admin.py |
| GET | `/admin/agent-tasks/plans/{plan_id}` | no_frontend | None | control_plane/app/api/agent_tasks_admin.py |
| POST | `/admin/agent-tasks/plans/{plan_id}/execute` | no_frontend | None | control_plane/app/api/agent_tasks_admin.py |
| POST | `/admin/agent-tasks/tasks/{task_id}/compensate` | no_frontend | None | control_plane/app/api/agent_tasks_admin.py |
| POST | `/admin/agent-tasks/tasks/{task_id}/retry` | no_frontend | None | control_plane/app/api/agent_tasks_admin.py |
| POST | `/admin/agent-tasks/tasks/{task_id}/skip` | no_frontend | None | control_plane/app/api/agent_tasks_admin.py |
| GET | `/admin/agent-tools` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| POST | `/admin/agent-tools` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| GET | `/admin/agent-tools/credentials` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| POST | `/admin/agent-tools/credentials` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| POST | `/admin/agent-tools/credentials/{id}/revoke` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| POST | `/admin/agent-tools/invocations/{id}/rollback` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| GET | `/admin/agent-tools/quotas` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| GET | `/admin/agent-tools/side-effects` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| PATCH | `/admin/agent-tools/{id}` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| POST | `/admin/agent-tools/{id}/disable` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| POST | `/admin/agent-tools/{id}/dry-run` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| POST | `/admin/agent-tools/{id}/enable` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| POST | `/admin/agent-tools/{id}/execute` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| GET | `/admin/agent-tools/{id}/invocations` | api_client_only | API Client Only | control_plane/app/api/agent_tools_admin.py |
| GET | `/admin/agents` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| POST | `/admin/agents` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| GET | `/admin/agents/a2a/agents` | api_client_only | API Client Only | control_plane/app/api/agent_a2a.py |
| POST | `/admin/agents/a2a/announce` | api_client_only | API Client Only | control_plane/app/api/agent_a2a.py |
| GET | `/admin/agents/a2a/discover` | api_client_only | API Client Only | control_plane/app/api/agent_a2a.py |
| GET | `/admin/agents/a2a/profile/{agent_id}` | api_client_only | API Client Only | control_plane/app/api/agent_a2a.py |
| POST | `/admin/agents/a2a/register` | api_client_only | API Client Only | control_plane/app/api/agent_a2a.py |
| GET | `/admin/agents/approval-portal/approvals/{id}` | api_client_only | API Client Only | control_plane/app/api/agent_approval_portal.py |
| POST | `/admin/agents/approval-portal/approvals/{id}/decide` | api_client_only | API Client Only | control_plane/app/api/agent_approval_portal.py |
| GET | `/admin/agents/approval-portal/pending` | api_client_only | API Client Only | control_plane/app/api/agent_approval_portal.py |
| GET | `/admin/agents/artifacts/{id}` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| POST | `/admin/agents/artifacts/{id}/comments` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| GET | `/admin/agents/artifacts/{id}/diff` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| GET | `/admin/agents/artifacts/{id}/events` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| GET | `/admin/agents/artifacts/{id}/export` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| POST | `/admin/agents/artifacts/{id}/lock` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| POST | `/admin/agents/artifacts/{id}/review` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| POST | `/admin/agents/artifacts/{id}/unlock` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| POST | `/admin/agents/artifacts/{id}/versions` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| GET | `/admin/agents/artifacts/{id}/versions` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| GET | `/admin/agents/budgets` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| POST | `/admin/agents/budgets/validate` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| GET | `/admin/agents/capability-catalog` | api_client_only | API Client Only | control_plane/app/api/agent_capability_catalog_admin.py |
| POST | `/admin/agents/capability-catalog/install` | api_client_only | API Client Only | control_plane/app/api/agent_capability_catalog_admin.py |
| POST | `/admin/agents/capability-catalog/{entry_id}/approve` | api_client_only | API Client Only | control_plane/app/api/agent_capability_catalog_admin.py |
| POST | `/admin/agents/capability-catalog/{entry_id}/disable` | api_client_only | API Client Only | control_plane/app/api/agent_capability_catalog_admin.py |
| GET | `/admin/agents/capability-catalog/{entry_id}/trust-report` | api_client_only | API Client Only | control_plane/app/api/agent_capability_catalog_admin.py |
| GET | `/admin/agents/catalog` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| POST | `/admin/agents/catalog/{id}/promote` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| POST | `/admin/agents/catalog/{id}/rollback` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| GET | `/admin/agents/catalog/{id}/versions` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| POST | `/admin/agents/cicd/deployments/{deployment_id}/rollback` | api_client_only | API Client Only | control_plane/app/api/agent_cicd_admin.py |
| POST | `/admin/agents/cicd/pipelines` | api_client_only | API Client Only | control_plane/app/api/agent_cicd_admin.py |
| GET | `/admin/agents/cicd/pipelines/{pipeline_id}` | api_client_only | API Client Only | control_plane/app/api/agent_cicd_admin.py |
| POST | `/admin/agents/cicd/pipelines/{pipeline_id}/run` | api_client_only | API Client Only | control_plane/app/api/agent_cicd_admin.py |
| GET | `/admin/agents/code-interpreter/artifacts/{artifact_id}` | api_client_only | API Client Only | control_plane/app/api/agent_code_interpreter_admin.py |
| POST | `/admin/agents/code-interpreter/run` | api_client_only | API Client Only | control_plane/app/api/agent_code_interpreter_admin.py |
| GET | `/admin/agents/code-interpreter/runs/{run_id}` | api_client_only | API Client Only | control_plane/app/api/agent_code_interpreter_admin.py |
| POST | `/admin/agents/code-interpreter/runs/{run_id}/cancel` | api_client_only | API Client Only | control_plane/app/api/agent_code_interpreter_admin.py |
| GET | `/admin/agents/collaboration-sessions` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| GET | `/admin/agents/collaboration-sessions/{id}/trace` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| GET | `/admin/agents/connectors` | no_frontend | Exempted: Connector configuration currently via YAML/CLI. | control_plane/app/api/agent_connectors_admin.py |
| DELETE | `/admin/agents/connectors/credentials/{id}` | api_client_only | API Client Only | control_plane/app/api/agent_connectors_admin.py |
| POST | `/admin/agents/connectors/credentials/{id}/rotate` | api_client_only | API Client Only | control_plane/app/api/agent_connectors_admin.py |
| GET | `/admin/agents/connectors/{name}` | api_client_only | API Client Only | control_plane/app/api/agent_connectors_admin.py |
| GET | `/admin/agents/connectors/{name}/audit` | api_client_only | API Client Only | control_plane/app/api/agent_connectors_admin.py |
| POST | `/admin/agents/connectors/{name}/dry-run` | api_client_only | API Client Only | control_plane/app/api/agent_connectors_admin.py |
| POST | `/admin/agents/connectors/{name}/execute` | api_client_only | API Client Only | control_plane/app/api/agent_connectors_admin.py |
| POST | `/admin/agents/connectors/{name}/oauth/callback` | api_client_only | API Client Only | control_plane/app/api/agent_connectors_admin.py |
| POST | `/admin/agents/connectors/{name}/oauth/clients` | api_client_only | API Client Only | control_plane/app/api/agent_connectors_admin.py |
| POST | `/admin/agents/connectors/{name}/oauth/start` | api_client_only | API Client Only | control_plane/app/api/agent_connectors_admin.py |
| POST | `/admin/agents/delegation-policies` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| POST | `/admin/agents/digital-twins` | api_client_only | API Client Only | control_plane/app/api/digital_twin_admin.py |
| POST | `/admin/agents/digital-twins/{twin_id}/command` | api_client_only | API Client Only | control_plane/app/api/digital_twin_admin.py |
| GET | `/admin/agents/digital-twins/{twin_id}/state` | api_client_only | API Client Only | control_plane/app/api/digital_twin_admin.py |
| GET | `/admin/agents/event-deliveries` | api_client_only | API Client Only | control_plane/app/api/agent_events_admin.py |
| POST | `/admin/agents/event-sources` | api_client_only | API Client Only | control_plane/app/api/agent_events_admin.py |
| POST | `/admin/agents/event-subscriptions` | api_client_only | API Client Only | control_plane/app/api/agent_events_admin.py |
| POST | `/admin/agents/event-triggers` | api_client_only | API Client Only | control_plane/app/api/agent_events_admin.py |
| GET | `/admin/agents/event-triggers` | api_client_only | API Client Only | control_plane/app/api/agent_events_admin.py |
| POST | `/admin/agents/event-triggers/{trigger_id}/pause` | api_client_only | API Client Only | control_plane/app/api/agent_events_admin.py |
| POST | `/admin/agents/event-triggers/{trigger_id}/resume` | api_client_only | API Client Only | control_plane/app/api/agent_events_admin.py |
| GET | `/admin/agents/execution/jobs` | has_frontend | Inherited from /admin/agents/execution: Covered by Worker DLQ and Operations Dashboard. | control_plane/app/api/agent_execution_admin.py |
| POST | `/admin/agents/execution/jobs/{job_id}/cancel` | has_frontend | Inherited from /admin/agents/execution: Covered by Worker DLQ and Operations Dashboard. | control_plane/app/api/agent_execution_admin.py |
| POST | `/admin/agents/execution/jobs/{job_id}/retry` | has_frontend | Inherited from /admin/agents/execution: Covered by Worker DLQ and Operations Dashboard. | control_plane/app/api/agent_execution_admin.py |
| GET | `/admin/agents/execution/workers` | has_frontend | Inherited from /admin/agents/execution: Covered by Worker DLQ and Operations Dashboard. | control_plane/app/api/agent_execution_admin.py |
| POST | `/admin/agents/federated-memory/peers` | api_client_only | Inherited from /admin/agents/federated-memory: Internal peer-to-peer sync. | control_plane/app/api/agent_federated_memory_admin.py |
| POST | `/admin/agents/federated-memory/revoke` | api_client_only | Inherited from /admin/agents/federated-memory: Internal peer-to-peer sync. | control_plane/app/api/agent_federated_memory_admin.py |
| POST | `/admin/agents/federated-memory/sync/summary` | api_client_only | Inherited from /admin/agents/federated-memory: Internal peer-to-peer sync. | control_plane/app/api/agent_federated_memory_admin.py |
| GET | `/admin/agents/governance/decisions` | has_frontend | Inherited from /admin/agents/governance: Covered by Sovereign Governance and Policy Center. | control_plane/app/api/agent_governance_admin.py |
| GET | `/admin/agents/governance/dlp/stats` | has_frontend | Inherited from /admin/agents/governance: Covered by Sovereign Governance and Policy Center. | control_plane/app/api/agent_governance_admin.py |
| GET | `/admin/agents/governance/dlp/violations` | has_frontend | Inherited from /admin/agents/governance: Covered by Sovereign Governance and Policy Center. | control_plane/app/api/agent_governance_admin.py |
| GET | `/admin/agents/governance/policies` | has_frontend | Inherited from /admin/agents/governance: Covered by Sovereign Governance and Policy Center. | control_plane/app/api/agent_governance_admin.py |
| POST | `/admin/agents/governance/policies/simulate` | has_frontend | Inherited from /admin/agents/governance: Covered by Sovereign Governance and Policy Center. | control_plane/app/api/agent_governance_admin.py |
| POST | `/admin/agents/governance/{agent_id}/promote` | has_frontend | Inherited from /admin/agents/governance: Covered by Sovereign Governance and Policy Center. | control_plane/app/api/agent_governance_admin.py |
| POST | `/admin/agents/governance/{agent_id}/promotion-check` | has_frontend | Inherited from /admin/agents/governance: Covered by Sovereign Governance and Policy Center. | control_plane/app/api/agent_governance_admin.py |
| GET | `/admin/agents/governance/{agent_id}/promotion-history` | has_frontend | Inherited from /admin/agents/governance: Covered by Sovereign Governance and Policy Center. | control_plane/app/api/agent_governance_admin.py |
| POST | `/admin/agents/graphs/run` | api_client_only | API Client Only | control_plane/app/api/agent_graph_admin.py |
| GET | `/admin/agents/graphs/runs` | api_client_only | API Client Only | control_plane/app/api/agent_graph_admin.py |
| GET | `/admin/agents/graphs/runs/{run_id}` | api_client_only | API Client Only | control_plane/app/api/agent_graph_admin.py |
| POST | `/admin/agents/graphs/runs/{run_id}/cancel` | api_client_only | API Client Only | control_plane/app/api/agent_graph_admin.py |
| POST | `/admin/agents/graphs/validate` | api_client_only | API Client Only | control_plane/app/api/agent_graph_admin.py |
| POST | `/admin/agents/handoff-policies` | api_client_only | API Client Only | control_plane/app/api/agent_handoffs_admin.py |
| GET | `/admin/agents/handoff-policies` | api_client_only | API Client Only | control_plane/app/api/agent_handoffs_admin.py |
| GET | `/admin/agents/iam/audit` | api_client_only | API Client Only | control_plane/app/api/agent_iam_admin.py |
| GET | `/admin/agents/incidents/playbooks` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| POST | `/admin/agents/incidents/{id}/run-playbook` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| GET | `/admin/agents/memory/access-events` | api_client_only | API Client Only | control_plane/app/api/agent_memory_admin.py |
| GET | `/admin/agents/memory/cognitive` | api_client_only | API Client Only | control_plane/app/api/agent_cognitive_memory_admin.py |
| GET | `/admin/agents/memory/consents` | api_client_only | API Client Only | control_plane/app/api/agent_memory_admin.py |
| POST | `/admin/agents/memory/consents` | api_client_only | API Client Only | control_plane/app/api/agent_memory_admin.py |
| POST | `/admin/agents/memory/delete-request` | api_client_only | API Client Only | control_plane/app/api/agent_memory_admin.py |
| GET | `/admin/agents/memory/explain/{memory_id}` | api_client_only | API Client Only | control_plane/app/api/agent_cognitive_memory_admin.py |
| POST | `/admin/agents/memory/export` | api_client_only | API Client Only | control_plane/app/api/agent_memory_admin.py |
| GET | `/admin/agents/memory/items` | api_client_only | API Client Only | control_plane/app/api/agent_memory_admin.py |
| DELETE | `/admin/agents/memory/items/{item_id}` | api_client_only | API Client Only | control_plane/app/api/agent_memory_admin.py |
| GET | `/admin/agents/memory/policies` | api_client_only | API Client Only | control_plane/app/api/agent_memory_admin.py |
| POST | `/admin/agents/memory/policies` | api_client_only | API Client Only | control_plane/app/api/agent_memory_admin.py |
| POST | `/admin/agents/memory/retention/run` | api_client_only | API Client Only | control_plane/app/api/agent_memory_admin.py |
| POST | `/admin/agents/memory/search` | api_client_only | API Client Only | control_plane/app/api/agent_cognitive_memory_admin.py |
| POST | `/admin/agents/memory/summarize` | api_client_only | API Client Only | control_plane/app/api/agent_cognitive_memory_admin.py |
| GET | `/admin/agents/observability/metrics/summary` | api_client_only | API Client Only | control_plane/app/api/agent_observability_admin.py |
| GET | `/admin/agents/observability/overview` | api_client_only | API Client Only | control_plane/app/api/agent_observability_admin.py |
| POST | `/admin/agents/observability/runs/{run_id}/replay` | api_client_only | API Client Only | control_plane/app/api/agent_observability_admin.py |
| GET | `/admin/agents/observability/runs/{run_id}/timeline` | api_client_only | API Client Only | control_plane/app/api/agent_observability_admin.py |
| GET | `/admin/agents/observability/runs/{run_id}/trace` | api_client_only | API Client Only | control_plane/app/api/agent_observability_admin.py |
| GET | `/admin/agents/observability/telemetry/status` | api_client_only | API Client Only | control_plane/app/api/agent_observability_admin.py |
| POST | `/admin/agents/observability/traces/export` | api_client_only | API Client Only | control_plane/app/api/agent_observability_admin.py |
| GET | `/admin/agents/observability/traces/{run_id}` | api_client_only | API Client Only | control_plane/app/api/agent_observability_admin.py |
| POST | `/admin/agents/optimization/candidates/{candidate_id}/apply` | api_client_only | API Client Only | control_plane/app/api/agent_optimization_admin.py |
| POST | `/admin/agents/optimization/candidates/{candidate_id}/approve` | api_client_only | API Client Only | control_plane/app/api/agent_optimization_admin.py |
| POST | `/admin/agents/optimization/candidates/{candidate_id}/eval` | api_client_only | API Client Only | control_plane/app/api/agent_optimization_admin.py |
| GET | `/admin/agents/optimization/tournaments` | api_client_only | API Client Only | control_plane/app/api/agent_optimization_tournaments_admin.py |
| GET | `/admin/agents/optimization/tournaments/{tournament_id}` | api_client_only | API Client Only | control_plane/app/api/agent_optimization_tournaments_admin.py |
| POST | `/admin/agents/optimization/tournaments/{tournament_id}/apply-winner` | api_client_only | API Client Only | control_plane/app/api/agent_optimization_tournaments_admin.py |
| POST | `/admin/agents/optimization/tournaments/{tournament_id}/approve-winner` | api_client_only | API Client Only | control_plane/app/api/agent_optimization_tournaments_admin.py |
| POST | `/admin/agents/optimization/tournaments/{tournament_id}/run` | api_client_only | API Client Only | control_plane/app/api/agent_optimization_tournaments_admin.py |
| POST | `/admin/agents/protocols/a2a/handshake/dry-run` | api_client_only | API Client Only | control_plane/app/api/admin_agent_protocols.py |
| GET | `/admin/agents/protocols/a2a/peers` | api_client_only | API Client Only | control_plane/app/api/admin_agent_protocols.py |
| GET | `/admin/agents/protocols/mcp/servers` | api_client_only | API Client Only | control_plane/app/api/admin_agent_protocols.py |
| POST | `/admin/agents/protocols/mcp/servers/{server_id}/approve-tool` | api_client_only | API Client Only | control_plane/app/api/admin_agent_protocols.py |
| GET | `/admin/agents/protocols/trust/explain` | api_client_only | API Client Only | control_plane/app/api/admin_agent_protocols.py |
| GET | `/admin/agents/provider-validation/check` | api_client_only | API Client Only | control_plane/app/api/provider_validation_admin.py |
| GET | `/admin/agents/provider-validation/latest` | api_client_only | API Client Only | control_plane/app/api/provider_validation_admin.py |
| GET | `/admin/agents/provider-validation/providers` | api_client_only | API Client Only | control_plane/app/api/provider_validation_admin.py |
| POST | `/admin/agents/provider-validation/run` | api_client_only | API Client Only | control_plane/app/api/provider_validation_admin.py |
| GET | `/admin/agents/readiness` | api_client_only | API Client Only | control_plane/app/api/agent_readiness_admin.py |
| POST | `/admin/agents/readiness/run` | api_client_only | API Client Only | control_plane/app/api/agent_readiness_admin.py |
| GET | `/admin/agents/replay/records` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| POST | `/admin/agents/replay/verify/{execution_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| GET | `/admin/agents/replay/violations` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| GET | `/admin/agents/routing/capabilities` | api_client_only | API Client Only | control_plane/app/api/agent_routing_admin.py |
| GET | `/admin/agents/routing/decisions` | api_client_only | API Client Only | control_plane/app/api/agent_routing_admin.py |
| POST | `/admin/agents/routing/policies` | api_client_only | API Client Only | control_plane/app/api/agent_routing_admin.py |
| POST | `/admin/agents/routing/simulate` | api_client_only | API Client Only | control_plane/app/api/agent_routing_admin.py |
| GET | `/admin/agents/runs/{run_id}/handoffs` | api_client_only | API Client Only | control_plane/app/api/agent_handoffs_admin.py |
| GET | `/admin/agents/runtime/actions/{execution_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| POST | `/admin/agents/runtime/execute/{execution_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| GET | `/admin/agents/runtime/executions` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| POST | `/admin/agents/runtime/plans` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| GET | `/admin/agents/runtime/profiles` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| GET | `/admin/agents/runtime/status` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| POST | `/admin/agents/sab/export/{agent_id}` | api_client_only | API Client Only | control_plane/app/api/agent_sab_admin.py |
| POST | `/admin/agents/sab/import` | api_client_only | API Client Only | control_plane/app/api/agent_sab_admin.py |
| POST | `/admin/agents/sab/verify` | api_client_only | API Client Only | control_plane/app/api/agent_sab_admin.py |
| GET | `/admin/agents/slo/classes` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| GET | `/admin/agents/slo/report` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| POST | `/admin/agents/studio/flows` | api_client_only | API Client Only | control_plane/app/api/agent_studio_ga_admin.py |
| GET | `/admin/agents/studio/flows` | api_client_only | API Client Only | control_plane/app/api/agent_studio_admin.py |
| GET | `/admin/agents/studio/flows/runs/{run_id}/trace` | api_client_only | API Client Only | control_plane/app/api/agent_studio_admin.py |
| POST | `/admin/agents/studio/flows/{flow_id}/deploy` | api_client_only | API Client Only | control_plane/app/api/agent_studio_ga_admin.py |
| POST | `/admin/agents/studio/flows/{flow_id}/versions` | api_client_only | API Client Only | control_plane/app/api/agent_studio_ga_admin.py |
| GET | `/admin/agents/studio/flows/{flow_id}/versions/{version_id}/dag` | api_client_only | API Client Only | control_plane/app/api/agent_studio_ga_admin.py |
| GET | `/admin/agents/studio/flows/{id}` | api_client_only | API Client Only | control_plane/app/api/agent_studio_admin.py |
| POST | `/admin/agents/studio/flows/{id}/compile` | api_client_only | API Client Only | control_plane/app/api/agent_studio_admin.py |
| POST | `/admin/agents/studio/flows/{id}/dry-run` | api_client_only | API Client Only | control_plane/app/api/agent_studio_admin.py |
| POST | `/admin/agents/studio/flows/{id}/explain` | api_client_only | API Client Only | control_plane/app/api/agent_studio_admin.py |
| POST | `/admin/agents/studio/flows/{id}/validate` | api_client_only | API Client Only | control_plane/app/api/agent_studio_admin.py |
| GET | `/admin/agents/studio/templates` | api_client_only | API Client Only | control_plane/app/api/agent_studio_ga_admin.py |
| GET | `/admin/agents/studio/templates/{template_id}` | api_client_only | API Client Only | control_plane/app/api/agent_studio_ga_admin.py |
| POST | `/admin/agents/studio/versions/{version_id}/compile` | api_client_only | API Client Only | control_plane/app/api/agent_studio_ga_admin.py |
| POST | `/admin/agents/studio/versions/{version_id}/deploy-real` | api_client_only | API Client Only | control_plane/app/api/agent_studio_ga_admin.py |
| POST | `/admin/agents/studio/versions/{version_id}/validate` | api_client_only | API Client Only | control_plane/app/api/agent_studio_ga_admin.py |
| POST | `/admin/agents/teams` | api_client_only | API Client Only | control_plane/app/api/agent_teams_admin.py |
| GET | `/admin/agents/teams` | api_client_only | API Client Only | control_plane/app/api/agent_teams_admin.py |
| GET | `/admin/agents/teams/runs/{run_id}/trace` | api_client_only | API Client Only | control_plane/app/api/agent_teams_admin.py |
| POST | `/admin/agents/teams/{id}/runs` | api_client_only | API Client Only | control_plane/app/api/agent_teams_admin.py |
| GET | `/admin/agents/tools` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| POST | `/admin/agents/tools` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| GET | `/admin/agents/tools/approvals` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| POST | `/admin/agents/tools/approvals/{action_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_trusted_agents_admin.py |
| POST | `/admin/agents/tools/web-search/test` | api_client_only | API Client Only | control_plane/app/api/web_search_admin.py |
| POST | `/admin/agents/wallet/authorizations/{auth_id}/approve` | api_client_only | API Client Only | control_plane/app/api/agent_wallet_admin.py |
| GET | `/admin/agents/web-search/audit` | api_client_only | API Client Only | control_plane/app/api/web_search_admin.py |
| GET | `/admin/agents/web-search/cache` | api_client_only | API Client Only | control_plane/app/api/web_search_admin.py |
| GET | `/admin/agents/worker/dlq` | api_client_only | API Client Only | control_plane/app/api/agent_worker_admin.py |
| DELETE | `/admin/agents/worker/dlq/{dlq_id}` | api_client_only | API Client Only | control_plane/app/api/agent_worker_admin.py |
| POST | `/admin/agents/worker/dlq/{dlq_id}/retry` | api_client_only | API Client Only | control_plane/app/api/agent_worker_admin.py |
| POST | `/admin/agents/workflows` | api_client_only | API Client Only | control_plane/app/api/agent_workflows_admin.py |
| POST | `/admin/agents/workflows/webhooks/{subscription_id}` | api_client_only | API Client Only | control_plane/app/api/agent_workflows_admin.py |
| POST | `/admin/agents/workflows/{id}/run` | api_client_only | API Client Only | control_plane/app/api/agent_workflows_admin.py |
| GET | `/admin/agents/workflows/{id}/run/{run_id}` | api_client_only | API Client Only | control_plane/app/api/agent_workflows_admin.py |
| POST | `/admin/agents/workflows/{id}/run/{run_id}/cancel` | api_client_only | API Client Only | control_plane/app/api/agent_workflows_admin.py |
| GET | `/admin/agents/workflows/{id}/run/{run_id}/external-events` | api_client_only | API Client Only | control_plane/app/api/agent_workflows_admin.py |
| POST | `/admin/agents/workflows/{id}/run/{run_id}/polling-job` | api_client_only | API Client Only | control_plane/app/api/agent_workflows_admin.py |
| POST | `/admin/agents/workflows/{id}/run/{run_id}/signal` | api_client_only | API Client Only | control_plane/app/api/agent_workflows_admin.py |
| POST | `/admin/agents/workflows/{id}/run/{run_id}/webhook-wait` | api_client_only | API Client Only | control_plane/app/api/agent_workflows_admin.py |
| POST | `/admin/agents/workspaces` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| GET | `/admin/agents/workspaces` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| POST | `/admin/agents/workspaces/{id}/artifacts` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| GET | `/admin/agents/workspaces/{id}/artifacts` | api_client_only | API Client Only | control_plane/app/api/agent_workspace_admin.py |
| GET | `/admin/agents/{agent_id}/canary/comparisons` | api_client_only | API Client Only | control_plane/app/api/agent_canary_admin.py |
| POST | `/admin/agents/{agent_id}/canary/promote` | api_client_only | API Client Only | control_plane/app/api/agent_canary_admin.py |
| POST | `/admin/agents/{agent_id}/canary/start` | api_client_only | API Client Only | control_plane/app/api/agent_canary_admin.py |
| GET | `/admin/agents/{agent_id}/environments` | api_client_only | API Client Only | control_plane/app/api/agent_environments_admin.py |
| POST | `/admin/agents/{agent_id}/feedback` | api_client_only | API Client Only | control_plane/app/api/agent_cognitive_loopback_admin.py |
| POST | `/admin/agents/{agent_id}/fewshot-examples/{example_id}/activate` | api_client_only | API Client Only | control_plane/app/api/agent_cognitive_loopback_admin.py |
| GET | `/admin/agents/{agent_id}/learning-candidates` | api_client_only | API Client Only | control_plane/app/api/agent_cognitive_loopback_admin.py |
| POST | `/admin/agents/{agent_id}/learning-candidates/{candidate_id}/approve` | api_client_only | API Client Only | control_plane/app/api/agent_cognitive_loopback_admin.py |
| POST | `/admin/agents/{agent_id}/learning-candidates/{candidate_id}/eval` | api_client_only | API Client Only | control_plane/app/api/agent_cognitive_loopback_admin.py |
| GET | `/admin/agents/{agent_id}/memory/` | api_client_only | API Client Only | control_plane/app/api/admin_agent_memory.py |
| POST | `/admin/agents/{agent_id}/memory/compact/dry-run` | api_client_only | API Client Only | control_plane/app/api/admin_agent_memory.py |
| GET | `/admin/agents/{agent_id}/memory/events` | api_client_only | API Client Only | control_plane/app/api/admin_agent_memory.py |
| POST | `/admin/agents/{agent_id}/memory/{event_id}/forget` | api_client_only | API Client Only | control_plane/app/api/admin_agent_memory.py |
| POST | `/admin/agents/{agent_id}/memory/{event_id}/redact` | api_client_only | API Client Only | control_plane/app/api/admin_agent_memory.py |
| POST | `/admin/agents/{agent_id}/promote` | api_client_only | API Client Only | control_plane/app/api/agent_environments_admin.py |
| POST | `/admin/agents/{agent_id}/rollback` | api_client_only | API Client Only | control_plane/app/api/agent_environments_admin.py |
| GET | `/admin/agents/{agent_id}/uncertainty-events` | api_client_only | API Client Only | control_plane/app/api/agent_uncertainty_admin.py |
| POST | `/admin/agents/{agent_id}/uncertainty-policy` | api_client_only | API Client Only | control_plane/app/api/agent_uncertainty_admin.py |
| POST | `/admin/agents/{agent_id}/wallet` | api_client_only | API Client Only | control_plane/app/api/agent_wallet_admin.py |
| GET | `/admin/agents/{agent_id}/wallet` | api_client_only | API Client Only | control_plane/app/api/agent_wallet_admin.py |
| POST | `/admin/agents/{agent_id}/wallet/spend` | api_client_only | API Client Only | control_plane/app/api/agent_wallet_admin.py |
| PATCH | `/admin/agents/{id}` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| POST | `/admin/agents/{id}/activate` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| POST | `/admin/agents/{id}/deprecate` | api_client_only | API Client Only | control_plane/app/api/agent_runtime_admin.py |
| GET | `/admin/agents/{id}/optimization/candidates` | api_client_only | API Client Only | control_plane/app/api/agent_optimization_admin.py |
| POST | `/admin/agents/{id}/optimization/experiments` | api_client_only | API Client Only | control_plane/app/api/agent_optimization_admin.py |
| POST | `/admin/agents/{id}/optimization/tournaments` | api_client_only | API Client Only | control_plane/app/api/agent_optimization_tournaments_admin.py |
| POST | `/admin/agents/{id}/service-principal` | api_client_only | API Client Only | control_plane/app/api/agent_iam_admin.py |
| GET | `/admin/agents/{id}/service-principal` | api_client_only | API Client Only | control_plane/app/api/agent_iam_admin.py |
| POST | `/admin/agents/{id}/token-grants` | api_client_only | API Client Only | control_plane/app/api/agent_iam_admin.py |
| DELETE | `/admin/agents/{id}/token-grants/{grant_id}` | api_client_only | API Client Only | control_plane/app/api/agent_iam_admin.py |
| POST | `/admin/agents/{id}/tokens/exchange` | api_client_only | API Client Only | control_plane/app/api/agent_iam_admin.py |
| GET | `/admin/aiops/anomalies` | api_client_only | API Client Only | control_plane/app/api/commercial_aiops_admin.py |
| GET | `/admin/aiops/forecasts` | api_client_only | API Client Only | control_plane/app/api/commercial_aiops_admin.py |
| GET | `/admin/aiops/recommendations` | api_client_only | API Client Only | control_plane/app/api/commercial_aiops_admin.py |
| GET | `/admin/aiops/risk-trends` | api_client_only | API Client Only | control_plane/app/api/commercial_aiops_admin.py |
| POST | `/admin/aiops/run-cycle` | api_client_only | API Client Only | control_plane/app/api/commercial_aiops_admin.py |
| GET | `/admin/aiops/status` | api_client_only | API Client Only | control_plane/app/api/commercial_aiops_admin.py |
| POST | `/admin/api-keys` | api_client_only | API Client Only | control_plane/app/api/admin_api_keys.py |
| GET | `/admin/api-keys` | api_client_only | API Client Only | control_plane/app/api/admin_api_keys.py |
| DELETE | `/admin/api-keys/{api_key_id}` | api_client_only | API Client Only | control_plane/app/api/admin_api_keys.py |
| POST | `/admin/api-keys/{api_key_id}/rotate` | api_client_only | API Client Only | control_plane/app/api/admin_api_keys.py |
| POST | `/admin/approvals` | no_frontend | None | control_plane/app/api/admin_critical_approvals.py |
| GET | `/admin/approvals` | no_frontend | None | control_plane/app/api/admin_critical_approvals.py |
| GET | `/admin/approvals/{id}` | no_frontend | None | control_plane/app/api/admin_critical_approvals.py |
| POST | `/admin/approvals/{id}/approve` | no_frontend | None | control_plane/app/api/admin_critical_approvals.py |
| POST | `/admin/approvals/{id}/reject` | no_frontend | None | control_plane/app/api/admin_critical_approvals.py |
| GET | `/admin/attestation/challenges` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| POST | `/admin/attestation/challenges` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| POST | `/admin/attestation/challenges/{challenge_id}/respond` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| GET | `/admin/attestation/drift` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| GET | `/admin/attestation/evidence` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| GET | `/admin/attestation/measurements` | no_frontend | None | control_plane/app/api/commercial_attestation_admin.py |
| GET | `/admin/attestation/measurements/summary` | no_frontend | None | control_plane/app/api/commercial_attestation_admin.py |
| GET | `/admin/attestation/policies` | no_frontend | None | control_plane/app/api/commercial_attestation_admin.py |
| POST | `/admin/attestation/policies` | no_frontend | None | control_plane/app/api/commercial_attestation_admin.py |
| GET | `/admin/attestation/runtime` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| POST | `/admin/attestation/runtime` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| GET | `/admin/attestation/runtime/summary` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| GET | `/admin/attestation/runtime/{attestation_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| POST | `/admin/attestation/runtime/{attestation_id}/drift` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| POST | `/admin/attestation/runtime/{attestation_id}/revoke` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| POST | `/admin/attestation/runtime/{attestation_id}/trust-score` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| POST | `/admin/attestation/runtime/{attestation_id}/verify` | api_client_only | API Client Only | control_plane/app/api/commercial_attestation_admin.py |
| GET | `/admin/attestation/verify` | no_frontend | None | control_plane/app/api/commercial_attestation_admin.py |
| GET | `/admin/autoscaling/events` | no_frontend | None | control_plane/app/api/gpu_autoscaling_admin.py |
| GET | `/admin/autoscaling/policies` | no_frontend | None | control_plane/app/api/gpu_autoscaling_admin.py |
| POST | `/admin/autoscaling/policies` | no_frontend | None | control_plane/app/api/gpu_autoscaling_admin.py |
| GET | `/admin/backends` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| POST | `/admin/backends` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| POST | `/admin/backends/circuit-breaker/reset` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| GET | `/admin/backends/health` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| GET | `/admin/backends/lifecycle/drift-history` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| POST | `/admin/backends/lifecycle/reconcile-all` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| POST | `/admin/backends/list-models` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| GET | `/admin/backends/routing` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| POST | `/admin/backends/test-connection` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| PATCH | `/admin/backends/{backend_id}` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| GET | `/admin/backends/{backend_id}/health` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| GET | `/admin/backends/{backend_id}/lifecycle/observed` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| POST | `/admin/backends/{backend_id}/lifecycle/reconcile` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| GET | `/admin/backends/{backend_id}/logs` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| POST | `/admin/backends/{backend_id}/restart` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| POST | `/admin/backends/{backend_id}/start` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| POST | `/admin/backends/{backend_id}/stop` | api_client_only | API Client Only | control_plane/app/api/admin_backends.py |
| POST | `/admin/backup` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| GET | `/admin/backup` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| POST | `/admin/backup/audit/verify` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| POST | `/admin/backup/create` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| GET | `/admin/backup/list` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| POST | `/admin/backup/restore-requests` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| POST | `/admin/backup/restore-requests/{id}/approve` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| POST | `/admin/backup/restore-requests/{id}/execute` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| GET | `/admin/backup/{backup_id}` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| POST | `/admin/backup/{backup_id}/restore` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| POST | `/admin/backup/{backup_id}/restore/dry-run` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| GET | `/admin/backup/{backup_id}/status` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| GET | `/admin/backup/{backup_id}/verify` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| POST | `/admin/backup/{backup_id}/verify` | api_client_only | API Client Only | control_plane/app/api/admin_backup.py |
| GET | `/admin/benchmarks` | no_frontend | None | control_plane/app/api/admin_benchmarks.py |
| GET | `/admin/benchmarks/{model}` | no_frontend | None | control_plane/app/api/admin_benchmarks.py |
| GET | `/admin/billing/anomalies` | no_frontend | None | control_plane/app/api/commercial_revenue_forecasting_admin.py |
| POST | `/admin/billing/anomalies/run` | no_frontend | None | control_plane/app/api/commercial_revenue_forecasting_admin.py |
| POST | `/admin/billing/anomalies/{anomaly_id}/ack` | no_frontend | None | control_plane/app/api/commercial_revenue_forecasting_admin.py |
| POST | `/admin/billing/anomalies/{anomaly_id}/ignore` | no_frontend | None | control_plane/app/api/commercial_revenue_forecasting_admin.py |
| POST | `/admin/billing/anomalies/{anomaly_id}/resolve` | no_frontend | None | control_plane/app/api/commercial_revenue_forecasting_admin.py |
| GET | `/admin/billing/audit/validate-chain` | no_frontend | None | control_plane/app/api/billing_reconciliation_admin.py |
| GET | `/admin/billing/clients/{client_id}/invoice/preview` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| GET | `/admin/billing/disputes` | no_frontend | None | control_plane/app/api/billing_reconciliation_admin.py |
| POST | `/admin/billing/disputes/manual-credit` | no_frontend | None | control_plane/app/api/billing_reconciliation_admin.py |
| POST | `/admin/billing/disputes/{id}/reject` | no_frontend | None | control_plane/app/api/billing_reconciliation_admin.py |
| POST | `/admin/billing/disputes/{id}/resolve` | api_client_only | API Client Only | control_plane/app/api/billing_reconciliation_admin.py |
| POST | `/admin/billing/disputes/{id}/review` | no_frontend | None | control_plane/app/api/billing_reconciliation_admin.py |
| GET | `/admin/billing/forecast/overview` | no_frontend | None | control_plane/app/api/commercial_revenue_forecasting_admin.py |
| GET | `/admin/billing/forecast/records` | no_frontend | None | control_plane/app/api/commercial_revenue_forecasting_admin.py |
| POST | `/admin/billing/forecast/run` | no_frontend | None | control_plane/app/api/commercial_revenue_forecasting_admin.py |
| GET | `/admin/billing/invoices` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| POST | `/admin/billing/invoices/generate` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| GET | `/admin/billing/invoices/preview` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| PATCH | `/admin/billing/invoices/{invoice_id}/cancel` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| PATCH | `/admin/billing/invoices/{invoice_id}/mark-overdue` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| PATCH | `/admin/billing/invoices/{invoice_id}/mark-paid` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| GET | `/admin/billing/margins/summary` | no_frontend | None | control_plane/app/api/billing_admin.py |
| GET | `/admin/billing/payments` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| POST | `/admin/billing/payments` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| POST | `/admin/billing/payments/create-intent` | api_client_only | API Client Only | control_plane/app/api/billing_payments.py |
| GET | `/admin/billing/payments/{id}` | api_client_only | API Client Only | control_plane/app/api/billing_payments.py |
| PATCH | `/admin/billing/payments/{payment_id}/cancel` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| GET | `/admin/billing/plans` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| POST | `/admin/billing/plans` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| PATCH | `/admin/billing/plans/{plan_id}` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| PATCH | `/admin/billing/plans/{plan_id}/models` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| GET | `/admin/billing/pricing-rules` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| POST | `/admin/billing/pricing/simulate` | no_frontend | None | control_plane/app/api/billing_admin.py |
| GET | `/admin/billing/provider-costs` | no_frontend | None | control_plane/app/api/billing_admin.py |
| GET | `/admin/billing/reconciliation/mismatches` | api_client_only | API Client Only | control_plane/app/api/billing_reconciliation_admin.py |
| GET | `/admin/billing/reconciliation/overview` | api_client_only | API Client Only | control_plane/app/api/billing_reconciliation_admin.py |
| POST | `/admin/billing/reconciliation/run` | api_client_only | API Client Only | control_plane/app/api/billing_reconciliation_admin.py |
| POST | `/admin/billing/reconciliation/{id}/resolve` | no_frontend | None | control_plane/app/api/billing_reconciliation_admin.py |
| GET | `/admin/billing/revenue-escalations/deliveries` | no_frontend | None | control_plane/app/api/commercial_revenue_escalations_admin.py |
| GET | `/admin/billing/revenue-escalations/policies` | no_frontend | None | control_plane/app/api/commercial_revenue_escalations_admin.py |
| POST | `/admin/billing/revenue-escalations/policies` | no_frontend | None | control_plane/app/api/commercial_revenue_escalations_admin.py |
| PATCH | `/admin/billing/revenue-escalations/policies/{policy_id}` | no_frontend | None | control_plane/app/api/commercial_revenue_escalations_admin.py |
| POST | `/admin/billing/revenue-escalations/retry/{delivery_id}` | no_frontend | None | control_plane/app/api/commercial_revenue_escalations_admin.py |
| GET | `/admin/billing/revenue-escalations/status` | no_frontend | None | control_plane/app/api/commercial_revenue_escalations_admin.py |
| POST | `/admin/billing/revenue-escalations/test` | no_frontend | None | control_plane/app/api/commercial_revenue_escalations_admin.py |
| GET | `/admin/billing/revenue-protection/actions` | no_frontend | None | control_plane/app/api/commercial_revenue_protection_admin.py |
| POST | `/admin/billing/revenue-protection/actions/{action_id}/apply` | no_frontend | None | control_plane/app/api/commercial_revenue_protection_admin.py |
| POST | `/admin/billing/revenue-protection/actions/{action_id}/revert` | no_frontend | None | control_plane/app/api/commercial_revenue_protection_admin.py |
| POST | `/admin/billing/revenue-protection/evaluate` | no_frontend | None | control_plane/app/api/commercial_revenue_protection_admin.py |
| GET | `/admin/billing/revenue-protection/policies` | no_frontend | None | control_plane/app/api/commercial_revenue_protection_admin.py |
| POST | `/admin/billing/revenue-protection/policies` | no_frontend | None | control_plane/app/api/commercial_revenue_protection_admin.py |
| PATCH | `/admin/billing/revenue-protection/policies/{policy_id}` | no_frontend | None | control_plane/app/api/commercial_revenue_protection_admin.py |
| GET | `/admin/billing/revenue-protection/status` | no_frontend | None | control_plane/app/api/commercial_revenue_protection_admin.py |
| POST | `/admin/billing/run-cycle` | api_client_only | API Client Only | control_plane/app/api/admin_billing.py |
| GET | `/admin/billing/usage-financials` | no_frontend | None | control_plane/app/api/billing_admin.py |
| GET | `/admin/billing/wallets` | no_frontend | None | control_plane/app/api/wallet_admin.py |
| GET | `/admin/billing/wallets/{client_id}` | no_frontend | None | control_plane/app/api/wallet_admin.py |
| POST | `/admin/billing/wallets/{client_id}/adjustment` | no_frontend | None | control_plane/app/api/wallet_admin.py |
| POST | `/admin/billing/wallets/{client_id}/manual-credit` | no_frontend | None | control_plane/app/api/wallet_admin.py |
| GET | `/admin/billing/wallets/{client_id}/transactions` | no_frontend | None | control_plane/app/api/wallet_admin.py |
| GET | `/admin/cache/entries` | no_frontend | None | control_plane/app/api/admin_cache.py |
| POST | `/admin/cache/invalidate` | no_frontend | None | control_plane/app/api/admin_cache.py |
| GET | `/admin/cache/policies` | no_frontend | None | control_plane/app/api/admin_cache.py |
| POST | `/admin/cache/policies` | no_frontend | None | control_plane/app/api/admin_cache.py |
| DELETE | `/admin/cache/responses` | no_frontend | None | control_plane/app/api/admin_cache.py |
| GET | `/admin/cache/stats` | no_frontend | None | control_plane/app/api/admin_cache.py |
| GET | `/admin/capabilities` | no_frontend | None | control_plane/app/api/admin.py |
| GET | `/admin/chaos/experiments` | no_frontend | None | control_plane/app/api/chaos_admin.py |
| GET | `/admin/chaos/runs` | no_frontend | None | control_plane/app/api/chaos_admin.py |
| POST | `/admin/chaos/runs` | no_frontend | None | control_plane/app/api/chaos_admin.py |
| POST | `/admin/chaos/runs/{id}/abort` | no_frontend | None | control_plane/app/api/chaos_admin.py |
| GET | `/admin/chaos/runs/{id}/report` | no_frontend | None | control_plane/app/api/chaos_admin.py |
| GET | `/admin/chaos/status` | no_frontend | None | control_plane/app/api/chaos_admin.py |
| POST | `/admin/clients` | api_client_only | API Client Only | control_plane/app/api/admin_clients.py |
| GET | `/admin/clients` | api_client_only | API Client Only | control_plane/app/api/admin_clients.py |
| GET | `/admin/clients/export-data` | api_client_only | API Client Only | control_plane/app/api/admin_clients.py |
| DELETE | `/admin/clients/{client_id}` | api_client_only | API Client Only | control_plane/app/api/admin_clients.py |
| PATCH | `/admin/clients/{client_id}` | api_client_only | API Client Only | control_plane/app/api/admin_clients.py |
| PATCH | `/admin/clients/{client_id}/billing-plan` | api_client_only | API Client Only | control_plane/app/api/admin_clients.py |
| POST | `/admin/clients/{client_id}/block` | api_client_only | API Client Only | control_plane/app/api/admin_clients.py |
| POST | `/admin/clients/{client_id}/purge` | api_client_only | API Client Only | control_plane/app/api/admin_clients.py |
| PATCH | `/admin/clients/{client_id}/system-prompt` | api_client_only | API Client Only | control_plane/app/api/admin_clients.py |
| POST | `/admin/clients/{client_id}/unblock` | api_client_only | API Client Only | control_plane/app/api/admin_clients.py |
| POST | `/admin/clusters` | no_frontend | None | control_plane/app/api/multi_cluster_admin.py |
| GET | `/admin/clusters` | no_frontend | None | control_plane/app/api/multi_cluster_admin.py |
| GET | `/admin/clusters/status` | no_frontend | None | control_plane/app/api/multi_cluster_admin.py |
| GET | `/admin/clusters/{id}` | no_frontend | None | control_plane/app/api/multi_cluster_admin.py |
| POST | `/admin/clusters/{id}/drain` | no_frontend | None | control_plane/app/api/multi_cluster_admin.py |
| POST | `/admin/clusters/{id}/maintenance` | no_frontend | None | control_plane/app/api/multi_cluster_admin.py |
| POST | `/admin/clusters/{id}/resume` | no_frontend | None | control_plane/app/api/multi_cluster_admin.py |
| GET | `/admin/clusters/{id}/sync-events` | no_frontend | None | control_plane/app/api/multi_cluster_admin.py |
| GET | `/admin/commercial-guardrails/overview` | no_frontend | None | control_plane/app/api/commercial_guardrails_admin.py |
| GET | `/admin/commercial-guardrails/runtime-status` | no_frontend | None | control_plane/app/api/commercial_guardrails_admin.py |
| POST | `/admin/commercial-guardrails/simulate` | no_frontend | None | control_plane/app/api/commercial_guardrails_admin.py |
| POST | `/admin/compat/analyze` | no_frontend | None | control_plane/app/api/agent_compatibility_admin.py |
| POST | `/admin/compat/migrate` | no_frontend | None | control_plane/app/api/agent_compatibility_admin.py |
| GET | `/admin/compliance/approval-chains` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/approval-chains/{chain_id}/approve` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/approval-chains/{chain_id}/reject` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| GET | `/admin/compliance/attestations` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/attestations` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/audit-pack/generate` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| GET | `/admin/compliance/audit-pack/{id}` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| GET | `/admin/compliance/audit-report` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| GET | `/admin/compliance/control-map` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| GET | `/admin/compliance/control-map/{framework}/{control_id}` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| GET | `/admin/compliance/controls` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/controls` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| GET | `/admin/compliance/evidence-packages` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/evidence/collect` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| POST | `/admin/compliance/evidence/collect-all` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| GET | `/admin/compliance/evidence/latest` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| GET | `/admin/compliance/exceptions` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/exceptions` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/exceptions/{exception_id}/accept` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/exceptions/{exception_id}/remediate` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| GET | `/admin/compliance/frameworks` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| GET | `/admin/compliance/gap-analysis` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| GET | `/admin/compliance/isms/policies` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| GET | `/admin/compliance/isms/risk-register` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| GET | `/admin/compliance/isms/status` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| GET | `/admin/compliance/operational-controls` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/operational-controls` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| GET | `/admin/compliance/operational-controls/effectiveness` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| GET | `/admin/compliance/operational-controls/evidence` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/operational-controls/evidence` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| GET | `/admin/compliance/operational-controls/overdue` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| GET | `/admin/compliance/operational-controls/reviews` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| POST | `/admin/compliance/operational-controls/reviews/{id}/complete` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| PATCH | `/admin/compliance/operational-controls/{id}` | no_frontend | None | control_plane/app/api/commercial_compliance_admin.py |
| GET | `/admin/compliance/readiness-report/{framework_id}` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| POST | `/admin/compliance/soc2/access-review` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| GET | `/admin/compliance/soc2/access-reviews` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| POST | `/admin/compliance/soc2/exceptions` | no_frontend | None | control_plane/app/api/compliance_admin.py |
| GET | `/admin/config/detailed/{key}` | no_frontend | None | control_plane/app/api/admin_config.py |
| GET | `/admin/config/effective` | no_frontend | None | control_plane/app/api/admin_config.py |
| GET | `/admin/distributed-runtime/clusters` | no_frontend | None | control_plane/app/api/distributed_fabric_admin.py |
| POST | `/admin/distributed-runtime/clusters` | no_frontend | None | control_plane/app/api/distributed_fabric_admin.py |
| GET | `/admin/distributed-runtime/jobs` | no_frontend | None | control_plane/app/api/distributed_fabric_admin.py |
| POST | `/admin/distributed-runtime/jobs/{job_id}/failover` | no_frontend | None | control_plane/app/api/distributed_fabric_admin.py |
| GET | `/admin/distributed-runtime/nodes` | no_frontend | None | control_plane/app/api/distributed_fabric_admin.py |
| POST | `/admin/enterprise/onboarding/projects` | api_client_only | API Client Only | control_plane/app/api/enterprise_onboarding_admin.py |
| GET | `/admin/enterprise/onboarding/projects` | api_client_only | API Client Only | control_plane/app/api/enterprise_onboarding_admin.py |
| GET | `/admin/enterprise/onboarding/projects/{id}` | api_client_only | API Client Only | control_plane/app/api/enterprise_onboarding_admin.py |
| POST | `/admin/enterprise/onboarding/projects/{id}/handover-report` | api_client_only | API Client Only | control_plane/app/api/enterprise_onboarding_admin.py |
| PATCH | `/admin/enterprise/onboarding/tasks/{id}` | no_frontend | None | control_plane/app/api/enterprise_onboarding_admin.py |
| GET | `/admin/evaluation/agent-evaluation/benchmarks` | api_client_only | API Client Only | control_plane/app/api/admin_evaluation.py |
| POST | `/admin/evaluation/agent-evaluation/runs` | api_client_only | API Client Only | control_plane/app/api/admin_evaluation.py |
| GET | `/admin/evaluation/agent-evaluation/runs` | api_client_only | API Client Only | control_plane/app/api/admin_evaluation.py |
| GET | `/admin/evaluation/agent-evaluation/runs/{run_id}/export` | api_client_only | API Client Only | control_plane/app/api/admin_evaluation.py |
| POST | `/admin/evaluation/arena/match` | no_frontend | None | control_plane/app/api/admin_evaluation.py |
| GET | `/admin/evaluation/rankings` | no_frontend | None | control_plane/app/api/admin_evaluation.py |
| GET | `/admin/evaluation/red-team/findings` | no_frontend | None | control_plane/app/api/admin_evaluation.py |
| POST | `/admin/evaluation/runs` | no_frontend | None | control_plane/app/api/admin_evaluation.py |
| GET | `/admin/evaluation/runs/{run_id}/results` | no_frontend | None | control_plane/app/api/admin_evaluation.py |
| GET | `/admin/executions/{run_id}/manifest` | no_frontend | None | control_plane/app/api/admin_executions.py |
| POST | `/admin/executions/{run_id}/replay/dry-run` | no_frontend | None | control_plane/app/api/admin_executions.py |
| GET | `/admin/executions/{run_id}/steps` | no_frontend | None | control_plane/app/api/admin_executions.py |
| GET | `/admin/export/clients` | no_frontend | None | control_plane/app/api/admin_exports.py |
| GET | `/admin/export/invoices` | no_frontend | None | control_plane/app/api/admin_exports.py |
| GET | `/admin/export/payments` | no_frontend | None | control_plane/app/api/admin_exports.py |
| GET | `/admin/export/request-logs` | no_frontend | None | control_plane/app/api/admin_exports.py |
| GET | `/admin/export/security-events` | no_frontend | None | control_plane/app/api/admin_exports.py |
| GET | `/admin/export/usage` | no_frontend | None | control_plane/app/api/admin_exports.py |
| GET | `/admin/feature-flags` | no_frontend | None | control_plane/app/api/feature_flags_admin.py |
| GET | `/admin/feature-flags/conflicts` | no_frontend | None | control_plane/app/api/feature_flags_admin.py |
| GET | `/admin/feature-flags/deprecated` | no_frontend | None | control_plane/app/api/feature_flags_admin.py |
| POST | `/admin/feature-flags/validate` | no_frontend | None | control_plane/app/api/feature_flags_admin.py |
| GET | `/admin/feature-flags/{name}` | no_frontend | None | control_plane/app/api/feature_flags_admin.py |
| GET | `/admin/financials/margin-dashboard` | no_frontend | None | control_plane/app/api/financial_admin.py |
| GET | `/admin/governance/airgap/packages` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| POST | `/admin/governance/airgap/packages` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| POST | `/admin/governance/airgap/packages/import` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| POST | `/admin/governance/airgap/packages/{package_id}/export` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| POST | `/admin/governance/airgap/packages/{package_id}/reject` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| POST | `/admin/governance/airgap/packages/{package_id}/verify` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| POST | `/admin/governance/deterministic-policies` | no_frontend | None | control_plane/app/api/governance_policy_engine_admin.py |
| GET | `/admin/governance/deterministic-policies` | no_frontend | None | control_plane/app/api/governance_policy_engine_admin.py |
| POST | `/admin/governance/deterministic-policies/bundles` | no_frontend | None | control_plane/app/api/governance_policy_engine_admin.py |
| GET | `/admin/governance/deterministic-policies/conflicts` | no_frontend | None | control_plane/app/api/governance_policy_engine_admin.py |
| POST | `/admin/governance/deterministic-policies/evaluate` | no_frontend | None | control_plane/app/api/governance_policy_engine_admin.py |
| POST | `/admin/governance/deterministic-policies/replay-verify` | no_frontend | None | control_plane/app/api/governance_policy_engine_admin.py |
| GET | `/admin/governance/deterministic-policies/{policy_id}/verify` | no_frontend | None | control_plane/app/api/governance_policy_engine_admin.py |
| GET | `/admin/governance/federation/audit-trail` | api_client_only | API Client Only | control_plane/app/api/commercial_governance_federation_admin.py |
| GET | `/admin/governance/federation/consistency` | api_client_only | API Client Only | control_plane/app/api/commercial_governance_federation_admin.py |
| GET | `/admin/governance/federation/export` | no_frontend | None | control_plane/app/api/commercial_governance_federation_admin.py |
| POST | `/admin/governance/federation/ingest-audit` | no_frontend | None | control_plane/app/api/commercial_governance_federation_admin.py |
| POST | `/admin/governance/federation/ingest-policy` | no_frontend | None | control_plane/app/api/commercial_governance_federation_admin.py |
| GET | `/admin/governance/federation/peers` | api_client_only | API Client Only | control_plane/app/api/commercial_governance_federation_admin.py |
| POST | `/admin/governance/federation/peers` | api_client_only | API Client Only | control_plane/app/api/commercial_governance_federation_admin.py |
| GET | `/admin/governance/federation/status` | api_client_only | API Client Only | control_plane/app/api/commercial_governance_federation_admin.py |
| POST | `/admin/governance/federation/sync` | no_frontend | None | control_plane/app/api/commercial_governance_federation_admin.py |
| GET | `/admin/governance/policies` | no_frontend | None | control_plane/app/api/commercial_policy_governance_admin.py |
| POST | `/admin/governance/policies` | no_frontend | None | control_plane/app/api/commercial_policy_governance_admin.py |
| GET | `/admin/governance/policies/artifacts` | no_frontend | None | control_plane/app/api/commercial_policy_governance_admin.py |
| GET | `/admin/governance/policies/drift` | no_frontend | None | control_plane/app/api/commercial_policy_governance_admin.py |
| POST | `/admin/governance/policies/drift/detect` | no_frontend | None | control_plane/app/api/commercial_policy_governance_admin.py |
| POST | `/admin/governance/policies/{bundle_id}/activate` | no_frontend | None | control_plane/app/api/commercial_policy_governance_admin.py |
| POST | `/admin/governance/policies/{bundle_id}/publish` | no_frontend | None | control_plane/app/api/commercial_policy_governance_admin.py |
| POST | `/admin/governance/policies/{bundle_id}/rollback` | no_frontend | None | control_plane/app/api/commercial_policy_governance_admin.py |
| POST | `/admin/governance/policies/{bundle_id}/simulate` | no_frontend | None | control_plane/app/api/commercial_policy_governance_admin.py |
| GET | `/admin/gpu/allocations` | no_frontend | None | control_plane/app/api/gpu_autoscaling_admin.py |
| GET | `/admin/gpu/capacity/{node_id}` | no_frontend | None | control_plane/app/api/gpu_autoscaling_admin.py |
| GET | `/admin/gpu/devices` | no_frontend | None | control_plane/app/api/gpu_autoscaling_admin.py |
| GET | `/admin/guardrails/blast-radius` | no_frontend | None | control_plane/app/api/commercial_autonomous_guardrails_admin.py |
| GET | `/admin/guardrails/checkpoints` | no_frontend | None | control_plane/app/api/commercial_autonomous_guardrails_admin.py |
| GET | `/admin/guardrails/receipts` | no_frontend | None | control_plane/app/api/commercial_autonomous_guardrails_admin.py |
| GET | `/admin/guardrails/status` | no_frontend | None | control_plane/app/api/commercial_autonomous_guardrails_admin.py |
| GET | `/admin/guardrails/violations` | no_frontend | None | control_plane/app/api/commercial_autonomous_guardrails_admin.py |
| GET | `/admin/harness/evals` | no_frontend | None | control_plane/app/api/harness.py |
| POST | `/admin/harness/evals/runs` | no_frontend | None | control_plane/app/api/harness.py |
| GET | `/admin/harness/evals/runs/{eval_run_id}` | no_frontend | None | control_plane/app/api/harness.py |
| GET | `/admin/harness/evals/runs/{eval_run_id}/events` | no_frontend | None | control_plane/app/api/harness.py |
| GET | `/admin/harness/health` | no_frontend | None | control_plane/app/api/harness.py |
| GET | `/admin/harness/providers` | no_frontend | None | control_plane/app/api/harness.py |
| GET | `/admin/harness/providers/{provider_name}/models` | no_frontend | None | control_plane/app/api/harness.py |
| POST | `/admin/harness/runs` | no_frontend | None | control_plane/app/api/harness.py |
| GET | `/admin/harness/runs` | no_frontend | None | control_plane/app/api/harness.py |
| GET | `/admin/harness/runs/{run_id}` | no_frontend | None | control_plane/app/api/harness.py |
| DELETE | `/admin/harness/runs/{run_id}` | no_frontend | None | control_plane/app/api/harness.py |
| POST | `/admin/harness/runs/{run_id}/cancel` | no_frontend | None | control_plane/app/api/harness.py |
| GET | `/admin/harness/runs/{run_id}/events` | no_frontend | None | control_plane/app/api/harness.py |
| GET | `/admin/harness/tools` | no_frontend | None | control_plane/app/api/harness.py |
| GET | `/admin/health/deep` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/admin/hybrid/cache` | no_frontend | None | control_plane/app/api/hybrid_admin.py |
| GET | `/admin/hybrid/financials` | no_frontend | None | control_plane/app/api/hybrid_admin.py |
| GET | `/admin/hybrid/providers` | no_frontend | None | control_plane/app/api/hybrid_admin.py |
| GET | `/admin/hybrid/rag` | no_frontend | None | control_plane/app/api/hybrid_admin.py |
| GET | `/admin/hybrid/routing` | no_frontend | None | control_plane/app/api/hybrid_admin.py |
| GET | `/admin/hybrid/summary` | no_frontend | None | control_plane/app/api/hybrid_admin.py |
| GET | `/admin/hybrid/wallets` | no_frontend | None | control_plane/app/api/hybrid_admin.py |
| GET | `/admin/inference/agents/executions` | no_frontend | None | control_plane/app/api/commercial_agents_admin.py |
| GET | `/admin/inference/agents/profiles` | no_frontend | None | control_plane/app/api/commercial_agents_admin.py |
| POST | `/admin/inference/agents/profiles` | no_frontend | None | control_plane/app/api/commercial_agents_admin.py |
| GET | `/admin/inference/agents/status` | no_frontend | None | control_plane/app/api/commercial_agents_admin.py |
| GET | `/admin/inference/agents/tool-executions` | no_frontend | None | control_plane/app/api/commercial_agents_admin.py |
| POST | `/admin/inference/agents/tool-executions/{id}/approve` | no_frontend | None | control_plane/app/api/commercial_agents_admin.py |
| GET | `/admin/inference/appliance/audit-packages` | no_frontend | None | control_plane/app/api/commercial_appliance_admin.py |
| POST | `/admin/inference/appliance/audit-packages` | no_frontend | None | control_plane/app/api/commercial_appliance_admin.py |
| GET | `/admin/inference/appliance/bundles` | no_frontend | None | control_plane/app/api/commercial_appliance_admin.py |
| GET | `/admin/inference/appliance/manifests` | no_frontend | None | control_plane/app/api/commercial_appliance_admin.py |
| POST | `/admin/inference/appliance/manifests` | no_frontend | None | control_plane/app/api/commercial_appliance_admin.py |
| GET | `/admin/inference/appliance/status` | no_frontend | None | control_plane/app/api/commercial_appliance_admin.py |
| GET | `/admin/inference/backends` | no_frontend | None | control_plane/app/api/admin_inference.py |
| GET | `/admin/inference/backends/vllm/health` | api_client_only | API Client Only | control_plane/app/api/admin_mlops.py |
| GET | `/admin/inference/backends/vllm/models` | api_client_only | API Client Only | control_plane/app/api/admin_mlops.py |
| POST | `/admin/inference/backends/vllm/test` | api_client_only | API Client Only | control_plane/app/api/admin_mlops.py |
| GET | `/admin/inference/confidential-runtime/audit` | no_frontend | None | control_plane/app/api/commercial_confidential_runtime_admin.py |
| GET | `/admin/inference/confidential-runtime/profiles` | no_frontend | None | control_plane/app/api/commercial_confidential_runtime_admin.py |
| POST | `/admin/inference/confidential-runtime/profiles` | no_frontend | None | control_plane/app/api/commercial_confidential_runtime_admin.py |
| GET | `/admin/inference/confidential-runtime/sessions` | no_frontend | None | control_plane/app/api/commercial_confidential_runtime_admin.py |
| GET | `/admin/inference/confidential-runtime/status` | no_frontend | None | control_plane/app/api/commercial_confidential_runtime_admin.py |
| GET | `/admin/inference/proofs/proofs` | no_frontend | None | control_plane/app/api/commercial_execution_proofs_admin.py |
| POST | `/admin/inference/proofs/proofs/generate/{receipt_id}` | no_frontend | None | control_plane/app/api/commercial_execution_proofs_admin.py |
| GET | `/admin/inference/proofs/proofs/{proof_id}/export` | no_frontend | None | control_plane/app/api/commercial_execution_proofs_admin.py |
| POST | `/admin/inference/proofs/proofs/{proof_id}/verify` | no_frontend | None | control_plane/app/api/commercial_execution_proofs_admin.py |
| GET | `/admin/inference/proofs/timelines` | no_frontend | None | control_plane/app/api/commercial_execution_proofs_admin.py |
| POST | `/admin/inference/proofs/timelines/build` | no_frontend | None | control_plane/app/api/commercial_execution_proofs_admin.py |
| POST | `/admin/inference/proofs/timelines/{timeline_id}/seal` | no_frontend | None | control_plane/app/api/commercial_execution_proofs_admin.py |
| POST | `/admin/inference/proofs/timelines/{timeline_id}/verify` | no_frontend | None | control_plane/app/api/commercial_execution_proofs_admin.py |
| GET | `/admin/inference/receipt-ledger` | no_frontend | None | control_plane/app/api/commercial_cryptographic_receipts_admin.py |
| GET | `/admin/inference/receipt-verification-reports` | no_frontend | None | control_plane/app/api/commercial_cryptographic_receipts_admin.py |
| GET | `/admin/inference/receipts` | no_frontend | None | control_plane/app/api/commercial_cryptographic_receipts_admin.py |
| POST | `/admin/inference/receipts/validate-chain` | no_frontend | None | control_plane/app/api/commercial_cryptographic_receipts_admin.py |
| GET | `/admin/inference/receipts/{receipt_id}` | no_frontend | None | control_plane/app/api/commercial_cryptographic_receipts_admin.py |
| POST | `/admin/inference/receipts/{receipt_id}/export` | no_frontend | None | control_plane/app/api/commercial_cryptographic_receipts_admin.py |
| POST | `/admin/inference/receipts/{receipt_id}/verify` | no_frontend | None | control_plane/app/api/commercial_cryptographic_receipts_admin.py |
| GET | `/admin/inference/replay-events` | no_frontend | None | control_plane/app/api/commercial_inference_reproducibility_admin.py |
| POST | `/admin/inference/replay/{record_id}` | no_frontend | None | control_plane/app/api/commercial_inference_reproducibility_admin.py |
| GET | `/admin/inference/reproducibility` | no_frontend | None | control_plane/app/api/commercial_inference_reproducibility_admin.py |
| GET | `/admin/inference/reproducibility/status` | no_frontend | None | control_plane/app/api/commercial_inference_reproducibility_admin.py |
| GET | `/admin/inference/reproducibility/{record_id}` | no_frontend | None | control_plane/app/api/commercial_inference_reproducibility_admin.py |
| DELETE | `/admin/inference/routing/decisions/cleanup` | no_frontend | None | control_plane/app/api/admin_inference.py |
| GET | `/admin/inference/routing/last-decision` | no_frontend | None | control_plane/app/api/admin_inference.py |
| POST | `/admin/inference/routing/simulate` | no_frontend | None | control_plane/app/api/admin_inference.py |
| GET | `/admin/inference/runtime-snapshots` | no_frontend | None | control_plane/app/api/commercial_inference_reproducibility_admin.py |
| GET | `/admin/inference/timelines/{timeline_id}/witness-quorum` | no_frontend | None | control_plane/app/api/commercial_witness_admin.py |
| POST | `/admin/inference/timelines/{timeline_id}/witness-sign` | no_frontend | None | control_plane/app/api/commercial_witness_admin.py |
| GET | `/admin/inference/transparency/checkpoints` | no_frontend | None | control_plane/app/api/commercial_transparency_admin.py |
| POST | `/admin/inference/transparency/checkpoints` | no_frontend | None | control_plane/app/api/commercial_transparency_admin.py |
| POST | `/admin/inference/transparency/gossip` | no_frontend | None | control_plane/app/api/commercial_transparency_admin.py |
| POST | `/admin/inference/transparency/ingest-checkpoint` | no_frontend | None | control_plane/app/api/commercial_transparency_admin.py |
| GET | `/admin/inference/transparency/peers` | no_frontend | None | control_plane/app/api/commercial_transparency_admin.py |
| POST | `/admin/inference/transparency/peers` | no_frontend | None | control_plane/app/api/commercial_transparency_admin.py |
| GET | `/admin/inference/transparency/split-view-alerts` | no_frontend | None | control_plane/app/api/commercial_transparency_admin.py |
| POST | `/admin/inference/transparency/split-view-alerts/{alert_id}/resolve` | no_frontend | None | control_plane/app/api/commercial_transparency_admin.py |
| GET | `/admin/inference/transparency/status` | no_frontend | None | control_plane/app/api/commercial_transparency_admin.py |
| GET | `/admin/inference/witness-signatures` | no_frontend | None | control_plane/app/api/commercial_witness_admin.py |
| GET | `/admin/inference/witness-status` | no_frontend | None | control_plane/app/api/commercial_witness_admin.py |
| GET | `/admin/inference/witnesses` | no_frontend | None | control_plane/app/api/commercial_witness_admin.py |
| POST | `/admin/inference/witnesses` | no_frontend | None | control_plane/app/api/commercial_witness_admin.py |
| PATCH | `/admin/inference/witnesses/{witness_id}` | no_frontend | None | control_plane/app/api/commercial_witness_admin.py |
| POST | `/admin/inference/witnesses/{witness_id}/verify` | no_frontend | None | control_plane/app/api/commercial_witness_admin.py |
| GET | `/admin/inference/workflows/definitions` | no_frontend | None | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/inference/workflows/definitions` | no_frontend | None | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/inference/workflows/executions` | no_frontend | None | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/inference/workflows/replays` | no_frontend | None | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/inference/workflows/reports` | no_frontend | None | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/inference/workflows/status` | no_frontend | None | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/jobs` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/admin/managed-control-plane/heartbeat` | no_frontend | None | control_plane/app/api/managed_control_plane_admin.py |
| POST | `/admin/managed-control-plane/link` | no_frontend | None | control_plane/app/api/managed_control_plane_admin.py |
| GET | `/admin/mesh/consensus` | no_frontend | None | control_plane/app/api/commercial_mesh_admin.py |
| POST | `/admin/mesh/failover/{failed_node_id}` | no_frontend | None | control_plane/app/api/commercial_mesh_admin.py |
| POST | `/admin/mesh/nodes` | no_frontend | None | control_plane/app/api/commercial_mesh_admin.py |
| GET | `/admin/mesh/nodes` | no_frontend | None | control_plane/app/api/commercial_mesh_admin.py |
| POST | `/admin/mesh/nodes/{node_id}/health` | no_frontend | None | control_plane/app/api/commercial_mesh_admin.py |
| GET | `/admin/mesh/replication` | no_frontend | None | control_plane/app/api/commercial_mesh_admin.py |
| GET | `/admin/metrics/stream` | no_frontend | None | control_plane/app/api/admin_metrics.py |
| POST | `/admin/mlops/datasets` | api_client_only | API Client Only | control_plane/app/api/admin_mlops.py |
| GET | `/admin/mlops/datasets` | api_client_only | API Client Only | control_plane/app/api/admin_mlops.py |
| POST | `/admin/mlops/datasets/{id}/approve` | api_client_only | API Client Only | control_plane/app/api/admin_mlops.py |
| POST | `/admin/mlops/datasets/{id}/versions` | api_client_only | API Client Only | control_plane/app/api/admin_mlops.py |
| GET | `/admin/mlops/experiments` | api_client_only | API Client Only | control_plane/app/api/admin_mlops.py |
| POST | `/admin/mlops/fine-tuning/jobs` | api_client_only | API Client Only | control_plane/app/api/admin_mlops.py |
| GET | `/admin/mlops/fine-tuning/jobs/{id}` | api_client_only | API Client Only | control_plane/app/api/admin_mlops.py |
| GET | `/admin/mlops/model-lineage/{model_id}` | api_client_only | API Client Only | control_plane/app/api/admin_mlops.py |
| GET | `/admin/models` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| POST | `/admin/models` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| POST | `/admin/models/experiments` | api_client_only | API Client Only | control_plane/app/api/admin_model_experiments.py |
| GET | `/admin/models/experiments` | api_client_only | API Client Only | control_plane/app/api/admin_model_experiments.py |
| POST | `/admin/models/experiments/{experiment_id}/promote` | api_client_only | API Client Only | control_plane/app/api/admin_model_experiments.py |
| POST | `/admin/models/experiments/{experiment_id}/rollback` | api_client_only | API Client Only | control_plane/app/api/admin_model_experiments.py |
| GET | `/admin/models/files` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| GET | `/admin/models/lifecycle` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| GET | `/admin/models/lifecycle/dashboard` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| GET | `/admin/models/lifecycle/lineage/entries` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/offline/bundle` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/offline/import` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/offline/verify` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| GET | `/admin/models/lifecycle/promotions` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/promotions` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/promotions/{request_id}/approve` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/promotions/{request_id}/execute` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/promotions/{request_id}/reject` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| GET | `/admin/models/lifecycle/quarantine/events` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| GET | `/admin/models/lifecycle/rollback/history` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| GET | `/admin/models/lifecycle/status` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| GET | `/admin/models/lifecycle/{lifecycle_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/{lifecycle_id}/enforce-gates` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/{lifecycle_id}/lineage` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| GET | `/admin/models/lifecycle/{lifecycle_id}/lineage` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| GET | `/admin/models/lifecycle/{lifecycle_id}/lineage/provenance` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| GET | `/admin/models/lifecycle/{lifecycle_id}/lineage/validate` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/{lifecycle_id}/quarantine` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/{lifecycle_id}/release-quarantine` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/{lifecycle_id}/rollback` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/{lifecycle_id}/stage` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/lifecycle/{lifecycle_id}/transition` | api_client_only | API Client Only | control_plane/app/api/commercial_model_lifecycle_admin.py |
| POST | `/admin/models/reload` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| GET | `/admin/models/runtime` | api_client_only | API Client Only | control_plane/app/api/admin_models_runtime.py |
| POST | `/admin/models/runtime/activate/{instance_id}` | api_client_only | API Client Only | control_plane/app/api/admin_models_runtime.py |
| POST | `/admin/models/runtime/load` | api_client_only | API Client Only | control_plane/app/api/admin_models_runtime.py |
| POST | `/admin/models/runtime/rollback` | api_client_only | API Client Only | control_plane/app/api/admin_models_runtime.py |
| POST | `/admin/models/runtime/unload/{instance_id}` | api_client_only | API Client Only | control_plane/app/api/admin_models_runtime.py |
| GET | `/admin/models/runtime/{instance_id}/health` | api_client_only | API Client Only | control_plane/app/api/admin_models_runtime.py |
| PATCH | `/admin/models/{model_id}` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| DELETE | `/admin/models/{model_id}` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| POST | `/admin/models/{model_id}/disable` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| POST | `/admin/models/{model_id}/enable` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| POST | `/admin/models/{model_id}/routes` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| DELETE | `/admin/models/{model_id}/routes/{backend_id}` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| PATCH | `/admin/models/{model_id}/routes/{backend_id}` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| POST | `/admin/models/{model_id}/set-default` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| POST | `/admin/models/{model_id}/test-prompt` | api_client_only | API Client Only | control_plane/app/api/admin_models.py |
| GET | `/admin/observability/agent-runs/{id}/timeline` | no_frontend | None | control_plane/app/api/observability_admin.py |
| GET | `/admin/observability/anomalies` | no_frontend | None | control_plane/app/api/admin_observability.py |
| POST | `/admin/observability/anomalies/dry-run` | no_frontend | None | control_plane/app/api/admin_observability.py |
| GET | `/admin/observability/dashboard-links` | no_frontend | None | control_plane/app/api/observability_admin.py |
| GET | `/admin/observability/error-budget` | no_frontend | None | control_plane/app/api/observability_admin.py |
| GET | `/admin/observability/metrics` | no_frontend | None | control_plane/app/api/admin_observability.py |
| GET | `/admin/observability/metrics/derived` | no_frontend | None | control_plane/app/api/observability_admin.py |
| GET | `/admin/observability/platform-health` | no_frontend | None | control_plane/app/api/observability_admin.py |
| GET | `/admin/observability/slo` | no_frontend | None | control_plane/app/api/observability_admin.py |
| GET | `/admin/observability/timeline` | no_frontend | None | control_plane/app/api/observability_admin.py |
| GET | `/admin/onboarding/status` | no_frontend | None | control_plane/app/api/admin_onboarding.py |
| POST | `/admin/onboarding/status` | no_frontend | None | control_plane/app/api/admin_onboarding.py |
| POST | `/admin/operations/attestation-bundles` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_attestation_admin.py |
| GET | `/admin/operations/attestation-bundles` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_attestation_admin.py |
| POST | `/admin/operations/attestation-bundles/import` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_attestation_admin.py |
| POST | `/admin/operations/attestation-bundles/{bundle_id}/verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_attestation_admin.py |
| GET | `/admin/operations/attestation-chains/{attestation_id}` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_attestation_admin.py |
| POST | `/admin/operations/attestations` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_attestation_admin.py |
| GET | `/admin/operations/attestations` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_attestation_admin.py |
| GET | `/admin/operations/attestations/{attestation_id}` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_attestation_admin.py |
| POST | `/admin/operations/attestations/{attestation_id}/receipt` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_attestation_admin.py |
| POST | `/admin/operations/attestations/{attestation_id}/revoke` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_attestation_admin.py |
| POST | `/admin/operations/attestations/{attestation_id}/verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_attestation_admin.py |
| POST | `/admin/operations/compatibility/capabilities/negotiate` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_compatibility_admin.py |
| POST | `/admin/operations/compatibility/contracts` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_compatibility_admin.py |
| GET | `/admin/operations/compatibility/contracts` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_compatibility_admin.py |
| GET | `/admin/operations/compatibility/contracts/{contract_id}` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_compatibility_admin.py |
| POST | `/admin/operations/compatibility/contracts/{contract_id}/deprecate` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_compatibility_admin.py |
| POST | `/admin/operations/compatibility/contracts/{contract_id}/receipt` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_compatibility_admin.py |
| POST | `/admin/operations/compatibility/contracts/{contract_id}/verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_compatibility_admin.py |
| GET | `/admin/operations/compatibility/deprecations` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_compatibility_admin.py |
| POST | `/admin/operations/compatibility/matrix` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_compatibility_admin.py |
| POST | `/admin/operations/compatibility/negotiate` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_compatibility_admin.py |
| GET | `/admin/operations/correlations/` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_correlation_admin.py |
| POST | `/admin/operations/correlations/correlation-risk-analysis` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_correlation_admin.py |
| POST | `/admin/operations/correlations/run` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_correlation_admin.py |
| GET | `/admin/operations/correlations/trust-graph` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_correlation_admin.py |
| POST | `/admin/operations/correlations/trust-graph/build` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_correlation_admin.py |
| GET | `/admin/operations/correlations/{correlation_id}` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_correlation_admin.py |
| GET | `/admin/operations/failure-forecasts` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_admin.py |
| POST | `/admin/operations/failure-forecasts/run` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_admin.py |
| POST | `/admin/operations/failure-risk-assessments` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_admin.py |
| GET | `/admin/operations/failure-risk-assessments` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_admin.py |
| POST | `/admin/operations/failure-signals` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_admin.py |
| GET | `/admin/operations/failure-signals` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_admin.py |
| POST | `/admin/operations/federation/bundles/export` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| POST | `/admin/operations/federation/bundles/import` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| POST | `/admin/operations/federation/bundles/{bundle_id}/verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| POST | `/admin/operations/federation/conflicts/resolve` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| POST | `/admin/operations/federation/environments` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| GET | `/admin/operations/federation/environments` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| GET | `/admin/operations/federation/lineage/{bundle_id}` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| POST | `/admin/operations/federation/sessions` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| GET | `/admin/operations/federation/sessions` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| GET | `/admin/operations/federation/sessions/{session_id}` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| POST | `/admin/operations/federation/sessions/{session_id}/receipt` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| POST | `/admin/operations/federation/trust-negotiate` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_federation_sync_admin.py |
| GET | `/admin/operations/incidents` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_ux_admin.py |
| POST | `/admin/operations/models/{model_id}/rollback` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_ux_admin.py |
| POST | `/admin/operations/nodes/{node_id}/drain` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_ux_admin.py |
| GET | `/admin/operations/overview` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_ux_admin.py |
| POST | `/admin/operations/plugin-runtime/contracts` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| GET | `/admin/operations/plugin-runtime/contracts` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| GET | `/admin/operations/plugin-runtime/contracts/{contract_id}` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| POST | `/admin/operations/plugin-runtime/contracts/{contract_id}/activate` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| POST | `/admin/operations/plugin-runtime/contracts/{contract_id}/capabilities` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| POST | `/admin/operations/plugin-runtime/contracts/{contract_id}/compatibility-check` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| POST | `/admin/operations/plugin-runtime/contracts/{contract_id}/execute` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| POST | `/admin/operations/plugin-runtime/contracts/{contract_id}/federation-compatibility` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| POST | `/admin/operations/plugin-runtime/contracts/{contract_id}/lifecycle` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| POST | `/admin/operations/plugin-runtime/contracts/{contract_id}/receipt` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| POST | `/admin/operations/plugin-runtime/contracts/{contract_id}/replay-verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| POST | `/admin/operations/plugin-runtime/load-plans` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| POST | `/admin/operations/plugin-runtime/load-plans/{load_plan_id}/simulate` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| GET | `/admin/operations/plugin-runtime/summary` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_runtime_admin.py |
| GET | `/admin/operations/plugin-supply-chain/dashboard` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| GET | `/admin/operations/plugin-supply-chain/dependency-verifications` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| GET | `/admin/operations/plugin-supply-chain/lineage` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| POST | `/admin/operations/plugin-supply-chain/provenance` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| GET | `/admin/operations/plugin-supply-chain/provenance` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| GET | `/admin/operations/plugin-supply-chain/provenance/{provenance_id}` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| POST | `/admin/operations/plugin-supply-chain/provenance/{provenance_id}/dependency-verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| POST | `/admin/operations/plugin-supply-chain/provenance/{provenance_id}/lineage` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| POST | `/admin/operations/plugin-supply-chain/provenance/{provenance_id}/receipt` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| POST | `/admin/operations/plugin-supply-chain/provenance/{provenance_id}/replay-verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| POST | `/admin/operations/plugin-supply-chain/provenance/{provenance_id}/revoke` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| POST | `/admin/operations/plugin-supply-chain/provenance/{provenance_id}/sbom` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| POST | `/admin/operations/plugin-supply-chain/provenance/{provenance_id}/sign-placeholder` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| POST | `/admin/operations/plugin-supply-chain/provenance/{provenance_id}/verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| GET | `/admin/operations/plugin-supply-chain/receipts` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| GET | `/admin/operations/plugin-supply-chain/sbom` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_plugin_supply_chain_admin.py |
| GET | `/admin/operations/readiness-report` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_ux_admin.py |
| GET | `/admin/operations/recommendations` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_ux_admin.py |
| GET | `/admin/operations/release-summary` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_ux_admin.py |
| GET | `/admin/operations/remediation-plans/` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_remediation_admin.py |
| POST | `/admin/operations/remediation-plans/propose` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_remediation_admin.py |
| GET | `/admin/operations/remediation-plans/{plan_id}` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_remediation_admin.py |
| GET | `/admin/operations/remediation-plans/{plan_id}/approvals` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_remediation_admin.py |
| POST | `/admin/operations/remediation-plans/{plan_id}/receipt` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_remediation_admin.py |
| GET | `/admin/operations/remediation-plans/{plan_id}/steps` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_remediation_admin.py |
| POST | `/admin/operations/reproducible-builds/artifacts/verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_reproducible_builds_admin.py |
| GET | `/admin/operations/reproducible-builds/dashboard` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_reproducible_builds_admin.py |
| POST | `/admin/operations/reproducible-builds/environment/validate` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_reproducible_builds_admin.py |
| POST | `/admin/operations/reproducible-builds/lineage/verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_reproducible_builds_admin.py |
| POST | `/admin/operations/reproducible-builds/manifests` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_reproducible_builds_admin.py |
| GET | `/admin/operations/reproducible-builds/manifests` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_reproducible_builds_admin.py |
| GET | `/admin/operations/reproducible-builds/manifests/{manifest_id}` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_reproducible_builds_admin.py |
| POST | `/admin/operations/reproducible-builds/manifests/{manifest_id}/receipt` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_reproducible_builds_admin.py |
| POST | `/admin/operations/reproducible-builds/manifests/{manifest_id}/verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_reproducible_builds_admin.py |
| POST | `/admin/operations/reproducible-builds/replay/verify` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_reproducible_builds_admin.py |
| POST | `/admin/operations/reset-circuit-breaker` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_ux_admin.py |
| POST | `/admin/operations/run-readiness` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_ux_admin.py |
| GET | `/admin/operations/runtime-nodes` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_ux_admin.py |
| GET | `/admin/operations/security-report` | has_frontend | Inherited from /admin/operations: Core operations center surface. | control_plane/app/api/operations_ux_admin.py |
| POST | `/admin/performance/apply-profile` | no_frontend | None | control_plane/app/api/performance_admin.py |
| POST | `/admin/performance/benchmark` | no_frontend | None | control_plane/app/api/performance_admin.py |
| GET | `/admin/performance/benchmarks` | no_frontend | None | control_plane/app/api/performance_admin.py |
| GET | `/admin/performance/current-profile` | no_frontend | None | control_plane/app/api/performance_admin.py |
| GET | `/admin/performance/profiles` | no_frontend | None | control_plane/app/api/performance_admin.py |
| GET | `/admin/performance/recommendations` | no_frontend | None | control_plane/app/api/performance_admin.py |
| POST | `/admin/performance/seed-profiles` | no_frontend | None | control_plane/app/api/performance_admin.py |
| GET | `/admin/platform/ga-readiness` | no_frontend | None | control_plane/app/api/platform_ga_admin.py |
| GET | `/admin/platform/maturity-report` | no_frontend | None | control_plane/app/api/platform_ga_admin.py |
| POST | `/admin/plugins/install` | no_frontend | None | control_plane/app/api/plugin_marketplace_admin.py |
| GET | `/admin/plugins/installs` | no_frontend | None | control_plane/app/api/plugin_marketplace_admin.py |
| GET | `/admin/plugins/marketplace` | no_frontend | None | control_plane/app/api/plugin_marketplace_admin.py |
| POST | `/admin/plugins/{entry_id}/reviews` | no_frontend | None | control_plane/app/api/plugin_marketplace_admin.py |
| GET | `/admin/plugins/{entry_id}/reviews` | no_frontend | None | control_plane/app/api/plugin_marketplace_admin.py |
| GET | `/admin/plugins/{entry_id}/versions` | no_frontend | None | control_plane/app/api/plugin_marketplace_admin.py |
| DELETE | `/admin/plugins/{install_id}` | no_frontend | None | control_plane/app/api/plugin_marketplace_admin.py |
| POST | `/admin/plugins/{install_id}/disable` | no_frontend | None | control_plane/app/api/plugin_marketplace_admin.py |
| POST | `/admin/plugins/{install_id}/enable` | no_frontend | None | control_plane/app/api/plugin_marketplace_admin.py |
| GET | `/admin/plugins/{install_id}/trust-report` | no_frontend | None | control_plane/app/api/plugin_marketplace_admin.py |
| POST | `/admin/plugins/{install_id}/upgrade` | no_frontend | None | control_plane/app/api/plugin_marketplace_admin.py |
| GET | `/admin/policies/` | no_frontend | None | control_plane/app/api/admin_policies.py |
| POST | `/admin/policies/dry-run` | no_frontend | None | control_plane/app/api/admin_policies.py |
| POST | `/admin/policies/evaluate` | no_frontend | None | control_plane/app/api/admin_policies.py |
| POST | `/admin/policy/runtime/evaluate` | no_frontend | None | control_plane/app/api/commercial_policy_runtime_admin.py |
| POST | `/admin/policy/runtime/simulate` | no_frontend | None | control_plane/app/api/commercial_policy_runtime_admin.py |
| GET | `/admin/policy/runtime/trace/{evaluation_id}` | no_frontend | None | control_plane/app/api/commercial_policy_runtime_admin.py |
| GET | `/admin/policy/runtime/violations` | no_frontend | None | control_plane/app/api/commercial_policy_runtime_admin.py |
| GET | `/admin/providers` | no_frontend | None | control_plane/app/api/providers.py |
| GET | `/admin/providers/capabilities/all` | no_frontend | None | control_plane/app/api/providers.py |
| GET | `/admin/providers/configuration` | no_frontend | None | control_plane/app/api/providers.py |
| PUT | `/admin/providers/configuration` | no_frontend | None | control_plane/app/api/providers.py |
| GET | `/admin/providers/cost-validation/latest` | no_frontend | None | control_plane/app/api/providers.py |
| GET | `/admin/providers/{provider_id}` | no_frontend | None | control_plane/app/api/providers.py |
| GET | `/admin/providers/{provider_id}/health` | no_frontend | None | control_plane/app/api/providers.py |
| GET | `/admin/rag/lineage/{chunk_hash}` | no_frontend | None | control_plane/app/api/commercial_rag_admin.py |
| GET | `/admin/rag/receipts` | no_frontend | None | control_plane/app/api/commercial_rag_admin.py |
| GET | `/admin/rag/usage` | api_client_only | API Client Only | control_plane/app/api/admin_usage.py |
| GET | `/admin/rag/violations` | no_frontend | None | control_plane/app/api/commercial_rag_admin.py |
| GET | `/admin/rbac/audit` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| GET | `/admin/rbac/permissions` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| POST | `/admin/rbac/permissions` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| GET | `/admin/rbac/roles` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| POST | `/admin/rbac/roles` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| PATCH | `/admin/rbac/roles/{role_id}` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| GET | `/admin/rbac/users` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| POST | `/admin/rbac/users` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| PATCH | `/admin/rbac/users/{user_id}` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| DELETE | `/admin/rbac/users/{user_id}` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| POST | `/admin/rbac/users/{user_id}/roles` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| DELETE | `/admin/rbac/users/{user_id}/roles/{role_id}` | api_client_only | API Client Only | control_plane/app/api/admin_rbac.py |
| GET | `/admin/readiness/latest` | no_frontend | None | control_plane/app/api/admin_usage.py |
| GET | `/admin/readiness/{capability}` | no_frontend | None | control_plane/app/api/admin_readiness.py |
| GET | `/admin/receipts/public-key` | no_frontend | None | control_plane/app/api/commercial_cryptographic_receipts_admin.py |
| GET | `/admin/receipts/{id}` | no_frontend | None | control_plane/app/api/commercial_cryptographic_receipts_admin.py |
| POST | `/admin/receipts/{id}/verify` | no_frontend | None | control_plane/app/api/commercial_cryptographic_receipts_admin.py |
| GET | `/admin/reports/monthly` | no_frontend | None | control_plane/app/api/admin_exports.py |
| GET | `/admin/requests` | no_frontend | None | control_plane/app/api/admin.py |
| GET | `/admin/revenue/summary` | api_client_only | API Client Only | control_plane/app/api/admin_usage.py |
| GET | `/admin/routing/analytics/summary` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/calibration/report` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/calibration/simulate` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/capacity/anomalies` | no_frontend | None | control_plane/app/api/commercial_capacity_admin.py |
| POST | `/admin/routing/capacity/capture` | no_frontend | None | control_plane/app/api/commercial_capacity_admin.py |
| GET | `/admin/routing/capacity/export` | no_frontend | None | control_plane/app/api/commercial_capacity_admin.py |
| GET | `/admin/routing/capacity/forecast` | no_frontend | None | control_plane/app/api/commercial_capacity_admin.py |
| GET | `/admin/routing/capacity/overview` | no_frontend | None | control_plane/app/api/commercial_capacity_admin.py |
| POST | `/admin/routing/capacity/rebuild-forecast` | no_frontend | None | control_plane/app/api/commercial_capacity_admin.py |
| GET | `/admin/routing/capacity/recommendations` | no_frontend | None | control_plane/app/api/commercial_capacity_admin.py |
| GET | `/admin/routing/commercial-configs` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial-configs/apply-recommendation` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial-configs/auto-apply-settings` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial-configs/auto-apply/dry-run` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial-configs/auto-apply/run` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/commercial-configs/canaries` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/commercial-configs/canary-promotions` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial-configs/canary/promotions/dry-run` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial-configs/rollback` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial-configs/{config_id}/canary/auto-rollback` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial-configs/{config_id}/canary/promote` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial-configs/{config_id}/canary/promote-step` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial-configs/{config_id}/canary/rollback` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/commercial-configs/{config_id}/canary/slo` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial-configs/{config_id}/deactivate` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/commercial/simulate` | no_frontend | None | control_plane/app/api/routing_admin.py |
| GET | `/admin/routing/distributed/aggregates` | no_frontend | None | control_plane/app/api/commercial_distributed_analytics_admin.py |
| POST | `/admin/routing/distributed/cleanup` | no_frontend | None | control_plane/app/api/commercial_distributed_analytics_admin.py |
| GET | `/admin/routing/distributed/cluster-overview` | no_frontend | None | control_plane/app/api/commercial_distributed_analytics_admin.py |
| GET | `/admin/routing/distributed/export` | no_frontend | None | control_plane/app/api/commercial_distributed_analytics_admin.py |
| POST | `/admin/routing/distributed/ingest` | no_frontend | None | control_plane/app/api/commercial_distributed_analytics_admin.py |
| GET | `/admin/routing/distributed/nodes` | no_frontend | None | control_plane/app/api/commercial_distributed_analytics_admin.py |
| POST | `/admin/routing/distributed/rebuild-aggregates` | no_frontend | None | control_plane/app/api/commercial_distributed_analytics_admin.py |
| GET | `/admin/routing/events` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/executive-dashboard/anomalies` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/executive-dashboard/export` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/executive-dashboard/export/preview` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/executive-dashboard/overview` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/executive-dashboard/recommendations` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/executive-dashboard/report-deliveries` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| GET | `/admin/routing/executive-dashboard/report-schedules` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/executive-dashboard/report-schedules` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/executive-dashboard/report-schedules/{schedule_id}/disable` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/executive-dashboard/report-schedules/{schedule_id}/enable` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/executive-dashboard/report-schedules/{schedule_id}/run-now` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/executive-dashboard/report-schedules/{schedule_id}/send-test-email` | no_frontend | None | control_plane/app/api/commercial_routing_admin.py |
| POST | `/admin/routing/explain` | no_frontend | None | control_plane/app/api/admin_models.py |
| POST | `/admin/routing/federation/cleanup` | no_frontend | None | control_plane/app/api/commercial_federation_admin.py |
| GET | `/admin/routing/federation/clusters` | no_frontend | None | control_plane/app/api/commercial_federation_admin.py |
| POST | `/admin/routing/federation/clusters` | no_frontend | None | control_plane/app/api/commercial_federation_admin.py |
| GET | `/admin/routing/federation/compare` | no_frontend | None | control_plane/app/api/commercial_federation_admin.py |
| GET | `/admin/routing/federation/export` | no_frontend | None | control_plane/app/api/commercial_federation_admin.py |
| POST | `/admin/routing/federation/ingest` | no_frontend | None | control_plane/app/api/commercial_federation_admin.py |
| GET | `/admin/routing/federation/overview` | no_frontend | None | control_plane/app/api/commercial_federation_admin.py |
| POST | `/admin/routing/federation/sync/manual` | no_frontend | None | control_plane/app/api/commercial_federation_admin.py |
| POST | `/admin/routing/ha/acquire` | no_frontend | None | control_plane/app/api/commercial_ha_admin.py |
| GET | `/admin/routing/ha/cluster-state` | no_frontend | None | control_plane/app/api/commercial_ha_admin.py |
| POST | `/admin/routing/ha/force-expire` | no_frontend | None | control_plane/app/api/commercial_ha_admin.py |
| GET | `/admin/routing/ha/leaders` | no_frontend | None | control_plane/app/api/commercial_ha_admin.py |
| POST | `/admin/routing/ha/release` | no_frontend | None | control_plane/app/api/commercial_ha_admin.py |
| GET | `/admin/routing/infra/adapters` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| GET | `/admin/routing/infra/approvals` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| POST | `/admin/routing/infra/approvals` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| GET | `/admin/routing/infra/executions` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| POST | `/admin/routing/infra/executions/{execution_id}/rollback` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| GET | `/admin/routing/infra/executions/{execution_id}/status` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| GET | `/admin/routing/infra/local-gpu/metrics` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| GET | `/admin/routing/infra/proxmox/capacity` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| GET | `/admin/routing/infra/safety-policies` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| POST | `/admin/routing/infra/safety-policies` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| PATCH | `/admin/routing/infra/safety-policies/{policy_id}` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| POST | `/admin/routing/infra/simulate` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| GET | `/admin/routing/infra/simulations` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| POST | `/admin/routing/infra/simulations/{simulation_id}/execute` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| POST | `/admin/routing/infra/validate` | no_frontend | None | control_plane/app/api/commercial_infra_admin.py |
| GET | `/admin/routing/last-decisions` | no_frontend | None | control_plane/app/api/routing_admin.py |
| GET | `/admin/routing/policies` | no_frontend | None | control_plane/app/api/routing_admin.py |
| POST | `/admin/routing/qos/chargeback/calculate` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| GET | `/admin/routing/qos/chargeback/export` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| GET | `/admin/routing/qos/chargeback/overview` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| POST | `/admin/routing/qos/fairness/collect` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| GET | `/admin/routing/qos/fairness/inversions` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| GET | `/admin/routing/qos/fairness/overview` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| GET | `/admin/routing/qos/fairness/starvation` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| GET | `/admin/routing/qos/overview` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| GET | `/admin/routing/qos/queue/jobs` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| GET | `/admin/routing/qos/queue/overview` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| GET | `/admin/routing/qos/rate-limits/overview` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| POST | `/admin/routing/qos/rate-limits/simulate` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| POST | `/admin/routing/qos/simulate` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| GET | `/admin/routing/qos/tiers` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| POST | `/admin/routing/qos/tiers` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| PATCH | `/admin/routing/qos/tiers/{tier_id}` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| DELETE | `/admin/routing/qos/tiers/{tier_id}` | no_frontend | None | control_plane/app/api/commercial_qos_admin.py |
| POST | `/admin/routing/simulate` | no_frontend | None | control_plane/app/api/routing_admin.py |
| GET | `/admin/routing/test/force-local-failure` | no_frontend | None | control_plane/app/api/routing_test.py |
| POST | `/admin/routing/test/force-local-failure` | no_frontend | None | control_plane/app/api/routing_test.py |
| GET | `/admin/runtime-profiles` | no_frontend | None | control_plane/app/api/runtime_profiles_admin.py |
| POST | `/admin/runtime-profiles/apply` | no_frontend | None | control_plane/app/api/runtime_profiles_admin.py |
| GET | `/admin/runtime-profiles/current` | no_frontend | None | control_plane/app/api/runtime_profiles_admin.py |
| POST | `/admin/runtime-profiles/validate` | no_frontend | None | control_plane/app/api/runtime_profiles_admin.py |
| GET | `/admin/runtime/drift` | no_frontend | None | control_plane/app/api/commercial_runtime_fabric_admin.py |
| POST | `/admin/runtime/drift/report` | no_frontend | None | control_plane/app/api/commercial_runtime_fabric_admin.py |
| GET | `/admin/runtime/fabric` | no_frontend | None | control_plane/app/api/commercial_runtime_fabric_admin.py |
| POST | `/admin/runtime/fabric/heartbeat` | no_frontend | None | control_plane/app/api/commercial_runtime_fabric_admin.py |
| GET | `/admin/runtime/healing` | no_frontend | None | control_plane/app/api/commercial_runtime_fabric_admin.py |
| POST | `/admin/runtime/recovery` | no_frontend | None | control_plane/app/api/commercial_runtime_fabric_admin.py |
| POST | `/admin/runtime/recovery/{plan_id}/execute` | no_frontend | None | control_plane/app/api/commercial_runtime_fabric_admin.py |
| POST | `/admin/runtime/replay-repair/{drift_id}` | no_frontend | None | control_plane/app/api/commercial_runtime_fabric_admin.py |
| GET | `/admin/runtime/summary` | no_frontend | None | control_plane/app/api/admin_usage.py |
| GET | `/admin/saas/overview` | no_frontend | None | control_plane/app/api/saas_admin.py |
| GET | `/admin/sales/leads` | no_frontend | None | control_plane/app/api/sales.py |
| POST | `/admin/sales/leads` | no_frontend | None | control_plane/app/api/sales.py |
| GET | `/admin/sales/leads/{id}` | no_frontend | None | control_plane/app/api/sales.py |
| PATCH | `/admin/sales/leads/{id}` | no_frontend | None | control_plane/app/api/sales.py |
| DELETE | `/admin/sales/leads/{id}` | no_frontend | None | control_plane/app/api/sales.py |
| POST | `/admin/sales/leads/{id}/advance-stage` | no_frontend | None | control_plane/app/api/sales.py |
| POST | `/admin/sales/leads/{id}/notes` | no_frontend | None | control_plane/app/api/sales.py |
| GET | `/admin/sales/monthly-report-preview` | no_frontend | None | control_plane/app/api/sales.py |
| POST | `/admin/sales/quote-preview` | no_frontend | None | control_plane/app/api/sales.py |
| POST | `/admin/sandbox/dry-run` | no_frontend | None | control_plane/app/api/admin_sandbox.py |
| GET | `/admin/sandbox/explain/{tool_name}` | no_frontend | None | control_plane/app/api/admin_sandbox.py |
| GET | `/admin/sandbox/providers` | no_frontend | None | control_plane/app/api/admin_sandbox.py |
| POST | `/admin/security/abuse/actions/{action_id}/ack` | api_client_only | API Client Only | control_plane/app/api/abuse_admin.py |
| POST | `/admin/security/abuse/clients/{client_id}/suspend` | api_client_only | API Client Only | control_plane/app/api/abuse_admin.py |
| POST | `/admin/security/abuse/clients/{client_id}/unsuspend` | api_client_only | API Client Only | control_plane/app/api/abuse_admin.py |
| GET | `/admin/security/abuse/events` | api_client_only | API Client Only | control_plane/app/api/abuse_admin.py |
| GET | `/admin/security/abuse/summary` | api_client_only | API Client Only | control_plane/app/api/abuse_admin.py |
| GET | `/admin/security/attestation/report` | no_frontend | None | control_plane/app/api/pki_attestation_admin.py |
| POST | `/admin/security/attestation/verify` | no_frontend | None | control_plane/app/api/pki_attestation_admin.py |
| POST | `/admin/security/clients/{client_id}/suspend` | no_frontend | None | control_plane/app/api/admin_clients.py |
| POST | `/admin/security/clients/{client_id}/unsuspend` | no_frontend | None | control_plane/app/api/admin_clients.py |
| GET | `/admin/security/encryption/audit` | no_frontend | None | control_plane/app/api/commercial_encryption_admin.py |
| POST | `/admin/security/encryption/classification` | no_frontend | None | control_plane/app/api/commercial_encryption_admin.py |
| POST | `/admin/security/encryption/decrypt` | no_frontend | None | control_plane/app/api/commercial_encryption_admin.py |
| POST | `/admin/security/encryption/encrypt` | no_frontend | None | control_plane/app/api/commercial_encryption_admin.py |
| GET | `/admin/security/encryption/keys` | no_frontend | None | control_plane/app/api/commercial_encryption_admin.py |
| POST | `/admin/security/encryption/keys` | no_frontend | None | control_plane/app/api/commercial_encryption_admin.py |
| POST | `/admin/security/encryption/keys/{key_id}/revoke` | no_frontend | None | control_plane/app/api/commercial_encryption_admin.py |
| POST | `/admin/security/encryption/keys/{key_id}/rotate` | no_frontend | None | control_plane/app/api/commercial_encryption_admin.py |
| GET | `/admin/security/events` | api_client_only | API Client Only | control_plane/app/api/admin.py |
| GET | `/admin/security/hardware-attestation` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| POST | `/admin/security/hardware-attestation/collect` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| POST | `/admin/security/hardware-attestation/verify` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| GET | `/admin/security/latest` | no_frontend | None | control_plane/app/api/admin_usage.py |
| GET | `/admin/security/offline-crl` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| POST | `/admin/security/offline-crl` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| POST | `/admin/security/offline-crl/{crl_id}/apply` | api_client_only | API Client Only | control_plane/app/api/commercial_sovereign_governance_admin.py |
| POST | `/admin/security/pki/init` | no_frontend | None | control_plane/app/api/pki_attestation_admin.py |
| GET | `/admin/status` | no_frontend | None | control_plane/app/api/system.py |
| POST | `/admin/support/bundle` | no_frontend | None | control_plane/app/api/support_admin.py |
| GET | `/admin/support/bundle/latest` | no_frontend | None | control_plane/app/api/support_admin.py |
| GET | `/admin/support/surface` | no_frontend | None | control_plane/app/api/supported_surface_admin.py |
| GET | `/admin/support/surface/status/{status}` | no_frontend | None | control_plane/app/api/supported_surface_admin.py |
| GET | `/admin/support/surface/{id}` | no_frontend | None | control_plane/app/api/supported_surface_admin.py |
| GET | `/admin/system/api-surface` | no_frontend | None | control_plane/app/api/admin.py |
| GET | `/admin/system/backups/latest` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/admin/system/benchmarks/latest` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/admin/system/control-center` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/admin/system/releases/latest` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/admin/system/reports/latest` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/admin/tenants/{tenant_id}/agentic-readiness` | no_frontend | None | control_plane/app/api/tenant_agentic_readiness_admin.py |
| POST | `/admin/test/clients/{client_id}/reset-usage` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/test/commands` | no_frontend | None | control_plane/app/api/admin_tests.py |
| POST | `/admin/test/run` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/tests/audit` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/tests/auth/whoami` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/tests/plans` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/tests/pytest/files` | no_frontend | None | control_plane/app/api/admin_tests.py |
| POST | `/admin/tests/pytest/run` | no_frontend | None | control_plane/app/api/admin_tests.py |
| POST | `/admin/tests/pytest/run/{run_id}/cancel` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/tests/pytest/run/{run_id}/status` | no_frontend | None | control_plane/app/api/admin_tests.py |
| POST | `/admin/tests/rag/clients/{client_id}/block` | no_frontend | None | control_plane/app/api/admin_tests.py |
| POST | `/admin/tests/rag/clients/{client_id}/unblock` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/tests/rag/clients/{client_id}/usage` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/tests/rag/status` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/tests/system/resources` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/tests/tokens/lookup` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/tests/users/{user_id}` | no_frontend | None | control_plane/app/api/admin_tests.py |
| POST | `/admin/tests/users/{user_id}/block` | no_frontend | None | control_plane/app/api/admin_tests.py |
| POST | `/admin/tests/users/{user_id}/plan` | no_frontend | None | control_plane/app/api/admin_tests.py |
| DELETE | `/admin/tests/users/{user_id}/quota/override` | no_frontend | None | control_plane/app/api/admin_tests.py |
| POST | `/admin/tests/users/{user_id}/quota/renew` | no_frontend | None | control_plane/app/api/admin_tests.py |
| POST | `/admin/tests/users/{user_id}/quota/reset` | no_frontend | None | control_plane/app/api/admin_tests.py |
| POST | `/admin/tests/users/{user_id}/quota/set` | no_frontend | None | control_plane/app/api/admin_tests.py |
| POST | `/admin/tests/users/{user_id}/unblock` | no_frontend | None | control_plane/app/api/admin_tests.py |
| GET | `/admin/usage` | no_frontend | None | control_plane/app/api/admin_usage.py |
| GET | `/admin/usage/by-client` | no_frontend | None | control_plane/app/api/admin_usage.py |
| GET | `/admin/usage/by-model` | no_frontend | None | control_plane/app/api/admin_usage.py |
| GET | `/admin/usage/summary` | api_client_only | API Client Only | control_plane/app/api/admin_usage.py |
| GET | `/admin/usage/{client_id}/summary` | no_frontend | None | control_plane/app/api/admin_usage.py |
| GET | `/admin/vectorstores/health` | api_client_only | API Client Only | control_plane/app/api/admin_vectorstores.py |
| GET | `/admin/vectorstores/provider` | api_client_only | API Client Only | control_plane/app/api/admin_vectorstores.py |
| POST | `/admin/vectorstores/test` | api_client_only | API Client Only | control_plane/app/api/admin_vectorstores.py |
| GET | `/admin/workflows/approvals` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/approvals/executions/{execution_id}/stages/{stage_key}/request` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/approvals/{chain_id}/decide` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/definitions` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/definitions` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/executions` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/executions` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/executions/{execution_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/executions/{execution_id}/checkpoints` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/executions/{execution_id}/pause` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/executions/{execution_id}/provenance` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/executions/{execution_id}/resume` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/executions/{execution_id}/rollback` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/executions/{execution_id}/stages/{stage_key}` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/federation/consensus` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_federated_workflows_admin.py |
| POST | `/admin/workflows/federation/consensus/{federated_execution_id}` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_federated_workflows_admin.py |
| GET | `/admin/workflows/federation/drift` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_federated_workflows_admin.py |
| GET | `/admin/workflows/federation/executions` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_federated_workflows_admin.py |
| POST | `/admin/workflows/federation/executions` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_federated_workflows_admin.py |
| POST | `/admin/workflows/federation/executions/{federated_execution_id}/lease` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_federated_workflows_admin.py |
| GET | `/admin/workflows/federation/overview` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_federated_workflows_admin.py |
| GET | `/admin/workflows/federation/peers` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_federated_workflows_admin.py |
| POST | `/admin/workflows/federation/reconcile/{federated_execution_id}` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_federated_workflows_admin.py |
| GET | `/admin/workflows/federation/replay` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_federated_workflows_admin.py |
| POST | `/admin/workflows/federation/replay/{federated_execution_id}` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_federated_workflows_admin.py |
| GET | `/admin/workflows/governance/executions/{execution_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/governance/executions/{execution_id}/ledger` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/governance/executions/{execution_id}/snapshots` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/governance/executions/{execution_id}/stages/{stage_key}/rollback-policy` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/receipts` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/receipts/{execution_id}` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/receipts/{receipt_id}/export` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/receipts/{receipt_id}/verify` | no_frontend | Inherited from /admin/workflows: Commercial Workflows engine is API-first. | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/replay-sessions` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/replay-sessions` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/replay-sessions/{session_id}/complete` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/replay/{execution_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/replay/{replay_id}/attach/{replay_execution_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/admin/workflows/replay/{replay_id}/verify` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/replays` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/reports` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| GET | `/admin/workflows/status` | api_client_only | API Client Only | control_plane/app/api/commercial_workflows_admin.py |
| POST | `/agents/a2a/delegate` | has_frontend | Route Only | control_plane/app/api/agent_a2a.py |
| POST | `/agents/a2a/message` | has_frontend | Route Only | control_plane/app/api/agent_a2a.py |
| POST | `/agents/events/webhooks/{trigger_id}` | has_frontend | Route Only | control_plane/app/api/agent_events.py |
| GET | `/agents/runs` | has_frontend | Route + API | control_plane/app/api/agents.py |
| GET | `/agents/runs/{run_id}` | has_frontend | Route + API | control_plane/app/api/agents.py |
| POST | `/agents/runs/{run_id}/cancel` | has_frontend | Route + API | control_plane/app/api/agents.py |
| POST | `/agents/runs/{run_id}/pause` | has_frontend | Route + API | control_plane/app/api/agents.py |
| POST | `/agents/runs/{run_id}/replay` | has_frontend | Route + API | control_plane/app/api/agents.py |
| POST | `/agents/runs/{run_id}/resume` | has_frontend | Route + API | control_plane/app/api/agents.py |
| GET | `/agents/runs/{run_id}/steps` | has_frontend | Route + API | control_plane/app/api/agents.py |
| POST | `/agents/{agent_id}/runs` | has_frontend | Route Only | control_plane/app/api/agents.py |
| GET | `/allowlist` | no_frontend | None | control_plane/app/api/operations_adapter_registry_admin.py |
| GET | `/api-keys` | has_frontend | Route Only | control_plane/app/api/portal.py |
| POST | `/api-keys` | has_frontend | Route Only | control_plane/app/api/portal.py |
| DELETE | `/api-keys/{api_key_id}` | has_frontend | Route Only | control_plane/app/api/portal.py |
| GET | `/api/admin/compliance/evidence` | no_frontend | None | control_plane/app/api/admin_compliance_evidence.py |
| POST | `/api/admin/compliance/evidence/collect` | no_frontend | None | control_plane/app/api/admin_compliance_evidence.py |
| GET | `/api/admin/compliance/evidence/export` | no_frontend | None | control_plane/app/api/admin_compliance_evidence.py |
| GET | `/api/admin/costs/by-agent` | api_client_only | API Client Only | control_plane/app/api/admin_costs.py |
| GET | `/api/admin/costs/by-tenant` | api_client_only | API Client Only | control_plane/app/api/admin_costs.py |
| GET | `/api/admin/costs/by-tool` | api_client_only | API Client Only | control_plane/app/api/admin_costs.py |
| GET | `/api/admin/costs/export` | api_client_only | API Client Only | control_plane/app/api/admin_costs.py |
| GET | `/api/admin/costs/summary` | api_client_only | API Client Only | control_plane/app/api/admin_costs.py |
| GET | `/api/admin/federation/peers` | has_frontend | Inherited from /api/admin/federation: Covered by Federation Overview. | control_plane/app/api/admin_federation_mesh.py |
| POST | `/api/admin/federation/sync/dry-run` | has_frontend | Inherited from /api/admin/federation: Covered by Federation Overview. | control_plane/app/api/admin_federation_mesh.py |
| POST | `/api/admin/federation/sync/export` | has_frontend | Inherited from /api/admin/federation: Covered by Federation Overview. | control_plane/app/api/admin_federation_mesh.py |
| POST | `/api/admin/federation/sync/import` | has_frontend | Inherited from /api/admin/federation: Covered by Federation Overview. | control_plane/app/api/admin_federation_mesh.py |
| GET | `/api/admin/marketplace/agents` | has_frontend | Inherited from /api/admin/marketplace: Internal marketplace sync logic. | control_plane/app/api/admin_marketplace.py |
| POST | `/api/admin/marketplace/install/approve` | has_frontend | Inherited from /api/admin/marketplace: Internal marketplace sync logic. | control_plane/app/api/admin_marketplace.py |
| POST | `/api/admin/marketplace/install/dry-run` | has_frontend | Inherited from /api/admin/marketplace: Internal marketplace sync logic. | control_plane/app/api/admin_marketplace.py |
| POST | `/api/admin/marketplace/validate` | has_frontend | Inherited from /api/admin/marketplace: Internal marketplace sync logic. | control_plane/app/api/admin_marketplace.py |
| GET | `/api/admin/models/provenance` | api_client_only | Exempted: Provenance verification helpers. | control_plane/app/api/admin_model_provenance.py |
| POST | `/api/admin/models/provenance/verify/{record_id}` | api_client_only | Inherited from /api/admin/models/provenance: Provenance verification helpers. | control_plane/app/api/admin_model_provenance.py |
| POST | `/api/admin/models/watermark/verify` | no_frontend | None | control_plane/app/api/admin_model_provenance.py |
| GET | `/api/admin/performance/backends` | api_client_only | API Client Only | control_plane/app/api/admin_performance.py |
| GET | `/api/admin/performance/capabilities` | api_client_only | API Client Only | control_plane/app/api/admin_performance.py |
| GET | `/api/admin/performance/recommendations` | api_client_only | API Client Only | control_plane/app/api/admin_performance.py |
| POST | `/api/admin/performance/simulate` | api_client_only | API Client Only | control_plane/app/api/admin_performance.py |
| GET | `/api/audit/export` | api_client_only | Inherited from /api/audit: Headless audit verification. | control_plane/app/api/audit.py |
| POST | `/api/audit/verify` | api_client_only | Inherited from /api/audit: Headless audit verification. | control_plane/app/api/audit.py |
| GET | `/api/backends/capabilities` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/api/multimodal/capabilities` | api_client_only | Inherited from /api/multimodal: Multimodal processing primitives. | control_plane/app/api/multimodal_v2.py |
| POST | `/api/multimodal/video/analyze` | api_client_only | Inherited from /api/multimodal: Multimodal processing primitives. | control_plane/app/api/multimodal_v2.py |
| POST | `/api/multimodal/vision/analyze` | api_client_only | Inherited from /api/multimodal: Multimodal processing primitives. | control_plane/app/api/multimodal_v2.py |
| GET | `/api/system/profile` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/api/v1/a2a/discover/{agent_id}` | intentionally_hidden | Inherited from /api/v1/a2a: Internal P2P routing. | control_plane/app/api/a2a_router.py |
| POST | `/api/v1/a2a/jsonrpc` | intentionally_hidden | Exempted: Agent-to-Agent internal RPC. | control_plane/app/api/a2a_router.py |
| POST | `/api/v1/a2a/register-server` | intentionally_hidden | Inherited from /api/v1/a2a: Internal P2P routing. | control_plane/app/api/a2a_router.py |
| POST | `/api/v1/a2a/send` | intentionally_hidden | Inherited from /api/v1/a2a: Internal P2P routing. | control_plane/app/api/a2a_router.py |
| GET | `/api/v1/admin/agents/analytics/dashboard` | no_frontend | None | control_plane/app/api/agent_analytics_admin.py |
| GET | `/api/v1/admin/agents/analytics/overview` | api_client_only | API Client Only | control_plane/app/api/agent_analytics_admin.py |
| GET | `/api/v1/admin/agents/analytics/{agent_id}` | api_client_only | API Client Only | control_plane/app/api/agent_analytics_admin.py |
| GET | `/api/v1/admin/agents/analytics/{agent_id}/costs` | api_client_only | API Client Only | control_plane/app/api/agent_analytics_admin.py |
| GET | `/api/v1/admin/agents/analytics/{agent_id}/latency` | api_client_only | API Client Only | control_plane/app/api/agent_analytics_admin.py |
| GET | `/api/v1/admin/agents/analytics/{agent_id}/tools` | api_client_only | API Client Only | control_plane/app/api/agent_analytics_admin.py |
| POST | `/api/v1/admin/debugger/breakpoints/{run_id}` | intentionally_hidden | Inherited from /api/v1/admin/debugger: Remote debugger backend. | control_plane/app/api/agent_debugger_admin.py |
| POST | `/api/v1/admin/debugger/sessions/{run_id}/pause` | intentionally_hidden | Inherited from /api/v1/admin/debugger: Remote debugger backend. | control_plane/app/api/agent_debugger_admin.py |
| POST | `/api/v1/admin/debugger/sessions/{run_id}/resume` | intentionally_hidden | Inherited from /api/v1/admin/debugger: Remote debugger backend. | control_plane/app/api/agent_debugger_admin.py |
| GET | `/api/v1/admin/debugger/sessions/{run_id}/state` | intentionally_hidden | Inherited from /api/v1/admin/debugger: Remote debugger backend. | control_plane/app/api/agent_debugger_admin.py |
| POST | `/api/v1/admin/kb/` | has_frontend | Exempted: Covered by RAG / Knowledge Graph pages. | control_plane/app/api/kb_admin.py |
| POST | `/api/v1/admin/kb/{kb_id}/documents` | has_frontend | Inherited from /api/v1/admin/kb: Covered by RAG / Knowledge Graph pages. | control_plane/app/api/kb_admin.py |
| GET | `/api/v1/admin/kb/{kb_id}/documents` | has_frontend | Inherited from /api/v1/admin/kb: Covered by RAG / Knowledge Graph pages. | control_plane/app/api/kb_admin.py |
| POST | `/api/v1/admin/kb/{kb_id}/ingest-url` | has_frontend | Inherited from /api/v1/admin/kb: Covered by RAG / Knowledge Graph pages. | control_plane/app/api/kb_admin.py |
| POST | `/api/v1/admin/kb/{kb_id}/reindex` | has_frontend | Inherited from /api/v1/admin/kb: Covered by RAG / Knowledge Graph pages. | control_plane/app/api/kb_admin.py |
| POST | `/api/v1/admin/prompts/` | has_frontend | Exempted: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| GET | `/api/v1/admin/prompts/` | has_frontend | Exempted: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/templates` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| GET | `/api/v1/admin/prompts/templates` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/templates/{template_id}/playground` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/templates/{template_id}/render` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| GET | `/api/v1/admin/prompts/templates/{template_id}/render-events` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/templates/{template_id}/rollback` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/templates/{template_id}/variables` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/templates/{template_id}/versions` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/templates/{template_id}/versions/{version_id}/promote` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/validate` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/{template_id}/experiments` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/{template_id}/playground` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/{template_id}/versions` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| POST | `/api/v1/admin/prompts/{template_id}/versions/{version_id}/promote` | has_frontend | Inherited from /api/v1/admin/prompts: Covered by Prompts page. | control_plane/app/api/prompt_admin.py |
| GET | `/api/v1/agent-service/runs/{run_id}` | api_client_only | Inherited from /api/v1/agent-service: Headless invocation endpoints. | control_plane/app/api/agent_service.py |
| POST | `/api/v1/agent-service/{agent_id}/callbacks` | api_client_only | Inherited from /api/v1/agent-service: Headless invocation endpoints. | control_plane/app/api/agent_service.py |
| POST | `/api/v1/agent-service/{agent_id}/invoke` | api_client_only | Inherited from /api/v1/agent-service: Headless invocation endpoints. | control_plane/app/api/agent_service.py |
| POST | `/api/v1/agent-service/{agent_id}/invoke-sync` | api_client_only | Inherited from /api/v1/agent-service: Headless invocation endpoints. | control_plane/app/api/agent_service.py |
| POST | `/api/v1/alerts/grafana-webhook` | intentionally_hidden | Exempted: Inbound webhook from Grafana. | control_plane/app/api/alert_webhooks.py |
| POST | `/api/v1/alerts/resolve` | api_client_only | Inherited from /api/v1/alerts: Alert remediation and webhook handlers. | control_plane/app/api/alert_webhooks.py |
| POST | `/api/v1/alerts/test-pagerduty` | api_client_only | Inherited from /api/v1/alerts: Alert remediation and webhook handlers. | control_plane/app/api/alert_webhooks.py |
| GET | `/attestation/status` | no_frontend | None | control_plane/app/api/commercial_attestation_public.py |
| POST | `/attestation/verify/lineage-consistency` | no_frontend | None | control_plane/app/api/commercial_attestation_public.py |
| POST | `/attestation/verify/receipt` | no_frontend | None | control_plane/app/api/commercial_attestation_public.py |
| POST | `/attestation/verify/retrieval-proof` | no_frontend | None | control_plane/app/api/commercial_attestation_public.py |
| POST | `/attestation/verify/retrieval-replay` | no_frontend | None | control_plane/app/api/commercial_attestation_public.py |
| POST | `/attestation/verify/timeline` | no_frontend | None | control_plane/app/api/commercial_attestation_public.py |
| POST | `/attestation/verify/witness-quorum` | no_frontend | None | control_plane/app/api/commercial_attestation_public.py |
| GET | `/audit/access-logs` | has_frontend | Inherited from /audit: Legacy audit path. | control_plane/app/api/portal.py |
| GET | `/audit/approval-chains` | has_frontend | Inherited from /audit: Legacy audit path. | control_plane/app/api/portal.py |
| GET | `/audit/attestations` | has_frontend | Inherited from /audit: Legacy audit path. | control_plane/app/api/portal.py |
| GET | `/audit/evidence-packages` | has_frontend | Inherited from /audit: Legacy audit path. | control_plane/app/api/portal.py |
| GET | `/audit/exceptions` | has_frontend | Inherited from /audit: Legacy audit path. | control_plane/app/api/portal.py |
| GET | `/audit/operational-controls` | has_frontend | Inherited from /audit: Legacy audit path. | control_plane/app/api/portal.py |
| GET | `/audit/operational-evidence` | has_frontend | Inherited from /audit: Legacy audit path. | control_plane/app/api/portal.py |
| GET | `/audit/operational-reviews` | has_frontend | Inherited from /audit: Legacy audit path. | control_plane/app/api/portal.py |
| GET | `/audit/reports` | has_frontend | Inherited from /audit: Legacy audit path. | control_plane/app/api/portal.py |
| POST | `/audit/reports/generate` | has_frontend | Inherited from /audit: Legacy audit path. | control_plane/app/api/portal.py |
| GET | `/audit/reports/{report_id}/download` | has_frontend | Inherited from /audit: Legacy audit path. | control_plane/app/api/portal.py |
| POST | `/auth/callback/{provider}` | intentionally_hidden | Exempted: OAuth callback handler. | control_plane/app/api/auth.py |
| GET | `/auth/enterprise/callback/{provider}` | intentionally_hidden | Exempted: SSO callback. | control_plane/app/api/enterprise_sso.py |
| GET | `/auth/enterprise/login/{provider}` | api_client_only | Exempted: SSO redirect. | control_plane/app/api/enterprise_sso.py |
| GET | `/auth/login/{provider}` | api_client_only | Exempted: Redirect-based OAuth login. | control_plane/app/api/auth.py |
| GET | `/auth/me` | no_frontend | None | control_plane/app/api/auth.py |
| POST | `/billing/disputes` | has_frontend | Route Only | control_plane/app/api/portal.py |
| GET | `/billing/disputes` | has_frontend | Route Only | control_plane/app/api/portal.py |
| POST | `/billing/payments/card` | has_frontend | Route Only | control_plane/app/api/billing_payments.py |
| POST | `/billing/payments/pix` | has_frontend | Route Only | control_plane/app/api/billing_payments.py |
| POST | `/billing/webhooks/stripe` | intentionally_hidden | Exempted: Inbound webhook from payment providers. | control_plane/app/api/billing_payments.py |
| POST | `/billing/webhooks/{provider}` | intentionally_hidden | Exempted: Inbound webhook from payment providers. | control_plane/app/api/billing_payments.py |
| GET | `/blocklist` | no_frontend | None | control_plane/app/api/operations_adapter_registry_admin.py |
| GET | `/capabilities` | no_frontend | None | control_plane/app/api/public.py |
| GET | `/circuit-breakers` | no_frontend | None | control_plane/app/api/commercial_cross_cluster_forwarding_admin.py |
| GET | `/client-portal` | intentionally_hidden | Exempted: Static files for the client portal. | control_plane/app/api/system.py |
| GET | `/client-portal/{rest:path}` | intentionally_hidden | Exempted: Static files for the client portal. | control_plane/app/api/system.py |
| GET | `/decisions` | no_frontend | None | control_plane/app/api/commercial_global_traffic_admin.py |
| GET | `/developer-docs` | no_frontend | None | control_plane/app/api/developer_docs.py |
| GET | `/docs` | intentionally_hidden | Exempted: Public API documentation. | control_plane/app/api/public.py |
| POST | `/entries` | has_frontend | Exempted: Generic entries path for adapters. | control_plane/app/api/operations_adapter_registry_admin.py |
| GET | `/entries` | has_frontend | Exempted: Generic entries path for adapters. | control_plane/app/api/operations_adapter_registry_admin.py |
| GET | `/entries/{entry_id}` | has_frontend | Inherited from /entries: Generic entries path for adapters. | control_plane/app/api/operations_adapter_registry_admin.py |
| POST | `/entries/{entry_id}/approve` | has_frontend | Inherited from /entries: Generic entries path for adapters. | control_plane/app/api/operations_adapter_registry_admin.py |
| POST | `/entries/{entry_id}/block` | has_frontend | Inherited from /entries: Generic entries path for adapters. | control_plane/app/api/operations_adapter_registry_admin.py |
| POST | `/entries/{entry_id}/deprecate` | has_frontend | Inherited from /entries: Generic entries path for adapters. | control_plane/app/api/operations_adapter_registry_admin.py |
| POST | `/entries/{entry_id}/receipt` | has_frontend | Inherited from /entries: Generic entries path for adapters. | control_plane/app/api/operations_adapter_registry_admin.py |
| POST | `/entries/{entry_id}/reject` | has_frontend | Inherited from /entries: Generic entries path for adapters. | control_plane/app/api/operations_adapter_registry_admin.py |
| POST | `/entries/{entry_id}/revoke` | has_frontend | Inherited from /entries: Generic entries path for adapters. | control_plane/app/api/operations_adapter_registry_admin.py |
| POST | `/entries/{entry_id}/submit` | has_frontend | Inherited from /entries: Generic entries path for adapters. | control_plane/app/api/operations_adapter_registry_admin.py |
| GET | `/examples` | no_frontend | None | control_plane/app/api/portal.py |
| POST | `/execute` | no_frontend | None | control_plane/app/api/operations_remediation_execution_admin.py |
| GET | `/explainability/{decision_id}` | no_frontend | None | control_plane/app/api/commercial_governance_supervisor_admin.py |
| GET | `/export` | no_frontend | None | control_plane/app/api/commercial_qos_billing_admin.py |
| GET | `/federation-map` | no_frontend | None | control_plane/app/api/commercial_operations_center.py |
| POST | `/generate` | no_frontend | None | control_plane/app/api/commercial_qos_billing_admin.py |
| GET | `/getting-started` | no_frontend | None | control_plane/app/api/public.py |
| GET | `/governance-federation-summary` | no_frontend | None | control_plane/app/api/portal.py |
| GET | `/graph` | no_frontend | None | control_plane/app/api/commercial_operations_center.py |
| GET | `/harness` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/harness/{rest:path}` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/health` | intentionally_hidden | Exempted: Public health check endpoint. | control_plane/app/api/system.py |
| GET | `/hub` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/incidents` | no_frontend | None | control_plane/app/api/commercial_governance_supervisor_admin.py |
| GET | `/inference/receipts` | no_frontend | None | control_plane/app/api/portal.py |
| GET | `/inference/receipts/{receipt_id}` | no_frontend | None | control_plane/app/api/portal.py |
| POST | `/inference/receipts/{receipt_id}/verify` | no_frontend | None | control_plane/app/api/portal.py |
| GET | `/inference/reproducibility` | no_frontend | None | control_plane/app/api/portal.py |
| GET | `/integrity` | no_frontend | None | control_plane/app/api/commercial_operations_center.py |
| GET | `/integrity/attestations` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| GET | `/integrity/events` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/integrity/quarantine/{entry_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/integrity/reverify/{entry_id}` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/integrity/scan` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| GET | `/integrity/scans` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| GET | `/integrity/status` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| GET | `/invoices` | has_frontend | Exempted: Legacy invoices path. | control_plane/app/api/portal.py |
| GET | `/invoices/{invoice_id}/download` | has_frontend | Inherited from /invoices: Legacy invoices path. | control_plane/app/api/portal.py |
| GET | `/keys` | no_frontend | None | control_plane/app/api/commercial_crypto_admin.py |
| POST | `/keys` | no_frontend | None | control_plane/app/api/commercial_crypto_admin.py |
| POST | `/kill-switch` | no_frontend | None | control_plane/app/api/operations_remediation_execution_admin.py |
| GET | `/kill-switch` | no_frontend | None | control_plane/app/api/operations_remediation_execution_admin.py |
| GET | `/lineage` | no_frontend | None | control_plane/app/api/commercial_operations_center.py |
| GET | `/managed/appliances` | no_frontend | None | control_plane/app/api/managed_control_plane.py |
| POST | `/managed/appliances/enroll` | no_frontend | None | control_plane/app/api/managed_control_plane.py |
| POST | `/managed/appliances/enrollment-token` | no_frontend | None | control_plane/app/api/managed_control_plane.py |
| POST | `/managed/appliances/{appliance_id}/heartbeat` | no_frontend | None | control_plane/app/api/managed_control_plane.py |
| POST | `/managed/appliances/{appliance_id}/revoke` | no_frontend | None | control_plane/app/api/managed_control_plane.py |
| POST | `/managed/organizations` | no_frontend | None | control_plane/app/api/managed_control_plane.py |
| GET | `/managed/organizations` | no_frontend | None | control_plane/app/api/managed_control_plane.py |
| POST | `/managed/workspaces` | no_frontend | None | control_plane/app/api/managed_control_plane.py |
| GET | `/managed/workspaces` | no_frontend | None | control_plane/app/api/managed_control_plane.py |
| POST | `/manifests` | has_frontend | Exempted: Adapter manifest management. | control_plane/app/api/operations_adapter_sandbox_admin.py |
| GET | `/manifests` | has_frontend | Exempted: Adapter manifest management. | control_plane/app/api/operations_adapter_sandbox_admin.py |
| GET | `/manifests/{manifest_id}` | has_frontend | Inherited from /manifests: Adapter manifest management. | control_plane/app/api/operations_adapter_sandbox_admin.py |
| GET | `/me` | no_frontend | None | control_plane/app/api/portal.py |
| GET | `/metrics` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/models` | has_frontend | Route Only | control_plane/app/api/portal.py |
| GET | `/monitoring` | no_frontend | None | control_plane/app/api/system.py |
| POST | `/onboarding/event` | no_frontend | None | control_plane/app/api/portal.py |
| GET | `/operational-readiness` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/opportunities` | no_frontend | None | control_plane/app/api/commercial_live_balancing_admin.py |
| GET | `/overview` | no_frontend | None | control_plane/app/api/commercial_geo_routing_admin.py |
| POST | `/payments/webhooks/{provider}` | intentionally_hidden | Exempted: Inbound webhook. | control_plane/app/api/payments.py |
| GET | `/plans` | no_frontend | None | control_plane/app/api/portal.py |
| GET | `/pocket-tts` | no_frontend | None | control_plane/app/api/pocket_tts.py |
| GET | `/pocket-tts/{path:path}` | no_frontend | None | control_plane/app/api/pocket_tts.py |
| POST | `/pocket-tts/{path:path}` | no_frontend | None | control_plane/app/api/pocket_tts.py |
| GET | `/policies` | no_frontend | None | control_plane/app/api/commercial_global_traffic_admin.py |
| POST | `/policies` | no_frontend | None | control_plane/app/api/commercial_global_traffic_admin.py |
| POST | `/policies/draft` | no_frontend | None | control_plane/app/api/commercial_global_routing_admin.py |
| POST | `/policies/rollback` | no_frontend | None | control_plane/app/api/commercial_global_routing_admin.py |
| POST | `/policies/simulate` | no_frontend | None | control_plane/app/api/commercial_global_routing_admin.py |
| GET | `/policies/{id}/health` | no_frontend | None | control_plane/app/api/commercial_global_traffic_admin.py |
| POST | `/policies/{id}/pause` | no_frontend | None | control_plane/app/api/commercial_global_traffic_admin.py |
| POST | `/policies/{id}/rollback` | no_frontend | None | control_plane/app/api/commercial_global_traffic_admin.py |
| POST | `/policies/{policy_id}/activate` | no_frontend | None | control_plane/app/api/commercial_global_routing_admin.py |
| GET | `/portal/agents/audit/actions` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_agent_audit_portal.py |
| GET | `/portal/agents/audit/executions` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_agent_audit_portal.py |
| GET | `/portal/agents/audit/executions/{execution_id}` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_agent_audit_portal.py |
| GET | `/portal/agents/audit/replay` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_agent_audit_portal.py |
| GET | `/portal/agents/audit/violations` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_agent_audit_portal.py |
| GET | `/portal/inference/proofs/proofs` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_execution_proofs_portal.py |
| GET | `/portal/inference/proofs/proofs/{proof_id}` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_execution_proofs_portal.py |
| POST | `/portal/inference/proofs/proofs/{proof_id}/verify` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_execution_proofs_portal.py |
| GET | `/portal/inference/timelines/{timeline_id}/witness-quorum` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_witness_portal.py |
| GET | `/portal/inference/timelines/{timeline_id}/witness-signatures` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_witness_portal.py |
| GET | `/portal/operations/correlations/` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/operations_correlation_portal.py |
| GET | `/portal/operations/correlations/trust-graph` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/operations_correlation_portal.py |
| GET | `/portal/policy/evaluations` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_policy_runtime_admin.py |
| GET | `/portal/workflows/audit/determinism/{execution_id}` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_workflow_audit_portal.py |
| GET | `/portal/workflows/audit/executions` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_workflow_audit_portal.py |
| GET | `/portal/workflows/audit/governance/executions` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_workflow_audit_portal.py |
| GET | `/portal/workflows/audit/governance/{execution_id}` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_workflow_audit_portal.py |
| GET | `/portal/workflows/audit/provenance/{execution_id}` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_workflow_audit_portal.py |
| GET | `/portal/workflows/audit/receipts` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_workflow_audit_portal.py |
| GET | `/portal/workflows/audit/replay/sessions` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_workflow_audit_portal.py |
| GET | `/portal/workflows/federation/status` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_federated_workflows_admin.py |
| GET | `/portal/workflows/governance/executions` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_workflow_governance_portal.py |
| GET | `/portal/workflows/governance/executions/{execution_id}` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_workflow_governance_portal.py |
| GET | `/portal/workflows/replay/sessions` | has_frontend | Inherited from /portal: Client portal surface. | control_plane/app/api/commercial_workflow_governance_portal.py |
| POST | `/prepare` | no_frontend | None | control_plane/app/api/operations_remediation_execution_admin.py |
| GET | `/pricing` | no_frontend | None | control_plane/app/api/public.py |
| GET | `/provider-settings` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/providers` | no_frontend | None | control_plane/app/api/commercial_crypto_admin.py |
| POST | `/providers` | no_frontend | None | control_plane/app/api/commercial_crypto_admin.py |
| GET | `/public/branding` | no_frontend | None | control_plane/app/api/public.py |
| GET | `/public/capabilities` | no_frontend | None | control_plane/app/api/public.py |
| GET | `/public/plans` | no_frontend | None | control_plane/app/api/public.py |
| POST | `/public/signup` | no_frontend | None | control_plane/app/api/public.py |
| POST | `/public/webhooks/local-payment` | no_frontend | None | control_plane/app/api/public.py |
| GET | `/qos-billing` | no_frontend | None | control_plane/app/api/portal.py |
| GET | `/rag/legal-holds` | has_frontend | Route Only | control_plane/app/api/portal.py |
| GET | `/rag/retrieval-history` | has_frontend | Route Only | control_plane/app/api/portal.py |
| GET | `/rag/trust-status` | has_frontend | Route Only | control_plane/app/api/portal.py |
| GET | `/rag/vault` | has_frontend | Route Only | control_plane/app/api/portal.py |
| GET | `/ready` | api_client_only | API Client Only | control_plane/app/api/system.py |
| GET | `/recommendations` | no_frontend | None | control_plane/app/api/commercial_geo_routing_admin.py |
| GET | `/records` | no_frontend | None | control_plane/app/api/commercial_qos_billing_admin.py |
| POST | `/reset-circuit-breaker` | no_frontend | None | control_plane/app/api/commercial_cross_cluster_forwarding_admin.py |
| GET | `/risk` | no_frontend | None | control_plane/app/api/commercial_governance_supervisor_admin.py |
| GET | `/robots.txt` | intentionally_hidden | Exempted: Standard crawler file. | control_plane/app/api/public.py |
| POST | `/rotate` | no_frontend | None | control_plane/app/api/commercial_crypto_admin.py |
| GET | `/runs` | has_frontend | Exempted: Sandbox run tracking. | control_plane/app/api/operations_adapter_sandbox_admin.py |
| POST | `/runs/prepare` | has_frontend | Inherited from /runs: Sandbox run tracking. | control_plane/app/api/operations_adapter_sandbox_admin.py |
| POST | `/runs/simulate` | has_frontend | Inherited from /runs: Sandbox run tracking. | control_plane/app/api/operations_adapter_sandbox_admin.py |
| GET | `/runs/{run_id}` | has_frontend | Inherited from /runs: Sandbox run tracking. | control_plane/app/api/operations_adapter_sandbox_admin.py |
| POST | `/runs/{run_id}/receipt` | has_frontend | Inherited from /runs: Sandbox run tracking. | control_plane/app/api/operations_adapter_sandbox_admin.py |
| GET | `/runtime/nodes/` | no_frontend | None | control_plane/app/api/distributed_runtime.py |
| POST | `/runtime/nodes/register` | no_frontend | None | control_plane/app/api/distributed_runtime.py |
| GET | `/runtime/nodes/{node_id}` | no_frontend | None | control_plane/app/api/distributed_runtime.py |
| POST | `/runtime/nodes/{node_id}/drain` | no_frontend | None | control_plane/app/api/distributed_runtime.py |
| POST | `/runtime/nodes/{node_id}/heartbeat` | no_frontend | None | control_plane/app/api/distributed_runtime.py |
| POST | `/sign` | no_frontend | None | control_plane/app/api/commercial_crypto_admin.py |
| GET | `/signup` | no_frontend | None | control_plane/app/api/public.py |
| POST | `/simulate` | no_frontend | None | control_plane/app/api/commercial_global_traffic_admin.py |
| POST | `/simulate-payment/{invoice_id}` | no_frontend | None | control_plane/app/api/portal.py |
| GET | `/sitemap.xml` | intentionally_hidden | Exempted: Standard SEO file. | control_plane/app/api/public.py |
| POST | `/snapshot` | no_frontend | None | control_plane/app/api/commercial_operations_center.py |
| GET | `/status` | api_client_only | API Client Only | control_plane/app/api/system.py |
| GET | `/supply-chain/bundles` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/supply-chain/bundles` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/supply-chain/bundles/{bundle_id}/promote` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/supply-chain/bundles/{bundle_id}/reject` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/supply-chain/bundles/{bundle_id}/verify` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| GET | `/supply-chain/provenance` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/supply-chain/provenance` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/supply-chain/register` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| GET | `/supply-chain/registry` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| GET | `/supply-chain/status` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/supply-chain/{entry_id}/approve` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/supply-chain/{entry_id}/quarantine` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/supply-chain/{entry_id}/revoke` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/supply-chain/{entry_id}/verify` | api_client_only | API Client Only | control_plane/app/api/commercial_model_supply_chain_admin.py |
| POST | `/test` | no_frontend | None | control_plane/app/api/commercial_cross_cluster_forwarding_admin.py |
| POST | `/test-chat` | no_frontend | None | control_plane/app/api/portal.py |
| GET | `/tests` | no_frontend | None | control_plane/app/api/system.py |
| GET | `/trust-chain` | no_frontend | None | control_plane/app/api/commercial_crypto_admin.py |
| GET | `/trust-violations` | no_frontend | None | control_plane/app/api/commercial_operations_center.py |
| POST | `/upgrade` | no_frontend | None | control_plane/app/api/portal.py |
| GET | `/usage` | has_frontend | Route Only | control_plane/app/api/portal.py |
| GET | `/usage-stats` | no_frontend | None | control_plane/app/api/portal.py |
| POST | `/v1/agents` | api_client_only | API Client Only | control_plane/app/api/agents_v1.py |
| GET | `/v1/agents` | api_client_only | API Client Only | control_plane/app/api/agents_v1.py |
| GET | `/v1/agents/runs/{run_id}` | api_client_only | Exempted: WebSocket streaming handled via internal helper. | control_plane/app/api/agents_v1.py |
| POST | `/v1/agents/runs/{run_id}/cancel` | api_client_only | Exempted: WebSocket streaming handled via internal helper. | control_plane/app/api/agents_v1.py |
| GET | `/v1/agents/runs/{run_id}/events` | api_client_only | Exempted: WebSocket streaming handled via internal helper. | control_plane/app/api/agents_v1.py |
| GET | `/v1/agents/sessions` | api_client_only | API Client Only | control_plane/app/api/agent_sessions.py |
| GET | `/v1/agents/sessions/{session_id}` | api_client_only | API Client Only | control_plane/app/api/agent_sessions.py |
| DELETE | `/v1/agents/sessions/{session_id}` | api_client_only | API Client Only | control_plane/app/api/agent_sessions.py |
| PATCH | `/v1/agents/sessions/{session_id}` | api_client_only | API Client Only | control_plane/app/api/agent_sessions.py |
| POST | `/v1/agents/sessions/{session_id}/messages` | api_client_only | API Client Only | control_plane/app/api/agent_sessions.py |
| GET | `/v1/agents/sessions/{session_id}/messages` | api_client_only | API Client Only | control_plane/app/api/agent_sessions.py |
| POST | `/v1/agents/sessions/{session_id}/runs` | api_client_only | API Client Only | control_plane/app/api/agent_sessions.py |
| GET | `/v1/agents/{agent_id}` | api_client_only | API Client Only | control_plane/app/api/agents_v1.py |
| POST | `/v1/agents/{agent_id}/runs` | api_client_only | API Client Only | control_plane/app/api/agents_v1.py |
| POST | `/v1/agents/{agent_id}/sessions` | api_client_only | API Client Only | control_plane/app/api/agent_sessions.py |
| POST | `/v1/assistants` | no_frontend | None | control_plane/app/api/assistants_v1.py |
| GET | `/v1/assistants` | no_frontend | None | control_plane/app/api/assistants_v1.py |
| POST | `/v1/batches` | api_client_only | Exempted: Asynchronous batch processing. | control_plane/app/api/batches_v1.py |
| GET | `/v1/batches/{batch_id}` | api_client_only | Inherited from /v1/batches: Asynchronous batch processing. | control_plane/app/api/batches_v1.py |
| POST | `/v1/batches/{batch_id}/cancel` | api_client_only | Inherited from /v1/batches: Asynchronous batch processing. | control_plane/app/api/batches_v1.py |
| GET | `/v1/batches/{batch_id}/results` | api_client_only | Inherited from /v1/batches: Asynchronous batch processing. | control_plane/app/api/batches_v1.py |
| GET | `/v1/chat/channels` | api_client_only | Inherited from /v1/chat: Standard OpenAI-compatible chat interface. | control_plane/app/api/collab_chat.py |
| POST | `/v1/chat/channels` | api_client_only | Inherited from /v1/chat: Standard OpenAI-compatible chat interface. | control_plane/app/api/collab_chat.py |
| GET | `/v1/chat/channels/{channel_id}/messages` | api_client_only | Inherited from /v1/chat: Standard OpenAI-compatible chat interface. | control_plane/app/api/collab_chat.py |
| POST | `/v1/chat/channels/{channel_id}/messages` | api_client_only | Inherited from /v1/chat: Standard OpenAI-compatible chat interface. | control_plane/app/api/collab_chat.py |
| POST | `/v1/chat/completions` | api_client_only | Inherited from /v1/chat: Standard OpenAI-compatible chat interface. | control_plane/app/api/client.py |
| POST | `/v1/chat/completions/async` | api_client_only | Inherited from /v1/chat: Standard OpenAI-compatible chat interface. | control_plane/app/api/client.py |
| POST | `/v1/completions` | api_client_only | Exempted: Legacy completion interface. | control_plane/app/api/client.py |
| POST | `/v1/embeddings` | api_client_only | Exempted: Standard embedding interface. | control_plane/app/api/client.py |
| GET | `/v1/ide/files` | no_frontend | None | control_plane/app/api/web_ide.py |
| GET | `/v1/ide/files/read` | no_frontend | None | control_plane/app/api/web_ide.py |
| POST | `/v1/ide/files/write` | no_frontend | None | control_plane/app/api/web_ide.py |
| POST | `/v1/ide/run` | no_frontend | None | control_plane/app/api/web_ide.py |
| POST | `/v1/ide/validate` | no_frontend | None | control_plane/app/api/web_ide.py |
| GET | `/v1/ide/workspace` | no_frontend | None | control_plane/app/api/web_ide.py |
| GET | `/v1/jobs/{job_id}` | no_frontend | None | control_plane/app/api/client.py |
| DELETE | `/v1/jobs/{job_id}/cancel` | no_frontend | None | control_plane/app/api/client.py |
| GET | `/v1/marketplace/categories` | no_frontend | None | control_plane/app/api/agent_marketplace_public.py |
| GET | `/v1/marketplace/items` | no_frontend | None | control_plane/app/api/agent_marketplace_public.py |
| POST | `/v1/marketplace/items` | no_frontend | None | control_plane/app/api/agent_marketplace_public.py |
| GET | `/v1/marketplace/items/{item_id}` | no_frontend | None | control_plane/app/api/agent_marketplace_public.py |
| PUT | `/v1/marketplace/items/{item_id}` | no_frontend | None | control_plane/app/api/agent_marketplace_public.py |
| POST | `/v1/marketplace/items/{item_id}/download` | no_frontend | None | control_plane/app/api/agent_marketplace_public.py |
| POST | `/v1/marketplace/items/{item_id}/rate` | no_frontend | None | control_plane/app/api/agent_marketplace_public.py |
| GET | `/v1/marketplace/items/{item_id}/reviews` | no_frontend | None | control_plane/app/api/agent_marketplace_public.py |
| GET | `/v1/marketplace/my-items` | no_frontend | None | control_plane/app/api/agent_marketplace_public.py |
| GET | `/v1/marketplace/publishers/me` | no_frontend | None | control_plane/app/api/agent_marketplace_public.py |
| POST | `/v1/marketplace/publishers/register` | no_frontend | None | control_plane/app/api/agent_marketplace_public.py |
| GET | `/v1/mobile/config` | api_client_only | Inherited from /v1/mobile: Mobile push and device registration. | control_plane/app/api/mobile_v1.py |
| POST | `/v1/mobile/devices/register` | api_client_only | Inherited from /v1/mobile: Mobile push and device registration. | control_plane/app/api/mobile_v1.py |
| POST | `/v1/mobile/push/subscribe` | api_client_only | Inherited from /v1/mobile: Mobile push and device registration. | control_plane/app/api/mobile_v1.py |
| POST | `/v1/mobile/push/unsubscribe` | api_client_only | Inherited from /v1/mobile: Mobile push and device registration. | control_plane/app/api/mobile_v1.py |
| GET | `/v1/models` | no_frontend | None | control_plane/app/api/client.py |
| POST | `/v1/multimodal/assets` | no_frontend | None | control_plane/app/api/multimodal.py |
| GET | `/v1/multimodal/assets/{asset_id}` | no_frontend | None | control_plane/app/api/multimodal.py |
| POST | `/v1/multimodal/speech-to-text` | no_frontend | None | control_plane/app/api/multimodal.py |
| POST | `/v1/multimodal/vision` | no_frontend | None | control_plane/app/api/multimodal.py |
| POST | `/v1/rag/collections` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag_enterprise.py |
| GET | `/v1/rag/collections` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag_enterprise.py |
| POST | `/v1/rag/documents` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag_enterprise.py |
| GET | `/v1/rag/documents` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag_enterprise.py |
| GET | `/v1/rag/documents/{doc_id}` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag_enterprise.py |
| DELETE | `/v1/rag/documents/{doc_id}` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag_enterprise.py |
| POST | `/v1/rag/files` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag.py |
| GET | `/v1/rag/files` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag.py |
| GET | `/v1/rag/files/{file_id}` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag.py |
| DELETE | `/v1/rag/files/{file_id}` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag.py |
| POST | `/v1/rag/files/{file_id}/reprocess` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag.py |
| POST | `/v1/rag/query` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag.py |
| GET | `/v1/rag/usage` | has_frontend | Inherited from /v1/rag: RAG client interface. | control_plane/app/api/rag.py |
| POST | `/v1/responses` | no_frontend | None | control_plane/app/api/client.py |
| POST | `/v1/threads` | api_client_only | Exempted: Stateful thread management for Assistants API. | control_plane/app/api/assistants_v1.py |
| POST | `/v1/threads/{thread_id}/messages` | api_client_only | Inherited from /v1/threads: Stateful thread management for Assistants API. | control_plane/app/api/assistants_v1.py |
| POST | `/v1/threads/{thread_id}/runs` | api_client_only | Inherited from /v1/threads: Stateful thread management for Assistants API. | control_plane/app/api/assistants_v1.py |
| GET | `/v1/threads/{thread_id}/runs/{run_id}` | api_client_only | Inherited from /v1/threads: Stateful thread management for Assistants API. | control_plane/app/api/assistants_v1.py |
| POST | `/v1/voice/sessions` | api_client_only | Inherited from /v1/voice: Real-time voice/WebRTC signaling. | control_plane/app/api/voice.py |
| GET | `/v1/voice/sessions` | api_client_only | Inherited from /v1/voice: Real-time voice/WebRTC signaling. | control_plane/app/api/voice.py |
| GET | `/v1/voice/sessions/{session_id}` | api_client_only | Inherited from /v1/voice: Real-time voice/WebRTC signaling. | control_plane/app/api/voice.py |
| DELETE | `/v1/voice/sessions/{session_id}` | api_client_only | Inherited from /v1/voice: Real-time voice/WebRTC signaling. | control_plane/app/api/voice.py |
| POST | `/v1/voice/webrtc/offer` | api_client_only | Inherited from /v1/voice: Real-time voice/WebRTC signaling. | control_plane/app/api/voice.py |
| POST | `/verify` | no_frontend | None | control_plane/app/api/commercial_crypto_admin.py |
| GET | `/violations` | no_frontend | None | control_plane/app/api/operations_adapter_sandbox_admin.py |
| GET | `/wallet` | has_frontend | Exempted: Legacy wallet path, redirecting to /portal/wallet. | control_plane/app/api/portal.py |
| POST | `/wallet/recharge-request` | has_frontend | Inherited from /wallet: Legacy wallet path, redirecting to /portal/wallet. | control_plane/app/api/portal.py |
| POST | `/wallet/topups` | has_frontend | Inherited from /wallet: Legacy wallet path, redirecting to /portal/wallet. | control_plane/app/api/portal.py |
| GET | `/wallet/topups` | has_frontend | Inherited from /wallet: Legacy wallet path, redirecting to /portal/wallet. | control_plane/app/api/portal.py |
| POST | `/workflows` | no_frontend | None | control_plane/app/api/operations_adapter_promotion_admin.py |
| GET | `/workflows` | no_frontend | None | control_plane/app/api/operations_adapter_promotion_admin.py |
| GET | `/workflows/{workflow_id}` | no_frontend | None | control_plane/app/api/operations_adapter_promotion_admin.py |
| GET | `/workflows/{workflow_id}/gates` | no_frontend | None | control_plane/app/api/operations_adapter_promotion_admin.py |
| POST | `/workflows/{workflow_id}/promote` | no_frontend | None | control_plane/app/api/operations_adapter_promotion_admin.py |
| POST | `/workflows/{workflow_id}/receipt` | no_frontend | None | control_plane/app/api/operations_adapter_promotion_admin.py |
| POST | `/workflows/{workflow_id}/rollback` | no_frontend | None | control_plane/app/api/operations_adapter_promotion_admin.py |
| GET | `/workflows/{workflow_id}/transitions` | no_frontend | None | control_plane/app/api/operations_adapter_promotion_admin.py |
| GET | `/{execution_id}` | no_frontend | None | control_plane/app/api/operations_remediation_execution_admin.py |
| POST | `/{execution_id}/kill` | no_frontend | None | control_plane/app/api/operations_remediation_execution_admin.py |
| GET | `/{execution_id}/rollback-plan` | no_frontend | None | control_plane/app/api/operations_remediation_execution_admin.py |
| GET | `/{page}.html` | intentionally_hidden | Exempted: Static HTML pages. | control_plane/app/api/system.py |
| POST | `/{record_id}/attach-invoice` | no_frontend | None | control_plane/app/api/commercial_qos_billing_admin.py |
| POST | `/{record_id}/debit-wallet` | no_frontend | None | control_plane/app/api/commercial_qos_billing_admin.py |