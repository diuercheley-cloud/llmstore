import logging

from app.models.agents.agents import AgentEvalFailure

logger = logging.getLogger(__name__)


class PromptOptimizer:
    def optimize_prompt(self, current_instructions: str, failures: list[AgentEvalFailure]) -> str:
        """
        Refines current system instructions using insights from evaluation failures.
        """
        if not failures:
            # Baseline tweak if no failures found
            return (
                current_instructions
                + "\n\nNote: Ensure all task inputs are validated prior to execution."
            )

        # Compile directives based on observed failure types
        directives = []
        failure_types = {f.failure_type for f in failures}

        if "regression" in failure_types or any(
            "regression" in str(f.details).lower() for f in failures
        ):
            directives.append(
                "- CRITICAL: Ensure performance does not regress on previously passing tasks."
            )

        if "secret_leak" in failure_types or any(
            "leak" in str(f.details).lower() for f in failures
        ):
            directives.append(
                "- SAFETY: Redact all API keys, tokens, or credentials from responses."
            )

        if "tool_error" in failure_types or any("tool" in str(f.details).lower() for f in failures):
            directives.append(
                "- ERROR HANDLING: Verify parameters before calling tools and handle exceptions gracefully."
            )

        if "policy_denial" in failure_types or any(
            "deny" in str(f.details).lower() for f in failures
        ):
            directives.append(
                "- GOVERNANCE: Respect security boundary limits and policy denials; request approval when needed."
            )

        if not directives:
            directives.append(
                "- OPTIMIZATION: Refine execution efficiency and ensure outputs are clear and concise."
            )

        # Build new instructions
        optimized_instructions = current_instructions
        optimized_instructions += "\n\n### Compiled Directives (DSPy-Optimized):\n" + "\n".join(
            directives
        )
        return optimized_instructions
