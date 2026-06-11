from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

from .install_wizard import InstallWizardError, run_install


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llmstack", description="LLMStack operator CLI")
    subparsers = parser.add_subparsers(dest="command")

    install = subparsers.add_parser("install", help="Run the installation wizard")
    mode = install.add_mutually_exclusive_group()
    mode.add_argument("--interactive", action="store_true", default=True)
    mode.add_argument("--non-interactive", action="store_false", dest="interactive")
    install.add_argument("--target-dir", type=Path, default=Path.cwd())
    install.add_argument("--base-url", default="http://localhost:18080")
    install.add_argument("--host-port", type=int, default=18080)
    install.add_argument("--gpu", action="store_true", dest="has_gpu", default=False)
    install.add_argument("--nvidia", action="store_true", default=False)
    install.add_argument("--amd", action="store_true", default=False)
    install.add_argument(
        "--apple-silicon",
        action="store_true",
        dest="apple_silicon",
        default=False,
    )
    install.add_argument("--users", type=int, default=5)
    install.add_argument("--multi-tenant", action="store_true", default=False)
    install.add_argument("--agentic", action="store_true", default=False)
    install.add_argument("--kubernetes", action="store_true", default=False)
    install.add_argument("--full-observability", action="store_true", default=False)
    install.add_argument("--marketplace", action="store_true", default=False)

    backup = subparsers.add_parser("backup", help="Create an encrypted logical agent backup")
    backup.add_argument("--logical-agent-backup", action="store_true", default=False, help="Create a logical agent backup")
    backup.add_argument("--full", action="store_true", default=False, help="Create a full backup (deprecated: use --logical-agent-backup)")
    backup.add_argument("--base-url", default=os.getenv("LLMSTACK_BASE_URL", "http://localhost:8080"))
    backup.add_argument("--admin-token", default=os.getenv("ADMIN_TOKEN", ""))

    restore = subparsers.add_parser("restore", help="Restore a system backup")
    restore.add_argument("backup_id", help="Backup identifier to restore")
    restore.add_argument("--dry-run", action="store_true", default=False)
    restore.add_argument(
        "--yes",
        action="store_true",
        default=False,
        help="Confirm destructive restore execution",
    )
    restore.add_argument("--base-url", default=os.getenv("LLMSTACK_BASE_URL", "http://localhost:8080"))
    restore.add_argument("--admin-token", default=os.getenv("ADMIN_TOKEN", ""))

    backups = subparsers.add_parser("backups", help="List backups")
    backups.add_argument("--base-url", default=os.getenv("LLMSTACK_BASE_URL", "http://localhost:8080"))
    backups.add_argument("--admin-token", default=os.getenv("ADMIN_TOKEN", ""))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "install":
        try:
            return run_install(args)
        except InstallWizardError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.command == "backup":
        if not args.logical_agent_backup and not args.full:
            print("ERROR: use `llmstack backup --logical-agent-backup`.", file=sys.stderr)
            return 2
        if args.full:
            print("WARNING: --full is deprecated. Use --logical-agent-backup instead.", file=sys.stderr)
        return _post_json(
            args.base_url,
            "/admin/backup",
            args.admin_token,
            {"scope": "logical-agent-backup"},
        )

    if args.command == "restore":
        if not args.dry_run and not args.yes:
            print(
                "ERROR: restore real requires explicit confirmation with `--yes`. "
                "Use `--dry-run` to validate without applying changes.",
                file=sys.stderr,
            )
            return 2
        return _post_json(
            args.base_url,
            f"/admin/backup/{args.backup_id}/restore",
            args.admin_token,
            {"dry_run": args.dry_run},
        )

    if args.command == "backups":
        return _get_json(args.base_url, "/admin/backup", args.admin_token)

    if args.command is None:
        parser.print_help()
        return 0

    parser.print_help()
    return 0


def _headers(admin_token: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if admin_token:
        headers["X-Admin-Token"] = admin_token
    return headers


def _post_json(base_url: str, path: str, admin_token: str, payload: dict[str, object]) -> int:
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}{path}",
            headers=_headers(admin_token),
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(response.text)
    return 0


def _get_json(base_url: str, path: str, admin_token: str) -> int:
    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}{path}",
            headers=_headers(admin_token),
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(response.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
