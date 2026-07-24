from __future__ import annotations

from app.common.errors import ConflictError, ValidationError
from app.common.validators import is_valid_email, normalize_email
from app.extensions import db
from app.models import Role, User, UserRole
from app.repositories.users import user_repository
from app.services.audit_service import audit_service
from app.services.auth_service import auth_service


class UserService:
    def create_user(
        self,
        *,
        display_name: str,
        email: str,
        password: str,
        role_ids: list[int],
        actor_id: int | None,
        is_active: bool = True,
        must_change_password: bool = True,
    ) -> User:
        if not display_name.strip():
            raise ValidationError("El nombre del usuario es obligatorio.")
        if not role_ids:
            raise ValidationError("Debes asignar al menos un rol.")
        normalized = normalize_email(email)
        if not is_valid_email(normalized):
            raise ValidationError("El correo electrónico no es válido.")
        if user_repository.get_by_email(normalized):
            raise ConflictError("Ya existe un usuario con ese correo electrónico.")
        roles = user_repository.roles_by_ids(role_ids)
        if len(roles) != len(set(role_ids)):
            raise ValidationError("Uno o más roles seleccionados no son válidos.")
        try:
            password_hash = auth_service.hash_password(password)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        user = User(
            display_name=display_name.strip(),
            email=email.strip(),
            email_normalized=normalized,
            password_hash=password_hash,
            is_active=is_active,
            must_change_password=must_change_password,
        )
        db.session.add(user)
        db.session.flush()
        user.role_links = [
            UserRole(user_id=user.id, role_id=role.id, assigned_by_id=actor_id)
            for role in roles
        ]
        audit_service.record(
            action="user.created",
            entity_type="user",
            entity_public_id=user.public_id,
            actor_user_id=actor_id,
            after={
                "display_name": user.display_name,
                "email": user.email,
                "roles": sorted(role.code for role in roles),
                "is_active": user.is_active,
            },
        )
        db.session.commit()
        return user

    def update_user(
        self,
        user: User,
        *,
        display_name: str,
        email: str,
        role_ids: list[int],
        is_active: bool,
        must_change_password: bool,
        actor_id: int,
    ) -> User:
        if not display_name.strip():
            raise ValidationError("El nombre del usuario es obligatorio.")
        if not role_ids:
            raise ValidationError("Debes asignar al menos un rol.")
        normalized = normalize_email(email)
        if not is_valid_email(normalized):
            raise ValidationError("El correo electrónico no es válido.")
        existing = user_repository.get_by_email(normalized)
        if existing and existing.id != user.id:
            raise ConflictError("Ya existe un usuario con ese correo electrónico.")
        roles = user_repository.roles_by_ids(role_ids)
        if len(roles) != len(set(role_ids)):
            raise ValidationError("Uno o más roles seleccionados no son válidos.")
        if user.id == actor_id and not is_active:
            raise ValidationError("No puedes desactivar tu propia cuenta.")
        if user.id == actor_id and not any(role.code == "admin" for role in roles):
            raise ValidationError("No puedes quitarte el rol administrador.")

        before = {
            "display_name": user.display_name,
            "email": user.email,
            "roles": sorted(user.role_codes),
            "is_active": user.is_active,
            "must_change_password": user.must_change_password,
        }
        user.display_name = display_name.strip()
        user.email = email.strip()
        user.email_normalized = normalized
        user.is_active = is_active
        user.must_change_password = must_change_password
        user.role_links.clear()
        db.session.flush()
        user.role_links = [
            UserRole(user_id=user.id, role_id=role.id, assigned_by_id=actor_id)
            for role in roles
        ]
        audit_service.record(
            action="user.updated",
            entity_type="user",
            entity_public_id=user.public_id,
            actor_user_id=actor_id,
            before=before,
            after={
                "display_name": user.display_name,
                "email": user.email,
                "roles": sorted(role.code for role in roles),
                "is_active": user.is_active,
                "must_change_password": user.must_change_password,
            },
        )
        db.session.commit()
        return user

    def reset_password(self, user: User, password: str, actor_id: int) -> None:
        try:
            user.password_hash = auth_service.hash_password(password)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        user.must_change_password = True
        user.failed_login_count = 0
        user.locked_until = None
        audit_service.record(
            action="user.password_reset",
            entity_type="user",
            entity_public_id=user.public_id,
            actor_user_id=actor_id,
        )
        db.session.commit()


user_service = UserService()
