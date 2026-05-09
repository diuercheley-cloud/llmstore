import os
import subprocess
from pathlib import Path


SCRIPT_PATH = Path("scripts/check-secrets.sh").resolve()


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)


def run_check(args, cwd=None):
    return subprocess.run([str(SCRIPT_PATH), *args], cwd=cwd, capture_output=True, text=True)


def test_script_exists():
    assert SCRIPT_PATH.is_file()
    assert os.access(SCRIPT_PATH, os.X_OK)


def test_hook_exists():
    hook_path = Path(".githooks/pre-commit")
    assert hook_path.is_file()
    assert os.access(hook_path, os.X_OK)


def test_detects_secret(tmp_path):
    init_git_repo(tmp_path)

    secret_val = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
    dirty_file = tmp_path / "dirty.txt"
    dirty_file.write_text(f"Key is {secret_val}\n")
    subprocess.run(["git", "add", "dirty.txt"], cwd=tmp_path, check=True)

    result = run_check(["--all"], cwd=tmp_path)

    assert result.returncode == 1
    assert "Potential secret in dirty.txt" in result.stdout
    assert "real_secret_suspected" in result.stdout
    assert secret_val not in result.stdout
    assert "sk-a" in result.stdout


def test_allows_safe_patterns(tmp_path):
    init_git_repo(tmp_path)

    safe_file = tmp_path / "safe.txt"
    safe_file.write_text(
        "ADMIN_TOKEN=admin-token-123\n"
        "MY_KEY=sk-local-example\n"
        "URL=http://user:changeme@localhost:8080\n"
    )
    subprocess.run(["git", "add", "safe.txt"], cwd=tmp_path, check=True)

    result = run_check(["--all"], cwd=tmp_path)

    assert result.returncode == 0
    assert "No secrets found" in result.stdout


def test_detects_pem_file(tmp_path):
    init_git_repo(tmp_path)

    pem_file = tmp_path / "cert.pem"
    pem_file.write_text("fake pem content\n")
    subprocess.run(["git", "add", "cert.pem"], cwd=tmp_path, check=True)

    result = run_check(["--all"], cwd=tmp_path)

    assert result.returncode == 1
    assert "Potential secret file found by extension" in result.stdout
    assert "cert.pem" in result.stdout


def test_staged_mode_only_checks_staged_files(tmp_path):
    init_git_repo(tmp_path)

    unstaged_file = tmp_path / "unstaged.txt"
    staged_file = tmp_path / "staged.txt"
    unstaged_file.write_text("ADMIN_TOKEN=" + "very-secret-token-12345" + "\n")
    staged_file.write_text("JWT_SECRET=" + "another-secret-token-67890" + "\n")
    subprocess.run(["git", "add", "staged.txt"], cwd=tmp_path, check=True)

    result = run_check(["--staged"], cwd=tmp_path)

    assert result.returncode == 1
    assert "staged.txt" in result.stdout
    assert "unstaged.txt" not in result.stdout
