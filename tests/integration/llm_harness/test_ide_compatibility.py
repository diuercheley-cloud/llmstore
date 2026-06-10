import os
import json
import pytest
from unittest.mock import MagicMock

from scripts.llm_harness.ide.importers import import_vscode_config, get_ide_config
from scripts.llm_harness.languages import (
    detect_language_by_filename,
    detect_primary_language_in_workspace,
    LANGUAGES,
)
from scripts.llm_harness.prompt_builder import PromptBuilder
from scripts.llm_harness.diagnostics import diagnose_errors

def test_language_detection():
    # Test by filename
    py_profile = detect_language_by_filename("foo/bar.py")
    assert py_profile is not None
    assert py_profile.name == "Python"
    assert py_profile.comment_style == "#"
    assert py_profile.test_command == "pytest"

    js_profile = detect_language_by_filename("index.js")
    assert js_profile is not None
    assert js_profile.name == "JavaScript"
    assert js_profile.comment_style == "//"
    assert js_profile.test_command == "npm test"

    ts_profile = detect_language_by_filename("src/App.tsx")
    assert ts_profile is not None
    assert ts_profile.name == "TypeScript"

    java_profile = detect_language_by_filename("Main.java")
    assert java_profile is not None
    assert java_profile.name == "Java"

    cs_profile = detect_language_by_filename("Program.cs")
    assert cs_profile is not None
    assert cs_profile.name == "C#"

    # Test unknown extension
    assert detect_language_by_filename("doc.txt") is None


def test_workspace_language_detection(tmp_path):
    # Python workspace
    py_ws = tmp_path / "py_ws"
    py_ws.mkdir()
    (py_ws / "pyproject.toml").write_text("[tool.poetry]")
    assert detect_primary_language_in_workspace(str(py_ws)).name == "Python"

    # JS/TS Workspace
    js_ws = tmp_path / "js_ws"
    js_ws.mkdir()
    (js_ws / "package.json").write_text("{}")
    assert detect_primary_language_in_workspace(str(js_ws)).name == "JavaScript"

    (js_ws / "tsconfig.json").write_text("{}")
    assert detect_primary_language_in_workspace(str(js_ws)).name == "TypeScript"

    # Java Workspace
    java_ws = tmp_path / "java_ws"
    java_ws.mkdir()
    (java_ws / "pom.xml").write_text("<project></project>")
    assert detect_primary_language_in_workspace(str(java_ws)).name == "Java"

    # C# Workspace
    cs_ws = tmp_path / "cs_ws"
    cs_ws.mkdir()
    (cs_ws / "app.csproj").write_text("<Project></Project>")
    assert detect_primary_language_in_workspace(str(cs_ws)).name == "C#"


def test_import_vscode_config(tmp_path):
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir()

    # Create fake settings.json with a secret AWS key
    settings_content = """
    {
        // AWS Key setting
        "aws.api_key": "AKIA1234567890123456",
        "editor.tabSize": 4,
        "editor.formatOnSave": true
    }
    """
    (vscode_dir / "settings.json").write_text(settings_content)

    # Create fake keybindings.json
    keybindings_content = """
    [
        {
            "key": "ctrl+shift+p",
            "command": "workbench.action.showCommands"
        }
    ]
    """
    (vscode_dir / "keybindings.json").write_text(keybindings_content)

    # Create fake extensions.json
    extensions_content = """
    {
        "recommendations": [
            "ms-python.python",
            "github.copilot"
        ]
    }
    """
    (vscode_dir / "extensions.json").write_text(extensions_content)

    # Create fake .cursorrules
    cursor_rules_text = "Always write clean code and redact password=supersecret"
    (tmp_path / ".cursorrules").write_text(cursor_rules_text)
    cursor_rules_dir = tmp_path / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True)
    (cursor_rules_dir / "python.md").write_text("Prefer pytest and api_key=sk-secret")

    # Perform import
    res = import_vscode_config(str(tmp_path), workspace_root=str(tmp_path))

    # Verify settings are parsed and AWS secret is redacted
    settings = res["settings"]
    assert settings["editor.tabSize"] == 4
    assert settings["editor.formatOnSave"] is True
    assert settings["aws.api_key"] == "[REDACTED_AWS_KEY]"

    # Verify keybindings are loaded
    keybindings = res["keybindings"]
    assert len(keybindings) == 1
    assert keybindings[0]["key"] == "ctrl+shift+p"

    # Verify extensions recommendations are loaded but not automatically installed
    extensions = res["extensions"]
    assert "ms-python.python" in extensions
    assert "github.copilot" in extensions

    # Verify cursor rules exist and secrets inside them are redacted
    cursor_rules = res["cursor_rules"]
    assert "Always write clean code" in cursor_rules
    assert "Prefer pytest" in cursor_rules
    assert "supersecret" not in cursor_rules
    assert "sk-secret" not in cursor_rules
    assert "password=[REDACTED]" in cursor_rules

    # Verify retrieval via get_ide_config
    cfg = get_ide_config(workspace_root=str(tmp_path))
    assert cfg["settings"]["editor.tabSize"] == 4
    assert cfg["cursor_rules"] == cursor_rules


def test_prompt_builder_language_profile():
    # PromptBuilder receives language profile
    py_profile = LANGUAGES["python"]
    builder = PromptBuilder(language_profile=py_profile)
    sys_prompt = builder.build_system_prompt()

    assert "Language Profile: Python" in sys_prompt
    assert "Suggested Test Command: pytest" in sys_prompt
    assert "Comment Style: #" in sys_prompt


def test_diagnostics_language_profile():
    # Diagnostic parses and enriches suggested actions with test command
    output = "tests/test_foo.py:12: AssertionError: Expected True but got False"
    py_profile = LANGUAGES["python"]
    diags = diagnose_errors(output, language_profile=py_profile)

    assert len(diags) > 0
    assert "pytest" in diags[0].suggested_action
