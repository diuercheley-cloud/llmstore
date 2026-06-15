import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"

REQUIRED_DOC_LINKS = [
    "docs/CANONICAL_INDEX.md",
    "docs/index.md",
    "docs/PRODUCT_SURFACE.md",
    "docs/API_REFERENCE.md",
    "docs/CONFIGURATION_REFERENCE.md",
    "docs/FLAGS_INVENTORY.md",
    "docs/support/supported-surface-area.md",
    "docs/api/supported-api-surface.md",
]


def test_required_doc_links():
    content = README.read_text(encoding="utf-8")
    for doc_link in REQUIRED_DOC_LINKS:
        assert doc_link in content, f"Missing link to {doc_link} in README"


def test_doc_links_resolve():
    """All docs/ links in README must resolve to existing files."""
    content = README.read_text(encoding="utf-8")
    links = re.findall(r"docs/[a-zA-Z0-9_/.-]+\.md", content)
    missing = []
    for link in links:
        target = ROOT / link
        if not target.exists():
            missing.append(link)
    assert not missing, "Broken doc links:\n" + "\n".join(missing)


def test_no_broken_script_links():
    """All ./scripts/ references in README must resolve."""
    content = README.read_text(encoding="utf-8")
    refs = re.findall(r"\./scripts/[a-zA-Z0-9_.-]+\.sh", content)
    missing = []
    for ref in refs:
        target = ROOT / ref
        if not target.exists():
            missing.append(ref)
    assert not missing, "Broken script refs:\n" + "\n".join(missing)


def test_product_surface_link():
    content = README.read_text(encoding="utf-8")
    assert "PRODUCT_SURFACE.md" in content


def test_api_reference_link():
    content = README.read_text(encoding="utf-8")
    assert "API_REFERENCE.md" in content


def test_configuration_reference_link():
    content = README.read_text(encoding="utf-8")
    assert "CONFIGURATION_REFERENCE.md" in content


def test_flags_inventory_link():
    content = README.read_text(encoding="utf-8")
    assert "FLAGS_INVENTORY.md" in content


def test_index_link():
    content = README.read_text(encoding="utf-8")
    assert "docs/index.md" in content


def test_canonical_index_link():
    content = README.read_text(encoding="utf-8")
    assert "CANONICAL_INDEX.md" in content


def test_readme_client_link():
    content = README.read_text(encoding="utf-8")
    assert "README_CLIENT.md" in content


def test_examples_link():
    content = README.read_text(encoding="utf-8")
    assert "examples/" in content


def test_integrations_link():
    content = README.read_text(encoding="utf-8")
    assert "docs/integrations/" in content


def test_documentation_table():
    content = README.read_text(encoding="utf-8")
    assert "| Documento | Conteúdo |" in content


def test_architecture_diagram_not_required():
    """Architecture diagram was moved to technical docs; README may or may not have it."""
    content = README.read_text(encoding="utf-8")
    has_diagram = "```text" in content and "Control Plane" in content
    has_runbook = "docs/operations/platform_runbook.md" in content
    assert has_diagram or has_runbook, (
        "README should have either architecture diagram or link to runbook"
    )
