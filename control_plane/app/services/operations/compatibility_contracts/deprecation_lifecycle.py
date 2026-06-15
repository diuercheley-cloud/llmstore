from typing import Any


class DeprecationLifecycleService:
    def propose_deprecation(self, contract: Any) -> dict[str, Any]:
        self._validate_replacement(contract)
        return self._transition(contract, "proposed")

    def announce_deprecation(self, contract: Any) -> dict[str, Any]:
        self._validate_replacement(contract)
        return self._transition(contract, "announced")

    def enforce_deprecation(self, contract: Any) -> dict[str, Any]:
        self._validate_replacement(contract)
        return self._transition(contract, "enforced")

    def complete_deprecation(self, contract: Any) -> dict[str, Any]:
        self._validate_replacement(contract)
        return self._transition(contract, "completed")

    def explain_deprecation(self, contract: Any) -> str:
        return (
            f"status={self._get(contract, 'deprecation_status')}; "
            f"migration_required={self._get(contract, 'migration_required')}; "
            f"replacement_contract={self._get(contract, 'replacement_contract')}"
        )

    def _validate_replacement(self, contract: Any) -> None:
        if self._get(contract, "migration_required") and not self._get(
            contract, "replacement_contract"
        ):
            raise ValueError("replacement_contract is required when migration_required=True")

    def _transition(self, contract: Any, status: str) -> dict[str, Any]:
        return {
            "contract_id": self._get(contract, "contract_id", fallback=self._get(contract, "id")),
            "deprecation_status": status,
            "migration_required": self._get(contract, "migration_required"),
            "replacement_contract": self._get(contract, "replacement_contract"),
        }

    @staticmethod
    def _get(item: Any, key: str, fallback: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(key, fallback)
        return getattr(item, key, fallback)
