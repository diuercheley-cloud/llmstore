"""
Example: Migrating an AutoGen agent setup into the harness via the compat layer.

Demonstrates:
  1. Analyze compatibility
  2. Import AutoGen agents
  3. Convert to native AgentTeam
"""

from scripts.llm_harness.compat.autogen import (
    AutoGenConverter,
    AutoGenImporter,
)
from scripts.llm_harness.compat.report import CompatibilityAnalyzer

# --- 1. Simulate an existing AutoGen setup ---
source_code = """
assistant = AssistantAgent(
    name="assistant",
    system_message="You are a helpful coding assistant.",
    llm_config={"config_list": [{"model": "gpt-4"}]},
)

user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    code_execution_config={"work_dir": "/tmp/coding"},
)

group_chat = GroupChat(
    agents=[assistant, user_proxy],
    messages=[],
    max_round=12,
    speaker_selection_method="auto",
)
"""

# --- 2. Analyze compatibility ---
report = CompatibilityAnalyzer.analyze_source_code("autogen", source_code)
print(f"Compatibility: {report.status.value} ({report.score}/100)")
if report.remediation_steps:
    print("Remediation steps:")
    for step in report.remediation_steps:
        print(f"  - {step}")

# --- 3. Import ---
importer = AutoGenImporter()
import_result = importer.from_source(source_code, target_variable="group_chat")
assert import_result.success, f"Import failed: {import_result.error}"
group_chat = import_result.data
print(f"\nImported GroupChat: {len(group_chat.agents)} agents")
print(f"  Agents: {[a.name for a in group_chat.agents]}")
print(f"  Max rounds: {group_chat.max_round}")

# --- 4. Convert ---
converter = AutoGenConverter()
convert_result = converter.convert(
    group_chat,
    team_name="coding_team",
    topology="mesh",
)
assert convert_result.success, f"Conversion failed: {convert_result.error}"
team = convert_result.data
print(f"\nConverted to team: {team.name}")
print(f"  Members: {[m.agent_id for m in team.members]}")
print(f"  Topology: {team.topology}")

# --- 5. Alternatively, import and convert a single agent ---
single_code = """
coder = ConversableAgent(
    name="coder",
    system_message="You write Python code.",
    llm_config={"config_list": [{"model": "gpt-4"}]},
)
"""
single_result = importer.from_source(single_code, target_variable="coder")
if single_result.success:
    single_team = converter.convert(single_result.data, team_name="single_coder").data
    print(f"\nSingle agent team: {single_team.name}")
    print(f"  Agent: {single_team.members[0].agent_id}")
