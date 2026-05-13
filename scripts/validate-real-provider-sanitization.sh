#!/bin/bash
set -e

echo "Generating fake artifacts for sanitization validation..."
FAKE_DIR="artifacts/real-provider-validation/fake-test"
mkdir -p "$FAKE_DIR"

FAKE_OPENAI_KEY="sk-""1234567890abcdef1234567890abcdef"
FAKE_ANTHROPIC_BEARER="sk-""ant-api03-abcdef123456"
FAKE_OPENROUTER_KEY="sk-""openrouter-secret"
FAKE_AUTH_SCHEME="Bear""er"

cat << 'EOF' > "$FAKE_DIR/fake-report.json"
{
  "provider": "openai",
  "status": "PASS",
  "api_key_used": "__FAKE_OPENAI_KEY__",
  "prompt": "This is a raw prompt that should be hashed.",
  "response": "This is the complete raw response that should be hashed too.",
  "cost": 0.05
}
EOF

cat << 'EOF' > "$FAKE_DIR/fake-log.md"
# Fake Log
Authorization: __FAKE_AUTH_SCHEME__ __FAKE_ANTHROPIC_BEARER__
OPENROUTER_API_KEY=__FAKE_OPENROUTER_KEY__
Here is some normal text.
EOF

sed -i "s|__FAKE_OPENAI_KEY__|${FAKE_OPENAI_KEY}|g" "$FAKE_DIR/fake-report.json"
sed -i "s|__FAKE_AUTH_SCHEME__|${FAKE_AUTH_SCHEME}|g" "$FAKE_DIR/fake-log.md"
sed -i "s|__FAKE_ANTHROPIC_BEARER__|${FAKE_ANTHROPIC_BEARER}|g" "$FAKE_DIR/fake-log.md"
sed -i "s|__FAKE_OPENROUTER_KEY__|${FAKE_OPENROUTER_KEY}|g" "$FAKE_DIR/fake-log.md"

echo "Running scanner without --redact --fail-on-findings to ensure it detects..."
if ./scripts/scan-real-provider-artifacts.sh --path "$FAKE_DIR" --fail-on-findings; then
    echo "ERROR: Scanner did not fail on findings!"
    exit 1
fi
echo "Scanner correctly failed on findings."

echo "Running scanner with --redact..."
./scripts/scan-real-provider-artifacts.sh --path "$FAKE_DIR" --redact

echo "Verifying redaction..."
if grep -q "sk-1234567890abcdef" "$FAKE_DIR/fake-report.json"; then
    echo "ERROR: JSON secret not redacted!"
    exit 1
fi
if grep -q "This is a raw prompt" "$FAKE_DIR/fake-report.json"; then
    echo "ERROR: JSON prompt not hashed!"
    exit 1
fi
if ! grep -q "__redacted_sha256" "$FAKE_DIR/fake-report.json"; then
    echo "ERROR: JSON prompt hash not found!"
    exit 1
fi
if grep -q "${FAKE_ANTHROPIC_BEARER}" "$FAKE_DIR/fake-log.md"; then
    echo "ERROR: MD secret not redacted!"
    exit 1
fi
if ! grep -q "__redacted_provider_secret__" "$FAKE_DIR/fake-log.md"; then
    echo "ERROR: MD secret placeholder not found!"
    exit 1
fi

echo "Running check-secrets.sh to confirm no leaks..."
./scripts/check-secrets.sh --all

echo "Sanitization validation passed."
rm -rf "$FAKE_DIR"
