import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401

from app.api.deps import get_inference_proxy
from app.api.admin import router as admin_router
from app.api.admin_rbac import router as admin_rbac_router
from app.api.saas_admin import router as saas_admin_router
from app.api.sales import router as sales_router
from app.api.admin_tests import router as admin_tests_router
from app.api.client import router as client_router
from app.api.rag import router as rag_router, client_rag_router
from app.api.rag_enterprise import router as rag_enterprise_router, admin_router as admin_rag_router
from app.api.portal import router as portal_router, account_router
from app.api.admin_models_runtime import router as admin_models_runtime_router
from app.api.public import router as public_router
from app.api.system import router as system_router
from app.api.pocket_tts import router as pocket_tts_router
from app.api.pki_attestation_admin import router as pki_attestation_admin_router
from app.api.developer_docs import router as developer_docs_router
from app.api.billing_admin import router as billing_admin_router
from app.api.wallet_admin import router as wallet_admin_router
from app.api.providers import router as providers_router
from app.api.routing_admin import router as routing_admin_router
from app.api.routing_test import router as routing_test_router
from app.api.hybrid_admin import router as hybrid_admin_router
from app.api.support_admin import router as support_admin_router
from app.api.abuse_admin import router as abuse_admin_router
from app.api.financial_admin import router as financial_admin_router
from app.api.commercial_guardrails_admin import router as commercial_guardrails_admin_router
from app.api.commercial_autonomous_guardrails_admin import router as commercial_autonomous_guardrails_admin_router
from app.api.commercial_routing_admin import router as commercial_routing_admin_router
from app.api.commercial_distributed_analytics_admin import router as commercial_distributed_analytics_admin_router
from app.api.commercial_ha_admin import router as commercial_ha_admin_router
from app.api.commercial_federation_admin import router as commercial_federation_admin_router
from app.api.billing_reconciliation_admin import router as billing_reconciliation_admin_router
from app.api.commercial_capacity_admin import router as commercial_capacity_admin_router
from app.api.commercial_infra_admin import router as commercial_infra_admin_router
from app.api.supported_surface_admin import router as supported_surface_admin_router
from app.api.runtime_profiles_admin import router as runtime_profiles_admin_router
from app.api.feature_flags_admin import router as feature_flags_admin_router
from app.api.commercial_policy_governance_admin import router as commercial_policy_governance_admin_router
from app.api.commercial_governance_federation_admin import router as commercial_governance_federation_admin_router
from app.api.commercial_encryption_admin import router as commercial_encryption_admin_router
from app.api.commercial_sovereign_governance_admin import router as commercial_sovereign_governance_admin_router
from app.api.commercial_model_supply_chain_admin import router as commercial_model_supply_chain_admin_router
from app.api.commercial_inference_reproducibility_admin import router as commercial_inference_reproducibility_admin_router
from app.api.commercial_cryptographic_receipts_admin import router as commercial_cryptographic_receipts_admin_router
from app.api.commercial_execution_proofs_admin import router as commercial_execution_proofs_admin_router
from app.api.commercial_execution_proofs_portal import router as commercial_execution_proofs_portal_router
from app.api.commercial_witness_admin import router as commercial_witness_admin_router
from app.api.commercial_witness_portal import router as commercial_witness_portal_router
from app.api.commercial_transparency_admin import router as commercial_transparency_admin_router
from app.api.commercial_attestation_public import router as commercial_attestation_public_router
from app.api.commercial_attestation_admin import router as commercial_attestation_admin_router
from app.api.commercial_attestation_admin import portal_router as commercial_attestation_portal_router
from app.api.commercial_confidential_runtime_admin import router as commercial_confidential_runtime_admin_router
from app.api.commercial_agents_admin import router as commercial_agents_admin_router
from app.api.commercial_trusted_agents_admin import router as commercial_trusted_agents_admin_router
from app.api.commercial_agent_audit_portal import router as commercial_agent_audit_portal_router
from app.api.commercial_workflows_admin import router as commercial_workflows_admin_router
from app.api.commercial_workflow_audit_portal import router as commercial_workflow_audit_portal_router
from app.api.commercial_workflow_governance_portal import router as commercial_workflow_governance_portal_router
from app.api.commercial_federated_workflows_admin import router as commercial_federated_workflows_admin_router
from app.api.commercial_appliance_admin import router as commercial_appliance_admin_router
from app.api.commercial_mesh_admin import router as commercial_mesh_admin_router, portal_router as commercial_mesh_portal_router
from app.api.commercial_runtime_fabric_admin import router as commercial_runtime_fabric_admin_router, portal_router as commercial_runtime_fabric_portal_router
from app.api.commercial_aiops_admin import router as commercial_aiops_admin_router
from app.api.commercial_operations_center_admin import commercial_ops_center_admin_router
from app.api.commercial_operations_center import router as commercial_ops_center_router
from app.api.commercial_rag_admin import router as commercial_rag_admin_router
from app.api.commercial_model_lifecycle_admin import router as commercial_model_lifecycle_admin_router
from app.api.commercial_model_lifecycle_admin import portal_router as commercial_model_lifecycle_portal_router
from app.api.operations_admin import router as operations_admin_router
from app.api.operations_correlation_admin import router as operations_correlation_admin_router
from app.api.operations_correlation_portal import router as operations_correlation_portal_router
from app.api.operations_remediation_admin import router as operations_remediation_admin_router
from app.api.operations_remediation_execution_admin import router as operations_remediation_execution_admin_router
from app.api.operations_adapter_sandbox_admin import router as operations_adapter_sandbox_admin_router
from app.api.operations_adapter_registry_admin import router as operations_adapter_registry_admin_router
from app.api.operations_adapter_promotion_admin import router as operations_adapter_promotion_admin_router
from app.api.operations_attestation_admin import router as operations_attestation_admin_router
from app.api.operations_federation_sync_admin import router as operations_federation_sync_admin_router
from app.api.operations_compatibility_admin import router as operations_compatibility_admin_router
from app.api.operations_plugin_runtime_admin import router as operations_plugin_runtime_admin_router
from app.api.operations_plugin_supply_chain_admin import router as operations_plugin_supply_chain_admin_router
from app.api.operations_reproducible_builds_admin import router as operations_reproducible_builds_admin_router
from app.api.governance_policy_engine_admin import router as governance_policy_engine_admin_router
from app.api.billing_reconciliation_admin import router as billing_reconciliation_admin_router
from app.api.observability_admin import router as observability_admin_router
from app.api.operations_ux_admin import router as operations_ux_admin_router
from app.api.performance_admin import router as performance_admin_router
from app.api.enterprise_onboarding_admin import router as enterprise_onboarding_admin_router
from app.api.admin_onboarding import router as admin_onboarding_router
from app.api.admin_metrics import router as admin_metrics_router
from app.api.multi_cluster_admin import router as multi_cluster_admin_router
from app.api.chaos_admin import router as chaos_admin_router
from app.api.compliance_admin import router as compliance_admin_router
from app.api.payments import router as payments_router
from app.api.supported_surface_admin import router as supported_surface_admin_router
from app.api.runtime_profiles_admin import router as runtime_profiles_admin_router
from app.api.feature_flags_admin import router as feature_flags_admin_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.runtime_security import validate_runtime_security
from app.db.session import SessionLocal, engine, redis_client
from app.middleware import request_context_middleware, deprecation_middleware
from app.services.billing_scheduler import billing_scheduler_loop
from app.services.routing.commercial_node_heartbeat import commercial_distributed_analytics_loop
from app.services.routing.commercial_federation import sync_federation_clusters
from app.services.routing.commercial_report_scheduler import commercial_report_scheduler_loop
from app.services.models.runtime_integrity_monitor import runtime_integrity_monitor_loop, scan_registered_models
from app.services.routing.commercial_node_heartbeat import resolve_node_identity
from app.services.seed import seed_defaults
from app.services.agents.tool_adapters import register_all_adapters

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()
validate_runtime_security(settings)

