import uuid
from typing import Any, Dict, List, Optional

from ..base import BaseAdapter


class Agent(BaseAdapter):
    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        llm: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        verbose: bool = False,
        allow_delegation: bool = True,
        max_iter: int = 15,
        max_rpm: Optional[int] = None,
    ):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.llm = llm or "default-model"
        self.tools = tools or []
        self.verbose = verbose
        self.allow_delegation = allow_delegation
        self.max_iter = max_iter
        self.max_rpm = max_rpm
        self.id = uuid.uuid4()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "goal": self.goal,
            "backstory": self.backstory,
            "llm": str(self.llm),
            "tools": [str(t) for t in self.tools],
            "allow_delegation": self.allow_delegation,
            "max_iter": self.max_iter,
        }


class Task(BaseAdapter):
    def __init__(
        self,
        description: str,
        expected_output: str,
        agent: Optional[Agent] = None,
        tools: Optional[List[Any]] = None,
        context: Optional[List["Task"]] = None,
    ):
        self.description = description
        self.expected_output = expected_output
        self.agent = agent
        self.tools = tools or []
        self.context = context or []
        self.id = uuid.uuid4()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "expected_output": self.expected_output,
            "agent_role": self.agent.role if self.agent else None,
            "tools": [str(t) for t in self.tools],
            "context": [t.description for t in self.context],
        }


class Crew(BaseAdapter):
    def __init__(
        self,
        agents: List[Agent],
        tasks: List[Task],
        verbose: int = 0,
        process: Optional[str] = "sequential",
    ):
        self.agents = agents
        self.tasks = tasks
        self.verbose = verbose
        self.process = process

    def kickoff(self, inputs: Optional[Dict[str, Any]] = None) -> str:
        results = []
        for i, task in enumerate(self.tasks):
            agent = task.agent or (self.agents[0] if self.agents else None)
            role = agent.role if agent else "Agent"
            desc = task.description
            if inputs:
                for k, v in inputs.items():
                    desc = desc.replace(f"{{{k}}}", str(v))
            result = (
                f"Task: {desc}\n"
                f"Result: Simulated output matching target: {task.expected_output} "
                f"(executed by {role})"
            )
            results.append(result)
        return "\n\n".join(results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "process": self.process,
            "agents": [a.to_dict() for a in self.agents],
            "tasks": [t.to_dict() for t in self.tasks],
        }
