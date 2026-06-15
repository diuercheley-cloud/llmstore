import subprocess


def test_no_key_leakage(tmp_path):
    out_dir = tmp_path / "artifacts"
    out_dir.mkdir()
    file_path = out_dir / "test.md"
    with open(file_path, "w") as f:
        f.write("Log line with OPENAI_API_KEY=sk-test-key-123\n")

    res = subprocess.run(
        [
            "./scripts/dev/scan-real-provider-artifacts.sh",
            "--path",
            str(out_dir),
            "--fail-on-findings",
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1  # Should fail since it's not redacting and finding exists

    res = subprocess.run(
        ["./scripts/dev/scan-real-provider-artifacts.sh", "--path", str(out_dir), "--redact"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0

    with open(file_path) as f:
        content = f.read()
        assert "sk-test-key-123" not in content
        assert "__redacted_provider_secret__" in content
