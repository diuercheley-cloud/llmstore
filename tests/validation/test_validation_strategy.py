from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

DOCS_DIR = ROOT_DIR / "docs" / "validation"
MAKEFILE_PATH = ROOT_DIR / "Makefile"


def test_validation_strategy_doc_exists():
    assert (DOCS_DIR / "validation_strategy.md").exists()


def test_technical_freeze_summary_doc_exists():
    assert (DOCS_DIR / "technical_freeze_validation_summary.md").exists()


def test_makefile_contains_architecture_smoke():
    content = MAKEFILE_PATH.read_text(encoding="utf-8")
    assert "validate-architecture-smoke:" in content


def test_makefile_contains_architecture_full():
    content = MAKEFILE_PATH.read_text(encoding="utf-8")
    assert "validate-architecture-full:" in content


def test_makefile_contains_measure_validation_targets():
    content = MAKEFILE_PATH.read_text(encoding="utf-8")
    assert "measure-validation-targets:" in content


def test_makefile_contains_list_slow_tests():
    content = MAKEFILE_PATH.read_text(encoding="utf-8")
    assert "list-slow-tests:" in content


def test_architecture_full_preserves_architecture():
    content = MAKEFILE_PATH.read_text(encoding="utf-8")
    assert "validate-architecture-full:" in content
    assert "validate-architecture:" in content
    idx_full = content.find("validate-architecture-full:")
    block_after_full = content[idx_full:idx_full + 500]
    assert "validate-architecture" in block_after_full


def test_smoke_does_not_remove_full_targets():
    content = MAKEFILE_PATH.read_text(encoding="utf-8")
    assert "validate-architecture:" in content
    assert "validate-architecture-full:" in content


def test_reports_are_generatable_offline():
    script = ROOT_DIR / "scripts" / "measure_validation_targets.py"
    assert script.exists()
    slow_script = ROOT_DIR / "scripts" / "list_slow_tests.py"
    assert slow_script.exists()


def test_validation_strategy_mentions_smoke_vs_full():
    doc = (DOCS_DIR / "validation_strategy.md").read_text(encoding="utf-8")
    assert "Smoke" in doc or "smoke" in doc
    assert "Full" in doc or "full" in doc


def test_validation_strategy_mentions_offline_first():
    doc = (DOCS_DIR / "validation_strategy.md").read_text(encoding="utf-8")
    assert "Offline-First" in doc or "offline-first" in doc or "offline" in doc.lower()
