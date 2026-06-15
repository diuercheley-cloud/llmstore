from pathlib import Path


def test_capability_matrix_exists():
    """
    Verifica se o arquivo docs/CAPABILITY_MATRIX.md existe.
    """
    project_root = Path(__file__).resolve().parents[2]
    matrix_path = project_root / "docs" / "CAPABILITY_MATRIX.md"
    assert matrix_path.exists(), "docs/CAPABILITY_MATRIX.md deve existir"


def test_capability_matrix_content():
    """
    Verifica se o arquivo docs/CAPABILITY_MATRIX.md contém as features obrigatórias.
    """
    project_root = Path(__file__).resolve().parents[2]
    matrix_path = project_root / "docs" / "CAPABILITY_MATRIX.md"
    content = matrix_path.read_text()

    mandatory_features = [
        "/v1/chat/completions",
        "streaming",
        "/v1/models",
        "RAG",
        "TTS",
        "PSP/PIX real",
        "tools/function calling",
    ]

    for feature in mandatory_features:
        assert feature in content, f"Feature '{feature}' deve estar documentada na matriz"
