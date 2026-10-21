

def test_new_accounts_need_a_real_email_and_a_password_with_letter_number_and_symbol():
    import pytest
    from pydantic import ValidationError

    from app.schemas.auth import PasswordResetConfirm, RegisterRequest

    assert RegisterRequest(email=" Me@Example.com ", password="study-hard-1").email == "me@example.com"
    for email, password in [("me@example", "study-hard-1"), ("me@example.com", "studyhard1"),
                            ("me@example.com", "study-hard!")]:
        with pytest.raises(ValidationError):
            RegisterRequest(email=email, password=password)
    with pytest.raises(ValidationError):
        PasswordResetConfirm(email="me@example.com", token="t" * 12, new_password="password")
