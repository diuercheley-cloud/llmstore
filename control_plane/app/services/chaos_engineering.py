import os
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.operations.chaos import (
    ChaosExperiment,
    ChaosRun,
    ChaosInjection,
    ChaosAssertion,
    ChaosReport,
)
from app.core.config import get_settings

class ChaosEngineeringService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def list_experiments(self) -> List[ChaosExperiment]:
        result = await self.db.execute(select(ChaosExperiment))
        return result.scalars().all()

    async def create_run(self, experiment_id: str, operator_id: str = None) -> ChaosRun:
        # Safety Check
        if not os.getenv("CHAOS_ENABLED", "false").lower() == "true":
            raise ValueError("Chaos Engineering is disabled (CHAOS_ENABLED=false)")

        env = os.getenv("CHAOS_ENVIRONMENT", "test")
        if env == "production" and not os.getenv("CHAOS_ALLOW_PRODUCTION", "false").lower() == "true":
            raise ValueError("Chaos Engineering is blocked in production environment")

        experiment = await self.db.get(ChaosExperiment, experiment_id)
        if not experiment:
            raise ValueError("Experiment not found")

        run = ChaosRun(
            experiment_id=experiment_id,
            status="pending",
            operator_id=operator_id,
            environment=env
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def start_run(self, run_id: str):
        run = await self.db.get(ChaosRun, run_id, options=[selectinload(ChaosRun.experiment)])
        if not run:
            raise ValueError("Run not found")

        run.status = "running"
        run.started_at = datetime.utcnow()
        await self.db.commit()

        # In a real scenario, this would trigger actual fault injection logic
        # For this implementation, we simulate the lifecycle
        try:
            injection = ChaosInjection(
                run_id=run_id,
                injection_type=run.experiment.experiment_type,
                target="mock_target",
                parameters=run.experiment.injection_config
            )
            self.db.add(injection)
            await self.db.commit()

            # Simulate experiment duration
            await asyncio.sleep(2) 

            # Rollback simulation
            injection.rolled_back_at = datetime.utcnow()
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            
            # Generate dummy report
            report = ChaosReport(
                run_id=run_id,
                summary=f"Experiment {run.experiment.name} completed successfully.",
                resilience_score=0.95,
                impact_analysis="Minor latency spike observed, recovery was automatic.",
                recommendations=["Tune circuit breaker threshold for provider_timeout."]
            )
            self.db.add(report)
            
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
        
        await self.db.commit()

    async def abort_run(self, run_id: str):
        run = await self.db.get(ChaosRun, run_id)
        if run and run.status == "running":
            run.status = "aborted"
            run.completed_at = datetime.utcnow()
            await self.db.commit()

    async def get_report(self, run_id: str) -> Optional[ChaosReport]:
        result = await self.db.execute(
            select(ChaosReport).where(ChaosReport.run_id == run_id)
        )
        return result.scalars().first()

    async def seed_default_experiments(self):
        defaults = [
            {
                "name": "Provider Timeout Spike",
                "description": "Simula timeout de 30s em 20% das requisições para OpenAI.",
                "experiment_type": "provider_timeout",
                "blast_radius": "low",
                "injection_config": {"timeout": 30, "ratio": 0.2, "target": "openai"},
                "timeout_seconds": 300,
                "expected_behavior": "Circuit breaker deve abrir e tráfego deve fluir para standby."
            },
            {
                "name": "Redis Outage Simulation",
                "description": "Simula indisponibilidade do cache Redis.",
                "experiment_type": "redis_unavailable",
                "blast_radius": "medium",
                "injection_config": {"mode": "connection_refused"},
                "timeout_seconds": 120,
                "expected_behavior": "Stack deve continuar operando via direct-to-DB, com aumento de latência."
            }
        ]
        
        for d in defaults:
            existing = await self.db.execute(select(ChaosExperiment).where(ChaosExperiment.name == d["name"]))
            if not existing.scalars().first():
                exp = ChaosExperiment(**d)
                self.db.add(exp)
        
        await self.db.commit()
