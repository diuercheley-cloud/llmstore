import json

import pytest


def test_sse_parsing_logic():
    # Mocking the SSE stream
    stream_content = [
        b'data: {"choices": [{"delta": {"content": "O"}}]}\n',
        b'data: {"choices": [{"delta": {"content": "K"}}]}\n',
        b'data: [DONE]\n'
    ]
    
    chunks_received = 0
    has_done = False
    full_text = ""
    
    for line in stream_content:
        line = line.decode('utf-8').strip()
        if not line:
            continue
        
        if line.startswith('data:'):
            chunks_received += 1
            data_str = line[5:].strip()
            
            if data_str == '[DONE]':
                has_done = True
                break
            
            try:
                data = json.loads(data_str)
                content = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                full_text += content
            except json.JSONDecodeError:
                continue
                
    assert chunks_received == 3
    assert has_done is True
    assert full_text == "OK"

@pytest.mark.parametrize("stream_body,expected_ok", [
    ("data: {\"choices\": [{\"delta\": {\"content\": \"OK\"}}]}\ndata: [DONE]\n", True),
    ("data: some noise\n", True), # Be lenient as long as it starts with data: and we have at least one chunk
    ("no data here", False),
])
def test_sse_stream_ok_logic(stream_body, expected_ok):
    # Logic from production-readiness-local.sh
    has_sse_data = "data:" in stream_body
    is_sse_content_type = False # Assume False for this test
    stream_status = 200
    
    stream_ok = stream_status == 200 and (has_sse_data or is_sse_content_type)
    assert stream_ok == expected_ok
