import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401

from app.api.deps import get_inference_proxy
from app.api.admin import router as admin_router
from app.api.saas_admin import router as saas_admin_router
from app.api.sales import router as sales_router
from app.api.admin_tests import router as admin_tests_router
from app.api.client import router as client_router
from app.api.rag import router as rag_router, client_rag_router
from app.api.rag_enterprise import router as rag_enterprise_router, admin_router as admin_rag_router
from app.api.portal import router as portal_router
from app.api.public import router as public_router
from app.api.system import router as system_router
from app.api.pocket_tts import router as pocket_tts_router
from app.api.developer_docs import router as developer_docs_router
from app.api.billing_admin import router as billing_admin_router
from app.api.wallet_admin import router as wallet_admin_router
from app.api.providers import router as providers_router
from app.api.routing_admin import router as routing_admin_router
from app.api.routing_test import router as routing_test_router
from app.api.hybrid_admin import router as hybrid_admin_router
from app.api.abuse_admin import router as abuse_admin_router
from app.api.financial_admin import router as financial_admin_router
from app.api.commercial_guardrails_admin import router as commercial_guardrails_admin_router
from app.api.commercial_autonomous_guardrails_admin import router as commercial_autonomous_guardrails_admin_router
from app.api.commercial_routing_admin import router as commercial_routing_admin_router
from app.api.commercial_distributed_analytics_admin import router as commercial_distributed_analytics_admin_router
from app.api.commercial_revenue_forecasting_admin import router as commercial_revenue_forecasting_admin_router
from app.api.commercial_revenue_protection_admin import router as commercial_revenue_protection_admin_router
from app.api.commercial_revenue_escalations_admin import router as commercial_revenue_escalations_admin_router
from app.api.commercial_ha_admin import router as commercial_ha_admin_router
from app.api.commercial_federation_admin import router as commercial_federation_admin_router
from app.api.commercial_global_routing_admin import router as commercial_global_routing_admin_router
from app.api.commercial_global_traffic_admin import router as commercial_global_traffic_admin_router
from app.api.commercial_cross_cluster_forwarding_admin import router as commercial_cross_cluster_forwarding_admin_router
from app.api.commercial_geo_routing_admin import router as commercial_geo_routing_admin_router
from app.api.commercial_live_balancing_admin import router as commercial_live_balancing_admin_router
from app.api.commercial_qos_admin import router as commercial_qos_admin_router
from app.api.commercial_qos_billing_admin import router as commercial_qos_billing_admin_router
from app.api.commercial_capacity_admin import router as commercial_capacity_admin_router
from app.api.commercial_infra_admin import router as commercial_infra_admin_router
from app.api.commercial_compliance_admin import router as commercial_compliance_admin_router
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
from app.api.billing_reconciliation_admin import router as billing_reconciliation_admin_router
from app.api.payments import router as payments_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.runtime_security import validate_runtime_security
from app.db.session import SessionLocal, engine, redis_client
from app.middleware import request_context_middleware
from app.services.billing_scheduler import billing_scheduler_loop
from app.services.routing.commercial_node_heartbeat import commercial_distributed_analytics_loop
from app.services.routing.commercial_federation import sync_federation_clusters
from app.services.routing.commercial_report_scheduler import commercial_report_scheduler_loop
from app.services.models.runtime_integrity_monitor import runtime_integrity_monitor_loop, scan_registered_models
from app.services.routing.commercial_node_heartbeat import resolve_node_identity
from app.services.seed import seed_defaults

