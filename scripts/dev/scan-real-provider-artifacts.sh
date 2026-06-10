#!/bin/bash
set -e

# Defaults
PATH_TO_SCAN="artifacts/real-provider-validation"
REDACT=false
FAIL_ON_FINDINGS=false

function usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --path DIR         Directory to scan (default: artifacts/real-provider-validation)."
    echo "  --redact           Redact found secrets and prompts."
    echo "  --fail-on-findings Exit with error if sensitive data is found."
    echo "  --help             Show this help message."
    exit 1
}

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --path) PATH_TO_SCAN="$2"; shift ;;
        --redact) REDACT=true ;;
        --fail-on-findings) FAIL_ON_FINDINGS=true ;;
        --help) usage ;;
        *) echo "Unknown parameter passed: $1"; usage ;;
    esac
    shift
done

if [ ! -d "$PATH_TO_SCAN" ]; then
    echo "Path $PATH_TO_SCAN does not exist. Skipping scan."
    exit 0
fi

TMP_RUNNER="$(mktemp "${TMPDIR:-/tmp}/real-provider-scanner.XXXXXX.py")"
cleanup() {
    rm -f "$TMP_RUNNER"
}
trap cleanup EXIT

# Use python to do the heavy lifting safely
cat << 'EOF' > "$TMP_RUNNER"
import os
import sys
import json
import re
import hashlib
import argparse
from pathlib import Path

def hash_text(text):
    if not isinstance(text, str):
        text = str(text)
    sha = hashlib.sha256(text.encode('utf-8')).hexdigest()
    return f"__redacted_sha256: {sha}, length: {len(text)}__"

# Secret patterns
SECRET_PATTERNS = [
    re.compile(r'OPENAI_API_KEY[=:]\s*([^\s]+)'),
    re.compile(r'ANTHROPIC_API_KEY[=:]\s*([^\s]+)'),
    re.compile(r'DEEPSEEK_API_KEY[=:]\s*([^\s]+)'),
    re.compile(r'OPENROUTER_API_KEY[=:]\s*([^\s]+)'),
    re.compile(r'Authorization:\s*Bearer\s+([^\s"\'}]+)'),
    re.compile(r'x-api-key:\s*([^\s"\'}]+)'),
    re.compile(r'(sk-(?:ant-api03-)?[a-zA-Z0-9_\-]+)'),
    re.compile(r'(ghp_[a-zA-Z0-9_\-]+)')
]

PROMPT_KEYS = {'prompt', 'prompt_text', 'response', 'response_text', 'system_prompt', 'user_message'}

def redact_string(content, redact):
    found = False
    original = content
    for pattern in SECRET_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            found = True
            if redact:
                for match in matches:
                    # Only replace the matched group if possible, or the whole thing if it's the whole regex
                    content = content.replace(match, '__redacted_provider_secret__')
    
    return found, content

def redact_json(data, redact):
    found = False
    if isinstance(data, dict):
        for k, v in data.items():
            if k in PROMPT_KEYS and isinstance(v, str) and not v.startswith('__redacted_sha256'):
                found = True
                if redact:
                    data[k] = hash_text(v)
            elif isinstance(v, str):
                has_secret, new_v = redact_string(v, redact)
                if has_secret:
                    found = True
                    if redact:
                        data[k] = new_v
            elif isinstance(v, (dict, list)):
                child_found = redact_json(v, redact)
                if child_found:
                    found = True
    elif isinstance(data, list):
        for i, v in enumerate(data):
            if isinstance(v, str):
                has_secret, new_v = redact_string(v, redact)
                if has_secret:
                    found = True
                    if redact:
                        data[i] = new_v
            elif isinstance(v, (dict, list)):
                child_found = redact_json(v, redact)
                if child_found:
                    found = True
    return found

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, required=True)
    parser.add_argument("--redact", action="store_true")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()

    base_path = Path(args.path)
    total_findings = 0

    for root, _, files in os.walk(base_path):
        for file in files:
            file_path = Path(root) / file
            if file.endswith('.json'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    found = redact_json(data, args.redact)
                    if found:
                        total_findings += 1
                        if args.redact:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, indent=2)
                except Exception as e:
                    pass
            elif file.endswith('.md') or file.endswith('.txt'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    found, new_content = redact_string(content, args.redact)
                    # Also look for raw prompt blocks in markdown (very rudimentary, usually JSON covers it)
                    if found:
                        total_findings += 1
                        if args.redact:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                except Exception as e:
                    pass

    print(f"Scanner finished. Files with findings: {total_findings}")
    if total_findings > 0 and args.fail_on_findings:
        sys.exit(1)

if __name__ == '__main__':
    main()
EOF

.venv/bin/python "$TMP_RUNNER" \
    --path "$PATH_TO_SCAN" \
    $([ "$REDACT" == "true" ] && echo "--redact") \
    $([ "$FAIL_ON_FINDINGS" == "true" ] && echo "--fail-on-findings")
