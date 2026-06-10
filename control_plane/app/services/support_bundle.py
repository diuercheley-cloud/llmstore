"""Support bundle generation for operator diagnostics within the existing support surface."""

# Owner: Platform Operations

import json
import os
import re
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from app.core.config import get_settings
from app.models.core.inference_backend import InferenceBackend
from app.models.core.request_log import RequestLog
from app.services.compliance_readiness import ComplianceReadinessService
from app.services.feature_flag_registry import FeatureFlagRegistryService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Regex patterns for sensitive data redaction (based on scripts/redact_json.py)
REDACT_PATTERNS = [
    r"sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}",
    r"ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}",
    r"JWT_SECRET=[a-zA-Z0-9._-]{12,}",
    r"ghp_[a-zA-Z0-9]{36}",
    r"Bearer [a-zA-Z0-9._-]{20,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"[a-zA-Z0-9_+.-]+:[a-zA-Z0-9_+.-]+@(?:[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|localhost|127\.0\.0\.1)",
    r"Authorization:\s*Bearer\s+[a-zA-Z0-9._-]{20,}",
    r"X-Admin-Token:\s*[a-zA-Z0-9._-]{12,}",
    r"API_KEY=[a-zA-Z0-9._-]{12,}",
    r"DATABASE_URL=[a-z]+://[^:]+:[^@]+@[^/]+",
    r"REDIS_URL=[a-z]+://:[^@]+@[^/]+"
]

SAFE_PATTERNS = [
    r"sk-local-example",
    r"admin-token-123",
    r"your-api-key",
    r"changeme",
    r"example",
    r"localhost",
    r"admin-token-example",
    r"sk-example",
    r"__redacted__",
    r"FAKE SECRET FOR TESTS ONLY"
]

class SupportBundleService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.settings = get_settings()
        self.db = db
        self.root_dir = Path(__file__).resolve().parents[3]
        self.bundles_dir = self.root_dir / "artifacts" / "support-bundles"
        self.bundles_dir.mkdir(parents=True, exist_ok=True)

    def _redact_string(self, val: str) -> str:
        if not val:
            return val
        
        for pattern in REDACT_PATTERNS:
            def replace_func(match):
                m_val = match.group(0)
                for safe in SAFE_PATTERNS:
                    if re.search(safe, m_val):
                        return m_val
                
                if "=" in m_val and not m_val.startswith("---"):
                    key, _ = m_val.split("=", 1)
                    return f"{key}=[REDACTED]"
                if "Bearer " in m_val:
                    return "Bearer [REDACTED]"
                if "X-Admin-Token: " in m_val:
                    return "X-Admin-Token: [REDACTED]"
                return "[REDACTED]"
                
            val = re.sub(pattern, replace_func, val)
        return val

    def _redact_obj(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._redact_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._redact_obj(i) for i in obj]
        elif isinstance(obj, str):
            return self._redact_string(obj)
        else:
            return obj

    def _run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> str:
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.root_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout.strip()
        except Exception as e:
            return f"Error running command {' '.join(cmd)}: {str(e)}"

    async def generate_bundle(self) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        bundle_name = f"support-bundle-{timestamp}"
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            bundle_root = tmp_path / bundle_name
            bundle_root.mkdir()

            # 1. Version and Git Info
            version_info = {
                "version": self.settings.project_version,
                "git_commit": self._run_command(["git", "rev-parse", "HEAD"]),
                "timestamp": timestamp,
                "docker_mode": os.path.exists("/.dockerenv"),
                "k8s_mode": "KUBERNETES_SERVICE_HOST" in os.environ
            }
            with open(bundle_root / "version.json", "w") as f:
                json.dump(version_info, f, indent=2)

            # 2. Runtime Profile and Feature Flags
            ff_service = FeatureFlagRegistryService()
            ff_results = ff_service.scan_orphans()
            
            runtime_info = {
                "runtime_profile": os.getenv("RUNTIME_PROFILE", "default"),
                "feature_flags": self._redact_obj(ff_results)
            }
            with open(bundle_root / "runtime.json", "w") as f:
                json.dump(runtime_info, f, indent=2)

            # 3. Health Summary
            health_summary = self._run_command(["./scripts/test-health.sh"])
            with open(bundle_root / "health.txt", "w") as f:
                f.write(health_summary)

            # 4. Readiness Summary (Latest)
            readiness_dir = self.root_dir / "artifacts" / "production-readiness"
            if readiness_dir.exists():
                latest_report = self._run_command(["find", str(readiness_dir), "-name", "report.json"])
                if latest_report:
                    report_paths = sorted(latest_report.split("\n"))
                    if report_paths:
                        report_path = report_paths[-1]
                        if os.path.exists(report_path):
                            with open(report_path, "r") as f:
                                try:
                                    report_data = json.load(f)
                                    with open(bundle_root / "readiness_report.json", "w") as rf:
                                        json.dump(self._redact_obj(report_data), rf, indent=2)
                                except json.JSONDecodeError:
                                    pass

            # 5. Alembic Head
            alembic_head = self._run_command(["alembic", "current"], cwd=self.root_dir / "control_plane")
            with open(bundle_root / "alembic.txt", "w") as f:
                f.write(alembic_head)

            # 6. API Surface and Script Manifest
            api_surface = self._run_command(["python3", "scripts/check_api_surface.py"])
            script_manifest = self._run_command(["python3", "scripts/check_script_manifest.py"])
            with open(bundle_root / "api_surface.txt", "w") as f:
                f.write(api_surface)
            with open(bundle_root / "script_manifest.txt", "w") as f:
                f.write(script_manifest)

            # 7. Hardware Summary (Sanitized)
            gpu_info = self._run_command(["nvidia-smi", "-L"]) if os.path.exists("/usr/bin/nvidia-smi") else "No NVIDIA GPU detected"
            cpu_info = self._run_command(["lscpu"])
            mem_info = self._run_command(["free", "-h"])
            hardware_summary = f"GPU:\n{gpu_info}\n\nCPU:\n{cpu_info}\n\nMemory:\n{mem_info}"
            with open(bundle_root / "hardware.txt", "w") as f:
                f.write(hardware_summary)

            # 8. Logs (Sanitized) - Last 1000 lines of common log files
            logs_dir = bundle_root / "logs"
            logs_dir.mkdir()
            
            log_files = ["logs/control-plane.log", "logs/data-plane.log", "logs/worker.log"]
            for log_file in log_files:
                log_path = self.root_dir / log_file
                if log_path.exists():
                    log_content = self._run_command(["tail", "-n", "1000", str(log_path)])
                    sanitized_log = self._redact_string(log_content)
                    with open(logs_dir / os.path.basename(log_file), "w") as f:
                        f.write(sanitized_log)

            # 9. Compliance Readiness
            if self.db:
                compliance_service = ComplianceReadinessService(self.db)
                try:
                    frameworks = await compliance_service.list_frameworks()
                    compliance_summary = []
                    for fw in frameworks:
                        report = await compliance_service.get_readiness_report(fw.id)
                        compliance_summary.append(report)
                    
                    with open(bundle_root / "compliance.json", "w") as f:
                        json.dump(self._redact_obj(compliance_summary), f, indent=2)
                except Exception:
                    pass

            # 10. Provider/Backend Health
            if self.db:
                try:
                    backends_result = await self.db.execute(select(InferenceBackend))
                    backends = backends_result.scalars().all()
                    backend_info = []
                    for b in backends:
                        backend_info.append({
                            "name": b.name,
                            "provider": b.provider,
                            "backend_url": b.backend_url,
                            "is_active": b.is_active,
                            "status": b.status
                        })
                    with open(bundle_root / "backends.json", "w") as f:
                        json.dump(self._redact_obj(backend_info), f, indent=2)
                except Exception:
                    pass

            # 11. Metrics Summary (Aggregated)
            if self.db:
                try:
                    total_requests_stmt = select(func.count()).select_from(RequestLog)
                    total_requests = await self.db.execute(total_requests_stmt)
                    
                    avg_latency_stmt = select(func.avg(RequestLog.latency_ms)).select_from(RequestLog)
                    avg_latency = await self.db.execute(avg_latency_stmt)
                    
                    metrics_summary = {
                        "total_requests": total_requests.scalar(),
                        "average_latency_ms": float(avg_latency.scalar() or 0)
                    }
                    with open(bundle_root / "metrics_summary.json", "w") as f:
                        json.dump(metrics_summary, f, indent=2)
                except Exception:
                    pass

            # Create Tarball
            bundle_path = self.bundles_dir / f"{bundle_name}.tar.gz"
            with tarfile.open(bundle_path, "w:gz") as tar:
                tar.add(bundle_root, arcname=bundle_name)

            return str(bundle_path)

    def get_latest_bundle(self) -> Optional[str]:
        bundles = list(self.bundles_dir.glob("support-bundle-*.tar.gz"))
        if not bundles:
            return None
        return str(sorted(bundles)[-1])
