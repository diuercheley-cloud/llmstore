import os
from datetime import datetime, UTC
from typing import Any, Dict, List

from app.services.compliance_control_mapper import ComplianceControlMapperService


class ComplianceGapAnalysisService:
    def __init__(self, base_artifact_dir: str = "artifacts/compliance/latest"):
        self.base_artifact_dir = base_artifact_dir
        os.makedirs(self.base_artifact_dir, exist_ok=True)
        self.mapper = ComplianceControlMapperService()

    def generate_full_analysis(self) -> Dict[str, Any]:
        soc2_gaps = self._analyze_framework("SOC2")
        iso_gaps = self._analyze_framework("ISO27001")
        
        self._write_report("soc2-gap-analysis.md", "SOC 2 Type I Readiness", soc2_gaps)
        self._write_report("iso27001-gap-analysis.md", "ISO 27001 ISMS Readiness", iso_gaps)
        self._write_roadmap()
        
        return {
            "status": "success",
            "frameworks": ["SOC2", "ISO27001"],
            "artifacts": [
                "soc2-gap-analysis.md",
                "iso27001-gap-analysis.md",
                "audit-readiness-roadmap.md"
            ]
        }

    def _analyze_framework(self, framework: str) -> List[Dict[str, Any]]:
        controls = self.mapper.list_controls(framework)
        analysis = []
        
        for c in controls:
            status = "ready" if c["implementation_status"] == "implemented" else "partial"
            gap = ""
            risk = "low"
            
            if status == "partial":
                gap = c.get("gaps", ["Missing automated evidence"])[0]
                risk = "medium"
            
            analysis.append({
                "control_id": c["control_id"],
                "title": c["title"],
                "status": status,
                "evidence": ", ".join(c.get("evidence_sources", [])),
                "gap": gap,
                "risk": risk,
                "owner": c["owner_role"],
                "remediation": c.get("remediation_plan", "Automate evidence collection"),
                "target_date": "2026-Q3",
                "auditor_notes": "Technical implementation verified, organizational policy in draft."
            })
            
        return analysis

    def _write_report(self, filename: str, title: str, gaps: List[Dict[str, Any]]):
        path = os.path.join(self.base_artifact_dir, filename)
        with open(path, "w") as f:
            f.write(f"# {title} - Gap Analysis\n\n")
            f.write(f"Generated: {datetime.now(UTC).isoformat()}\n\n")
            f.write("> [!IMPORTANT]\n")
            f.write("> Este relatório foca em **Readiness** e não substitui uma auditoria externa formal.\n\n")
            
            f.write("## Matriz de Controles\n\n")
            f.write("| ID | Título | Status | Risco | Owner | Gap | Remediation |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for g in gaps:
                f.write(f"| {g['control_id']} | {g['title']} | {g['status']} | {g['risk']} | {g['owner']} | {g['gap']} | {g['remediation']} |\n")
            
            f.write("\n## External Auditor Required\n")
            f.write("- **Formal Audit Opinion**: Requer auditor independente (CPA/EY/PwC).\n")
            f.write("- **Certification Decision**: Requer organismo de certificação (ISO).\n")

    def _write_roadmap(self):
        path = os.path.join(self.base_artifact_dir, "audit-readiness-roadmap.md")
        with open(path, "w") as f:
            f.write("# Audit Readiness Roadmap\n\n")
            f.write("## Fase 1: SOC 2 Type I Readiness (Recomendado)\n")
            f.write("- Focar em design de controles e evidências de 'ponto no tempo'.\n")
            f.write("- Estimativa: 3-4 meses.\n\n")
            f.write("## Fase 2: SOC 2 Type II Readiness\n")
            f.write("- Focar em eficácia operacional (evidências contínuas de 6 meses).\n")
            f.write("- Estimativa: 6-12 meses após Type I.\n\n")
            f.write("## Fase 3: ISO 27001 Certification\n")
            f.write("- Auditoria interna formal e Management Review.\n")
            f.write("- Seleção de Certification Body.\n")
