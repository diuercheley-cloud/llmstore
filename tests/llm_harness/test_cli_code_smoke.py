import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

import pytest

RESPONSES = [
    # 1. Plan
    {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "type": "plan",
                    "reason": "Identify and fix addition bug",
                    "payload": {"message": "I will read app.py and fix the bug"}
                })
            }
        }],
        "usage": {"total_tokens": 100}
    },
    # 2. Read File
    {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "type": "read_file",
                    "reason": "Need to see the code",
                    "payload": {"path": "app.py"}
                })
            }
        }],
        "usage": {"total_tokens": 100}
    },
    # 3. Apply Patch
    {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "type": "apply_patch",
                    "reason": "Correcting subtraction to addition",
                    "payload": {"diff": "--- app.py\n+++ app.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n"}
                })
            }
        }],
        "usage": {"total_tokens": 100}
    },
    # 4. Run Tests
    {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "type": "run_tests",
                    "reason": "Verify the fix",
                    "payload": {"test_path": "tests/test_app.py"}
                })
            }
        }],
        "usage": {"total_tokens": 100}
    },
    # 5. Final
    {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "type": "final",
                    "reason": "Verified and fixed",
                    "payload": {"message": "Bug fixed successfully"}
                })
            }
        }],
        "usage": {"total_tokens": 100}
    }
]


class MockLLMHandler(http.server.BaseHTTPRequestHandler):
    responses = RESPONSES
    count = 0

    def do_POST(self):
        if MockLLMHandler.count >= len(MockLLMHandler.responses):
            resp = MockLLMHandler.responses[-1]
        else:
            resp = MockLLMHandler.responses[MockLLMHandler.count]
            MockLLMHandler.count += 1
        
        content = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        content = json.dumps({"data": [{"id": "gpt-4"}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="function")
def mock_llm_server():
    MockLLMHandler.count = 0
    server = http.server.HTTPServer(("127.0.0.1", 0), MockLLMHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()
    thread.join()


def test_cli_code_smoke_real_cycle(mock_llm_server):
    """
    Smoke test running the real CLI via subprocess with a local mock HTTP server.
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        # Create temp repo base
        repo_dir = os.path.join(tmp_dir, "repo")
        os.makedirs(repo_dir)

        app_file = os.path.join(repo_dir, "app.py")
        with open(app_file, "w") as f:
            f.write("def add(a, b):\n    return a - b\n")

        tests_dir = os.path.join(repo_dir, "tests")
        os.makedirs(tests_dir)
        test_file = os.path.join(tests_dir, "test_app.py")
        with open(test_file, "w") as f:
            f.write("from app import add\ndef test_add():\n    assert add(1, 2) == 3\n")

        config_file = os.path.join(tmp_dir, "config.toml")
        with open(config_file, "w") as f:
            f.write("")

        # Set environment variables for the subprocess
        env = os.environ.copy()
        env["MOCK_API_KEY"] = "sk-test-key"
        # PYTHONPATH=. and os.getcwd() ensures the python subprocess can import scripts.*
        env["PYTHONPATH"] = f".{os.pathsep}{os.getcwd()}{os.pathsep}{env.get('PYTHONPATH', '')}"

        cmd = [
            sys.executable,
            "-m",
            "scripts.llm_harness.cli",
            "--config",
            config_file,
            "code",
            "--task",
            "Fix the bug in app.py",
            "--provider",
            "openai-compatible",
            "--model",
            "gpt-4",
            "--base-url",
            mock_llm_server,
            "--report-output-path",
            tmp_dir,
            "--api-key-env",
            "MOCK_API_KEY",
            "--temp-base-dir",
            tmp_dir,
            "--workspace",
            repo_dir,
        ]

        # Run CLI with repo_dir as cwd so it acts as target repo
        res = subprocess.run(
            cmd,
            cwd=repo_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        print("STDOUT:")
        print(res.stdout)
        print("STDERR:")
        print(res.stderr)

        # 1. Exit code is 0
        assert res.returncode == 0

        # 2. File was altered
        with open(app_file, "r") as f:
            content = f.read()
            assert "return a + b" in content

        # 3. Reports were generated
        files = os.listdir(tmp_dir)
        json_reports = [f for f in files if f.startswith("report_") and f.endswith(".json")]
        md_reports = [f for f in files if f.startswith("report_") and f.endswith(".md")]
        
        assert len(json_reports) == 1
        assert len(md_reports) == 1

        json_report_path = os.path.join(tmp_dir, json_reports[0])
        md_report_path = os.path.join(tmp_dir, md_reports[0])

        with open(json_report_path, "r") as f:
            json_data = json.load(f)
            assert json_data["success"] is True

        with open(md_report_path, "r") as f:
            md_content = f.read()
            assert "Success" in md_content or "success" in md_content.lower()

        # 4. No secrets leaked in stdout, stderr, or reports
        assert "sk-test-key" not in res.stdout
        assert "sk-test-key" not in res.stderr
        
        with open(json_report_path, "r") as f:
            assert "sk-test-key" not in f.read()
            
        with open(md_report_path, "r") as f:
            assert "sk-test-key" not in f.read()

    finally:
        shutil.rmtree(tmp_dir)


def test_cli_stub_warning():
    """
    Validate that a warning is written to the markdown report when stub is explicitly used.
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        repo_dir = os.path.join(tmp_dir, "repo")
        os.makedirs(repo_dir)

        config_file = os.path.join(tmp_dir, "config.toml")
        with open(config_file, "w") as f:
            f.write("")

        env = os.environ.copy()
        env["PYTHONPATH"] = f".{os.pathsep}{os.getcwd()}{os.pathsep}{env.get('PYTHONPATH', '')}"

        cmd = [
            sys.executable,
            "-m",
            "scripts.llm_harness.cli",
            "--config",
            config_file,
            "code",
            "--task",
            "Do nothing task",
            "--provider",
            "stub",
            "--allow-stub-code-agent",
            "--report-output-path",
            tmp_dir,
            "--temp-base-dir",
            tmp_dir,
        ]

        res = subprocess.run(
            cmd,
            cwd=repo_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        assert res.returncode == 0

        # Reports were generated
        files = os.listdir(tmp_dir)
        md_reports = [f for f in files if f.startswith("report_") and f.endswith(".md")]
        assert len(md_reports) == 1

        md_report_path = os.path.join(tmp_dir, md_reports[0])
        with open(md_report_path, "r") as f:
            md_content = f.read()
            # The template report.md.jinja warns when provider == "stub":
            # WARNING: code agent provider is stub; no real task execution was performed.
            assert "WARNING" in md_content
            assert "code agent provider is stub" in md_content

    finally:
        shutil.rmtree(tmp_dir)
