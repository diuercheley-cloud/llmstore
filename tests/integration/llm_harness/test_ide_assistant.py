import os
import subprocess

import pytest

from scripts.llm_harness.ide.chat import IDEChatSession
from scripts.llm_harness.ide.context_refs import build_context_bundle, parse_refs
from scripts.llm_harness.ide.inline_edit import perform_inline_edit
from scripts.llm_harness.ide.models import ContextBundle, InlineEditRequest
from scripts.llm_harness.ide.rules import load_rules_for_path, parse_rule_file
from scripts.llm_harness.memory import LocalMemory
from scripts.llm_harness.policy import PolicyEngine
from scripts.llm_harness.prompt_builder import PromptBuilder
from scripts.llm_harness.workspace import Workspace


class MockProvider:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.last_messages = None

    async def chat_completion(self, messages):
        self.last_messages = messages
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": self.response_text
                }
            }],
            "usage": {"total_tokens": 100}
        }

@pytest.mark.asyncio
async def test_chat_session_uses_fake_provider_and_responds(temp_repo):
    provider = MockProvider("Simulated assistant reply")
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        policy_engine = PolicyEngine()
        prompt_builder = PromptBuilder(policy_summary=policy_engine.describe_for_agent())
        memory = LocalMemory(memory_dir=os.path.join(temp_repo, ".memory"))
        
        session = IDEChatSession(
            provider=provider,
            prompt_builder=prompt_builder,
            policy_engine=policy_engine,
            memory=memory,
            token_budget=4096
        )
        
        reply = await session.send_message("Hello assistant")
        assert reply == "Simulated assistant reply"
        assert len(session.history) == 2
        assert session.history[0]["content"] == "Hello assistant"
        assert session.history[1]["content"] == "Simulated assistant reply"


@pytest.mark.asyncio
async def test_chat_session_prunes_history_by_token_budget(temp_repo):
    provider = MockProvider("reply")
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        policy_engine = PolicyEngine()
        prompt_builder = PromptBuilder(policy_summary=policy_engine.describe_for_agent())
        session = IDEChatSession(
            provider=provider,
            prompt_builder=prompt_builder,
            policy_engine=policy_engine,
            token_budget=40,
        )

        long_message = "token " * 200
        await session.send_message(long_message)
        await session.send_message(long_message)

        assert provider.last_messages is not None
        assert len(provider.last_messages) < 5
        assert any(message["role"] == "system" for message in provider.last_messages)


@pytest.mark.asyncio
async def test_chat_session_does_not_modify_files_without_explicit_action(temp_repo):
    provider = MockProvider("read-only reply")
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        workspace.write_file("safe.txt", "original\n")
        original = workspace.read_file("safe.txt")

        policy_engine = PolicyEngine()
        prompt_builder = PromptBuilder(policy_summary=policy_engine.describe_for_agent())
        session = IDEChatSession(
            provider=provider,
            prompt_builder=prompt_builder,
            policy_engine=policy_engine,
            token_budget=256,
        )

        await session.send_message("Summarize the workspace")

        assert workspace.read_file("safe.txt") == original

