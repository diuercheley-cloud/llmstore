#!/usr/bin/env bash
set -e

echo "========================================"
echo " Validating Local AI Appliance Branding"
echo "========================================"

BRANDING_DOC="docs/LOCAL_AI_APPLIANCE_BRANDING.md"
BRANDING_JSON="config/branding.example.json"
README="README.md"
CAPABILITIES_API="control_plane/app/api/public.py"

# 1. Check if BRANDING_DOC exists
if [ ! -f "$BRANDING_DOC" ]; then
    echo "❌ ERROR: $BRANDING_DOC does not exist."
    exit 1
fi
echo "✅ $BRANDING_DOC exists."

# 2. Check branding example mentions Local AI Appliance
if ! grep -q "Local AI Appliance" "$BRANDING_JSON"; then
    echo "❌ ERROR: $BRANDING_JSON does not mention Local AI Appliance."
    exit 1
fi
echo "✅ $BRANDING_JSON mentions Local AI Appliance."

# 3. Check /capabilities or static file contains Local AI Appliance
if ! grep -q "Local AI Appliance" "control_plane/app/static/www/capabilities.html"; then
    echo "❌ ERROR: capabilities.html does not contain Local AI Appliance."
    exit 1
fi
echo "✅ capabilities.html mentions Local AI Appliance."

# 4. Check README mentions Local AI Appliance
if ! grep -q "Local AI Appliance" "$README"; then
    echo "❌ ERROR: $README does not mention Local AI Appliance."
    exit 1
fi
echo "✅ README mentions Local AI Appliance."

# 5. Check white-label local continues documented in BRANDING_DOC
if ! grep -q -i "White-Label" "$BRANDING_DOC"; then
    echo "❌ ERROR: $BRANDING_DOC missing mention of White-Label."
    exit 1
fi
echo "✅ White-label local documented in $BRANDING_DOC."

# 6. Check limitations PSP/PIX real appear
if ! grep -q -i "PSP.*real" "$BRANDING_DOC" || ! grep -q -i "PIX.*real" "$BRANDING_DOC"; then
    echo "❌ ERROR: PSP/PIX real limitations missing in $BRANDING_DOC."
    exit 1
fi
echo "✅ PSP/PIX limitations present."

echo "========================================"
echo "✅ All validations passed successfully!"
echo "========================================"
exit 0
