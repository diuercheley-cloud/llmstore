import uuid
from typing import Any, Dict, Optional

from app.models.agent_routing import AgentStepRoutingDecision
from app.services.agents.routing.cost_quality_policy import CostQualityPolicy, PolicyType
from app.services.agents.routing.model_capability_registry import ModelCapabilityRegistry
from app.services.agents.routing.routing_explainer import RoutingExplainer
from app.services.agents.routing.step_classifier import StepClassifier
from sqlalchemy.ext.asyncio import AsyncSession


class AgenticRouterV2:
    """
    Agentic Router 2.0: Orchestrates per-step model routing based on capabilities, cost, and quality.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.classifier = StepClassifier()
        self.registry = ModelCapabilityRegistry(db)
        self.policy_engine = CostQualityPolicy(db)
        self.explainer = RoutingExplainer()

    async def route_step(
        self,
        run_id: uuid.UUID,
        step_type: str,
        input_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        step_id: Optional[uuid.UUID] = None,
        policy_name: str = PolicyType.BALANCED,
        profile_name: Optional[str] = None,
        fallback_from_model_id: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> str:
        # 1. Classify Step
        step_class = self.classifier.classify(step_type, input_text, metadata)

        # 2. Consult Capabilities & Find Suitable Models
        # Extract requirements from metadata
        requires_tool_calling = metadata.get("requires_tool_calling", False) if metadata else False
        requires_json_mode = metadata.get("requires_json_mode", False) if metadata else False
        
        candidates = await self.registry.find_suitable_models(
            step_class=step_class,
            requires_tool_calling=requires_tool_calling,
            requires_json_mode=requires_json_mode
        )

        if not candidates:
            raise ValueError(f"No suitable models found for step class {step_class}")

        # 3. Apply Policy/Budget
        ranked_models = await self.policy_engine.apply_policy(
            models=candidates,
            policy_name=policy_name,
            profile_name=profile_name
        )

        if not ranked_models:
            raise ValueError(f"No models matched policy {policy_name} for step class {step_class}")

        # 4. Handle Fallback if necessary
        chosen_model = ranked_models[0]
        if fallback_from_model_id:
            # Skip the failed model if it's the top choice
            if chosen_model.model_id == fallback_from_model_id:
                if len(ranked_models) > 1:
                    chosen_model = ranked_models[1]
                else:
                    # If only one model exists and it failed, we might have to use a different policy or just fail
                    pass

        # 5. Generate Explanation
        explanation = self.explainer.explain(
            chosen_model=chosen_model,
            step_class=step_class,
            policy_name=policy_name,
            candidates_count=len(ranked_models),
            fallback_happened=fallback_from_model_id is not None,
            failure_reason=failure_reason
        )

        # 6. Record Decision
        decision = AgentStepRoutingDecision(
            run_id=run_id,
            step_id=step_id,
            step_class=step_class,
            chosen_model_id=chosen_model.model_id,
            policy_applied=policy_name,
            explanation=explanation,
            budget_spent=0.0, # Will be updated after execution
            routing_metadata=metadata
        )
        self.db.add(decision)
        await self.db.commit()

        return chosen_model.model_id
