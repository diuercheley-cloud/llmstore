import re

path = "control_plane/app/models/__init__.py"
with open(path, "r") as f:
    content = f.read()

new_imports = """
from app.models.agent_tool_synthesis import (
    AgentGeneratedTool,
    AgentGeneratedToolVersion,
    AgentCodeInterpreterRun,
    AgentSandboxSession,
    AgentSandboxArtifact,
    AgentSandboxPolicyEvent,
)
"""

new_all_items = [
    "AgentGeneratedTool",
    "AgentGeneratedToolVersion",
    "AgentCodeInterpreterRun",
    "AgentSandboxSession",
    "AgentSandboxArtifact",
    "AgentSandboxPolicyEvent",
]

content = new_imports + "\n" + content

all_match = re.search(r'__all__\s*=\s*\[(.*?)\]', content, re.DOTALL)
if all_match:
    inner = all_match.group(1)
    new_inner = inner.rstrip()
    if new_inner and not new_inner.endswith(','):
        new_inner += ','
    for item in new_all_items:
        new_inner += f'\n    "{item}",'
    new_inner += '\n'
    content = content[:all_match.start(1)] + new_inner + content[all_match.end(1):]

with open(path, "w") as f:
    f.write(content)
