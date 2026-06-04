import logging
from typing import Any, Dict, List, Optional, Tuple

from .providers import create_code_agent

logger = logging.getLogger(__name__)

def is_cloud_provider(provider_name: str) -> bool:
    return provider_name in ("openai-compatible", "anthropic", "google", "control-plane")

class ModelRouter:
    def __init__(self, config: Any):
        self.config = config
        self.models_config = getattr(config, "models", {}) or {}

    def get_profiles(self) -> Dict[str, Dict[str, Any]]:
        return self.models_config.get("profiles", {})

    def resolve_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        profiles = self.get_profiles()
        if profile_name in profiles:
            return dict(profiles[profile_name])
        return None

    def get_default_profile_name(self) -> Optional[str]:
        return self.models_config.get("default")

    def resolve_by_task_type(self, task_type: str) -> Tuple[Optional[str], Dict[str, Any]]:
        routing = self.models_config.get("routing", {})
        profile_name = routing.get(task_type)
        if not profile_name:
            profile_name = self.get_default_profile_name()

        if profile_name:
            profile_cfg = self.resolve_profile(profile_name)
            if profile_cfg:
                return profile_name, profile_cfg

        # Fallback to global config settings
        fallback_cfg = {
            "provider": (
                getattr(self.config, "provider", None)
                or getattr(self.config, "code_agent", "stub")
            ),
            "model": getattr(self.config, "model", "stub"),
            "base_url": getattr(self.config, "base_url", ""),
            "timeout": getattr(self.config, "timeout", 30.0),
        }
        return "default-config", fallback_cfg

    def check_policy(self, profile_config: Dict[str, Any]) -> bool:
        provider = profile_config.get("provider", "")
        # Check global config or models allow_cloud_models setting
        allow_cloud = True
        if hasattr(self.config, "allow_cloud_models"):
            if self.config.allow_cloud_models is not None:
                allow_cloud = self.config.allow_cloud_models
        elif isinstance(self.models_config, dict):
            allow_cloud = self.models_config.get("allow_cloud_models", True)

        if not allow_cloud and is_cloud_provider(provider):
            return False
        return True

    def estimate_cost(self, profile_config: Dict[str, Any]) -> Dict[str, Any]:
        provider = profile_config.get("provider", "")
        model = profile_config.get("model", "")

        if provider in ("local-openai-compatible", "stub", "fake"):
            return {
                "prompt_token_price_per_1m": 0.0,
                "completion_token_price_per_1m": 0.0,
                "currency": "USD",
                "is_local": True
            }

        from .pricing import DEFAULT_PRICING
        pricing_info = None
        for k, v in DEFAULT_PRICING.items():
            if k in model or model in k:
                pricing_info = v
                break

        if pricing_info:
            return {
                "prompt_token_price_per_1m": pricing_info["prompt_token_price_per_1m"],
                "completion_token_price_per_1m": pricing_info["completion_token_price_per_1m"],
                "currency": pricing_info["currency"],
                "is_local": False
            }

        return {
            "prompt_token_price_per_1m": 10.0,
            "completion_token_price_per_1m": 30.0,
            "currency": "USD",
            "is_local": False
        }

    async def chat_completion_with_fallback(
        self,
        messages: List[Dict[str, Any]],
        task_type: Optional[str] = None,
        profile_name: Optional[str] = None,
        fallback_profile_name: Optional[str] = None,
        plain_chat: bool = False,
    ) -> Any:
        primary_cfg: Dict[str, Any] = {}
        # 1. Determine primary profile
        resolved_name = profile_name or getattr(self.config, "model_profile", None)
        if resolved_name:
            resolved_cfg = self.resolve_profile(resolved_name)
            if not resolved_cfg:
                raise ValueError(
                    f"Model profile '{resolved_name}' not found in configuration."
                )
            primary_cfg = resolved_cfg
        elif task_type:
            resolved_name, primary_cfg = self.resolve_by_task_type(task_type)
        else:
            default_name = self.get_default_profile_name()
            resolved_cfg = self.resolve_profile(default_name) if default_name else None
            if resolved_cfg:
                resolved_name = default_name
                primary_cfg = resolved_cfg
            else:
                resolved_name = "default-config"
                primary_cfg = {
                    "provider": (
                        getattr(self.config, "provider", None)
                        or getattr(self.config, "code_agent", "stub")
                    ),
                    "model": getattr(self.config, "model", "stub"),
                    "base_url": getattr(self.config, "base_url", ""),
                    "timeout": getattr(self.config, "timeout", 30.0),
                }

        # Check policy
        if not self.check_policy(primary_cfg):
            raise PermissionError(
                f"Cloud model provider '{primary_cfg.get('provider')}' "
                "is blocked by policy."
            )

        # Build config override dict
        cfg_dict = self.config.model_dump() if hasattr(self.config, "model_dump") else {}
        cfg_dict.update(primary_cfg)
        if plain_chat:
            cfg_dict["plain_chat"] = True

        try:
            agent = create_code_agent(primary_cfg.get("provider", "stub"), cfg_dict)
            return await agent.chat_completion(messages)
        except Exception as e:
            logger.warning(
                f"Primary model profile '{resolved_name}' failed: {e}. "
                "Attempting fallback..."
            )
            # Try fallback
            fb_name = (
                fallback_profile_name
                or getattr(self.config, "fallback_model_profile", None)
            )
            fb_cfg: Dict[str, Any] = {}
            if fb_name:
                resolved_fb_cfg = self.resolve_profile(fb_name)
                if not resolved_fb_cfg:
                    raise ValueError(f"Fallback model profile '{fb_name}' not found.")
                fb_cfg = resolved_fb_cfg
            else:
                # Default fallback is config default
                fb_name = "default-config"
                fb_cfg = {
                    "provider": (
                        getattr(self.config, "provider", None)
                        or getattr(self.config, "code_agent", "stub")
                    ),
                    "model": getattr(self.config, "model", "stub"),
                    "base_url": getattr(self.config, "base_url", ""),
                    "timeout": getattr(self.config, "timeout", 30.0),
                }

            if not self.check_policy(fb_cfg):
                raise PermissionError(
                    f"Fallback cloud model provider '{fb_cfg.get('provider')}' "
                    "is blocked by policy."
                )

            fb_cfg_dict = self.config.model_dump() if hasattr(self.config, "model_dump") else {}
            fb_cfg_dict.update(fb_cfg)
            if plain_chat:
                fb_cfg_dict["plain_chat"] = True

            agent_fb = create_code_agent(fb_cfg.get("provider", "stub"), fb_cfg_dict)
            return await agent_fb.chat_completion(messages)

