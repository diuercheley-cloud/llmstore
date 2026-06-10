# P0 Security Rotation: Sensitive Key Remediation

## Context
A private key (`control_plane/.local_ed25519_key`) was identified in the repository history. This poses a severe security risk. It has been removed from the repository tracking, and `.gitignore` has been updated to prevent future occurrences.

## Action Required: Immediate Rotation
The compromised key **must be considered public**. You must rotate this key immediately.

### Steps to Rotate
1. **Invalidate old key**: Revoke the access associated with the old `.local_ed25519_key` in all systems it authenticated (e.g., control plane access, CI/CD, remote servers).
2. **Generate new key**: Generate a new, secure ED25519 key on your local machine:
   ```bash
   ssh-keygen -t ed25519 -f <path_to_new_key> -C "new-key-rotation"
   ```
3. **Update configurations**: Replace any references to the old file with the new key path. Ensure the new file is in a secure, non-versioned location.
4. **Update Authorized Systems**: Upload the new public key (`.pub`) to all required systems.

## Validation
To verify the key is no longer tracked:
1. Run `git ls-files | grep -E '(\.env$|\.local_ed25519_key|\.pem$|\.key$|\.sqlite|\.db$)'`. This should return no output.
2. Ensure new keys are not added by following the updated `.gitignore` patterns.
