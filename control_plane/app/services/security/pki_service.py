import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.models.security_pki import CertificateInventory
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class PKIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.storage_path = Path(self.settings.pki_storage_path)
        self.ca_cert_path = self.storage_path / "ca.crt"
        self.ca_key_path = self.storage_path / "ca.key"
        self.crl_path = self.storage_path / "ca.crl"
        
        if self.settings.pki_enabled:
            self._ensure_storage()

    def _ensure_storage(self):
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def initialize_ca(self):
        if not self.settings.pki_enabled:
            logger.info("PKI is disabled, skipping CA initialization.")
            return

        if self.ca_cert_path.exists() and self.ca_key_path.exists():
            logger.info("CA already exists.")
            return

        logger.info("Initializing new local CA.")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"LLM Inference Stack"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"Local Root CA"),
        ])

        now = datetime.now(timezone.utc)
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            now
        ).not_valid_after(
            now + timedelta(days=self.settings.pki_ca_rotation_days)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True,
        ).sign(private_key, hashes.SHA256())

        # Write to disk
        self.ca_key_path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        self.ca_cert_path.write_bytes(
            cert.public_bytes(serialization.Encoding.PEM)
        )
        
        # Initialize an empty CRL
        await self._generate_crl([])

    def _get_ca_key_and_cert(self):
        if not self.ca_cert_path.exists() or not self.ca_key_path.exists():
            raise RuntimeError("CA not initialized")
            
        ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())
        ca_key = serialization.load_pem_private_key(
            self.ca_key_path.read_bytes(),
            password=None,
        )
        return ca_key, ca_cert

    async def issue_certificate(self, common_name: str) -> tuple[str, str]:
        if not self.settings.pki_enabled:
            return "", ""
            
        ca_key, ca_cert = self._get_ca_key_and_cert()

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        subject = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"LLM Inference Stack"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        now = datetime.now(timezone.utc)
        serial_number = x509.random_serial_number()
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            serial_number
        ).not_valid_before(
            now
        ).not_valid_after(
            now + timedelta(days=self.settings.pki_cert_rotation_days)
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True,
        ).sign(ca_key, hashes.SHA256())

        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode('utf-8')

        # Store in inventory
        db_cert = CertificateInventory(
            subject=common_name,
            issuer="Local Root CA",
            serial_number=str(serial_number),
            valid_from=now,
            valid_until=now + timedelta(days=self.settings.pki_cert_rotation_days),
            pem_cert=cert_pem
        )
        self.db.add(db_cert)
        await self.db.commit()

        return cert_pem, key_pem

    async def revoke_certificate(self, serial_number: str):
        if not self.settings.pki_enabled:
            return
            
        result = await self.db.execute(select(CertificateInventory).where(CertificateInventory.serial_number == serial_number))
        db_cert = result.scalars().first()
        if not db_cert:
            raise ValueError(f"Certificate with serial {serial_number} not found")

        if not db_cert.is_revoked:
            db_cert.is_revoked = True
            db_cert.revoked_at = utc_now()
            await self.db.commit()
            await self._update_crl()

    async def verify_certificate(self, cert_pem: str) -> bool:
        if not self.settings.pki_enabled:
            return True # Advisory/Simulated fallback if PKI disabled
            
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode('utf-8'))
            serial_str = str(cert.serial_number)
            
            # Check DB revocation status first
            result = await self.db.execute(select(CertificateInventory).where(CertificateInventory.serial_number == serial_str))
            db_cert = result.scalars().first()
            if db_cert and db_cert.is_revoked:
                logger.warning(f"Certificate {serial_str} is revoked in DB")
                return False
                
            # Verify signature against CA
            ca_key, ca_cert = self._get_ca_key_and_cert()
            
            from cryptography.hazmat.primitives.asymmetric import padding
            ca_cert.public_key().verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm,
            )
            
            # Check expiration
            now = datetime.now(timezone.utc)
            if now < cert.not_valid_before_utc or now > cert.not_valid_after_utc:
                logger.warning(f"Certificate {serial_str} is expired or not yet valid")
                return False

            # Optional: check CRL file logic here if needed (e.g. for external consumers)
            
            return True
        except Exception as e:
            logger.error(f"Certificate verification failed: {e}")
            return False

    async def _update_crl(self):
        result = await self.db.execute(select(CertificateInventory).where(CertificateInventory.is_revoked == True))
        revoked_certs = result.scalars().all()
        await self._generate_crl(revoked_certs)

    async def _generate_crl(self, revoked_certs: list[CertificateInventory]):
        ca_key, ca_cert = self._get_ca_key_and_cert()
        builder = x509.CertificateRevocationListBuilder()
        builder = builder.issuer_name(ca_cert.subject)
        now = datetime.now(timezone.utc)
        builder = builder.last_update(now)
        builder = builder.next_update(now + timedelta(days=1))
        
        for r_cert in revoked_certs:
            revoked_cert = x509.RevokedCertificateBuilder().serial_number(
                int(r_cert.serial_number)
            ).revocation_date(
                r_cert.revoked_at or now
            ).build()
            builder = builder.add_revoked_certificate(revoked_cert)

        crl = builder.sign(
            private_key=ca_key, algorithm=hashes.SHA256(),
        )
        self.crl_path.write_bytes(crl.public_bytes(serialization.Encoding.PEM))
