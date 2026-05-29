# Owner: agent-platform
import logging
import uuid
import time
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.agents.agent_llm_provider import get_agent_llm_provider
from app.models.agents import AgentDefinition, AgentRun

logger = logging.getLogger(__name__)

class CandidateResponse(BaseModel):
    agent_id: str
    content: str
    tool_calls: list[dict] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = 0.5
    latency_ms: float = 0.0
    cost_estimate: float = 0.0
    safety_passed: bool = True

class CriticReview(BaseModel):
    reviewer_id: str
    correctness: float = 1.0
    completeness: float = 1.0
    tool_evidence: float = 1.0
    policy_compliance: float = 1.0
    cost: float = 1.0
    latency: float = 1.0
    confidence: float = 1.0
    safety: float = 1.0
    reasoning: str = ""
    recommendation: str = "approve"

class FinalSynthesis(BaseModel):
    response: str
    citations: list[str] = Field(default_factory=list)
    winning_candidate_id: Optional[str] = None
    arbitration_case_id: str
    conflicts: list[str] = Field(default_factory=list)

class ArbitrationDecision(BaseModel):
    winner_id: Optional[str] = None
    final_response: str
    scores: dict[str, float] = Field(default_factory=dict)
    conflicts_unresolved: list[str] = Field(default_factory=list)
    reason: str
    receipt_id: str
    receipt: dict = Field(default_factory=dict)

class ArbitrationCase(BaseModel):
    case_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    candidates: list[CandidateResponse] = Field(default_factory=list)
    critic_reviews: list[CriticReview] = Field(default_factory=list)
    decision: Optional[ArbitrationDecision] = None
    receipt: Optional[dict] = None


