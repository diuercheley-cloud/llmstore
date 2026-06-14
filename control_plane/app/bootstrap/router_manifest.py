from app.api.abuse_admin import router as abuse_admin_router
from app.api.admin import router as admin_router
from app.api.admin_clients import router as admin_clients_router
from app.api.admin_config import router as admin_config_router
from app.api.admin_models import router as admin_models_router
from app.api.admin_backends import router as admin_backends_router
from app.api.admin_billing import router as admin_billing_router
from app.api.admin_api_keys import router as admin_api_keys_router
from app.api.admin_usage import router as admin_usage_router
from app.api.admin_exports import router as admin_exports_router
from app.api.admin_mlops import router as admin_mlops_router
from app.api.admin_benchmarks import router as admin_benchmarks_router
from app.api.admin_cache import router as admin_cache_router
from app.api.admin_tests import router as admin_tests_router
from app.api.admin_inference import router as admin_inference_router
from app.api.admin_executions import router as admin_executions_router
from app.api.admin_evaluation import router as admin_evaluation_router
from app.api.admin_costs import router as admin_costs_router
from app.api.admin_federation_mesh import router as admin_federation_mesh_router
from app.api.admin_backup import router as admin_backup_router
from app.api.admin_compliance_evidence import router as admin_compliance_evidence_router
from app.api.admin_marketplace import router as admin_marketplace_router
from app.api.admin_performance import router as admin_performance_v2_router
from app.api.admin_model_provenance import router as admin_model_provenance_router
from app.api.admin_agent_memory import router as admin_agent_memory_router
from app.api.admin_metrics import router as admin_metrics_router
from app.api.admin_observability import router as admin_observability_router
from app.api.admin_model_experiments import router as admin_model_experiments_router
from app.api.admin_models_runtime import router as admin_models_runtime_router
from app.api.admin_onboarding import router as admin_onboarding_router
from app.api.admin_agent_protocols import router as admin_agent_protocols_router
from app.api.admin_policies import router as admin_policies_router
from app.api.admin_rbac import router as admin_rbac_router
from app.api.admin_sandbox import router as admin_sandbox_router
from app.api.admin_vectorstores import router as admin_vectorstores_router
from app.api.auth import router as auth_router
from app.api.billing_admin import router as billing_admin_router
from app.api.billing_reconciliation_admin import router as billing_reconciliation_admin_router
from app.api.chaos_admin import router as chaos_admin_router
from app.api.client import router as client_router
from app.api.collab_chat import router as collab_chat_router
from app.api.commercial_aiops_admin import router as commercial_aiops_admin_router
from app.api.commercial_appliance_admin import router as commercial_appliance_admin_router
from app.api.commercial_attestation_admin import (
    portal_router as commercial_attestation_portal_router,
)
from app.api.commercial_attestation_admin import router as commercial_attestation_admin_router
from app.api.commercial_attestation_public import router as commercial_attestation_public_router
from app.api.commercial_autonomous_guardrails_admin import (
    router as commercial_autonomous_guardrails_admin_router,
)
from app.api.commercial_capacity_admin import router as commercial_capacity_admin_router
from app.api.commercial_confidential_runtime_admin import (
    router as commercial_confidential_runtime_admin_router,
)
from app.api.commercial_cryptographic_receipts_admin import (
    router as commercial_cryptographic_receipts_admin_router,
)
from app.api.commercial_distributed_analytics_admin import (
    router as commercial_distributed_analytics_admin_router,
)
from app.api.commercial_encryption_admin import router as commercial_encryption_admin_router
from app.api.commercial_execution_proofs_admin import (
    router as commercial_execution_proofs_admin_router,
)
from app.api.commercial_execution_proofs_portal import (
    router as commercial_execution_proofs_portal_router,
)
from app.api.commercial_federation_admin import router as commercial_federation_admin_router
from app.api.commercial_governance_federation_admin import (
    router as commercial_governance_federation_admin_router,
)
from app.api.commercial_guardrails_admin import router as commercial_guardrails_admin_router
from app.api.commercial_ha_admin import router as commercial_ha_admin_router
from app.api.commercial_inference_reproducibility_admin import (
    router as commercial_inference_reproducibility_admin_router,
)
from app.api.commercial_infra_admin import router as commercial_infra_admin_router
from app.api.commercial_mesh_admin import portal_router as commercial_mesh_portal_router
from app.api.commercial_mesh_admin import router as commercial_mesh_admin_router
from app.api.commercial_model_lifecycle_admin import (
    portal_router as commercial_model_lifecycle_portal_router,
)
from app.api.commercial_model_lifecycle_admin import (
    router as commercial_model_lifecycle_admin_router,
)
from app.api.commercial_model_supply_chain_admin import (
    router as commercial_model_supply_chain_admin_router,
)
from app.api.commercial_operations_center import router as commercial_ops_center_router
from app.api.commercial_operations_center_admin import commercial_ops_center_admin_router
from app.api.commercial_policy_governance_admin import (
    router as commercial_policy_governance_admin_router,
)
from app.api.commercial_rag_admin import router as commercial_rag_admin_router
from app.api.commercial_routing_admin import router as commercial_routing_admin_router
from app.api.commercial_runtime_fabric_admin import (
    portal_router as commercial_runtime_fabric_portal_router,
)
from app.api.commercial_runtime_fabric_admin import router as commercial_runtime_fabric_admin_router
from app.api.commercial_sovereign_governance_admin import (
    router as commercial_sovereign_governance_admin_router,
)
from app.api.commercial_transparency_admin import router as commercial_transparency_admin_router
from app.api.commercial_witness_admin import router as commercial_witness_admin_router
from app.api.commercial_witness_portal import router as commercial_witness_portal_router
from app.api.compliance_admin import router as compliance_admin_router
from app.api.developer_docs import router as developer_docs_router
from app.api.enterprise_onboarding_admin import router as enterprise_onboarding_admin_router
from app.api.feature_flags_admin import router as feature_flags_admin_router
from app.api.financial_admin import router as financial_admin_router
from app.api.governance_policy_engine_admin import router as governance_policy_engine_admin_router
from app.api.hybrid_admin import router as hybrid_admin_router
from app.api.harness import router as harness_router
from app.api.mobile_v1 import router as mobile_v1_router
from app.api.multi_cluster_admin import router as multi_cluster_admin_router
from app.api.observability_admin import router as observability_admin_router
from app.api.operations_adapter_promotion_admin import (
    router as operations_adapter_promotion_admin_router,
)
from app.api.operations_adapter_registry_admin import (
    router as operations_adapter_registry_admin_router,
)
from app.api.operations_adapter_sandbox_admin import (
    router as operations_adapter_sandbox_admin_router,
)
from app.api.operations_admin import router as operations_admin_router
from app.api.operations_attestation_admin import router as operations_attestation_admin_router
from app.api.operations_compatibility_admin import router as operations_compatibility_admin_router
from app.api.operations_correlation_admin import router as operations_correlation_admin_router
from app.api.operations_correlation_portal import router as operations_correlation_portal_router
from app.api.operations_federation_sync_admin import (
    router as operations_federation_sync_admin_router,
)
from app.api.operations_plugin_runtime_admin import router as operations_plugin_runtime_admin_router
from app.api.operations_plugin_supply_chain_admin import (
    router as operations_plugin_supply_chain_admin_router,
)
from app.api.operations_remediation_admin import router as operations_remediation_admin_router
from app.api.operations_remediation_execution_admin import (
    router as operations_remediation_execution_admin_router,
)
from app.api.operations_reproducible_builds_admin import (
    router as operations_reproducible_builds_admin_router,
)
from app.api.operations_ux_admin import router as operations_ux_admin_router
from app.api.payments import router as payments_router
from app.api.performance_admin import router as performance_admin_router
from app.api.pki_attestation_admin import router as pki_attestation_admin_router
from app.api.pocket_tts import router as pocket_tts_router
from app.api.portal import account_router
from app.api.portal import router as portal_router
from app.api.providers import router as providers_router
from app.api.public import router as public_router
from app.api.rag import client_rag_router
from app.api.rag import router as rag_router
from app.api.rag_enterprise import admin_router as admin_rag_router
from app.api.rag_enterprise import router as rag_enterprise_router
from app.api.routing_admin import router as routing_admin_router
from app.api.routing_test import router as routing_test_router
from app.api.runtime_profiles_admin import router as runtime_profiles_admin_router
from app.api.saas_admin import router as saas_admin_router
from app.api.sales import router as sales_router
from app.api.support_admin import router as support_admin_router
from app.api.supported_surface_admin import router as supported_surface_admin_router
from app.api.system import router as system_router
from app.api.voice import router as voice_router
from app.api.wallet_admin import router as wallet_admin_router
from app.api.web_ide import router as web_ide_router
from app.api.web_search_admin import router as web_search_admin_router

