from app.services.inference.reproducibility import (
    build_runtime_snapshot,
    compare_outputs,
    compare_runtime_snapshots,
)


def test_runtime_snapshot_detects_tokenizer_and_template_drift():
    original = build_runtime_snapshot(
        model_name="demo/model",
        backend_name="backend-a",
        provider="llama.cpp",
        prompt_template="chatml",
        request_payload={"temperature": 0.2},
        tokenizer_name="tok-a",
        tokenizer_version="1",
        model_metadata_json={"model_file": "demo-Q4_K_M.gguf"},
    )
    replay = build_runtime_snapshot(
        model_name="demo/model",
        backend_name="backend-a",
        provider="llama.cpp",
        prompt_template="jinja2",
        request_payload={"temperature": 0.2},
        tokenizer_name="tok-b",
        tokenizer_version="2",
        model_metadata_json={"model_file": "demo-Q8_0.gguf"},
    )

    result = compare_runtime_snapshots(original, replay)
    assert result["matched"] is False
    assert result["tokenizer_drift"] is True
    assert result["template_drift"] is True
    assert result["quantization_drift"] is True


def test_compare_outputs_similarity_scoring():
    result = compare_outputs("hello brave new world", "hello brave old world")
    assert result["exact_hash_match"] is False
    assert result["similarity"] >= 0.85
    assert result["distance"] > 0
