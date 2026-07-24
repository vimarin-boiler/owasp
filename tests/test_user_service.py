import pytest
from sqlalchemy import func, select

from app.common.errors import ConflictError, ValidationError
from app.extensions import db
from app.models import AuditLog, User
from app.services.user_service import user_service


def test_create_user_assigns_roles_and_audits(app, admin_user, roles):
    with app.app_context():
        user = user_service.create_user(
            display_name="Nuevo Respondedor",
            email="new@example.com",
            password="Another-Secure-9!",
            role_ids=[roles["respondent"].id],
            actor_id=admin_user.id,
        )
        assert user.has_role("respondent")
        assert user.must_change_password is True
        assert db.session.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.action == "user.created")
        ) == 1


def test_create_user_rejects_duplicate_email(app, admin_user, respondent_user, roles):
    with app.app_context():
        with pytest.raises(ConflictError):
            user_service.create_user(
                display_name="Duplicado",
                email=respondent_user.email.upper(),
                password="Another-Secure-9!",
                role_ids=[roles["respondent"].id],
                actor_id=admin_user.id,
            )


def test_admin_cannot_deactivate_own_account(app, admin_user, roles):
    with app.app_context():
        user = db.session.get(User, admin_user.id)
        with pytest.raises(ValidationError):
            user_service.update_user(
                user,
                display_name=user.display_name,
                email=user.email,
                role_ids=[roles["admin"].id],
                is_active=False,
                must_change_password=False,
                actor_id=user.id,
            )
