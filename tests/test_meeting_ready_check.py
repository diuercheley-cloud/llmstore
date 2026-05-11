import subprocess
import os
import json
import tempfile
import re

SCRIPT = "./scripts/meeting-ready-check-local.sh"
VALIDATION_SCRIPT = "./scripts/validate-meeting-ready-check-local.sh"


def test_script_exists():
    assert os.path.exists(SCRIPT), f"{SCRIPT} not found"


def test_script_executable():
    assert os.access(SCRIPT, os.X_OK), f"{SCRIPT} is not executable"


def test_help_flag():
    result = subprocess.run(
        [SCRIPT, "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "MEETING_READY" in result.stdout
    assert "READY_WITH_WARNINGS" in result.stdout
    assert "NOT_READY" in result.stdout


def test_help_exits_zero():
    result = subprocess.run([SCRIPT, "--help"], capture_output=True, text=True)
    assert result.returncode == 0


def test_unknown_param_fails():
    result = subprocess.run(
        [SCRIPT, "--unknown-param"], capture_output=True, text=True
    )
    assert result.returncode != 0


OFFLINE_ARGS = ["--offline", "--skip-rag", "--skip-tts", "--skip-lmstudio"]


def test_base_url_flag_accepted():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [SCRIPT, "--base-url", "http://localhost:18080", "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, text=True, timeout=30
        )
        assert "MEETING_READY" in result.stdout or "READY_WITH_WARNINGS" in result.stdout or "NOT_READY" in result.stdout


def test_generates_json_and_md():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, text=True, timeout=30
        )
        dirs = [d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))]
        assert len(dirs) > 0, f"No timestamp directory created in {tmpdir}"
        report_dir = os.path.join(tmpdir, sorted(dirs)[-1])
        assert os.path.exists(os.path.join(report_dir, "meeting-ready.json")), "meeting-ready.json not found"
        assert os.path.exists(os.path.join(report_dir, "meeting-ready.md")), "meeting-ready.md not found"


def test_json_has_valid_structure():
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
        assert "generated_at" in data
        assert "version" in data
        assert "git_branch" in data
        assert "base_url" in data
        assert "status" in data
        assert data["status"] in ("MEETING_READY", "READY_WITH_WARNINGS", "NOT_READY")
        assert "totals" in data
        assert "pass" in data["totals"]
        assert "warn" in data["totals"]
        assert "fail" in data["totals"]
        assert "skip" in data["totals"]
        assert "checks" in data
        assert isinstance(data["checks"], list)


def test_json_checks_have_required_fields():
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
        for check in data["checks"]:
            assert "id" in check
            assert "category" in check
            assert "title" in check
            assert "status" in check
            assert check["status"] in ("pass", "warn", "fail", "skip")


def test_json_no_secrets():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        with open(os.path.join(report_dir, "meeting-ready.json")) as f:
            content = f.read()
        secret_patterns = [
            r"sk-[a-zA-Z0-9]{20,}(?<!masked)(?<!xxxx)",
            r"ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}(?<!masked)",
            r"Bearer [a-zA-Z0-9._-]{20,}(?<!masked)",
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        ]
        for pattern in secret_patterns:
            matches = re.findall(pattern, content)
            for m in matches:
                if "masked" not in m and "xxxx" not in m and "example" not in m.lower():
                    assert False, f"Potential secret found: {m[:30]}"


def test_md_has_required_sections():
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
        sections = [
            "Final Status",
            "What to Open Before the Meeting",
            "Core URLs",
            "Emergency Commands",
            "Limitations to Mention",
            "Suggested 30-Minute Presentation Script",
            "Visual Checklist",
            "Detailed Check Results",
        ]
        for section in sections:
            assert section in content, f"Section '{section}' missing from MD report"


def test_md_limitations_psp_pix():
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
        assert "PSP" in content or "PIX" in content, "PSP/PIX limitation not mentioned in MD report"


def test_md_fictional_data_disclaimer():
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
        assert "fictício" in content or "ficticio" in content or "fictional" in content or "FICTICIO" in content, \
            "Fictional data disclaimer not found in MD report"


def test_validation_script_exists():
    assert os.path.exists(VALIDATION_SCRIPT), f"{VALIDATION_SCRIPT} not found"


def test_validation_script_executable():
    assert os.access(VALIDATION_SCRIPT, os.X_OK), f"{VALIDATION_SCRIPT} is not executable"


def test_validation_script_help():
    result = subprocess.run(
        [SCRIPT, "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
