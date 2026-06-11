# Compatibility Layer

A comprehensive compatibility layer for migrating external agent frameworks into the LLM Harness ecosystem.

## Supported Frameworks

| Framework   | Status        | Description                                            |
|-------------|---------------|--------------------------------------------------------|
| **LangGraph** | ✅ Supported | Graph-based state machine agents (StateGraph, CompiledStateGraph) |
| **CrewAI**    | ✅ Supported | Role-based multi-agent teams (Agent, Task, Crew)          |
| **AutoGen**   | ✅ Supported | Conversational multi-agent systems (ConversableAgent, GroupChat) |

## Architecture

```
compat/
├── __init__.py          # Unified API entry point
├── base.py              # Base classes: BaseAdapter, BaseImporter, BaseConverter
├── report.py            # CompatibilityReport, CompatibilityAnalyzer
├── langgraph/
│   ├── __init__.py
│   ├── adapters.py      # StateGraph, CompiledStateGraph (drop-in replacements)
│   ├── importers.py     # LangGraphImporter (from_source, from_file)
│   └── converters.py    # LangGraphConverter -> AgentTeam
├── crewai/
│   ├── __init__.py
│   ├── adapters.py      # Agent, Task, Crew (drop-in replacements)
│   ├── importers.py     # CrewAIImporter (from_source, from_file)
│   └── converters.py    # CrewAIConverter -> AgentTeam
└── autogen/
    ├── __init__.py
    ├── adapters.py      # ConversableAgent, UserProxyAgent, AssistantAgent, GroupChat
    ├── importers.py     # AutoGenImporter (from_source, from_file)
    └── converters.py    # AutoGenConverter -> AgentTeam
```

## Quick Start

### 1. Analyze Compatibility

```python
from scripts.llm_harness.compat.report import CompatibilityAnalyzer

with open("my_agent.py") as f:
    code = f.read()

report = CompatibilityAnalyzer.analyze_source_code("langgraph", code)
print(f"Score: {report.score}/100")
print(f"Status: {report.status.value}")
print(f"Remediation steps: {report.remediation_steps}")
```

### 2. Import External Agents

```python
from scripts.llm_harness.compat.langgraph import LangGraphImporter
from scripts.llm_harness.compat.crewai import CrewAIImporter
from scripts.llm_harness.compat.autogen import AutoGenImporter

# LangGraph
result = LangGraphImporter().from_file("my_langgraph_agent.py")
graph = result.data

# CrewAI
result = CrewAIImporter().from_file("my_crew.py")
crew = result.data

# AutoGen
result = AutoGenImporter().from_file("my_autogen_agent.py")
agent = result.data
```

### 3. Convert to Native Types

```python
from scripts.llm_harness.compat.langgraph import LangGraphConverter
from scripts.llm_harness.compat.crewai import CrewAIConverter
from scripts.llm_harness.compat.autogen import AutoGenConverter

# LangGraph -> AgentTeam
team = LangGraphConverter().convert(graph, team_name="my_team").data

# CrewAI -> AgentTeam
team = CrewAIConverter().convert(crew, team_name="my_crew").data

# AutoGen -> AgentTeam
team = AutoGenConverter().convert(agent, team_name="my_autogen_team").data
```

### 4. Full Pipeline (Import + Convert)

```python
from scripts.llm_harness.compat.langgraph import LangGraphImporter, LangGraphConverter

importer = LangGraphImporter()
import_result = importer.from_file("existing_langgraph.py")

converter = LangGraphConverter()
convert_result = converter.convert(import_result.data)

# Use with MAS orchestrator
from scripts.llm_harness.mas.orchestrator import Orchestrator
orchestrator = Orchestrator(coding_loop)
result = await orchestrator.run(convert_result.data, "my task")
```

## Adapter Details

### LangGraph Adapters

`StateGraph` and `CompiledStateGraph` mirror LangGraph's API:

```python
from scripts.llm_harness.compat.langgraph import StateGraph

graph = StateGraph(state_schema=dict)
graph.add_node("agent_a", my_function)
graph.add_edge("agent_a", "agent_b")
graph.add_conditional_edges("agent_a", routing_fn, {"path1": "agent_b", "path2": "agent_c"})
graph.set_entry_point("agent_a")
graph.set_finish_point("agent_c")
compiled = graph.compile()
result = await compiled.invoke({"input": "data"})
```

### CrewAI Adapters

`Agent`, `Task`, and `Crew` mirror CrewAI's API:

```python
from scripts.llm_harness.compat.crewai import Agent, Task, Crew

researcher = Agent(role="researcher", goal="Find information", backstory="Expert researcher")
writer = Agent(role="writer", goal="Write reports", backstory="Technical writer")
task = Task(description="Research topic X", expected_output="summary", agent=researcher)
crew = Crew(agents=[researcher, writer], tasks=[task], process="sequential")
crew.kickoff(inputs={"topic": "AI"})
```

### AutoGen Adapters

`ConversableAgent`, `UserProxyAgent`, `AssistantAgent`, and `GroupChat` mirror AutoGen's API:

```python
from scripts.llm_harness.compat.autogen import ConversableAgent, AssistantAgent, GroupChat

alice = ConversableAgent(name="Alice", system_message="I am Alice")
bob = AssistantAgent(name="Bob", system_message="I am Bob")
alice.initiate_chat(bob, "Hello Bob!")

group = GroupChat(agents=[alice, bob], max_round=10)
```

## Compatibility Report

```python
from scripts.llm_harness.compat.report import CompatibilityAnalyzer

report = CompatibilityAnalyzer.analyze_source_code("autogen", source_code)
print(report.to_dict())
# {
#   "framework": "autogen",
#   "compatibility_score": 70.0,
#   "status": "partially_compatible",
#   "features_analyzed": [...],
#   "remediation_steps": ["..."],
#   "details": {"code_length": 1234}
# }
```

## Running Tests

```bash
pytest tests/integration/operations/test_compatibility_layer.py -v
pytest tests/integration/operations/test_compatibility_layer.py -v -k "TestLangGraph"
pytest tests/integration/operations/test_compatibility_layer.py -v -k "TestCrewAI"
pytest tests/integration/operations/test_compatibility_layer.py -v -k "TestAutoGen"
```
