import os


def test_docs_exist():
    docs = [
        "docs/CUSTOMER_INSTALL_GUIDE.md",
        "docs/CUSTOMER_QUICKSTART.md",
        "docs/CUSTOMER_TROUBLESHOOTING.md",
        "docs/CUSTOMER_REQUIREMENTS.md"
    ]
    for doc in docs:
        assert os.path.exists(doc), f"Missing {doc}"

def test_docs_content_validation():
    with open("docs/CUSTOMER_INSTALL_GUIDE.md", "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "install-local-appliance.sh" in content
    assert "LOCAL_APPLIANCE_MODE" in content
    
    # Check PSP/PIX disclaimer
    assert "PSP" in content.upper() and "PIX" in content.upper()

def test_readme_links():
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "CUSTOMER_INSTALL_GUIDE.md" in content
    assert "CUSTOMER_REQUIREMENTS.md" in content
    assert "CUSTOMER_QUICKSTART.md" in content
    assert "CUSTOMER_TROUBLESHOOTING.md" in content
