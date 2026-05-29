from __future__ import annotations


def validate_separation_of_duties(requester_role: str, reviewer_roles: list[str]) -> bool:
    requester = requester_role.strip()
    normalized_reviewers = {role.strip() for role in reviewer_roles if role.strip()}
    return requester not in normalized_reviewers
