import json
import os
import shutil
import tempfile
from argparse import Namespace
from unittest.mock import MagicMock, patch

import httpx
import pytest

from scripts.llm_harness.cli_commands import run_docs_command, run_index_command
from scripts.llm_harness.indexing.ast_index import PythonASTParser
from scripts.llm_harness.indexing.docs import DocsManager
from scripts.llm_harness.indexing.repository_index import RepositoryIndexer
from scripts.llm_harness.indexing.retrieval import get_retrieved_context, query_index
from scripts.llm_harness.indexing.symbol_index import RegexFallbackParser
from scripts.llm_harness.policy import PolicyEngine
from scripts.llm_harness.prompt_builder import PromptBuilder


@pytest.fixture
def temp_indexing_repo():
    """Sets up a temporary repo with files and directories for testing indexer."""
    temp_dir = tempfile.mkdtemp()

    # Python code
    app_py_content = '''"""This is app.py docstring."""
import math
from os import path

class Calculator:
    """A simple calculator class."""
    def __init__(self, start: int = 0):
        self.val = start

    def add(self, x: int) -> int:
        """Adds x to val."""
        self.val += x
        return self.val

def helper_func():
    """A standalone helper function."""
    return 42
'''
    with open(os.path.join(temp_dir, "app.py"), "w", encoding="utf-8") as f:
        f.write(app_py_content)

    # JS Code
    js_content = """
// import statement
import { helper } from "./utils.js";
const config = require("config-lib");

class Parser {
  constructor() {}
}

function processData(data) {
  return data;
}
"""
    with open(os.path.join(temp_dir, "script.js"), "w", encoding="utf-8") as f:
        f.write(js_content)

    # Secret file (should be redacted)
    secret_content = '''
def leak_secret():
    """API secret key: api_key=bearer-test-token """
    # password=bearer-test-token
'''
    with open(os.path.join(temp_dir, "secret_config.py"), "w", encoding="utf-8") as f:
        f.write(secret_content)

    # Gitignore
    gitignore_content = """
# ignore logs
*.log
# ignore specific folder
ignored_dir/
"""
    with open(os.path.join(temp_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(gitignore_content)

    # Create ignored folder
    os.makedirs(os.path.join(temp_dir, "ignored_dir"))
    with open(os.path.join(temp_dir, "ignored_dir", "ignored.py"), "w", encoding="utf-8") as f:
        f.write("def ignored_function():\n    pass\n")

    # Create default ignored folder (e.g. node_modules)
    os.makedirs(os.path.join(temp_dir, "node_modules"))
    with open(os.path.join(temp_dir, "node_modules", "package.json"), "w", encoding="utf-8") as f:
        f.write('{"name": "test"}')

    # Create an ignored pattern file (like a .log file)
    with open(os.path.join(temp_dir, "build.log"), "w", encoding="utf-8") as f:
        f.write("building system...\n")

    yield temp_dir
    shutil.rmtree(temp_dir)


def test_python_ast_parser():
    parser = PythonASTParser()
    content = '''"""Module docstring."""
import sys
from os import environ

class User:
    """User representation."""
    def __init__(self, username):
        self.username = username

    def get_name(self) -> str:
        """Gets name."""
        return self.username

def get_active_users(limit: int):
    """Retrieves active users."""
    return []
'''
    result = parser.parse(content)

    # Imports
    assert "sys" in result["imports"]
    assert "os" in result["imports"]

    # Classes
    assert len(result["classes"]) == 1
    cls = result["classes"][0]
    assert cls["name"] == "User"
    assert cls["docstring"] == "User representation."
    assert cls["start_line"] > 0

    # Methods
    assert len(cls["methods"]) == 2
    method_names = {m["name"] for m in cls["methods"]}
    assert "__init__" in method_names
    assert "get_name" in method_names

    get_name_method = next(m for m in cls["methods"] if m["name"] == "get_name")
    assert get_name_method["docstring"] == "Gets name."

    # Functions
    assert len(result["functions"]) == 1
    func = result["functions"][0]
    assert func["name"] == "get_active_users"
    assert func["docstring"] == "Retrieves active users."
    assert func["args"] == ["limit"]


def test_regex_fallback_parser():
    parser = RegexFallbackParser()
    content = """
    import { Component } from "@angular/core";
    const fs = require("fs");

    class AngularComp {
        title = "demo";
    }

    interface DataModel {
        id: string;
    }

    function calculateTotal(items) {
        return items.length;
    }

    customFunc() {
        console.log("no keyword function match sample");
    }
    """
    result = parser.parse(content)

    # Imports
    assert "@angular/core" in result["imports"]
    assert "fs" in result["imports"]

    # Classes (extracts both class and interface definitions)
    class_names = {c["name"] for c in result["classes"]}
    assert "AngularComp" in class_names
    assert "DataModel" in class_names

    # Functions
    func_names = {f["name"] for f in result["functions"]}
    assert "calculateTotal" in func_names


def test_repository_indexer_and_ignore_rules(temp_indexing_repo):
    indexer = RepositoryIndexer(workspace_root=temp_indexing_repo)
    indexed = indexer.build_index()

    # Verify that files are indexed
    assert "app.py" in indexed
    assert "script.js" in indexed
    assert "secret_config.py" in indexed

    # Verify ignore patterns
    assert "ignored_dir/ignored.py" not in indexed
    assert "node_modules/package.json" not in indexed
    assert "build.log" not in indexed

    # Check content of the index for secret redaction
    index_file_path = os.path.join(temp_indexing_repo, ".llm_harness_index", "repo_index.json")
    assert os.path.exists(index_file_path)

    with open(index_file_path, encoding="utf-8") as f:
        data = json.load(f)

    # Check secret redaction
    assert "secret_config.py" in data
    # The placeholder token must not be in the metadata or hash
    # Because sanitizer redacts secrets
    metadata_str = json.dumps(data["secret_config.py"])
    assert "bearer-test-token" not in metadata_str
    assert "[REDACTED" in metadata_str


def test_retrieval_query_ranking(temp_indexing_repo):
    indexer = RepositoryIndexer(workspace_root=temp_indexing_repo)
    indexer.build_index()

    # Query for path/file
    results_path = query_index("app", workspace_root=temp_indexing_repo)
    assert len(results_path) > 0
    # app.py should have higher score because of the path name match
    assert results_path[0]["path"] == "app.py"
    assert results_path[0]["score"] >= 15

    # Query for class/function symbol
    results_symbol = query_index("Calculator", workspace_root=temp_indexing_repo)
    assert len(results_symbol) > 0
    assert "Calculator" in results_symbol[0]["symbols"]
    assert results_symbol[0]["path"] == "app.py"

    # Query for keyword content
    results_content = query_index("standalone", workspace_root=temp_indexing_repo)
    assert len(results_content) > 0
    assert results_content[0]["path"] == "app.py"

    results_language = query_index("lang:python Calculator", workspace_root=temp_indexing_repo)
    assert len(results_language) > 0
    assert all(result["language"] == "python" for result in results_language)


def test_get_retrieved_context_and_prompt_builder(temp_indexing_repo):
    indexer = RepositoryIndexer(workspace_root=temp_indexing_repo)
    indexer.build_index()

    context = get_retrieved_context(
        "Calculator", workspace_root=temp_indexing_repo, max_tokens=1000
    )
    assert "=== Retrieved Context ===" in context
    assert "app.py" in context
    assert "class Calculator" in context

    # Test integration with PromptBuilder
    pb = PromptBuilder(retrieved_context=context)
    task_prompt = pb.build_task_prompt("Show me how to use the calculator")

    assert "### Context" in task_prompt
    assert "=== Retrieved Context ===" in task_prompt
    assert "class Calculator" in task_prompt
    assert "Show me how to use the calculator" in task_prompt


def test_docs_manager_crud(temp_indexing_repo):
    docs_mgr = DocsManager(workspace_root=temp_indexing_repo)

    # Add external doc configuration
    docs_mgr.add_doc(
        name="FastAPI",
        url="https://fastapi.tiangolo.com/tutorial/",
        allowlist_domain="fastapi.tiangolo.com",
    )

    configs = docs_mgr.load_config()
    assert len(configs) == 1
    assert configs[0]["name"] == "FastAPI"
    assert configs[0]["url"] == "https://fastapi.tiangolo.com/tutorial/"
    assert configs[0]["allowlist_domain"] == "fastapi.tiangolo.com"

    # Overwrite domain and url
    docs_mgr.add_doc(
        name="FastAPI",
        url="https://fastapi.tiangolo.com/index.html",
        allowlist_domain="fastapi.tiangolo.com",
    )
    configs = docs_mgr.load_config()
    assert len(configs) == 1
    assert configs[0]["url"] == "https://fastapi.tiangolo.com/index.html"


def test_docs_manager_policy_checks(temp_indexing_repo):
    # Initialize with default policy which denies network
    policy = PolicyEngine(config={"allow_network": False})
    docs_mgr = DocsManager(workspace_root=temp_indexing_repo, policy_engine=policy)

    docs_mgr.add_doc(
        name="FastAPI",
        url="https://fastapi.tiangolo.com/index.html",
        allowlist_domain="fastapi.tiangolo.com",
    )

    # Attempt fetch without network policy -> raises PermissionError
    with pytest.raises(PermissionError, match="Network fetch is disabled"):
        docs_mgr.fetch_doc("FastAPI")

    # Domain mismatch check
    policy_allowed = PolicyEngine(config={"allow_network": True})
    docs_mgr_allowed = DocsManager(workspace_root=temp_indexing_repo, policy_engine=policy_allowed)

    docs_mgr_allowed.add_doc(
        name="FastAPI-Bad",
        url="https://attacker.com/fake-docs",
        allowlist_domain="fastapi.tiangolo.com",
    )

    with pytest.raises(PermissionError, match="does not match allowed domain"):
        docs_mgr_allowed.fetch_doc("FastAPI-Bad")


@patch("httpx.get")
def test_docs_manager_fetching_and_cache(mock_get, temp_indexing_repo):
    policy = PolicyEngine(config={"allow_network": True})
    docs_mgr = DocsManager(workspace_root=temp_indexing_repo, policy_engine=policy)

    docs_mgr.add_doc(
        name="FastAPI",
        url="https://fastapi.tiangolo.com/index.html",
        allowlist_domain="fastapi.tiangolo.com",
    )

    # Mock response HTML with a script tag to test stripping
    mock_html = """
    <html>
      <head>
        <title>FastAPI Title</title>
        <script>console.log("malicious code here");</script>
        <style>body { color: red; }</style>
      </head>
      <body>
        <h1>FastAPI Reference Documentation</h1>
        <p>This is the official docs page.</p>
        <p>API Key leak test: api_key=bearer-test-token</p>
      </body>
    </html>
    """
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = mock_html
    mock_get.return_value = mock_response

    # Fetch document
    content = docs_mgr.fetch_doc("FastAPI")

    # Verify HTMl and script stripping
    assert "malicious code here" not in content
    assert "body { color: red; }" not in content
    assert "FastAPI Reference Documentation" in content
    assert "This is the official docs page." in content
    # Secret should be redacted
    assert "bearer-test-token" not in content
    assert "[REDACTED]" in content or "[REDACTED_IMAGE_BASE64]" not in content  # sanitizer check

    # Verify cache
    cached = docs_mgr.get_cached_doc("FastAPI")
    assert cached == content

    # Test refresh docs
    # Change mock content to ensure it executes httpx.get again
    mock_response.text = "<html><body>Updated FastAPI doc</body></html>"
    docs_mgr.refresh_docs()

    updated_cached = docs_mgr.get_cached_doc("FastAPI")
    assert updated_cached == "Updated FastAPI doc"

    prompt_context = docs_mgr.build_prompt_context()
    assert "=== External Documentation Context ===" in prompt_context
    assert "FastAPI" in prompt_context
    assert "Updated FastAPI doc" in prompt_context

    prompt_builder = PromptBuilder(retrieved_context=prompt_context)
    system_prompt = prompt_builder.build_system_prompt()
    assert "## Retrieved Context" in system_prompt
    assert "Updated FastAPI doc" in system_prompt


def test_cli_index_build_and_query(temp_indexing_repo):
    # Test "llm-harness index build" and query CLI commands
    # Pre-populate some files in temp_indexing_repo
    with open(os.path.join(temp_indexing_repo, "app.py"), "w", encoding="utf-8") as f:
        f.write("def my_special_function():\n    pass\n")

    # Test CLI index build
    args_build = Namespace(command="index", index_command="build", workspace=temp_indexing_repo)

    with patch("builtins.print") as mock_print:
        run_index_command(args_build)
        # Verify success output
        any_success = any("SUCCESS: Indexed" in call[0][0] for call in mock_print.call_args_list)
        assert any_success

    # Test CLI index query
    args_query = Namespace(
        command="index",
        index_command="query",
        query="my_special_function",
        workspace=temp_indexing_repo,
    )

    with patch("builtins.print") as mock_print:
        run_index_command(args_query)
        # Verify matches output
        any_match = any(
            "Found" in call[0][0] and "matches" in call[0][0] for call in mock_print.call_args_list
        )
        assert any_match


def test_cli_docs_add_and_refresh(temp_indexing_repo):
    # Test CLI docs commands
    args_add = Namespace(
        command="docs",
        docs_command="add",
        name="FastAPI",
        url="https://fastapi.tiangolo.com/index.html",
        allowlist_domain="fastapi.tiangolo.com",
        workspace=temp_indexing_repo,
        config=None,
        agent_id=None,
        provider=None,
        model=None,
        base_url=None,
        sandbox=None,
        docker_image=None,
        self_heal=None,
        api_key_env=None,
        timeout=None,
        local_model_timeout=None,
        auto_increase_timeout=None,
        max_retries=None,
        stream=None,
        stream_local_default=None,
        verbose_stream=None,
        tool_calling=None,
        supports_tool_calling=None,
        workspace_mount_path=None,
        temp_base_dir=None,
        sandbox_network=None,
        proxy_url=None,
        loop_timeout=None,
        max_output_chars=None,
        report_output_path=None,
        cache=None,
        no_cache=False,
        cache_dir=None,
        pricing_file=None,
        max_cost_per_run=None,
        max_tokens_per_run=None,
        memory=None,
        memory_dir=None,
        memory_retention_days=None,
        agent_mode=None,
        approval_mode=None,
        approval_default=None,
        edit_action_before_run=None,
        checkpoint_dir=None,
        checkpoint_every_step=None,
        multimodal=None,
        max_tokens=None,
    )

    with patch("builtins.print") as mock_print:
        run_docs_command(args_add)
        any_success = any(
            "SUCCESS: Config updated." in call[0][0] for call in mock_print.call_args_list
        )
        assert any_success

    # Verify YAML is present
    yaml_path = os.path.join(temp_indexing_repo, ".harness.yaml")
    assert os.path.exists(yaml_path)

    # Test docs refresh command
    args_refresh = Namespace(
        command="docs",
        docs_command="refresh",
        workspace=temp_indexing_repo,
        config=None,
        agent_id=None,
        provider=None,
        model=None,
        base_url=None,
        sandbox=None,
        docker_image=None,
        self_heal=None,
        api_key_env=None,
        timeout=None,
        local_model_timeout=None,
        auto_increase_timeout=None,
        max_retries=None,
        stream=None,
        stream_local_default=None,
        verbose_stream=None,
        tool_calling=None,
        supports_tool_calling=None,
        workspace_mount_path=None,
        temp_base_dir=None,
        sandbox_network=None,
        proxy_url=None,
        loop_timeout=None,
        max_output_chars=None,
        report_output_path=None,
        cache=None,
        no_cache=False,
        cache_dir=None,
        pricing_file=None,
        max_cost_per_run=None,
        max_tokens_per_run=None,
        memory=None,
        memory_dir=None,
        memory_retention_days=None,
        agent_mode=None,
        approval_mode=None,
        approval_default=None,
        edit_action_before_run=None,
        checkpoint_dir=None,
        checkpoint_every_step=None,
        multimodal=None,
        max_tokens=None,
    )

    # Mock fetch_doc to prevent external network request or failure
    with patch("scripts.llm_harness.indexing.docs.DocsManager.fetch_doc") as mock_fetch:
        with patch("builtins.print") as mock_print:
            run_docs_command(args_refresh)
            mock_fetch.assert_called_once_with("FastAPI")
            any_success = any(
                "SUCCESS: Refresh completed." in call[0][0] for call in mock_print.call_args_list
            )
            assert any_success
