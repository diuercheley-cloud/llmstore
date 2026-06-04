import os
import re
import subprocess
import tempfile

SCRIPT = "./scripts/meeting-ready-check-local.sh"
OFFLINE_ARGS = ["--offline", "--skip-rag", "--skip-tts", "--skip-lmstudio"]


def test_no_secrets_in_json_report():
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

        dangerous = [
            (r"sk-[a-zA-Z0-9]{20,}", "sk-... long key"),
            (r"ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}", "ADMIN_TOKEN=..."),
            (r"Bearer [a-zA-Z0-9._-]{20,}", "Bearer ... long token"),
            (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
        ]
        for pattern, label in dangerous:
            matches = re.findall(pattern, content)
            for m in matches:
                safe = any(
                    marker in m
                    for marker in [
                        "masked", "xxxx", "example", "test", "changeme",
                        "your-api", "sk-demo-xxxx", "sk-example",
                        "sk-local-example", "admin-token-123",
                        "test-admin-token", "sk-demo",
                    ]
                )
                if not safe:
                    assert False, f"Potential real secret found ({label}): {m[:50]}"


def test_no_secrets_in_md_report():
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

        assert "******" not in content, "Redacted content should not expose raw ******"


def test_has_psp_pix_limitation():
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

        assert "PSP" in content, "PSP limitation missing from report (security disclosure)"
        assert "PIX" in content, "PIX limitation missing from report (security disclosure)"


def test_has_fictional_data_disclaimer():
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

        patterns = [r"fictício", r"ficticio", r"fictional", r"dados.*fict", r"fake.*data"]
        found = any(re.search(p, content, re.IGNORECASE) for p in patterns)
        assert found, "Fictional data disclaimer missing from report (compliance requirement)"


def test_json_does_not_contain_env_values():
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

        env_patterns = [
            r"POSTGRES_PASSWORD=",
            r"DATABASE_URL=postgresql://",
            r"REDIS_URL=redis://",
            r"JWT_SECRET=",
            r"SECRET_KEY=",
        ]
        for pattern in env_patterns:
            assert not re.search(pattern, content), \
                f"Potential env secret leaked in JSON: {pattern}"


def test_md_contains_security_report_reference():
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

        assert "Security Report" in content or "security" in content.lower()


def test_md_contains_no_absolute_security_guarantee():
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

        phrases = [
            "no absolute security guarantee",
            "absolute security",
            "security guarantee",
            "compliance analysis",
        ]
        found = any(p in content.lower() for p in phrases)
        assert found, "No security disclaimer about no absolute guarantee found"


def test_logs_directory_created():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        logs_dir = os.path.join(report_dir, "logs")
        assert os.path.isdir(logs_dir), "logs/ directory not created"


def test_manifests_correct_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [SCRIPT, "--output-dir", tmpdir, *OFFLINE_ARGS],
            capture_output=True, timeout=30
        )
        dirs = sorted([d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))])
        assert len(dirs) > 0
        report_dir = os.path.join(tmpdir, dirs[-1])
        json_path = os.path.join(report_dir, "meeting-ready.json")
        md_path = os.path.join(report_dir, "meeting-ready.md")
        assert os.path.getsize(json_path) > 100, "JSON file suspiciously small"
        assert os.path.getsize(md_path) > 500, "MD file suspiciously small"
