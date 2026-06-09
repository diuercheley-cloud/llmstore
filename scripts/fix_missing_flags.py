from pathlib import Path

import yaml

ff_path = Path("config/feature-flags.yaml")
with open(ff_path, "r") as f:
    flags = yaml.safe_load(f)

existing_names = {f["name"] for f in flags}

missing = [
    "CARD_PAYMENT_ENABLED",
    "COLLAB_CHAT_ENABLED",
    "COLLAB_CHAT_WEBSOCKET_ENABLED",
    "MILVUS_ENABLED",
    "MOBILE_FOUNDATION_ENABLED",
    "MODEL_AB_TESTING_ENABLED",
    "MODEL_CANARY_ENABLED",
    "MODEL_EXPERIMENTS_ENABLED",
    "PIX_PAYMENT_ENABLED",
    "PUSH_NOTIFICATIONS_ENABLED",
    "QDRANT_ENABLED",
    "REALTIME_VOICE_ENABLED",
    "VECTOR_DB_PROVIDER",
    "VLLM_BACKEND_ENABLED",
    "VLLM_DEFAULT_MODEL",
    "VLLM_OPENAI_COMPAT_ENABLED",
    "WEAVIATE_ENABLED",
    "WEBRTC_AUDIO_ENABLED",
    "WEB_IDE_ENABLED"
]

for m in missing:
    if m not in existing_names:
        default_val = False
        if "PROVIDER" in m or "MODEL" in m:
            default_val = "none"
            
        flags.append({
            "name": m,
            "default": default_val,
            "owner": "platform",
            "area": "core",
            "status": "beta",
            "introduced_in": "v2.0.2-agentic-platform-expansion",
            "risk_level": "low",
            "dependencies": [],
            "conflicts": [],
            "safe_default_reason": "Opt-in by default to ensure safety."
        })

with open(ff_path, "w") as f:
    yaml.dump(flags, f, sort_keys=False, default_flow_style=False)
