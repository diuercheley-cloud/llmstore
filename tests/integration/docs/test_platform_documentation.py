"""Tests for platform documentation completeness and consistency."""

import os
import re

import pytest

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


def path(relative_path):
    return os.path.join(REPO_ROOT, relative_path)


def read(relative_path):
    with open(path(relative_path)) as f:
        return f.read()


REQUIRED_ARCHITECTURE_DOCS = [
    "docs/architecture/platform_overview.md",
    "docs/architecture/platform_domain_map.md",
    "docs/architecture/platform_guarantees_and_limitations.md",
    "docs/architecture/platform_operational_model.md",
    "docs/architecture/platform_validation_workflows.md",
    "docs/architecture/platform_module_relationships.md",
    "docs/architecture/platform_glossary.md",
    "docs/architecture/platform_phase_timeline.md",
]

REQUIRED_OPERATIONS_DOCS = [
    "docs/operations/platform_runbook.md",
]


class TestRequiredFiles:
    def test_readme_exists(self):
        assert os.path.isfile(path("README.md")), "README.md must exist"

    def test_docs_index_exists(self):
        assert os.path.isfile(path("docs/index.md")), "docs/index.md must exist"

    @pytest.mark.parametrize("doc", REQUIRED_ARCHITECTURE_DOCS)
    def test_architecture_docs_exist(self, doc):
        assert os.path.isfile(path(doc)), f"{doc} must exist"

    @pytest.mark.parametrize("doc", REQUIRED_OPERATIONS_DOCS)
    def test_operations_docs_exist(self, doc):
        assert os.path.isfile(path(doc)), f"{doc} must exist"


class TestReadmeSections:
    def test_has_platform_architecture_section(self):
        content = read("README.md")
        assert "## Platform Architecture" in content

    def test_has_principles(self):
        content = read("README.md")
        assert "Deterministic" in content
        assert "Replay-Safe" in content
        assert "Offline-First" in content
        assert "Sovereign" in content
        assert "Advisory-First" in content

    def test_has_bounded_contexts(self):
        content = read("README.md")
        assert "Bounded Contexts" in content

    def test_has_phases_69_82_flow(self):
        content = read("README.md")
        assert "Phases 69" in content

    def test_has_explicit_limitations(self):
        content = read("README.md").lower()
        assert "plugin abi sandbox" in content
        assert "local pki" in content
        assert "policy-based attestation" in content
        assert "offline-first" in content
        assert "evidence-driven compliance" in content

    def test_has_validation_commands(self):
        content = read("README.md")
        assert "validate-architecture-smoke" in content
        assert "validate-architecture-full" in content
        assert "validate-platform-documentation" in content

    def test_has_documentation_navigation(self):
        content = read("README.md")
        assert "Navigating the Documentation" in content


class TestGlossary:
    REQUIRED_TERMS = [
        "advisory-only",
        "bounded context",
        "compatibility contract",
        "deterministic",
        "dry-run",
        "federation",
        "governance workflow",
        "lineage",
        "offline-first",
        "placeholder trust",
        "plugin ABI",
        "policy bundle",
        "provenance",
        "replay-safe",
        "reproducible build",
        "sovereign",
    ]

    def test_glossary_exists(self):
        assert os.path.isfile(path("docs/architecture/platform_glossary.md"))

    @pytest.mark.parametrize("term", REQUIRED_TERMS)
    def test_glossary_contains_term(self, term):
        content = read("docs/architecture/platform_glossary.md").lower()
        assert term.lower() in content, f"Glossary must contain term: {term}"


class TestDocsIndex:
    def test_index_exists(self):
        assert os.path.isfile(path("docs/index.md"))

    def test_canonical_index_exists(self):
        assert os.path.isfile(path("docs/CANONICAL_INDEX.md"))

    def test_index_has_start_here(self):
        content = read("docs/index.md")
        assert "## Start Here" in content

    def test_index_has_supported_surfaces(self):
        content = read("docs/index.md")
        assert "## Supported Surfaces" in content

    def test_index_has_reference(self):
        content = read("docs/index.md")
        assert "## Reference" in content

    def test_canonical_index_classifies_docs(self):
        content = read("docs/CANONICAL_INDEX.md")
        assert "## Canonical" in content
        assert "## Reference" in content
        assert "## Release Historical" in content
        assert "## Deprecated" in content
        assert "## Duplicate" in content


class TestPhaseTimeline:
    def test_timeline_exists(self):
        assert os.path.isfile(path("docs/architecture/platform_phase_timeline.md"))

    @pytest.mark.parametrize("phase_num", range(69, 83))
    def test_phase_in_timeline(self, phase_num):
        content = read("docs/architecture/platform_phase_timeline.md")
        assert f"Phase {phase_num}" in content, f"Timeline must contain Phase {phase_num}"


class TestMermaidDiagrams:
    def _count_mermaid(self, filepath):
        content = read(filepath)
        return len(re.findall(r"```mermaid", content))

    def test_domain_map_has_diagram(self):
        assert self._count_mermaid("docs/architecture/platform_domain_map.md") >= 1

    def test_module_relationships_has_diagram(self):
        assert self._count_mermaid("docs/architecture/platform_module_relationships.md") >= 1

    def test_validation_workflows_has_diagram(self):
        assert self._count_mermaid("docs/architecture/platform_validation_workflows.md") >= 1

    def test_phase_timeline_has_diagram(self):
        assert self._count_mermaid("docs/architecture/platform_phase_timeline.md") >= 1


class TestLimitations:
    LIMITATIONS_DOC = "docs/architecture/platform_guarantees_and_limitations.md"

    def test_limitations_doc_exists(self):
        assert os.path.isfile(path(self.LIMITATIONS_DOC))

    def test_has_prohibited_claims_section(self):
        content = read(self.LIMITATIONS_DOC)
        assert "Prohibited Claims" in content

    def test_has_advisory_nature_section(self):
        content = read(self.LIMITATIONS_DOC)
        assert "Advisory Nature" in content

    def test_no_military_grade(self):
        content = read("README.md").lower()
        assert "military-grade" not in content

    def test_no_guaranteed_secure(self):
        content = read("README.md").lower()
        assert "guaranteed secure" not in content


class TestOperationalDocs:
    def test_runbook_exists(self):
        assert os.path.isfile(path("docs/operations/platform_runbook.md"))

    def test_runbook_has_smoke_workflow(self):
        content = read("docs/operations/platform_runbook.md")
        assert "Smoke Validation" in content

    def test_runbook_has_full_workflow(self):
        content = read("docs/operations/platform_runbook.md")
        assert "Full Validation" in content

    def test_runbook_has_troubleshooting(self):
        content = read("docs/operations/platform_runbook.md")
        assert "Troubleshooting" in content

    def test_runbook_has_report_reading(self):
        content = read("docs/operations/platform_runbook.md")
        assert "Reading Reports" in content
