from app.services.tts_readiness import assess_tts_probe, build_tts_probe_skip


def test_tts_readiness_disabled_is_optional_skip():
    result = build_tts_probe_skip("TTS desabilitado via TTS_ENABLED=false.")

    assert result.status == "skip"
    assert result.optional is True
    assert "TTS_ENABLED=false" in result.details


def test_tts_readiness_assessment_uses_specific_401_remediation():
    result = assess_tts_probe(
        tts_enabled=True,
        http_status=401,
        headers={"Content-Type": "application/json"},
        body=b'{"detail":"invalid api key"}',
        usage_recorded=False,
        client_detail="client=tts-readiness key=sk-123...[redacted]",
    )

    assert result.status == "fail"
    assert "Bearer inválido" in result.remediation
    assert "nova API key" in result.remediation
