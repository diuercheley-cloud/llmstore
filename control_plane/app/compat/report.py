# Owner: platform-operations
from typing import Any


class CompatibilityReport:
    """
    Structured report containing migration and compatibility details for external agent setups.
    """

    def __init__(
        self,
        framework: str,
        score: float,
        status: str,
        analyzed_features: list[dict[str, Any]],
        remediation_steps: list[str],
        details: dict[str, Any] | None = None,
    ):
        self.framework = framework
        self.score = score  # 0.0 to 100.0
        self.status = status  # fully_compatible | partially_compatible | incompatible
        self.analyzed_features = analyzed_features
        self.remediation_steps = remediation_steps
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework": self.framework,
            "compatibility_score": self.score,
            "status": self.status,
            "features_analyzed": self.analyzed_features,
            "remediation_steps": self.remediation_steps,
            "details": self.details,
        }


class CompatibilityAnalyzer:
    """
    Analyzes Python code files or configurations for compatibility with our migration layer.
    """

    @staticmethod
    def analyze_source_code(framework: str, source_code: str) -> CompatibilityReport:
        framework = framework.lower()

        # Default analysis
        score = 100.0
        features = []
        remediations = []

        if framework == "langgraph":
            # Check for StateGraph use
            has_state_graph = "StateGraph" in source_code
            has_compile = ".compile(" in source_code
            has_conditional_edges = "add_conditional_edges" in source_code
            has_checkpointer = "SqliteSaver" in source_code or "MemorySaver" in source_code

            features.append(
                {
                    "feature": "StateGraph & CompiledStateGraph",
                    "status": "supported" if has_state_graph else "not_found",
                    "description": "Standard graph definitions with entry and finish points.",
                }
            )

            if has_conditional_edges:
                score -= 20.0
                features.append(
                    {
                        "feature": "Conditional Edges",
                        "status": "partially_supported",
                        "description": "Conditional routing is partially supported. Define clear deterministic transition keys.",
                    }
                )
                remediations.append(
                    "Map conditional edge branches explicitly to separate agent workflow edges in the console."
                )
            else:
                features.append(
                    {
                        "feature": "Conditional Edges",
                        "status": "supported",
                        "description": "No conditional routing detected, clean path migration.",
                    }
                )

            if has_checkpointer:
                score -= 15.0
                features.append(
                    {
                        "feature": "Checkpointer / Persistent Memory",
                        "status": "partially_supported",
                        "description": "LangGraph checkpointer persistence is mapped to AgentWorkflowRun state_data.",
                    }
                )
                remediations.append(
                    "Replace external Checkpointers with native platform Session / Run state management."
                )
            else:
                features.append(
                    {
                        "feature": "Checkpointer / Persistent Memory",
                        "status": "supported",
                        "description": "No external checkpointers found.",
                    }
                )

        elif framework == "crewai":
            has_agent = "Agent" in source_code
            has_task = "Task" in source_code
            has_crew = "Crew" in source_code
            has_hierarchical = "Process.hierarchical" in source_code
            has_memory = "memory=True" in source_code

            features.append(
                {
                    "feature": "Agent & Task Emulation",
                    "status": "supported" if (has_agent or has_task) else "not_found",
                    "description": "Maps CrewAI roles and goals directly to system instructions.",
                }
            )

            if has_hierarchical:
                score -= 30.0
                features.append(
                    {
                        "feature": "Hierarchical Process Flow",
                        "status": "unsupported",
                        "description": "Hierarchical manager agent flow is not natively emulated; sequential chaining is used.",
                    }
                )
                remediations.append(
                    "Convert hierarchical Crew structures into multi-agent teams with explicit delegation rules."
                )
            else:
                features.append(
                    {
                        "feature": "Process Flow",
                        "status": "supported",
                        "description": "Standard sequential process flow.",
                    }
                )

            if has_memory:
                score -= 15.0
                features.append(
                    {
                        "feature": "CrewAI Context Memory",
                        "status": "partially_supported",
                        "description": "Short/long term agent memory is mapped to platform cognitive memory stores.",
                    }
                )
                remediations.append(
                    "Integrate database memory policies in the AgentRegistry instead of CrewAI memory options."
                )
            else:
                features.append(
                    {
                        "feature": "Context Memory",
                        "status": "supported",
                        "description": "No custom CrewAI memory fields detected.",
                    }
                )

        elif framework == "autogen":
            has_conversable = "ConversableAgent" in source_code
            has_user_proxy = "UserProxyAgent" in source_code
            has_group_chat = "GroupChat" in source_code
            has_code_execution = "code_execution_config" in source_code

            features.append(
                {
                    "feature": "ConversableAgent Messaging",
                    "status": "supported" if has_conversable else "not_found",
                    "description": "Peer-to-peer message exchanges and auto-replies.",
                }
            )

            if has_group_chat:
                score -= 30.0
                features.append(
                    {
                        "feature": "GroupChat & GroupChatManager",
                        "status": "partially_supported",
                        "description": "Multi-agent group chats require converting to AgentTeam collaborations.",
                    }
                )
                remediations.append(
                    "Convert GroupChat to native AgentTeam definition with defined members and team runs."
                )
            else:
                features.append(
                    {
                        "feature": "GroupChat",
                        "status": "supported",
                        "description": "No complex group chat managers found.",
                    }
                )

            if has_code_execution:
                score -= 20.0
                features.append(
                    {
                        "feature": "Code Execution Config",
                        "status": "partially_supported",
                        "description": "Local docker execution configurations should migrate to platform sandboxes.",
                    }
                )
                remediations.append(
                    "Use the platform's native ToolSandbox service for running generated code safely."
                )
            else:
                features.append(
                    {
                        "feature": "Code Execution",
                        "status": "supported",
                        "description": "No custom code execution configurations found.",
                    }
                )

        else:
            score = 0.0
            features.append(
                {
                    "feature": "Framework Detection",
                    "status": "unsupported",
                    "description": f"Framework '{framework}' is not supported for migration.",
                }
            )
            remediations.append("Ensure target framework is 'langgraph', 'crewai', or 'autogen'.")

        score = max(0.0, min(100.0, score))
        if score >= 90.0:
            status = "fully_compatible"
        elif score >= 50.0:
            status = "partially_compatible"
        else:
            status = "incompatible"

        return CompatibilityReport(
            framework=framework,
            score=score,
            status=status,
            analyzed_features=features,
            remediation_steps=remediations,
            details={"code_length": len(source_code)},
        )
