# Owner: agent-platform
import logging
from typing import Any, Dict, List, Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class SemanticModelFallback:
    """
    Handles model fallback based on semantic capabilities and failure modes.
    """
    def __init__(self):
        self.settings = get_settings()

    async def get_fallback_model(self, current_model: str, failure_reason: str) -> Optional[str]:
        if not self.settings.agent_semantic_model_fallback_enabled:
            return None

        # Fallback map based on failure reason and current model
        fallback_map = {
            "json_malformed": {"gpt-4o-mini": "gpt-4o", "llama-3-8b": "gpt-4o-mini"},
            "context_length_exceeded": {"gpt-4o": "gpt-4o-32k", "gpt-3.5-turbo": "gpt-4o-mini"},
            "provider_failure": {"openai": "anthropic", "anthropic": "google"}
        }

        reason_lower = failure_reason.lower()
        if "json" in reason_lower or "structured" in reason_lower:
            return fallback_map["json_malformed"].get(current_model, "gpt-4o")
        
        if "context" in reason_lower:
            return fallback_map["context_length_exceeded"].get(current_model, "gpt-4o-32k")
        
        if "provider" in reason_lower or "rate limit" in reason_lower:
            return "anthropic" # Simplified fallback to different provider
        
        return None
