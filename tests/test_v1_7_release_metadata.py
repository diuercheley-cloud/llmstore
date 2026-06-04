import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VERSION = "v1.7.0-local-ai-appliance"
RELEASE_DIR = ROOT / "releases" / VERSION


def test_release_dir_exists():
    assert RELEASE_DIR.exists(), f"releases/{VERSION} not found"


def test_release_manifest_exists():
    fp = RELEASE_DIR / "release-manifest.json"
    assert fp.exists(), "release-manifest.json not found"


def test_bundle_manifest_exists():
    fp = RELEASE_DIR / "bundle-manifest.json"
    assert fp.exists(), "bundle-manifest.json not found"


def test_version_consistency():
    """VERSION file, release-manifest, and bundle-manifest must agree."""
    version_file = ROOT / "VERSION"
    rm = RELEASE_DIR / "release-manifest.json"
    bm = RELEASE_DIR / "bundle-manifest.json"

    v_from_file = version_file.read_text(encoding="utf-8").strip()

    if rm.exists():
        rm_data = json.loads(rm.read_text(encoding="utf-8"))
        v_from_rm = rm_data.get("version", "")
        assert v_from_rm == v_from_file or v_from_rm == VERSION, (
            f"release-manifest version '{v_from_rm}' doesn't match "
            f"VERSION file '{v_from_file}' or expected '{VERSION}'"
        )

    if bm.exists():
        bm_data = json.loads(bm.read_text(encoding="utf-8"))
        v_from_bm = bm_data.get("version", "")
        assert v_from_bm == VERSION, (
            f"bundle-manifest version '{v_from_bm}' != expected '{VERSION}'"
        )


def test_git_metadata_present():
    """Both manifests must have git metadata."""
    rm = RELEASE_DIR / "release-manifest.json"
    bm = RELEASE_DIR / "bundle-manifest.json"

    for fp, name in [(rm, "release-manifest"), (bm, "bundle-manifest")]:
        if not fp.exists():
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        assert "git_branch" in data, f"{name} missing git_branch"
        assert "git_commit" in data, f"{name} missing git_commit"
        assert data["git_branch"], f"{name} has empty git_branch"
        assert data["git_commit"], f"{name} has empty git_commit"


def test_generated_at_timestamp():
    """Both manifests must have valid timestamps."""
    rm = RELEASE_DIR / "release-manifest.json"
    bm = RELEASE_DIR / "bundle-manifest.json"

    for fp, name in [(rm, "release-manifest"), (bm, "bundle-manifest")]:
        if not fp.exists():
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        ts = data.get("generated_at", "")
        assert ts, f"{name} missing generated_at"
        assert "T" in ts, f"{name} generated_at not ISO format: {ts}"
        assert ts.endswith("Z") or "+" in ts, (
            f"{name} generated_at missing timezone: {ts}"
        )


def test_release_manifest_validation_path():
    """release-manifest.json should reference a validation artifact path."""
    fp = RELEASE_DIR / "release-manifest.json"
    if not fp.exists():
        pytest.skip("release-manifest.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    vpath = data.get("validation_artifact_path", "")
    assert vpath, "validation_artifact_path is empty"
    vpath_obj = Path(vpath)
    if not vpath_obj.exists():
        pytest.skip(f"validation_artifact_path '{vpath}' does not exist locally (may have been cleaned)")


def test_release_manifest_scripts_count():
    """release-manifest.json should have scripts_included_count > 0."""
    fp = RELEASE_DIR / "release-manifest.json"
    if not fp.exists():
        pytest.skip("release-manifest.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    count = data.get("scripts_included_count", 0)
    assert count > 0, f"scripts_included_count is {count}"


def test_release_manifest_docs_count():
    """release-manifest.json should have docs_included_count > 0."""
    fp = RELEASE_DIR / "release-manifest.json"
    if not fp.exists():
        pytest.skip("release-manifest.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    count = data.get("docs_included_count", 0)
    assert count > 0, f"docs_included_count is {count}"


def test_bundle_manifest_files_count():
    """bundle-manifest.json should have files_count > 0."""
    fp = RELEASE_DIR / "bundle-manifest.json"
    if not fp.exists():
        pytest.skip("bundle-manifest.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    count = data.get("files_count", 0)
    assert count > 0, f"files_count is {count}"


def test_bundle_manifest_included_paths():
    """bundle-manifest.json must include core paths."""
    fp = RELEASE_DIR / "bundle-manifest.json"
    if not fp.exists():
        pytest.skip("bundle-manifest.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    included = data.get("included_paths", [])
    core = ["control_plane", "scripts", "docker", "Makefile"]
    for item in core:
        assert item in included, f"'{item}' not in included_paths"


def test_checksums_match_bundle_manifest():
    """bundle-checksums.sha256 archive_name must match bundle-manifest.json."""
    cs = RELEASE_DIR / "bundle-checksums.sha256"
    bm = RELEASE_DIR / "bundle-manifest.json"
    if not cs.exists() or not bm.exists():
        pytest.skip("bundle-checksums or bundle-manifest not found")
    bm_data = json.loads(bm.read_text(encoding="utf-8"))
    expected_name = bm_data.get("archive_name", "")
    assert expected_name, "archive_name is empty in bundle-manifest"
    cs_content = cs.read_text(encoding="utf-8").strip()
    assert expected_name in cs_content, (
        f"archive_name '{expected_name}' not found in checksums file"
    )


def test_bundle_manifest_archive_sha256_hex():
    """archive_sha256 in bundle-manifest must be valid hex."""
    fp = RELEASE_DIR / "bundle-manifest.json"
    if not fp.exists():
        pytest.skip("bundle-manifest.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    sha = data.get("archive_sha256", "")
    if sha == "dry-run":
        pytest.skip("dry-run mode, no real checksum")
    assert len(sha) == 64, f"archive_sha256 length is {len(sha)}, expected 64"
    try:
        int(sha, 16)
    except ValueError:
        assert False, f"archive_sha256 is not valid hex: {sha}"


def test_git_commit_format():
    """git_commit must be a valid hex string."""
    rm = RELEASE_DIR / "release-manifest.json"
    bm = RELEASE_DIR / "bundle-manifest.json"
    for fp, name in [(rm, "release-manifest"), (bm, "bundle-manifest")]:
        if not fp.exists():
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        commit = data.get("git_commit", "")
        assert commit != "unknown", f"{name} git_commit is 'unknown'"
        assert len(commit) >= 7, f"{name} git_commit too short: {commit}"
        try:
            int(commit, 16)
        except ValueError:
            assert False, f"{name} git_commit not valid hex: {commit}"
