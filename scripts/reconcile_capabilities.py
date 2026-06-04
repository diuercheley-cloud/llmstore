#!/usr/bin/env python3
# Owner: platform-ops
import os
import sys

import yaml

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

def main():
    yaml_path = os.path.join(base_dir, "config/supported-surface.yaml")
    if not os.path.exists(yaml_path):
        print(f"FAIL: config/supported-surface.yaml not found at {yaml_path}")
        sys.exit(1)
        
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"FAIL: Error reading config/supported-surface.yaml: {e}")
        sys.exit(1)

    capabilities = data.get("capabilities", [])
    
    # Mapping definitions
    mapping = {
        "agent-shared-artifacts": {
            "services": ["artifact_permissions", "agent_workspace_admin"]
        },
        "agent-event-driven": {
            "services": [
                "cron_triggers",
                "webhook_triggers",
                "pubsub_triggers",
                "event_policy",
                "event_hooks",
                "event_deduplication",
                "agent_events_admin",
                "agent_events"
            ],
            "flags": [
                "agent_event_hooks_enabled",
                "agent_cron_triggers_enabled",
                "agent_pubsub_triggers_enabled",
                "agent_external_webhook_triggers_enabled"
            ]
        },
        "agent-auto-optimization": {
            "services": [
                "tool_selection_optimizer",
                "optimizer",
                "optimization_gate",
                "policy_optimizer",
                "prompt_optimizer",
                "agent_optimization_admin"
            ]
        },
        "agent-iam": {
            "services": [
                "delegated_tokens",
                "service_principal",
                "agent_identity",
                "agent_scopes",
                "credential_broker"
            ]
        },
        "agent-router-v2": {
            "services": [
                "agentic_router",
                "cost_quality_policy",
                "routing_explainer",
                "model_capability_registry"
            ]
        },
        "agent-tool-synthesis": {
            "services": ["sandbox_policy"]
        },
        "agent-real-connectors": {
            "services": ["connector_mode", "connector_runtime", "http_client"]
        },
        "agent-knowledge-graph": {
            "services": [
                "graph_policy",
                "graph_reasoner",
                "graph_extractor",
                "graph_models"
            ],
            "flags": [
                "agent_graph_rag_enabled",
                "agent_graph_write_enabled",
                "agent_graph_external_db_enabled"
            ]
        },
        "agent-execution-plane": {
            "services": ["agent_scheduler"]
        },
        "agent-tool-governance": {
            "services": ["sandbox_escape_analysis"]
        },
        "agent-readiness": {
            "services": ["real_execution_readiness"]
        }
    }
    
    # 11. Add a new capability for plugins runtime if missing
    has_plugin_runtime = False
    for cap in capabilities:
        if cap.get("id") == "plugin-runtime":
            has_plugin_runtime = True
            break
            
    if not has_plugin_runtime:
        capabilities.append({
            "id": "plugin-runtime",
            "name": "Plugin Runtime",
            "area": "operations",
            "status": "supported",
            "owner": "platform-ops",
            "support_level": "production",
            "docs_url": "docs/plugins",
            "feature_flag": "PLUGIN_MARKETPLACE_ENABLED",
            "since_version": "v2.1.0-agentic-autonomy",
            "limitations": "Standard plugin runtime controls.",
            "test_coverage": "80%",
            "rollback_story": "Standard feature flag deactivation or deployment rollback.",
            "associated_services": ["execution_runtime"]
        })
        print("Added new 'plugin-runtime' capability.")

    # Reconcile services and flags
    for cap in capabilities:
        cap_id = cap.get("id")
        if cap_id in mapping:
            # Reconcile associated_services
            assoc = cap.get("associated_services", []) or []
            for s in mapping[cap_id].get("services", []):
                if s not in assoc:
                    assoc.append(s)
            cap["associated_services"] = assoc
            
            # Reconcile additional_flags
            flags = cap.get("additional_flags", []) or []
            for f in mapping[cap_id].get("flags", []):
                if f.upper() not in [x.upper() for x in flags]:
                    flags.append(f)
            cap["additional_flags"] = flags

    # Save back
    try:
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        print("INFO: successfully reconciled supported-surface.yaml.")
    except Exception as e:
        print(f"FAIL: Failed to save updated supported-surface.yaml: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
