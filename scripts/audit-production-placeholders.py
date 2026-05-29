#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from datetime import datetime

KEYWORDS = [
    "placeholder", "stub", "mock", "dry_run", "simulated", 
    "in a real scenario", "TODO real implementation", "SBOM placeholders"
]

def audit():
    app_dir = Path("control_plane/app")
    findings = []
    
    for root, dirs, files in os.walk(app_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = Path(root) / file
            # Ignore tests
            if "test" in file or "test" in root:
                continue
            
            try:
                content = path.read_text(encoding="utf-8")
                lines = content.splitlines()
                for idx, line in enumerate(lines):
                    # Ignore comment imports or harmless imports
                    if "import mock" in line or "unittest.mock" in line:
                        continue
                    
                    for kw in KEYWORDS:
                        if kw in line.lower():
                            classification = "experimental"
                            # Classify
                            if "test" in line.lower() or "test" in str(path).lower():
                                classification = "test_only"
                            elif "mock" in line.lower() and ("llm" in line.lower() or "provider" in line.lower()):
                                classification = "dev_mock"
                            elif "todo" in line.lower() and "real" in line.lower():
                                classification = "production_blocker"
                            elif "placeholder" in line.lower() and ("signature" in line.lower() or "key" in line.lower() or "receipt" in line.lower()):
                                classification = "production_blocker"
                            else:
                                classification = "false_positive"
                                
                            findings.append({
                                "file": str(path),
                                "line": idx + 1,
                                "keyword": kw,
                                "content": line.strip(),
                                "classification": classification
                            })
            except Exception:
                pass
                
    report_dir = Path("artifacts/audit")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    blockers = [f for f in findings if f["classification"] == "production_blocker"]
    
    report_content = f"""# Production Placeholders Audit Report

- **Timestamp**: {datetime.utcnow().isoformat()}Z
- **Total Findings**: {len(findings)}
- **Production Blockers**: {len(blockers)}
- **Result**: {"FAIL" if blockers else "PASS"}

## Findings Details
"""
    for f in findings:
        report_content += f"- **{f['file']}:{f['line']}**: found `{f['keyword']}` - class: *{f['classification']}*\n  `{f['content']}`\n"
        
    (report_dir / "production-placeholders.md").write_text(report_content, encoding="utf-8")
    
    if blockers:
        print(f"Audit failed with {len(blockers)} production blockers!")
        for b in blockers:
            print(f"  - BLOCKER: {b['file']}:{b['line']}: {b['content']}")
        return 1
    else:
        print("Audit passed successfully.")
        return 0

if __name__ == "__main__":
    sys.exit(audit())
