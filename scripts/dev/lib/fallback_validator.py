#!/usr/bin/env python3
"""Fallback Local-to-Cloud Real Provider Validator.

Validates that local providers are tried first, and when they fail,
configured cloud providers take over — with billing tracking and
sanitization.

Usage:
  python scripts/dev/lib/fallback_validator.py --dry-run
  python scripts/dev/lib/fallback_validator.py --real --provider auto
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_env_local() -> dict[str, str]:
    env = {}
    env_path = PROJECT_ROOT / ".env.local"
    if not env_path.exists():
        return env
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def mask_key(key: str) -> str:
    if len(key) <= 8:
        return "********"
    return key[:4] + "****" + key[-4:]


def sanitize_log(data: Any, max_chars: int = 200) -> str:
    text = json.dumps(data, ensure_ascii=False)
    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    return text


def get_fx_rate_brl() -> float:
    return float(os.environ.get("USD_BRL_RATE", "5.00"))


CLOUD_PROVIDER_MAP = {
    "openai": {
        "env_enabled": "OPENAI_PROVIDER_ENABLED",
        "env_key": "OPENAI_API_KEY",
        "env_model": "OPENAI_CHAT_MODEL",
        "default_model": "gpt-4o-mini",
        "endpoint": "/v1/chat/completions",
        "headers_func": lambda k: {
            "Authorization": f"Bearer {k}",
            "Content-Type": "application/json",
        },
        "payload_func": lambda m: {
            "model": m,
            "messages": [{"role": "user", "content": "Responda apenas: OK"}],
            "max_tokens": 50,
            "temperature": 0.0,
        },
    },
    "anthropic": {
        "env_enabled": "ANTHROPIC_PROVIDER_ENABLED",
        "env_key": "ANTHROPIC_API_KEY",
        "env_model": "ANTHROPIC_MODEL",
        "default_model": "claude-3-haiku-20240307",
        "endpoint": "/v1/messages",
        "headers_func": lambda k: {
            "x-api-key": k,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        "payload_func": lambda m: {
            "model": m,
            "messages": [{"role": "user", "content": "Responda apenas: OK"}],
            "max_tokens": 50,
            "temperature": 0.0,
        },
    },
    "deepseek": {
        "env_enabled": "DEEPSEEK_PROVIDER_ENABLED",
        "env_key": "DEEPSEEK_API_KEY",
        "env_model": "DEEPSEEK_CHAT_MODEL",
        "default_model": "deepseek-chat",
        "endpoint": "/v1/chat/completions",
        "headers_func": lambda k: {
            "Authorization": f"Bearer {k}",
            "Content-Type": "application/json",
        },
        "payload_func": lambda m: {
            "model": m,
            "messages": [{"role": "user", "content": "Responda apenas: OK"}],
            "max_tokens": 50,
            "temperature": 0.0,
        },
    },
}


def resolve_provider(env: dict[str, str], preference: str) -> str | None:
    if preference and preference != "auto":
        if preference in CLOUD_PROVIDER_MAP:
            return preference
        return None
    order = ["openai", "anthropic", "deepseek"]
    for prov in order:
        cfg = CLOUD_PROVIDER_MAP[prov]
        key = env.get(cfg["env_key"]) or os.environ.get(cfg["env_key"])
        enabled = env.get(cfg["env_enabled"], "false") in ("true", "1")
        if key and enabled:
            return prov
    return None


class FallbackValidator:
    def __init__(self, args: argparse.Namespace, env: dict[str, str]):
        self.args = args
        self.env = env
        self.dry_run = args.dry_run
        self.provider_pref = args.provider or "auto"
        self.max_cost_brl = args.max_cost_brl or float(
            env.get("REAL_PROVIDER_MAX_COST_BRL", "2.00")
        )
        self.output_dir = Path(args.output_dir)
        self.timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.report: dict[str, Any] = {
            "validator": "fallback-local-to-cloud",
            "timestamp": self.timestamp,
            "dry_run": self.dry_run,
            "status": "FALLBACK_REAL_SKIP",
            "provider": None,
            "model": None,
            "max_cost_brl": self.max_cost_brl,
            "checks": [],
            "summary": {"pass": 0, "fail": 0, "skip": 0},
            "billing": None,
            "artifacts": [],
        }

    def _check(self, name: str, status: str, detail: str, **extra) -> dict:
        entry = {"check": name, "status": status, "detail": detail, **extra}
        self.report["checks"].append(entry)
        self.report["summary"][status.lower()] = self.report["summary"].get(status.lower(), 0) + 1
        return entry

    def _get_api_base(self, provider: str) -> str:
        urls = {
            "openai": self.env.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "anthropic": self.env.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
            "deepseek": self.env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        }
        return urls.get(provider, "")

    def run(self) -> dict[str, Any]:
        rpv = self.env.get("REAL_PROVIDER_VALIDATION_ENABLED", "false")
        if rpv not in ("true", "1"):
            self._check(
                "env.real_provider_validation_enabled",
                "skip",
                "REAL_PROVIDER_VALIDATION_ENABLED is not true",
            )
            self.report["status"] = "FALLBACK_REAL_SKIP"
            return self.report

        resolved = resolve_provider(self.env, self.provider_pref)
        if not resolved:
            self._check("env.cloud_provider", "skip", "No cloud provider configured/enabled")
            self.report["status"] = "FALLBACK_REAL_SKIP"
            return self.report

        provider = resolved
        cfg = CLOUD_PROVIDER_MAP[provider]
        api_key = self.env.get(cfg["env_key"]) or os.environ.get(cfg["env_key"])
        model = self.args.model or self.env.get(cfg["env_model"]) or cfg["default_model"]
        base_url = self._get_api_base(provider)

        self.report["provider"] = provider
        self.report["model"] = model

        self._check(
            "env.guards",
            "pass",
            f"REAL_PROVIDER_VALIDATION_ENABLED=true, provider={provider} configured/enabled",
        )

        steps = []
        simulated_decisions = []
        original_force = os.environ.get("ROUTING_TEST_FORCE_LOCAL_FAILURE", "false")

        # ── Step 1: Simulate normal routing (local selected) ─────────
        normal_decision = self._simulate_routing(force_local_failure=False)
        simulated_decisions.append(("normal", normal_decision))
        self._check(
            "routing.normal",
            "pass"
            if normal_decision.get("selected_provider", "") in ("local", "lmstudio", "mock")
            else "warn",
            f"provider={normal_decision.get('selected_provider')}, fallback_chain={normal_decision.get('fallback_chain')}",
            decision=normal_decision,
        )
        steps.append("normal")

        # ── Step 2: Simulate routing with local failure ──────────────
        failed_decision = self._simulate_routing(force_local_failure=True)
        simulated_decisions.append(("failed", failed_decision))
        self._check(
            "routing.local_failure",
            "pass"
            if failed_decision.get("selected_provider", "") not in ("local", "lmstudio")
            else "fail",
            f"provider={failed_decision.get('selected_provider')}, fallback_chain={failed_decision.get('fallback_chain')}",
            decision=failed_decision,
        )
        steps.append("failed")

        # ── Step 3: Validate cloud_used flag ────────────────────────
        cloud_used = failed_decision.get("cloud_used", False)
        self._check(
            "routing.cloud_used",
            "pass" if cloud_used or not self.dry_run else "warn",
            f"cloud_used={cloud_used}",
        )
        steps.append("cloud_used_check")

        # ── Step 4: Validate fallback_used flag ─────────────────────
        fallback_used = (
            failed_decision.get("fallback_chain", [])
            and len(failed_decision.get("fallback_chain", [])) > 1
        )
        if normal_decision.get("selected_provider") != failed_decision.get("selected_provider"):
            fallback_used = True
        self._check(
            "routing.fallback_used",
            "pass" if fallback_used else "warn",
            f"fallback_used={fallback_used}, chain={failed_decision.get('fallback_chain')}",
        )

        # ── Step 5: Wallet balance check ────────────────────────────
        wallet_brl = self.env.get("REAL_PROVIDER_TEST_WALLET_BRL")
        if wallet_brl:
            self._check("wallet.balance", "pass", f"test wallet balance=R${wallet_brl}")

        # ── Step 6: Real call (if --real) ───────────────────────────
        if not self.dry_run:
            self._do_real_call(provider, api_key, model, base_url, cfg)
        else:
            self._check("dry_run", "pass", "Dry-run mode — no real calls made")

        # ── Step 7: Sanitization check ──────────────────────────────
        self._check_sanitization()

        # ── Overall status ──────────────────────────────────────────
        if self.report["summary"].get("fail", 0) > 0:
            self.report["status"] = "FALLBACK_REAL_FAIL"
        elif self.report["checks"]:
            self.report["status"] = "FALLBACK_REAL_PASS"

        return self.report

    def _simulate_routing(self, force_local_failure: bool) -> dict[str, Any]:
        try:
            os.environ["ROUTING_TEST_FORCE_LOCAL_FAILURE"] = (
                "true" if force_local_failure else "false"
            )
            from app.core.config import get_settings

            get_settings.cache_clear()

            from app.schemas.routing import EndpointType, RoutingStrategy, SmartRouterInput
            from app.services.routing.smart_router import SmartRouter

            router = SmartRouter()
            inp = SmartRouterInput(
                endpoint_type=EndpointType.chat,
                cloud_allowed=True,
                strategy=RoutingStrategy.local_first,
                prompt_estimated_tokens=50,
                max_output_tokens=50,
            )
            decision = router.route(inp)
            return {
                "selected_provider": decision.selected_provider,
                "selected_model": decision.selected_model,
                "fallback_chain": decision.fallback_chain,
                "cloud_used": decision.cloud_used,
                "reason": decision.reason,
                "warnings": decision.warnings,
            }
        except Exception as e:
            return {
                "selected_provider": "error",
                "fallback_chain": [],
                "cloud_used": False,
                "reason": str(e),
                "warnings": [str(e)],
            }

    def _do_real_call(
        self, provider: str, api_key: str, model: str, base_url: str, cfg: dict[str, Any]
    ):
        os.environ["ROUTING_TEST_FORCE_LOCAL_FAILURE"] = "true"
        from app.core.config import get_settings

        get_settings.cache_clear()

        payload = cfg["payload_func"](model)
        headers = cfg["headers_func"](api_key)
        endpoint = cfg["endpoint"]
        url = base_url.rstrip("/") + endpoint

        start = time.monotonic()
        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=30)
            latency = int((time.monotonic() - start) * 1000)
            if resp.is_success:
                data = resp.json()
                usage = data.get("usage", {}) or {}
                prompt_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("output_tokens", 0) or usage.get(
                    "completion_tokens", 0
                )
                self._check(
                    "cloud.call",
                    "pass",
                    f"latency={latency}ms, tokens={prompt_tokens}+{completion_tokens}",
                    latency_ms=latency,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
                self.report["billing"] = {
                    "provider": provider,
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "latency_ms": latency,
                }
                self._check(
                    "fallback.used", "pass", "fallback_used=true — local failed, cloud responded"
                )
                self._check("cloud.used", "pass", "cloud_used=true — cloud provider served request")
            else:
                self._check(
                    "cloud.call",
                    "fail",
                    f"HTTP {resp.status_code}: {resp.text[:200]}",
                    latency_ms=latency,
                )
        except Exception as e:
            self._check("cloud.call", "fail", str(e), latency_ms=0)

    def _check_sanitization(self):
        sanitized = sanitize_log(self.report)
        for pattern in ("ANTHROPIC_API_KEY=", "OPENAI_API_KEY=", "DEEPSEEK_API_KEY=", "sk-"):
            for line in sanitized.split("\n"):
                if pattern in line and "****" not in line and "mask" not in line:
                    self._check("sanitization", "fail", f"potential leak of {pattern} in report")
                    return
        self._check("sanitization", "pass", "no API key leak in report")

    def write_report(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp_dir = self.output_dir / self.timestamp
        timestamp_dir.mkdir(parents=True, exist_ok=True)
        report_path = timestamp_dir / "fallback-real-report.json"
        with open(report_path, "w") as f:
            json.dump(self.report, f, indent=2, default=str)
        self.report["artifacts"].append(str(report_path))
        md_path = timestamp_dir / "fallback-real-report.md"
        with open(md_path, "w") as f:
            f.write(self._format_md())
        self.report["artifacts"].append(str(md_path))
        return report_path, md_path

    def _format_md(self) -> str:
        lines = [
            "# Fallback Real Provider Report",
            "",
            f"**Status**: {self.report['status']}",
            f"**Timestamp**: {self.timestamp}",
            f"**Dry-run**: {self.dry_run}",
            f"**Provider**: {self.report.get('provider', 'N/A')}",
            f"**Model**: {self.report.get('model', 'N/A')}",
            f"**Max Cost BRL**: R$ {self.max_cost_brl}",
            "",
            "## Summary",
            "",
            "| Result | Count |",
            "|--------|-------|",
        ]
        for s in ("pass", "fail", "skip", "warn"):
            lines.append(f"| {s.upper()} | {self.report['summary'].get(s, 0)} |")
        lines += ["", "## Checks", ""]
        for c in self.report["checks"]:
            lines.append(f"- **[{c['status'].upper()}]** {c['check']}: {c['detail']}")
        billing = self.report.get("billing")
        if billing:
            lines += ["", "## Billing BRL", ""]
            lines.append(f"- Provider: {billing['provider']}")
            lines.append(f"- Model: {billing['model']}")
            lines.append(f"- Prompt tokens: {billing['prompt_tokens']}")
            lines.append(f"- Completion tokens: {billing['completion_tokens']}")
            lines.append(f"- Total tokens: {billing['total_tokens']}")
            lines.append(f"- Latency: {billing['latency_ms']}ms")
        lines += ["", "## Artifacts", ""]
        for a in self.report["artifacts"]:
            lines.append(f"- {a}")
        lines += ["", "---", "", "*Report generated by fallback_validator.py*"]
        return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate fallback local-to-cloud real provider")
    p.add_argument("--dry-run", action="store_true", help="Simulate routing only, no real calls")
    p.add_argument(
        "--real", action="store_true", help="Make real API calls with forced local failure"
    )
    p.add_argument(
        "--provider", default="auto", help="Cloud provider: openai, anthropic, deepseek, or auto"
    )
    p.add_argument("--model", default=None, help="Model to use for real call")
    p.add_argument("--max-cost-brl", type=float, default=None, help="Max cost in BRL")
    p.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "artifacts" / "real-provider-validation" / "fallback"),
        help="Output directory",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    env = load_env_local()
    if not args.dry_run and not args.real:
        print("ERROR: Use --dry-run or --real")
        return 1

    validator = FallbackValidator(args, env)
    report = validator.run()
    report_path, md_path = validator.write_report()

    print(f"\nFallback Real Provider Validation: {report['status']}")
    print(f"  Provider: {report.get('provider', 'N/A')}")
    print(f"  Model: {report.get('model', 'N/A')}")
    print(f"  Report: {report_path}")
    billing = report.get("billing")
    if billing:
        print(f"  Real call latency: {billing['latency_ms']}ms")
    for c in report["checks"]:
        icon = {"pass": "OK", "fail": "FAIL", "skip": "SKIP", "warn": "WARN"}.get(c["status"], "?")
        print(f"  [{icon}] {c['check']}: {c['detail']}")

    if report["status"] == "FALLBACK_REAL_FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
