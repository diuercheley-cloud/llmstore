from datetime import datetime
from typing import Any, Dict, List, Optional

from .schemas import AgentMessage, BlackboardState, SubTask


class Blackboard:
    def __init__(self, task: str):
        self.state = BlackboardState(task=task)
        self.audit_log: List[Dict[str, Any]] = []

    def add_message(self, sender: str, recipient: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        msg = AgentMessage(
            sender=sender,
            recipient=recipient,
            content=content,
            metadata=metadata or {}
        )
        self.state.messages.append(msg)
        self._add_audit_event("message", {
            "sender": sender,
            "recipient": recipient,
            "content": content,
            "metadata": metadata
        })

    def set_plan(self, plan: List[Dict[str, Any]]):
        self.state.plan = plan
        self._add_audit_event("plan_updated", {"plan_length": len(plan)})

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

    def add_reviewer_feedback(self, feedback: str):
        self.state.reviewer_feedback.append(feedback)
        self._add_audit_event("reviewer_feedback", {"feedback": feedback})

    def set_custom_state(self, key: str, value: Any):
        self.state.custom_state[key] = value
        # Don't log potentially large custom state changes in audit unless small
        if isinstance(value, (str, int, float, bool)) or (isinstance(value, list) and len(value) < 10):
             self._add_audit_event("state_updated", {key: value})

    def log_policy_block(self, agent_id: str, tool_name: str, reason: str):
        self._add_audit_event("policy_blocked", {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "reason": reason
        })

    def log_tool_call(self, agent_id: str, tool_name: str, arguments: Dict[str, Any], result: Any):
        # Redact potentially sensitive content from result if needed
        self._add_audit_event("tool_call", {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "result_summary": str(result)[:200] if result else None
        })

    def _add_audit_event(self, event_type: str, data: Dict[str, Any]):
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        })

    def to_summary(self) -> str:
        """
        Generates a summary of the current blackboard state for agent context.
        """
        summary_lines = [
            "--- Work Memory (Blackboard) ---",
            f"Original Task: {self.state.task}",
        ]
        
        if self.state.sub_tasks:
            summary_lines.append("Hierarchical Goals (Sub-tasks):")
            for st in self.state.sub_tasks:
                summary_lines.append(f"  - [{st.status.upper()}] {st.id}: {st.description} (Assigned: {st.assigned_to})")

        if self.state.plan:
            summary_lines.append("Current Plan (Low-level):")
            for idx, action in enumerate(self.state.plan):
                action_type = action.get('type') or action.get('action_type')
                summary_lines.append(f"  {idx+1}. {action_type}: {action}")
        
        if self.state.changed_files:
            summary_lines.append(f"Modified Files so far: {', '.join(self.state.changed_files)}")
            
        if self.state.reviewer_feedback:
            summary_lines.append("Previous Reviewer Feedback:")
            for idx, fb in enumerate(self.state.reviewer_feedback):
                summary_lines.append(f"  [{idx+1}] {fb}")
                
        summary_lines.append("--------------------------------")
        return "\n".join(summary_lines)

    def generate_timeline(self) -> str:
        lines = ["# Team Execution Timeline", ""]
        for event in self.audit_log:
            ts = event["timestamp"]
            etype = event["type"]
            data = event["data"]
            
            if etype == "message":
                lines.append(f"[{ts}] **Message**: {data['sender']} -> {data['recipient']}")
                lines.append(f"  > {data['content'][:200]}...")
            elif etype == "tool_call":
                lines.append(f"[{ts}] **Tool**: {data['agent_id']} called `{data['tool_name']}`")
            elif etype == "policy_blocked":
                lines.append(f"[{ts}] **BLOCKED**: {data['agent_id']} tried `{data['tool_name']}`. Reason: {data['reason']}")
            elif etype == "sub_task_updated":
                lines.append(f"[{ts}] **SubTask Update**: {data['id']} is now {data['status']}")
            else:
                lines.append(f"[{ts}] **{etype.replace('_', ' ').title()}**")
            
            lines.append("")
        return "\n".join(lines)
