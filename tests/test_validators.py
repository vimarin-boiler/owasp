from app.common.validators import normalize_email, slugify, validate_password


def test_normalize_email_is_case_insensitive_and_trimmed():
    assert normalize_email("  User.Name@Example.COM ") == "user.name@example.com"


def test_slugify_removes_accents_and_unsafe_characters():
    assert slugify("Compañía de Crédito & Riesgo") == "compania-de-credito-riesgo"


def test_password_policy_accepts_strong_password():
    result = validate_password("Strong-Password-9!", min_length=12)
    assert result.valid is True
    assert result.errors == ()


def test_password_policy_reports_all_missing_requirements():
    result = validate_password("weak", min_length=12)
    assert result.valid is False
    assert len(result.errors) >= 3
