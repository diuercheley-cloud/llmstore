from app.services.operations.remediation.approval_requirements import RemediationApprovalRequirementService

class TestRemediationApprovalRequirements:
    def test_executive_approval_for_critical(self):
        service = RemediationApprovalRequirementService()
        plan = {"risk_level": "critical", "blast_radius": "critical"}
        steps = []
        reqs = service.determine_required_approvals(plan, steps)
        assert any(r["approval_scope"] == "executive" for r in reqs)

    def test_technical_approval_for_irreversible(self):
        service = RemediationApprovalRequirementService()
        plan = {"risk_level": "low", "blast_radius": "low"}
        steps = [{"reversible": False}]
        reqs = service.determine_required_approvals(plan, steps)
        assert any(r["approval_scope"] == "technical_risk" for r in reqs)

    def test_no_approval_for_low_risk_reversible(self):
        service = RemediationApprovalRequirementService()
        plan = {"risk_level": "low", "blast_radius": "low"}
        steps = [{"reversible": True}]
        reqs = service.determine_required_approvals(plan, steps)
        assert len(reqs) == 0
