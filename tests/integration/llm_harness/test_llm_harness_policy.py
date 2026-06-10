from scripts.llm_harness.policy import PolicyEngine


def test_policy_usage_limits():
    policy = PolicyEngine({"max_tokens": 100, "max_cost": 0.5})
    assert policy.check_usage(tokens=50, cost=0.1) is True
    assert policy.check_usage(tokens=150, cost=0.1) is False
    assert policy.check_usage(tokens=50, cost=0.6) is False


def test_policy_shell_semantic_parser_blocks_unsafe_constructs(tmp_path):
    policy = PolicyEngine({"shell_policy": {"workspace_root": str(tmp_path)}})

    assert policy.evaluate_shell_command("ls; rm -rf /").allowed is False
    assert policy.evaluate_shell_command("ls | grep foo").allowed is False
    assert policy.evaluate_shell_command("ls && echo done").allowed is False
    assert policy.evaluate_shell_command("ls || echo fail").allowed is False
    assert policy.evaluate_shell_command("echo $(whoami)").allowed is False
    assert policy.evaluate_shell_command("echo `whoami`").allowed is False
    assert policy.evaluate_shell_command("cat < /etc/passwd").allowed is False
    assert policy.evaluate_shell_command("echo hi > file.txt").allowed is False

    analysis = policy.analyze_shell_command("pytest -q tests/")
    assert analysis.main_command == "pytest"
    assert analysis.args == ["-q", "tests/"]
    assert analysis.chain_operators == []


def test_policy_global_deny_wins_over_allow():
    policy = PolicyEngine(
        {
            "allowed_tools": ["git"],
            "shell_policy": {
                "command_allow": {"git": True},
            },
        }
    )

    decision = policy.evaluate_shell_command("git push origin main")
    assert decision.allowed is False
    assert decision.policy_level == "global_deny"


def test_policy_shell_validation_allowed(tmp_path):
    policy = PolicyEngine({"shell_policy": {"workspace_root": str(tmp_path)}})
    assert policy.evaluate_shell_command("ls").allowed is True
    assert policy.evaluate_shell_command("ls -la").allowed is True
    assert policy.evaluate_shell_command("git status").allowed is True
    assert policy.evaluate_shell_command("git diff HEAD").allowed is True
    assert policy.evaluate_shell_command("pytest -q tests/").allowed is True


def test_policy_path_specific_exception_for_rm_tmp(tmp_path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    (workspace_root / "tmp").mkdir()
    policy = PolicyEngine(
        {
            "shell_policy": {
                "workspace_root": str(workspace_root),
                "path_exceptions": [
                    {
                        "name": "cleanup-tmp",
                        "command": "rm",
                        "args": ["-rf"],
                        "path": "./tmp",
                    }
                ],
            }
        }
    )

    allowed = policy.evaluate_shell_command("rm -rf ./tmp")
    denied = policy.evaluate_shell_command("rm -rf ./other")

    assert allowed.allowed is True
    assert allowed.policy_level == "path_exception"
    assert denied.allowed is False


def test_policy_rm_root_always_denied_even_with_exception(tmp_path):
    policy = PolicyEngine(
        {
            "shell_policy": {
                "workspace_root": str(tmp_path),
                "path_exceptions": [
                    {
                        "command": "rm",
                        "args": ["-rf"],
                        "path": "/",
                    }
                ],
            }
        }
    )

    decision = policy.evaluate_shell_command("rm -rf /")
    assert decision.allowed is False
    assert decision.policy_level == "global_deny"


def test_policy_workspace_boundary_blocks_outside_paths(tmp_path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    policy = PolicyEngine({"shell_policy": {"workspace_root": str(workspace_root)}})

    decision = policy.evaluate_shell_command("cat ../secret.txt")
    assert decision.allowed is False
    assert decision.policy_level == "workspace_allow"


def test_policy_file_path_validation():
    policy = PolicyEngine()
    assert policy.evaluate_file_path("src/main.py").allowed is True
    assert policy.evaluate_file_path("../outside.py").allowed is False
    assert policy.evaluate_file_path("/etc/passwd").allowed is False
    assert policy.evaluate_file_path(".env").allowed is False
    assert policy.evaluate_file_path("secrets/key.txt").allowed is False


def test_policy_patch_validation():
    policy = PolicyEngine()
    safe_patch = "--- a.py\n+++ a.py\n@@ -1 +1 @@\n-x = 1\n+x = 2"
    assert policy.evaluate_patch(safe_patch).allowed is True

    unsafe_patch_file = "--- policy.py\n+++ policy.py\n..."
    assert policy.evaluate_patch(unsafe_patch_file).allowed is False

    unsafe_patch_cmd = "--- a.py\n+++ a.py\n+import os; os.system('sudo rm -rf /')"
    assert policy.evaluate_patch(unsafe_patch_cmd).allowed is False


def test_policy_describe_for_agent():
    policy = PolicyEngine()
    description = policy.describe_for_agent()
    assert "Security & Execution Policy" in description
    assert "Allowed tools" in description
    assert "Global deny" in description
    assert "id_rsa" not in description or "deny" in description.lower()