# Structure: {"router": router_obj, "kwargs": {prefix: ..., tags: ...}}
ADMIN_ROUTERS = [
    {"router": abuse_admin_router, "kwargs": {}},
    {"router": admin_router, "kwargs": {}},
    {"router": admin_clients_router, "kwargs": {}},
    {"router": admin_config_router, "kwargs": {}},
    {"router": admin_models_router, "kwargs": {}},
    {"router": admin_backends_router, "kwargs": {}},
    {"router": admin_billing_router, "kwargs": {}},
    {"router": admin_api_keys_router, "kwargs": {}},
    {"router": admin_usage_router, "kwargs": {}},
    {"router": admin_exports_router, "kwargs": {}},
    {"router": admin_mlops_router, "kwargs": {}},
    {"router": admin_benchmarks_router, "kwargs": {}},
    {"router": admin_cache_router, "kwargs": {}},
    {"router": admin_tests_router, "kwargs": {}},
    {"router": admin_inference_router, "kwargs": {}},
    {"router": admin_executions_router, "kwargs": {}},
    {"router": admin_evaluation_router, "kwargs": {}},
    {"router": admin_costs_router, "kwargs": {}},
    {"router": admin_federation_mesh_router, "kwargs": {}},
    {"router": admin_backup_router, "kwargs": {}},
    {"router": admin_compliance_evidence_router, "kwargs": {}},
    {"router": admin_marketplace_router, "kwargs": {}},
    {"router": admin_performance_v2_router, "kwargs": {}},
    {"router": admin_model_provenance_router, "kwargs": {}},
    {"router": admin_agent_memory_router, "kwargs": {}},
    {"router": admin_metrics_router, "kwargs": {}},
    {"router": admin_observability_router, "kwargs": {}},
    {"router": admin_model_experiments_router, "kwargs": {}},
    {"router": admin_models_runtime_router, "kwargs": {}},
    {"router": admin_onboarding_router, "kwargs": {}},
    {"router": admin_agent_protocols_router, "kwargs": {}},
    {"router": admin_policies_router, "kwargs": {}},
    {"router": admin_rbac_router, "kwargs": {}},
    {"router": admin_sandbox_router, "kwargs": {}},
    {"router": admin_vectorstores_router, "kwargs": {}},
    {"router": chaos_admin_router, "kwargs": {}},
    {"router": compliance_admin_router, "kwargs": {}},
    {"router": enterprise_onboarding_admin_router, "kwargs": {}},
    {"router": feature_flags_admin_router, "kwargs": {}},
    {"router": financial_admin_router, "kwargs": {}},
    {"router": governance_policy_engine_admin_router, "kwargs": {}},
    {"router": hybrid_admin_router, "kwargs": {}},
    {"router": harness_router, "kwargs": {}},
    {"router": multi_cluster_admin_router, "kwargs": {}},
    {"router": observability_admin_router, "kwargs": {}},
    {"router": performance_admin_router, "kwargs": {}},
    {"router": pki_attestation_admin_router, "kwargs": {}},
    {"router": runtime_profiles_admin_router, "kwargs": {}},
    {"router": saas_admin_router, "kwargs": {}},
    {"router": support_admin_router, "kwargs": {}},
    {"router": supported_surface_admin_router, "kwargs": {}},
    {"router": wallet_admin_router, "kwargs": {}},
    {"router": web_search_admin_router, "kwargs": {}},
]

