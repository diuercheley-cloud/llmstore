import os

def test_local_demo_files_exist():
    docs_path = "docs"
    required_files = [
        "LOCAL_DEMO_GUIDE.md",
        "LOCAL_DEMO_SCRIPT.md",
        "LOCAL_DEMO_FAQ.md"
    ]
    for filename in required_files:
        path = os.path.join(docs_path, filename)
        assert os.path.exists(path), f"File {path} is missing"

def test_readme_links_to_demo_docs():
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
        assert "docs/LOCAL_DEMO_GUIDE.md" in content
        assert "docs/LOCAL_DEMO_SCRIPT.md" in content
        assert "docs/LOCAL_DEMO_FAQ.md" in content

def test_guide_mentions_scripts():
    path = "docs/LOCAL_DEMO_GUIDE.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "seed-demo-local.sh" in content
        assert "reset-demo-local.sh" in content

def test_script_contains_presentation_sequence():
    path = "docs/LOCAL_DEMO_SCRIPT.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        # Check for some sections
        assert "Abertura" in content
        assert "Experiência do Cliente" in content
        assert "Encerramento" in content

def test_faq_mentions_psp_scope():
    path = "docs/LOCAL_DEMO_FAQ.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        # Check if it clarifies that real PSP/PIX is out of scope
        assert "PIX real" in content
        assert "simulado" in content or "manual" in content
