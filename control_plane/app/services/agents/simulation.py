import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents.agents import AgentRun, AgentRunStep

logger = logging.getLogger(__name__)

class SimulationRuntime:
    @staticmethod
    def classify_tool(tool_name: str, tool_category: Optional[str] = None) -> str:
        name_lower = tool_name.lower()
        cat_lower = (tool_category or "").lower()

        # 1. Email
        if (
            "email" in name_lower
            or "mail" in name_lower
            or "smtp" in name_lower
            or cat_lower == "email"
        ):
            return "email"

        # 2. Filesystem
        if (
            "file" in name_lower
            or "fs" in name_lower
            or "write_file" in name_lower
            or "read_file" in name_lower
            or "delete_file" in name_lower
            or "mkdir" in name_lower
            or "directory" in name_lower
            or "folder" in name_lower
            or cat_lower in ("filesystem", "filesystem_safe", "fs")
        ):
            return "filesystem"

        # 3. Shell
        if (
            "shell" in name_lower
            or "bash" in name_lower
            or "cmd" in name_lower
            or "command" in name_lower
            or "execute_cmd" in name_lower
            or "run_cmd" in name_lower
            or cat_lower in ("shell", "shell_command", "terminal")
        ):
            return "shell"

        # 4. APIs
        if (
            "api" in name_lower
            or "http" in name_lower
            or "request" in name_lower
            or "fetch" in name_lower
            or "webhook" in name_lower
            or "curl" in name_lower
            or "url" in name_lower
            or cat_lower in ("external_api", "api", "http")
        ):
            return "APIs"

        # 5. Database Writes
        if (
            "db_write" in name_lower
            or "sql_write" in name_lower
            or "insert" in name_lower
            or "update" in name_lower
            or "delete" in name_lower
            or "write_db" in name_lower
            or "save" in name_lower
            or "persist" in name_lower
            or cat_lower in ("database_write", "db_write")
        ):
            return "database writes"

        return "other"

    @staticmethod
    def simulate_tool_execution(tool_name: str, category: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate a tool execution, ensuring NO real side effects occur,
        but returning a schema-compatible response for the agent.
        """
        if category == "email":
            return {
                "status": "success",
                "message": f"Email successfully sent to {parameters.get('to', 'recipient')} (simulated)",
                "recipient": parameters.get("to"),
                "subject": parameters.get("subject"),
                "simulated": True,
            }
        elif category == "filesystem":
            return {
                "status": "success",
                "message": f"Simulated filesystem operation: {tool_name} at path '{parameters.get('path', 'unknown')}'",
                "path": parameters.get("path"),
                "bytes_written": len(str(parameters.get("content", ""))) if "content" in parameters else 0,
                "simulated": True,
            }
        elif category == "shell":
            return {
                "status": "success",
                "exit_code": 0,
                "stdout": f"Simulated command execution output for tool '{tool_name}'",
                "stderr": "",
                "simulated": True,
            }
        elif category == "APIs":
            return {
                "status": "success",
                "message": f"Simulated HTTP request for {tool_name}",
                "status_code": 200,
                "response_data": {"message": "Success (simulated)"},
                "simulated": True,
            }
        elif category == "database writes":
            return {
                "status": "success",
                "message": f"Simulated database operation for tool {tool_name}",
                "rows_affected": 1,
                "last_insert_id": 100,
                "simulated": True,
            }
        else:
            return {
                "status": "success",
                "message": f"Simulated tool call: {tool_name}",
                "simulated": True,
            }

    @classmethod
    async def generate_simulation_report(cls, db: AsyncSession, run_id: uuid.UUID) -> Dict[str, Any]:
        """
        Compiles the agent run's steps into a simulation report, and saves it on the AgentRun record.
        """
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        res = await db.execute(stmt)
        run = res.scalar_one_or_none()
        if not run:
            logger.error(f"Cannot generate simulation report: run {run_id} not found.")
            return {}

        # Fetch steps
        stmt_steps = select(AgentRunStep).where(AgentRunStep.run_id == run_id).order_by(AgentRunStep.step_number.asc())
        res_steps = await db.execute(stmt_steps)
        steps = res_steps.scalars().all()

        intercepted_actions = []
        category_counts = {
            "email": 0,
            "filesystem": 0,
            "shell": 0,
            "APIs": 0,
            "database writes": 0,
            "other": 0,
        }

        for step in steps:
            meta = step.step_metadata or {}
            if meta.get("simulated"):
                category = meta.get("simulation_category", "other")
                tool_name = meta.get("tool_name", "unknown")
                tool_input = meta.get("tool_input", {})
                tool_output = meta.get("tool_output", {})

                if category in category_counts:
                    category_counts[category] += 1
                else:
                    category_counts["other"] += 1

                intercepted_actions.append({
                    "step_number": step.step_number,
                    "tool_name": tool_name,
                    "category": category,
                    "parameters": tool_input,
                    "simulated_output": tool_output,
                })

        report = {
            "status": "success",
            "summary": {
                "total_intercepted": len(intercepted_actions),
                "categories": category_counts,
            },
            "intercepted_actions": intercepted_actions,
        }

        run.simulation_report = report
        db.add(run)
        await db.commit()
        logger.info(f"Generated simulation report for run {run_id}: {report}")
        return report
