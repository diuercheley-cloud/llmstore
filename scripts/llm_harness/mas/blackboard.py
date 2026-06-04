from typing import Any, Dict, List, Optional
from .schemas import BlackboardState, AgentMessage, SubTask

class Blackboard:
    def __init__(self, task: str):
        self.state = BlackboardState(task=task)

    def add_message(self, sender: str, recipient: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        msg = AgentMessage(
            sender=sender,
            recipient=recipient,
            content=content,
            metadata=metadata or {}
        )
        self.state.messages.append(msg)

    def set_plan(self, plan: List[Dict[str, Any]]):
        self.state.plan = plan

    def update_sub_task(self, sub_task: SubTask):
        # Update existing or add new
        for i, existing in enumerate(self.state.sub_tasks):
            if existing.id == sub_task.id:
                self.state.sub_tasks[i] = sub_task
                return
        self.state.sub_tasks.append(sub_task)

    def record_changes(self, changed_files: List[str]):
        self.state.changed_files = list(set(self.state.changed_files + changed_files))

    def add_reviewer_feedback(self, feedback: str):
        self.state.reviewer_feedback.append(feedback)

    def set_custom_state(self, key: str, value: Any):
        self.state.custom_state[key] = value

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
