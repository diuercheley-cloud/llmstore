import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.ai_wallet import AiWallet
from app.models.rag_document import RAGDocument
from app.models.rag_document_chunk import RAGDocumentChunk
from app.models.rag_collection import RAGCollection
from app.models.commercial_rag_vault import (
    CommercialRAGDocument,
    CommercialRAGLegalHold,
    CommercialRAGPoisoningAlert,
    CommercialRAGRetrievalAudit,
    CommercialRAGVault,
)
from app.models.commercial_retrieval_proofs import (
    CommercialContextLineage,
    CommercialRetrievalProof,
    CommercialRetrievalReplayRecord,
)
from app.models.request_financial import RequestFinancial
from app.services.auth import require_admin
from app.services.billing.pricing_engine import get_provider_pricing_config

from app.services.providers.registry import (
    get_all_provider_health,
    get_all_provider_statuses,
    get_providers,
)
from app.services.routing.smart_router import get_smart_router

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/admin/hybrid",
    tags=["admin", "hybrid"],
    dependencies=[Depends(require_admin)],
)


def _mask(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


@router.get("/summary")
async def hybrid_summary(
    session: AsyncSession = Depends(get_db_session),
):
    settings_local = get_settings()

    total_requests = 0
    local_requests = 0
    cloud_requests = 0
    cache_hit_count = 0
    cache_miss_count = 0

    try:
        count_result = await session.execute(select(func.count(RequestFinancial.id)))
        total_requests = count_result.scalar() or 0
    except Exception:
        pass

    try:
        local_count = await session.execute(
            select(func.count(RequestFinancial.id)).where(
                RequestFinancial.provider.in_(["local", "lmstudio", "mock"])
            )
        )
        local_requests = local_count.scalar() or 0
    except Exception:
        pass

    cloud = total_requests - local_requests
    cloud_requests = max(cloud, 0)

    try:
        hit = await session.execute(
            select(func.count(RequestFinancial.id)).where(RequestFinancial.cache_hit == True)
        )
        cache_hit_count = hit.scalar() or 0
        miss = await session.execute(
            select(func.count(RequestFinancial.id)).where(RequestFinancial.cache_hit == False)
        )
        cache_miss_count = miss.scalar() or 0
    except Exception:
        pass

    cache_hit_rate = (cache_hit_count / (cache_hit_count + cache_miss_count) * 100) if (cache_hit_count + cache_miss_count) > 0 else 0.0

    provider_cost_brl = 0.0
    customer_revenue_brl = 0.0
    gross_profit_brl = 0.0
    margin_percent = 0.0

    try:
        cost = await session.execute(select(func.sum(RequestFinancial.provider_cost_brl)))
        provider_cost_brl = float(cost.scalar() or 0.0)
    except Exception:
        pass

    try:
        revenue = await session.execute(select(func.sum(RequestFinancial.customer_price_brl)))
        customer_revenue_brl = float(revenue.scalar() or 0.0)
    except Exception:
        pass

    try:
        profit = await session.execute(select(func.sum(RequestFinancial.gross_profit_brl)))
        gross_profit_brl = float(profit.scalar() or 0.0)
    except Exception:
        pass

    margin_percent = (gross_profit_brl / customer_revenue_brl * 100) if customer_revenue_brl > 0 else 0.0

    active_wallets = 0
    low_balance_clients = 0
    try:
        wallets_active = await session.execute(
            select(func.count(AiWallet.id)).where(AiWallet.status == "active")
        )
        active_wallets = wallets_active.scalar() or 0
        low = await session.execute(
            select(func.count(AiWallet.id)).where(
                AiWallet.status == "active", AiWallet.balance_brl < 10.0
            )
        )
        low_balance_clients = low.scalar() or 0
    except Exception:
        pass

    providers_enabled = 0
    providers_configured = 0
    try:
        for p in get_providers().values():
            if p.enabled:
                providers_enabled += 1
            if p.configured:
                providers_configured += 1
    except Exception:
        pass

    warnings = []
    critical_failures = []

    for pid, p in get_providers().items():
        if p.provider_type.value in ("openai", "anthropic", "deepseek", "openrouter"):
            if p.enabled and not p.configured:
                warnings.append(f"Cloud provider '{pid}' enabled but missing API key")
            if settings_local.cloud_providers_enabled and not p.configured:
                warnings.append(f"Cloud provider '{pid}' enabled via CLOUD_PROVIDERS_ENABLED but no API key configured")

    if not settings_local.cloud_providers_enabled:
        warnings.append("Cloud providers are disabled (CLOUD_PROVIDERS_ENABLED=false)")

    wallets_disabled_count = 0
    try:
        wallets_disabled = await session.execute(
            select(func.count(AiWallet.id)).where(AiWallet.status != "active")
        )
        wallets_disabled_count = wallets_disabled.scalar() or 0
    except Exception:
        pass

    if wallets_disabled_count > 0:
        warnings.append(f"{wallets_disabled_count} wallet(s) are not active")

    pricing_config = get_provider_pricing_config()
    providers_cfg = pricing_config.get("providers", {})
    for pid, cfg in providers_cfg.items():
        if not cfg.get("pricing_configured", False):
            warnings.append(f"Pricing not configured for provider '{pid}'")

    try:
        provider_health = await get_all_provider_health()
        for ph in provider_health:
            if ph.healthy is False:
                critical_failures.append(f"Provider '{ph.provider_id}' is unhealthy")
    except Exception:
        pass

    cloud_enabled = settings_local.cloud_providers_enabled
    local_providers = {"local", "lmstudio", "mock"}
    all_providers_dict = get_providers()
    local_first = any(
        p.enabled and p.configured and p.provider_id in local_providers
        for p in all_providers_dict.values()
    )

    return {
        "total_requests": total_requests,
        "local_requests": local_requests,
        "cloud_requests": cloud_requests,
        "cache_hit_rate": round(cache_hit_rate, 2),
        "provider_cost_brl": round(provider_cost_brl, 2),
        "customer_revenue_brl": round(customer_revenue_brl, 2),
        "gross_profit_brl": round(gross_profit_brl, 2),
        "margin_percent": round(margin_percent, 2),
        "active_wallets": active_wallets,
        "low_balance_clients": low_balance_clients,
        "providers_enabled": providers_enabled,
        "providers_configured": providers_configured,
        "cloud_enabled": cloud_enabled,
        "local_first": local_first,
        "warnings": warnings,
        "critical_failures": critical_failures,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/providers")
async def hybrid_providers():
    statuses = get_all_provider_statuses()
    result = []
    for s in statuses:
        masked_key = None
        p = get_providers().get(s.provider_id)
        if p and hasattr(p, "api_key") and p.api_key:
            masked_key = _mask(p.api_key)
        result.append({
            "provider_id": s.provider_id,
            "provider_type": s.provider_type,
            "enabled": s.enabled,
            "configured": s.configured,
            "healthy": s.healthy,
            "capabilities": s.capabilities.model_dump(),
            "masked_api_key": masked_key,
        })
    return result


@router.get("/routing")
async def hybrid_routing():
    smart_router = get_smart_router()
    policy = smart_router.get_policy()
    decisions = smart_router.get_last_decisions(limit=20)
    return {
        "default_strategy": policy.get("default_strategy", "local_first"),
        "allow_cloud_fallback": policy.get("allow_cloud_fallback", False),
        "cloud_providers_enabled": settings.cloud_providers_enabled,
        "fallback_order": policy.get("fallback_order", []),
        "tenant_policy_overrides": policy.get("tenant_policy_overrides", {}),
        "last_decisions": [
            {
                "id": d.get("id"),
                "timestamp": d.get("timestamp"),
                "requested_model": d.get("requested_model"),
                "selected_provider": d.get("selected_provider"),
                "routing_strategy": d.get("routing_strategy"),
                "fallback_used": d.get("fallback_used", False),
                "cloud_used": d.get("cloud_used", False),
                "estimated_cost_brl": d.get("estimated_cost_brl", 0.0),
            }
            for d in decisions
        ],
    }


@router.get("/financials")
async def hybrid_financials(
    session: AsyncSession = Depends(get_db_session),
):
    provider_costs = []
    try:
        stmt = (
            select(
                RequestFinancial.provider,
                func.count(RequestFinancial.id).label("total_requests"),
                func.sum(RequestFinancial.provider_cost_brl).label("total_provider_cost_brl"),
                func.sum(RequestFinancial.customer_price_brl).label("total_customer_price_brl"),
                func.sum(RequestFinancial.gross_profit_brl).label("total_gross_profit_brl"),
                func.avg(RequestFinancial.margin_percent).label("avg_margin_percent"),
            )
            .group_by(RequestFinancial.provider)
            .order_by(func.count(RequestFinancial.id).desc())
        )
        rows = (await session.execute(stmt)).all()
        for row in rows:
            provider_costs.append({
                "provider": row.provider,
                "total_requests": int(row.total_requests),
                "total_provider_cost_brl": round(float(row.total_provider_cost_brl or 0.0), 2),
                "total_customer_price_brl": round(float(row.total_customer_price_brl or 0.0), 2),
                "total_gross_profit_brl": round(float(row.total_gross_profit_brl or 0.0), 2),
                "avg_margin_percent": round(float(row.avg_margin_percent), 2) if row.avg_margin_percent is not None else None,
            })
    except Exception:
        pass

    pricing_config = get_provider_pricing_config()
    costs_config = pricing_config.get("providers", {})

    return {
        "provider_costs": provider_costs,
        "costs_config": {
            pid: {
                "cost_usd_per_1k_prompt": float(cfg.get("cost_usd_per_1k_prompt", 0.0)),
                "cost_usd_per_1k_completion": float(cfg.get("cost_usd_per_1k_completion", 0.0)),
                "pricing_configured": cfg.get("pricing_configured", False),
            }
            for pid, cfg in costs_config.items()
        },
    }


@router.get("/cache")
async def hybrid_cache(
    session: AsyncSession = Depends(get_db_session),
):
    from app.models.response_cache import ResponseCache
    from app.models.semantic_cache_entry import SemanticCacheEntry

    exact_entries = 0
    semantic_entries = 0
    try:
        exact_count = await session.execute(select(func.count(ResponseCache.id)))
        exact_entries = exact_count.scalar() or 0
    except Exception:
        pass
    try:
        semantic_count = await session.execute(select(func.count(SemanticCacheEntry.id)))
        semantic_entries = semantic_count.scalar() or 0
    except Exception:
        pass

    from app.models.request_log import RequestLog
    exact_hits = 0
    exact_misses = 0
    try:
        hits = await session.execute(
            select(func.count(RequestLog.id)).where(RequestLog.cache_hit == True)
        )
        exact_hits = hits.scalar() or 0
    except Exception:
        pass
    try:
        misses = await session.execute(
            select(func.count(RequestLog.id)).where(RequestLog.cache_hit == False)
        )
        exact_misses = misses.scalar() or 0
    except Exception:
        pass

    return {
        "exact_cache_enabled": settings.response_cache_enabled,
        "semantic_cache_enabled": settings.semantic_cache_enabled,
        "ttl_seconds": settings.response_cache_ttl_seconds,
        "exact_hits": exact_hits,
        "exact_misses": exact_misses,
        "semantic_hits": 0,
        "semantic_misses": 0,
        "total_entries": exact_entries,
        "memory_estimate_bytes": 0,
    }


@router.get("/wallets")
async def hybrid_wallets(
    session: AsyncSession = Depends(get_db_session),
):
    wallets = []
    try:
        result = await session.execute(
            select(AiWallet).order_by(AiWallet.balance_brl.asc())
        )
        rows = result.scalars().all()
        for w in rows:
            wallets.append({
                "wallet_id": str(w.id),
                "client_id": str(w.client_id),
                "currency": w.currency,
                "balance_brl": float(w.balance_brl),
                "reserved_brl": float(w.reserved_brl),
                "available_brl": float(w.balance_brl - w.reserved_brl),
                "status": w.status,
            })
    except Exception:
        pass
    return wallets


@router.get("/rag")
async def hybrid_rag(
    session: AsyncSession = Depends(get_db_session),
):
    result = {
        "rag_enabled": settings.rag_enabled,
        "regulated_rag_vault_enabled": settings.commercial_rag_vault_enabled,
        "embedding_provider": settings.rag_embedding_provider,
        "total_documents": 0,
        "total_chunks": 0,
        "total_collections": 0,
        "total_storage_bytes": 0,
        "clients_with_rag": 0,
        "documents_by_status": {},
        "regulated_rag_vault": {
            "vaults": 0,
            "retrievals": 0,
            "poisoning_alerts": 0,
            "acl_violations": 0,
            "legal_holds": 0,
            "signed_documents": 0,
            "confidential_retrieval_percent": 0.0,
        },
        "context_lineage_retrieval_proofs": {
            "retrieval_proofs": 0,
            "lineage_nodes": 0,
            "replay_records": 0,
            "verified_proofs": 0,
            "drift_events": 0,
        },
    }
    if not settings.rag_enabled:
        return result

    try:
        total_docs = await session.execute(select(func.count(RAGDocument.id)))
        result["total_documents"] = total_docs.scalar() or 0
    except Exception:
        pass

    try:
        total_chunks = await session.execute(select(func.count(RAGDocumentChunk.id)))
        result["total_chunks"] = total_chunks.scalar() or 0
    except Exception:
        pass

    try:
        total_cols = await session.execute(select(func.count(RAGCollection.id)))
        result["total_collections"] = total_cols.scalar() or 0
    except Exception:
        pass

    try:
        storage = await session.execute(select(func.sum(RAGDocument.file_size_bytes)))
        result["total_storage_bytes"] = storage.scalar() or 0
    except Exception:
        pass

    try:
        clients = await session.execute(
            select(func.count(func.distinct(RAGDocument.client_id)))
        )
        result["clients_with_rag"] = clients.scalar() or 0
    except Exception:
        pass

    try:
        status_rows = await session.execute(
            select(RAGDocument.status, func.count(RAGDocument.id)).group_by(RAGDocument.status)
        )
        result["documents_by_status"] = dict(status_rows.all())
    except Exception:
        pass

    if settings.commercial_rag_vault_enabled:
        try:
            result["regulated_rag_vault"]["vaults"] = (await session.execute(select(func.count(CommercialRAGVault.id)))).scalar() or 0
            result["regulated_rag_vault"]["retrievals"] = (await session.execute(select(func.count(CommercialRAGRetrievalAudit.id)))).scalar() or 0
            result["regulated_rag_vault"]["poisoning_alerts"] = (await session.execute(select(func.count(CommercialRAGPoisoningAlert.id)).where(CommercialRAGPoisoningAlert.resolved == False))).scalar() or 0
            result["regulated_rag_vault"]["acl_violations"] = (await session.execute(select(func.count(CommercialRAGRetrievalAudit.id)).where(CommercialRAGRetrievalAudit.policy_result != "allow"))).scalar() or 0
            result["regulated_rag_vault"]["legal_holds"] = (await session.execute(select(func.count(CommercialRAGLegalHold.id)).where(CommercialRAGLegalHold.active == True))).scalar() or 0
            result["regulated_rag_vault"]["signed_documents"] = (await session.execute(select(func.count(CommercialRAGDocument.id)).where(CommercialRAGDocument.signed_manifest_hash.is_not(None)))).scalar() or 0
            confidential_count = (await session.execute(select(func.count(CommercialRAGVault.id)).where(CommercialRAGVault.vault_mode.in_(["confidential", "sovereign", "airgap"])))).scalar() or 0
            total_vaults = result["regulated_rag_vault"]["vaults"] or 0
            result["regulated_rag_vault"]["confidential_retrieval_percent"] = round((confidential_count / total_vaults) * 100, 2) if total_vaults else 0.0
        except Exception:
            pass
        try:
            result["context_lineage_retrieval_proofs"]["retrieval_proofs"] = (await session.execute(select(func.count(CommercialRetrievalProof.id)))).scalar() or 0
            result["context_lineage_retrieval_proofs"]["lineage_nodes"] = (await session.execute(select(func.count(CommercialContextLineage.id)))).scalar() or 0
            result["context_lineage_retrieval_proofs"]["replay_records"] = (await session.execute(select(func.count(CommercialRetrievalReplayRecord.id)))).scalar() or 0
            result["context_lineage_retrieval_proofs"]["verified_proofs"] = (await session.execute(select(func.count(CommercialRetrievalProof.id)).where(CommercialRetrievalProof.verification_status == "valid"))).scalar() or 0
            result["context_lineage_retrieval_proofs"]["drift_events"] = (await session.execute(select(func.count(CommercialRetrievalReplayRecord.id)).where(CommercialRetrievalReplayRecord.drift_status != "stable"))).scalar() or 0
        except Exception:
            pass

    return result
