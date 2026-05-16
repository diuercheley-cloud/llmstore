#!/usr/bin/env python3
"""Validate core runtime contract documentation structure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = {
    "docs/runtime/core_runtime_spec.md": [
        "# Core Runtime Spec",
        "## Execution Lifecycle",
        "- `submitted`",
        "- `validated`",
        "- `policy_checked`",
        "- `scheduled`",
        "- `executing`",
        "- `checkpointed`",
        "- `completed`",
        "- `failed`",
        "- `repaired`",
        "- `replayed`",
        "## Workflow Lifecycle",
        "### DAG creation",
        "### DAG hashing",
        "### Policy gates",
        "### Checkpoint creation",
        "### Pause/resume",
        "### Rollback",
        "### Replay validation",
        "## Receipt Lifecycle",
        "### Receipt creation",
        "### immutable_hash",
        "### SHA-256 chaining",
        "### Signature placeholder",
        "### Verification",
        "### Export restrictions",
        "## Governance Lifecycle",
        "### policy match",
        "### advisory mode",
        "### dry_run mode",
        "### approval required",
        "### enforcement",
        "### incident creation",
        "## Repair Lifecycle",
        "### failure detection",
        "### recovery plan",
        "### deterministic repair",
        "### signed healing receipt",
        "### replay verification",
        "nao implementa hardware attestation real",
        "nao faz claim de certificacao formal",
    ],
    "docs/runtime/runtime_invariants.md": [
        "# Runtime Invariants",
        "## Invariants Globais",
        "## Invariants de Execucao",
        "## Invariants de Workflow",
        "## Invariants de Receipts",
        "## Invariants de Governanca",
        "## Invariants de Repair",
    ],
    "docs/runtime/state_machine_contracts.md": [
        "# State Machine Contracts",
        "## Execution State Machine",
        "## Workflow State Machine",
        "## Receipt State Machine",
        "## Governance State Machine",
        "## Repair State Machine",
        "nenhuma secao deve ser interpretada como claim de certificacao formal ou hardware attestation real",
    ],
}


def validate_documents() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for relative_path, required_fragments in REQUIRED_FILES.items():
        path = REPO_ROOT / relative_path
        if not path.exists():
            failures.append({"path": relative_path, "issue": "missing file"})
            continue
        content = path.read_text(encoding="utf-8")
        for fragment in required_fragments:
            if fragment not in content:
                failures.append({"path": relative_path, "issue": f"missing fragment: {fragment}"})
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON.")
    args = parser.parse_args()

    failures = validate_documents()
    if args.json:
        print(json.dumps(failures, indent=2, sort_keys=True))
    elif failures:
        print("Runtime contract validation failed:")
        for failure in failures:
            print(f"- {failure['path']}: {failure['issue']}")
    else:
        print("Runtime contract validation passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
