#!/usr/bin/env python3
import json
import re
import sys
import argparse

# Regex patterns for sensitive data
REDACT_PATTERNS = [
    r"sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}",
    r"ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}",
    r"JWT_SECRET=[a-zA-Z0-9._-]{12,}",
    r"ghp_[a-zA-Z0-9]{36}",
    r"Bearer [a-zA-Z0-9._-]{20,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"[a-zA-Z0-9_+.-]+:[a-zA-Z0-9_+.-]+@(?:[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|localhost|127\.0\.0\.1)",
    r"Authorization:\s*Bearer\s+[a-zA-Z0-9._-]{20,}",
    r"X-Admin-Token:\s*[a-zA-Z0-9._-]{12,}",
    r"API_KEY=[a-zA-Z0-9._-]{12,}",
    r"DATABASE_URL=[a-z]+://[^:]+:[^@]+@[^/]+",
    r"REDIS_URL=[a-z]+://:[^@]+@[^/]+"
]

SAFE_PATTERNS = [
    r"sk-local-example",
    r"admin-token-123",
    r"your-api-key",
    r"changeme",
    r"example",
    r"localhost",
    r"admin-token-example",
    r"sk-example",
    r"__redacted__",
    r"FAKE SECRET FOR TESTS ONLY"
]

def redact_string(val):
    if not isinstance(val, str):
        return val
    
    for pattern in REDACT_PATTERNS:
        def replace_func(match):
            m_val = match.group(0)
            for safe in SAFE_PATTERNS:
                if re.search(safe, m_val):
                    return m_val
            
            if "=" in m_val and not m_val.startswith("---"):
                key, _ = m_val.split("=", 1)
                return f"{key}=[REDACTED]"
            if "Bearer " in m_val:
                return "Bearer [REDACTED]"
            if "X-Admin-Token: " in m_val:
                return "X-Admin-Token: [REDACTED]"
            return "[REDACTED]"
            
        val = re.sub(pattern, replace_func, val)
    return val

def redact_obj(obj):
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [redact_obj(i) for i in obj]
    elif isinstance(obj, str):
        return redact_string(obj)
    else:
        return obj

def main():
    parser = argparse.ArgumentParser(description="Redact sensitive information from JSON.")
    parser.add_argument("input", nargs="?", type=argparse.FileType("r"), default=sys.stdin)
    parser.add_argument("--inplace", "-i", help="Modify file in place", action="store_true")
    parser.add_argument("--file", "-f", help="File to process")
    
    args = parser.parse_args()
    
    if args.file:
        with open(args.file, "r") as f:
            data = json.load(f)
    else:
        data = json.load(args.input)
        
    redacted_data = redact_obj(data)
    
    if args.inplace and args.file:
        with open(args.file, "w") as f:
            json.dump(redacted_data, f, indent=2)
            f.write("\n")
    else:
        json.dump(redacted_data, sys.stdout, indent=2)
        sys.stdout.write("\n")

if __name__ == "__main__":
    main()
