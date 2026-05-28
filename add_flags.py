import json
from pathlib import Path
import yaml

# 1. Update feature-flags.yaml
ff_path = Path("config/feature-flags.yaml")
with open(ff_path, "r") as f:
    flags = yaml.safe_load(f)

new_flags = [
    {
        "name": "AGENT_TOOL_SYNTHESIS_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "beta",
        "introduced_in": "v2.1.0-agentic-ai-platform",
        "risk_level": "high",
        "dependencies": ["AGENT_RUNTIME_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "Tool synthesis allows executing auto-generated code, disabled by default."
    },
    {
        "name": "AGENT_CODE_INTERPRETER_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "beta",
        "introduced_in": "v2.1.0-agentic-ai-platform",
        "risk_level": "high",
        "dependencies": ["AGENT_RUNTIME_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "Code interpreter runs arbitrary python code, disabled by default."
    },
    {
        "name": "AGENT_DYNAMIC_TOOL_EXECUTION_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "beta",
        "introduced_in": "v2.1.0-agentic-ai-platform",
        "risk_level": "high",
        "dependencies": ["AGENT_TOOL_SYNTHESIS_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "Executing dynamically generated tools is dangerous, opt-in only."
    },
    {
        "name": "AGENT_CODE_SANDBOX_NETWORK_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "beta",
        "introduced_in": "v2.1.0-agentic-ai-platform",
        "risk_level": "high",
        "dependencies": ["AGENT_CODE_INTERPRETER_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "Network access from sandbox is restricted."
    },
    {
        "name": "AGENT_CODE_SANDBOX_WRITE_ENABLED",
        "default": False,
        "owner": "agent-platform",
        "area": "Agentic AI Platform",
        "status": "beta",
        "introduced_in": "v2.1.0-agentic-ai-platform",
        "risk_level": "high",
        "dependencies": ["AGENT_CODE_INTERPRETER_ENABLED"],
        "conflicts": [],
        "safe_default_reason": "Disk write access from sandbox is restricted."
    }
]

existing_names = {f["name"] for f in flags}
for nf in new_flags:
    if nf["name"] not in existing_names:
        flags.append(nf)

with open(ff_path, "w") as f:
    yaml.dump(flags, f, sort_keys=False, default_flow_style=False)

# 2. Update config.py
config_path = Path("control_plane/app/core/config.py")
content = config_path.read_text()
if "agent_tool_synthesis_enabled" not in content:
    lines = content.splitlines()
    insert_idx = next(i for i, line in enumerate(lines) if "agent_tool_adapters_enabled" in line)
    
    new_config_lines = [
        "    # Tool Synthesis & Code Interpreter",
        "    agent_tool_synthesis_enabled: bool = Field(default=False, alias=\"AGENT_TOOL_SYNTHESIS_ENABLED\")",
        "    agent_code_interpreter_enabled: bool = Field(default=False, alias=\"AGENT_CODE_INTERPRETER_ENABLED\")",
        "    agent_dynamic_tool_execution_enabled: bool = Field(default=False, alias=\"AGENT_DYNAMIC_TOOL_EXECUTION_ENABLED\")",
        "    agent_code_sandbox_network_enabled: bool = Field(default=False, alias=\"AGENT_CODE_SANDBOX_NETWORK_ENABLED\")",
        "    agent_code_sandbox_write_enabled: bool = Field(default=False, alias=\"AGENT_CODE_SANDBOX_WRITE_ENABLED\")",
        ""
    ]
    lines = lines[:insert_idx] + new_config_lines + lines[insert_idx:]
    config_path.write_text("\n".join(lines))
