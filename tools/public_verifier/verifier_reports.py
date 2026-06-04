
from .verifier_models import VerificationReport


def format_terminal_report(report: VerificationReport):
    colors = {
        "VALID": "\033[92m",
        "INVALID": "\033[91m",
        "WARNING": "\033[93m",
        "PARTIAL": "\033[93m",
        "RESET": "\033[0m"
    }
    
    print("=" * 60)
    print(f" Verification Report - {report.verified_at}")
    print("=" * 60)
    print(f"Proof Hash: {report.proof_hash}")
    print(f"Timeline Root: {report.timeline_root}")
    print("-" * 60)
    
    for check in report.checks:
        status_color = colors.get(check.status, "")
        reset = colors["RESET"]
        print(f"[{status_color}{check.status}{reset}] {check.name}")
        print(f"    {check.message}")
        if "Witness Quorum" in check.name and check.status != "SKIP":
            print("    Details: Multi-party verification enabled")
    
    print("-" * 60)
    overall_color = colors.get(report.overall_status, "")
    reset = colors["RESET"]
    print(f"OVERALL STATUS: {overall_color}{report.overall_status}{reset}")
    print("=" * 60)

def generate_json_report(report: VerificationReport) -> str:
    return report.model_dump_json(indent=2)
