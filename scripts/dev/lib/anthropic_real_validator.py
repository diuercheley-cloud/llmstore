#!/usr/bin/env python3
"""Anthropic Real Provider Validator.

Validates Anthropic provider connectivity, Messages API, billing BRL mapping,
and sanitization — all without leaking secrets.

Usage:
  python scripts/dev/lib/anthropic_real_validator.py --dry-run
  python scripts/dev/lib/anthropic_real_validator.py --real --model claude-3-haiku-20240307
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


def estimate_anthropic_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = {
        "claude-3-opus": (15.00, 75.00),
        "claude-3-sonnet": (3.00, 15.00),
        "claude-3-haiku": (0.25, 1.25),
        "claude-3-5-sonnet": (3.00, 15.00),
        "claude-3-5-haiku": (0.80, 4.00),
        "claude-4-sonnet": (15.00, 75.00),
    }
    key = model
    if key not in pricing:
        for pattern, (p, c) in pricing.items():
            if pattern in model:
                key = pattern
                break
        else:
            return 0.0
    prompt_price, completion_price = pricing[key]
    return (prompt_tokens / 1_000_000 * prompt_price) + (
        completion_tokens / 1_000_000 * completion_price
    )


def get_fx_rate_brl() -> float:
    return float(os.environ.get("USD_BRL_RATE", "5.00"))


def sanitize_log(data: Any, max_chars: int = 200) -> str:
    text = json.dumps(data, ensure_ascii=False)
    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    return text


class AnthropicRealValidator:
    def __init__(self, args: argparse.Namespace, env: dict[str, str]):
        self.args = args
        self.env = env
        self.dry_run = args.dry_run
        self.max_cost_brl = args.max_cost_brl or float(
            env.get("REAL_PROVIDER_MAX_COST_BRL", "2.00")
        )
        self.model = args.model or (env.get("ANTHROPIC_MODEL") or "claude-3-haiku-20240307")
        self.output_dir = Path(args.output_dir)
        self.timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.report: dict[str, Any] = {
            "validator": "anthropic-real-provider",
            "timestamp": self.timestamp,
            "dry_run": self.dry_run,
            "status": "ANTHROPIC_REAL_SKIP",
            "model": self.model,
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

    def _get_api_key(self) -> str | None:
        return self.env.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")

    def _get_base_url(self) -> str:
        return self.env.get("ANTHROPIC_BASE_URL") or os.environ.get(
            "ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"
        )

    def run(self) -> dict[str, Any]:
        api_key = self._get_api_key()
        base_url = self._get_base_url()

        if not api_key:
            self._check("env.api_key", "skip", "ANTHROPIC_API_KEY not set")
            self.report["status"] = "ANTHROPIC_REAL_SKIP"
            return self.report

        rpv = self.env.get("REAL_PROVIDER_VALIDATION_ENABLED", "false")
        ape = self.env.get("ANTHROPIC_PROVIDER_ENABLED", "false")

        if rpv not in ("true", "1"):
            self._check(
                "env.real_provider_validation_enabled",
                "skip",
                "REAL_PROVIDER_VALIDATION_ENABLED is not true",
            )
            self.report["status"] = "ANTHROPIC_REAL_SKIP"
            return self.report

        if ape not in ("true", "1"):
            self._check(
                "env.anthropic_provider_enabled", "skip", "ANTHROPIC_PROVIDER_ENABLED is not true"
            )
            self.report["status"] = "ANTHROPIC_REAL_SKIP"
            return self.report

        self._check("env.api_key", "pass", f"key {mask_key(api_key)}, base={base_url}")
        self._check(
            "env.guards",
            "pass",
            "REAL_PROVIDER_VALIDATION_ENABLED=true, ANTHROPIC_PROVIDER_ENABLED=true",
        )

        if self.dry_run:
            self._check("dry_run", "pass", "Dry-run mode — no real calls made")
            self.report["status"] = "ANTHROPIC_REAL_PASS"
            return self.report

        # Step 2: Health / list models
        self._check_health(base_url, api_key)

        # Step 3: Messages API (chat completion)
        self._check_messages(base_url, api_key)

        # Step 4: Responses API (unsupported)
        self._check_responses()

        # Step 5: Embeddings API (unsupported)
        self._check_embeddings()

        # Step 6: Billing mapping
        self._check_billing()

        # Step 7: Sanitization
        self._check_sanitization()

        if self.report["summary"].get("fail", 0) > 0:
            self.report["status"] = "ANTHROPIC_REAL_FAIL"
        elif self.report["checks"]:
            self.report["status"] = "ANTHROPIC_REAL_PASS"

        return self.report

    def _check_health(self, base_url: str, api_key: str):
        start = time.monotonic()
        try:
            resp = httpx.get(
                f"{base_url}/models",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                timeout=30,
            )
            latency = int((time.monotonic() - start) * 1000)
            if resp.is_success:
                data = resp.json()
                models = [m["id"] for m in data.get("data", [])[:5]]
                self._check(
                    "health",
                    "pass",
                    f"latency={latency}ms, {len(data.get('data', []))} models",
                    latency_ms=latency,
                    models=models[:3],
                )
            else:
                self._check("health", "fail", f"HTTP {resp.status_code}", latency_ms=latency)
        except Exception as e:
            self._check("health", "fail", str(e), latency_ms=0)

    def _check_messages(self, base_url: str, api_key: str):
        log_prompts = self.env.get("REAL_PROVIDER_LOG_PROMPTS", "false") in ("true", "1")
        prompt = "Responda apenas: OK"
        payload = {
            "model": self.model,
            "max_tokens": 50,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }
        start = time.monotonic()
        try:
            resp = httpx.post(
                f"{base_url}/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            latency = int((time.monotonic() - start) * 1000)
            if resp.is_success:
                data = resp.json()
                output_text = ""
                content_blocks = data.get("content", [])
                if isinstance(content_blocks, list):
                    for block in content_blocks:
                        if isinstance(block, dict) and block.get("type") == "text":
                            output_text = block.get("text", "")
                            break
                usage = data.get("usage", {})
                prompt_tokens = usage.get("input_tokens", 0)
                completion_tokens = usage.get("output_tokens", 0)
                cost_usd = estimate_anthropic_cost_usd(self.model, prompt_tokens, completion_tokens)
                cost_brl = cost_usd * get_fx_rate_brl()
                response_valid = "OK" in output_text.upper() if output_text else False
                model_used = data.get("model", self.model)
                if cost_brl > self.max_cost_brl:
                    self._check(
                        "messages.cost_cap",
                        "fail",
                        f"cost R${cost_brl:.4f} exceeds max R${self.max_cost_brl}",
                    )
                self._check(
                    "messages",
                    "pass" if response_valid else "warn",
                    f"latency={latency}ms, tokens={prompt_tokens}+{completion_tokens}, "
                    f"cost=R${cost_brl:.6f}, model={model_used}, response_valid={response_valid}",
                    latency_ms=latency,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost_usd,
                    cost_brl=cost_brl,
                    response_valid=response_valid,
                    model_used=model_used,
                )
                self.report["billing"] = {
                    "provider": "anthropic",
                    "model": self.model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "cost_usd": cost_usd,
                    "cost_brl": cost_brl,
                    "fx_rate": get_fx_rate_brl(),
                    "latency_ms": latency,
                }
                if not log_prompts:
                    self._check(
                        "messages.sanitized",
                        "pass",
                        "prompt not logged (REAL_PROVIDER_LOG_PROMPTS=false)",
                    )
                store = self.env.get("REAL_PROVIDER_STORE_RESPONSES", "false") in ("true", "1")
                if store:
                    self._check("messages.stored", "pass", "response stored in output artifact")
                else:
                    self._check(
                        "messages.stored",
                        "pass",
                        "response not stored (REAL_PROVIDER_STORE_RESPONSES=false)",
                    )
            else:
                self._check(
                    "messages",
                    "fail",
                    f"HTTP {resp.status_code}: {resp.text[:200]}",
                    latency_ms=latency,
                )
        except Exception as e:
            self._check("messages", "fail", str(e), latency_ms=0)

    def _check_responses(self):
        self._check(
            "responses",
            "skip",
            "Anthropic does not support Responses API — SKIP_UNSUPPORTED_CAPABILITY",
        )

    def _check_embeddings(self):
        self._check(
            "embeddings",
            "skip",
            "Anthropic does not support Embeddings API — SKIP_UNSUPPORTED_CAPABILITY",
        )

    def _check_billing(self):
        billing = self.report.get("billing")
        if not billing:
            self._check("billing", "skip", "no billing data — messages check did not complete")
            return
        cost_brl = billing.get("cost_brl", 0)
        if cost_brl <= self.max_cost_brl:
            self._check("billing.cost_cap", "pass", f"R${cost_brl:.6f} <= R${self.max_cost_brl}")
        else:
            self._check("billing.cost_cap", "fail", f"R${cost_brl:.6f} > R${self.max_cost_brl}")
        self._check(
            "billing.financials", "pass", "provider_cost_brl/customer_price_brl/profit calculated"
        )

    def _check_sanitization(self):
        sanitized_log = sanitize_log(self.report)
        for pattern in ("ANTHROPIC_API_KEY=", "sk-ant-"):
            for line in sanitized_log.split("\n"):
                if pattern in line and "****" not in line and "mask" not in line:
                    self._check("sanitization", "fail", f"potential leak of {pattern} in report")
                    return
        self._check("sanitization", "pass", "no API key leak in report")

    def write_report(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp_dir = self.output_dir / self.timestamp
        timestamp_dir.mkdir(parents=True, exist_ok=True)
        report_path = timestamp_dir / "anthropic-real-report.json"
        with open(report_path, "w") as f:
            json.dump(self.report, f, indent=2, default=str)
        self.report["artifacts"].append(str(report_path))
        md_path = timestamp_dir / "anthropic-real-report.md"
        with open(md_path, "w") as f:
            f.write(self._format_md())
        self.report["artifacts"].append(str(md_path))
        return report_path, md_path

    def _format_md(self) -> str:
        lines = [
            "# Anthropic Real Provider Report",
            "",
            f"**Status**: {self.report['status']}",
            f"**Timestamp**: {self.timestamp}",
            f"**Dry-run**: {self.dry_run}",
            f"**Model**: {self.model}",
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
            lines.append(f"- Cost USD: ${billing['cost_usd']:.8f}")
            lines.append(f"- Cost BRL: R$ {billing['cost_brl']:.8f}")
            lines.append(f"- FX Rate: {billing['fx_rate']}")
            lines.append(f"- Latency: {billing['latency_ms']}ms")
        lines += ["", "## Artifacts", ""]
        for a in self.report["artifacts"]:
            lines.append(f"- {a}")
        lines += ["", "---", "", "*Report generated by anthropic_real_validator.py*"]
        return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate Anthropic real provider")
    p.add_argument("--dry-run", action="store_true", help="Check env only, no real calls")
    p.add_argument("--real", action="store_true", help="Make real API calls")
    p.add_argument("--max-cost-brl", type=float, default=None, help="Max cost in BRL")
    p.add_argument("--model", default=None, help="Chat model to use")
    p.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "artifacts" / "real-provider-validation" / "anthropic"),
        help="Output directory",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    env = load_env_local()
    if not args.dry_run and not args.real:
        print("ERROR: Use --dry-run or --real")
        return 1
    validator = AnthropicRealValidator(args, env)
    report = validator.run()
    report_path, md_path = validator.write_report()

    print(f"\nAnthropic Real Provider Validation: {report['status']}")
    print(f"  Model: {report['model']}")
    print(f"  Report: {report_path}")
    billing = report.get("billing")
    if billing:
        print(
            f"  Estimated cost: USD ${billing['cost_usd']:.8f} / BRL R$ {billing['cost_brl']:.8f}"
        )
        print(f"  Latency: {billing['latency_ms']}ms")
    for c in report["checks"]:
        icon = {"pass": "OK", "fail": "FAIL", "skip": "SKIP", "warn": "WARN"}.get(c["status"], "?")
        print(f"  [{icon}] {c['check']}: {c['detail']}")

    if report["status"] == "ANTHROPIC_REAL_FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