COMMERCIAL_ROUTERS = [
    {"router": collab_chat_router, "kwargs": {}},
    {"router": commercial_aiops_admin_router, "kwargs": {}},
    {"router": commercial_appliance_admin_router, "kwargs": {}},
    {"router": commercial_attestation_admin_router, "kwargs": {}},
    {"router": commercial_attestation_public_router, "kwargs": {}},
    {"router": commercial_autonomous_guardrails_admin_router, "kwargs": {}},
    {"router": commercial_capacity_admin_router, "kwargs": {}},
    {"router": commercial_confidential_runtime_admin_router, "kwargs": {}},
    {"router": commercial_cryptographic_receipts_admin_router, "kwargs": {}},
    {"router": commercial_distributed_analytics_admin_router, "kwargs": {}},
    {"router": commercial_encryption_admin_router, "kwargs": {"prefix": "/admin/security/encryption", "tags": ["commercial_encryption"]}},
    {"router": commercial_execution_proofs_admin_router, "kwargs": {}},
    {"router": commercial_federation_admin_router, "kwargs": {}},
    {"router": commercial_governance_federation_admin_router, "kwargs": {}},
    {"router": commercial_guardrails_admin_router, "kwargs": {}},
    {"router": commercial_ha_admin_router, "kwargs": {}},
    {"router": commercial_inference_reproducibility_admin_router, "kwargs": {}},
    {"router": commercial_infra_admin_router, "kwargs": {}},
    {"router": commercial_mesh_admin_router, "kwargs": {}},
    {"router": commercial_model_lifecycle_admin_router, "kwargs": {}},
    {"router": commercial_model_supply_chain_admin_router, "kwargs": {"prefix": "/admin/models", "tags": ["commercial_model_supply_chain"]}},
    {"router": commercial_ops_center_router, "kwargs": {"prefix": "/admin/ops-center", "tags": ["commercial_ops_center"]}},
    {"router": commercial_ops_center_admin_router, "kwargs": {}},
    {"router": commercial_policy_governance_admin_router, "kwargs": {}},
    {"router": commercial_rag_admin_router, "kwargs": {}},
    {"router": commercial_routing_admin_router, "kwargs": {}},
    {"router": commercial_runtime_fabric_admin_router, "kwargs": {}},
    {"router": commercial_sovereign_governance_admin_router, "kwargs": {}},
    {"router": commercial_transparency_admin_router, "kwargs": {}},
    {"router": commercial_witness_admin_router, "kwargs": {}},
    {"router": payments_router, "kwargs": {}},
    {"router": pocket_tts_router, "kwargs": {}},
    {"router": sales_router, "kwargs": {}},
    {"router": voice_router, "kwargs": {}},
    {"router": web_ide_router, "kwargs": {}},
]

