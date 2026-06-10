# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict

from app.core.time import utc_now
from app.models.agents.agent_cicd import AgentPipeline
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class AgentPipelineService:
    """
    Orchestrates the CI/CD pipeline for agents.
    Stages: validate -> test -> eval -> security_scan -> deploy
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_pipeline(self, agent_id: uuid.UUID, tenant_id: str, config: Dict[str, Any]) -> AgentPipeline:
        pipeline = AgentPipeline(
            agent_id=agent_id,
            tenant_id=tenant_id,
            config=config,
            status="pending"
        )
        self.db.add(pipeline)
        await self.db.flush()
        return pipeline

    async def run_pipeline(self, pipeline_id: uuid.UUID):
        stmt = select(AgentPipeline).where(AgentPipeline.id == pipeline_id)
        res = await self.db.execute(stmt)
        pipeline = res.scalar_one_or_none()
        if not pipeline: return

        pipeline.status = "running"
        await self.db.flush()

        try:
            # 1. Validate
            await self._step_validate(pipeline)
            # 2. Test
            await self._step_test(pipeline)
            # 3. Eval
            await self._step_eval(pipeline)
            # 4. Security Scan
            await self._step_security_scan(pipeline)
            # 5. Deploy per environment plan
            config = pipeline.config or {}
            promotion_environments = config.get("promotion_environments") or ["staging"]
            if isinstance(promotion_environments, str):
                promotion_environments = [promotion_environments]
            for environment in promotion_environments:
                await self._step_deploy(pipeline, environment)
            
            pipeline.status = "completed"
        except Exception as e:
            logger.error(f"Pipeline {pipeline_id} failed: {e}")
            pipeline.status = "failed"
        
        pipeline.updated_at = utc_now()
        await self.db.flush()

    async def _step_validate(self, pipeline: AgentPipeline):
        logger.info(f"Pipeline {pipeline.id}: Validating agent definition")
        from app.models.agents.agents import AgentDefinition
        stmt = select(AgentDefinition).where(AgentDefinition.id == pipeline.agent_id)
        res = await self.db.execute(stmt)
        agent = res.scalar_one_or_none()
        if not agent:
            raise RuntimeError(f"Agent {pipeline.agent_id} not found")

        errors = []
        agent_name = getattr(agent, "name", None)
        agent_model_id = getattr(agent, "model_id", None)
        agent_instructions = getattr(agent, "instructions", None)
        agent_config = getattr(agent, "config", None) or {}
        agent_tools = getattr(agent, "tools", None)
        allowed_tools = getattr(agent, "allowed_tools", None)

        if not agent_name or len(str(agent_name).strip()) == 0:
            errors.append("Agent name is empty")
        if not agent_model_id:
            errors.append("Agent model_id is not set")
        if not agent_instructions or len(str(agent_instructions).strip()) == 0:
            errors.append("Agent instructions are empty")
        if agent_config.get("require_tools") and not (agent_tools or allowed_tools):
            errors.append("Agent requires tools but none are configured")

        if errors:
            raise RuntimeError(f"Agent validation failed: {'; '.join(errors)}")
        logger.info(f"Pipeline {pipeline.id}: Validation passed")

    async def _step_test(self, pipeline: AgentPipeline):
        logger.info(f"Pipeline {pipeline.id}: Running unit tests")
        config = pipeline.config or {}
        test_suite_id = config.get("test_suite_id")
        if test_suite_id:
            from app.services.agents.cicd.agent_cicd_tests import AgentCICDTestService
            test_service = AgentCICDTestService(self.db)
            result = await test_service.run_suite(test_suite_id, pipeline.tenant_id)
            if result.get("failed", 0) > 0:
                raise RuntimeError(f"Unit tests failed: {result.get('failed')} failures")
        else:
            logger.info(f"Pipeline {pipeline.id}: No test suite configured, skipping")

    async def _step_eval(self, pipeline: AgentPipeline):
        logger.info(f"Pipeline {pipeline.id}: Running agent evaluations")
        from app.services.agents.agent_evals import AgentEvalService
        eval_service = AgentEvalService(self.db)
        config = pipeline.config or {}
        suite_ids = config.get("eval_suite_ids", config.get("suite_ids", []))
        if suite_ids:
            for sid in suite_ids:
                eval_run = await eval_service.run_eval_suite(uuid.UUID(sid) if isinstance(sid, str) else sid)
                if eval_run.failed_count > 0:
                    logger.warning(f"Pipeline {pipeline.id}: Eval suite {sid} had {eval_run.failed_count} failures")
                    if config.get("fail_on_eval_failure", True) and eval_run.failed_count > 0:
                        raise RuntimeError(f"Eval suite {sid} failed: {eval_run.failed_count} failures")
        else:
            logger.info(f"Pipeline {pipeline.id}: No eval suites configured, skipping")

    async def _step_security_scan(self, pipeline: AgentPipeline):
        logger.info(f"Pipeline {pipeline.id}: Running security scans")
        from app.models.agents.agents import AgentDefinition
        stmt = select(AgentDefinition).where(AgentDefinition.id == pipeline.agent_id)
        res = await self.db.execute(stmt)
        agent = res.scalar_one_or_none()
        if not agent:
            raise RuntimeError(f"Agent {pipeline.agent_id} not found")

        instructions = agent.instructions or ""
        findings = []

        if "ignore_security" in instructions.lower() or "bypass security" in instructions.lower():
            findings.append("Instructions contain security bypass phrases")
        if "eval(" in instructions or "exec(" in instructions: # nosec
            findings.append("Instructions contain potentially dangerous function calls (eval/exec)")
        if "rm -rf /" in instructions or "rm -rf /*" in instructions:
            findings.append("Instructions contain destructive filesystem commands")
        if instructions.count("{") > 50 or instructions.count("}") > 50:
            findings.append("Instructions have excessive template expressions (possible injection attempt)")

        config = pipeline.config or {}
        if config.get("fail_on_security_findings", True) and findings:
            raise RuntimeError(f"Security scan failed: {'; '.join(findings)}")
        if findings:
            logger.warning(f"Pipeline {pipeline.id}: Security findings: {'; '.join(findings)}")
        else:
            logger.info(f"Pipeline {pipeline.id}: Security scan passed")

    async def _step_deploy(self, pipeline: AgentPipeline, environment: str):
        logger.info(f"Pipeline {pipeline.id}: Deploying to {environment}")
        from app.services.agents.cicd.blue_green_deployment import BlueGreenDeploymentService
        bg_service = BlueGreenDeploymentService(self.db)
        config = pipeline.config or {}
        strategy = config.get("rollout_strategy", "blue-green")
        if environment in {"production", "dr", "disaster-recovery"} and config.get("require_manual_approval_for_production", True):
            if not config.get("production_approved", False):
                raise RuntimeError(f"Production deployment blocked: approval missing for environment {environment}")

        deployment = await bg_service.start_deployment(
            pipeline.agent_id,
            environment,
            strategy=strategy,
            pipeline_id=pipeline.id,
            version_tag=config.get("version_tag"),
            rollout_metadata={
                "promotion_environments": config.get("promotion_environments", ["staging"]),
            },
        )

        rollout_weights = config.get("rollout_weights")
        if environment == "staging":
            await bg_service.progressive_rollout(
                deployment.id,
                weights=rollout_weights or [1.0],
                require_healthy=True,
                healthy=config.get("staging_healthy", True),
            )
            return deployment

        await bg_service.progressive_rollout(
            deployment.id,
            weights=rollout_weights or [0.1, 0.5, 1.0],
            require_healthy=True,
            healthy=config.get("production_healthy", True),
        )
        return deployment
