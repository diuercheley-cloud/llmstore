import logging
from typing import List, Dict, Any, Tuple
from app.core.config import get_settings
from app.utils.token_estimator import estimate_prompt_tokens
from app.services.tokenizer_service import TokenizerService

logger = logging.getLogger(__name__)
settings = get_settings()

class ContextManager:
    def __init__(self):
        self.max_context_tokens = settings.inference_max_context_tokens
        self.max_completion_tokens = settings.inference_max_completion_tokens
        self.max_system_chars = settings.inference_max_system_chars
        self.max_history_messages = settings.inference_max_history_messages

    async def manage(
        self,
        messages: List[Dict[str, Any]],
        requested_max_tokens: int | None = None,
        model_id: str | None = None,
        tokenizer: TokenizerService | None = None,
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """
        Manage chat context to optimize inference quality and performance.
        Returns (processed_messages, final_max_tokens, metrics).
        """
        if tokenizer:
            token_res = await tokenizer.count_chat_tokens(messages, model=model_id)
            original_tokens_estimate = token_res.input_tokens
            method = token_res.method
            is_estimated = token_res.is_estimated
        else:
            original_tokens_estimate = estimate_prompt_tokens(messages=messages)
            method = "estimated"
            is_estimated = True

        metrics = {
            "model": model_id,
            "original_message_count": len(messages),
            "final_message_count": 0,
            "original_tokens_estimate": original_tokens_estimate,
            "final_tokens_estimate": 0,
            "token_count_method": method,
            "tokens_estimated": is_estimated,
            "truncated": False,
            "simple_input_mode": False,
        }
        
        # ... rest of the method logic should use tokenizer if available ...
        # For simplicity in this step, I'll keep using estimate_prompt_tokens inside the loop
        # but I should ideally use the tokenizer if provided.
        
        async def _count(msgs):
            if tokenizer:
                res = await tokenizer.count_chat_tokens(msgs, model=model_id)
                return res.input_tokens
            return estimate_prompt_tokens(messages=msgs)
        
        # 1. Clean messages (remove empty, duplicates, and very short repeated content)
        seen_content = set()
        processed_messages = []
        for m in messages:
            content = str(m.get("content", "")).strip()
            if not content:
                continue
            
            # Simple deduplication for exact repeated content (especially very short ones <= 2 chars)
            if content in seen_content and (len(content) <= 2 or m["role"] == "user"):
                metrics["truncated"] = True
                continue
            
            processed_messages.append(m)
            seen_content.add(content)

        if not processed_messages:
            return messages, requested_max_tokens or 256, metrics

        # 2. Detect Simple Input Mode
        last_user_msg = next((m for m in reversed(processed_messages) if m["role"] == "user"), None)
        if last_user_msg:
            content = str(last_user_msg.get("content", "")).strip().lower()
            if len(content) < 10 or content in {"oi", "ok", "teste", "ola", "olá", "hello", "hi"}:
                metrics["simple_input_mode"] = True
                # Ignore history completely
                system_msgs = [m for m in processed_messages if m["role"] == "system"]
                processed_messages = system_msgs + [last_user_msg]

        # 3. Consolidate and truncate system prompt
        system_messages = [m for m in processed_messages if m["role"] == "system"]
        other_messages = [m for m in processed_messages if m["role"] != "system"]
        
        if system_messages:
            system_content = "\n\n".join([str(m["content"]) for m in system_messages])
            processed_messages = [{"role": "system", "content": system_content}] + other_messages
        else:
            processed_messages = other_messages

        # 4. Limit history count (max 4 previous messages if not in simple mode)
        if not metrics["simple_input_mode"] and len(processed_messages) > 1:
            system_msg = [m for m in processed_messages if m["role"] == "system"]
            non_system = [m for m in processed_messages if m["role"] != "system"]
            
            if len(non_system) > self.max_history_messages + 1: # +1 for the current user msg
                non_system = non_system[-(self.max_history_messages + 1):]
                metrics["truncated"] = True
            
            processed_messages = system_msg + non_system

        # 5. Limit by tokens (MAX_CONTEXT_TOKENS = 2048)
        while await _count(processed_messages) > self.max_context_tokens and len(processed_messages) > 2:
            if processed_messages[0]["role"] == "system":
                processed_messages.pop(1) # Remove oldest history
            else:
                processed_messages.pop(0)
            metrics["truncated"] = True

        final_count = await _count(processed_messages)
        metrics["final_tokens_estimate"] = final_count
        metrics["final_message_count"] = len(processed_messages)

        # 6. Use requested max_tokens or default
        final_max_tokens = requested_max_tokens
        if final_max_tokens is None or final_max_tokens <= 0:
            final_max_tokens = 256
        
        return processed_messages, final_max_tokens, metrics

def get_context_manager():
    return ContextManager()
