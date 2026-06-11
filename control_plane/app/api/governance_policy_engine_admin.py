# Owner: platform-ops
import json
from uuid import UUID

from app.db.session import get_db_session
from app.models.governance.policy_engine import (
    DeterministicPolicy,
    PolicyBundle,
    PolicyConflict,
    PolicyEvaluationResult,
)
from app.services.auth import require_admin
from app.services.governance.policy_engine.audit_events import build_policy_audit_event
from app.services.governance.policy_engine.policy_bundle_service import build_bundle_hash
from app.services.governance.policy_engine.policy_conflict_resolver import detect_policy_conflicts
from app.services.governance.policy_engine.policy_evaluator import evaluate_policy
from app.services.governance.policy_engine.policy_parser import hash_payload, parse_policy_dsl
from app.services.governance.policy_engine.policy_replay_verifier import verify_replay
from app.services.governance.policy_engine.receipts import build_policy_receipt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/admin/governance/deterministic-policies",
    tags=["admin", "governance", "phase-82"],
    dependencies=[Depends(require_admin)],
)


class PolicyCreateRequest(BaseModel):
    client_id: UUID
    policy_name: str = Field(min_length=1, max_length=120)
    policy_scope: str = Field(min_length=1, max_length=64)
    policy_version: str = Field(min_length=1, max_length=32)
    policy_dsl: dict
    policy_status: str = "draft"


class PolicyBundleCreateRequest(BaseModel):
    client_id: UUID
    bundle_name: str
    bundle_scope: str
    policy_ids: list[str]


class PolicyEvaluationRequest(BaseModel):
    client_id: UUID
    policy_id: str
    subject_type: str
    subject_ref: str
    subject: dict


class PolicyReplayVerifyRequest(BaseModel):
    policy_id: str
    subject: dict
    expected_decision: str


def _serialize_policy(item: DeterministicPolicy) -> dict:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "policy_name": item.policy_name,
        "policy_scope": item.policy_scope,
        "policy_version": item.policy_version,
        "policy_status": item.policy_status,
        "policy_hash": item.policy_hash,
        "immutable_hash": item.immutable_hash,
        "created_at": item.created_at.isoformat(),
    }


def _serialize_bundle(item: PolicyBundle) -> dict:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "bundle_name": item.bundle_name,
        "bundle_scope": item.bundle_scope,
        "bundle_hash": item.bundle_hash,
        "policy_count": item.policy_count,
        "immutable_hash": item.immutable_hash,
        "created_at": item.created_at.isoformat(),
    }


def _serialize_conflict(item: PolicyConflict) -> dict:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "policy_id": item.policy_id,
        "conflict_type": item.conflict_type,
        "resolution_strategy": item.resolution_strategy,
        "resolution_status": item.resolution_status,
        "immutable_hash": item.immutable_hash,
        "created_at": item.created_at.isoformat(),
    }


@router.post("", status_code=201)
async def create_policy(payload: PolicyCreateRequest, db: AsyncSession = Depends(get_db_session)):
    normalized = parse_policy_dsl(payload.policy_dsl)
    policy_id = hash_payload(
        {
            "client_id": str(payload.client_id),
            "policy_name": payload.policy_name,
            "policy_scope": payload.policy_scope,
            "policy_version": payload.policy_version,
        }
    )[:32]
    policy_hash = hash_payload(normalized)
    immutable_hash = hash_payload({"policy_id": policy_id, "policy_hash": policy_hash, "status": payload.policy_status})
    policy = DeterministicPolicy(
        id=policy_id,
        client_id=payload.client_id,
        policy_name=payload.policy_name,
        policy_scope=payload.policy_scope,
        policy_version=payload.policy_version,
        policy_dsl=json.dumps(normalized, sort_keys=True),
        policy_hash=policy_hash,
        policy_status=payload.policy_status,
        immutable_hash=immutable_hash,
    )
    db.add(policy)
    for index, conflict in enumerate(detect_policy_conflicts(normalized)):
        db.add(
            PolicyConflict(
                id=hash_payload({"policy_id": policy_id, "index": index})[:32],
                client_id=payload.client_id,
                policy_id=policy_id,
                conflict_type=conflict["conflict_type"],
                resolution_strategy=conflict["resolution_strategy"],
                resolution_status=conflict["resolution_status"],
                immutable_hash=hash_payload({"policy_id": policy_id, "conflict": conflict}),
            )
        )
    await db.commit()
    await db.refresh(policy)
    return {"policy": _serialize_policy(policy), "audit_event": build_policy_audit_event("create", policy.id, "created")}


