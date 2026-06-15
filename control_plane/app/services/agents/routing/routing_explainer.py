from app.models.agents.agent_routing import AgentModelCapability


class RoutingExplainer:
    """
    Generates explanations for routing decisions.
    """

    @staticmethod
    def explain(
        chosen_model: AgentModelCapability,
        step_class: str,
        policy_name: str,
        candidates_count: int,
        fallback_happened: bool = False,
        failure_reason: str | None = None,
    ) -> str:
        explanation = (
            f"Selected model '{chosen_model.model_id}' (tier {chosen_model.quality_tier}) "
            f"for step class '{step_class}' using policy '{policy_name}'. "
        )

        if candidates_count > 1:
            explanation += f"Evaluated {candidates_count} potential models. "
        else:
            explanation += "Only one suitable model found. "

        if fallback_happened:
            explanation += f"Fallback occurred due to previous failure: {failure_reason}. "

        explanation += (
            f"Model capabilities: tool_calling={chosen_model.supports_tool_calling}, "
            f"json_mode={chosen_model.supports_json_mode}, cost_input={chosen_model.cost_input}."
        )

        return explanation
