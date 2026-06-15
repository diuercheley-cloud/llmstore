from collections.abc import Iterable
from typing import Any

RESTRICTED_CAPABILITIES = {
    "shell",
    "subprocess",
    "network",
    "kubernetes_apply",
    "proxmox_mutate",
    "nomad_run",
    "external_secret_read",
    "hardware_attestation_real",
}


class CapabilityNegotiationService:
    def negotiate_capabilities(
        self, requested: Iterable[str], available: Iterable[str]
    ) -> dict[str, Any]:
        requested_set = self._normalize(requested)
        available_set = self._normalize(available)
        denied = sorted(
            {*self.deny_restricted_capabilities(requested_set), *(requested_set - available_set)}
        )
        approved = sorted((requested_set & available_set) - set(denied))
        if approved and denied:
            status = "partially_approved"
        elif approved:
            status = "approved"
        else:
            status = "denied"
        return {
            "requested_capabilities": sorted(requested_set),
            "approved_capabilities": approved,
            "denied_capabilities": denied,
            "negotiation_status": status,
        }

    def validate_capabilities(self, result: dict[str, Any]) -> bool:
        requested = set(result["requested_capabilities"])
        approved = set(result["approved_capabilities"])
        denied = set(result["denied_capabilities"])
        if approved & denied:
            return False
        if approved - requested:
            return False
        if denied & RESTRICTED_CAPABILITIES and result["negotiation_status"] == "approved":
            return False
        return approved <= requested

    def deny_restricted_capabilities(self, capabilities: Iterable[str]) -> list[str]:
        return sorted(set(capabilities) & RESTRICTED_CAPABILITIES)

    def explain_capabilities(self, result: dict[str, Any]) -> str:
        return (
            f"status={result['negotiation_status']}; "
            f"approved={','.join(result['approved_capabilities']) or 'none'}; "
            f"denied={','.join(result['denied_capabilities']) or 'none'}"
        )

    @staticmethod
    def _normalize(capabilities: Iterable[str]) -> set[str]:
        return {str(capability).strip() for capability in capabilities if str(capability).strip()}
