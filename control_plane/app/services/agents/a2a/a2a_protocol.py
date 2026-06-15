"""
A2A (Agent-to-Agent) Protocol implementation.
Based on Google's Agent-to-Agent specification for inter-agent communication.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class A2AMessageRole(str, Enum):
    AGENT = "agent"
    USER = "user"
    SYSTEM = "system"


class A2ATaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class A2APart:
    text: str | None = None
    data: dict[str, Any] | None = None
    artifact: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        d = {}
        if self.text is not None:
            d["text"] = self.text
        if self.data is not None:
            d["data"] = self.data
        if self.artifact is not None:
            d["artifact"] = self.artifact
        return d

    @classmethod
    def from_text(cls, text: str) -> "A2APart":
        return cls(text=text)

    @classmethod
    def from_data(cls, data: dict) -> "A2APart":
        return cls(data=data)


@dataclass
class A2AMessage:
    role: A2AMessageRole
    parts: list[A2APart] = field(default_factory=list)
    agent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "role": self.role.value,
            "parts": [p.to_dict() for p in self.parts],
            "agentId": self.agent_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "A2AMessage":
        return cls(
            role=A2AMessageRole(d["role"]),
            parts=[A2APart(**p) for p in d.get("parts", [])],
            agent_id=d.get("agentId"),
            metadata=d.get("metadata", {}),
        )


@dataclass
class A2ATask:
    id: str
    session_id: str
    state: A2ATaskState
    history: list[A2AMessage] = field(default_factory=list)
    artifact: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sessionId": self.session_id,
            "state": self.state.value,
            "history": [m.to_dict() for m in self.history],
            "artifact": self.artifact,
            "metadata": self.metadata,
        }


@dataclass
class A2ACard:
    """Agent capability card for discovery."""

    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    url: str = ""
    capabilities: list[str] = field(default_factory=list)
    skills: list[dict[str, Any]] = field(default_factory=list)
    authentication: dict[str, Any] | None = None


class A2AClient:
    """
    A2A client for sending tasks to remote agents.
    Implements the Google A2A spec for agent-to-agent communication.
    """

    def __init__(self, base_url: str = "", api_key: str = ""):
        self.settings = get_settings()
        self.base_url = base_url or self.settings.a2a_base_url or ""
        self.api_key = api_key or self.settings.a2a_api_key or ""
        self._http = httpx.AsyncClient(timeout=30.0)

    async def send_task(self, target_url: str, task: A2ATask) -> A2ATask:
        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {"task": task.to_dict()},
            "id": str(uuid.uuid4()),
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        resp = await self._http.post(target_url, json=payload, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        result = body.get("result", {})
        task_data = result.get("task", result)
        return A2ATask(
            id=task_data.get("id", task.id),
            session_id=task_data.get("sessionId", task.session_id),
            state=A2ATaskState(task_data.get("state", "submitted")),
            history=[A2AMessage.from_dict(m) for m in task_data.get("history", [])],
            artifact=task_data.get("artifact"),
            metadata=task_data.get("metadata", {}),
        )

    async def get_task(self, target_url: str, task_id: str) -> A2ATask | None:
        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"id": task_id},
            "id": str(uuid.uuid4()),
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = await self._http.post(target_url, json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()
            result = body.get("result", {})
            task_data = result.get("task", result)
            return A2ATask(
                id=task_data["id"],
                session_id=task_data.get("sessionId", ""),
                state=A2ATaskState(task_data["state"]),
                history=[A2AMessage.from_dict(m) for m in task_data.get("history", [])],
                artifact=task_data.get("artifact"),
                metadata=task_data.get("metadata", {}),
            )
        except Exception as e:
            logger.error("A2A get_task failed: %s", e)
            return None

    async def cancel_task(self, target_url: str, task_id: str) -> bool:
        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/cancel",
            "params": {"id": task_id},
            "id": str(uuid.uuid4()),
        }
        try:
            resp = await self._http.post(
                target_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                },
            )
            return resp.is_success
        except Exception:
            return False

    async def discover(self, target_url: str) -> A2ACard | None:
        payload = {
            "jsonrpc": "2.0",
            "method": "agents/discover",
            "params": {},
            "id": str(uuid.uuid4()),
        }
        try:
            resp = await self._http.post(
                target_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            body = resp.json()
            result = body.get("result", {})
            card = result.get("card", result)
            return A2ACard(
                agent_id=card.get("agentId", card.get("agent_id", "")),
                name=card.get("name", ""),
                description=card.get("description", ""),
                version=card.get("version", "1.0.0"),
                url=card.get("url", target_url),
                capabilities=card.get("capabilities", []),
                skills=card.get("skills", []),
                authentication=card.get("authentication"),
            )
        except Exception as e:
            logger.error("A2A discover failed for %s: %s", target_url, e)
            return None

    async def close(self):
        await self._http.aclose()


class A2AServer:
    """
    A2A server that handles incoming agent-to-agent requests.
    Register this in FastAPI as a router.
    """

    def __init__(self, agent_id: str, agent_name: str, agent_description: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_description = agent_description
        self._handlers: dict[str, callable] = {}
        self._tasks: dict[str, A2ATask] = {}

    def register_handler(self, skill: str, handler: callable):
        self._handlers[skill] = handler

    def get_card(self) -> A2ACard:
        return A2ACard(
            agent_id=self.agent_id,
            name=self.agent_name,
            description=self.agent_description,
            version="1.0.0",
            url="",
            capabilities=list(self._handlers.keys()),
            skills=[{"name": k} for k in self._handlers],
        )

    async def handle_jsonrpc(self, body: dict) -> dict:
        method = body.get("method", "")
        params = body.get("params", {})
        req_id = body.get("id")

        if method == "agents/discover":
            card = self.get_card()
            return {
                "jsonrpc": "2.0",
                "result": {
                    "card": {
                        "agentId": card.agent_id,
                        "name": card.name,
                        "description": card.description,
                        "version": card.version,
                        "capabilities": card.capabilities,
                        "skills": card.skills,
                    }
                },
                "id": req_id,
            }

        if method == "tasks/send":
            task_data = params.get("task", params)
            task = A2ATask(
                id=task_data.get("id", str(uuid.uuid4())),
                session_id=task_data.get("sessionId", str(uuid.uuid4())),
                state=A2ATaskState.SUBMITTED,
                history=[A2AMessage.from_dict(m) for m in task_data.get("history", [])],
                metadata=task_data.get("metadata", {}),
            )
            self._tasks[task.id] = task
            asyncio.create_task(self._execute_task(task))
            return {"jsonrpc": "2.0", "result": {"task": task.to_dict()}, "id": req_id}

        if method == "tasks/get":
            task_id = params.get("id")
            task = self._tasks.get(task_id)
            if not task:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32000, "message": "Task not found"},
                    "id": req_id,
                }
            return {"jsonrpc": "2.0", "result": {"task": task.to_dict()}, "id": req_id}

        if method == "tasks/cancel":
            task_id = params.get("id")
            task = self._tasks.get(task_id)
            if task:
                task.state = A2ATaskState.CANCELED
            return {"jsonrpc": "2.0", "result": {"success": True}, "id": req_id}

        return {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"Method not found: {method}"},
            "id": req_id,
        }

    async def _execute_task(self, task: A2ATask):
        task.state = A2ATaskState.WORKING
        try:
            last_message = task.history[-1] if task.history else None
            input_text = ""
            if last_message:
                for part in last_message.parts:
                    if part.text:
                        input_text += part.text + "\n"

            skill_name = task.metadata.get("skill", "")
            handler = self._handlers.get(skill_name)
            if handler:
                result = await handler(task)
                task.history.append(
                    A2AMessage(
                        role=A2AMessageRole.AGENT,
                        parts=[A2APart.from_text(str(result))],
                        agent_id=self.agent_id,
                    )
                )
            else:
                task.history.append(
                    A2AMessage(
                        role=A2AMessageRole.AGENT,
                        parts=[A2APart.from_text(f"Received: {input_text[:200]}")],
                        agent_id=self.agent_id,
                    )
                )

            task.state = A2ATaskState.COMPLETED
        except Exception as e:
            logger.exception("A2A task execution failed")
            task.state = A2ATaskState.FAILED
            task.history.append(
                A2AMessage(
                    role=A2AMessageRole.AGENT,
                    parts=[A2APart.from_text(f"Error: {e}")],
                    agent_id=self.agent_id,
                )
            )
