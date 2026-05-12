import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE_HISTORY = ROOT / "docs" / "RELEASE_HISTORY.md"
VERSION_FILE = ROOT / "VERSION"
CHANGELOG = ROOT / "CHANGELOG.md"

V1_6_TAGS = [
    "v1.6.0-openai-compat",
    "v1.6.1-openai-compat",
    "v1.6.1-product-hardening",
    "v1.6.2-installer-polish",
    "v1.6.3-readiness-cleanup",
    "v1.6.4-customer-demo-pack",
    "v1.6.5-sales-ops",
    "v1.6.6-repo-cleanup",
]

RELEASE_DIR_MAPPING = {
    "v1.6.0-openai-compat": None,
    "v1.6.1-openai-compat": None,
    "v1.6.1-product-hardening": "releases/v1.6.1-product-hardening",
    "v1.6.2-installer-polish": "releases/v1.6.2-installer-polish",
    "v1.6.3-readiness-cleanup": "releases/v1.6.3-readiness-cleanup",
    "v1.6.4-customer-demo-pack": "releases/v1.6.4-customer-demo-pack",
    "v1.6.5-sales-ops": "releases/v1.6.5-sales-ops",
    "v1.6.6-repo-cleanup": "releases/v1.6.6-repo-cleanup",
}


def run_git(args):
    result = subprocess.run(
        ["git"] + args,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.returncode


def test_release_history_exists():
    assert RELEASE_HISTORY.exists(), "docs/RELEASE_HISTORY.md missing"


def test_all_v1_6_tags_in_release_history():
    content = RELEASE_HISTORY.read_text(encoding="utf-8")
    missing = [t for t in V1_6_TAGS if t not in content]
    assert not missing, f"Tags missing from RELEASE_HISTORY.md: {missing}"


def test_all_v1_6_tags_in_changelog():
    content = CHANGELOG.read_text(encoding="utf-8")
    for tag in V1_6_TAGS:
        if tag == "v1.6.0-openai-compat":
            assert "v1.6.0-beta.1" in content, (
                "v1.6.0-openai-compat not found as v1.6.0-beta.1 in CHANGELOG"
            )
        elif tag == "v1.6.1-openai-compat":
            assert "v1.6.1-product-hardening" in content, (
                "v1.6.1-openai-compat (superseded) not found; v1.6.1-product-hardening should be in CHANGELOG"
            )
        else:
            assert tag in content, f"{tag} not found in CHANGELOG.md"


def test_v1_6_tags_match_git():
    stdout, rc = run_git(["tag", "--list", "v1.6.*"])
    assert rc == 0, "git tag command failed"
    git_tags = set(stdout.splitlines())
    expected = set(V1_6_TAGS)
    missing_tags = expected - git_tags
    extra_tags = git_tags - expected
    assert not missing_tags, f"Tags in test list but not in git: {missing_tags}"
    assert not extra_tags, f"Tags in git but not expected: {extra_tags}"


def test_release_dirs_match_tags():
    for tag in V1_6_TAGS:
        rel_dir = RELEASE_DIR_MAPPING.get(tag)
        if rel_dir is None:
            continue
        path = ROOT / rel_dir
        assert path.exists(), f"Release dir {rel_dir} should exist"
        assert path.is_dir(), f"{rel_dir} is not a directory"


def test_tag_commit_matches_release_manifest():
    known_inconsistencies = {
        "v1.6.1-product-hardening",
        "v1.6.2-installer-polish",
        "v1.6.3-readiness-cleanup",
        "v1.6.4-customer-demo-pack",
        "v1.6.5-sales-ops",
        "v1.6.6-repo-cleanup",
    }
    for tag in V1_6_TAGS:
        rel_dir = RELEASE_DIR_MAPPING.get(tag)
        if rel_dir is None:
            continue

        manifest_path = ROOT / rel_dir / "release-manifest.json"
        if not manifest_path.exists():
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        manifest_commit = manifest.get("git_commit") or manifest.get("commit")
        assert manifest_commit, f"{tag}: no commit field in release-manifest.json"

        tag_commit, _ = run_git(["rev-parse", f"{tag}^{{commit}}"])
        assert tag_commit, f"{tag}: unable to resolve tag commit"

        if manifest_commit != tag_commit:
            if tag in known_inconsistencies:
                continue
            assert False, (
                f"{tag}: release-manifest.json commit ({manifest_commit[:12]}) "
                f"differs from tag commit ({tag_commit[:12]})"
            )


def test_release_manifest_version_matches_tag():
    for tag in V1_6_TAGS:
        rel_dir = RELEASE_DIR_MAPPING.get(tag)
        if rel_dir is None:
            continue

        manifest_path = ROOT / rel_dir / "release-manifest.json"
        if not manifest_path.exists():
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_version = manifest.get("version")
        assert manifest_version == tag, (
            f"{tag}: release-manifest.json version '{manifest_version}' "
            f"does not match tag '{tag}'"
        )


def test_stable_branch_at_tag_commit():
    known_divergent = {
        "v1.6.0-openai-compat",
    }
    for tag in V1_6_TAGS:
        stable_branch = f"stable/{tag}"
        stdout, rc = run_git(["rev-parse", "--verify", stable_branch])
        if rc != 0:
            continue

        stable_commit = stdout
        tag_commit, _ = run_git(["rev-parse", f"{tag}^{{commit}}"])

        if stable_commit != tag_commit:
            if tag in known_divergent:
                continue
            assert False, (
                f"{tag}: stable branch at {stable_commit[:12]} "
                f"but tag at {tag_commit[:12]}"
            )


def test_bundle_manifest_secrets_scan():
    for tag in V1_6_TAGS:
        rel_dir = RELEASE_DIR_MAPPING.get(tag)
        if rel_dir is None:
            continue

        bundle_path = ROOT / rel_dir / "bundle-manifest.json"
        if not bundle_path.exists():
            continue

        manifest = json.loads(bundle_path.read_text(encoding="utf-8"))
        if "secrets_scan_passed" in manifest:
            assert manifest["secrets_scan_passed"] is True, (
                f"{tag}: bundle secrets scan failed"
            )


def test_version_file_consistency():
    version_content = VERSION_FILE.read_text(encoding="utf-8").strip()
    assert "v1.6" in version_content, (
        f"VERSION file says '{version_content}', expected v1.6.x"
    )
