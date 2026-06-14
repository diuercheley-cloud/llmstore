import logging
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from app.services.auth import require_admin
from .router_manifest import (
    ADMIN_ROUTERS,
    COMMERCIAL_ROUTERS,
    OPERATIONS_ROUTERS,
    PORTAL_ROUTERS,
    CORE_ROUTERS,
    CLIENT_ROUTERS,
    RAG_ROUTERS,
    ROUTING_ROUTERS,
    AUTH_ROUTERS,
)

logger = logging.getLogger(__name__)

def _is_admin_path(path: str) -> bool:
    return path.startswith(("/admin", "/api/admin", "/api/v1/admin"))


def _secure_include_router(app: FastAPI):
    original_include_router = app.include_router

    def include_router(router, **kwargs):
        include_prefix = kwargs.get("prefix", "")
        paths = [
            f"{include_prefix}{route.path}"
            for route in router.routes
            if isinstance(route, APIRoute)
        ]
        if paths and all(_is_admin_path(path) for path in paths):
            dependencies = list(kwargs.get("dependencies") or [])
            if not any(getattr(dep, "dependency", None) is require_admin for dep in dependencies):
                dependencies.append(Depends(require_admin))
            kwargs["dependencies"] = dependencies
        return original_include_router(router, **kwargs)

    return include_router


def register_routers(app: FastAPI, settings) -> None:
    app.include_router = _secure_include_router(app)
    all_router_lists = [
        ADMIN_ROUTERS,
        COMMERCIAL_ROUTERS,
        OPERATIONS_ROUTERS,
        PORTAL_ROUTERS,
        CORE_ROUTERS,
        CLIENT_ROUTERS,
        RAG_ROUTERS,
        ROUTING_ROUTERS,
        AUTH_ROUTERS,
    ]
    
    for router_list in all_router_lists:
        for router_info in router_list:
            app.include_router(router_info["router"], **router_info["kwargs"])
            
    include_optional_routers(app, settings)