configure_logging()
settings = get_settings()
validate_runtime_security(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with SessionLocal() as session:
        await seed_defaults(session)
        if settings.commercial_model_integrity_monitor_enabled and settings.commercial_model_integrity_boot_scan_enabled:
            identity = resolve_node_identity(settings)
            await scan_registered_models(
                session,
                scan_type="boot",
                node_id=identity["node_id"],
                cluster_id=settings.cluster_id,
                settings=settings,
            )
        await session.commit()
    stop_event = asyncio.Event()
    scheduler_task = asyncio.create_task(billing_scheduler_loop(stop_event))
    commercial_report_task = asyncio.create_task(commercial_report_scheduler_loop(stop_event))
    distributed_analytics_task = asyncio.create_task(commercial_distributed_analytics_loop(stop_event))
    federation_task = asyncio.create_task(commercial_federation_loop(stop_event))
    integrity_task = asyncio.create_task(runtime_integrity_monitor_loop(stop_event))
    yield
    stop_event.set()
    scheduler_task.cancel()
    commercial_report_task.cancel()
    distributed_analytics_task.cancel()
    federation_task.cancel()
    integrity_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    try:
        await commercial_report_task
    except asyncio.CancelledError:
        pass
    try:
        await distributed_analytics_task
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
    openapi_tags=[
        {"name": "system", "description": "Endpoints de saúde e métricas do sistema."},
        {"name": "public", "description": "Endpoints públicos para onboarding e listagem de planos."},
        {"name": "client", "description": "API compatível com OpenAI para consumo dos modelos."},
        {"name": "portal", "description": "API do portal do cliente para gestão de conta e faturas."},
        {"name": "admin", "description": "API administrativa para gestão de clientes, chaves e infraestrutura."},
    ]
)
app.middleware("http")(request_context_middleware)
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
app.include_router(saas_admin_router)
app.include_router(sales_router)
app.include_router(admin_tests_router)
app.include_router(client_router)
app.include_router(rag_router)
app.include_router(client_rag_router)
app.include_router(rag_enterprise_router)
app.include_router(admin_rag_router)
app.include_router(portal_router, prefix="/portal")
app.include_router(portal_router, prefix="/v1") # Alias for /account
app.include_router(developer_docs_router)
app.include_router(billing_admin_router)
app.include_router(wallet_admin_router)
app.include_router(providers_router)
app.include_router(routing_admin_router)
app.include_router(routing_test_router)
app.include_router(hybrid_admin_router)
app.include_router(abuse_admin_router)
app.include_router(financial_admin_router)
app.include_router(commercial_guardrails_admin_router)
app.include_router(commercial_autonomous_guardrails_admin_router)
app.include_router(commercial_routing_admin_router)
app.include_router(commercial_distributed_analytics_admin_router)
app.include_router(commercial_revenue_forecasting_admin_router)
app.include_router(commercial_revenue_protection_admin_router)
app.include_router(commercial_revenue_escalations_admin_router)
app.include_router(commercial_ha_admin_router)
app.include_router(commercial_federation_admin_router)
app.include_router(commercial_global_routing_admin_router, prefix="/admin/routing/global-router", tags=["commercial_global_routing"])
app.include_router(commercial_global_traffic_admin_router, prefix="/admin/routing/global-traffic", tags=["commercial_global_traffic"])
app.include_router(commercial_cross_cluster_forwarding_admin_router, prefix="/admin/routing/cross-cluster-forwarding", tags=["commercial_cross_cluster_forwarding"])
app.include_router(commercial_geo_routing_admin_router, prefix="/admin/routing/geo-routing", tags=["commercial_geo_routing"])
app.include_router(commercial_live_balancing_admin_router, prefix="/admin/routing/live-balancing", tags=["commercial_live_balancing"])
app.include_router(commercial_qos_admin_router)
app.include_router(commercial_qos_billing_admin_router, prefix="/admin/billing/qos", tags=["commercial_qos_billing"])
app.include_router(billing_reconciliation_admin_router)
app.include_router(commercial_capacity_admin_router)
app.include_router(commercial_infra_admin_router)
app.include_router(commercial_compliance_admin_router)
app.include_router(commercial_policy_governance_admin_router)
app.include_router(commercial_governance_federation_admin_router)
app.include_router(commercial_encryption_admin_router, prefix="/admin/security/encryption", tags=["commercial_encryption"])
app.include_router(commercial_sovereign_governance_admin_router)
app.include_router(commercial_model_supply_chain_admin_router)
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
app.include_router(commercial_agents_admin_router)
app.include_router(commercial_trusted_agents_admin_router)
app.include_router(commercial_agent_audit_portal_router)
app.include_router(commercial_workflows_admin_router)
app.include_router(commercial_workflow_audit_portal_router)
app.include_router(commercial_workflow_governance_portal_router)
app.include_router(commercial_federated_workflows_admin_router)
app.include_router(commercial_appliance_admin_router)
app.include_router(commercial_mesh_admin_router)
app.include_router(commercial_mesh_portal_router)
app.include_router(commercial_runtime_fabric_admin_router)
app.include_router(commercial_runtime_fabric_portal_router)
app.include_router(commercial_aiops_admin_router)
app.include_router(commercial_ops_center_admin_router)
app.include_router(commercial_ops_center_router)
app.include_router(commercial_rag_admin_router)
app.include_router(commercial_model_lifecycle_admin_router)
app.include_router(commercial_model_lifecycle_portal_router)
app.include_router(payments_router)
app.include_router(pocket_tts_router)


async def commercial_federation_loop(stop_event) -> None:
    cfg = get_settings()
    if not cfg.commercial_federation_enabled:
        return
    while not stop_event.is_set():
        try:
            if cfg.commercial_federation_mode in {"push", "hybrid"} and cfg.commercial_federation_allow_push:
                async with SessionLocal() as session:
                    await sync_federation_clusters(session, sync_type="push", settings=cfg)
                    await session.commit()
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=cfg.commercial_federation_sync_interval_seconds)
        except Exception:
            continue

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
