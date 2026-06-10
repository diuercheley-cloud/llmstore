from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
RELEASE_HISTORY = ROOT_DIR / "docs" / "RELEASE_HISTORY.md"

REQUIRED_TAGS = [
    "v1.5.3-local-ops",
    "v1.5.4-security-cleanup",
    "v1.5.5-security-artifacts-clean",
    "v1.5.6-runtime-hardening",
    "v1.6.0-openai-compat",
    "v1.6.1-product-hardening",
    "v1.6.2-installer-polish",
    "v1.6.3-readiness-cleanup",
    "v1.6.4-customer-demo-pack",
    "v1.6.5-sales-ops",
]

REQUIRED_SECTIONS = [
    "Visao Geral",
    "Linha do Tempo",
    "Releases",
    "Releases Recomendadas",
    "Releases Antigas",
    "Como Restaurar",
    "Como Criar uma Nova Release",
    "Politica de Branches",
]


def test_release_history_exists():
    assert RELEASE_HISTORY.exists(), "docs/RELEASE_HISTORY.md missing"


def test_required_tags_present():
    content = RELEASE_HISTORY.read_text()
    missing = [t for t in REQUIRED_TAGS if t not in content]
    assert not missing, f"Tags missing: {missing}"


def test_required_sections_present():
    content = RELEASE_HISTORY.read_text()
    missing = [s for s in REQUIRED_SECTIONS if s.lower() not in content.lower()]
    assert not missing, f"Sections missing: {missing}"


def test_no_secrets():
    content = RELEASE_HISTORY.read_text()
    secrets = ["sk-", "ghp_", "-----BEGIN", "ADMIN_TOKEN=", "JWT_SECRET="]
    for s in secrets:
        assert s not in content, f"Secret pattern '{s}' found in RELEASE_HISTORY"


def test_uses_relative_paths():
    content = RELEASE_HISTORY.read_text()
    has_rel = any(p in content for p in ["releases/", "docs/", "scripts/"])
    assert has_rel, "No relative paths found"
