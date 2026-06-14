import pytest
from pydantic import ValidationError

from app.schemas.public import PublicSignupRequest


def valid_payload(**overrides):
    payload = {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "company": "Example",
        "plan_code": "free",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "field,value",
    [
        ("full_name", "x" * 121),
        ("email", f"{'x' * 65}@example.com"),
        ("company", "x" * 121),
        ("use_case", "x" * 501),
        ("full_name", "Jane\x00Doe"),
    ],
)
def test_signup_rejects_oversized_or_unsafe_fields(field, value):
    with pytest.raises(ValidationError):
        PublicSignupRequest(**valid_payload(**{field: value}))


def test_signup_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        PublicSignupRequest(**valid_payload(unexpected="database filler"))


def test_signup_normalizes_bounded_fields():
    payload = PublicSignupRequest(**valid_payload(full_name="  Jane Doe  ", email="  JANE@EXAMPLE.COM  "))
    assert payload.full_name == "Jane Doe"
    assert payload.email == "jane@example.com"
