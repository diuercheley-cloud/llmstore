from scripts.llm_harness._code_agents import CodeAgent, OpenAICodeAgent


def test_code_agent_prompt():
    agent = CodeAgent(agent_id="coder")
    # Agora CodeAgent herda de OpenAICodeAgent
    messages = agent.get_initial_messages(task="Fix bug", context="file.py")
    assert any("Fix bug" in m["content"] for m in messages)
    assert any("Senior Software Engineer" in m["content"] for m in messages)


def test_openai_code_agent_policy():
    policy_summary = "POLICY: NO SUDO"
    agent = OpenAICodeAgent(agent_id="test", policy_summary=policy_summary)
    messages = agent.get_initial_messages(task="Task")
    system_msg = next(m for m in messages if m["role"] == "system")
    assert policy_summary in system_msg["content"]


def test_agent_message_generation():
    agent = OpenAICodeAgent(agent_id="test", policy_summary="Rules: No sudo.")
    messages = agent.get_initial_messages(task="Task")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "No sudo" in messages[0]["content"]