from app.domains.policy.contracts import PolicyRepository
from app.domains.policy.repositories import SqlAlchemyPolicyRepository

@router.get("")
async def list_policies(db: AsyncSession = Depends(get_db_session)):
    repo = SqlAlchemyPolicyRepository(db)
    # The original query was global, so we need a global list method or use a dummy client_id if applicable.
    # For now, let's add list_all_policies to the repo if needed, 
    # but the repo has list_policies_by_client.
    # Let's adjust the repo to have list_all_policies or just query all in repo.
    
    # Actually, I'll update the repo to have list_all_policies.
    return {"items": await repo.list_all_policies()}


@router.get("/{policy_id}/verify")
async def verify_policy(policy_id: str, db: AsyncSession = Depends(get_db_session)):
    policy = (await db.execute(select(DeterministicPolicy).where(DeterministicPolicy.id == policy_id))).scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="policy_not_found")
    parsed = parse_policy_dsl(policy.dsl_json())
    return {"policy": _serialize_policy(policy), "verified": True, "rule_count": len(parsed["rules"])}


@router.post("/bundles", status_code=201)
async def create_bundle(payload: PolicyBundleCreateRequest, db: AsyncSession = Depends(get_db_session)):
    policies = (
        await db.execute(
            select(DeterministicPolicy).where(
                DeterministicPolicy.id.in_(payload.policy_ids),
                DeterministicPolicy.client_id == payload.client_id,
            )
        )
    ).scalars().all()
    if len(policies) != len(payload.policy_ids):
        raise HTTPException(status_code=400, detail="bundle_contains_unknown_policy")
    policy_hashes = [item.policy_hash for item in policies]
    bundle_hash = build_bundle_hash(policy_hashes)
    bundle = PolicyBundle(
        id=bundle_hash[:32],
        client_id=payload.client_id,
        bundle_name=payload.bundle_name,
        bundle_scope=payload.bundle_scope,
        bundle_hash=bundle_hash,
        policy_count=len(policies),
        immutable_hash=hash_payload({"bundle_hash": bundle_hash, "policy_count": len(policies)}),
    )
    db.add(bundle)
    await db.commit()
    await db.refresh(bundle)
    return _serialize_bundle(bundle)


@router.post("/evaluate", status_code=201)
async def evaluate_policy_against_subject(payload: PolicyEvaluationRequest, db: AsyncSession = Depends(get_db_session)):
    policy = (
        await db.execute(
            select(DeterministicPolicy).where(
                DeterministicPolicy.id == payload.policy_id,
                DeterministicPolicy.client_id == payload.client_id,
            )
        )
    ).scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="policy_not_found")
    result = evaluate_policy(policy.dsl_json(), payload.subject)
    row = PolicyEvaluationResult(
        id=hash_payload({"policy_id": policy.id, "subject_ref": payload.subject_ref, "subject": payload.subject})[:32],
        client_id=payload.client_id,
        policy_id=policy.id,
        subject_type=payload.subject_type,
        subject_ref=payload.subject_ref,
        evaluation_status=result["evaluation_status"],
        decision=result["decision"],
        explanation=result["explanation"],
        replay_safe=result["replay_safe"],
        immutable_hash=hash_payload(result),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "result": {
            "id": row.id,
            "decision": row.decision,
            "evaluation_status": row.evaluation_status,
            "explanation": row.explanation,
            "replay_safe": row.replay_safe,
            "receipt": build_policy_receipt(policy.id, row.decision, row.subject_ref),
        }
    }


@router.post("/replay-verify")
async def replay_verify(payload: PolicyReplayVerifyRequest, db: AsyncSession = Depends(get_db_session)):
    policy = (await db.execute(select(DeterministicPolicy).where(DeterministicPolicy.id == payload.policy_id))).scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="policy_not_found")
    return verify_replay(policy.dsl_json(), payload.subject, payload.expected_decision)


@router.get("/conflicts")
async def list_conflicts(db: AsyncSession = Depends(get_db_session)):
    items = (await db.execute(select(PolicyConflict).order_by(desc(PolicyConflict.created_at)))).scalars().all()
    return {"items": [_serialize_conflict(item) for item in items]}
