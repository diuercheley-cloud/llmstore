from pathlib import Path


def test_no_misleading_pix_in_public_docs():
    """Validates that public documentation clarifies real PIX/PSP is out of scope."""
    root_dir = Path(__file__).parent.parent
    docs_to_check = [
        root_dir / "README.md",
        root_dir / "docs/LOCAL_DEMO_FAQ.md",
        root_dir / "docs/LOCAL_DEMO_GUIDE.md",
        root_dir / "docs/LOCAL_PRODUCTION_RUNBOOK.md",
        root_dir / "control_plane/app/static/www/index.html",
    ]
    
    for doc_path in docs_to_check:
        if not doc_path.exists():
            continue
        content = doc_path.read_text()
        
        # Should NOT contain these in a misleading way
        # (We allow them if they are followed by 'fora do escopo', 'simulação', 'manual', etc.)
        bad_patterns = [
            "PIX real",
            "pagamento PIX real",
            "gerar PIX",
            "QR Code PIX",
            "PSP ativo",
        ]
        
        for pattern in bad_patterns:
            # If the pattern exists, it MUST be clarified
            if pattern in content:
                # Basic check: is there a clarification nearby?
                # This is a bit loose but helps find obvious promises
                assert any(clarification in content.lower() for clarification in [
                    "fora do escopo", 
                    "não há integração", 
                    "simulação", 
                    "manual", 
                    "preparado para futura",
                    "sem pix real"
                ]), f"Misleading pattern '{pattern}' found in {doc_path} without clarification."

def test_billing_terminology_in_static_files():
    """Checks that static UI files use manual/local terminology."""
    root_dir = Path(__file__).parent.parent
    admin_lab_path = root_dir / "control_plane/app/static/admin-lab/index.html"
    
    if admin_lab_path.exists():
        content = admin_lab_path.read_text()
        # Should use 'Billing Local/Manual' instead of just 'Manual PIX'
        assert "Billing Local/Manual" in content
        # Should NOT have 'Manual PIX' as the visible label in the select (we changed it)
        assert "<option value=\"manual_pix\">Manual PIX</option>" not in content

def test_no_real_psp_endpoints_in_code():
    """Ensures no real PSP (Stripe/Asaas) integration endpoints were accidentally added."""
    root_dir = Path(__file__).parent.parent
    api_dir = root_dir / "control_plane/app/api"
    
    for py_file in api_dir.glob("*.py"):
        content = py_file.read_text()
        # Check for typical PSP SDK imports or webhook patterns that look real
        assert "import stripe" not in content.lower()
        assert "import asaas" not in content.lower()
        # The only allowed webhook is the local-payment one we renamed
        assert "/public/webhooks/pix" not in content

def test_portal_api_billing_message():
    """
    Validates that the portal API returns 'pagamento manual/local' 
    when in manual billing mode.
    Note: This is a structural check on the source code as we might not have a running DB here.
    """
    portal_api_path = Path(__file__).parent.parent / "control_plane/app/api/portal.py"
    if portal_api_path.exists():
        content = portal_api_path.read_text()
        assert '"local_billing_message": "pagamento manual/local"' in content
