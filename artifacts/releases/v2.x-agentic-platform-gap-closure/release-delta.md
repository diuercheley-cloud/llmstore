# Release Delta

Files included in the release delta:

- config/feature-flags.yaml (Explicitly requested release file)
- config/platform-freeze-rules.json (Explicitly requested release file)
- control_plane/app/core/config.py (Explicitly requested release file)
- control_plane/app/api/agent_a2a.py (Matches release keyword: a2a)
- control_plane/app/services/agents/a2a/a2a_client.py (Matches release keyword: a2a)
- control_plane/app/services/agents/a2a/a2a_messages.py (Matches release keyword: a2a)
- control_plane/app/services/agents/a2a/a2a_registry.py (Matches release keyword: a2a)
- control_plane/app/services/agents/a2a/a2a_security.py (Matches release keyword: a2a)
- control_plane/app/services/agents/a2a/a2a_server.py (Matches release keyword: a2a)
- control_plane/app/services/agents/streaming/run_event_stream.py (Matches release keyword: streaming)
- control_plane/app/services/agents/streaming/stream_auth.py (Matches release keyword: streaming)
- control_plane/app/services/agents/streaming/websocket_manager.py (Matches release keyword: streaming)
- docs/agents/a2a-protocol.md (Matches release keyword: a2a)
- docs/api/agent-websocket-streaming.md (Matches release keyword: streaming)
- docs/releases/V2_X_AGENTIC_PLATFORM_GAP_CLOSURE.md (Explicitly requested release file)
- tests/e2e/test_agent_a2a_protocol.py (Matches release keyword: a2a)
- tests/e2e/test_agent_executor_real_flow.py (Matches release keyword: e2e/test_agent_executor)
- tests/e2e/test_agent_websocket_streaming.py (Matches release keyword: streaming)
- tests/test_agent_cancellation.py (Explicitly requested release file)
- tests/test_connector_mock_execution.py (Explicitly requested release file)
