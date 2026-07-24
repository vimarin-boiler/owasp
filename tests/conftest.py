from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models import Role, User, UserRole
from app.services.auth_service import auth_service


@pytest.fixture()
def app(tmp_path: Path):
    database_path = tmp_path / "test.db"
    upload_path = tmp_path / "uploads"
    application = create_app(
        "testing",
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "UPLOAD_FOLDER": str(upload_path),
            "RATELIMIT_ENABLED": False,
            "SERVER_NAME": "localhost",
        },
    )
    with application.app_context():
        db.create_all()
        roles = {
            code: Role(code=code, name=name, description=description, is_system=True)
            for code, name, description in (
                ("admin", "Administrador", "Administración global."),
                ("respondent", "Respondedor", "Responde assessments."),
                ("reviewer", "Revisor", "Revisa assessments."),
            )
        }
        db.session.add_all(roles.values())
        db.session.commit()
        application.extensions["test_roles"] = roles
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def roles(app):
    return app.extensions["test_roles"]


@pytest.fixture()
def make_user(app, roles):
    def factory(
        email: str,
        *,
        display_name: str = "Usuario de prueba",
        password: str = "Secure-Test-9!",
        role_codes: tuple[str, ...] = ("respondent",),
        must_change_password: bool = False,
        is_active: bool = True,
    ) -> User:
        user = User(
            display_name=display_name,
            email=email,
            email_normalized=email.casefold(),
            password_hash=auth_service.hash_password(password),
            must_change_password=must_change_password,
            is_active=is_active,
        )
        db.session.add(user)
        db.session.flush()
        for code in role_codes:
            user.role_links.append(UserRole(user_id=user.id, role_id=roles[code].id))
        db.session.commit()
        return user

    return factory


@pytest.fixture()
def login(client):
    def perform(email: str, password: str = "Secure-Test-9!", follow_redirects: bool = False):
        return client.post(
            "/auth/login",
            data={"email": email, "password": password, "remember": "y"},
            follow_redirects=follow_redirects,
        )

    return perform


@pytest.fixture()
def admin_user(make_user):
    return make_user(
        "admin@example.com",
        display_name="Administrador",
        role_codes=("admin",),
    )


@pytest.fixture()
def respondent_user(make_user):
    return make_user(
        "respondent@example.com",
        display_name="Respondedor",
        role_codes=("respondent",),
    )
