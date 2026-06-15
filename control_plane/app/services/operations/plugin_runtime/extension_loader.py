import json
from typing import Any

from app.models.operations.plugin_runtime import DeterministicExtensionLoadPlan
from app.services.operations.plugin_runtime.hash_utils import compute_load_plan_hash, sha256_hex


class DeterministicExtensionLoader:
    def build_load_plan(self, contracts: list[Any]) -> list[DeterministicExtensionLoadPlan]:
        ordered_contracts = sorted(
            contracts,
            key=lambda item: (item.plugin_name, item.plugin_version, item.abi_version),
        )
        load_plans: list[DeterministicExtensionLoadPlan] = []
        for index, contract in enumerate(ordered_contracts, start=1):
            status = "blocked" if contract.contract_status in {"blocked", "revoked"} else "proposed"
            load_order_items = [
                {
                    "position": index,
                    "plugin_name": contract.plugin_name,
                    "plugin_version": contract.plugin_version,
                    "abi_version": contract.abi_version,
                }
            ]
            logical_payload = {
                "client_id": str(contract.client_id),
                "abi_contract_id": contract.id,
                "load_order": load_order_items,
                "load_status": status,
                "dry_run": True,
            }
            load_plan_hash = compute_load_plan_hash(logical_payload)
            load_plans.append(
                DeterministicExtensionLoadPlan(
                    id=sha256_hex({"kind": "plugin_load_plan_id", **logical_payload}),
                    client_id=contract.client_id,
                    abi_contract_id=contract.id,
                    load_order=json.dumps(load_order_items, sort_keys=True, separators=(",", ":")),
                    load_plan_hash=load_plan_hash,
                    load_status=status,
                    dry_run=True,
                    immutable_hash=sha256_hex(
                        {"kind": "plugin_load_plan_immutable", "load_plan_hash": load_plan_hash}
                    ),
                )
            )
        return load_plans

    def validate_load_plan(self, load_plan: DeterministicExtensionLoadPlan) -> dict[str, Any]:
        entries = json.loads(load_plan.load_order)
        deterministic = entries == sorted(
            entries,
            key=lambda item: (item["plugin_name"], item["plugin_version"], item["abi_version"]),
        )
        blocked = load_plan.load_status == "blocked"
        return {
            "valid": deterministic and load_plan.dry_run and not blocked,
            "blocked": blocked,
            "dry_run": load_plan.dry_run,
            "no_real_plugin_execution": True,
        }

    def simulate_load(self, load_plan: DeterministicExtensionLoadPlan) -> dict[str, Any]:
        validation = self.validate_load_plan(load_plan)
        if validation["blocked"]:
            load_plan.load_status = "blocked"
        else:
            load_plan.load_status = "simulated"
        return {
            "load_plan_id": load_plan.id,
            "load_status": load_plan.load_status,
            "dry_run": True,
            "executed_plugins": 0,
            "simulated_entries": json.loads(load_plan.load_order),
            "validation": validation,
        }

    def explain_load_plan(self, load_plan: DeterministicExtensionLoadPlan) -> dict[str, Any]:
        return {
            "abi_contract_id": load_plan.abi_contract_id,
            "load_status": load_plan.load_status,
            "dry_run": load_plan.dry_run,
            "load_order": json.loads(load_plan.load_order),
            "notes": [
                "deterministic load simulation only",
                "no external dynamic import for plugins",
                "no real plugin execution",
            ],
        }
