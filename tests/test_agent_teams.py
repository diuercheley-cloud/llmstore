import os
import yaml
import pytest
from scripts.llm_harness.mas.registry import AgentRegistry
from scripts.llm_harness.config import HarnessConfig

class Args:
    def __init__(self, **kwargs):
        self.config = None
        self.code_agent = None
        self.provider = None
        self.model = None
        self.base_url = None
        self.sandbox = None
        self.docker_image = None
        self.self_heal = None
        self.api_key_env = None
        self.timeout = None
        self.local_model_timeout = None
        self.auto_increase_timeout = None
        self.max_retries = None
        self.stream = None
        self.stream_local_default = None
        self.verbose_stream = None
        self.tool_calling = None
        self.supports_tool_calling = None
        self.allow_native_tools_for_local = None
        self.lm_studio_compatibility = None
        self.capability_cache_ttl_seconds = None
        self.workspace_mount_path = None
        self.temp_base_dir = None
        self.sandbox_network = None
        self.proxy_url = None
        self.loop_timeout = None
        self.max_output_chars = None
        self.report_output_path = None
        self.cache = None
        self.no_cache = False
        self.pricing_file = None
        self.max_cost_per_run = None
        self.max_tokens_per_run = None
        self.memory = None
        self.memory_dir = None
        self.memory_retention_days = None
        self.agent_mode = "single"
        self.team = None
        self.agent_registry_file = None
        self.approval_mode = None
        self.approval_default = None
        self.edit_action_before_run = None
        self.checkpoint_dir = None
        self.checkpoint_every_step = None
        self.multimodal = None
        self.max_tokens = None
        self.auto = None
        self.max_auto_fixes = None
        self.stop_on_risk = None
        self.require_approval_for_edits = None
        self.model_profile = None
        self.fallback_model_profile = None
        self.allow_cloud_models = None
        
        for k, v in kwargs.items():
            setattr(self, k, v)

@pytest.fixture
def sample_registry_yaml(tmp_path):
    registry_data = {
        "agents": {
            "alice": {
                "role": "Developer",
                "prompt": "You are Alice"
            },
            "bob": {
                "role": "Tester",
                "prompt": "You are Bob"
            }
        },
        "teams": {
            "dream_team": {
                "name": "Dream Team",
                "description": "A great team",
                "topology": "supervisor",
                "members": [
                    {"agent_id": "alice", "role": "coder"},
                    {"agent_id": "bob", "role": "qa"}
                ]
            }
        },
        "roles": {
            "coder": {"name": "Coder", "description": "Codes"},
            "qa": {"name": "QA", "description": "Tests"}
        }
    }
    registry_file = tmp_path / "agent-registry.yaml"
    with open(registry_file, "w") as f:
        yaml.dump(registry_data, f)
    return str(registry_file)

def test_load_registry_with_teams(sample_registry_yaml):
    registry = AgentRegistry.load(sample_registry_yaml)
    assert "alice" in registry.agents
    assert "dream_team" in registry.teams
    assert len(registry.teams["dream_team"].members) == 2
    assert registry.teams["dream_team"].members[0].agent_id == "alice"

def test_validate_registry_success(sample_registry_yaml):
    registry = AgentRegistry.load(sample_registry_yaml)
    assert registry.validate() is True

def test_validate_registry_missing_agent(tmp_path):
    registry_data = {
        "agents": {"alice": {"role": "Dev", "prompt": "..."}},
        "teams": {
            "bad_team": {
                "name": "Bad",
                "description": "...",
                "members": [{"agent_id": "missing", "role": "coder"}]
            }
        }
    }
    registry_file = tmp_path / "bad-registry.yaml"
    with open(registry_file, "w") as f:
        yaml.dump(registry_data, f)
    
    registry = AgentRegistry.load(str(registry_file))
    with pytest.raises(ValueError, match="not found in agents"):
        registry.validate()

def test_config_loading_with_teams():
    config = HarnessConfig(agent_mode="team", default_team="dream_team")
    assert config.agent_mode == "team"
    assert config.default_team == "dream_team"

def test_cli_teams_list(sample_registry_yaml):
    from scripts.llm_harness.cli_commands import run_teams_command
    import asyncio

    args = Args(
        agent_registry_file=sample_registry_yaml,
        teams_command="list"
    )
    
    asyncio.run(run_teams_command(args))

def test_cli_teams_inspect(sample_registry_yaml):
    from scripts.llm_harness.cli_commands import run_teams_command
    import asyncio

    args = Args(
        agent_registry_file=sample_registry_yaml,
        teams_command="inspect",
        team_name="dream_team"
    )
    
    asyncio.run(run_teams_command(args))
