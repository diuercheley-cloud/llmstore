# Owner: agent-platform
import logging
from typing import Any, Dict, List

from jinja2 import Template

logger = logging.getLogger(__name__)

class PromptRuntime:
    """
    Manages prompt templates and runtime injection for different reasoning loops.
    """
    
    REACT_SYSTEM_PROMPT = """
You are an intelligent agent operating in a Thought/Action/Observation/Final loop.
Current Goal: {{ goal }}

Available Tools:
{% for tool in tools %}
- {{ tool.name }}: {{ tool.description }}
  Schema: {{ tool.input_schema }}
{% endfor %}

Process:
1. Thought: Reason about what to do next.
2. Action: Select a tool and provide valid JSON parameters.
3. Observation: Analyze the tool output.
... repeat until goal met ...
Final Answer: Provide the final result.

Format your output exactly as:
Thought: <your thought>
Action: {"tool_name": "...", "parameters": {...}}
"""

    PLAN_AND_SOLVE_PROMPT = """
Goal: {{ goal }}
Create a multi-step plan to achieve this goal.
Execute each step and synthesize the final answer.
"""

    @staticmethod
    def render_react_prompt(goal: str, tools: List[Dict[str, Any]]) -> str:
        template = Template(PromptRuntime.REACT_SYSTEM_PROMPT)
        return template.render(goal=goal, tools=tools)
