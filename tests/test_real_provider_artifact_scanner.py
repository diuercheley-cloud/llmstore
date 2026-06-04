import subprocess


def test_scanner_help():
    res = subprocess.run(["./scripts/scan-real-provider-artifacts.sh", "--help"], capture_output=True, text=True)
    assert "Usage:" in res.stdout
