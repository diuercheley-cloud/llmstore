import abc
import json
import os
from datetime import UTC, datetime
from typing import Any

from ..sanitizer import Sanitizer


class Exporter(abc.ABC):
    @abc.abstractmethod
    def export_run(self, run_dir: str, metadata: dict[str, Any]) -> None:
        pass


class ExperimentConfig:
    def __init__(
        self,
        model: str = "",
        provider: str = "",
        prompt_version: str = "",
        prompt_hash: str = "",
        policy_preset: str = "",
        sandbox: bool = False,
        judge_provider: str = "disabled",
        judge_model: str = "",
        judge_threshold: float = 0.75,
        max_steps: int = 10,
        suite_name: str = "",
        suite_path: str = "",
        extra: dict[str, Any] | None = None,
    ):
        self.model = model
        self.provider = provider
        self.prompt_version = prompt_version
        self.prompt_hash = prompt_hash
        self.policy_preset = policy_preset
        self.sandbox = sandbox
        self.judge_provider = judge_provider
        self.judge_model = judge_model
        self.judge_threshold = judge_threshold
        self.max_steps = max_steps
        self.suite_name = suite_name
        self.suite_path = suite_path
        self.extra = extra or {}

    def to_dict(self) -> dict[str, Any]:
        return Sanitizer.sanitize_data(
            {
                "model": self.model,
                "provider": self.provider,
                "prompt_version": self.prompt_version,
                "prompt_hash": self.prompt_hash,
                "policy_preset": self.policy_preset,
                "sandbox": self.sandbox,
                "judge_provider": self.judge_provider,
                "judge_model": self.judge_model,
                "judge_threshold": self.judge_threshold,
                "max_steps": self.max_steps,
                "suite_name": self.suite_name,
                "suite_path": self.suite_path,
                **self.extra,
            }
        )


class RunMetrics:
    def __init__(
        self,
        accuracy: float = 0.0,
        pass_at_1: float = 0.0,
        judge_avg_score: float = 0.0,
        total_duration_ms: float = 0.0,
        total_tokens: int = 0,
        estimated_cost: float = 0.0,
        cache_hits: int = 0,
        cache_misses: int = 0,
        extra: dict[str, Any] | None = None,
    ):
        self.accuracy = accuracy
        self.pass_at_1 = pass_at_1
        self.judge_avg_score = judge_avg_score
        self.total_duration_ms = total_duration_ms
        self.total_tokens = total_tokens
        self.estimated_cost = estimated_cost
        self.cache_hits = cache_hits
        self.cache_misses = cache_misses
        self.extra = extra or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "accuracy": round(self.accuracy, 4),
            "pass_at_1": round(self.pass_at_1, 4),
            "judge_avg_score": round(self.judge_avg_score, 4),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "total_tokens": self.total_tokens,
            "estimated_cost": round(self.estimated_cost, 6),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            **self.extra,
        }


