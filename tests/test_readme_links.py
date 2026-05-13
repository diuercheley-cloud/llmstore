import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"

REQUIRED_DOC_LINKS = [
    "docs/V1_7_RELEASE_NOTES.md",
    "docs/CLIENT_READY_FINAL_REPORT.md",
    "docs/V1_7_GO_NO_GO_SUMMARY.md",
    "docs/FRESH_MACHINE_VALIDATION.md",
    "docs/demo-visual-guide/README.md",
    "docs/LOCAL_DEMO_GUIDE.md",
    "docs/CUSTOMER_INSTALL_GUIDE.md",
    "docs/RELEASE_HISTORY.md",
]


def test_required_doc_links():
    content = README.read_text(encoding="utf-8")
    for doc_link in REQUIRED_DOC_LINKS:
        assert doc_link in content, f"Missing link to {doc_link} in README"


def test_doc_links_resolve():
    """All docs/ links in README must resolve to existing files."""
    content = README.read_text(encoding="utf-8")
    links = re.findall(r'docs/[a-zA-Z0-9_/.-]+\.md', content)
    missing = []
    for link in links:
        target = ROOT / link
        if not target.exists():
            missing.append(link)
    assert not missing, f"Broken doc links:\n" + "\n".join(missing)


def test_no_broken_script_links():
    """All ./scripts/ references in README must resolve."""
    content = README.read_text(encoding="utf-8")
    refs = re.findall(r'\./scripts/[a-zA-Z0-9_.-]+\.sh', content)
    missing = []
    for ref in refs:
        target = ROOT / ref
        if not target.exists():
            missing.append(ref)
    assert not missing, f"Broken script refs:\n" + "\n".join(missing)


def test_release_notes_link():
    content = README.read_text(encoding="utf-8")
    assert "V1_7_RELEASE_NOTES.md" in content


def test_client_ready_report_link():
    content = README.read_text(encoding="utf-8")
    assert "CLIENT_READY_FINAL_REPORT.md" in content


def test_fresh_machine_validation_link():
    content = README.read_text(encoding="utf-8")
    assert "FRESH_MACHINE_VALIDATION.md" in content


def test_demo_visual_guide_link():
    content = README.read_text(encoding="utf-8")
    assert "demo-visual-guide/README.md" in content


def test_local_demo_guide_link():
    content = README.read_text(encoding="utf-8")
    assert "LOCAL_DEMO_GUIDE.md" in content


def test_customer_install_guide_link():
    content = README.read_text(encoding="utf-8")
    assert "CUSTOMER_INSTALL_GUIDE.md" in content


def test_release_history_link():
    content = README.read_text(encoding="utf-8")
    assert "RELEASE_HISTORY.md" in content


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
    has_runbook = "docs/LOCAL_PRODUCTION_RUNBOOK.md" in content
    assert has_diagram or has_runbook, (
        "README should have either architecture diagram or link to runbook"
    )