# Print operational modes banner
try:
    from app.services.platform.deployment_modes import DeploymentModeService
    mode_svc = DeploymentModeService()
    mode_svc.print_startup_banner(settings)
except Exception as e:
    logger.error(f"Failed to print startup banner: {e}")



def include_optional_routers(app: FastAPI, settings) -> None:
    if settings.distributed_runtime_enabled:
        from app.api.distributed_runtime import router as distributed_runtime_router
        app.include_router(distributed_runtime_router)
    
    if settings.gpu_autoscaling_enabled:
        from app.api.gpu_autoscaling_admin import router as gpu_autoscaling_admin_router
        app.include_router(gpu_autoscaling_admin_router)
    
    if settings.plugin_marketplace_enabled:
        from app.api.plugin_marketplace_admin import router as plugin_marketplace_admin_router
        app.include_router(plugin_marketplace_admin_router)
    
    if settings.managed_control_plane_enabled and settings.deployment_mode == "enterprise_managed":
        from app.api.managed_control_plane import router as managed_control_plane_router
        app.include_router(managed_control_plane_router)

    # Agentic Platform Routers
    # Always include readiness for release gates
    from app.api.agent_readiness_admin import router as agent_readiness_admin_router
    from app.api.platform_ga_admin import router as platform_ga_admin_router
    app.include_router(agent_readiness_admin_router)
    app.include_router(platform_ga_admin_router)

    if settings.agent_runtime_enabled or settings.agent_execution_enabled:
        from app.api.agents import router as agents_router
        from app.api.agents_v1 import router as agents_v1_router
        from app.api.agent_runtime_admin import router as agent_runtime_admin_router
        from app.api.agent_registry_admin import router as agent_registry_admin_router
        from app.api.tenant_agentic_readiness_admin import router as tenant_agentic_readiness_admin_router
        app.include_router(agents_router)
        app.include_router(agents_v1_router)
        app.include_router(agent_runtime_admin_router)
        app.include_router(agent_registry_admin_router)
        app.include_router(tenant_agentic_readiness_admin_router)

    if settings.agent_worker_enabled:
        from app.api.agent_worker_admin import router as agent_worker_admin_router
        app.include_router(agent_worker_admin_router)

    if settings.agent_tool_registry_enabled:
        from app.api.agent_tools_admin import router as agent_tools_admin_router
        app.include_router(agent_tools_admin_router)

    if settings.agent_multi_agent_enabled:
        from app.api.agent_teams_admin import router as agent_teams_admin_router
        app.include_router(agent_teams_admin_router)

    if settings.agent_studio_enabled:
        from app.api.agent_studio_admin import router as agent_studio_admin_router
        app.include_router(agent_studio_admin_router)

    if settings.agent_human_approval_enabled:
        from app.api.agent_approvals_admin import router as agent_approvals_admin_router
        app.include_router(agent_approvals_admin_router)

    if settings.agent_saas_connectors_enabled:
        from app.api.agent_connectors_admin import router as agent_connectors_admin_router
        app.include_router(agent_connectors_admin_router)

    if settings.agent_observability_enabled:
        from app.api.agent_observability_admin import router as agent_observability_admin_router
        app.include_router(agent_observability_admin_router)

    if settings.agent_evals_enabled:
        from app.api.agent_evals_admin import router as agent_evals_admin_router
        app.include_router(agent_evals_admin_router)

    if settings.agent_real_provider_validation_enabled:
        from app.api.provider_validation_admin import router as provider_validation_admin_router
        app.include_router(provider_validation_admin_router)

    if settings.agent_memory_enabled:
        from app.api.agent_memory_admin import router as agent_memory_admin_router
        app.include_router(agent_memory_admin_router)

    if settings.agent_planning_enabled:
        from app.api.agent_tasks_admin import router as agent_tasks_admin_router
        app.include_router(agent_tasks_admin_router)

    if getattr(settings, "commercial_agent_governance_enabled", False):
        from app.api.agent_governance_admin import router as agent_governance_admin_router
        from app.api.commercial_agents_admin import router as commercial_agents_admin_router
        from app.api.commercial_trusted_agents_admin import router as commercial_trusted_agents_admin_router
        from app.api.commercial_agent_audit_portal import router as commercial_agent_audit_portal_router
        app.include_router(agent_governance_admin_router)
        app.include_router(commercial_agents_admin_router)
        app.include_router(commercial_trusted_agents_admin_router)
        app.include_router(commercial_agent_audit_portal_router)

    if settings.agent_stateful_workflows_enabled:
        from app.api.agent_workflows_admin import router as agent_workflows_admin_router
        from app.api.commercial_workflows_admin import router as commercial_workflows_admin_router
        from app.api.commercial_workflow_audit_portal import router as commercial_workflow_audit_portal_router
        from app.api.commercial_workflow_governance_portal import router as commercial_workflow_governance_portal_router
        from app.api.commercial_federated_workflows_admin import router as commercial_federated_workflows_admin_router
        app.include_router(agent_workflows_admin_router)
        app.include_router(commercial_workflows_admin_router)
        app.include_router(commercial_workflow_audit_portal_router)
        app.include_router(commercial_workflow_governance_portal_router)
        app.include_router(commercial_federated_workflows_admin_router)

    if settings.agent_handoffs_enabled:
        from app.api.agent_handoffs_admin import router as agent_handoffs_admin_router
        app.include_router(agent_handoffs_admin_router)

    if settings.agent_marketplace_enabled:
        from app.api.agent_marketplace_admin import router as agent_marketplace_admin_router
        app.include_router(agent_marketplace_admin_router)

    # Enterprise/Commercial Optional Routers
    if getattr(settings, "commercial_qos_enabled", True):
        from app.api.commercial_qos_admin import router as commercial_qos_admin_router
        from app.api.commercial_qos_billing_admin import router as commercial_qos_billing_admin_router
        app.include_router(commercial_qos_admin_router)
        app.include_router(commercial_qos_billing_admin_router, prefix="/admin/billing/qos", tags=["commercial_qos_billing"])

    if getattr(settings, "commercial_compliance_controls_enabled", True):
        from app.api.commercial_compliance_admin import router as commercial_compliance_admin_router
        app.include_router(commercial_compliance_admin_router)

    if getattr(settings, "commercial_revenue_protection_enabled", True):
        from app.api.commercial_revenue_protection_admin import router as commercial_revenue_protection_admin_router
        app.include_router(commercial_revenue_protection_admin_router, prefix="/admin/billing/revenue-protection", tags=["commercial_revenue_protection"])

    if getattr(settings, "commercial_revenue_forecasting_enabled", True):
        from app.api.commercial_revenue_forecasting_admin import router as commercial_revenue_forecasting_admin_router
        app.include_router(commercial_revenue_forecasting_admin_router)

    if getattr(settings, "commercial_revenue_escalations_enabled", True):
        from app.api.commercial_revenue_escalations_admin import router as commercial_revenue_escalations_admin_router
        app.include_router(commercial_revenue_escalations_admin_router, prefix="/admin/billing/revenue-escalations", tags=["commercial_revenue_escalation"])

    if getattr(settings, "commercial_global_routing_enabled", True):
        from app.api.commercial_global_routing_admin import router as commercial_global_routing_admin_router
        from app.api.commercial_global_traffic_admin import router as commercial_global_traffic_admin_router
        app.include_router(commercial_global_routing_admin_router, prefix="/admin/routing/global-router", tags=["commercial_global_routing"])
        app.include_router(commercial_global_traffic_admin_router, prefix="/admin/routing/global-traffic", tags=["commercial_global_traffic"])

    if getattr(settings, "commercial_cross_cluster_forwarding_enabled", True):
        from app.api.commercial_cross_cluster_forwarding_admin import router as commercial_cross_cluster_forwarding_admin_router
        app.include_router(commercial_cross_cluster_forwarding_admin_router, prefix="/admin/routing/cross-cluster-forwarding", tags=["commercial_cross_cluster_forwarding"])

    if getattr(settings, "commercial_geo_routing_enabled", True):
        from app.api.commercial_geo_routing_admin import router as commercial_geo_routing_admin_router
        app.include_router(commercial_geo_routing_admin_router, prefix="/admin/routing/geo-routing", tags=["commercial_geo_routing"])

    if getattr(settings, "commercial_live_balancing_enabled", True):
        from app.api.commercial_live_balancing_admin import router as commercial_live_balancing_admin_router
        app.include_router(commercial_live_balancing_admin_router, prefix="/admin/routing/live-balancing", tags=["commercial_live_balancing"])


