"""
Owner: agent-platform
Status: beta
"""
import base64
import hashlib
import logging
import secrets
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agent_tool_execution import AgentToolCredential, AgentToolCredentialGrant
from app.services.security.local_aead import AESGCM

logger = logging.getLogger(__name__)


def mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if secret.startswith("sk-"):
        return f"sk-...{secret[-4:]}" if len(secret) > 7 else "sk-..."
    if len(secret) <= 6:
        return "****"
    return f"{secret[:3]}...{secret[-3:]}"


def _get_aesgcm() -> AESGCM:
    settings = get_settings()
    master_key = hashlib.sha256(settings.commercial_tenant_encryption_master_key.encode("utf-8")).digest()
    return AESGCM(master_key)


def encrypt_secret(raw_secret: str) -> str:
    aesgcm = _get_aesgcm()
    nonce = secrets.token_bytes(12)
    encrypted_bytes = aesgcm.encrypt(nonce, raw_secret.encode("utf-8"), None)
    return base64.b64encode(nonce + encrypted_bytes).decode("utf-8")


def decrypt_secret(encrypted_secret: str) -> str:
    aesgcm = _get_aesgcm()
    data = base64.b64decode(encrypted_secret)
    nonce = data[:12]
    ciphertext = data[12:]
    decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return decrypted_bytes.decode("utf-8")


async def register_credential(
    db: AsyncSession,
    tenant_id: str,
    name: str,
    credential_type: str,
    raw_secret: str,
    expires_at: Optional[datetime] = None,
) -> AgentToolCredential:
    encrypted = encrypt_secret(raw_secret)
    masked = mask_secret(raw_secret)

    credential = AgentToolCredential(
        tenant_id=tenant_id,
        name=name,
        credential_type=credential_type,
        encrypted_secret=encrypted,
        secret_masked=masked,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(credential)
    await db.flush()
    return credential


async def grant_credential(
    db: AsyncSession,
    tenant_id: str,
    credential_id: Any,
    agent_tool_id: Any,
    agent_id: Optional[Any] = None,
    expires_at: Optional[datetime] = None,
) -> AgentToolCredentialGrant:
    grant = AgentToolCredentialGrant(
        credential_id=credential_id,
        agent_id=agent_id,
        agent_tool_id=agent_tool_id,
        tenant_id=tenant_id,
        expires_at=expires_at,
    )
    db.add(grant)
    await db.flush()
    return grant


async def revoke_credential(
    db: AsyncSession,
    tenant_id: str,
    credential_id: Any,
) -> bool:
    stmt = select(AgentToolCredential).where(
        AgentToolCredential.id == credential_id,
        AgentToolCredential.tenant_id == tenant_id
    )
    res = await db.execute(stmt)
    cred = res.scalar_one_or_none()
    if not cred:
        return False
    cred.revoked = True
    await db.flush()
    return True


async def resolve_credential(
    db: AsyncSession,
    tenant_id: str,
    agent_tool_id: Any,
    agent_id: Optional[Any] = None,
) -> Optional[str]:
    """Resolves appropriate active credential grant and returns decrypted raw secret.
    
    If delegation feature flag is disabled, returns None.
    """
    settings = get_settings()
    if not settings.agent_tool_credential_delegation_enabled:
        logger.info("Credential delegation is disabled by feature flag.")
        return None

    now = utc_now()
    # Query grants for this tool and tenant (and optionally agent if specific)
    stmt = select(AgentToolCredentialGrant).where(
        AgentToolCredentialGrant.tenant_id == tenant_id,
        AgentToolCredentialGrant.agent_tool_id == agent_tool_id
    )
    if agent_id:
        # Match either agent specific grant or general tool grant
        stmt = stmt.where((AgentToolCredentialGrant.agent_id == agent_id) | (AgentToolCredentialGrant.agent_id == None))
    else:
        stmt = stmt.where(AgentToolCredentialGrant.agent_id == None)

    res = await db.execute(stmt)
    grants = res.scalars().all()

    for grant in grants:
        if grant.expires_at and grant.expires_at < now:
            continue
        
        # Load credential
        cred_stmt = select(AgentToolCredential).where(
            AgentToolCredential.id == grant.credential_id,
            AgentToolCredential.tenant_id == tenant_id,
            AgentToolCredential.revoked == False
        )
        cred_res = await db.execute(cred_stmt)
        cred = cred_res.scalar_one_or_none()
        if not cred:
            continue
        
        if cred.expires_at and cred.expires_at < now:
            continue
        
        # Found valid unexpired credential
        try:
            return decrypt_secret(cred.encrypted_secret)
        except Exception as e:
            logger.error(f"Failed to decrypt credential {cred.id}: {e}")
            continue

    return None
