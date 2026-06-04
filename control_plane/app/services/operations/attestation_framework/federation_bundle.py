from typing import Any

from app.models.operations.attestation_framework import (
    AttestationFederationBundle,
    SovereignExecutionAttestation,
)
from app.services.operations.attestation_framework.hash_utils import compute_bundle_hash, sha256_hex


class AttestationFederationBundleService:
    deterministic_version = "v1"

    def create_bundle(
        self,
        attestations: list[SovereignExecutionAttestation],
        target_environment: str,
        bundle_name: str = "attestation-federation-bundle",
        source_environment: str = "offline-source",
        bundle_scope: str = "operations",
    ) -> tuple[AttestationFederationBundle, dict[str, Any]]:
        if not attestations:
            raise ValueError("at least one attestation is required")
        client_id = attestations[0].client_id
        bundle_payload = {
            "client_id": str(client_id),
            "bundle_name": bundle_name,
            "bundle_scope": bundle_scope,
            "source_environment": source_environment,
            "target_environment": target_environment,
            "attestations": [
                {
                    "id": item.id,
                    "attestation_hash": item.attestation_hash,
                    "attestation_type": item.attestation_type,
                    "subject_ref": item.subject_ref,
                    "signature": item.signature,
                    "replay_verifiable": item.replay_verifiable,
                    "offline_verifiable": item.offline_verifiable,
                }
                for item in attestations
            ],
            "deterministic_version": self.deterministic_version,
        }
        bundle_hash = compute_bundle_hash(bundle_payload)
        bundle = AttestationFederationBundle(
            id=sha256_hex({"kind": "bundle_id", "bundle_hash": bundle_hash}),
            client_id=client_id,
            bundle_name=bundle_name,
            bundle_scope=bundle_scope,
            bundle_hash=bundle_hash,
            source_environment=source_environment,
            target_environment=target_environment,
            bundle_status="draft",
            replay_verifiable=True,
            offline_verifiable=True,
            immutable_hash=sha256_hex({"kind": "bundle", "bundle_hash": bundle_hash, "status": "draft"}),
        )
        bundle._bundle_payload = bundle_payload
        return bundle, bundle_payload

    def export_bundle(self, bundle: AttestationFederationBundle) -> dict[str, Any]:
        bundle.bundle_status = "exported"
        bundle.immutable_hash = sha256_hex({"kind": "bundle", "bundle_hash": bundle.bundle_hash, "status": "exported"})
        return {
            "id": bundle.id,
            "client_id": str(bundle.client_id),
            "bundle_name": bundle.bundle_name,
            "bundle_scope": bundle.bundle_scope,
            "bundle_hash": bundle.bundle_hash,
            "source_environment": bundle.source_environment,
            "target_environment": bundle.target_environment,
            "bundle_status": bundle.bundle_status,
            "replay_verifiable": bundle.replay_verifiable,
            "offline_verifiable": bundle.offline_verifiable,
            "immutable_hash": bundle.immutable_hash,
            "deterministic_version": self.deterministic_version,
            "attestations": getattr(bundle, "_bundle_payload", {}).get("attestations", []),
        }

    def import_bundle(self, bundle_payload: dict[str, Any]) -> AttestationFederationBundle:
        bundle_hash = compute_bundle_hash(
            {
                "client_id": str(bundle_payload["client_id"]),
                "bundle_name": bundle_payload["bundle_name"],
                "bundle_scope": bundle_payload["bundle_scope"],
                "source_environment": bundle_payload["source_environment"],
                "target_environment": bundle_payload["target_environment"],
                "attestations": bundle_payload.get("attestations", []),
                "deterministic_version": bundle_payload.get("deterministic_version", self.deterministic_version),
            }
        )
        bundle = AttestationFederationBundle(
            id=sha256_hex({"kind": "bundle_id", "bundle_hash": bundle_hash}),
            client_id=bundle_payload["client_id"],
            bundle_name=bundle_payload["bundle_name"],
            bundle_scope=bundle_payload["bundle_scope"],
            bundle_hash=bundle_hash,
            source_environment=bundle_payload["source_environment"],
            target_environment=bundle_payload["target_environment"],
            bundle_status="imported",
            replay_verifiable=True,
            offline_verifiable=True,
            immutable_hash=sha256_hex({"kind": "bundle", "bundle_hash": bundle_hash, "status": "imported"}),
        )
        bundle._bundle_payload = {
            "client_id": str(bundle_payload["client_id"]),
            "bundle_name": bundle_payload["bundle_name"],
            "bundle_scope": bundle_payload["bundle_scope"],
            "source_environment": bundle_payload["source_environment"],
            "target_environment": bundle_payload["target_environment"],
            "attestations": bundle_payload.get("attestations", []),
            "deterministic_version": bundle_payload.get("deterministic_version", self.deterministic_version),
        }
        return bundle

    def verify_bundle(self, bundle: AttestationFederationBundle) -> dict[str, Any]:
        passed = bundle.replay_verifiable and bundle.offline_verifiable and bool(bundle.bundle_hash)
        bundle.bundle_status = "verified" if passed else "rejected"
        bundle.immutable_hash = sha256_hex({"kind": "bundle", "bundle_hash": bundle.bundle_hash, "status": bundle.bundle_status})
        return {
            "bundle_id": bundle.id,
            "bundle_hash": bundle.bundle_hash,
            "verification_status": "passed" if passed else "failed",
            "replay_verified": bundle.replay_verifiable,
            "offline_verified": bundle.offline_verifiable,
            "summary": self.explain_bundle(bundle),
        }

    def explain_bundle(self, bundle: AttestationFederationBundle) -> str:
        return (
            f"placeholder federation bundle; source={bundle.source_environment}; "
            f"target={bundle.target_environment}; offline_verifiable={bundle.offline_verifiable}; "
            f"replay_verifiable={bundle.replay_verifiable}; hardware_backed_trust=false"
        )
