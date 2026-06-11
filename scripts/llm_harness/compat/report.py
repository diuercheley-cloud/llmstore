from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class FrameworkSupport(str, Enum):
    FULLY_COMPATIBLE = "fully_compatible"
    PARTIALLY_COMPATIBLE = "partially_compatible"
    INCOMPATIBLE = "incompatible"


@dataclass
class FeatureAnalysis:
    feature: str
    status: str
    description: str


@dataclass
class CompatibilityReport:
    framework: str
    score: float
    status: FrameworkSupport
    analyzed_features: List[FeatureAnalysis] = field(default_factory=list)
    remediation_steps: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "framework": self.framework,
            "compatibility_score": self.score,
            "status": self.status.value,
            "features_analyzed": [
                {"feature": f.feature, "status": f.status, "description": f.description}
                for f in self.analyzed_features
            ],
            "remediation_steps": self.remediation_steps,
            "details": self.details,
        }


class CompatibilityAnalyzer:
    @staticmethod
    def analyze_source_code(framework: str, source_code: str) -> CompatibilityReport:
        framework = framework.lower().strip()
        score = 100.0
        features: List[FeatureAnalysis] = []
        remediations: List[str] = []

        if framework == "langgraph":
            has_state_graph = "StateGraph" in source_code
            has_compile = ".compile(" in source_code
            has_conditional_edges = "add_conditional_edges" in source_code
            has_checkpointer = "SqliteSaver" in source_code or "MemorySaver" in source_code
            has_node = "add_node" in source_code
            has_edge = "add_edge" in source_code

            features.append(FeatureAnalysis(
                feature="StateGraph definition",
                status="supported" if has_state_graph else "not_found",
                description="Standard graph definitions with entry and finish points.",
            ))
            features.append(FeatureAnalysis(
                feature="Nodes and edges",
                status="supported" if (has_node and has_edge) else "partial",
                description="Graph nodes and edges define the agent workflow topology.",
            ))

            if has_compile:
                features.append(FeatureAnalysis(
                    feature="Graph compilation (.compile())",
                    status="supported",
                    description="Compiled graphs can be migrated to native workflows.",
                ))

            if has_conditional_edges:
                score -= 20.0
                features.append(FeatureAnalysis(
                    feature="Conditional edges",
                    status="partially_supported",
                    description="Conditional routing requires explicit mapping to deterministic transitions.",
                ))
                remediations.append(
                    "Map conditional edge branches to separate agent workflow edges "
                    "with explicit condition expressions."
                )

            if has_checkpointer:
                score -= 15.0
                features.append(FeatureAnalysis(
                    feature="Checkpointer / persistent memory",
                    status="partially_supported",
                    description="LangGraph checkpointers map to native session/run state.",
                ))
                remediations.append(
                    "Replace external checkpointers with native platform session state management."
                )

        elif framework == "crewai":
            has_agent = "Agent(" in source_code
            has_task = "Task(" in source_code
            has_crew = "Crew(" in source_code or "Crew(" in source_code
            has_hierarchical = "hierarchical" in source_code.lower() or "Process.hierarchical" in source_code
            has_memory = "memory=True" in source_code
            has_delegation = "allow_delegation" in source_code

            features.append(FeatureAnalysis(
                feature="Agent definitions",
                status="supported" if has_agent else "not_found",
                description="CrewAI Agent definitions map directly to AgentDefinition with role, goal, backstory.",
            ))
            features.append(FeatureAnalysis(
                feature="Task definitions",
                status="supported" if has_task else "not_found",
                description="Tasks map to workflow steps with description, expected output, and assigned agent.",
            ))

            if has_crew:
                features.append(FeatureAnalysis(
                    feature="Crew orchestration",
                    status="supported",
                    description="Crew instances become AgentTeam definitions.",
                ))

            if has_hierarchical:
                score -= 30.0
                features.append(FeatureAnalysis(
                    feature="Hierarchical process flow",
                    status="unsupported",
                    description="Hierarchical manager flow is not natively emulated; sequential is used.",
                ))
                remediations.append(
                    "Convert hierarchical Crew structures into multi-agent teams "
                    "with explicit supervisor delegation rules."
                )

            if has_memory:
                score -= 15.0
                features.append(FeatureAnalysis(
                    feature="CrewAI context memory",
                    status="partially_supported",
                    description="Memory maps to native cognitive memory stores.",
                ))
                remediations.append(
                    "Use native memory policies in AgentRegistry instead of CrewAI memory options."
                )

            if has_delegation:
                score -= 5.0
                features.append(FeatureAnalysis(
                    feature="Agent delegation",
                    status="partially_supported",
                    description="Delegation is supported via team topology configurations.",
                ))

        elif framework == "autogen":
            has_conversable = "ConversableAgent" in source_code
            has_user_proxy = "UserProxyAgent" in source_code
            has_group_chat = "GroupChat" in source_code
            has_group_manager = "GroupChatManager" in source_code
            has_code_exec = "code_execution_config" in source_code
            has_llm_config = "llm_config" in source_code

            features.append(FeatureAnalysis(
                feature="ConversableAgent messaging",
                status="supported" if has_conversable else "not_found",
                description="Peer-to-peer message exchanges and auto-replies.",
            ))

            if has_user_proxy:
                features.append(FeatureAnalysis(
                    feature="UserProxyAgent",
                    status="supported",
                    description="User proxy agents map to human-in-the-loop approval configs.",
                ))

            if has_group_chat or has_group_manager:
                score -= 30.0
                features.append(FeatureAnalysis(
                    feature="GroupChat / GroupChatManager",
                    status="partially_supported",
                    description="Group chats require conversion to AgentTeam collaborations.",
                ))
                remediations.append(
                    "Convert GroupChat to native AgentTeam definition with defined members "
                    "and topology (supervisor, mesh, etc.)."
                )

            if has_code_exec:
                score -= 20.0
                features.append(FeatureAnalysis(
                    feature="Code execution config",
                    status="partially_supported",
                    description="Local/Docker code execution should migrate to platform sandboxes.",
                ))
                remediations.append(
                    "Use the platform's native sandbox service for running generated code safely."
                )

            if has_llm_config:
                features.append(FeatureAnalysis(
                    feature="LLM configuration",
                    status="supported",
                    description="llm_config maps to model profiles in the harness.",
                ))

        else:
            score = 0.0
            features.append(FeatureAnalysis(
                feature="Framework detection",
                status="unsupported",
                description=f"Framework '{framework}' is not supported for migration.",
            ))
            remediations.append(
                "Ensure target framework is 'langgraph', 'crewai', or 'autogen'."
            )

        score = max(0.0, min(100.0, score))
        if score >= 90.0:
            status = FrameworkSupport.FULLY_COMPATIBLE
        elif score >= 50.0:
            status = FrameworkSupport.PARTIALLY_COMPATIBLE
        else:
            status = FrameworkSupport.INCOMPATIBLE

        return CompatibilityReport(
            framework=framework,
            score=score,
            status=status,
            analyzed_features=features,
            remediation_steps=remediations,
            details={"code_length": len(source_code)},
        )
