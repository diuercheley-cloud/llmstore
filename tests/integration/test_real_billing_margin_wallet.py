import json
import subprocess


def test_wallet_deduction(tmp_path):
    out_dir = tmp_path / "billing"
    res = subprocess.run([
        "./scripts/validators/validate-real-billing-margin.sh",
        "--dry-run",
        "--output-dir", str(out_dir)
    ], capture_output=True, text=True)
    assert res.returncode == 0
    
    runs = [d for d in out_dir.iterdir() if d.is_dir()]
    assert len(runs) == 1
    
    json_path = runs[0] / "billing-margin-report.json"
    with open(json_path) as f:
        data = json.load(f)
        before = data["wallet_balance_before_brl"]
        after = data["wallet_balance_after_brl"]
        price = data["financials"]["customer_price_brl"]
        assert after == before - price
        assert after >= 0