@pytest.mark.asyncio
async def test_context_ref_file_includes_content(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        workspace.write_file("test.py", "# Hello test file\n")
        policy_engine = PolicyEngine()
        
        refs = parse_refs("@file:test.py", workspace)
        assert len(refs) == 1
        assert refs[0].path == "test.py"
        
        bundle = await build_context_bundle(refs, workspace, policy_engine)
        assert len(bundle.files) == 1
        assert bundle.files[0]["path"] == "test.py"
        assert bundle.files[0]["content"] == "# Hello test file\n"
        
        refs_short = parse_refs("@test.py", workspace)
        assert len(refs_short) == 1
        assert refs_short[0].path == "test.py"

@pytest.mark.asyncio
async def test_context_ref_folder_includes_multiple_files_with_limit(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        os.makedirs(os.path.join(workspace.path, "src"))
        workspace.write_file("src/a.py", "print('a')\n" * 10)
        workspace.write_file("src/b.py", "print('b')\n" * 10)
        
        policy_engine = PolicyEngine()
        refs = parse_refs("@folder:src", workspace)
        assert len(refs) == 1
        
        # Budget enough to fit both
        bundle = await build_context_bundle(refs, workspace, policy_engine, token_budget=1000)
        assert len(bundle.files) == 2
        
        # Budget small enough to trigger limit
        bundle_limited = await build_context_bundle(refs, workspace, policy_engine, token_budget=10)
        assert len(bundle_limited.files) < 2

@pytest.mark.asyncio
async def test_path_traversal_in_refs_is_blocked(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        policy_engine = PolicyEngine()
        
        # Path traversal
        refs = parse_refs("@file:../outside.py", workspace)
        with pytest.raises(PermissionError):
            await build_context_bundle(refs, workspace, policy_engine)
            
        refs_folder = parse_refs("@folder:../../outside_dir", workspace)
        with pytest.raises(PermissionError):
            await build_context_bundle(refs_folder, workspace, policy_engine)

@pytest.mark.asyncio
async def test_inline_edit_generates_patch(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        subprocess.run(["git", "init"], cwd=workspace.path, check=True, capture_output=True)
        workspace.write_file("calc.py", "def add(a, b):\n    # TODO implement\n    pass\n")
        subprocess.run(["git", "add", "calc.py"], cwd=workspace.path, check=True, capture_output=True)
        
        policy_engine = PolicyEngine()
        provider = MockProvider("def add(a, b):\n    return a + b\n")
        
        request = InlineEditRequest(
            file_path="calc.py",
            start_line=1,
            end_line=3,
            instruction="implement add",
        )
        
        res = await perform_inline_edit(
            request=request,
            provider=provider,
            policy_engine=policy_engine,
            workspace=workspace,
            dry_run=False
        )
        
        assert res["success"] is True
        assert "def add(a, b):" in res["diff"]
        assert "+    return a + b" in res["diff"]
        
        content = workspace.read_file("calc.py")
        assert "return a + b" in content

@pytest.mark.asyncio
async def test_inline_edit_dry_run_does_not_alter_file(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        subprocess.run(["git", "init"], cwd=workspace.path, check=True, capture_output=True)
        workspace.write_file("calc.py", "def add(a, b):\n    # TODO implement\n    pass\n")
        subprocess.run(["git", "add", "calc.py"], cwd=workspace.path, check=True, capture_output=True)
        
        policy_engine = PolicyEngine()
        provider = MockProvider("def add(a, b):\n    return a + b\n")
        
        request = InlineEditRequest(
            file_path="calc.py",
            start_line=1,
            end_line=3,
            instruction="implement add",
        )
        
        res = await perform_inline_edit(
            request=request,
            provider=provider,
            policy_engine=policy_engine,
            workspace=workspace,
            dry_run=True
        )
        
        assert res["success"] is True
        assert "def add(a, b):" in res["diff"]
        
        content = workspace.read_file("calc.py")
        assert "return a + b" not in content
        assert "pass" in content


@pytest.mark.asyncio
async def test_inline_edit_preserves_indentation_from_provider_output(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        subprocess.run(["git", "init"], cwd=workspace.path, check=True, capture_output=True)
        workspace.write_file("calc.py", "def add(a, b):\n    return a - b\n")
        subprocess.run(["git", "add", "calc.py"], cwd=workspace.path, check=True, capture_output=True)

        policy_engine = PolicyEngine()
        provider = MockProvider("    return a + b\n")

        request = InlineEditRequest(
            file_path="calc.py",
            start_line=2,
            end_line=2,
            instruction="replace implementation",
        )

        res = await perform_inline_edit(
            request=request,
            provider=provider,
            policy_engine=policy_engine,
            workspace=workspace,
            dry_run=False,
        )

        assert res["success"] is True
        assert workspace.read_file("calc.py") == "def add(a, b):\n    return a + b\n"


@pytest.mark.asyncio
async def test_inline_edit_restores_single_line_indentation_when_model_omits_it(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        subprocess.run(["git", "init"], cwd=workspace.path, check=True, capture_output=True)
        workspace.write_file("calc.py", "def add(a, b):\n    return a - b\n")
        subprocess.run(["git", "add", "calc.py"], cwd=workspace.path, check=True, capture_output=True)

        policy_engine = PolicyEngine()
        provider = MockProvider("return a + b\n")

        request = InlineEditRequest(
            file_path="calc.py",
            start_line=2,
            end_line=2,
            instruction="replace implementation",
        )

        res = await perform_inline_edit(
            request=request,
            provider=provider,
            policy_engine=policy_engine,
            workspace=workspace,
            dry_run=False,
        )

        assert res["success"] is True
        assert workspace.read_file("calc.py") == "def add(a, b):\n    return a + b\n"

@pytest.mark.asyncio
async def test_rules_in_harness_rules_enter_prompt(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        os.makedirs(os.path.join(workspace.path, ".harness"))
        workspace.write_file(".harness/rules.md", "Use descriptive names for everything.")
        
        rules = load_rules_for_path("some_file.py", workspace.path)
        assert "descriptive names" in rules
        
        policy_engine = PolicyEngine()
        prompt_builder = PromptBuilder(
            policy_summary=policy_engine.describe_for_agent(),
            rules_context=rules
        )
        
        sys_prompt = prompt_builder.build_system_prompt()
        assert "Custom AI Rules" in sys_prompt
        assert "Use descriptive names for everything." in sys_prompt

@pytest.mark.asyncio
async def test_rules_cannot_free_blocked_command(temp_repo):
    policy_engine = PolicyEngine(config={
        "shell_policy": {
            "global_deny": {
                "commands": ["rm"]
            }
        }
    })
    
    decision = policy_engine.evaluate_shell_command("rm -rf /")
    assert decision.allowed is False
    
    assert policy_engine.evaluate_shell_command("rm -rf /").allowed is False

@pytest.mark.asyncio
async def test_no_secrets_appear_in_prompt_or_report(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        secret_content = "AWS_SECRET = AKIA1234567890ABCDEF\n"
        workspace.write_file("data.txt", secret_content)
        
        policy_engine = PolicyEngine()
        refs = parse_refs("@file:data.txt", workspace)
        bundle = await build_context_bundle(refs, workspace, policy_engine)
        
        content = bundle.files[0]["content"]
        assert "AKIA1234567890ABCDEF" not in content
        assert "[REDACTED_AWS_KEY]" in content

@pytest.mark.asyncio
async def test_context_ref_symbol_ast_search(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        code = "class Calculator:\n    def add(self, a, b):\n        return a + b\n\ndef multiply(a, b):\n    return a * b\n"
        workspace.write_file("math_lib.py", code)
        
        policy_engine = PolicyEngine()
        
        # Test @symbol:Calculator
        refs = parse_refs("@symbol:Calculator", workspace)
        assert len(refs) == 1
        bundle = await build_context_bundle(refs, workspace, policy_engine)
        assert len(bundle.symbols) == 1
        assert bundle.symbols[0]["name"] == "Calculator"
        assert "class Calculator:" in bundle.symbols[0]["content"]
        
        # Test @symbol:multiply
        refs_func = parse_refs("@symbol:multiply", workspace)
        assert len(refs_func) == 1
        bundle_func = await build_context_bundle(refs_func, workspace, policy_engine)
        assert len(bundle_func.symbols) == 1
        assert "def multiply(a, b):" in bundle_func.symbols[0]["content"]

@pytest.mark.asyncio
async def test_context_ref_selection_formats(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        code = "\n".join(f"line_{i}" for i in range(1, 41)) + "\n"
        workspace.write_file("lines.py", code)
        policy_engine = PolicyEngine()
        
        # Format: @selection:path:start-end
        refs1 = parse_refs("@selection:lines.py:10-20", workspace)
        assert len(refs1) == 1
        assert refs1[0].start_line == 10
        assert refs1[0].end_line == 20
        bundle1 = await build_context_bundle(refs1, workspace, policy_engine)
        assert "line_10" in bundle1.selections[0]["content"]
        assert "line_20" in bundle1.selections[0]["content"]
        assert "line_9" not in bundle1.selections[0]["content"]
        assert "line_21" not in bundle1.selections[0]["content"]
        
        # Format: short form selection @path:start-end
        refs2 = parse_refs("@lines.py:5-15", workspace)
        assert len(refs2) == 1
        assert refs2[0].start_line == 5
        assert refs2[0].end_line == 15
        
        # Format: short form single line range @path:15
        refs3 = parse_refs("@lines.py:15", workspace)
        assert len(refs3) == 1
        assert refs3[0].start_line == 15
        assert refs3[0].end_line == 15

def test_context_bundle_helper_methods():
    bundle = ContextBundle()
    assert bundle.is_empty() is True
    
    bundle.files.append({"path": "a.txt", "content": "hello"})
    assert bundle.is_empty() is False
    
    bundle.selections.append({"path": "b.txt", "start_line": 1, "end_line": 2, "content": "world"})
    bundle.symbols.append({"name": "cls", "path": "c.py", "content": "class C:"})
    
    text = bundle.to_text()
    assert "=== Context Reference Bundle ===" in text
    assert "--- File: a.txt ---" in text
    assert "--- Selection: b.txt (lines 1-2) ---" in text
    assert "--- Symbol: cls (in c.py) ---" in text

def test_rules_frontmatter_filtering():
    rule_py = "---\nglobs: *.py\n---\nPython rule."
    rule_glob = "---\nglobs: src/*.md, docs/**/*.md\n---\nGlob rule."
    rule_none = "Global rule."
    
    assert parse_rule_file(rule_py, "test.py") == "Python rule."
    assert parse_rule_file(rule_py, "test.txt") is None
    
    assert parse_rule_file(rule_glob, "src/info.md") == "Glob rule."
    assert parse_rule_file(rule_glob, "test.py") is None
    
    assert parse_rule_file(rule_none, "any.py") == "Global rule."

@pytest.mark.asyncio
async def test_folder_filtering_ignores_hidden_items(temp_repo):
    ws = Workspace(base_path=temp_repo)
    async with ws as workspace:
        os.makedirs(os.path.join(workspace.path, ".git"))
        os.makedirs(os.path.join(workspace.path, "src"))
        workspace.write_file(".git/config", "some git config")
        workspace.write_file("src/.hidden", "hidden file")
        workspace.write_file("src/main.py", "print('hello')")
        
        policy_engine = PolicyEngine()
        refs = parse_refs("@folder:.", workspace)
        bundle = await build_context_bundle(refs, workspace, policy_engine)
        
        paths = [f["path"] for f in bundle.files]
        assert "src/main.py" in paths
        assert ".git/config" not in paths
        assert "src/.hidden" not in paths
