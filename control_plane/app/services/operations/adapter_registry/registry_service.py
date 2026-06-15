from app.core.time import utc_now
from app.models.operations.adapter_registry import (
    AdapterRegistryDecision,
    SignedAdapterRegistryEntry,
)
from app.models.operations.adapter_sandbox import AdapterManifest
from app.services.operations.adapter_registry.hash_utils import compute_registry_hash, sha256_hex
from app.utils.crypto_signer import sign_payload
from sqlalchemy.ext.asyncio import AsyncSession


class SignedAdapterRegistryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_entry(
        self, manifest: AdapterManifest, status: str = "draft"
    ) -> SignedAdapterRegistryEntry:
        payload = {
            "client_id": str(manifest.client_id),
            "adapter_name": manifest.adapter_name,
            "adapter_version": manifest.adapter_version,
            "adapter_type": manifest.adapter_type,
            "manifest_hash": manifest.manifest_hash,
        }
        registry_hash = compute_registry_hash(payload)

        # Signature
        signature = sign_payload(f"{sha256_hex(registry_hash)[:16]}")

        # Deterministic immutable_hash
        immutable_hash = sha256_hex(
            f"entry_{manifest.client_id}_{manifest.adapter_name}_{manifest.adapter_version}_{manifest.manifest_hash}"
        )

        entry = SignedAdapterRegistryEntry(
            client_id=manifest.client_id,
            adapter_name=manifest.adapter_name,
            adapter_version=manifest.adapter_version,
            adapter_type=manifest.adapter_type,
            manifest_id=manifest.id,
            manifest_hash=manifest.manifest_hash,
            registry_status=status,
            registry_hash=registry_hash,
            signature=signature,
            approval_required=manifest.approval_required,
            immutable_hash=immutable_hash,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def submit_entry(
        self, entry: SignedAdapterRegistryEntry, decided_by: str
    ) -> AdapterRegistryDecision:
        if entry.registry_status != "draft":
            raise ValueError(
                f"Cannot submit entry in status '{entry.registry_status}'. Must be 'draft'."
            )

        entry.registry_status = "submitted"
        return await self._create_decision(
            entry, "submit", "accepted", "Submitted for approval", decided_by
        )

    async def approve_entry(
        self, entry: SignedAdapterRegistryEntry, approved_by: str
    ) -> AdapterRegistryDecision:
        if entry.registry_status not in ["submitted", "rejected"]:
            raise ValueError(
                f"Cannot approve entry in status '{entry.registry_status}'. Must be 'submitted' or 'rejected'."
            )

        entry.registry_status = "approved"
        entry.approved_by = approved_by
        entry.approved_at = utc_now()
        return await self._create_decision(
            entry, "approve", "accepted", "Approved by admin", approved_by
        )

    async def reject_entry(
        self, entry: SignedAdapterRegistryEntry, reason: str, decided_by: str
    ) -> AdapterRegistryDecision:
        if not reason:
            raise ValueError("Reason is mandatory for rejection")
        if entry.registry_status != "submitted":
            raise ValueError(
                f"Cannot reject entry in status '{entry.registry_status}'. Must be 'submitted'."
            )

        entry.registry_status = "rejected"
        return await self._create_decision(entry, "reject", "denied", reason, decided_by)

    async def revoke_entry(
        self, entry: SignedAdapterRegistryEntry, reason: str, decided_by: str
    ) -> AdapterRegistryDecision:
        if not reason:
            raise ValueError("Reason is mandatory for revocation")
        if entry.registry_status != "approved":
            raise ValueError(
                f"Cannot revoke entry in status '{entry.registry_status}'. Must be 'approved'."
            )

        entry.registry_status = "revoked"
        entry.revoked_at = utc_now()
        entry.revoked_reason = reason
        return await self._create_decision(entry, "revoke", "denied", reason, decided_by)

    async def block_entry(
        self, entry: SignedAdapterRegistryEntry, reason: str, decided_by: str
    ) -> AdapterRegistryDecision:
        if not reason:
            raise ValueError("Reason is mandatory for blocking")
        # Block can happen from any state
        entry.registry_status = "blocked"
        entry.blocked_reason = reason
        return await self._create_decision(entry, "block", "denied", reason, decided_by)

    async def deprecate_entry(
        self, entry: SignedAdapterRegistryEntry, reason: str, decided_by: str
    ) -> AdapterRegistryDecision:
        if not reason:
            raise ValueError("Reason is mandatory for deprecation")
        if entry.registry_status != "approved":
            raise ValueError(
                f"Cannot deprecate entry in status '{entry.registry_status}'. Must be 'approved'."
            )

        entry.registry_status = "deprecated"
        return await self._create_decision(entry, "deprecate", "accepted", reason, decided_by)

    async def get_effective_status(self, entry: SignedAdapterRegistryEntry) -> str:
        # Status precedence: blocked > revoked > deprecated > approved > submitted > draft
        return entry.registry_status

    async def _create_decision(
        self,
        entry: SignedAdapterRegistryEntry,
        decision_type: str,
        decision_status: str,
        reason: str,
        decided_by: str,
    ) -> AdapterRegistryDecision:
        # Deterministic immutable_hash for decision
        # Use entry_id, decision_type, and current timestamp is NOT allowed.
        # But we need uniqueness if multiple decisions happen.
        # In a deterministic system, we should ideally have a version or sequence.
        # For Phase 74, let's use the logical payload.
        payload = f"decision_{entry.id}_{decision_type}_{decision_status}_{decided_by}_{reason}"
        immutable_hash = sha256_hex(payload)

        decision = AdapterRegistryDecision(
            client_id=entry.client_id,
            registry_entry_id=entry.id,
            decision_type=decision_type,
            decision_status=decision_status,
            reason=reason,
            decided_by=decided_by,
            immutable_hash=immutable_hash,
        )
        self.session.add(decision)
        await self.session.flush()
        return decision
