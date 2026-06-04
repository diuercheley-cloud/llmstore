import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINAL_VAL_BASE = ROOT / "artifacts" / "v1.7-final-validation"

def latest_final_val_dir():
    if not FINAL_VAL_BASE.exists():
        return None
    subdirs = sorted([d for d in FINAL_VAL_BASE.iterdir() if d.is_dir()])
    return subdirs[-1] if subdirs else None

def test_final_status_policy():
    d = latest_final_val_dir()
    if d is None:
        return
    
    report_json = d / "v1.7-final-validation.json"
    if not report_json.exists():
        return
        
    with open(report_json) as f:
        data = json.load(f)
        
    status = data.get("final_status")
    non_blocking_warns = data.get("nonblocking_warnings", 0)
    
    if non_blocking_warns > 0:
        # If there are warnings, it must be either WITH_WARNINGS or WITH_ACCEPTED_WARNINGS
        assert status in ("V1_7_READY_WITH_WARNINGS", "V1_7_READY_WITH_ACCEPTED_WARNINGS")
        
        # Verify the logic of ACCEPTED if it's the case
        if status == "V1_7_READY_WITH_ACCEPTED_WARNINGS":
            warn_list = data.get("nonblocking_warning_list", [])
            for warn in warn_list:
                accepted = any(x in warn for x in ["PSP", "PIX", "404", "Meeting-ready", "skipped", "DEMO_READY_WITH_WARNINGS"])
                assert accepted, f"Unaccepted warning found in ACCEPTED status: {warn}"
    else:
        assert status == "V1_7_READY"
