import uuid
import logging
import hashlib
import json
import zipfile
import tarfile
import io
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Set

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.plugins.marketplace import (
    PluginMarketplaceEntry,
    PluginVersion,
    PluginInstall,
    PluginPermission,
    PluginTrustReport,
    PluginReview,
)
from app.models.security_pki import PluginRegistry
from app.models.security_event import SecurityEvent
from app.core.time import utc_now
from app.services.security.pki_service import PKIService
from app.core.config import get_settings
from app.contracts.plugin import ManifestV1
from app.contracts.plugin_types import PLUGIN_TYPES, ALLOWED_PERMISSIONS

logger = logging.getLogger(__name__)


PLUGIN_ALLOWLIST_KEY = "marketplace:allowlist"
PLUGIN_DENYLIST_KEY = "marketplace:denylist"


class PluginMarketplaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.pki_service = PKIService(db)
        self._data_dir = Path(self.settings.pki_storage_path).parent / "plugins"

    async def list_marketplace(self) -> List[PluginMarketplaceEntry]:
        result = await self.db.execute(
            select(PluginMarketplaceEntry).order_by(PluginMarketplaceEntry.name)
        )
        return list(result.scalars().all())

    async def list_versions(self, plugin_entry_id: uuid.UUID) -> List[PluginVersion]:
        result = await self.db.execute(
            select(PluginVersion)
            .where(PluginVersion.plugin_entry_id == plugin_entry_id)
            .order_by(PluginVersion.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_installs(self) -> List[PluginInstall]:
        result = await self.db.execute(
            select(PluginInstall).order_by(PluginInstall.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_plugin_entry(self, plugin_entry_id: uuid.UUID) -> Optional[PluginMarketplaceEntry]:
        result = await self.db.execute(
            select(PluginMarketplaceEntry).where(PluginMarketplaceEntry.id == plugin_entry_id)
        )
        return result.scalars().first()

    async def get_install(self, install_id: uuid.UUID) -> Optional[PluginInstall]:
        return await self.db.get(PluginInstall, install_id)

    async def install_plugin(self, plugin_file: bytes, filename: str) -> PluginInstall:
        manifest_data = self._extract_manifest(plugin_file, filename)
        if not manifest_data:
            raise ValueError("Plugin manifest (manifest.json) not found in archive")

        manifest = self._validate_manifest_v1(manifest_data)

        if not manifest_data.get("checksums"):
            sha256 = hashlib.sha256(plugin_file).hexdigest()
        else:
            archive_sha = manifest_data["checksums"].get("archive")
            if archive_sha:
                actual_sha = hashlib.sha256(plugin_file).hexdigest()
                if actual_sha != archive_sha:
                    raise ValueError(f"Archive checksum mismatch: expected {archive_sha}, got {actual_sha}")
                sha256 = actual_sha
            else:
                sha256 = hashlib.sha256(plugin_file).hexdigest()

        name = manifest.name
        plugin_type = manifest.plugin_type
        permissions = manifest.permissions
        version_str = manifest.version

        if name in self._get_denylist():
            raise ValueError(f"Plugin '{name}' is in the denylist and cannot be installed")

        allowlist = self._get_allowlist()
        if allowlist and name not in allowlist:
            raise ValueError(f"Plugin '{name}' is not in the allowlist")

        signature = manifest_data.get("signature")
        if self.settings.plugin_signature_required:
            if not signature:
                raise ValueError("Plugin signature is required but missing")
            await self._verify_signature(manifest_data, signature, plugin_file)

        query = select(PluginMarketplaceEntry).where(PluginMarketplaceEntry.name == name)
        result = await self.db.execute(query)
        entry = result.scalars().first()

        if not entry:
            entry = PluginMarketplaceEntry(
                name=name,
                description=manifest_data.get("description", ""),
                author=manifest_data.get("author", "Unknown"),
                license=manifest_data.get("license", "Proprietary"),
                plugin_type=plugin_type,
            )
            self.db.add(entry)
            await self.db.flush()

        version = PluginVersion(
            plugin_entry_id=entry.id,
            version=version_str,
            checksum_sha256=sha256,
            manifest_json=manifest_data,
            min_platform_version=manifest_data.get("minimum_platform_version", "1.0.0"),
        )
        self.db.add(version)
        await self.db.flush()

        plugin_dir = self._data_dir / entry.name / version_str
        plugin_dir.mkdir(parents=True, exist_ok=True)
        archive_path = plugin_dir / filename
        archive_path.write_bytes(plugin_file)
        install_path = str(plugin_dir)

        install = PluginInstall(
            plugin_entry_id=entry.id,
            current_version_id=version.id,
            install_path=install_path,
            status="installed",
            is_enabled=False,
        )
        self.db.add(install)

        for perm_name in permissions:
            perm = PluginPermission(
                plugin_install_id=install.id,
                permission_name=perm_name,
                granted=False,
            )
            self.db.add(perm)

        legacy_plugin = PluginRegistry(
            name=entry.name,
            version=version_str,
            entrypoint=manifest_data.get("entrypoint", "main.py"),
            permissions_json=json.dumps(permissions),
            sha256=sha256,
            is_active=False,
            signature=signature,
        )
        self.db.add(legacy_plugin)

        await self._log_security_event(
            "plugin_installed",
            f"Plugin '{name}' v{version_str} installed",
            {"name": name, "version": version_str, "plugin_type": plugin_type, "sha256": sha256},
        )

        await self.db.commit()
        await self.db.refresh(install)
        return install

    async def enable_plugin(self, install_id: uuid.UUID):
        install = await self.db.get(PluginInstall, install_id)
        if not install:
            raise ValueError("Plugin install not found")

        install.is_enabled = True
        install.status = "enabled"

        entry = await self.db.get(PluginMarketplaceEntry, install.plugin_entry_id)
        await self.db.execute(
            update(PluginRegistry)
            .where(PluginRegistry.name == entry.name)
            .values(is_active=True)
        )

        await self._log_security_event(
            "plugin_enabled",
            f"Plugin '{entry.name}' enabled",
            {"install_id": str(install_id), "name": entry.name},
        )

        await self.db.commit()

    async def disable_plugin(self, install_id: uuid.UUID):
        install = await self.db.get(PluginInstall, install_id)
        if not install:
            raise ValueError("Plugin install not found")

        install.is_enabled = False
        install.status = "disabled"

        entry = await self.db.get(PluginMarketplaceEntry, install.plugin_entry_id)
        await self.db.execute(
            update(PluginRegistry)
            .where(PluginRegistry.name == entry.name)
            .values(is_active=False)
        )

        await self._log_security_event(
            "plugin_disabled",
            f"Plugin '{entry.name}' disabled",
            {"install_id": str(install_id), "name": entry.name},
        )

        await self.db.commit()

    async def uninstall_plugin(self, install_id: uuid.UUID):
        install = await self.db.get(PluginInstall, install_id)
        if not install:
            raise ValueError("Plugin install not found")

        install.is_enabled = False
        install.status = "uninstalling"

        entry = await self.db.get(PluginMarketplaceEntry, install.plugin_entry_id)

        await self.db.execute(
            delete(PluginPermission).where(PluginPermission.plugin_install_id == install.id)
        )

        await self.db.execute(
            delete(PluginRegistry).where(PluginRegistry.name == entry.name)
        )

        install_path = Path(install.install_path)
        if install_path.exists():
            shutil.rmtree(install_path, ignore_errors=True)

        await self._log_security_event(
            "plugin_uninstalled",
            f"Plugin '{entry.name}' uninstalled",
            {"install_id": str(install_id), "name": entry.name, "path": install.install_path},
        )

        await self.db.delete(install)
        await self.db.commit()

    async def upgrade_plugin(
        self, install_id: uuid.UUID, plugin_file: bytes, filename: str
    ) -> PluginInstall:
        install = await self.db.get(PluginInstall, install_id)
        if not install:
            raise ValueError("Plugin install not found")

        manifest_data = self._extract_manifest(plugin_file, filename)
        if not manifest_data:
            raise ValueError("Plugin manifest not found in archive")

        manifest = self._validate_manifest_v1(manifest_data)
        entry = await self.db.get(PluginMarketplaceEntry, install.plugin_entry_id)

        if manifest.name != entry.name:
            raise ValueError(
                f"Plugin name mismatch: archive is '{manifest.name}', install is '{entry.name}'"
            )

        old_config = install.config_json.copy()

        new_sha256 = hashlib.sha256(plugin_file).hexdigest()

        version = PluginVersion(
            plugin_entry_id=entry.id,
            version=manifest.version,
            checksum_sha256=new_sha256,
            manifest_json=manifest_data,
            min_platform_version=manifest_data.get("minimum_platform_version", "1.0.0"),
        )
        self.db.add(version)
        await self.db.flush()

        plugin_dir = self._data_dir / entry.name / manifest.version
        plugin_dir.mkdir(parents=True, exist_ok=True)
        archive_path = plugin_dir / filename
        archive_path.write_bytes(plugin_file)

        install.current_version_id = version.id
        install.install_path = str(plugin_dir)
        install.config_json = old_config
        install.status = "installed"
        install.is_enabled = install.is_enabled

        await self.db.execute(
            delete(PluginPermission).where(PluginPermission.plugin_install_id == install.id)
        )
        for perm_name in manifest.permissions:
            perm = PluginPermission(
                plugin_install_id=install.id,
                permission_name=perm_name,
                granted=False,
            )
            self.db.add(perm)

        await self.db.execute(
            update(PluginRegistry)
            .where(PluginRegistry.name == entry.name)
            .values(version=manifest.version, sha256=new_sha256)
        )

        await self._log_security_event(
            "plugin_upgraded",
            f"Plugin '{entry.name}' upgraded to v{manifest.version}",
            {"install_id": str(install_id), "name": entry.name, "new_version": manifest.version},
        )

        await self.db.commit()
        await self.db.refresh(install)
        return install

    async def create_trust_report(
        self, version_id: uuid.UUID, *, trust_score: float = 1.0,
        vulnerabilities: int = 0, details: Optional[Dict] = None,
        is_signed: bool = False, signer: Optional[str] = None,
    ) -> PluginTrustReport:
        report = PluginTrustReport(
            plugin_version_id=version_id,
            trust_score=trust_score,
            vulnerabilities_found=vulnerabilities,
            report_details=details or {},
            is_signed=is_signed,
            signer_identity=signer,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_trust_report(self, install_id: uuid.UUID) -> Optional[PluginTrustReport]:
        install = await self.db.get(PluginInstall, install_id)
        if not install:
            return None

        result = await self.db.execute(
            select(PluginTrustReport)
            .where(PluginTrustReport.plugin_version_id == install.current_version_id)
            .order_by(PluginTrustReport.scanned_at.desc())
        )
        return result.scalars().first()

    async def add_review(
        self, plugin_entry_id: uuid.UUID, *, version: str,
        rating: int, review_text: Optional[str] = None,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> PluginReview:
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        entry = await self.db.get(PluginMarketplaceEntry, plugin_entry_id)
        if not entry:
            raise ValueError("Plugin entry not found")

        review = PluginReview(
            plugin_entry_id=plugin_entry_id,
            admin_user_id=admin_user_id,
            version=version,
            rating=rating,
            review_text=review_text,
        )
        self.db.add(review)

        result = await self.db.execute(
            select(PluginReview)
            .where(PluginReview.plugin_entry_id == plugin_entry_id)
        )
        all_reviews = result.scalars().all()
        if all_reviews:
            entry.avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews)
        else:
            entry.avg_rating = float(rating)

        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def list_reviews(self, plugin_entry_id: uuid.UUID) -> List[PluginReview]:
        result = await self.db.execute(
            select(PluginReview)
            .where(PluginReview.plugin_entry_id == plugin_entry_id)
            .order_by(PluginReview.created_at.desc())
        )
        return list(result.scalars().all())

    def _validate_manifest_v1(self, data: Dict) -> ManifestV1:
        return ManifestV1(**data)

    def _extract_manifest(self, plugin_file: bytes, filename: str) -> Optional[Dict]:
        if filename.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(plugin_file)) as z:
                if "manifest.json" in z.namelist():
                    return json.loads(z.read("manifest.json").decode("utf-8"))
        elif filename.endswith(".tar.gz") or filename.endswith(".tgz"):
            with tarfile.open(fileobj=io.BytesIO(plugin_file), mode="r:gz") as t:
                try:
                    m = t.extractfile("manifest.json")
                    if m:
                        return json.loads(m.read().decode("utf-8"))
                except KeyError:
                    pass
        elif filename.endswith(".tar"):
            with tarfile.open(fileobj=io.BytesIO(plugin_file), mode="r:") as t:
                try:
                    m = t.extractfile("manifest.json")
                    if m:
                        return json.loads(m.read().decode("utf-8"))
                except KeyError:
                    pass
        return None

    async def _verify_signature(self, manifest: Dict, signature: str, plugin_binary: bytes):
        cert_chain = manifest.get("certificate_chain", "")
        if self.settings.pki_enabled and cert_chain:
            is_valid = await self.pki_service.verify_certificate(cert_chain)
            if not is_valid:
                await self._log_security_event(
                    "plugin_signature_verify_failed",
                    f"Plugin '{manifest.get('name')}' signature verification failed",
                    {"name": manifest.get("name"), "reason": "invalid_certificate_chain"},
                )
                raise ValueError("Plugin certificate chain verification failed")
        elif self.settings.attestation_mode == "enforcing":
            raise ValueError("Plugin signature is required but no certificate chain provided")

    def _get_denylist(self) -> Set[str]:
        return set()

    def _get_allowlist(self) -> Set[str]:
        return set()

    async def _log_security_event(self, event_type: str, title: str, detail: dict):
        event = SecurityEvent(
            event_type=event_type,
            title=title,
            detail_json=json.dumps(detail),
            severity="high",
        )
        self.db.add(event)
