from pathlib import Path

from scripts.validators.validate_governance_documentation_foundation import validate

ROOT = Path(__file__).resolve().parents[3]


def test_governance_documentation_foundation_validation_script():
    failures = validate()
    assert failures == []


def test_governance_summary_mentions_placeholder_and_offline_first():
    summary = (ROOT / "docs/governance/governance_documentation_foundation_summary.md").read_text(
        encoding="utf-8"
    ).lower()
    assert "placeholder-only" in summary
    assert "offline-first" in summary
    assert "does not provide real certification" in summary
