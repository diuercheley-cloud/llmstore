
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import requests  # Need to add this to requirements.txt

from .verifier_core import Verifier
from .verifier_models import VerificationReport
from .verifier_reports import format_terminal_report, generate_json_report


def verify_file(file_path: str, export_path: str = None, gateway_url: str = None):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return False
    
    with open(file_path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: {file_path} is not a valid JSON")
            return False
    
    verifier = Verifier(data)
    verifier.run_all_checks()

    # Online Verification
    if gateway_url:
        print(f"\nPerforming online verification against {gateway_url}...")
        try:
            # 1. Verify Receipt
            if "receipt" in data:
                res = requests.post(f"{gateway_url}/verify/receipt", json={"receipt_hash": data["receipt"]["receipt_hash"]})
                if res.status_code == 200:
                    status = res.json().get("status", "unknown")
                    print(f"  [Online] Receipt Status: {status.upper()}")
                else:
                    print(f"  [Online] Receipt Error: {res.status_code}")
            
            # 2. Verify Timeline/Witness
            if "merkle_root" in data:
                res = requests.post(f"{gateway_url}/verify/witness-quorum", json={"merkle_root": data["merkle_root"]})
                if res.status_code == 200:
                    q_status = res.json().get("quorum_status", "unknown")
                    print(f"  [Online] Witness Quorum: {q_status.upper()}")
                else:
                    print(f"  [Online] Witness Error: {res.status_code}")
            if data.get("proof_type") == "retrieval" and data.get("proof_hash"):
                res = requests.post(f"{gateway_url}/verify/retrieval-proof", json={"proof_hash": data["proof_hash"]})
                if res.status_code == 200:
                    print(f"  [Online] Retrieval Proof: {res.json().get('status', 'unknown').upper()}")
                res = requests.post(f"{gateway_url}/verify/lineage-consistency", json={"proof_hash": data["proof_hash"]})
                if res.status_code == 200:
                    print(f"  [Online] Lineage Consistency: {res.json().get('status', 'unknown').upper()}")
                res = requests.post(f"{gateway_url}/verify/retrieval-replay", json={"proof_hash": data['proof_hash']})
                if res.status_code == 200:
                    print(f"  [Online] Retrieval Replay: {res.json().get('status', 'unknown').upper()}")
        except Exception as e:
            print(f"  [Online] Connection Failed: {str(e)}")
    
    report = VerificationReport(
        overall_status=verifier.get_overall_status(),
        proof_hash=verifier.proof.proof_hash,
        timeline_root=verifier.proof.timeline_root,
        verified_at=datetime.now(timezone.utc).isoformat(),
        checks=verifier.checks,
        warnings=verifier.warnings,
        errors=verifier.errors
    )
    
    format_terminal_report(report)
    
    if export_path:
        with open(export_path, "w") as f:
            f.write(generate_json_report(report))
        print(f"Report exported to {export_path}")
    
    return verifier.get_overall_status() == "VALID"

def verify_batch(directory: str):
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a directory")
        return
    
    files = [f for f in os.listdir(directory) if f.endswith(".json")]
    print(f"Batch verification of {len(files)} proofs in {directory}...")
    
    results = {"VALID": 0, "INVALID": 0, "PARTIAL": 0}
    for f in files:
        path = os.path.join(directory, f)
        print(f"\nProcessing {f}...")
        try:
            with open(path, "r") as jf:
                data = json.load(jf)
            v = Verifier(data)
            v.run_all_checks()
            status = v.get_overall_status()
            results[status] += 1
            print(f"Result: {status}")
        except Exception as e:
            print(f"Error processing {f}: {e}")
            results["INVALID"] += 1
            
    print("\n" + "=" * 30)
    print(" BATCH SUMMARY")
    print("=" * 30)
    for s, count in results.items():
        print(f"{s}: {count}")
    print("=" * 30)

def main():
    parser = argparse.ArgumentParser(description="Public Verifier CLI for Verifiable AI Execution Proofs")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify a single proof JSON file")
    verify_parser.add_argument("file", help="Path to the proof JSON file")
    verify_parser.add_argument("--export", help="Export report to JSON file")
    verify_parser.add_argument("--gateway-url", help="Verify online against an Attestation Gateway")
    
    # Online verify command (convenience alias)
    online_parser = subparsers.add_parser("verify-online", help="Verify a proof against a public gateway")
    online_parser.add_argument("file", help="Path to the proof JSON file")
    online_parser.add_argument("--gateway-url", required=True, help="Gateway URL (e.g., http://localhost:8080/attestation)")
    
    # Batch command
    batch_parser = subparsers.add_parser("verify-batch", help="Verify all JSON proofs in a directory")
    batch_parser.add_argument("dir", help="Directory containing proof JSON files")
    
    args = parser.parse_args()
    
    if args.command == "verify" or args.command == "verify-online":
        gateway = getattr(args, "gateway_url", None)
        success = verify_file(args.file, args.export, gateway_url=gateway)
        sys.exit(0 if success else 1)
    elif args.command == "verify-batch":
        verify_batch(args.dir)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
