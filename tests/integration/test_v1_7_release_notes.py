import os
import re

import pytest

RELEASE_NOTES_PATH = "docs/V1_7_RELEASE_NOTES.md"


@pytest.fixture
def release_notes_content():
    assert os.path.exists(RELEASE_NOTES_PATH), f"File {RELEASE_NOTES_PATH} not found"
    with open(RELEASE_NOTES_PATH, encoding="utf-8") as f:
        return f.read()


def test_release_notes_exists():
    assert os.path.exists(RELEASE_NOTES_PATH)


def test_mentions_local_ai_appliance(release_notes_content):
    assert "Local AI Appliance" in release_notes_content, "Missing mention of 'Local AI Appliance'"


def test_mentions_v1_6_x_versions(release_notes_content):
    versions = ["v1.6.0", "v1.6.1", "v1.6.2", "v1.6.3", "v1.6.4", "v1.6.5", "v1.6.6", "v1.6.7"]
    for v in versions:
        assert v in release_notes_content, f"Missing mention of version {v}"


def test_mentions_psp_pix_limitations(release_notes_content):
    content_lower = release_notes_content.lower()
    assert "psp" in content_lower and "fora do escopo" in content_lower, "Missing PSP limitation"
    assert "pix" in content_lower and "fora do escopo" in content_lower, "Missing PIX limitation"


def test_no_secrets_in_release_notes(release_notes_content):
    # Basic check for obvious secrets
    secret_patterns = [r"sk-[A-Za-z0-9]{20,}", r"ghp_[A-Za-z0-9]{36}"]
    for pattern in secret_patterns:
        match = re.search(pattern, release_notes_content)
        assert not match, f"Potential secret found matching pattern: {pattern}"


def test_readme_points_to_release_notes():
    readme_path = "README.md"
    assert os.path.exists(readme_path)
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()
    assert "docs/V1_7_RELEASE_NOTES.md" in content, (
        "README.md does not point to V1_7_RELEASE_NOTES.md"
    )
