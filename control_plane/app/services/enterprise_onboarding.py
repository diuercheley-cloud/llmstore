from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.models.commercial.commercial_enterprise_onboarding import (
    EnterpriseCustomer,
    EnterpriseHandoverReport,
    EnterpriseOnboardingProject,
    EnterpriseOnboardingTask,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class EnterpriseOnboardingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def create_customer(
        self, name: str, email: str, tier: str = "pilot"
    ) -> EnterpriseCustomer:
        customer = EnterpriseCustomer(name=name, contact_email=email, tier=tier)
        self.db.add(customer)
        await self.db.commit()
        await self.db.refresh(customer)
        return customer

    async def create_project(
        self, customer_id: str, project_name: str
    ) -> EnterpriseOnboardingProject:
        project = EnterpriseOnboardingProject(
            customer_id=customer_id, name=project_name, status="discovery"
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)

        # Initialize default tasks
        await self.initialize_default_tasks(project.id)

        return project

    async def initialize_default_tasks(self, project_id: str):
        default_tasks = [
            ("discovery", "Discovery Workshop", "high"),
            ("environment", "Infrastructure Assessment", "high"),
            ("security", "Security Review & InfoSec Approval", "critical"),
            ("deployment", "Deployment Plan Definition", "high"),
            ("installation", "Base Stack Installation", "high"),
            ("validation", "Operational Readiness Validation", "high"),
            ("acceptance", "User Acceptance Tests (UAT)", "critical"),
            ("training", "Operator Training Session", "medium"),
            ("handover", "Production Handover Report", "high"),
            ("support", "Support Transition Meeting", "medium"),
        ]

        for category, title, priority in default_tasks:
            task = EnterpriseOnboardingTask(
                project_id=project_id, title=title, category=category, status="pending"
            )
            self.db.add(task)

        await self.db.commit()

    async def get_project(self, project_id: str) -> EnterpriseOnboardingProject | None:
        result = await self.db.execute(
            select(EnterpriseOnboardingProject)
            .options(selectinload(EnterpriseOnboardingProject.tasks))
            .where(EnterpriseOnboardingProject.id == project_id)
        )
        return result.scalars().first()

    async def list_projects(self) -> list[EnterpriseOnboardingProject]:
        result = await self.db.execute(
            select(EnterpriseOnboardingProject)
            .options(selectinload(EnterpriseOnboardingProject.customer))
            .order_by(EnterpriseOnboardingProject.start_date.desc())
        )
        return result.scalars().all()

    async def update_task_status(
        self, task_id: str, status: str, notes: str = None
    ) -> EnterpriseOnboardingTask:
        task = await self.db.get(EnterpriseOnboardingTask, task_id)
        if not task:
            raise ValueError("Task not found")

        task.status = status
        if notes:
            task.notes = notes
        if status == "completed":
            task.completed_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def generate_handover_report(self, project_id: str) -> dict[str, Any]:
        project = await self.get_project(project_id)
        if not project:
            raise ValueError("Project not found")

        # In a real scenario, this would aggregate data from:
        # - Operational Readiness
        # - Security Audits
        # - Model Inventory

        report_content = {
            "project_name": project.name,
            "customer_name": "Enterprise Client",  # Should come from project.customer
            "handover_date": datetime.now(UTC).isoformat(),
            "status": project.status,
            "tasks_completed": len([t for t in project.tasks if t.status == "completed"]),
            "total_tasks": len(project.tasks),
            "environment_summary": {
                "deployment_mode": "appliance",
                "security_posture": "hardened",
                "model_count": 4,
                "readiness_score": 0.98,
            },
            "support_contacts": [
                {
                    "role": "Technical Lead",
                    "name": "Pipolante Support",
                    "email": "support@pipolante.ai",
                }
            ],
        }

        report = EnterpriseHandoverReport(project_id=project_id, content_json=report_content)
        self.db.add(report)
        await self.db.commit()

        return report_content
