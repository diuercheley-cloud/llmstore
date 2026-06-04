from app.core.config import get_settings
from app.services.context_manager import ContextManager

settings = get_settings()

def test_context_manager_keeps_last_user_message():
    cm = ContextManager()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "This is a long message to avoid simple mode."},
        {"role": "assistant", "content": "This is another long message to avoid simple mode."},
        {"role": "user", "content": "What is 2+2? Tell me more please."}
    ]
    # Limit to 1 history message (non-system). 
    cm.max_history_messages = 1 
    
    processed, _, metrics = cm.manage(messages)
    
    # sys + assistant + user (last)
    assert len(processed) == 3
    assert processed[0]["role"] == "system"
    assert processed[-1]["content"] == "What is 2+2? Tell me more please."
    assert metrics["truncated"] is True

def test_context_manager_limits_history():
    cm = ContextManager()
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "Long message 1..."},
        {"role": "assistant", "content": "Long message 2..."},
        {"role": "user", "content": "Long message 3..."},
        {"role": "assistant", "content": "Long message 4..."},
        {"role": "user", "content": "Long message 5..."}
    ]
    cm.max_history_messages = 2 # Max 2 history messages + current user
    
    processed, _, _ = cm.manage(messages)
    
    # sys + 3, 4, 5
    assert len(processed) == 4
    assert processed[1]["content"] == "Long message 3..."
    assert processed[2]["content"] == "Long message 4..."
    assert processed[3]["content"] == "Long message 5..."

def test_context_manager_simple_input_mode():
    cm = ContextManager()
    messages = [
        {"role": "system", "content": "You are a coding expert."},
        {"role": "user", "content": "Explain React."},
        {"role": "assistant", "content": "React is a UI library."},
        {"role": "user", "content": "oi"}
    ]
    
    processed, _, metrics = cm.manage(messages)
    
    assert metrics["simple_input_mode"] is True
    assert len(processed) == 2
    assert processed[0]["role"] == "system"
    assert processed[1]["content"] == "oi"

def test_max_tokens_is_capped_force_512():
    cm = ContextManager()
    
    _, capped_tokens, metrics = cm.manage([{"role": "user", "content": "test message"}], requested_max_tokens=32000)
    
    assert capped_tokens == 512
    assert metrics["truncated"] is True

def test_max_tokens_default_256():
    cm = ContextManager()
    
    _, capped_tokens, _ = cm.manage([{"role": "user", "content": "test message"}], requested_max_tokens=None)
    
    assert capped_tokens == 256

def test_system_prompt_truncation_stricter():
    cm = ContextManager()
    cm.max_system_chars = 1000
    long_sys = "s" * 1500
    messages = [
        {"role": "system", "content": long_sys},
        {"role": "user", "content": "This is a long message to avoid simple mode."}
    ]
    
    processed, _, metrics = cm.manage(messages)
    
    assert len(processed[0]["content"]) == 1000
    assert metrics["truncated"] is True

def test_empty_and_duplicate_short_messages():
    cm = ContextManager()
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": ""},
        {"role": "user", "content": "x"},
        {"role": "assistant", "content": "x"}, # duplicate short content
        {"role": "user", "content": "how are you today? Tell me everything."}
    ]
    
    processed, _, metrics = cm.manage(messages)
    
    # sys + x + how are you? (duplicate x removed)
    assert len(processed) == 3
    assert processed[1]["content"] == "x"
    assert "how are you" in processed[2]["content"]

def test_context_manager_token_limit():
    cm = ContextManager()
    # Mocking tokens: each word is roughly 1 token + 4.
    # "word" -> 1 token + 4 = 5.
    cm.max_context_tokens = 15 # Allow system (5) + last (5) + maybe one more (5) = 15
    
    messages = [
        {"role": "system", "content": "system prompt"}, # 5
        {"role": "user", "content": "one long message"},     # 5
        {"role": "assistant", "content": "two long message"}, # 5
        {"role": "user", "content": "three long message"},   # 5
        {"role": "assistant", "content": "four long message"}, # 5
        {"role": "user", "content": "five long message"}      # 5
    ]
    
    processed, _, metrics = cm.manage(messages)
    
    # Should keep system and last, and as many as fits.
    # system (5) + five (5) = 10.
    # plus four (5) = 15.
    # plus three (5) = 20 (TOO MUCH)
    assert len(processed) <= 3 
    assert processed[0]["role"] == "system"
    assert processed[-1]["content"] == "five long message"
    assert metrics["truncated"] is True
