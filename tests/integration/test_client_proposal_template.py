import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/dev/generate-client-proposal.sh"


class TestClientProposalTemplate:
    def test_required_sections(self):
        output_dir = ROOT / "artifacts/test-py-template"
        cmd = [
            str(SCRIPT),
            "--company-name",
            "Template Corp",
            "--segment",
            "Healthcare",
            "--output-dir",
            str(output_dir),
        ]
        subprocess.run(cmd, check=True)

        # Find the md file
        md_file = next(output_dir.glob("**/*.md"))
        content = md_file.read_text()

        sections = [
            "Capa",
            "Diagnóstico do Problema",
            "Solução Proposta",
            "Arquitetura Local",
            "Escopo",
            "Fora do Escopo",
            "Plano Recomendado",
            "Valores",
            "Cronograma",
            "Responsabilidades do Cliente",
            "Responsabilidades do Fornecedor",
            "Critérios de Aceite",
            "Validade da Proposta",
            "Próximos Passos",
        ]

        for section in sections:
            assert "## " in content and section in content, f"Section {section} missing in proposal"

    def test_placeholders_replaced(self):
        output_dir = ROOT / "artifacts/test-py-placeholders"
        cmd = [
            str(SCRIPT),
            "--company-name",
            "Custom Company",
            "--contact-name",
            "John Doe",
            "--segment",
            "Finance",
            "--output-dir",
            str(output_dir),
        ]
        subprocess.run(cmd, check=True)

        md_file = next(output_dir.glob("**/*.md"))
        content = md_file.read_text()

        assert "Custom Company" in content
        assert "John Doe" in content
        assert "Finance" in content
        assert "[Nome do Cliente]" not in content
