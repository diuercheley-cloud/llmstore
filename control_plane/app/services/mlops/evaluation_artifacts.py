import re
import uuid

from app.core.time import utc_now
from app.models.core.mlops import MLEvalArtifact, MLExperimentRun
from app.services.mlops.dataset_registry import log_mlops_audit
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def detect_sensitive_data(content: str) -> bool:
    if not content:
        return False
    patterns = [
        r"(?i)(api[-_ ]?key|secret|password|private[-_ ]?key|auth_token)\s*[:=]",
        r"sk-[a-zA-Z0-9]{32,}",
        r"Bearer\s+[a-zA-Z0-9_\-\.]+",
    ]
    for p in patterns:
        if re.search(p, content):
            return True
    return False


class EvaluationArtifacts:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_artifact(
        self,
        run_id: uuid.UUID,
        name: str,
        path: str,
        content: str | None = None,
        redaction_policy: str | None = None,
        admin_user_id: uuid.UUID | None = None,
    ) -> MLEvalArtifact:
        # Verify run exists
        result = await self.session.execute(
            select(MLExperimentRun).where(MLExperimentRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            raise HTTPException(status_code=404, detail="Experiment run not found")

        contains_sensitive = (
            detect_sensitive_data(content or "")
            or detect_sensitive_data(name)
            or detect_sensitive_data(path)
        )
        is_redacted = False

        if contains_sensitive:
            if not redaction_policy:
                await log_mlops_audit(
                    self.session,
                    event_type="eval_artifact_register",
                    status="failed",
                    target_type="ml_experiment_runs",
                    target_id=str(run_id),
                    details={"name": name, "reason": "sensitive_data_no_policy"},
                    admin_user_id=admin_user_id,
                )
                raise HTTPException(
                    status_code=400,
                    detail="Sensitive data detected in artifact but no redaction policy was provided. Blocked.",
                )
            else:
                is_redacted = True

        artifact = MLEvalArtifact(
            id=uuid.uuid4(),
            run_id=run_id,
            name=name,
            path=path,
            redaction_policy=redaction_policy,
            is_redacted=is_redacted,
            contains_sensitive_data=contains_sensitive,
            created_at=utc_now(),
        )
        self.session.add(artifact)
        await self.session.flush()

        await log_mlops_audit(
            self.session,
            event_type="eval_artifact_register",
            status="success",
            target_type="ml_eval_artifacts",
            target_id=str(artifact.id),
            details={
                "run_id": str(run_id),
                "name": name,
                "is_redacted": is_redacted,
                "contains_sensitive_data": contains_sensitive,
            },
            admin_user_id=admin_user_id,
        )
        return artifact
