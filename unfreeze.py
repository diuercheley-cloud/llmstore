import json

with open("config/platform-freeze-rules.json", "r") as f:
    data = json.load(f)

for key in data:
    if isinstance(data[key], bool):
        data[key] = False

with open("config/platform-freeze-rules.json", "w") as f:
    json.dump(data, f, indent=2)
