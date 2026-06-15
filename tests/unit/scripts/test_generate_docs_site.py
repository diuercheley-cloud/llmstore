from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_docs_site_generator_check_passes() -> None:
    subprocess.run(
        [".venv/bin/python", "scripts/docs/generate_docs_site.py", "--check"],
        cwd=ROOT,
        check=True,
    )


def test_mkdocs_config_uses_portal_and_mike_versioning() -> None:
    content = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "docs_dir: docs-site/docs" in content
    assert "name: material" in content
    assert "provider: mike" in content
    assert "Docs Migration Plan: migration-plan.md" in content


def test_profiles_reference_is_generated_into_portal() -> None:
    content = (ROOT / "docs-site" / "docs" / "reference" / "profiles.md").read_text(
        encoding="utf-8"
    )

    assert "generated_by: scripts/docs/generate_docs_site.py" in content
    assert "# Profiles Reference" in content
    assert "`lite`" in content
    assert "`enterprise`" in content


def test_portal_docs_rewrite_legacy_links() -> None:
    quickstart = (ROOT / "docs-site" / "docs" / "getting-started" / "quickstart.md").read_text(
        encoding="utf-8"
    )
    api_reference = (ROOT / "docs-site" / "docs" / "reference" / "api-reference.md").read_text(
        encoding="utf-8"
    )
    product_surface = (ROOT / "docs-site" / "docs" / "reference" / "product-surface.md").read_text(
        encoding="utf-8"
    )

    assert "(../reference/api-reference.md)" in quickstart
    assert "(../api/supported-surface.md)" in api_reference
    assert "[admin-tests.md](" not in product_surface
