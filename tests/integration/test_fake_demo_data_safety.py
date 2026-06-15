import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAKE_DIR = ROOT / "demo-pack" / "fake-data"


class TestFakeDataSafetyNoRealInfo:
    def test_no_real_patient_names(self):
        real_names = ["Maria Silva", "Joao Silva", "Ana Costa"]
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text()
                for name in real_names:
                    assert name not in content, f"Possible real name {name} in {f}"

    def test_no_real_company_names(self):
        real_companies = [
            "Microsoft",
            "Google",
            "Amazon",
            "Meta",
            "Apple",
            "Petrobras",
            "Vale",
            "Itau",
            "Bradesco",
            "Santander",
        ]
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text()
                for company in real_companies:
                    assert company not in content, f"Real company {company} in {f}"

    def test_no_real_addresses(self):
        suspicious = ["Rua Augusta", "Avenida Paulista", "Copacabana", "Ipanema"]
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text()
                for addr in suspicious:
                    assert addr not in content, f"Real address {addr} in {f}"

    def test_no_real_medical_conditions_described_as_real(self):
        """Medical terms are OK if clearly marked as DEMO/FICTICIO."""
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text().lower()
                if "diabetes" in content or "glicemia" in content or "hipertensao" in content:
                    assert "ficticio" in content or "demo" in content

    def test_no_real_legal_cases(self):
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text().lower()
                if (
                    "trabalhista" in content
                    or "indenizatoria" in content
                    or "reclamacao" in content
                ):
                    assert "ficticio" in content or "demo" in content

    def test_no_sequential_real_phone_numbers(self):
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text()
                phones = re.findall(r"\+55\s*\(?\d{2}\)?\s*\d{4,5}-?\d{4}", content)
                for phone in phones:
                    digits = re.sub(r"\D", "", phone)
                    assert "99999" in digits or "00000" in digits


class TestFakeDataSeedCompatibility:
    def test_seed_script_references_fake_data(self):
        seed = ROOT / "scripts" / "seed-commercial-demo-pack.sh"
        content = seed.read_text()
        assert "fake-data" in content, "Seed script should reference fake-data/"

    def test_validate_script_exists(self):
        script = ROOT / "scripts" / "validate-fake-demo-data.sh"
        assert script.exists()
        assert script.stat().st_mode & 0o111, "Script not executable"

    def test_reset_script_handles_fake_data_clients(self):
        reset = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = reset.read_text()
        clients = json.loads((FAKE_DIR / "clients.json").read_text())
        for c in clients["clients"]:
            assert c["name"] not in content, (
                f"Reset script should not hardcode new client names: {c['name']}"
            )

    def test_validation_script_references_fake_data(self):
        script = ROOT / "scripts" / "validate-fake-demo-data.sh"
        content = script.read_text()
        assert "fake-data" in content
        assert "demo-pack" in content


class TestFakeDataBilling:
    def test_no_real_payment_methods(self):
        real_psp = ["stripe", "mercadopago", "pagseguro", "asaas", "pagar.me"]
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text().lower()
                for psp in real_psp:
                    assert psp not in content, f"Real PSP {psp} found in {f}"

    def test_invoice_amounts_are_fictional(self):
        data = json.loads((FAKE_DIR / "invoices.json").read_text())
        for inv in data["invoices"]:
            assert inv["total_brl"] in (197.00, 297.00, 497.00, 797.00, 1997.00)


class TestFakeDataDemoMarkers:
    def test_every_json_file_has_meta_warning_block(self):
        for f in FAKE_DIR.iterdir():
            if f.suffix == ".json":
                data = json.loads(f.read_text())
                assert "meta" in data
                meta = data["meta"]
                assert "warning" in meta
                assert "FICTICIOS" in meta["warning"].upper()

    def test_every_rag_document_contains_demo_marker(self):
        rag_dir = FAKE_DIR / "rag_documents"
        for f in rag_dir.iterdir():
            if f.is_file():
                content = f.read_text().upper()
                assert "DEMO" in content
                assert "FICTICIO" in content or "FICTÍCIO" in content

    def test_clients_all_end_with_demo_suffix(self):
        data = json.loads((FAKE_DIR / "clients.json").read_text())
        for c in data["clients"]:
            assert c["name"].endswith("Demo"), f"Client {c['name']} missing Demo suffix"

    def test_plan_names_begin_with_demo_prefix(self):
        data = json.loads((FAKE_DIR / "plans.json").read_text())
        for p in data["plans"]:
            assert p["code"].startswith("demo-"), f"Plan {p['code']} missing demo- prefix"

    def test_invoice_numbers_contain_demo_prefix(self):
        data = json.loads((FAKE_DIR / "invoices.json").read_text())
        for inv in data["invoices"]:
            assert inv["invoice_number"].startswith("DEMO-")


class TestFakeDataConsistency:
    def test_client_scenarios_match_across_files(self):
        clients = json.loads((FAKE_DIR / "clients.json").read_text())
        usage = json.loads((FAKE_DIR / "usage.json").read_text())
        invoices = json.loads((FAKE_DIR / "invoices.json").read_text())
        tts = json.loads((FAKE_DIR / "tts_samples.json").read_text())
        prompts = json.loads((FAKE_DIR / "prompts.json").read_text())

        client_scenarios = {c["scenario"] for c in clients["clients"]}
        usage_scenarios = {u["client_scenario"] for u in usage["usage"]}
        invoice_scenarios = {inv["client_scenario"] for inv in invoices["invoices"]}
        tts_scenarios = {t["client_scenario"] for t in tts["tts_samples"]}
        prompt_scenarios = {p["client_scenario"] for p in prompts["prompts"]}

        assert client_scenarios == usage_scenarios
        assert client_scenarios == invoice_scenarios
        assert client_scenarios == tts_scenarios
        assert client_scenarios == prompt_scenarios

    def test_makefile_has_validate_fake_target(self):
        makefile = (ROOT / "Makefile").read_text()
        assert "validate-fake-data" in makefile or "validate-fake-demo" in makefile

    def test_readme_references_fake_data(self):
        readme = ROOT / "demo-pack" / "README.md"
        content = readme.read_text()
        assert "fake-data" in content or "ficticio" in content or "fictício" in content

    def test_local_demo_guide_references_fake_data(self):
        guide = ROOT / "docs" / "LOCAL_DEMO_GUIDE.md"
        if guide.exists():
            content = guide.read_text()
            assert "fake-data" in content or "ficticio" in content or "fictício" in content
