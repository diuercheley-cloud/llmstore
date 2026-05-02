import pytest
from app.utils.anti_loop import detect_repetition, truncate_at_repetition


def test_detect_repetition_blocks():
    text = "Goal: something\nProgress: 10%\nGoal: something else\nProgress: 20%\nGoal: loop\nProgress: loop"
    assert detect_repetition(text, max_repeats=2) is True


def test_detect_repetition_long_lines():
    long_line = "This is a very long line that should be detected if it repeats multiple times in the response."
    text = f"{long_line}\n{long_line}\n{long_line}"
    assert detect_repetition(text, max_repeats=2) is True


def test_no_repetition():
    text = "Goal: once\nProgress: once\nNext Steps: once"
    assert detect_repetition(text, max_repeats=2) is False


def test_truncate_at_repetition():
    text = "Header\nGoal: 1\nGoal: 2\nGoal: 3\nFooter"
    truncated = truncate_at_repetition(text, max_repeats=2)
    assert "Goal: 3" not in truncated
    assert "[Truncated due to repetition loop]" in truncated
    assert "Goal: 1" in truncated
    assert "Goal: 2" in truncated


def test_detect_ngram_repetition_gemma_loop():
    text = "I am an AI assistant. I am an AI assistant. I am an AI assistant. I am an AI assistant."
    assert detect_repetition(text) is True


def test_detect_ngram_repetition_short_loop():
    text = "Yes yes yes yes yes yes yes yes yes yes yes yes yes yes yes yes"
    assert detect_repetition(text) is True


def test_detect_short_phrase_repetition():
    text = "Let me think about this.\nLet me think about this.\nLet me think about this."
    assert detect_repetition(text, max_repeats=2) is True


def test_no_repetition_normal_text():
    text = "Hello! I am an AI assistant. How can I help you today? Let me know what you need."
    assert detect_repetition(text) is False


def test_truncate_at_ngram_repetition():
    text = "First part of response. I am an AI assistant. I am an AI assistant. I am an AI assistant. I am an AI assistant."
    truncated = truncate_at_repetition(text)
    assert "[Truncated due to repetition loop]" in truncated
    assert "First part" in truncated


def test_truncate_at_short_phrase_repetition():
    text = "Introduction\nLet me think about this\nLet me think about this\nLet me think about this"
    truncated = truncate_at_repetition(text, max_repeats=2)
    assert "[Truncated due to repetition loop]" in truncated
    assert "Introduction" in truncated
