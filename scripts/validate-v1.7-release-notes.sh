#!/usr/bin/env bash
set -e

echo "========================================"
echo " Validating v1.7.0 Release Notes"
echo "========================================"

RELEASE_NOTES="docs/V1_7_RELEASE_NOTES.md"
CHANGELOG="CHANGELOG.md"
README="README.md"
SECRETS_SCRIPT="./scripts/check-secrets.sh"

# 1. Check if docs/V1_7_RELEASE_NOTES.md exists
if [ ! -f "$RELEASE_NOTES" ]; then
    echo "❌ ERROR: $RELEASE_NOTES does not exist."
    exit 1
fi
echo "✅ $RELEASE_NOTES exists."

# 2. Check CHANGELOG.md contains v1.7.0-local-ai-appliance
if ! grep -q "v1.7.0-local-ai-appliance" "$CHANGELOG"; then
    echo "❌ ERROR: $CHANGELOG does not contain 'v1.7.0-local-ai-appliance'."
    exit 1
fi
echo "✅ CHANGELOG.md contains v1.7.0 entry."

# 3. Check README.md points to release notes
if ! grep -q "docs/V1_7_RELEASE_NOTES.md" "$README"; then
    echo "❌ ERROR: $README does not point to $RELEASE_NOTES."
    exit 1
fi
echo "✅ README.md points to release notes."

# 4. Check limitations (PSP/PIX)
if ! grep -q -i "PSP.*fora do escopo\|fora do escopo.*PSP" "$RELEASE_NOTES"; then
    echo "❌ ERROR: $RELEASE_NOTES missing PSP out of scope limitation."
    exit 1
fi
if ! grep -q -i "PIX.*fora do escopo\|fora do escopo.*PIX" "$RELEASE_NOTES"; then
    echo "❌ ERROR: $RELEASE_NOTES missing PIX out of scope limitation."
    exit 1
fi
echo "✅ Limitations for PSP/PIX mentioned."

# 5. Check mentions of Local AI Appliance
if ! grep -q -i "Local AI Appliance" "$RELEASE_NOTES"; then
    echo "❌ ERROR: $RELEASE_NOTES missing 'Local AI Appliance'."
    exit 1
fi
echo "✅ Local AI Appliance mentioned."

# 6. Check mentions of all v1.6.x versions
for version in "v1.6.0" "v1.6.1" "v1.6.2" "v1.6.3" "v1.6.4" "v1.6.5" "v1.6.6" "v1.6.7"; do
    if ! grep -q "$version" "$RELEASE_NOTES"; then
        echo "❌ ERROR: $RELEASE_NOTES missing mention of $version."
        exit 1
    fi
done
echo "✅ All v1.6.0 to v1.6.7 versions mentioned."

# 7. Check for secrets using the existing project script if available, or basic grep
if [ -x "$SECRETS_SCRIPT" ]; then
    echo "Running secrets check script..."
    if ! "$SECRETS_SCRIPT" --path "$RELEASE_NOTES"; then
        echo "❌ ERROR: Secrets detected in $RELEASE_NOTES."
        exit 1
    fi
else
    # Fallback basic secret check
    if grep -q -E "sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}" "$RELEASE_NOTES"; then
        echo "❌ ERROR: Potential secrets detected in $RELEASE_NOTES."
        exit 1
    fi
fi
echo "✅ No secrets detected in $RELEASE_NOTES."

echo "========================================"
echo "✅ All validations passed successfully!"
echo "========================================"
exit 0
