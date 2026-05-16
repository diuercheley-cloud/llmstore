from pathlib import Path

from app.domains import OFFICIAL_PLATFORM_DOMAINS


def test_official_domain_dependency_graph_files_exist():
    base = Path(__file__).resolve().parents[2] / "control_plane" / "app" / "domains"
    for domain in OFFICIAL_PLATFORM_DOMAINS:
        assert (base / domain / "contracts.py").exists()
        assert (base / domain / "events.py").exists()
        assert (base / domain / "schemas.py").exists()
