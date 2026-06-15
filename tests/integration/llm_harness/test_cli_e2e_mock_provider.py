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
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "plan",
                            "reason": "Identify and fix spelling bug",
                            "payload": {"message": "I will read hello.py and fix the spelling"},
                        }
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 50},
    },
    # 2. Read File
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "read_file",
                            "reason": "Need to see hello.py code",
                            "payload": {"path": "hello.py"},
                        }
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 50},
    },
    # 3. Apply Patch
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "apply_patch",
                            "reason": "Correcting spelling greeting",
                            "payload": {
                                "diff": '--- hello.py\n+++ hello.py\n@@ -1,2 +1,2 @@\n def greet():\n-    return "helko"\n+    return "hello"\n'
                            },
                        }
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 50},
    },
    # 4. Run Tests
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "run_tests",
                            "reason": "Verify the patch passes the test",
                            "payload": {"test_path": "test_hello.py"},
                        }
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 50},
    },
    # 5. Final
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "final",
                            "reason": "Spelling fixed and verified",
                            "payload": {"message": "Bug fixed successfully"},
                        }
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 50},
    },
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


def test_cli_e2e_mock_provider(mock_llm_server):
    """
    E2E standalone CLI execution test against mock HTTP server,
    verifying patch application, report generation, and secret safety.
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        repo_dir = os.path.join(tmp_dir, "repo")
        os.makedirs(repo_dir)

        # Create hello.py with spelling bug
        hello_file = os.path.join(repo_dir, "hello.py")
        with open(hello_file, "w") as f:
            f.write('def greet():\n    return "helko"\n')

        # Create test_hello.py
        test_file = os.path.join(repo_dir, "test_hello.py")
        with open(test_file, "w") as f:
            f.write('from hello import greet\ndef test_greet():\n    assert greet() == "hello"\n')

        config_file = os.path.join(tmp_dir, "config.toml")
        with open(config_file, "w") as f:
            f.write("")

        env = os.environ.copy()
        env["MOCK_API_KEY"] = "sk-super-secret-key"
        env["PYTHONPATH"] = f".{os.pathsep}{os.getcwd()}{os.pathsep}{env.get('PYTHONPATH', '')}"

        cmd = [
            sys.executable,
            "-m",
            "scripts.llm_harness.cli",
            "--config",
            config_file,
            "code",
            "--task",
            "Fix the greeting spelling error in hello.py",
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

        res = subprocess.run(
            cmd,
            cwd=repo_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        assert res.returncode == 0

        # Verify patch was applied
        with open(hello_file) as f:
            content = f.read()
            assert 'return "hello"' in content

        # Verify reports generated
        files = os.listdir(tmp_dir)
        json_reports = [f for f in files if f.startswith("report_") and f.endswith(".json")]
        md_reports = [f for f in files if f.startswith("report_") and f.endswith(".md")]

        assert len(json_reports) == 1
        assert len(md_reports) == 1

        json_report_path = os.path.join(tmp_dir, json_reports[0])
        md_report_path = os.path.join(tmp_dir, md_reports[0])

        with open(json_report_path) as f:
            json_data = json.load(f)
            assert json_data["success"] is True

        # Ensure no secrets leak in stdout, stderr, or reports
        assert "sk-super-secret-key" not in res.stdout
        assert "sk-super-secret-key" not in res.stderr

        with open(json_report_path) as f:
            assert "sk-super-secret-key" not in f.read()

        with open(md_report_path) as f:
            assert "sk-super-secret-key" not in f.read()

    finally:
        shutil.rmtree(tmp_dir)
