"""
Example: Migrating a CrewAI agent setup into the harness via the compat layer.

Demonstrates:
  1. Analyze compatibility
  2. Import the CrewAI Crew
  3. Convert to native AgentTeam
"""

from scripts.llm_harness.compat.report import CompatibilityAnalyzer
from scripts.llm_harness.compat.crewai import CrewAIImporter, CrewAIConverter, Agent, Task, Crew

# --- 1. Simulate an existing CrewAI setup ---
source_code = """
researcher = Agent(
    role="Senior Researcher",
    goal="Find groundbreaking information about AI",
    backstory="You are a seasoned researcher with 20 years of experience.",
    verbose=True,
)

analyst = Agent(
    role="Data Analyst",
    goal="Analyze research data and produce insights",
    backstory="You are a meticulous analyst who loves data.",
    allow_delegation=False,
)

research_task = Task(
    description="Research the latest advances in AI agents",
    expected_output="A comprehensive research document with key findings",
    agent=researcher,
)

analysis_task = Task(
    description="Analyze the research findings",
    expected_output="An analytical report with insights and recommendations",
    agent=analyst,
    context=[research_task],
)

crew = Crew(
    agents=[researcher, analyst],
    tasks=[research_task, analysis_task],
    verbose=2,
)
"""

# --- 2. Analyze compatibility ---
report = CompatibilityAnalyzer.analyze_source_code("crewai", source_code)
print(f"Compatibility: {report.status.value} ({report.score}/100)")
if report.remediation_steps:
    print("Remediation steps:")
    for step in report.remediation_steps:
        print(f"  - {step}")

# --- 3. Import ---
importer = CrewAIImporter()
import_result = importer.from_source(source_code, target_variable="crew")
assert import_result.success, f"Import failed: {import_result.error}"
crew = import_result.data
print(f"\nImported Crew: {crew.process} process")
print(f"  Agents: {[a.role for a in crew.agents]}")
print(f"  Tasks: {[t.description[:50] for t in crew.tasks]}")

# --- 4. Convert ---
converter = CrewAIConverter()
convert_result = converter.convert(crew, team_name="research_crew")
assert convert_result.success, f"Conversion failed: {convert_result.error}"
team = convert_result.data
print(f"\nConverted to team: {team.name}")
print(f"  Members: {[m.agent_id for m in team.members]}")
print(f"  Topology: {team.topology}")

# --- 5. Ready for orchestration ---
