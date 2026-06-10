from unittest.mock import MagicMock, patch

import pytest

from scripts.llm_harness.tracing import OTEL_AVAILABLE, Tracer


def test_tracer_no_otel(monkeypatch):
    """Verify tracer works and does not fail when OTEL is disabled or unavailable."""
    monkeypatch.setenv("LLM_HARNESS_ENABLE_OTEL", "0")
    tracer = Tracer()
    assert tracer.otel_tracer is None
    
    # Starting and ending span should not crash
    span_id = tracer.start_span("test-span", attributes={"secret_key": "api_key=super-secret"})
    assert span_id in tracer.spans
    tracer.end_span(span_id, success=True)
    assert span_id not in tracer.spans

    # Context manager trace_span should work
    with tracer.trace_span("test-span-context", attributes={"password": "123"}):
        pass


def test_tracer_otel_secret_redaction(monkeypatch):
    """Verify that Tracer redacts secrets from attributes when OpenTelemetry is enabled."""
    if not OTEL_AVAILABLE:
        pytest.skip("opentelemetry is not installed in the environment")

    monkeypatch.setenv("LLM_HARNESS_ENABLE_OTEL", "1")
    
    # Mock OpenTelemetry's get_tracer to return a mock tracer
    mock_otel_tracer = MagicMock()
    mock_span = MagicMock()
    mock_otel_tracer.start_span.return_value = mock_span
    mock_otel_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

    with patch("opentelemetry.trace.get_tracer", return_value=mock_otel_tracer):
        tracer = Tracer()
        assert tracer.otel_tracer is not None

        # 1. Test start_span sanitizes attributes
        tracer.start_span("test", attributes={"api_key": "secret-token-value"})
        args, kwargs = mock_otel_tracer.start_span.call_args
        assert kwargs["attributes"]["api_key"] == "[REDACTED]"

        # 2. Test trace_span context manager sanitizes attributes
        with tracer.trace_span(
            "test-ctx", 
            attributes={"bearer_token": "bearer eyJ1c2VyIjoiYW50aWdyYXZpdHkifQ.eyJpYXQiOjE2MjIzNTQ4MDB9.xyz"}
        ):
            pass
        args, kwargs = mock_otel_tracer.start_as_current_span.call_args
        assert "[REDACTED]" in kwargs["attributes"]["bearer_token"] or "Bearer [REDACTED]" in kwargs["attributes"]["bearer_token"]


@pytest.mark.asyncio
async def test_coding_loop_span_calls(monkeypatch, temp_repo, fake_provider):
    """Verify that coding loop starts spans during execution (run, llm_call)."""
    monkeypatch.setenv("LLM_HARNESS_ENABLE_OTEL", "1")
    
    mock_otel_tracer = MagicMock()
    mock_span = MagicMock()
    mock_otel_tracer.start_span.return_value = mock_span
    mock_otel_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

    with patch("opentelemetry.trace.get_tracer", return_value=mock_otel_tracer):
        # Instantiate coding loop with a mock/fake provider
        from scripts.llm_harness.agent_client import AgentClient
        from scripts.llm_harness.coding_loop import CodingLoop
        
        client = AgentClient(agent_id="test-coder", provider="stub", transport=fake_provider)
        
        loop = CodingLoop(
            agent_client=client,
            workspace=temp_repo,
            use_docker=False,
            checkpoint_every_step=False
        )
        
        # Execute coding loop
        result = await loop.run("Fix a simple bug")
        
        # Verify spans: we expect at least 'run' and 'llm_call' (since LLM is called via StubProvider)
        assert result.success
        assert result.trace_id is not None
        
        # Check start_span or start_as_current_span calls on mock tracer
        span_names = [call[0][0] for call in mock_otel_tracer.start_span.call_args_list] + \
                     [call[0][0] for call in mock_otel_tracer.start_as_current_span.call_args_list]
        
        assert "run" in span_names
        assert "llm_call" in span_names
