import os

import pytest

CHANGELOG_PATH = "CHANGELOG.md"

@pytest.fixture
def changelog_content():
    assert os.path.exists(CHANGELOG_PATH), f"File {CHANGELOG_PATH} not found"
    with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
        return f.read()

def test_changelog_contains_v1_7_0(changelog_content):
    assert "v1.7.0-local-ai-appliance" in changelog_content, "CHANGELOG.md missing v1.7.0-local-ai-appliance entry"

def test_changelog_mentions_v1_6_x_consolidation(changelog_content):
    assert "Consolidação da linha v1.6.x" in changelog_content or "v1.6.0 a v1.6.7" in changelog_content, "CHANGELOG.md should mention consolidation of v1.6.x line"
