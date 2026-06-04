import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_command(args, **kwargs):
    env = os.environ.copy()
    env.update(kwargs.pop("env", {}))
    return subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        **kwargs,
    )


def latest_validation_artifact():
    artifact_root = ROOT / "artifacts" / "local-production-validation"
    subdirs = [path for path in artifact_root.iterdir() if path.is_dir()]
    return max(subdirs, key=lambda path: path.stat().st_mtime)


def test_validate_local_production_full_respects_validation_version():
    version = "v9.9.9-validation-version-test"
    result = run_command(
        ["bash", "scripts/validate-local-production-full.sh"],
        env={
            "VALIDATION_VERSION": version,
            "VALIDATION_METADATA_ONLY": "true",
            "BASE_URL": "http://localhost:18080",
        },
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"Version: {version}" in result.stdout

    artifact_dir = latest_validation_artifact()
    summary_json = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    summary_md = (artifact_dir / "summary.md").read_text(encoding="utf-8")

    assert summary_json["version"] == version
    assert f"**Version:** {version}" in summary_md


def test_release_local_production_passes_version_to_summary_and_manifest():
    version = "v9.9.9-release-metadata-test"
    release_dir = ROOT / "releases" / version
    if release_dir.exists():
        shutil.rmtree(release_dir)

    try:
        result = run_command(
            [
                "bash",
                "scripts/release-local-production.sh",
                "--version",
                version,
                "--allow-dirty",
            ],
            env={
                "VALIDATION_METADATA_ONLY": "true",
                "BASE_URL": "http://localhost:18080",
            },
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert (release_dir / "release-manifest.json").exists()
        assert (release_dir / "summary.json").exists()
        assert (release_dir / "summary.md").exists()

        manifest = json.loads((release_dir / "release-manifest.json").read_text(encoding="utf-8"))
        summary = json.loads((release_dir / "summary.json").read_text(encoding="utf-8"))
        summary_md = (release_dir / "summary.md").read_text(encoding="utf-8")

        assert manifest["version"] == version
        assert summary["version"] == version
        assert f"**Version:** {version}" in summary_md
        assert "v1.4.4-local-demo" not in summary_md
        assert "v1.4.4-local-demo" not in json.dumps(manifest)
        assert "v1.4.4-local-demo" not in json.dumps(summary)
        assert manifest["git_commit"] == summary["git_commit"]
        assert manifest["psp_integration"] is False
        assert manifest["pix_real_billing"] is False
        assert manifest["models_included"] is False
        assert manifest["rag_uploads_included"] is False
        assert manifest["localhost_mode"] is True
    finally:
        if release_dir.exists():
            shutil.rmtree(release_dir)


def test_validate_release_metadata_script_exists_and_validates_current_release():
    script = ROOT / "scripts" / "validate-release-metadata.sh"
    assert script.exists()
    assert os.access(script, os.X_OK)

    version = "v9.9.9-release-validator-test"
    release_dir = ROOT / "releases" / version
    release_dir.mkdir(parents=True, exist_ok=True)
    git_result = run_command(["git", "rev-parse", "HEAD"])
    commit = git_result.stdout.strip() if git_result.returncode == 0 else "unknown"
    if not commit:
        commit = "unknown"

    try:
        (release_dir / "release-manifest.json").write_text(
            json.dumps(
                {
                    "release_name": "llm-inference-stack-local-production",
                    "version": version,
                    "git_commit": commit,
                    "validation_result": "success",
                    "psp_integration": False,
                    "pix_real_billing": False,
                    "models_included": False,
                    "rag_uploads_included": False,
                    "localhost_mode": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (release_dir / "summary.json").write_text(
            json.dumps({"version": version, "git_commit": commit}, indent=2) + "\n",
            encoding="utf-8",
        )
        (release_dir / "summary.md").write_text(
            f"# Summary\n\n- **Version:** {version}\n",
            encoding="utf-8",
        )

        result = run_command(
            [
                "bash",
                "scripts/validate-release-metadata.sh",
                "--version",
                version,
                "--release-dir",
                str(release_dir),
            ]
        )

        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        if release_dir.exists():
            shutil.rmtree(release_dir)
