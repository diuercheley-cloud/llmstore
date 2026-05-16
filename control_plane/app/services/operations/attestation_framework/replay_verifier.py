from typing import Any

from app.models.operations.attestation_framework import AttestationFederationBundle, SovereignExecutionAttestation
from app.services.operations.attestation_framework.hash_utils import compute_attestation_hash, compute_bundle_hash


class AttestationReplayVerifier:
    def replay_attestation(self, attestation: SovereignExecutionAttestation) -> dict[str, Any]:
        replay_hash = compute_attestation_hash(
            {
                "client_id": str(attestation.client_id),
                "attestation_type": attestation.attestation_type,
                "subject_type": attestation.subject_type,
                "subject_ref": attestation.subject_ref,
                "attestation_scope": attestation.attestation_scope,
                "payload_hash": attestation.payload_hash,
                "previous_attestation_hash": attestation.previous_attestation_hash,
                "signature_placeholder": attestation.signature_placeholder,
                "attestation_chain_position": attestation.attestation_chain_position,
                "replay_verifiable": attestation.replay_verifiable,
                "offline_verifiable": attestation.offline_verifiable,
                "deterministic_version": attestation.deterministic_version,
            }
        )
        return self.compare_replay_hashes(attestation.attestation_hash, replay_hash)

    def replay_chain(self, chain: list[Any]) -> dict[str, Any]:
        consistent = True
        previous_link_hash = None
        for link in sorted(chain, key=lambda item: int(item.chain_position)):
            if link.previous_link_hash != previous_link_hash:
                consistent = False
                break
            previous_link_hash = link.current_link_hash
        return {"match": consistent, "original": previous_link_hash, "replayed": previous_link_hash}

    def replay_bundle(self, bundle: AttestationFederationBundle) -> dict[str, Any]:
        logical_payload = getattr(bundle, "_bundle_payload", None) or {
            "client_id": str(bundle.client_id),
            "bundle_name": bundle.bundle_name,
            "bundle_scope": bundle.bundle_scope,
            "source_environment": bundle.source_environment,
            "target_environment": bundle.target_environment,
            "attestations": [],
            "deterministic_version": "v1",
        }
        replay_hash = compute_bundle_hash(logical_payload)
        return self.compare_replay_hashes(bundle.bundle_hash, replay_hash)

    def compare_replay_hashes(self, original: str, replayed: str) -> dict[str, Any]:
        return {"match": original == replayed, "original": original, "replayed": replayed}