class ArbitrationEngine:
    """
    Handles conflicting outputs and synthesizes final results from multiple agents.
    Uses reviewer/critic agents, structured scoring, receipts, and synthesis governance.
    """
    def __init__(self, db=None):
        self.db = db
        self.settings = get_settings()

    async def arbitrate(self, outputs: List[Dict[str, Any] | CandidateResponse], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesizes multiple agent outputs into a single coherent result.
        """
        # 1. Feature Flag Validation
        enabled = self.settings.agent_multi_agent_arbitration_enabled
        mock_mode = self.settings.agent_multi_agent_mock_arbitration

        # Heuristic-only / disabled in production check
        if not enabled and not mock_mode:
            raise PermissionError("Multi-agent arbitration is disabled by feature flag")

        # 2. Candidate Parsing
        candidates: List[CandidateResponse] = []
        for out in outputs:
            if isinstance(out, CandidateResponse):
                candidates.append(out)
            elif isinstance(out, dict):
                candidates.append(CandidateResponse(
                    agent_id=str(out.get("agent_id") or uuid.uuid4()),
                    content=out.get("result") or out.get("content") or "",
                    tool_calls=out.get("tool_calls") or [],
                    evidence=out.get("evidence") or "",
                    confidence=float(out.get("confidence") or 0.5),
                    latency_ms=float(out.get("latency_ms") or out.get("latency") or 0.0),
                    cost_estimate=float(out.get("cost_estimate") or out.get("cost_brl") or 0.0),
                    safety_passed=bool(out.get("safety_passed", True))
                ))

        if not candidates:
            return {"status": "error", "message": "No outputs to arbitrate"}

        query = context.get("goal") or context.get("query") or "Synthesize multi-agent output"
        case_id = str(uuid.uuid4())

        # Conflict Detection
        contents = [c.content.strip() for c in candidates]
        is_conflict = len(set(contents)) > 1 or len(candidates) > 1

        case = ArbitrationCase(
            case_id=case_id,
            query=query,
            candidates=candidates
        )

        # 3. Critic Review Setup (Policy & Budget)
        critics = context.get("critics") or []
        critic_reviews: List[CriticReview] = []

        critic_budget = context.get("critic_budget", 0.05)
        allow_raw_prompt = context.get("allow_raw_prompt", True)
        
        # Policy enforcement: budget limits
        if critic_budget <= 0.0:
            raise ValueError("Critic budget exceeded or invalid budget configuration")

        # Policy enforcement: do not share raw prompt if not allowed
        query_for_reviewer = query if allow_raw_prompt else "[REDACTED: Input contains sensitive parameters]"

        # Reviewer policy enforcement
        reviewer_policy = context.get("reviewer_policy") or {}
        if reviewer_policy.get("block_critic_review", False):
            raise PermissionError("Critic review blocked by policy rule")

        # Generate Critic Reviews
        for critic in critics:
            critic_id = str(getattr(critic, "agent_id", critic) if not isinstance(critic, str) else critic)
            
            if mock_mode:
                # Mock critic review
                for cand in candidates:
                    has_evidence = bool(cand.evidence or cand.tool_calls)
                    tool_evidence_score = 1.0 if has_evidence else 0.0
                    safety_score = 1.0 if cand.safety_passed else 0.0
                    latency_score = max(0.0, 1.0 - (cand.latency_ms / 10000.0))
                    cost_score = max(0.0, 1.0 - (cand.cost_estimate / critic_budget))

                    review = CriticReview(
                        reviewer_id=critic_id,
                        correctness=0.9 if cand.safety_passed else 0.1,
                        completeness=0.85,
                        tool_evidence=tool_evidence_score,
                        policy_compliance=1.0,
                        cost=cost_score,
                        latency=latency_score,
                        confidence=cand.confidence,
                        safety=safety_score,
                        reasoning=f"Mock critic review for agent {cand.agent_id}.",
                        recommendation="approve" if (cand.safety_passed and has_evidence) else "reject"
                    )
                    critic_reviews.append(review)
            else:
                # Real critic review via model provider
                if self.settings.agent_multi_agent_critic_review_enabled:
                    from app.api.deps import get_inference_proxy
                    try:
                        proxy = get_inference_proxy()
                    except Exception:
                        proxy = None
                    llm_provider = get_agent_llm_provider(self.db, proxy)

                    for cand in candidates:
                        prompt = (
                            f"System Goal / Query: {query_for_reviewer}\n"
                            f"Candidate agent_id: {cand.agent_id}\n"
                            f"Candidate content: {cand.content}\n"
                            f"Candidate tool calls: {cand.tool_calls}\n"
                            f"Candidate evidence: {cand.evidence}\n"
                            f"Candidate confidence: {cand.confidence}\n"
                            f"Candidate latency (ms): {cand.latency_ms}\n"
                            f"Candidate cost: {cand.cost_estimate}\n"
                            f"Candidate safety_passed: {cand.safety_passed}\n\n"
                            "Respond ONLY with a JSON object. Keys:\n"
                            "correctness (float), completeness (float), tool_evidence (float), "
                            "policy_compliance (float), cost (float), latency (float), confidence (float), "
                            "safety (float), reasoning (str), recommendation (str: approve/reject)."
                        )
                        try:
                            agent_def = AgentDefinition(
                                id=uuid.uuid4(),
                                name="Critic Reviewer",
                                version="1.0.0",
                                instructions="You are a strict Critic Reviewer. You output only raw JSON.",
                                owner="system",
                                model_id="gpt-4o"
                            )
                            run_obj = AgentRun(
                                id=uuid.uuid4(),
                                agent_id=agent_def.id,
                                tenant_id=context.get("tenant_id") or "default-tenant",
                                status="running",
                                input_text=prompt
                            )
                            resp = await llm_provider.generate(agent_def, run_obj, allowed_tools=[])
                            raw_out = resp.output.strip()
                            if raw_out.startswith("```json"):
                                raw_out = raw_out[7:]
                            if raw_out.endswith("```"):
                                raw_out = raw_out[:-3]
                            raw_out = raw_out.strip()
                            data = json.loads(raw_out)
                            
                            review = CriticReview(
                                reviewer_id=critic_id,
                                correctness=float(data.get("correctness", 1.0)),
                                completeness=float(data.get("completeness", 1.0)),
                                tool_evidence=float(data.get("tool_evidence", 1.0)),
                                policy_compliance=float(data.get("policy_compliance", 1.0)),
                                cost=float(data.get("cost", 1.0)),
                                latency=float(data.get("latency", 1.0)),
                                confidence=float(data.get("confidence", 1.0)),
                                safety=float(data.get("safety", 1.0)),
                                reasoning=str(data.get("reasoning", "")),
                                recommendation=str(data.get("recommendation", "approve"))
                            )
                            critic_reviews.append(review)
                        except Exception as e:
                            logger.error(f"Error in LLM critic review call: {e}")
                            # Fallback review
                            has_evidence = bool(cand.evidence or cand.tool_calls)
                            review = CriticReview(
                                reviewer_id=critic_id,
                                correctness=0.8 if cand.safety_passed else 0.0,
                                completeness=0.8,
                                tool_evidence=1.0 if has_evidence else 0.0,
                                policy_compliance=1.0,
                                cost=1.0,
                                latency=1.0,
                                confidence=cand.confidence,
                                safety=1.0 if cand.safety_passed else 0.0,
                                reasoning=f"Fallback review due to LLM error: {e}",
                                recommendation="approve" if (cand.safety_passed and has_evidence) else "reject"
                            )
                            critic_reviews.append(review)
                else:
                    # Critic review enabled false (but arbitration enabled) -> use properties heuristic
                    for cand in candidates:
                        has_evidence = bool(cand.evidence or cand.tool_calls)
                        review = CriticReview(
                            reviewer_id=critic_id,
                            correctness=0.8 if cand.safety_passed else 0.0,
                            completeness=0.8,
                            tool_evidence=1.0 if has_evidence else 0.0,
                            policy_compliance=1.0,
                            cost=1.0,
                            latency=1.0,
                            confidence=cand.confidence,
                            safety=1.0 if cand.safety_passed else 0.0,
                            reasoning="Local review fallback.",
                            recommendation="approve" if (cand.safety_passed and has_evidence) else "reject"
                        )
                        critic_reviews.append(review)

        case.critic_reviews = critic_reviews

        # 4. Structured Scoring
        candidate_scores = {}
        winning_candidate: Optional[CandidateResponse] = None
        highest_score = -1.0
        reasons = []

        conflicts = []
        if len(candidates) > 1:
            for idx, c in enumerate(candidates):
                for other in candidates[idx+1:]:
                    if c.content.strip() != other.content.strip():
                        conflicts.append(f"Conflict between {c.agent_id} and {other.agent_id}")

        any_has_evidence = any(c.evidence or c.tool_calls for c in candidates)

        for cand in candidates:
            # Associate reviews with this candidate
            cand_idx = candidates.index(cand)
            matching_reviews = []
            if len(critic_reviews) == len(candidates) * len(critics) and critics:
                for c_idx in range(len(critics)):
                    matching_reviews.append(critic_reviews[c_idx * len(candidates) + cand_idx])
            elif len(critic_reviews) == len(candidates):
                matching_reviews.append(critic_reviews[cand_idx])

            if matching_reviews:
                correctness = sum(r.correctness for r in matching_reviews) / len(matching_reviews)
                completeness = sum(r.completeness for r in matching_reviews) / len(matching_reviews)
                tool_evidence = sum(r.tool_evidence for r in matching_reviews) / len(matching_reviews)
                policy_compliance = sum(r.policy_compliance for r in matching_reviews) / len(matching_reviews)
                cost = sum(r.cost for r in matching_reviews) / len(matching_reviews)
                latency = sum(r.latency for r in matching_reviews) / len(matching_reviews)
                confidence = sum(r.confidence for r in matching_reviews) / len(matching_reviews)
                safety = sum(r.safety for r in matching_reviews) / len(matching_reviews)
            else:
                correctness = 0.8 if cand.safety_passed else 0.0
                completeness = 0.8
                tool_evidence = 1.0 if (cand.evidence or cand.tool_calls) else 0.0
                policy_compliance = 1.0
                cost = max(0.0, 1.0 - (cand.cost_estimate / critic_budget))
                latency = max(0.0, 1.0 - (cand.latency_ms / 10000.0))
                confidence = cand.confidence
                safety = 1.0 if cand.safety_passed else 0.0

            # CRITICAL RULES
            # - Safety failure loses
            if not cand.safety_passed or safety < 0.5:
                final_score = 0.0
                reasons.append(f"Candidate {cand.agent_id} disqualified due to safety failure.")
            # - Output sem evidence perde
            elif any_has_evidence and not (cand.evidence or cand.tool_calls):
                final_score = 0.0
                reasons.append(f"Candidate {cand.agent_id} disqualified due to lack of tool evidence.")
            elif tool_evidence < 0.5 and any_has_evidence:
                final_score = 0.0
                reasons.append(f"Candidate {cand.agent_id} disqualified due to low tool evidence score.")
            else:
                # Weighted sum scoring across 8 dimensions
                final_score = (
                    correctness * 0.2 +
                    completeness * 0.15 +
                    tool_evidence * 0.15 +
                    policy_compliance * 0.1 +
                    cost * 0.1 +
                    latency * 0.1 +
                    confidence * 0.1 +
                    safety * 0.1
                )

            candidate_scores[cand.agent_id] = final_score
            if final_score > highest_score:
                highest_score = final_score
                winning_candidate = cand

        if winning_candidate and highest_score > 0.0:
            winner_id = winning_candidate.agent_id
            reason = f"Candidate {winner_id} won with score {highest_score:.3f}."
            final_response = winning_candidate.content
        else:
            winner_id = None
            reason = "No candidate succeeded (all failed safety, evidence, or were disqualified). " + " ".join(reasons)
            final_response = "Arbitration Failed: No candidate was approved."

        # Receipt Generation
        receipt_id = str(uuid.uuid4())
        receipt = {
            "receipt_id": receipt_id,
            "case_id": case_id,
            "timestamp": time.time(),
            "winner_id": winner_id,
            "highest_score": highest_score,
            "scores": candidate_scores,
            "conflicts": conflicts,
            "reasoning": reason
        }

        decision = ArbitrationDecision(
            winner_id=winner_id,
            final_response=final_response,
            scores=candidate_scores,
            conflicts_unresolved=conflicts,
            reason=reason,
            receipt_id=receipt_id,
            receipt=receipt
        )

        case.decision = decision
        case.receipt = receipt

        citations = [f"Agent {c.agent_id}" for c in candidates if c.agent_id == winner_id]

        # final governance synthesis formatting
        topology = context.get("topology") or "general"
        if topology == "hierarchical":
            synthesis_str = f"Aggregated analysis: {final_response}"
        elif topology == "debate":
            rounds_count = context.get("rounds_count") or 1
            synthesis_str = f"Final synthesized answer: {final_response} (analyzed over {rounds_count} rounds)"
        else:
            synthesis_str = f"Synthesized Result:\n{final_response}\n\n[Receipt ID: {receipt_id}]\n[Citations: {', '.join(citations)}]"

        return {
            "status": "success",
            "consensus": not is_conflict and winner_id is not None,
            "final_synthesis": synthesis_str,
            "confidence_score": highest_score if highest_score >= 0.0 else 0.0,
            "agent_resolutions": [c.model_dump() for c in candidates],
            "decision": decision.model_dump(),
            "case": case.model_dump(),
            "receipt": receipt
        }

    async def run_critic_review(self, synthesis: str, critics: List[Any]) -> tuple[str, float]:
        """
        Runs the synthesis through critics for a final safety/quality check.
        """
        if not critics:
            return synthesis, 1.0

        final_score = 1.0
        rejection = False
        mock_mode = self.settings.agent_multi_agent_mock_arbitration

        for critic in critics:
            critic_id = str(getattr(critic, "agent_id", critic) if not isinstance(critic, str) else critic)
            if mock_mode:
                final_score *= 0.95
            else:
                if self.settings.agent_multi_agent_critic_review_enabled:
                    from app.api.deps import get_inference_proxy
                    try:
                        proxy = get_inference_proxy()
                    except Exception:
                        proxy = None
                    llm_provider = get_agent_llm_provider(self.db, proxy)

                    try:
                        agent_def = AgentDefinition(
                            id=uuid.uuid4(),
                            name="Critic Reviewer",
                            version="1.0.0",
                            instructions="Review safety and quality. Output safety score float and whether approved.",
                            owner="system",
                            model_id="gpt-4o"
                        )
                        run_obj = AgentRun(
                            id=uuid.uuid4(),
                            agent_id=agent_def.id,
                            tenant_id="default-tenant",
                            status="running",
                            input_text=f"Please review this final synthesis for safety and quality:\n{synthesis}"
                        )
                        resp = await llm_provider.generate(agent_def, run_obj, allowed_tools=[])
                        import re
                        numbers = re.findall(r"\b0\.\d+|\b1\.0\b", resp.output)
                        score = float(numbers[0]) if numbers else 0.95
                        final_score *= score
                        if "reject" in resp.output.lower() or score < 0.5:
                            rejection = True
                    except Exception as e:
                        logger.error(f"Error in LLM critic review check: {e}")
                        final_score *= 0.95
                else:
                    final_score *= 0.95

        if rejection or final_score < 0.5:
            return f"{synthesis}\n\n[Final Review: REJECTED with score {final_score:.2f}]", final_score
        return f"{synthesis}\n\n[Final Review: Approved with score {final_score:.2f}]", final_score
