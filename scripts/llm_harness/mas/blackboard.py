import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .contracts import AgentMessage, BlackboardState, SubTask

logger = logging.getLogger(__name__)


class Blackboard:
    def __init__(self, task: str):
        self.state = BlackboardState(task=task)
        self.audit_log: List[Dict[str, Any]] = []

    def _redact_secrets(self, content: str) -> str:
        if not isinstance(content, str):
            return content
        # Basic redaction patterns for common secrets
        patterns = [
            (r'sk-[a-zA-Z0-9]{32,}', '[REDACTED_API_KEY]'),
            (r'AIza[0-9A-Za-z-_]{35}', '[REDACTED_GOOGLE_KEY]'),
            (r'password\s*[:=]\s*[^\s,]+', 'password: [REDACTED]'),
        ]
        redacted = content
        for pattern, replacement in patterns:
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
        return redacted

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def add_message(self, sender: str, recipient: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        redacted_content = self._redact_secrets(content)
        msg_hash = self._compute_hash(redacted_content)
        
        msg = AgentMessage(
            sender=sender,
            recipient=recipient,
            content=redacted_content,
            metadata=metadata or {},
            hash=msg_hash
        )
        self.state.messages.append(msg)
        self._add_audit_event("message", {
            "sender": sender,
            "recipient": recipient,
            "content_hash": msg_hash,
            "metadata": metadata
        })

    def update_sub_task(self, sub_task: SubTask):
        # Update existing or add new
        for i, existing in enumerate(self.state.sub_tasks):
            if existing.id == sub_task.id:
                self.state.sub_tasks[i] = sub_task
                self._add_audit_event("sub_task_updated", sub_task.model_dump())
                return
        self.state.sub_tasks.append(sub_task)
        self._add_audit_event("sub_task_created", sub_task.model_dump())

    def record_changes(self, changed_files: List[str]):
        self.state.changed_files = list(set(self.state.changed_files + changed_files))
        self._add_audit_event("files_changed", {"files": changed_files})

    def set_plan(self, plan: List[Dict[str, Any]]):
        self.state.plan = plan
        self._add_audit_event("plan_updated", {"plan_length": len(plan)})

    def add_reviewer_feedback(self, feedback: str):
        if not hasattr(self.state, 'reviewer_feedback'):
             # Handle potential schema mismatch if contracts.py was changed
             self.state.custom_state.setdefault('reviewer_feedback', []).append(feedback)
        else:
             self.state.reviewer_feedback.append(feedback)
        self._add_audit_event("reviewer_feedback", {"feedback": feedback})

    def set_custom_state(self, key: str, value: Any):
        self.state.custom_state[key] = value
        self._add_audit_event("state_updated", {key: value})

    def log_policy_block(self, agent_id: str, tool_name: str, reason: str):
        self._add_audit_event("policy_blocked", {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "reason": reason
        })

    def log_tool_call(self, agent_id: str, tool_name: str, arguments: Dict[str, Any], result: Any):
        self._add_audit_event("tool_call", {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "result_summary": str(result)[:200] if result else None
        })

    def generate_timeline(self) -> str:
        lines = ["# Team Execution Timeline", ""]
        for event in self.audit_log:
            ts = event["timestamp"]
            etype = event["type"]
            data = event["data"]
            
            if etype == "message":
                lines.append(f"[{ts}] **Message**: {data['sender']} -> {data['recipient']}")
            elif etype == "tool_call":
                lines.append(f"[{ts}] **Tool**: {data['agent_id']} called `{data['tool_name']}`")
            elif etype == "policy_blocked":
                lines.append(f"[{ts}] **BLOCKED**: {data['agent_id']} tried `{data['tool_name']}`. Reason: {data['reason']}")
            else:
                lines.append(f"[{ts}] **{etype.replace('_', ' ').title()}**")
            lines.append("")
        return "\n".join(lines)

    def _add_audit_event(self, event_type: str, data: Dict[str, Any]):
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data,
            "hash": self._compute_hash(json.dumps(data, sort_keys=True))
        })

    def to_summary(self) -> str:
        summary_lines = [
            "--- Shared Blackboard ---",
            f"Task: {self.state.task}",
        ]
        if self.state.sub_tasks:
            summary_lines.append("Sub-tasks:")
            for st in self.state.sub_tasks:
                summary_lines.append(f"  - {st.id}: {st.status} ({st.assigned_to})")
        
        if self.state.changed_files:
            summary_lines.append(f"Files Modified: {', '.join(self.state.changed_files)}")
            
        summary_lines.append("Recent messages:")
        for msg in self.state.messages[-5:]:
            summary_lines.append(f"  [{msg.sender} -> {msg.recipient}]: {msg.content[:100]}...")
            
        summary_lines.append("-------------------------")
        return "\n".join(summary_lines)
