from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog, User


def test_valid_login_redirects_to_dashboard(app, login, respondent_user):
    response = login(respondent_user.email)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    with app.app_context():
        user = db.session.scalar(select(User).where(User.id == respondent_user.id))
        assert user.last_login_at is not None
        assert db.session.scalar(
            select(AuditLog).where(AuditLog.action == "auth.login_succeeded")
        ) is not None


def test_invalid_credentials_do_not_reveal_user_existence(client, make_user):
    make_user("known@example.com")
    known = client.post(
        "/auth/login",
        data={"email": "known@example.com", "password": "wrong"},
        follow_redirects=True,
    )
    unknown = client.post(
        "/auth/login",
        data={"email": "missing@example.com", "password": "wrong"},
        follow_redirects=True,
    )
    assert known.status_code == unknown.status_code == 200
    assert b"Credenciales inv" in known.data
    assert b"Credenciales inv" in unknown.data


def test_account_is_temporarily_locked_after_threshold(app, client, make_user):
    user = make_user("locked@example.com")
    for _ in range(3):
        response = client.post(
            "/auth/login",
            data={"email": user.email, "password": "wrong"},
            follow_redirects=True,
        )
    assert b"temporalmente bloqueada" in response.data
    with app.app_context():
        persisted = db.session.get(User, user.id)
        assert persisted.locked_until is not None


def test_initial_password_change_is_enforced(client, login, make_user):
    user = make_user("change@example.com", must_change_password=True)
    response = login(user.email)
    assert response.status_code == 302
    assert "/auth/change-password" in response.headers["Location"]


def test_logout_requires_post_and_clears_session(client, login, respondent_user):
    login(respondent_user.email)
    assert client.get("/auth/logout").status_code == 405
    response = client.post("/auth/logout")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
