#!/bin/bash
set -e

BASE_URL=${BASE_URL:-http://localhost:18080}
CLIENT_API_KEY=${CLIENT_API_KEY}

if [ -z "$CLIENT_API_KEY" ]; then
    echo "Error: CLIENT_API_KEY is not set"
    exit 1
fi

echo "--- Checking Health ---"
curl -fsS "$BASE_URL/health"
echo "PASS: Health OK"

echo "--- Checking Ready ---"
curl -fsS "$BASE_URL/ready"
echo "PASS: Ready OK"

echo "--- Uploading PDF ---"
# Create a dummy PDF for testing
echo "%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length 50 >> stream
BT /F1 12 Tf 100 700 Td (RAG Test Document - Invoice #1234) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000120 00000 n 
0000000210 00000 n 
trailer << /Size 5 /Root 1 0 R >>
startxref
310
%%EOF" > test-rag.pdf

UPLOAD_RESP=$(curl -s -X POST "$BASE_URL/v1/rag/files" \
  -H "Authorization: Bearer $CLIENT_API_KEY" \
  -F "file=@test-rag.pdf")

FILE_ID=$(echo $UPLOAD_RESP | grep -oP '"id":"\K[^"]+')
echo "Uploaded File ID: $FILE_ID"

echo "--- Waiting for processing ---"
MAX_RETRIES=30
COUNT=0
STATUS="uploaded"
while [ "$STATUS" != "ready" ] && [ "$COUNT" -lt "$MAX_RETRIES" ]; do
    sleep 2
    STATUS_RESP=$(curl -s -X GET "$BASE_URL/v1/rag/files/$FILE_ID" \
      -H "Authorization: Bearer $CLIENT_API_KEY")
    STATUS=$(echo $STATUS_RESP | grep -oP '"status":"\K[^"]+')
    echo "Current status: $STATUS"
    if [ "$STATUS" == "failed" ]; then
        echo "FAIL: Processing failed"
        exit 1
    fi
    COUNT=$((COUNT+1))
done

if [ "$STATUS" != "ready" ]; then
    echo "FAIL: Timeout waiting for ready status"
    exit 1
fi

echo "--- Querying RAG ---"
QUERY_RESP=$(curl -s -X POST "$BASE_URL/v1/rag/query" \
  -H "Authorization: Bearer $CLIENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"question\": \"Qual o numero do invoice no documento?\",
    \"top_k\": 5
  }")

ANSWER=$(echo $QUERY_RESP | grep -oP '"answer":"\K[^"]+')
echo "Answer: $ANSWER"

if [[ "$ANSWER" == *"1234"* ]]; then
    echo "PASS: Correct answer found"
else
    echo "FAIL: Answer does not contain expected info"
fi

echo "--- Cleanup ---"
curl -s -X DELETE "$BASE_URL/v1/rag/files/$FILE_ID" \
  -H "Authorization: Bearer $CLIENT_API_KEY"
rm test-rag.pdf

echo "ALL RAG TESTS PASSED"
