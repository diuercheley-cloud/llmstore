import json
import os
import subprocess
import tempfile

SCRIPT = "./scripts/validators/meeting-ready-check-local.sh"
OFFLINE_ARGS = ["--offline", "--skip-rag", "--skip-tts", "--skip-lmstudio"]


def test_report_has_correct_totals():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        with open(os.path.join(report_dir, "meeting-ready.json")) as f:
            data = json.load(f)

        totals = data["totals"]
        checks = data["checks"]

        actual_pass = sum(1 for c in checks if c["status"] == "pass")
        actual_warn = sum(1 for c in checks if c["status"] == "warn")
        actual_fail = sum(1 for c in checks if c["status"] == "fail")
        actual_skip = sum(1 for c in checks if c["status"] == "skip")

        assert totals["pass"] == actual_pass, \
            f"pass mismatch: report says {totals['pass']}, actual {actual_pass}"
        assert totals["warn"] == actual_warn, \
            f"warn mismatch: report says {totals['warn']}, actual {actual_warn}"
        assert totals["fail"] == actual_fail, \
            f"fail mismatch: report says {totals['fail']}, actual {actual_fail}"
        assert totals["skip"] == actual_skip, \
            f"skip mismatch: report says {totals['skip']}, actual {actual_skip}"


def test_report_has_git_info():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        with open(os.path.join(report_dir, "meeting-ready.json")) as f:
            data = json.load(f)

        assert data["git_branch"], "git_branch is empty"
        assert data["version"], "version is empty"
        assert data["base_url"] == "http://localhost:18080"


def test_report_cover_all_categories():
    expected_categories = {
        "environment", "api", "readiness", "security", "demo", "ui", "billing", "urls", "docs"
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        with open(os.path.join(report_dir, "meeting-ready.json")) as f:
            data = json.load(f)

        actual_categories = {c["category"] for c in data["checks"]}
        for cat in expected_categories:
            assert cat in actual_categories, \
                f"Category '{cat}' missing from checks (found: {actual_categories})"


def test_report_md_has_status_heading():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        with open(os.path.join(report_dir, "meeting-ready.md")) as f:
            content = f.read()

        assert "MEETING_READY" in content or "READY_WITH_WARNINGS" in content or "NOT_READY" in content


def test_report_md_has_emergency_commands():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        with open(os.path.join(report_dir, "meeting-ready.md")) as f:
            content = f.read()

        assert "Emergency Commands" in content
        assert "make logs" in content or "./scripts/deploy/up.sh" in content or "./scripts/deploy/down.sh" in content


def test_report_md_has_presentation_script():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        with open(os.path.join(report_dir, "meeting-ready.md")) as f:
            content = f.read()

        assert "Suggested 30-Minute Presentation Script" in content
        assert "Opening" in content
        assert "Closing & Next Steps" in content


def test_report_md_has_visual_checklist():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        with open(os.path.join(report_dir, "meeting-ready.md")) as f:
            content = f.read()

        checkbox_count = content.count("[ ]")
        assert checkbox_count >= 10, \
            f"Only {checkbox_count} checkboxes found (expected >= 10)"


def test_report_json_artifacts_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        with open(os.path.join(report_dir, "meeting-ready.json")) as f:
            data = json.load(f)

        artifacts = data.get("artifacts", {})
        assert "report_json" in artifacts
        assert "report_md" in artifacts
        assert artifacts["report_json"].endswith("meeting-ready.json")
        assert artifacts["report_md"].endswith("meeting-ready.md")


def test_md_includes_ui_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        with open(os.path.join(report_dir, "meeting-ready.md")) as f:
            content = f.read()

        assert "Admin Dashboard" in content
        assert "Admin Lab" in content
        assert "Client Portal" in content
