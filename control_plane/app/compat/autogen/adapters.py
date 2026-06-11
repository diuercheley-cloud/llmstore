# Owner: platform-operations
from typing import List, Dict, Any, Optional
import uuid

class ConversableAgent:
    """
    AutoGen ConversableAgent adapter.
    """
    def __init__(
        self,
        name: str,
        system_message: str = "A helpful assistant.",
        llm_config: Optional[Dict[str, Any]] = None,
        human_input_mode: str = "NEVER",
        max_consecutive_auto_reply: Optional[int] = None,
    ):
        self.name = name
        self.system_message = system_message
        self.llm_config = llm_config or {}
        self.human_input_mode = human_input_mode
        self.max_consecutive_auto_reply = max_consecutive_auto_reply
        self.chat_history: Dict[str, List[Dict[str, Any]]] = {} # maps recipient name -> list of messages
        self.id = uuid.uuid4()

    def send(self, message: Any, recipient: "ConversableAgent", request_reply: bool = True):
        """
        Sends a message to the recipient.
        """
        msg_payload = {"content": str(message), "role": "assistant"}
        if recipient.name not in self.chat_history:
            self.chat_history[recipient.name] = []
        self.chat_history[recipient.name].append(msg_payload)
        
        recipient.receive(msg_payload, self, request_reply=request_reply)

    def receive(self, message: Dict[str, Any], sender: "ConversableAgent", request_reply: bool = True):
        """
        Receives a message from the sender.
        """
        sender_msg = {"content": message["content"], "role": "user"}
        if sender.name not in self.chat_history:
            self.chat_history[sender.name] = []
        self.chat_history[sender.name].append(sender_msg)
        
        if request_reply:
            reply = self.generate_reply(self.chat_history[sender.name], sender)
            if reply:
                # Send back the reply, but request_reply=False to prevent infinite loops
                self.send(reply, sender, request_reply=False)

    def generate_reply(self, messages: List[Dict[str, Any]], sender: "ConversableAgent") -> Optional[str]:
        """
        Generates a reply. In this emulator, it simulates a response.
        """
        last_message = messages[-1]["content"] if messages else ""
        return f"Simulated reply from {self.name} responding to: '{last_message}'"

    def initiate_chat(self, recipient: "ConversableAgent", message: str, max_turns: int = 1):
        """
        Initiates a chat with the recipient.
        """
        self.send(message, recipient, request_reply=True)
        # Continue back and forth if needed up to max_turns
        # Our basic receive loop already triggers auto-replies.

class UserProxyAgent(ConversableAgent):
    """
    AutoGen UserProxyAgent adapter.
    """
    def __init__(
        self,
        name: str,
        system_message: str = "",
        human_input_mode: str = "NEVER",
        max_consecutive_auto_reply: Optional[int] = None,
        llm_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode=human_input_mode,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
        )

    def generate_reply(self, messages: List[Dict[str, Any]], sender: "ConversableAgent") -> Optional[str]:
        # UserProxy typically acts as the user or runs code. Let's return a simple confirmation.
        last_message = messages[-1]["content"] if messages else ""
        return f"UserProxy ({self.name}) acknowledged: '{last_message}'"
