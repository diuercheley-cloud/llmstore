import json
import logging

from app.utils.tool_calling import filter_unsupported_tooling_parameters

logging.basicConfig(level=logging.WARNING)

payload = {
    "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "tools": [{"type": "function", "function": {"name": "question"}}],
    "tool_choice": "auto",
    "parallel_tool_calls": True
}

metadata = {} # Empty metadata, as in our database
provider = "openrouter"

print("Before:", payload)
updated = filter_unsupported_tooling_parameters(provider, payload, json.dumps(metadata))
print("After:", updated)

