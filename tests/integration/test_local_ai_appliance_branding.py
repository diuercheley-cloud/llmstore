import os

import pytest

BRANDING_DOC = "docs/LOCAL_AI_APPLIANCE_BRANDING.md"


@pytest.fixture
def branding_content():
    assert os.path.exists(BRANDING_DOC), f"File {BRANDING_DOC} not found"
    with open(BRANDING_DOC, encoding="utf-8") as f:
        return f.read()


def test_branding_doc_exists():
    assert os.path.exists(BRANDING_DOC)


def test_branding_mentions_local_ai_appliance(branding_content):
    assert "Local AI Appliance" in branding_content


def test_branding_mentions_white_label(branding_content):
    assert "White-Label" in branding_content or "white-label" in branding_content.lower()


def test_branding_mentions_limitations(branding_content):
    content = branding_content.lower()
    assert "psp" in content and "fora do escopo" in content
    assert "pix" in content and "fora do escopo" in content


def test_readme_mentions_local_ai_appliance():
    assert os.path.exists("README.md")
    with open("README.md", encoding="utf-8") as f:
        content = f.read()
    assert "Local AI Appliance" in content
