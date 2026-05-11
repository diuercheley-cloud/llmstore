import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FAKE_DIR = ROOT / "demo-pack" / "fake-data"


class TestFakeDataStructure:
    def test_fake_data_dir_exists(self):
        assert FAKE_DIR.is_dir()

    def test_rag_documents_dir_exists(self):
        rag_dir = FAKE_DIR / "rag_documents"
        assert rag_dir.is_dir()

    def test_all_required_files_exist(self):
        required = [
            "clients.json",
            "plans.json",
            "invoices.json",
            "usage.json",
            "tts_samples.json",
            "prompts.json",
        ]
        for f in required:
            assert (FAKE_DIR / f).exists(), f"Missing required file: {f}"

    def test_all_rag_documents_exist(self):
        expected = [
            "politica_interna_horizonte.txt",
            "contrato_atlas.txt",
            "manual_suporte_orion.txt",
            "faq_prisma.txt",
            "base_conhecimento_nebula.txt",
        ]
        for doc in expected:
            assert (FAKE_DIR / "rag_documents" / doc).exists(), f"Missing RAG doc: {doc}"


class TestFakeDataJsonValidity:
    def test_clients_json_valid(self):
        data = json.loads((FAKE_DIR / "clients.json").read_text())
        assert "clients" in data
        assert len(data["clients"]) == 5
        assert "meta" in data
        assert data["meta"]["demo_marker"] is True

    def test_plans_json_valid(self):
        data = json.loads((FAKE_DIR / "plans.json").read_text())
        assert "plans" in data
        assert len(data["plans"]) == 5
        assert data["meta"]["demo_marker"] is True

    def test_invoices_json_valid(self):
        data = json.loads((FAKE_DIR / "invoices.json").read_text())
        assert "invoices" in data
        assert len(data["invoices"]) == 5
        assert data["meta"]["demo_marker"] is True

    def test_usage_json_valid(self):
        data = json.loads((FAKE_DIR / "usage.json").read_text())
        assert "usage" in data
        assert len(data["usage"]) == 5
        assert data["meta"]["demo_marker"] is True

    def test_tts_samples_json_valid(self):
        data = json.loads((FAKE_DIR / "tts_samples.json").read_text())
        assert "tts_samples" in data
        assert len(data["tts_samples"]) == 5
        assert data["meta"]["demo_marker"] is True

    def test_prompts_json_valid(self):
        data = json.loads((FAKE_DIR / "prompts.json").read_text())
        assert "prompts" in data
        assert len(data["prompts"]) >= 5
        assert data["meta"]["demo_marker"] is True


class TestFakeClientNames:
    def test_expected_clients_present(self):
        data = json.loads((FAKE_DIR / "clients.json").read_text())
        names = {c["name"] for c in data["clients"]}
        expected = {
            "Clinica Horizonte Demo",
            "Juridico Atlas Demo",
            "Suporte Orion Demo",
            "Escola Prisma Demo",
            "Provedor API Nebula Demo",
        }
        assert names == expected, f"Expected {expected}, got {names}"

    def test_all_clients_have_demo_flag(self):
        data = json.loads((FAKE_DIR / "clients.json").read_text())
        for c in data["clients"]:
            assert c.get("demo") is True, f"Client {c['name']} missing demo=true"
            assert "Demo" in c["name"], f"Client {c['name']} missing Demo suffix"

    def test_all_clients_have_required_fields(self):
        data = json.loads((FAKE_DIR / "clients.json").read_text())
        required = ["client_id", "name", "email", "scenario", "plan_code", "metadata"]
        for c in data["clients"]:
            for field in required:
                assert field in c, f"Client {c.get('name', '?')} missing field: {field}"

    def test_client_ids_are_deterministic_uuids(self):
        data = json.loads((FAKE_DIR / "clients.json").read_text())
        uuids = {c["client_id"] for c in data["clients"]}
        assert len(uuids) == 5
        for uid in uuids:
            assert re.match(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                uid,
            ), f"Invalid UUID format: {uid}"

    def test_all_clients_have_plans(self):
        data = json.loads((FAKE_DIR / "clients.json").read_text())
        plans = json.loads((FAKE_DIR / "plans.json").read_text())
        plan_codes = {p["code"] for p in plans["plans"]}
        for c in data["clients"]:
            assert c["plan_code"] in plan_codes, (
                f"Client {c['name']} references unknown plan {c['plan_code']}"
            )


