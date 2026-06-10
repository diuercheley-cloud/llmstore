from app.services.governance.human_governance.approval_quorum_service import normalize_roles
from app.services.governance.human_governance.separation_of_duties import (
    validate_separation_of_duties,
)


def test_human_governance_normalizes_roles():
    assert normalize_roles(["admin", "reviewer", "admin"]) == "[\"admin\", \"reviewer\"]"


def test_human_governance_separation_of_duties():
    assert validate_separation_of_duties("requester", ["approver", "reviewer"]) is True
    assert validate_separation_of_duties("requester", ["requester"]) is False

