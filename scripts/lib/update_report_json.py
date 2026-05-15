#!/usr/bin/env python3
import json
import sys
import os

report_path = sys.argv[1]
category = sys.argv[2]
name = sys.argv[3]
status = sys.argv[4]
message = sys.argv[5]
details = sys.argv[6] if len(sys.argv) > 6 else None

if not os.path.exists(report_path):
    data = {"checks": {}}
else:
    with open(report_path, 'r') as f:
        data = json.load(f)

if category not in data['checks']:
    data['checks'][category] = []

data['checks'][category].append({
    "name": name,
    "status": status,
    "message": message,
    "details": details
})

with open(report_path, 'w') as f:
    json.dump(data, f, indent=2)
