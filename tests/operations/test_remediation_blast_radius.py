from app.services.operations.remediation.blast_radius import RemediationBlastRadiusService

class TestRemediationBlastRadius:
    def test_calculate_blast_radius_low(self):
        service = RemediationBlastRadiusService()
        inputs = {"involved_domains": ["auth"], "risk_level": "low"}
        assert service.calculate_blast_radius(inputs) == "low"

    def test_calculate_blast_radius_critical(self):
        service = RemediationBlastRadiusService()
        inputs = {"involved_domains": ["auth"], "risk_level": "critical"}
        assert service.calculate_blast_radius(inputs) == "critical"

    def test_calculate_blast_radius_high_domain_count(self):
        service = RemediationBlastRadiusService()
        inputs = {"involved_domains": ["d1", "d2", "d3", "d4"], "risk_level": "low"}
        assert service.calculate_blast_radius(inputs) == "high"

    def test_explain_blast_radius(self):
        service = RemediationBlastRadiusService()
        inputs = {"involved_domains": ["auth"], "risk_level": "low"}
        explanation = service.explain_blast_radius(inputs)
        assert "low" in explanation.lower()
