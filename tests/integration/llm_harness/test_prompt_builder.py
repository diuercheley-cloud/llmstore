from scripts.llm_harness.prompt_builder import PromptBuilder


def test_prompt_builder_includes_task_and_context():
    builder = PromptBuilder()
    task = "Fix a bug in main.py"
    context = "main.py content"
    prompt = builder.build_task_prompt(task, context)

    assert "### Task" in prompt
    assert task in prompt
    assert "### Context" in prompt
    assert context in prompt
    assert "Respond only with the next action as a JSON object." in prompt


def test_prompt_builder_includes_policy_summary():
    policy = "ALLOWED: ls, cat. FORBIDDEN: rm."
    builder = PromptBuilder(policy_summary=policy)
    prompt = builder.build_system_prompt()

    assert policy in prompt
    assert "Senior Software Engineer" in prompt


def test_prompt_builder_demands_json_action():
    builder = PromptBuilder()
    prompt = builder.build_system_prompt()

    assert "Always produce valid JSON for actions." in prompt
    assert '{"type":"plan|read_file|apply_patch|run_shell|run_tests|final"' in prompt


def test_prompt_builder_no_secrets_guideline():
    builder = PromptBuilder()
    prompt = builder.build_system_prompt()

    # Guidelines should mention not accessing forbidden files like .env
    assert "Do not attempt to use 'sudo' or access forbidden files like '.env'." in prompt
