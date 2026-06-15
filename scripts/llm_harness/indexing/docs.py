import json
import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

from ..policy import PolicyEngine
from ..sanitizer import Sanitizer


class DocsManager:
    def __init__(self, workspace_root: str = ".", policy_engine: PolicyEngine | None = None):
        self.workspace_root = workspace_root
        self.policy_engine = policy_engine or PolicyEngine()
        self.docs_dir = os.path.join(workspace_root, ".llm_harness_index", "docs")
        os.makedirs(self.docs_dir, exist_ok=True)

    def load_config(self) -> list[dict[str, str]]:
        config_path = os.path.join(self.workspace_root, ".harness.yaml")
        if not os.path.exists(config_path):
            config_path = os.path.join(self.workspace_root, ".harness.yml")
        if not os.path.exists(config_path):
            return []
        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return data.get("external_docs", [])
        except Exception:
            return []

    def save_config(self, external_docs: list[dict[str, str]]) -> None:
        config_path = os.path.join(self.workspace_root, ".harness.yaml")
        try:
            data: dict[str, Any] = {}
            if os.path.exists(config_path):
                with open(config_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            data["external_docs"] = external_docs
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)
        except Exception:
            pass

    def add_doc(self, name: str, url: str, allowlist_domain: str | None = None) -> None:
        configs = self.load_config()
        found = False
        for doc in configs:
            if doc.get("name") == name:
                doc["url"] = url
                if allowlist_domain:
                    doc["allowlist_domain"] = allowlist_domain
                else:
                    doc.pop("allowlist_domain", None)
                found = True
                break
        if not found:
            new_doc = {"name": name, "url": url}
            if allowlist_domain:
                new_doc["allowlist_domain"] = allowlist_domain
            configs.append(new_doc)
        self.save_config(configs)

    def fetch_doc(self, name: str) -> str:
        configs = self.load_config()
        doc_config = None
        for doc in configs:
            if doc.get("name") == name:
                doc_config = doc
                break
        if not doc_config:
            raise ValueError(f"No external doc configuration found for '{name}'")

        url = doc_config["url"]
        allowlist_domain = doc_config.get("allowlist_domain")

        # Check network access policy
        allow_network = self.policy_engine.config.get("allow_network", False)
        if not allow_network:
            raise PermissionError(
                "Network fetch is disabled. Enable it by setting "
                "'allow_network': true in policy config."
            )

        # Validate domain match
        if allowlist_domain:
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname or ""
            if not (hostname == allowlist_domain or hostname.endswith("." + allowlist_domain)):
                raise PermissionError(
                    f"URL '{url}' does not match allowed domain '{allowlist_domain}'"
                )

        response = httpx.get(url, follow_redirects=True, timeout=10.0)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch doc from {url}: status {response.status_code}")

        raw_html = response.text

        # Simple HTML stripping
        cleaned_text = re.sub(r"<(script|style)\b[^>]*>([\s\S]*?)<\/\1>", "", raw_html, flags=re.I)
        cleaned_text = re.sub(r"<[^>]+>", " ", cleaned_text)
        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

        sanitized_text = Sanitizer.sanitize_text(cleaned_text)

        # Save to cache
        cache_file = os.path.join(self.docs_dir, f"{name}.json")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"name": name, "url": url, "content": sanitized_text}, f, indent=2)

        return sanitized_text

    def get_cached_doc(self, name: str) -> str | None:
        cache_file = os.path.join(self.docs_dir, f"{name}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("content")
            except Exception:
                pass
        return None

    def build_prompt_context(
        self,
        names: list[str] | None = None,
        max_chars: int = 8000,
    ) -> str:
        configs = self.load_config()
        selected_names = names or [doc.get("name", "") for doc in configs if doc.get("name")]
        if not selected_names:
            return ""

        parts = ["=== External Documentation Context ==="]
        remaining = max_chars
        for name in selected_names:
            if remaining <= 0:
                break
            content = self.get_cached_doc(name)
            if not content:
                continue
            section = f"\n-- Doc: {name} --\n{content[:remaining]}\n"
            parts.append(section)
            remaining -= len(section)

        return "\n".join(parts) if len(parts) > 1 else ""

    def refresh_docs(self) -> None:
        configs = self.load_config()
        for doc in configs:
            name = doc.get("name")
            if name:
                try:
                    self.fetch_doc(name)
                except Exception as e:
                    print(f"Failed to refresh doc '{name}': {e}")