class LocalExperimentTracker:
    def __init__(self, base_dir: str = "artifacts/evals/runs"):
        self.base_dir = base_dir
        self.run_id: str = ""
        self.run_dir: str = ""

    def create_run(self, config: ExperimentConfig) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        self.run_id = f"{timestamp}"
        self.run_dir = os.path.join(self.base_dir, self.run_id)
        os.makedirs(os.path.join(self.run_dir, "cases"), exist_ok=True)
        self._save_config(config)
        return self.run_id

    def _save_config(self, config: ExperimentConfig) -> str:
        path = os.path.join(self.run_dir, "config.json")
        with open(path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)
        return path

    def save_results(self, results: dict[str, Any]) -> str:
        path = os.path.join(self.run_dir, "results.json")
        sanitized = Sanitizer.sanitize_data(results)
        with open(path, "w") as f:
            json.dump(sanitized, f, indent=2)
        return path

    def save_report(self, report_md: str) -> str:
        path = os.path.join(self.run_dir, "report.md")
        sanitized = Sanitizer.sanitize_text(report_md)
        with open(path, "w") as f:
            f.write(sanitized)
        return path

    def save_case(self, case_id: str, data: dict[str, Any]) -> str:
        path = os.path.join(self.run_dir, "cases", f"{case_id}.json")
        sanitized = Sanitizer.sanitize_data(data)
        with open(path, "w") as f:
            json.dump(sanitized, f, indent=2)
        return path

    def save_metrics(self, metrics: RunMetrics) -> str:
        path = os.path.join(self.run_dir, "metrics.json")
        with open(path, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)
        return path

    def list_runs(self) -> list[dict[str, Any]]:
        if not os.path.isdir(self.base_dir):
            return []
        runs = []
        for entry in sorted(os.listdir(self.base_dir), reverse=True):
            entry_path = os.path.join(self.base_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            config_path = os.path.join(entry_path, "config.json")
            metrics_path = os.path.join(entry_path, "metrics.json")
            run_info: dict[str, Any] = {"run_id": entry, "path": entry_path}
            if os.path.exists(config_path):
                try:
                    with open(config_path) as f:
                        run_info["config"] = json.load(f)
                except (json.JSONDecodeError, OSError):
                    pass
            if os.path.exists(metrics_path):
                try:
                    with open(metrics_path) as f:
                        run_info["metrics"] = json.load(f)
                except (json.JSONDecodeError, OSError):
                    pass
            runs.append(run_info)
        return runs

    def compare_runs(self, run_id_a: str, run_id_b: str) -> dict[str, Any]:
        def load_json(base: str, rid: str, name: str) -> dict[str, Any]:
            path = os.path.join(base, rid, f"{name}.json")
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
            return {}

        base = self.base_dir
        config_a = load_json(base, run_id_a, "config")
        config_b = load_json(base, run_id_b, "config")
        metrics_a = load_json(base, run_id_a, "metrics")
        metrics_b = load_json(base, run_id_b, "metrics")

        return {
            "run_a": {"run_id": run_id_a, "config": config_a, "metrics": metrics_a},
            "run_b": {"run_id": run_id_b, "config": config_b, "metrics": metrics_b},
            "comparison": {
                "accuracy_diff": self._safe_diff(metrics_a, metrics_b, "accuracy"),
                "pass_at_1_diff": self._safe_diff(metrics_a, metrics_b, "pass_at_1"),
                "judge_avg_score_diff": self._safe_diff(metrics_a, metrics_b, "judge_avg_score"),
                "duration_diff_ms": self._safe_diff(metrics_a, metrics_b, "total_duration_ms"),
                "tokens_diff": self._safe_int_diff(metrics_a, metrics_b, "total_tokens"),
            },
        }

    @staticmethod
    def _safe_diff(a: dict[str, Any], b: dict[str, Any], key: str) -> float:
        va = a.get(key, 0.0)
        vb = b.get(key, 0.0)
        if isinstance(va, int | float) and isinstance(vb, int | float):
            return round(vb - va, 4)
        return 0.0

    @staticmethod
    def _safe_int_diff(a: dict[str, Any], b: dict[str, Any], key: str) -> int:
        va = a.get(key, 0)
        vb = b.get(key, 0)
        return int(vb) - int(va)


class MLflowExporter(Exporter):
    def export_run(self, run_dir: str, metadata: dict[str, Any]) -> None:
        try:
            import mlflow
        except ImportError:
            logger = __import__("logging").getLogger(__name__)
            logger.warning("mlflow not installed, skipping MLflow export")
            return

        with mlflow.start_run(run_name=metadata.get("run_id", "eval-run")):
            config = metadata.get("config", {})
            metrics = metadata.get("metrics", {})
            for key, value in config.items():
                if isinstance(value, int | float | str | bool):
                    mlflow.log_param(key, value)
            for key, value in metrics.items():
                if isinstance(value, int | float):
                    mlflow.log_metric(key, value)
            results_path = os.path.join(run_dir, "results.json")
            if os.path.exists(results_path):
                mlflow.log_artifact(results_path)
            report_path = os.path.join(run_dir, "report.md")
            if os.path.exists(report_path):
                mlflow.log_artifact(report_path)
