from scripts.llm_harness.memory import LocalMemory


def test_local_memory_record_and_retrieve(tmp_path):
    memory_dir = tmp_path / "memory"
    lm = LocalMemory(memory_dir=str(memory_dir))
    
    task = "Fix bug X"
    result = {
        "success": True,
        "message": "Fixed",
        "metrics": {"changed_files": ["file1.py"]}
    }
    
    lm.record_run(task, result)
    
    history = lm.get_recent_history()
    assert len(history) == 1
    assert history[0]["task"] == task
    assert history[0]["success"] is True

def test_memory_context_prompt(tmp_path):
    memory_dir = tmp_path / "memory"
    lm = LocalMemory(memory_dir=str(memory_dir))
    
    lm.record_run("Task 1", {"success": True})
    lm.record_run("Task 2", {"success": False, "error": "Fail"})
    
    context = lm.get_context_for_prompt()
    assert "Task 1" in context
    assert "Task 2" in context
    assert "Failed" in context
    assert "Success" in context
