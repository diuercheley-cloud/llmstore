import pytest
from app.services.backup.contracts import (
    CryptoProvider, 
    ArchiveProvider, 
    BackupManifestProvider,
    RestorePlannerProvider,
    StagingProvider,
    PromotionProvider,
    RollbackProvider,
    AuditProvider
)
from app.services.backup.crypto import BackupCryptoService
from app.services.backup.archive import ArchiveService
from app.services.backup.manifest import ManifestService
from app.services.backup.planner import RestorePlanner
from app.services.backup.staging import RestoreStagingService as StagingLogic
from app.services.backup.promotion import RestorePromotionService
from app.services.backup.rollback import RestoreRollbackService
from app.services.backup.audit import BackupAuditEmitter

def test_crypto_provider_contract():
    # Crypto might need env vars, but we just check if it matches protocol
    # If init fails, we might need a dummy env
    import os
    os.environ.setdefault("BACKUP_ENCRYPTION_KEY", "a" * 32)
    os.environ.setdefault("BACKUP_SIGNING_KEY", "b" * 32)
    assert isinstance(BackupCryptoService(), CryptoProvider)

def test_archive_provider_contract():
    assert isinstance(ArchiveService(), ArchiveProvider)

def test_manifest_provider_contract():
    assert isinstance(ManifestService(), BackupManifestProvider)

def test_planner_provider_contract():
    assert isinstance(RestorePlanner(), RestorePlannerProvider)

def test_audit_provider_contract():
    # Mock db for init
    from unittest.mock import MagicMock
    assert isinstance(BackupAuditEmitter(MagicMock()), AuditProvider)

def test_staging_provider_contract():
    from unittest.mock import MagicMock
    assert isinstance(StagingLogic(MagicMock(), "sqlite:///"), StagingProvider)

def test_promotion_provider_contract():
    from unittest.mock import MagicMock
    from pathlib import Path
    assert isinstance(RestorePromotionService(MagicMock(), Path("/tmp")), PromotionProvider)

def test_rollback_provider_contract():
    from unittest.mock import MagicMock
    assert isinstance(RestoreRollbackService(MagicMock()), RollbackProvider)
