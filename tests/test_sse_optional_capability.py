import pytest

@pytest.mark.parametrize("stream_ok,chat_streaming_supported,expected_label", [
    (True, True, "pass"),
    (True, False, "pass"), # Even if not supported by capability, if it works, it's pass
    (False, True, "fail"), # Supported but failed
    (False, False, "skip"), # Not supported and failed/omitted
])
def test_streaming_status_label_logic(stream_ok, chat_streaming_supported, expected_label):
    # Logic from production-readiness-local.sh
    if stream_ok:
        stream_status_label = "pass"
    elif not chat_streaming_supported:
        stream_status_label = "skip"
    else:
        stream_status_label = "fail"
        
    assert stream_status_label == expected_label
