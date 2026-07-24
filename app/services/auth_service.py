from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from flask import current_app

from app.common.validators import normalize_email, validate_password
from app.extensions import db
from app.models import User
from app.models.base import as_utc, utc_now
from app.repositories.users import user_repository
from app.services.audit_service import audit_service

password_hasher = PasswordHasher()
DUMMY_HASH = password_hasher.hash("Dummy-password-9!not-a-user")


@dataclass(frozen=True)
class AuthenticationResult:
    user: User | None
    error: str | None = None
    locked: bool = False


class AuthService:
    def hash_password(self, password: str) -> str:
        validation = validate_password(
            password, current_app.config.get("PASSWORD_MIN_LENGTH", 12)
        )
        if not validation.valid:
            raise ValueError(" ".join(validation.errors))
        return password_hasher.hash(password)

    def verify_password(self, password_hash: str, password: str) -> bool:
        try:
            return password_hasher.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    def authenticate(self, email: str, password: str) -> AuthenticationResult:
        normalized = normalize_email(email)
        user = user_repository.get_by_email(normalized)
        now = utc_now()

        if user is None:
            self.verify_password(DUMMY_HASH, password)
            audit_service.record(
                action="auth.login_failed",
                entity_type="user",
                after={"email": normalized, "reason": "invalid_credentials"},
                result="failure",
                error_code="INVALID_CREDENTIALS",
            )
            db.session.commit()
            return AuthenticationResult(None, "Credenciales inválidas.")

        if not user.is_active:
            audit_service.record(
                action="auth.login_failed",
                entity_type="user",
                entity_public_id=user.public_id,
                actor_user_id=None,
                after={"reason": "inactive_user"},
                result="failure",
                error_code="INACTIVE_USER",
            )
            db.session.commit()
            return AuthenticationResult(None, "Credenciales inválidas.")

        locked_until = as_utc(user.locked_until)
        if locked_until and locked_until > now:
            audit_service.record(
                action="auth.login_blocked",
                entity_type="user",
                entity_public_id=user.public_id,
                actor_user_id=None,
                after={"locked_until": locked_until.isoformat()},
                result="failure",
                error_code="ACCOUNT_LOCKED",
            )
            db.session.commit()
            return AuthenticationResult(
                None,
                "La cuenta está temporalmente bloqueada. Intenta más tarde.",
                locked=True,
            )

        if not self.verify_password(user.password_hash, password):
            user.failed_login_count += 1
            threshold = current_app.config.get("LOGIN_MAX_FAILED_ATTEMPTS", 5)
            locked = user.failed_login_count >= threshold
            if locked:
                user.locked_until = now + timedelta(
                    minutes=current_app.config.get("LOGIN_LOCKOUT_MINUTES", 15)
                )
                user.failed_login_count = 0
            audit_service.record(
                action="auth.login_failed",
                entity_type="user",
                entity_public_id=user.public_id,
                actor_user_id=None,
                after={"reason": "invalid_credentials", "locked": locked},
                result="failure",
                error_code="INVALID_CREDENTIALS",
            )
            db.session.commit()
            return AuthenticationResult(
                None,
                "La cuenta está temporalmente bloqueada. Intenta más tarde."
                if locked
                else "Credenciales inválidas.",
                locked=locked,
            )

        if password_hasher.check_needs_rehash(user.password_hash):
            user.password_hash = password_hasher.hash(password)
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now
        audit_service.record(
            action="auth.login_succeeded",
            entity_type="user",
            entity_public_id=user.public_id,
            actor_user_id=user.id,
        )
        db.session.commit()
        return AuthenticationResult(user)

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not self.verify_password(user.password_hash, current_password):
            raise ValueError("La contraseña actual no es correcta.")
        if self.verify_password(user.password_hash, new_password):
            raise ValueError("La nueva contraseña debe ser diferente a la actual.")
        user.password_hash = self.hash_password(new_password)
        user.must_change_password = False
        user.password_changed_at = utc_now()
        audit_service.record(
            action="auth.password_changed",
            entity_type="user",
            entity_public_id=user.public_id,
            actor_user_id=user.id,
        )
        db.session.commit()


auth_service = AuthService()
