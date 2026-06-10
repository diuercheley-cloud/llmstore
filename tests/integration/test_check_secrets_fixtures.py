import shutil
import subprocess
from pathlib import Path

SCRIPT_PATH = Path("scripts/validators/check-secrets.sh").resolve()


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)


def run_check(args, cwd=None):
    return subprocess.run([str(SCRIPT_PATH), *args], cwd=cwd, capture_output=True, text=True)


def test_real_secret_temp_file_fails(tmp_path):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("ADMIN_TOKEN=" + "very-secret-token-1234567890" + "\n")

    result = run_check(["--path", str(tmp_path)])

    assert result.returncode == 1
    assert "real_secret_suspected" in result.stdout
    assert "Potential secret in" in result.stdout


def test_safe_fixture_passes():
    result = run_check(["--path", "tests/fixtures", "--verbose"])

    assert result.returncode == 0
    assert "fixture_expected" in result.stdout
    assert "Safe fixture in tests/fixtures/fake_secret_sample.txt" in result.stdout


def test_fake_secret_without_marker_fails(tmp_path):
    fixture_dir = tmp_path / "tests" / "fixtures"
    fixture_dir.mkdir(parents=True)
    fake_file = fixture_dir / "fake_no_marker.txt"
    fake_file.write_text("sk-" + "thisisaverylongfakesecretkeythatshouldfail" + "\n")

    result = run_check(["--path", str(tmp_path)])

    assert result.returncode == 1
    assert "real_secret_suspected" in result.stdout


def test_secret_in_releases_is_classified_as_obsolete_release_file(tmp_path):
    release_dir = tmp_path / "releases" / "v1.0"
    release_dir.mkdir(parents=True)
    secret_file = release_dir / "leak.txt"
    secret_file.write_text("ADMIN_TOKEN=" + "very-secret-token-1234567890" + "\n")

    result = run_check(["--path", str(tmp_path), "--verbose"])

    assert result.returncode == 1
    assert "obsolete_release_file" in result.stdout
    assert "releases/v1.0/leak.txt" in result.stdout


def test_staged_flag_detects_secret_in_staged_file(tmp_path):
    init_git_repo(tmp_path)

    secret_file = tmp_path / "tests" / "input.txt"
    secret_file.parent.mkdir(parents=True)
    secret_file.write_text("JWT_SECRET=" + "runtime-generated-secret-123456" + "\n")
    subprocess.run(["git", "add", "tests/input.txt"], cwd=tmp_path, check=True)

    result = run_check(["--staged"], cwd=tmp_path)

    assert result.returncode == 1
    assert "tests/input.txt" in result.stdout


def test_path_flag_works_with_safe_fixture_tree(tmp_path):
    fixture_root = tmp_path / "tests" / "fixtures"
    fixture_root.mkdir(parents=True)
    source_fixture = Path("tests/fixtures/fake_secret_sample.txt")
    shutil.copy2(source_fixture, fixture_root / "fake_secret_sample.txt")

    result = run_check(["--path", str(tmp_path), "--verbose"])

    assert result.returncode == 0
    assert "fixture_expected" in result.stdout
