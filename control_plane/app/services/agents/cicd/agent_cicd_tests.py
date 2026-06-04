import logging
import uuid
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentCICDTestService:
    """
    CI/CD unit test runner for agent pipelines.
    Executes predefined test suites against agent definitions.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_suite(self, suite_id: uuid.UUID, tenant_id: str) -> Dict[str, Any]:
        from app.models.agent_test_suites import AgentTestCase, AgentTestSuite

        stmt = select(AgentTestSuite).where(
            AgentTestSuite.id == suite_id,
            AgentTestSuite.tenant_id == tenant_id,
        )
        res = await self.db.execute(stmt)
        suite = res.scalar_one_or_none()
        if not suite:
            raise ValueError(f"Test suite {suite_id} not found for tenant {tenant_id}")

        stmt_cases = select(AgentTestCase).where(AgentTestCase.suite_id == suite_id)
        res_cases = await self.db.execute(stmt_cases)
        cases = res_cases.scalars().all()

        passed = 0
        failed = 0
        results = []

        for case in cases:
            try:
                outcome = await self._run_case(case, tenant_id)
                if outcome["passed"]:
                    passed += 1
                else:
                    failed += 1
                results.append(outcome)
            except Exception as e:
                failed += 1
                results.append({"case_id": str(case.id), "case_name": case.name, "passed": False, "error": str(e)})

        return {
            "suite_id": str(suite_id),
            "suite_name": suite.name,
            "total": len(cases),
            "passed": passed,
            "failed": failed,
            "results": results,
        }

    async def _run_case(self, case, tenant_id: str) -> Dict[str, Any]:
        import json

        instructions = case.input_data or ""

        assertions = []
        if isinstance(case.expected_output, str):
            assertions = json.loads(case.expected_output) if case.expected_output.startswith("[") else [{"type": "exact_match", "value": case.expected_output}]
        elif isinstance(case.expected_output, list):
            assertions = case.expected_output

        for assertion in assertions:
            a_type = assertion.get("type", "exact_match")
            a_value = assertion.get("value", "")

            if a_type == "exact_match":
                if instructions.strip() != a_value.strip():
                    return {"case_id": str(case.id), "case_name": case.name, "passed": False, "error": f"Expected '{a_value}', got '{instructions.strip()}'"}
            elif a_type == "contains":
                if a_value not in instructions:
                    return {"case_id": str(case.id), "case_name": case.name, "passed": False, "error": f"Expected '{a_value}' not found in instructions"}
            elif a_type == "not_contains":
                if a_value in instructions:
                    return {"case_id": str(case.id), "case_name": case.name, "passed": False, "error": f"Unexpected '{a_value}' found in instructions"}
            elif a_type == "regex":
                import re
                if not re.search(a_value, instructions):
                    return {"case_id": str(case.id), "case_name": case.name, "passed": False, "error": f"Regex '{a_value}' did not match"}

        return {"case_id": str(case.id), "case_name": case.name, "passed": True}
