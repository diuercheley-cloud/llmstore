import os
from typing import Any

from app.core.config import get_settings
from app.models.operations.runtime_tuning import (
    RuntimeBenchmarkRun,
    RuntimeTuningEvent,
    RuntimeTuningProfile,
    RuntimeTuningRecommendation,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class RuntimeTuningService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def get_current_profile(self) -> RuntimeTuningProfile | None:
        result = await self.db.execute(
            select(RuntimeTuningProfile).where(RuntimeTuningProfile.is_active == True)
        )
        return result.scalars().first()

    async def list_profiles(self) -> list[RuntimeTuningProfile]:
        result = await self.db.execute(select(RuntimeTuningProfile))
        return result.scalars().all()

    async def seed_default_profiles(self):
        profiles = [
            {
                "name": "balanced",
                "description": "Equilíbrio entre latência e throughput.",
                "config": {
                    "max_concurrent_generations": 4,
                    "response_cache_enabled": True,
                    "queue_timeout_seconds": 30,
                    "retry_attempts": 2,
                },
            },
            {
                "name": "low_latency",
                "description": "Otimizado para tempo de resposta mínimo.",
                "config": {
                    "max_concurrent_generations": 1,
                    "response_cache_enabled": True,
                    "queue_timeout_seconds": 5,
                    "retry_attempts": 1,
                },
            },
            {
                "name": "high_throughput",
                "description": "Maximiza o volume de tokens processados.",
                "config": {
                    "max_concurrent_generations": 16,
                    "response_cache_enabled": False,
                    "queue_timeout_seconds": 120,
                    "retry_attempts": 3,
                },
            },
            {
                "name": "low_cost",
                "description": "Minimiza custos priorizando modelos locais.",
                "config": {
                    "max_concurrent_generations": 2,
                    "response_cache_enabled": True,
                    "semantic_cache_enabled": True,
                    "cloud_providers_enabled": False,
                },
            },
            {
                "name": "gpu_conservative",
                "description": "Economiza memória GPU para outros processos.",
                "config": {
                    "llama_n_gpu_layers": 0,
                    "bonsai_n_gpu_layers": 0,
                    "max_concurrent_generations": 2,
                },
            },
            {
                "name": "memory_constrained",
                "description": "Otimizado para dispositivos com pouca RAM.",
                "config": {
                    "max_context_tokens": 2048,
                    "llama_batch_size": 128,
                    "response_cache_enabled": False,
                },
            },
        ]

        for p_data in profiles:
            p = await self.db.get(RuntimeTuningProfile, p_data["name"])
            if not p:
                new_p = RuntimeTuningProfile(**p_data)
                self.db.add(new_p)

        await self.db.commit()

    async def run_benchmark(self, model_id: str) -> RuntimeBenchmarkRun:
        # Fake benchmark metrics as requested
        import random

        benchmark = RuntimeBenchmarkRun(
            model_id=model_id,
            tokens_per_sec=random.uniform(10, 100),
            latency_p50=random.uniform(100, 500),
            latency_p95=random.uniform(500, 2000),
            latency_p99=random.uniform(2000, 5000),
            queue_wait_ms=random.uniform(0, 1000),
            gpu_memory_pressure=random.uniform(0.1, 0.95),
            cpu_usage=random.uniform(10, 90),
            cache_hit_ratio=random.uniform(0, 0.5),
            fallback_rate=random.uniform(0, 0.2),
            cost_per_1k_tokens=random.uniform(0.001, 0.05),
            error_rate=random.uniform(0, 0.05),
        )

        self.db.add(benchmark)
        await self.db.commit()
        await self.db.refresh(benchmark)

        # Generate recommendations based on these fake metrics
        await self.generate_recommendations(benchmark)

        return benchmark

    async def generate_recommendations(self, benchmark: RuntimeBenchmarkRun):
        recommendations = []

        if benchmark.queue_wait_ms > 500:
            recommendations.append(
                {
                    "title": "Aumentar Paralelismo",
                    "description": "Tempo de espera em fila elevado detectado. Considere aumentar 'max_concurrent_generations'.",
                    "action_type": "CONFIG_UPDATE",
                    "impact": "PERFORMANCE",
                    "priority": "high",
                    "suggested_config": {"max_concurrent_generations": 8},
                }
            )

        if benchmark.gpu_memory_pressure > 0.85:
            recommendations.append(
                {
                    "title": "Aliviar Pressão de GPU",
                    "description": "Uso de memória GPU crítico. Considere reduzir o tamanho do contexto ou o batch size.",
                    "action_type": "CONFIG_UPDATE",
                    "impact": "STABILITY",
                    "priority": "critical",
                    "suggested_config": {"max_context_tokens": 4096, "llama_batch_size": 256},
                }
            )

        if benchmark.fallback_rate > 0.1:
            recommendations.append(
                {
                    "title": "Otimizar Roteamento",
                    "description": "Alta taxa de fallback para provedores secundários. Verifique a saúde do backend principal.",
                    "action_type": "ROUTING_UPDATE",
                    "impact": "STABILITY",
                    "priority": "medium",
                    "suggested_config": {},
                }
            )

        if benchmark.cache_hit_ratio < 0.05:
            recommendations.append(
                {
                    "title": "Ativar Cache Semântico",
                    "description": "Taxa de acerto de cache muito baixa. O cache semântico pode melhorar a performance em 30%.",
                    "action_type": "CONFIG_UPDATE",
                    "impact": "PERFORMANCE",
                    "priority": "low",
                    "suggested_config": {"semantic_cache_enabled": True},
                }
            )

        for rec_data in recommendations:
            rec = RuntimeTuningRecommendation(benchmark_run_id=benchmark.id, **rec_data)
            self.db.add(rec)

        await self.db.commit()

    async def apply_profile(self, profile_name: str, operator_id: str = "system") -> dict[str, Any]:
        profile = await self.db.get(RuntimeTuningProfile, profile_name)
        if not profile:
            raise ValueError(f"Perfil {profile_name} não encontrado.")

        current_profile = await self.get_current_profile()
        previous_config = current_profile.config if current_profile else {}

        # Deactivate all and activate this one
        await self.db.execute(update(RuntimeTuningProfile).values(is_active=False))
        profile.is_active = True

        # Audit event
        event = RuntimeTuningEvent(
            event_type="PROFILE_APPLIED",
            profile_name=profile_name,
            previous_config=previous_config,
            new_config=profile.config,
            operator_id=operator_id,
            metadata_json={
                "advisory": not os.getenv("RUNTIME_TUNING_APPLY_ENABLED", "false").lower() == "true"
            },
        )
        self.db.add(event)

        # In a real scenario, we would update the system config here
        # if RUNTIME_TUNING_APPLY_ENABLED=true

        await self.db.commit()

        return {
            "status": "success",
            "advisory": event.metadata_json["advisory"],
            "profile": profile_name,
            "config": profile.config,
        }

    async def get_recommendations(self) -> list[RuntimeTuningRecommendation]:
        result = await self.db.execute(
            select(RuntimeTuningRecommendation).where(
                RuntimeTuningRecommendation.status == "pending"
            )
        )
        return result.scalars().all()

    async def list_benchmarks(self) -> list[RuntimeBenchmarkRun]:
        result = await self.db.execute(
            select(RuntimeBenchmarkRun).order_by(RuntimeBenchmarkRun.timestamp.desc()).limit(50)
        )
        return result.scalars().all()
