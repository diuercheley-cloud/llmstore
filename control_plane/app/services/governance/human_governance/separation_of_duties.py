def validate_separation_of_duties(requester_role: str, approver_roles: list[str]) -> bool:
    return requester_role not in approver_roles

