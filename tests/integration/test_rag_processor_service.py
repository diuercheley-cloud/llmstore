from app.services.rag_processor import estimate_tokens_from_text


def test_token_estimation_basic():
    text = "Hello world"
    tokens = estimate_tokens_from_text(text)
    assert tokens > 0
    
def test_token_estimation_long():
    text = "This is a much longer text that should result in more tokens than the previous one."
    tokens_short = estimate_tokens_from_text("Hello world")
    tokens_long = estimate_tokens_from_text(text)
    assert tokens_long > tokens_short
