#!/bin/bash
# scripts/test-streaming-concatenation.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:18080}"
API_KEY="${API_KEY:-sk-local-mU7fr1Yqna-jdwA624WTvGk40yj9abAa}"

echo "Testing streaming concatenation..."
curl -s -X POST "$BASE_URL/v1/chat/completions"   -H "Content-Type: application/json"   -H "Authorization: Bearer $API_KEY"   -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Conte uma piada longa."}],
    "stream": true,
    "temperature": 0.7
  }' | tee streaming_output.txt

echo -e "\n--------------------------------------------------------------------------------"
echo "Extracted Content:"
grep "data: {" streaming_output.txt | python3 -c "
import sys, json
full_content = ''
for line in sys.stdin:
    line = line.strip().replace('data: ', '')
    try:
        data = json.loads(line)
        delta = data['choices'][0]['delta']
        if 'content' in delta:
            full_content += delta['content']
    except:
        pass
print(full_content)
"
echo "--------------------------------------------------------------------------------"
rm streaming_output.txt