class TestFakeDataSafety:
    def test_no_real_cpf_in_any_file(self):
        cpf_pattern = r"\d{3}\.\d{3}\.\d{3}-\d{2}"
        allowed = {"000.000.000-00", "123.456.789-00"}
        files = list(FAKE_DIR.rglob("*"))
        for f in files:
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text()
                matches = re.findall(cpf_pattern, content)
                for m in matches:
                    assert m in allowed, f"Possible real CPF {m} in {f}"

    def test_no_real_cnpj_in_any_file(self):
        cnpj_pattern = r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"
        allowed = {"00.000.000/0001-00"}
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text()
                matches = re.findall(cnpj_pattern, content)
                for m in matches:
                    assert m in allowed, f"Possible real CNPJ {m} in {f}"

    def test_emails_use_safe_domains_only(self):
        allowed_suffixes = {".demo.local", ".example.local"}
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text()
                emails = re.findall(r"[\w.+-]+@[\w.-]+\.[\w.+-]+", content)
                for email in emails:
                    domain = email.split("@")[1]
                    ok = any(domain.endswith(suffix) for suffix in allowed_suffixes)
                    assert ok, f"Domain {domain} not allowed in {f}: {email}"

    def test_phones_use_fake_prefix(self):
        phone_pattern = r"\+55\s*\(?\d{2}\)?\s*\d{4,5}-?\d{4}"
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text()
                phones = re.findall(phone_pattern, content)
                for phone in phones:
                    assert "99999" in phone, f"Possible real phone {phone} in {f}"

    def test_no_api_keys_or_secrets(self):
        secret_patterns = [
            r"sk-[a-zA-Z0-9]{20,}",
            r"ghp_[a-zA-Z0-9]{36}",
            r"-----BEGIN (RSA |EC )?PRIVATE KEY-----",
            r"ADMIN_TOKEN=[a-zA-Z0-9]{10,}",
        ]
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text()
                for pattern in secret_patterns:
                    matches = re.findall(pattern, content)
                    for m in matches:
                        if "demo" in m.lower() or "example" in m.lower() or "XXXX" in m:
                            continue
                        if "sk-nebula-demo" in m:
                            continue
                        pytest.fail(f"Possible secret {m[:30]}... in {f}")

    def test_all_files_have_demo_marker(self):
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text().lower()
                assert "demo" in content or "ficticio" in content, (
                    f"No DEMO marker in {f}"
                )

    def test_no_real_email_domains(self):
        real_domains = [
            "gmail.com",
            "yahoo.com",
            "hotmail.com",
            "outlook.com",
            "uol.com.br",
            "bol.com.br",
            "terra.com.br",
            "ig.com.br",
            "globo.com",
        ]
        for f in FAKE_DIR.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".txt"):
                content = f.read_text().lower()
                for domain in real_domains:
                    assert domain not in content, f"Real domain {domain} found in {f}"

    def test_all_files_have_meta_warning(self):
        json_files = [f for f in FAKE_DIR.iterdir() if f.suffix == ".json"]
        for f in json_files:
            data = json.loads(f.read_text())
            assert "meta" in data, f"Missing meta in {f.name}"
            assert "warning" in data["meta"], f"Missing warning in meta of {f.name}"
            assert "FICTICIOS" in data["meta"]["warning"].upper(), (
                f"Warning not strong enough in {f.name}"
            )


class TestFakeDataPlans:
    def test_all_plans_have_demo_flag(self):
        data = json.loads((FAKE_DIR / "plans.json").read_text())
        for p in data["plans"]:
            assert p.get("demo") is True, f"Plan {p['code']} missing demo=true"

    def test_all_plans_have_required_fields(self):
        data = json.loads((FAKE_DIR / "plans.json").read_text())
        required = ["code", "name", "monthly_price_brl", "rate_limit_per_minute"]
        for p in data["plans"]:
            for field in required:
                assert field in p, f"Plan {p.get('code', '?')} missing {field}"

    def test_plan_codes_match_prefix(self):
        data = json.loads((FAKE_DIR / "plans.json").read_text())
        for p in data["plans"]:
            assert p["code"].startswith("demo-"), f"Plan {p['code']} not prefixed demo-"


class TestFakeDataInvoices:
    def test_all_invoices_have_demo_flag(self):
        data = json.loads((FAKE_DIR / "invoices.json").read_text())
        for inv in data["invoices"]:
            assert inv.get("demo") is True
            assert "DEMO" in inv["invoice_number"]

    def test_invoice_client_references_match(self):
        clients = json.loads((FAKE_DIR / "clients.json").read_text())
        invoices = json.loads((FAKE_DIR / "invoices.json").read_text())
        client_names = {c["name"] for c in clients["clients"]}
        for inv in invoices["invoices"]:
            assert inv["client_name"] in client_names, (
                f"Invoice references unknown client: {inv['client_name']}"
            )


class TestFakeDataUsage:
    def test_all_usage_have_demo_flag(self):
        data = json.loads((FAKE_DIR / "usage.json").read_text())
        for u in data["usage"]:
            assert u.get("demo") is True

    def test_usage_client_references_match(self):
        clients = json.loads((FAKE_DIR / "clients.json").read_text())
        usage_data = json.loads((FAKE_DIR / "usage.json").read_text())
        scenarios = {c["scenario"] for c in clients["clients"]}
        for u in usage_data["usage"]:
            assert u["client_scenario"] in scenarios, (
                f"Usage references unknown scenario: {u['client_scenario']}"
            )


class TestFakeDataPrompts:
    def test_all_prompts_have_demo_flag(self):
        data = json.loads((FAKE_DIR / "prompts.json").read_text())
        for p in data["prompts"]:
            assert p.get("demo") is True

    def test_prompts_cover_all_clients(self):
        data = json.loads((FAKE_DIR / "prompts.json").read_text())
        scenarios = {p["client_scenario"] for p in data["prompts"]}
        expected = {"clinica", "juridico", "suporte", "educacao", "provedor-api"}
        assert scenarios == expected

    def test_prompts_mention_ficticio(self):
        data = json.loads((FAKE_DIR / "prompts.json").read_text())
        for p in data["prompts"]:
            assert "ficticio" in p["user_prompt"].lower() or "ficticio" in p["system_prompt"].lower()


class TestFakeDataTts:
    def test_all_tts_have_demo_flag(self):
        data = json.loads((FAKE_DIR / "tts_samples.json").read_text())
        for t in data["tts_samples"]:
            assert t.get("demo") is True

    def test_tts_cover_all_clients(self):
        data = json.loads((FAKE_DIR / "tts_samples.json").read_text())
        scenarios = {t["client_scenario"] for t in data["tts_samples"]}
        expected = {"clinica", "juridico", "suporte", "educacao", "provedor-api"}
        assert scenarios == expected