OPERATIONS_ROUTERS = [
    {"router": operations_admin_router, "kwargs": {}},
    {"router": operations_adapter_promotion_admin_router, "kwargs": {"prefix": "/admin/operations/adapter-promotion", "tags": ["operations-adapter-promotion"]}},
    {"router": operations_adapter_registry_admin_router, "kwargs": {"prefix": "/admin/operations/adapter-registry", "tags": ["operations-adapter-registry"]}},
    {"router": operations_adapter_sandbox_admin_router, "kwargs": {"prefix": "/admin/operations/adapter-sandbox", "tags": ["operations-adapter-sandbox"]}},
    {"router": operations_attestation_admin_router, "kwargs": {"prefix": "/admin/operations", "tags": ["operations-attestation"]}},
    {"router": operations_compatibility_admin_router, "kwargs": {"tags": ["operations-compatibility"]}},
    {"router": operations_correlation_admin_router, "kwargs": {}},
    {"router": operations_federation_sync_admin_router, "kwargs": {"tags": ["operations-federation-sync"]}},
    {"router": operations_plugin_runtime_admin_router, "kwargs": {"tags": ["operations-plugin-runtime"]}},
    {"router": operations_plugin_supply_chain_admin_router, "kwargs": {"tags": ["operations-plugin-supply-chain"]}},
    {"router": operations_remediation_admin_router, "kwargs": {}},
    {"router": operations_remediation_execution_admin_router, "kwargs": {"prefix": "/admin/operations/remediation-executions", "tags": ["operations-remediation-execution"]}},
    {"router": operations_reproducible_builds_admin_router, "kwargs": {"tags": ["operations-reproducible-builds"]}},
    {"router": operations_ux_admin_router, "kwargs": {}},
]

