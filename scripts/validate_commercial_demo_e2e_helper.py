#!/usr/bin/env python3
"""Helper for validate-commercial-demo-e2e-local.sh.

Commands:
  generate_json <output_file> <timestamp> <version> <base_url>
      <reset_first> <seed_demo> <skip_tts> <skip_rag> <skip_lmstudio>
      <pass_count> <fail_count> <warn_count>
      <results_file> <warnings_file> <errors_file>
      <status>
"""
import json
import os
import sys


def generate_json(args):
    (
        output_file, timestamp, version, base_url,
        reset_first, seed_demo, skip_tts, skip_rag, skip_lmstudio,
        pass_count, fail_count, warn_count,
        results_file, warnings_file, errors_file,
        status,
    ) = args

    def read_lines(path):
        if os.path.isfile(path):
            with open(path) as f:
                return [line.strip() for line in f if line.strip()]
        return []

    results = read_lines(results_file)
    warnings = read_lines(warnings_file)
    errors = read_lines(errors_file)

    data = {
        "tool": "scripts/validate-commercial-demo-e2e-local.sh",
        "timestamp": timestamp,
        "version": version,
        "base_url": base_url,
        "flags": {
            "reset_first": reset_first.lower() == "true",
            "seed_demo": seed_demo.lower() == "true",
            "skip_tts": skip_tts.lower() == "true",
            "skip_rag": skip_rag.lower() == "true",
            "skip_lmstudio": skip_lmstudio.lower() == "true",
        },
        "status": status,
        "counts": {
            "pass": int(pass_count),
            "fail": int(fail_count),
            "warn": int(warn_count),
        },
        "results": results,
        "warnings": warnings,
        "errors": errors,
        "limitations": [
            "Real PSP/PIX not included — manual billing only",
            "Tools/Function Calling may be partial",
            "TTS may not be available without pocket-tts",
            "RAG requires running data plane with embedding support",
            "LM Studio integration depends on external backend",
        ],
        "report_paths": {
            "json": output_file,
            "md": output_file.replace(".json", ".md"),
            "logs": os.path.join(os.path.dirname(output_file), "logs"),
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