async def sync_federation_clusters_loop(stop_event: asyncio.Event) -> None:
    if not settings.commercial_federation_enabled:
        return
    while not stop_event.is_set():
        try:
            async with SessionLocal() as session:
                await sync_federation_clusters(session, sync_type="scheduled", settings=settings)
                await session.commit()
        except Exception as exc:
            logging.getLogger(__name__).exception("federation sync loop failed", extra={"extra_data": {"error": str(exc)}})
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.commercial_federation_sync_interval_seconds)
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Initialize Tool Adapters
    if settings.agent_runtime_enabled or settings.agent_tool_adapters_enabled:
        register_all_adapters()

    if getattr(settings, "create_tables_on_startup", False):
        from app.db.base import Base
        from app.models import api_key, billing_invoice, billing_plan, client, customer_payment, generation_job, inference_backend, model_backend_route, model_registry, pricing_rule, quota_counter, request_log, response_cache, security_event, usage_record, admin_action_log, user_quota_override, rag_document, rag_document_chunk, client_feature_block, rag_usage_event, tts_usage_event, ai_wallet, commercial_routing_event, commercial_routing_config, commercial_report_schedule, commercial_report_delivery_log, commercial_node_heartbeat, commercial_routing_event_ingest, commercial_cluster_aggregate, commercial_capacity, commercial_infra_simulation, commercial_revenue_alert_delivery, commercial_revenue_escalation_policy, commercial_compliance, commercial_governance, commercial_governance_federation, commercial_encryption, commercial_sovereign_governance, commercial_model_supply_chain, commercial_cryptographic_receipts, operations, agents
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        await seed_defaults(session)
        if settings.commercial_model_integrity_monitor_enabled and settings.commercial_model_integrity_boot_scan_enabled:
            await scan_registered_models(session)
    
    # Agent Embedded Worker (dev mode only, off by default)
    agent_worker_task = None
    if settings.agent_embedded_worker_enabled and settings.agent_worker_enabled:
        from app.services.agents.agent_worker import AgentWorkerService
        embedded_worker = AgentWorkerService(worker_id="embedded-dev")
        agent_worker_task = asyncio.create_task(embedded_worker.start())
        logger.info("Embedded agent worker started (AGENT_EMBEDDED_WORKER_ENABLED=true)")

    # Workflow Scheduler
    workflow_scheduler_task = None
    if settings.agent_stateful_workflows_enabled:
        from app.services.agents.workflows.workflow_scheduler import WorkflowScheduler
        scheduler = WorkflowScheduler()
        workflow_scheduler_task = asyncio.create_task(scheduler.start())
        logger.info("Stateful Workflow Scheduler started")

    stop_event = asyncio.Event()
    billing_task = asyncio.create_task(billing_scheduler_loop(stop_event))
    analytics_task = asyncio.create_task(commercial_distributed_analytics_loop(stop_event))
    federation_task = asyncio.create_task(sync_federation_clusters_loop(stop_event))
    report_task = asyncio.create_task(commercial_report_scheduler_loop(stop_event))
    integrity_task = asyncio.create_task(runtime_integrity_monitor_loop(stop_event))
    
    yield
    
    stop_event.set()
    if agent_worker_task:
        agent_worker_task.cancel()
    if workflow_scheduler_task:
        workflow_scheduler_task.cancel()
    billing_task.cancel()
    analytics_task.cancel()
    federation_task.cancel()
    report_task.cancel()
    integrity_task.cancel()
    
    try:
        await billing_task
    except asyncio.CancelledError:
        pass
    try:
        await analytics_task
    except asyncio.CancelledError:
        pass
    try:
        await report_task
    except asyncio.CancelledError:
        pass
    try:
        await federation_task
    except asyncio.CancelledError:
        pass
    try:
        await integrity_task
    except asyncio.CancelledError:
        pass
    await get_inference_proxy().close()
    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(
    title=settings.project_name,
    description="""
Stack local e portátil para servir modelos de linguagem com separação explícita entre Control Plane e Data Plane.
Oferece compatibilidade com a API OpenAI, gestão de cotas, faturamento e roteamento com fallback.
""",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/api-docs",
    redoc_url="/api-redoc",
    openapi_tags=[
        {"name": "system", "description": "Endpoints de saúde e métricas do sistema."},
        {"name": "public", "description": "Endpoints públicos para onboarding e listagem de planos."},
        {"name": "client", "description": "API compatível com OpenAI para consumo dos modelos."},
        {"name": "portal", "description": "API do portal do cliente para gestão de conta e faturas."},
        {"name": "admin", "description": "API administrativa para gestão de clientes, chaves e infraestrutura."},
    ]
)
app.middleware("http")(request_context_middleware)
app.middleware("http")(deprecation_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=bool(settings.cors_origins) and "*" not in settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Token", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)
app.include_router(public_router)
app.include_router(system_router)
app.include_router(admin_router)
app.include_router(admin_models_runtime_router)
app.include_router(admin_rbac_router)
app.include_router(saas_admin_router)
app.include_router(sales_router)
app.include_router(admin_tests_router)
app.include_router(client_router)
app.include_router(rag_router)
app.include_router(client_rag_router)
app.include_router(rag_enterprise_router)
app.include_router(admin_rag_router)
app.include_router(portal_router, prefix="/portal")
app.include_router(account_router, prefix="/v1") # Alias for /account
app.include_router(developer_docs_router)
app.include_router(billing_admin_router)
app.include_router(wallet_admin_router)
app.include_router(providers_router)
app.include_router(routing_admin_router)
app.include_router(routing_test_router)
app.include_router(hybrid_admin_router)
app.include_router(support_admin_router)
app.include_router(abuse_admin_router)
app.include_router(financial_admin_router)
app.include_router(commercial_guardrails_admin_router)
app.include_router(commercial_autonomous_guardrails_admin_router)
app.include_router(commercial_routing_admin_router)
app.include_router(commercial_distributed_analytics_admin_router)
app.include_router(commercial_ha_admin_router)
app.include_router(commercial_federation_admin_router)
app.include_router(billing_reconciliation_admin_router)
app.include_router(commercial_capacity_admin_router)
app.include_router(commercial_infra_admin_router)
app.include_router(supported_surface_admin_router)
app.include_router(runtime_profiles_admin_router)
app.include_router(feature_flags_admin_router)
app.include_router(commercial_policy_governance_admin_router)
app.include_router(commercial_governance_federation_admin_router)
app.include_router(commercial_encryption_admin_router, prefix="/admin/security/encryption", tags=["commercial_encryption"])
app.include_router(commercial_sovereign_governance_admin_router)
app.include_router(commercial_model_supply_chain_admin_router, prefix="/admin/models", tags=["commercial_model_supply_chain"])
app.include_router(commercial_inference_reproducibility_admin_router)
app.include_router(commercial_cryptographic_receipts_admin_router)
app.include_router(commercial_execution_proofs_admin_router)
app.include_router(commercial_execution_proofs_portal_router)
app.include_router(commercial_witness_admin_router)
app.include_router(commercial_witness_portal_router)
app.include_router(commercial_transparency_admin_router)
app.include_router(commercial_attestation_public_router)
app.include_router(commercial_attestation_admin_router)
app.include_router(commercial_attestation_portal_router)
app.include_router(commercial_confidential_runtime_admin_router)
app.include_router(commercial_appliance_admin_router)
app.include_router(commercial_mesh_admin_router)
app.include_router(commercial_mesh_portal_router)
app.include_router(commercial_runtime_fabric_admin_router)
app.include_router(commercial_runtime_fabric_portal_router)
app.include_router(commercial_aiops_admin_router)
app.include_router(commercial_ops_center_admin_router)
app.include_router(commercial_ops_center_router, prefix="/admin/ops-center", tags=["commercial_ops_center"])
app.include_router(commercial_rag_admin_router)
app.include_router(commercial_model_lifecycle_admin_router)
app.include_router(commercial_model_lifecycle_portal_router)
app.include_router(operations_admin_router)
app.include_router(operations_correlation_admin_router, prefix="/admin/operations/correlations", tags=["operations-correlation"])
app.include_router(operations_correlation_portal_router)
app.include_router(operations_remediation_admin_router, prefix="/admin/operations/remediation-plans", tags=["operations-remediation"])
app.include_router(operations_remediation_execution_admin_router, prefix="/admin/operations/remediation-executions", tags=["operations-remediation-execution"])
app.include_router(operations_adapter_sandbox_admin_router, prefix="/admin/operations/adapter-sandbox", tags=["operations-adapter-sandbox"])
app.include_router(operations_adapter_registry_admin_router, prefix="/admin/operations/adapter-registry", tags=["operations-adapter-registry"])
app.include_router(operations_adapter_promotion_admin_router, prefix="/admin/operations/adapter-promotion", tags=["operations-adapter-promotion"])
app.include_router(operations_attestation_admin_router, prefix="/admin/operations", tags=["operations-attestation"])
app.include_router(operations_federation_sync_admin_router, tags=["operations-federation-sync"])
app.include_router(operations_compatibility_admin_router, tags=["operations-compatibility"])
app.include_router(operations_plugin_runtime_admin_router, tags=["operations-plugin-runtime"])
app.include_router(operations_plugin_supply_chain_admin_router, tags=["operations-plugin-supply-chain"])
app.include_router(operations_reproducible_builds_admin_router, tags=["operations-reproducible-builds"])
app.include_router(governance_policy_engine_admin_router)
app.include_router(observability_admin_router)
app.include_router(operations_ux_admin_router)
app.include_router(performance_admin_router)
app.include_router(enterprise_onboarding_admin_router)
app.include_router(admin_onboarding_router)
app.include_router(admin_metrics_router)
app.include_router(multi_cluster_admin_router)
app.include_router(chaos_admin_router)
app.include_router(compliance_admin_router)
app.include_router(payments_router)
app.include_router(pocket_tts_router)
app.include_router(pki_attestation_admin_router)

include_optional_routers(app, settings)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.control_plane_host,
        port=settings.control_plane_port,
        reload=settings.debug,
    )
