from __future__ import annotations

from typing import Any


class ReleaseNotesGenerator:
    def generate_deterministic_notes(
        self, manifest: dict[str, Any], changelog: list[dict[str, Any]]
    ) -> str:
        lines = [
            f"# Release Notes - {manifest['version']}",
            "",
            f"**Baseline Hash**: `{manifest['manifest_hash']}`",
            f"**Validation Snapshot**: `{manifest['snapshot_hash']}`",
            f"**Replay Safe**: `{manifest['replay_safe']}`",
            "",
            "## Scope",
        ]
        for item in manifest.get("scope", []):
            lines.append(f"- {item}")

        lines.extend(["", "## Changelog"])
        for section in changelog:
            lines.append(f"### {section['type']}")
            for change in section.get("changes", []):
                lines.append(f"- {change}")
        lines.append("")
        return "\n".join(lines)
