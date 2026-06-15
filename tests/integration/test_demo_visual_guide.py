import os
import subprocess

BASE_DIR = "docs/demo-visual-guide"
SCREENS = [
    "Landing Page",
    "Capabilities",
    "Client Portal",
    "Admin Dashboard",
    "Admin Lab",
    "System Control Center",
    "Sales/Leads",
    "Pricing/Plans",
    "RAG demo",
    "TTS demo",
    "API examples",
    "Security Report",
    "Production Readiness",
    "Meeting Ready",
    "Proposal/Quote/SOW",
]


def test_demo_visual_guide_docs_exist():
    required = [
        f"{BASE_DIR}/README.md",
        f"{BASE_DIR}/SCREENSHOT_CHECKLIST.md",
        f"{BASE_DIR}/DEMO_VISUAL_FLOW.md",
        f"{BASE_DIR}/CAPTURE_COMMANDS.md",
        f"{BASE_DIR}/DEMO_STORYBOARD.md",
        f"{BASE_DIR}/placeholders/README.md",
    ]
    for doc in required:
        assert os.path.exists(doc), f"Documento obrigatorio nao encontrado: {doc}"


def test_all_screens_documented_in_storyboard():
    with open(f"{BASE_DIR}/DEMO_STORYBOARD.md") as f:
        content = f.read()
    content_lower = content.lower()
    for screen in SCREENS:
        assert screen.lower() in content_lower, (
            f"Tela '{screen}' nao encontrada em DEMO_STORYBOARD.md"
        )


def test_psp_pix_limitations_documented():
    with open(f"{BASE_DIR}/README.md") as f:
        content = f.read()
    assert "PSP" in content or "PIX" in content, "Limitacoes PSP/PIX devem estar no README.md"
    assert "dados reais" in content or "sanitizados" in content


def test_capture_commands_referenced():
    assert os.path.exists(f"{BASE_DIR}/CAPTURE_COMMANDS.md")


def test_storyboard_has_required_fields():
    """Verifica se o storyboard contém os campos obrigatorios."""
    with open(f"{BASE_DIR}/DEMO_STORYBOARD.md") as f:
        content = f.read()
    required_fields = [
        "Ordem",
        "URL",
        "Screenshot esperado",
        "Fala sugerida",
        "Objetivo",
        "Pontos de aten",
    ]
    for field in required_fields:
        assert field in content, f"Campo obrigatorio '{field}' ausente em DEMO_STORYBOARD.md"


def test_readme_links_consistent():
    with open(f"{BASE_DIR}/README.md") as f:
        content = f.read()
    assert "SCREENSHOT_CHECKLIST.md" in content
    assert "DEMO_VISUAL_FLOW.md" in content
    assert "CAPTURE_COMMANDS.md" in content
    assert "DEMO_STORYBOARD.md" in content
    assert "placeholders/README.md" in content


def test_validate_script_runs():
    result = subprocess.run(
        ["bash", "scripts/validators/validate-demo-visual-guide.sh"], capture_output=True, text=True
    )
    # Should pass or have warnings, but not crash
    assert result.returncode == 0 or "AVISO" in result.stdout


def test_prepare_script_help_works():
    result = subprocess.run(
        ["bash", "scripts/dev/prepare-demo-screenshots-local.sh", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Uso:" in result.stdout


def test_screenshot_checklist_items():
    with open(f"{BASE_DIR}/SCREENSHOT_CHECKLIST.md") as f:
        content = f.read()
    assert "- [ ]" in content, "SCREENSHOT_CHECKLIST.md deve conter checklist items"
    assert "Landing Page" in content
    assert "Capabilities" in content
