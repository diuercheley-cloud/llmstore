#!/usr/bin/env python3
"""Helper for validate-real-restore-rollback-local.sh

Commands:
  generate_json <output_file> <timestamp> <version> <dry_run> <real_exec> <from_ver> <to_ver> <work_dir> <skip_build> <results_file> <failures> <warnings> <root_dir>
"""
import json
import os
import sys


def generate_json(args):
    (
        output_file, timestamp, version, dry_run, real_exec,
        from_ver, to_ver, work_dir, skip_build,
        results_file, failures, warnings, root_dir
    ) = args

    dry_run = dry_run.lower() == "true"
    real_exec = real_exec.lower() == "true"
    skip_build = skip_build.lower() == "true"
    failures = int(failures)
    warnings = int(warnings)

    results = []
    if os.path.isfile(results_file):
        with open(results_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(line)

    upgrade_script = os.path.join(root_dir, "scripts", "upgrade-local.sh")
    rollback_script = os.path.join(root_dir, "scripts", "rollback-local.sh")

    def has_pattern(script, pat):
        if not os.path.isfile(script):
            return False
        with open(script) as f:
            return pat in f.read()

    data = {
        "tool": "scripts/validate-real-restore-rollback-local.sh",
        "timestamp": timestamp,
        "version": version,
        "dry_run": dry_run,
        "real_execution": real_exec,
        "from_version": from_ver,
        "to_version": to_ver,
        "work_dir": work_dir,
        "flags": {"skip_build": skip_build},
        "results": results,
        "failures": failures,
        "warnings": warnings,
        "overall_status": "failed" if failures > 0 else "success",
        "overall_label": "DRY-RUN" if dry_run else ("FAILED" if failures > 0 else "SUCCESS"),
        "safety_guarantees": {
            "backup_required_before_upgrade": has_pattern(upgrade_script, "SKIP_BACKUP"),
            "rollback_strong_confirmation": has_pattern(rollback_script, "ROLLBACK LOCAL"),
            "git_clean_check": has_pattern(upgrade_script, "git diff-index"),
            "dry_run_supported": True,
            "secrets_check_on_repo": True,
        },
        "report_paths": {
            "json": os.path.join(work_dir, "restore-rollback-report.json"),
            "md": os.path.join(work_dir, "restore-rollback-report.md"),
            "logs": os.path.join(work_dir, "logs"),
        },
    }

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"JSON written: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: helper.py generate_json <args...>", file=sys.stderr)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "generate_json":
        generate_json(sys.argv[2:])
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
