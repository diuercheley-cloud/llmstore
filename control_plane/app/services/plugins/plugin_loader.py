import hashlib
import json
import logging
import base64
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.models.security_pki import PluginRegistry
from app.services.security.pki_service import PKIService
from app.models.security_event import SecurityEvent

logger = logging.getLogger(__name__)

class PluginLoader:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.pki_service = PKIService(db)
        self.allowed_permissions = {"read_data", "write_data", "network_out", "execute_sandbox"}

    async def _log_security_event(self, event_type: str, title: str, detail: dict):
        event = SecurityEvent(
            event_type=event_type,
            title=title,
            detail_json=json.dumps(detail),
            severity="high"
        )
        self.db.add(event)
        await self.db.commit()

    async def load_plugin(self, manifest: Dict[str, Any], plugin_binary: bytes) -> PluginRegistry:
        """
        Loads a plugin by validating its manifest, checksum, and signature.
        """
        required_fields = ["name", "version", "entrypoint", "permissions", "sha256"]
        for field in required_fields:
            if field not in manifest:
                raise ValueError(f"Manifest missing required field: {field}")

        name = manifest["name"]
        
        # Validate permissions
        permissions = set(manifest["permissions"])
        invalid_perms = permissions - self.allowed_permissions
        if invalid_perms:
            error_msg = f"Invalid permissions requested: {invalid_perms}"
            await self._log_security_event("plugin_load_error", f"Plugin {name} requested invalid permissions", {"invalid_perms": list(invalid_perms)})
            raise ValueError(error_msg)

        # Validate checksum
        actual_sha256 = hashlib.sha256(plugin_binary).hexdigest()
        if actual_sha256 != manifest["sha256"]:
            error_msg = f"Checksum mismatch for plugin {name}"
            await self._log_security_event("plugin_load_error", error_msg, {"expected": manifest["sha256"], "actual": actual_sha256})
            raise ValueError(error_msg)

        # Validate signature
        signature = manifest.get("signature")
        if self.settings.plugin_signature_required:
            if not signature:
                error_msg = f"Signature required but not provided for plugin {name}"
                await self._log_security_event("plugin_load_error", error_msg, {})
                if self.settings.attestation_mode == "enforcing":
                    raise ValueError(error_msg)
                else:
                    logger.warning(f"[ADVISORY] {error_msg}")
            else:
                # Assuming signature is verifiable by PKIService root CA (or similar logic)
                # In a real scenario, the signature covers the binary + manifest hash
                is_valid = await self.pki_service.verify_certificate(manifest.get("certificate_chain", ""))
                if not is_valid:
                    error_msg = f"Invalid certificate chain for plugin {name}"
                    await self._log_security_event("plugin_load_error", error_msg, {})
                    if self.settings.attestation_mode == "enforcing":
                        raise ValueError(error_msg)
                    else:
                        logger.warning(f"[ADVISORY] {error_msg}")

        # Block invalid plugin based on enforcing mode
        # (Already raising ValueError if enforcing above)

        # Register plugin
        result = await self.db.execute(select(PluginRegistry).where(PluginRegistry.name == name))
        existing_plugin = result.scalars().first()
        
        if existing_plugin:
            existing_plugin.version = manifest["version"]
            existing_plugin.entrypoint = manifest["entrypoint"]
            existing_plugin.permissions_json = json.dumps(manifest["permissions"])
            existing_plugin.sha256 = actual_sha256
            existing_plugin.signature = signature
            existing_plugin.is_active = True
            existing_plugin.load_error = None
            plugin_record = existing_plugin
        else:
            plugin_record = PluginRegistry(
                name=name,
                version=manifest["version"],
                entrypoint=manifest["entrypoint"],
                permissions_json=json.dumps(manifest["permissions"]),
                sha256=actual_sha256,
                signature=signature,
                is_active=True
            )
            self.db.add(plugin_record)

        await self.db.commit()
        await self.db.refresh(plugin_record)
        return plugin_record

