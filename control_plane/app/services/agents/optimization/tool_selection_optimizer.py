import logging

from app.models.agents.agents import AgentEvalFailure

logger = logging.getLogger(__name__)


class ToolSelectionOptimizer:
    def optimize_tool_selection(
        self, current_tools: list[str], failures: list[AgentEvalFailure]
    ) -> list[str]:
        """
        Adjusts the allowlist of tools based on execution failures.
        Removes error-prone tools or logs details.
        """
        optimized_tools = list(current_tools) if current_tools else ["*"]

        # If wildcard is allowed, specify concrete tools based on observed errors
        if "*" in optimized_tools:
            # For this prototype, if it's wildcard, let's keep it or replace it with a typical list
            optimized_tools = [
                "confluence",
                "github",
                "jira",
                "microsoft365",
                "salesforce",
                "slack",
            ]

        for f in failures:
            if f.failure_type == "tool_error":
                offending_tool = f.details.get("tool_name")
                if offending_tool and offending_tool in optimized_tools:
                    # Remove the failing tool to prevent execution crash
                    logger.info(
                        f"Removing failing tool '{offending_tool}' from candidate allowed list."
                    )
                    optimized_tools.remove(offending_tool)

        # Fallback to make sure there's at least one tool
        if not optimized_tools:
            optimized_tools = ["slack"]

        return optimized_tools
