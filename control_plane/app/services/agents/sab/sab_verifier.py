# Owner: agent-platform
import hashlib
import json

from .sab_manifest import AgentSABManifest


class SABVerifier:
    def verify(self, manifest: AgentSABManifest) -> tuple[bool, str]:
        # 1. Verify Checksum
        data_to_hash = manifest.model_dump(exclude={"checksums", "signature"})
        payload = json.dumps(data_to_hash, sort_keys=True).encode()
        actual_checksum = hashlib.sha256(payload).hexdigest()

        if actual_checksum != manifest.checksums.get("manifest"):
            return False, "Checksum mismatch: bundle might be tampered."

        # 2. Verify Signature (Mock)
        if manifest.signature:
            expected_sig = f"sig:{actual_checksum}:prod_key"
            if manifest.signature != expected_sig:
                return False, "Invalid signature: bundle origin untrusted."

        # 3. Sanity check for secrets in memory snapshot
        if manifest.memory_snapshot:
            for item in manifest.memory_snapshot:
                content = str(item.get("content", "")).lower()
                if any(k in content for k in ["sk-", "password", "secret"]):
                    return False, "Security violation: memory snapshot contains raw secrets."

        return True, "Bundle verified."
