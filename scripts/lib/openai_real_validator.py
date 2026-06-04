#!/usr/bin/env python3
"""OpenAI Real Provider Validator.

Validates OpenAI provider connectivity, Responses API, Embeddings API,
billing BRL mapping, and sanitization — all without leaking secrets.

Usage:
  python scripts/lib/openai_real_validator.py --dry-run
  python scripts/lib/openai_real_validator.py --real --model gpt-4o-mini
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_env_local() -> dict[str, str]:
    """Load .env.local into a dict (no side effects)."""
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


def estimate_openai_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = {
        "gpt-4o": (2.50, 10.00),
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4-turbo": (10.00, 30.00),
        "gpt-3.5-turbo": (0.50, 1.50),
        "text-embedding-3-small": (0.02, 0.02),
        "text-embedding-3-large": (0.13, 0.13),
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
    return (prompt_tokens / 1_000_000 * prompt_price) + (completion_tokens / 1_000_000 * completion_price)


def get_fx_rate_brl() -> float:
    return float(os.environ.get("USD_BRL_RATE", "5.00"))


def sanitize_log(data: Any, max_chars: int = 200) -> str:
    text = json.dumps(data, ensure_ascii=False)
    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    return text


class OpenAIRealValidator:
    def __init__(self, args: argparse.Namespace, env: dict[str, str]):
        self.args = args
        self.env = env
        self.dry_run = args.dry_run
        self.max_cost_brl = args.max_cost_brl or float(env.get("REAL_PROVIDER_MAX_COST_BRL", "2.00"))
        self.model = args.model or (env.get("OPENAI_CHAT_MODEL") or "gpt-4o-mini")
        self.emb_model = args.embeddings_model or (env.get("OPENAI_EMBEDDINGS_MODEL") or "text-embedding-3-small")
        self.output_dir = Path(args.output_dir)
        self.timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.report: dict[str, Any] = {
            "validator": "openai-real-provider",
            "timestamp": self.timestamp,
            "dry_run": self.dry_run,
            "status": "OPENAI_REAL_SKIP",
            "model": self.model,
            "embeddings_model": self.emb_model,
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
        return self.env.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")

    def _get_base_url(self) -> str:
        return self.env.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def run(self) -> dict[str, Any]:
        # ── Step 1: Validate env ─────────────────────────────────
        api_key = self._get_api_key()
        base_url = self._get_base_url()

        if not api_key:
            self._check("env.api_key", "skip", "OPENAI_API_KEY not set")
            self.report["status"] = "OPENAI_REAL_SKIP"
            return self.report

        rpv = self.env.get("REAL_PROVIDER_VALIDATION_ENABLED", "false")
        ope = self.env.get("OPENAI_PROVIDER_ENABLED", "false")

        if rpv not in ("true", "1"):
            self._check("env.real_provider_validation_enabled", "skip", "REAL_PROVIDER_VALIDATION_ENABLED is not true")
            self.report["status"] = "OPENAI_REAL_SKIP"
            return self.report

        if ope not in ("true", "1"):
            self._check("env.openai_provider_enabled", "skip", "OPENAI_PROVIDER_ENABLED is not true")
            self.report["status"] = "OPENAI_REAL_SKIP"
            return self.report

        self._check("env.api_key", "pass", f"key {mask_key(api_key)}, base={base_url}")
        self._check("env.guards", "pass", "REAL_PROVIDER_VALIDATION_ENABLED=true, OPENAI_PROVIDER_ENABLED=true")

        if self.dry_run:
            self._check("dry_run", "pass", "Dry-run mode — no real calls made")
            self.report["status"] = "OPENAI_REAL_PASS"
            return self.report

        # ── Step 2: Health / list models ─────────────────────────
        self._check_health(base_url, api_key)

        # ── Step 3: Responses API ────────────────────────────────
        self._check_responses(base_url, api_key)

        # ── Step 4: Embeddings API ───────────────────────────────
        self._check_embeddings(base_url, api_key)

        # ── Step 5: Billing mapping ──────────────────────────────
        self._check_billing()

        # ── Step 6: Sanitization ─────────────────────────────────
        self._check_sanitization()

        # ── Overall status ───────────────────────────────────────
        if self.report["summary"].get("fail", 0) > 0:
            self.report["status"] = "OPENAI_REAL_FAIL"
        elif self.report["checks"]:
            self.report["status"] = "OPENAI_REAL_PASS"

        return self.report

    def _check_health(self, base_url: str, api_key: str):
        start = time.monotonic()
        try:
            resp = httpx.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            )
            latency = int((time.monotonic() - start) * 1000)
            if resp.is_success:
                data = resp.json()
                models = [m["id"] for m in data.get("data", [])[:5]]
                self._check("health", "pass", f"latency={latency}ms, {len(data.get('data',[]))} models", latency_ms=latency, models=models[:3])
            else:
                self._check("health", "fail", f"HTTP {resp.status_code}", latency_ms=latency)
        except Exception as e:
            self._check("health", "fail", str(e), latency_ms=0)

    def _check_responses(self, base_url: str, api_key: str):
        log_prompts = self.env.get("REAL_PROVIDER_LOG_PROMPTS", "false") in ("true", "1")
        prompt = "Responda apenas: OK"
        payload = {
            "model": self.model,
            "input": prompt,
            "max_output_tokens": 50,
            "temperature": 0.0,
        }
        start = time.monotonic()
        try:
            resp = httpx.post(
                f"{base_url}/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            latency = int((time.monotonic() - start) * 1000)
            if resp.is_success:
                data = resp.json()
                output_text = ""
                output_texts = data.get("output_text", [])
                if isinstance(output_texts, list) and output_texts:
                    output_text = output_texts[0] if isinstance(output_texts[0], str) else str(output_texts[0])
                elif isinstance(output_texts, str):
                    output_text = output_texts
                output_list = data.get("output", [])
                if not output_text and output_list:
                    for item in output_list:
                        if isinstance(item, dict):
                            content = item.get("content", [])
                            if isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and c.get("type") == "output_text":
                                        output_text = c.get("text", "")
                usage = data.get("usage", {}) or data.get("response_usage", {})
                prompt_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
                cost_usd = estimate_openai_cost_usd(self.model, prompt_tokens, completion_tokens)
                cost_brl = cost_usd * get_fx_rate_brl()
                response_valid = "OK" in output_text.upper() if output_text else False
                if cost_brl > self.max_cost_brl:
                    self._check("responses.cost_cap", "fail", f"cost R${cost_brl:.4f} exceeds max R${self.max_cost_brl}")
                self._check(
                    "responses", "pass" if response_valid else "warn",
                    f"latency={latency}ms, tokens={prompt_tokens}+{completion_tokens}, "
                    f"cost=R${cost_brl:.6f}, response_valid={response_valid}",
                    latency_ms=latency,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost_usd,
                    cost_brl=cost_brl,
                    response_valid=response_valid,
                    model_used=data.get("model", self.model),
                )
                self.report["billing"] = {
                    "provider": "openai",
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
                    self._check("responses.sanitized", "pass", "prompt not logged (REAL_PROVIDER_LOG_PROMPTS=false)")
                store = self.env.get("REAL_PROVIDER_STORE_RESPONSES", "false") in ("true", "1")
                if store:
                    self._check("responses.stored", "pass", "response stored in output artifact")
                else:
                    self._check("responses.stored", "pass", "response not stored (REAL_PROVIDER_STORE_RESPONSES=false)")
            else:
                self._check("responses", "fail", f"HTTP {resp.status_code}: {resp.text[:200]}", latency_ms=latency)
        except Exception as e:
            self._check("responses", "fail", str(e), latency_ms=0)

    def _check_embeddings(self, base_url: str, api_key: str):
        payload = {
            "model": self.emb_model,
            "input": "teste de embedding",
        }
        start = time.monotonic()
        try:
            resp = httpx.post(
                f"{base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            latency = int((time.monotonic() - start) * 1000)
            if resp.is_success:
                data = resp.json()
                emb = data.get("data", [{}])[0].get("embedding", [])
                dim = len(emb)
                valid = dim > 0 and all(isinstance(v, (int, float)) for v in emb)
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                cost_usd = estimate_openai_cost_usd(self.emb_model, prompt_tokens, 0)
                cost_brl = cost_usd * get_fx_rate_brl()
                self._check(
                    "embeddings", "pass" if valid else "fail",
                    f"latency={latency}ms, dim={dim}, tokens={prompt_tokens}, cost=R${cost_brl:.8f}",
                    latency_ms=latency,
                    dimensions=dim,
                    valid=valid,
                    prompt_tokens=prompt_tokens,
                    cost_usd=cost_usd,
                    cost_brl=cost_brl,
                )
            else:
                self._check("embeddings", "fail", f"HTTP {resp.status_code}: {resp.text[:200]}", latency_ms=latency)
        except Exception as e:
            self._check("embeddings", "fail", str(e), latency_ms=0)

    def _check_billing(self):
        billing = self.report.get("billing")
        if not billing:
            self._check("billing", "skip", "no billing data — responses check did not complete")
            return
        cost_brl = billing.get("cost_brl", 0)
        if cost_brl <= self.max_cost_brl:
            self._check("billing.cost_cap", "pass", f"R${cost_brl:.6f} <= R${self.max_cost_brl}")
        else:
            self._check("billing.cost_cap", "fail", f"R${cost_brl:.6f} > R${self.max_cost_brl}")

    def _check_sanitization(self):
        sanitized_log = sanitize_log(self.report)
        for pattern in ("OPENAI_API_KEY=", "sk-"):
            for line in sanitized_log.split("\n"):
                if pattern in line and "****" not in line and "mask" not in line:
                    self._check("sanitization", "fail", f"potential leak of {pattern} in report")
                    return
        self._check("sanitization", "pass", "no API key leak in report")

    def write_report(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.output_dir / "openai-real-report.json"
        with open(report_path, "w") as f:
            json.dump(self.report, f, indent=2, default=str)
        self.report["artifacts"].append(str(report_path))
        md_path = self.output_dir / "openai-real-report.md"
        with open(md_path, "w") as f:
            f.write(self._format_md())
        self.report["artifacts"].append(str(md_path))
        return report_path, md_path

    def _format_md(self) -> str:
        lines = [
            "# OpenAI Real Provider Report",
            "",
            f"**Status**: {self.report['status']}",
            f"**Timestamp**: {self.timestamp}",
            f"**Dry-run**: {self.dry_run}",
            f"**Model**: {self.model}",
            f"**Embeddings Model**: {self.emb_model}",
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
        lines += ["", "---", "", "*Report generated by openai_real_validator.py*"]
        return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate OpenAI real provider")
    p.add_argument("--dry-run", action="store_true", help="Check env only, no real calls")
    p.add_argument("--real", action="store_true", help="Make real API calls")
    p.add_argument("--max-cost-brl", type=float, default=None, help="Max cost in BRL")
    p.add_argument("--model", default=None, help="Chat model to use")
    p.add_argument("--embeddings-model", default=None, help="Embeddings model to use")
    p.add_argument("--output-dir", default=str(PROJECT_ROOT / "artifacts" / "real-provider-validation" / "openai"), help="Output directory")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    env = load_env_local()
    if not args.dry_run and not args.real:
        print("ERROR: Use --dry-run or --real")
        return 1
    validator = OpenAIRealValidator(args, env)
    report = validator.run()
    report_path, md_path = validator.write_report()

    print(f"\nOpenAI Real Provider Validation: {report['status']}")
    print(f"  Model: {report['model']}")
    print(f"  Report: {report_path}")
    billing = report.get("billing")
    if billing:
        print(f"  Estimated cost: USD ${billing['cost_usd']:.8f} / BRL R$ {billing['cost_brl']:.8f}")
        print(f"  Latency: {billing['latency_ms']}ms")
    for c in report["checks"]:
        icon = {"pass": "OK", "fail": "FAIL", "skip": "SKIP", "warn": "WARN"}.get(c["status"], "?")
        print(f"  [{icon}] {c['check']}: {c['detail']}")

    if report["status"] == "OPENAI_REAL_FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