def include_optional_routers(app: FastAPI, settings) -> None:
    def _flag(name: str, default: bool = False) -> bool:
        return bool(getattr(settings, name, default))

    if _flag("agent_debugger_enabled"):
        from app.api.agent_debugger_admin import router as agent_debugger_admin_router
        app.include_router(agent_debugger_admin_router, prefix="/api/v1/admin/debugger", tags=["agent-debugger"])

    from app.api.prompt_admin import router as prompt_admin_router
    app.include_router(prompt_admin_router, prefix="/api/v1/admin/prompts", tags=["prompt-management"])

    from app.api.agent_analytics_admin import router as agent_analytics_admin_router
    app.include_router(agent_analytics_admin_router, prefix="/api/v1/admin/agents/analytics", tags=["agent-analytics"])

    from app.api.kb_admin import router as kb_admin_router
    app.include_router(kb_admin_router, prefix="/api/v1/admin/kb", tags=["knowledge-base"])

    from app.api.agent_service import router as agent_service_router
    app.include_router(agent_service_router, prefix="/api/v1/agent-service", tags=["agent-as-a-service"])

    from app.api.agent_deployments import admin_router as agent_deployments_admin_router
    from app.api.agent_deployments import public_router as agent_deployments_public_router
    app.include_router(agent_deployments_admin_router)
    app.include_router(agent_deployments_public_router)

    if _flag("distributed_runtime_enabled"):
        from app.api.distributed_runtime import router as distributed_runtime_router
        app.include_router(distributed_runtime_router)
    
    if _flag("gpu_autoscaling_enabled"):
        from app.api.gpu_autoscaling_admin import router as gpu_autoscaling_admin_router
        app.include_router(gpu_autoscaling_admin_router)

    from app.api.alert_webhooks import router as alert_webhooks_router
    app.include_router(alert_webhooks_router, prefix="/api/v1", tags=["alerting"])

    if _flag("a2a_enabled"):
        from app.api.a2a_router import router as a2a_router
        app.include_router(a2a_router, prefix="/api/v1", tags=["a2a-protocol"])
    
    if _flag("plugin_marketplace_enabled"):
        from app.api.plugin_marketplace_admin import router as plugin_marketplace_admin_router
        app.include_router(plugin_marketplace_admin_router)
    
    if _flag("managed_control_plane_enabled") and getattr(settings, "deployment_mode", None) in ("enterprise_managed", "managed_control_plane"):
        from app.api.managed_control_plane import router as managed_control_plane_router
        app.include_router(managed_control_plane_router)

    # Agentic Platform Routers
    # Always include readiness for release gates
    from app.api.admin_readiness import router as admin_readiness_router
    from app.api.agent_capability_catalog_admin import plugin_router as plugin_admin_router
    from app.api.agent_capability_catalog_admin import router as capability_catalog_admin_router
    from app.api.agent_execution_admin import router as agent_execution_admin_router
    from app.api.agent_readiness_admin import router as agent_readiness_admin_router
    from app.api.agent_tools_admin import router as agent_tools_admin_router
    from app.api.platform_ga_admin import router as platform_ga_admin_router
    app.include_router(agent_readiness_admin_router)
    app.include_router(admin_readiness_router)
    app.include_router(capability_catalog_admin_router)
    app.include_router(plugin_admin_router)
    app.include_router(agent_execution_admin_router)
    app.include_router(agent_tools_admin_router)
    app.include_router(platform_ga_admin_router)

    from app.api.agent_a2a import router as agent_a2a_router
    app.include_router(agent_a2a_router)

    from app.api.agent_sessions import router as agent_sessions_router
    app.include_router(agent_sessions_router)

    from app.api.agents_ws import router as agents_ws_router
    app.include_router(agents_ws_router)

    from app.api.billing_payments import router as billing_payments_router
    app.include_router(billing_payments_router)

    from app.api.multimodal import router as optional_multimodal_router
    from app.api.multimodal_v2 import router as multimodal_v2_router
    app.include_router(optional_multimodal_router)
    app.include_router(multimodal_v2_router)

    if _flag("agentic_router_v2_enabled"):
        from app.api.agent_routing_admin import router as agent_routing_admin_router
        app.include_router(agent_routing_admin_router)

    from app.api.agent_cicd_admin import router as agent_cicd_admin_router
    app.include_router(agent_cicd_admin_router)
    from app.api.agents import router as agents_router
    from app.api.agents_v1 import router as agents_v1_router
    from app.api.audit import router as audit_router
    app.include_router(agents_router)
    app.include_router(agents_v1_router)
    app.include_router(audit_router)

    if _flag("agent_runtime_enabled") or _flag("agent_execution_enabled"):
        from app.api.agent_environments_admin import router as agent_environments_admin_router
        from app.api.agent_registry_admin import router as agent_registry_admin_router
        from app.api.agent_runtime_admin import router as agent_runtime_admin_router
        from app.api.tenant_agentic_readiness_admin import (
            router as tenant_agentic_readiness_admin_router,
        )
        app.include_router(agent_runtime_admin_router)
        app.include_router(agent_registry_admin_router)
        app.include_router(tenant_agentic_readiness_admin_router)
        app.include_router(agent_environments_admin_router)

    if _flag("agent_assistants_api_enabled"):
        from app.api.assistants_v1 import router as assistants_v1_router
        app.include_router(assistants_v1_router)

    if _flag("agent_batch_api_enabled"):
        from app.api.batches_v1 import router as batches_v1_router
        app.include_router(batches_v1_router)

    if _flag("agent_worker_enabled"):
        from app.api.agent_worker_admin import router as agent_worker_admin_router
        app.include_router(agent_worker_admin_router)

    if _flag("agent_multi_agent_enabled"):
        from app.api.agent_teams_admin import router as agent_teams_admin_router
        app.include_router(agent_teams_admin_router)

    if _flag("agent_studio_enabled"):
        from app.api.agent_studio_admin import router as agent_studio_admin_router
        app.include_router(agent_studio_admin_router)
        if _flag("agent_studio_ga_enabled"):
            from app.api.agent_studio_ga_admin import router as agent_studio_ga_admin_router
            app.include_router(agent_studio_ga_admin_router, prefix="/api/v1")

    if _flag("agent_human_approval_enabled"):
        from app.api.agent_approvals_admin import router as agent_approvals_admin_router
        app.include_router(agent_approvals_admin_router)
    if _flag("agent_approval_portal_enabled"):
        from app.api.agent_approval_portal import router as agent_approval_portal_router
        app.include_router(agent_approval_portal_router)

    from app.api.admin_critical_approvals import router as admin_critical_approvals_router
    app.include_router(admin_critical_approvals_router)

    if _flag("agent_saas_connectors_enabled"):
        from app.api.agent_connectors_admin import router as agent_connectors_admin_router
        app.include_router(agent_connectors_admin_router)

    if _flag("agent_observability_enabled"):
        from app.api.agent_observability_admin import router as agent_observability_admin_router
        app.include_router(agent_observability_admin_router)

    if _flag("agent_evals_enabled"):
        from app.api.agent_evals_admin import router as agent_evals_admin_router
        app.include_router(agent_evals_admin_router)

    if _flag("agent_real_provider_validation_enabled"):
        from app.api.provider_validation_admin import router as provider_validation_admin_router
        app.include_router(provider_validation_admin_router)

    if _flag("agent_memory_enabled"):
        from app.api.agent_memory_admin import router as agent_memory_admin_router
        app.include_router(agent_memory_admin_router)

    if _flag("agent_cognitive_memory_enabled"):
        from app.api.agent_cognitive_memory_admin import (
            router as agent_cognitive_memory_admin_router,
        )
        app.include_router(agent_cognitive_memory_admin_router)

    if _flag("agent_planning_enabled"):
        from app.api.agent_tasks_admin import router as agent_tasks_admin_router
        app.include_router(agent_tasks_admin_router)

    if getattr(settings, "commercial_agent_governance_enabled", False):
        from app.api.agent_governance_admin import router as agent_governance_admin_router
        from app.api.commercial_agent_audit_portal import (
            router as commercial_agent_audit_portal_router,
        )
        from app.api.commercial_agents_admin import router as commercial_agents_admin_router
        from app.api.commercial_trusted_agents_admin import (
            router as commercial_trusted_agents_admin_router,
        )
        app.include_router(agent_governance_admin_router)
        app.include_router(commercial_agents_admin_router)
        app.include_router(commercial_trusted_agents_admin_router)
        app.include_router(commercial_agent_audit_portal_router)

    if _flag("agent_stateful_workflows_enabled"):
        from app.api.agent_workflows_admin import router as agent_workflows_admin_router
        from app.api.commercial_federated_workflows_admin import (
            router as commercial_federated_workflows_admin_router,
        )
        from app.api.commercial_workflow_audit_portal import (
            router as commercial_workflow_audit_portal_router,
        )
        from app.api.commercial_workflow_governance_portal import (
            router as commercial_workflow_governance_portal_router,
        )
        from app.api.commercial_workflows_admin import router as commercial_workflows_admin_router
        app.include_router(agent_workflows_admin_router)
        app.include_router(commercial_workflows_admin_router)
        app.include_router(commercial_workflow_audit_portal_router)
        app.include_router(commercial_workflow_governance_portal_router)
        app.include_router(commercial_federated_workflows_admin_router)

    if _flag("agent_handoffs_enabled"):
        from app.api.agent_handoffs_admin import router as agent_handoffs_admin_router
        app.include_router(agent_handoffs_admin_router)

    if _flag("agent_marketplace_enabled"):
        from app.api.agent_marketplace_admin import router as agent_marketplace_admin_router
        app.include_router(agent_marketplace_admin_router)
        from app.api.agent_marketplace_public import router as agent_marketplace_public_router
        app.include_router(agent_marketplace_public_router, prefix="/api/v1")

    if _flag("agent_event_driven_enabled"):
        from app.api.agent_events import router as agent_events_router
        from app.api.agent_events_admin import router as agent_events_admin_router
        app.include_router(agent_events_admin_router)
        app.include_router(agent_events_router)

    if _flag("agent_iam_enabled"):
        from app.api.agent_iam_admin import router as agent_iam_admin_router
        app.include_router(agent_iam_admin_router)

    if _flag("agent_code_interpreter_enabled"):
        from app.api.agent_code_interpreter_admin import (
            router as agent_code_interpreter_admin_router,
        )
        app.include_router(agent_code_interpreter_admin_router)

    from app.api.agent_mcp_admin import admin_router as agent_mcp_admin_router
    from app.api.agent_mcp_admin import server_router as agent_mcp_server_router
    app.include_router(agent_mcp_admin_router)
    app.include_router(agent_mcp_server_router)

    if _flag("agent_auto_optimization_enabled"):
        from app.api.agent_optimization_admin import router as agent_optimization_admin_router
        app.include_router(agent_optimization_admin_router)

    if _flag("agent_optimizer_tournaments_enabled"):
        from app.api.agent_optimization_tournaments_admin import (
            router as agent_optimization_tournaments_admin_router,
        )
        app.include_router(agent_optimization_tournaments_admin_router)

    # Agent Shared Workspace and Artifacts Routers
    from app.api.agent_workspace_admin import router as agent_workspace_admin_router
    app.include_router(agent_workspace_admin_router)

    if _flag("agent_canary_agents_enabled"):
        from app.api.agent_canary_admin import router as agent_canary_admin_router
        app.include_router(agent_canary_admin_router)

    if _flag("agent_cognitive_loopback_enabled"):
        from app.api.agent_cognitive_loopback_admin import (
            router as agent_cognitive_loopback_admin_router,
        )
        app.include_router(agent_cognitive_loopback_admin_router)

    if _flag("agent_federated_memory_enabled"):
        from app.api.agent_federated_memory_admin import (
            router as agent_federated_memory_admin_router,
        )
        app.include_router(agent_federated_memory_admin_router)

    if _flag("agent_sab_enabled"):
        from app.api.agent_sab_admin import router as agent_sab_admin_router
        app.include_router(agent_sab_admin_router)

    if _flag("agent_uncertainty_detection_enabled"):
        from app.api.agent_uncertainty_admin import router as agent_uncertainty_admin_router
        app.include_router(agent_uncertainty_admin_router)

    # Enterprise/Commercial Optional Routers
    if getattr(settings, "commercial_qos_enabled", True):
        from app.api.commercial_qos_admin import router as commercial_qos_admin_router
        from app.api.commercial_qos_billing_admin import (
            router as commercial_qos_billing_admin_router,
        )
        app.include_router(commercial_qos_admin_router)
        app.include_router(commercial_qos_billing_admin_router, prefix="/admin/billing/qos", tags=["commercial_qos_billing"])

    if getattr(settings, "commercial_compliance_controls_enabled", True):
        from app.api.commercial_compliance_admin import router as commercial_compliance_admin_router
        app.include_router(commercial_compliance_admin_router)

    if getattr(settings, "commercial_revenue_protection_enabled", True):
        from app.api.commercial_revenue_protection_admin import (
            router as commercial_revenue_protection_admin_router,
        )
        app.include_router(commercial_revenue_protection_admin_router, tags=["commercial_revenue_protection"])

    if getattr(settings, "commercial_revenue_forecasting_enabled", True):
        from app.api.commercial_revenue_forecasting_admin import (
            router as commercial_revenue_forecasting_admin_router,
        )
        app.include_router(commercial_revenue_forecasting_admin_router)

    if getattr(settings, "commercial_revenue_escalations_enabled", True):
        from app.api.commercial_revenue_escalations_admin import (
            router as commercial_revenue_escalations_admin_router,
        )
        app.include_router(commercial_revenue_escalations_admin_router, tags=["commercial_revenue_escalation"])

    if getattr(settings, "commercial_global_routing_enabled", True):
        from app.api.commercial_global_routing_admin import (
            router as commercial_global_routing_admin_router,
        )
        from app.api.commercial_global_traffic_admin import (
            router as commercial_global_traffic_admin_router,
        )
        app.include_router(commercial_global_routing_admin_router, prefix="/admin/routing/global-router", tags=["commercial_global_routing"])
        app.include_router(commercial_global_traffic_admin_router, prefix="/admin/routing/global-traffic", tags=["commercial_global_traffic"])

    if getattr(settings, "commercial_cross_cluster_forwarding_enabled", True):
        from app.api.commercial_cross_cluster_forwarding_admin import (
            router as commercial_cross_cluster_forwarding_admin_router,
        )
        app.include_router(commercial_cross_cluster_forwarding_admin_router, prefix="/admin/routing/cross-cluster-forwarding", tags=["commercial_cross_cluster_forwarding"])

    if getattr(settings, "commercial_geo_routing_enabled", True):
        from app.api.commercial_geo_routing_admin import (
            router as commercial_geo_routing_admin_router,
        )
        app.include_router(commercial_geo_routing_admin_router, prefix="/admin/routing/geo-routing", tags=["commercial_geo_routing"])

    if getattr(settings, "commercial_live_balancing_enabled", True):
        from app.api.commercial_live_balancing_admin import (
            router as commercial_live_balancing_admin_router,
        )
        app.include_router(commercial_live_balancing_admin_router, prefix="/admin/routing/live-balancing", tags=["commercial_live_balancing"])

    # Agent Tool Synthesis and Sandbox Routers
    from app.api.agent_tool_synthesis_admin import admin_router as tool_synthesis_admin_router
    from app.api.agent_tool_synthesis_admin import public_router as tool_synthesis_public_router
    from app.api.agent_tool_synthesis_admin import sandbox_router as tool_synthesis_sandbox_router
    app.include_router(tool_synthesis_admin_router, prefix="/admin/agents/tool-synthesis", tags=["agent_tool_synthesis"])
    app.include_router(tool_synthesis_sandbox_router, prefix="/admin/agents/sandbox", tags=["agent_sandbox"])
    app.include_router(tool_synthesis_public_router, prefix="/agents/tools/generated", tags=["agent_generated_tools"])

    # Agent Knowledge Graph Routers
    if _flag("agent_knowledge_graph_enabled"):
        from app.api.agent_knowledge_graph_admin import admin_router as kg_admin_router
        from app.api.agent_knowledge_graph_admin import public_router as kg_public_router
        app.include_router(kg_admin_router)
        app.include_router(kg_public_router)

    # Agent Graph (DAG-based orchestration)
    from app.api.agent_graph_admin import router as agent_graph_router
    app.include_router(agent_graph_router)

    # Agent Compatibility Layer Router
    from app.api.agent_compatibility_admin import router as agent_compatibility_admin_router
    app.include_router(agent_compatibility_admin_router)
