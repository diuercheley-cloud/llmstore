from pathlib import Path

from app.services.platform.current_release_context import get_current_tag


class ReleaseArtifactResolver:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def get_summary_path(self, tag: str = None) -> Path:
        if not tag:
            tag = get_current_tag()
        return self.base_dir / "artifacts" / "releases" / tag / "summary.md"

    def get_validation_path(self, tag: str = None) -> Path:
        if not tag:
            tag = get_current_tag()
        return self.base_dir / "artifacts" / "releases" / tag / "validation.md"

    def get_production_gate_path(self, tag: str = None) -> Path:
        if not tag:
            tag = get_current_tag()
        return self.base_dir / "artifacts" / "releases" / tag / "production-gate.md"
