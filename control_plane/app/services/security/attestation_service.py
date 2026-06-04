import base64
import hashlib
import json
import logging
from typing import Dict

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.security_pki import AttestationReport as AttestationReportDB
from app.models.security_pki import PluginRegistry
from app.services.security.hardware_trust import get_hardware_trust_provider
from app.services.security.pki_service import PKIService
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.contracts.attestation import (
    AttestationCapabilities,
    AttestationContract,
    AttestationReport,
)


class NodeAttestationService(AttestationContract):
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.hardware_provider = get_hardware_trust_provider()
        self.pki_service = PKIService(db)

    def capabilities(self) -> AttestationCapabilities:
        return AttestationCapabilities(
            hardware_trust=self.settings.attestation_mode == "enforcing",
            pki_integration=self.settings.pki_enabled,
            enforcement_mode=self.settings.attestation_mode == "enforcing"
        )

    def validate_contract(self) -> bool:
        return True

    def _get_config_hash(self) -> str:
        # Sanitize config to avoid hashing secrets
        config_dict = self.settings.model_dump()
        sanitized = {k: v for k, v in config_dict.items() if "secret" not in k.lower() and "key" not in k.lower()}
        config_str = json.dumps(sanitized, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def _get_binary_hash(self) -> str:
        # Simplistic hash of main entrypoint as placeholder for binary/container digest
        try:
            with open("app/main.py", "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return hashlib.sha256(b"unknown_binary").hexdigest()

    async def _get_plugin_checksums(self) -> Dict[str, str]:
        result = await self.db.execute(select(PluginRegistry).where(PluginRegistry.is_active == True))
        plugins = result.scalars().all()
        return {p.name: p.sha256 for p in plugins}

    def _get_migrations(self) -> str:
        # Placeholder for alembic migrations
        return "head"

    async def generate_report(self) -> AttestationReport:
        plugin_checksums = await self._get_plugin_checksums()
        
        measurements = {
            "binary_hash": self._get_binary_hash(),
            "config_hash": self._get_config_hash(),
            "code_version": self.settings.project_version,
            "migrations": self._get_migrations(),
            "plugins": plugin_checksums,
            "hardware_trust": self.hardware_provider.get_measurements(),
        }
        
        policy_result = "passed"
        if self.settings.attestation_mode == "enforcing":
            # If enforcing, check hardware trust
            if measurements["hardware_trust"].get("status") not in ["mock_trusted", "file_trusted", "trusted"]:
                policy_result = "failed"
                
        # Generate signature
        cert_pem = ""
        key_pem = ""
        signature_b64 = ""
        if self.settings.pki_enabled:
            # Issue ephemeral or node cert to sign
            try:
                cert_pem, key_pem = await self.pki_service.issue_certificate("node-attestation")
                from cryptography.hazmat.primitives import serialization
                private_key = serialization.load_pem_private_key(key_pem.encode(), password=None)
                
                payload = json.dumps(measurements, sort_keys=True).encode()
                signature = private_key.sign(
                    payload,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                signature_b64 = base64.b64encode(signature).decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to sign attestation report: {e}")
                
        # Store in DB
        db_report = AttestationReportDB(
            measurements_json=json.dumps(measurements),
            policy_result=policy_result,
            signature=signature_b64,
            certificate_chain=cert_pem
        )
        self.db.add(db_report)
        await self.db.commit()
        
        return AttestationReport(
            subject="node-attestation",
            timestamp=utc_now().isoformat(),
            measurements=measurements,
            policy_result=policy_result,
            signature=signature_b64,
            certificate_chain=cert_pem
        )

    async def verify_report(self, report: AttestationReport) -> bool:
        if self.settings.attestation_mode == "advisory":
            logger.warning("Attestation is in advisory mode, accepting report.")
            return True
            
        policy_result = report.policy_result
        if policy_result != "passed":
            logger.warning("Attestation report policy check failed.")
            from app.core.metrics import record_attestation_failure
            record_attestation_failure(node_id="unknown", reason="policy_check_failed")
            return False
            
        if self.settings.pki_enabled:
            cert_chain = report.certificate_chain
            signature_b64 = report.signature
            measurements = report.measurements
            
            if not cert_chain or not signature_b64:
                return False
                
            is_valid_cert = await self.pki_service.verify_certificate(cert_chain)
            if not is_valid_cert:
                return False
                
            try:
                from cryptography import x509
                cert = x509.load_pem_x509_certificate(cert_chain.encode())
                public_key = cert.public_key()
                
                payload = json.dumps(measurements, sort_keys=True).encode()
                public_key.verify(
                    base64.b64decode(signature_b64),
                    payload,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                return True
            except Exception as e:
                logger.error(f"Failed to verify attestation signature: {e}")
                return False
        
        return True
