# Owner: agent-platform
import uuid
from typing import Any

from app.services.agents.cognitive_loopback.fewshot_curator import FewShotCurator
from app.services.agents.cognitive_loopback.learning_candidate_registry import (
    LearningCandidateRegistry,
)
from app.services.agents.cognitive_loopback.learning_promotion_gate import LearningPromotionGate
from app.services.agents.cognitive_loopback.loopback_service import CognitiveLoopbackService
from app.services.runtime_dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents", tags=["Agent Cognitive Loopback"])


@router.post("/{agent_id}/feedback")
async def submit_agent_feedback(
    agent_id: uuid.UUID,
    feedback: dict[str, Any],
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = CognitiveLoopbackService(db)
    run_id = feedback.get("run_id")
    if run_id:
        run_id = uuid.UUID(run_id)
    return await service.submit_feedback(agent_id, run_id, tenant_id, feedback)


@router.get("/{agent_id}/learning-candidates")
async def list_learning_candidates(
    agent_id: uuid.UUID, tenant_id: str, db: AsyncSession = Depends(get_db)
):
    registry = LearningCandidateRegistry(db)
    return await registry.list_candidates(agent_id, tenant_id)


@router.post("/{agent_id}/learning-candidates/{candidate_id}/eval")
async def evaluate_learning_candidate(
    agent_id: uuid.UUID, candidate_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    gate = LearningPromotionGate(db)
    return await gate.run_eval(candidate_id)


@router.post("/{agent_id}/learning-candidates/{candidate_id}/approve")
async def approve_learning_candidate(
    agent_id: uuid.UUID,
    candidate_id: uuid.UUID,
    reviewer_id: str,
    comments: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    gate = LearningPromotionGate(db)
    return await gate.approve_candidate(candidate_id, reviewer_id, comments)


@router.post("/{agent_id}/fewshot-examples/{example_id}/activate")
async def activate_fewshot_example(
    agent_id: uuid.UUID, example_id: uuid.UUID, tenant_id: str, db: AsyncSession = Depends(get_db)
):
    curator = FewShotCurator(db)
    success = await curator.activate_example(example_id, tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Example not found")
    return {"status": "activated"}
