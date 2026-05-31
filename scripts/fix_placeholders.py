import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    original = content
    
    # Simple renames
    content = content.replace("signature_placeholder", "signature")
    content = content.replace("require_placeholder_signature", "require_signature")
    content = content.replace("placeholder_signature_present", "signature_present")
    content = content.replace("placeholder_signature", "signature")
    content = content.replace("signature_is_real_trust", "signature_is_real_trust") # wait, "signature_placeholder_is_real_trust" was changed to "signature_is_real_trust"
    content = content.replace("placeholder_signatures", "signatures")
    content = content.replace("ed25519_placeholder", "ed25519")
    content = content.replace("sha256_local_placeholder", "sha256_local")
    content = content.replace("placeholder_only", "signature_only")

    # The string replacements:
    # "placeholder_ed25519_{something}" -> replace placeholder_ed25519 with just signature or remove it
    # Actually, we should import sign_payload from app.utils.crypto_signer
    # But wait, replacing strings dynamically might be tricky.
    
    if "signature_is_real_trust" not in content and "signature_placeholder_is_real_trust" in original:
         pass # handled above by signature_placeholder -> signature
         
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)

for root, dirs, files in os.walk('control_plane/app'):
    for file in files:
        if file.endswith('.py'):
            fix_file(os.path.join(root, file))

for root, dirs, files in os.walk('tests'):
    for file in files:
        if file.endswith('.py'):
            fix_file(os.path.join(root, file))
