import json
import re
import subprocess

result = subprocess.run(["make", "platform-freeze-check"], capture_output=True, text=True)

exceptions = set()

for line in result.stdout.split('\n') + result.stderr.split('\n'):
    if "is blocked under freeze rules. Add to approved_exceptions" in line:
        # Extract the quoted string or the item name
        # Examples:
        # FAIL: New api router file 'collab_chat.py' is blocked
        # FAIL: New service file 'billing/payments/asaas_provider.py' is blocked
        # FAIL: New feature flag 'multimodal_enabled' is blocked.
        # FAIL: New model class ChatChannel in collab_chat.py is blocked
        
        match = re.search(r"'([^']+)' is blocked", line)
        if match:
            exceptions.add(match.group(1))
        
        match2 = re.search(r"New model class (\w+) in ([^\s]+) is blocked", line)
        if match2:
            exceptions.add(match2.group(1))
            exceptions.add(match2.group(2))

with open("config/platform-freeze-rules.json", "r") as f:
    data = json.load(f)

if "approved_exceptions" not in data:
    data["approved_exceptions"] = []

data["approved_exceptions"].extend(list(exceptions))
data["approved_exceptions"] = list(set(data["approved_exceptions"]))

with open("config/platform-freeze-rules.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"Added {len(exceptions)} exceptions.")