PORTAL_ROUTERS = [
    {"router": portal_router, "kwargs": {"prefix": "/portal"}},
    {"router": account_router, "kwargs": {"prefix": "/v1"}},
    {"router": commercial_attestation_portal_router, "kwargs": {}},
    {"router": commercial_execution_proofs_portal_router, "kwargs": {}},
    {"router": commercial_mesh_portal_router, "kwargs": {}},
    {"router": commercial_model_lifecycle_portal_router, "kwargs": {}},
    {"router": commercial_runtime_fabric_portal_router, "kwargs": {}},
    {"router": commercial_witness_portal_router, "kwargs": {}},
    {"router": operations_correlation_portal_router, "kwargs": {}},
]

CORE_ROUTERS = [
    {"router": public_router, "kwargs": {}},
    {"router": system_router, "kwargs": {}},
    {"router": providers_router, "kwargs": {}},
    {"router": developer_docs_router, "kwargs": {}},
]

CLIENT_ROUTERS = [
    {"router": client_router, "kwargs": {}},
    {"router": mobile_v1_router, "kwargs": {}},
]

RAG_ROUTERS = [
    {"router": rag_router, "kwargs": {}},
    {"router": client_rag_router, "kwargs": {}},
    {"router": rag_enterprise_router, "kwargs": {}},
    {"router": admin_rag_router, "kwargs": {}},
]

ROUTING_ROUTERS = [
    {"router": routing_admin_router, "kwargs": {}},
    {"router": routing_test_router, "kwargs": {}},
]

AUTH_ROUTERS = [
    {"router": auth_router, "kwargs": {}},
]

# Aggregate all routers to construct ROUTER_MANIFEST for compatibility and testing
ROUTER_MANIFEST = []
_seen_keys = set()
for router_list in [
    ADMIN_ROUTERS,
    COMMERCIAL_ROUTERS,
    OPERATIONS_ROUTERS,
    PORTAL_ROUTERS,
    CORE_ROUTERS,
    CLIENT_ROUTERS,
    RAG_ROUTERS,
    ROUTING_ROUTERS,
    AUTH_ROUTERS,
]:
    for entry in router_list:
        router = entry["router"]
        module = router.__module__
        router_name = "router"
        for k, v in list(globals().items()):
            if v is router and k != "router":
                router_name = k
                break
        key = (module, router_name)
        if key not in _seen_keys:
            _seen_keys.add(key)
            ROUTER_MANIFEST.append({
                "module": module,
                "router_name": router_name,
            })

