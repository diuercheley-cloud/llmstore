"""
Example: Migrating a LangGraph agent into the harness via the compat layer.

This demonstrates the full pipeline:
  1. Analyze compatibility
  2. Import the LangGraph StateGraph
  3. Convert to native AgentTeam
  4. Register with the harness
"""

from scripts.llm_harness.compat.report import CompatibilityAnalyzer
from scripts.llm_harness.compat.langgraph import LangGraphImporter, LangGraphConverter, StateGraph

# --- 1. Simulate an existing LangGraph agent ---
source_code = """
graph = StateGraph(dict)

def research_node(state):
    state["notes"] = "Research completed"
    return state

def write_node(state):
    state["draft"] = "Draft written based on: " + state.get("notes", "")
    return state

graph.add_node("researcher", research_node)
graph.add_node("writer", write_node)
graph.add_edge("researcher", "writer")
graph.set_entry_point("researcher")
graph.set_finish_point("writer")
compiled = graph.compile()
"""

# --- 2. Analyze compatibility ---
report = CompatibilityAnalyzer.analyze_source_code("langgraph", source_code)
print(f"Compatibility: {report.status.value} ({report.score}/100)")
if report.remediation_steps:
    print("Remediation steps:")
    for step in report.remediation_steps:
        print(f"  - {step}")

# --- 3. Import ---
importer = LangGraphImporter()
import_result = importer.from_source(source_code, target_variable="graph")
assert import_result.success, f"Import failed: {import_result.error}"
print(f"\nImported graph: {type(import_result.data).__name__}")

# --- 4. Convert ---
converter = LangGraphConverter()
convert_result = converter.convert(
    import_result.data,
    team_name="research_writer_team",
    topology="linear",
)
assert convert_result.success, f"Conversion failed: {convert_result.error}"
team = convert_result.data
print(f"Converted to team: {team.name}")
print(f"  Members: {[m.agent_id for m in team.members]}")
print(f"  Topology: {team.topology}")

# --- 5. The team is now ready for the MAS orchestrator ---
# from scripts.llm_harness.mas.orchestrator import Orchestrator
# result = await orchestrator.run(team, "Research and write about AI")
