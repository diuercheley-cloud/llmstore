import uuid
from typing import Any

from ..base import BaseAdapter


class ConversableAgent(BaseAdapter):
    def __init__(
        self,
        name: str,
        system_message: str = "A helpful assistant.",
        llm_config: dict[str, Any] | None = None,
        human_input_mode: str = "NEVER",
        max_consecutive_auto_reply: int | None = None,
        code_execution_config: dict[str, Any] | None = None,
    ):
        self.name = name
        self.system_message = system_message
        self.llm_config = llm_config or {}
        self.human_input_mode = human_input_mode
        self.max_consecutive_auto_reply = max_consecutive_auto_reply
        self.code_execution_config = code_execution_config
        self.chat_history: dict[str, list[dict[str, Any]]] = {}
        self.id = uuid.uuid4()

    def send(self, message: Any, recipient: "ConversableAgent", request_reply: bool = True):
        msg_payload = {"content": str(message), "role": "assistant"}
        if recipient.name not in self.chat_history:
            self.chat_history[recipient.name] = []
        self.chat_history[recipient.name].append(msg_payload)
        recipient.receive(msg_payload, self, request_reply=request_reply)

    def receive(
        self,
        message: dict[str, Any],
        sender: "ConversableAgent",
        request_reply: bool = True,
    ):
        sender_msg = {"content": message["content"], "role": "user"}
        if sender.name not in self.chat_history:
            self.chat_history[sender.name] = []
        self.chat_history[sender.name].append(sender_msg)
        if request_reply:
            reply = self.generate_reply(self.chat_history[sender.name], sender)
            if reply:
                self.send(reply, sender, request_reply=False)

    def generate_reply(
        self,
        messages: list[dict[str, Any]],
        sender: "ConversableAgent",
    ) -> str | None:
        last_message = messages[-1]["content"] if messages else ""
        return f"Simulated reply from {self.name} responding to: '{last_message[:100]}'"

    def initiate_chat(self, recipient: "ConversableAgent", message: str, max_turns: int = 1):
        self.send(message, recipient, request_reply=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "system_message": self.system_message,
            "human_input_mode": self.human_input_mode,
            "llm_config": self.llm_config,
            "has_code_execution": self.code_execution_config is not None,
            "chat_partners": list(self.chat_history.keys()),
        }


class UserProxyAgent(ConversableAgent):
    def __init__(
        self,
        name: str,
        system_message: str = "",
        human_input_mode: str = "ALWAYS",
        max_consecutive_auto_reply: int | None = None,
        llm_config: dict[str, Any] | None = None,
        code_execution_config: dict[str, Any] | None = None,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode=human_input_mode,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            code_execution_config=code_execution_config,
        )

    def generate_reply(
        self,
        messages: list[dict[str, Any]],
        sender: ConversableAgent,
    ) -> str | None:
        last_message = messages[-1]["content"] if messages else ""
        return f"UserProxy ({self.name}) acknowledged: '{last_message[:100]}'"


class AssistantAgent(ConversableAgent):
    def __init__(
        self,
        name: str,
        system_message: str = "A helpful AI assistant.",
        llm_config: dict[str, Any] | None = None,
        code_execution_config: dict[str, Any] | None = None,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode="NEVER",
            code_execution_config=code_execution_config,
        )

    def generate_reply(
        self,
        messages: list[dict[str, Any]],
        sender: ConversableAgent,
    ) -> str | None:
        last_message = messages[-1]["content"] if messages else ""
        return f"Assistant ({self.name}) response to: '{last_message[:100]}'"


class GroupChat(BaseAdapter):
    def __init__(
        self,
        agents: list[ConversableAgent],
        messages: list[dict[str, Any]] | None = None,
        max_round: int = 10,
        speaker_selection_method: str = "auto",
    ):
        self.agents = agents
        self.messages = messages or []
        self.max_round = max_round
        self.speaker_selection_method = speaker_selection_method

    def to_dict(self) -> dict[str, Any]:
        return {
            "agents": [a.name for a in self.agents],
            "max_round": self.max_round,
            "speaker_selection": self.speaker_selection_method,
            "message_count": len(self.messages),
        }
