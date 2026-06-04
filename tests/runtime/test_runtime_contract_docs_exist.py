from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_runtime_contract_docs_exist():
    required = [
        ROOT_DIR / "docs" / "runtime" / "core_runtime_spec.md",
        ROOT_DIR / "docs" / "runtime" / "runtime_invariants.md",
        ROOT_DIR / "docs" / "runtime" / "state_machine_contracts.md",
        ROOT_DIR / "scripts" / "validate_runtime_contracts.py",
    ]
    missing = [str(path.relative_to(ROOT_DIR)) for path in required if not path.exists()]
    assert not missing, "Missing runtime contract artifacts:\n" + "\n".join(missing)
