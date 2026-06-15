from scripts.llm_harness.prompt_builder import PromptBuilder


def test_prompt_builder_includes_policy():
    policy_summary = "ALLOWED: ls, cat. FORBIDDEN: sudo."
    builder = PromptBuilder(policy_summary=policy_summary)
    prompt = builder.build_system_prompt()
    assert policy_summary in prompt
    assert "Senior Software Engineer" in prompt
    assert "JSON" in prompt


def test_prompt_builder_no_policy():
    builder = PromptBuilder()
    prompt = builder.build_system_prompt()
    assert "Senior Software Engineer" in prompt
    assert "Security & Execution Policy" not in prompt


def test_prompt_builder_structure():
    builder = PromptBuilder(policy_summary="Policy context")
    prompt = builder.build_system_prompt()
    assert "Policy context" in prompt
    assert "Guidelines" in prompt
