"""Agent scaffolding from templates."""

import json
import os
import shutil
import re
from pathlib import Path
from typing import Optional

TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "examples" / "agents"

TEMPLATE_METADATA = {
    "hello-world": {
        "description": "Minimal agent with a single system prompt",
        "prompts": {"name": {"prompt": "Agent name", "default": "my-agent"}},
    },
    "support-triage-agent": {
        "description": "Customer support ticket triage agent",
        "prompts": {"name": {"prompt": "Agent name", "default": "support-triage"}},
    },
    "rag-research": {
        "description": "Research agent with RAG document retrieval",
        "prompts": {"name": {"prompt": "Agent name", "default": "research-agent"}},
    },
    "incident-response": {
        "description": "Incident response and remediation agent",
        "prompts": {"name": {"prompt": "Agent name", "default": "incident-responder"}},
    },
    "billing-review": {
        "description": "Billing review and invoice analysis agent",
        "prompts": {"name": {"prompt": "Agent name", "default": "billing-review"}},
    },
    "devops-runbook": {
        "description": "DevOps runbook execution agent",
        "prompts": {"name": {"prompt": "Agent name", "default": "devops-agent"}},
    },
    "salesforce-account-summary": {
        "description": "Salesforce account summary generator",
        "prompts": {"name": {"prompt": "Agent name", "default": "salesforce-agent"}},
    },
    "ops-readiness-agent": {
        "description": "Operations readiness checker agent",
        "prompts": {"name": {"prompt": "Agent name", "default": "ops-readiness"}},
    },
    "compliance-evidence": {
        "description": "Compliance evidence collection agent",
        "prompts": {"name": {"prompt": "Agent name", "default": "compliance-agent"}},
    },
}


def list_templates() -> list[dict]:
    results = []
    for tid, meta in TEMPLATE_METADATA.items():
        template_dir = TEMPLATES_DIR / tid
        exists = template_dir.exists()
        results.append({
            "id": tid,
            "description": meta["description"],
            "exists": exists,
        })
    return results


def scaffold(
    template_id: str,
    output_dir: str,
    values: Optional[dict] = None,
    force: bool = False,
) -> str:
    if template_id not in TEMPLATE_METADATA:
        available = list(TEMPLATE_METADATA.keys())
        raise ValueError(f"Unknown template '{template_id}'. Available: {', '.join(available)}")

    template_path = TEMPLATES_DIR / template_id
    if not template_path.exists():
        raise ValueError(f"Template directory not found: {template_path}")

    out = Path(output_dir)
    if out.exists() and not force:
        raise FileExistsError(f"Output directory exists: {out}. Use --force to overwrite.")

    out.mkdir(parents=True, exist_ok=True)
    values = values or {}

    for item in template_path.rglob("*"):
        if item.is_file():
            rel = item.relative_to(template_path)
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)

            content = item.read_text(encoding="utf-8")
            for key, val in values.items():
                content = content.replace(f"{{{{ {key} }}}}", val)
                content = content.replace(f"{{{{ {key} }}}}", val)

            if content != item.read_text(encoding="utf-8"):
                content = _apply_template_vars(content, values)

            dest.write_text(content, encoding="utf-8")

    readme = out / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {values.get('name', template_id)}\n\n"
            f"Scaffolded from `{template_id}` template.\n"
            f"See [agent.yaml](agent.yaml) for configuration.\n"
        )

    return str(out)


def _apply_template_vars(text: str, values: dict) -> str:
    def _replacer(m):
        key = m.group(1).strip()
        return str(values.get(key, m.group(0)))
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", _replacer, text)
