from __future__ import annotations

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import select

from app.common.validators import normalize_email
from config import validate_runtime_config
from app.extensions import db
from app.models import Organization, Role, User, UserRole
from app.services.auth_service import auth_service

ROLE_SEED = (
    ("admin", "Administrador", "Administración global de la plataforma."),
    ("respondent", "Respondedor", "Responde assessments asignados."),
    ("reviewer", "Revisor", "Revisa respuestas y evidencias asignadas."),
)


def _seed_roles() -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for code, name, description in ROLE_SEED:
        role = db.session.scalar(select(Role).where(Role.code == code))
        if role is None:
            role = Role(code=code, name=name, description=description, is_system=True)
            db.session.add(role)
            db.session.flush()
        roles[code] = role
    return roles


def register_cli(app) -> None:
    app.cli.add_command(seed)
    app.cli.add_command(create_admin)
    app.cli.add_command(check_config)


@click.command("seed")
@with_appcontext
def seed() -> None:
    """Crea roles, administrador inicial y organización de demostración."""
    roles = _seed_roles()
    email = normalize_email(current_app.config["INITIAL_ADMIN_EMAIL"])
    password = current_app.config.get("INITIAL_ADMIN_PASSWORD", "")
    if not password:
        raise click.ClickException(
            "INITIAL_ADMIN_PASSWORD es obligatoria para ejecutar el seed."
        )

    admin = db.session.scalar(select(User).where(User.email_normalized == email))
    if admin is None:
        admin = User(
            display_name=current_app.config["INITIAL_ADMIN_NAME"],
            email=current_app.config["INITIAL_ADMIN_EMAIL"],
            email_normalized=email,
            password_hash=auth_service.hash_password(password),
            must_change_password=True,
            is_active=True,
        )
        db.session.add(admin)
        db.session.flush()
        admin.role_links.append(UserRole(user_id=admin.id, role_id=roles["admin"].id))
        click.echo(f"Administrador creado: {admin.email}")
    elif not admin.has_role("admin"):
        admin.role_links.append(UserRole(user_id=admin.id, role_id=roles["admin"].id))
        click.echo(f"Rol administrador asignado a: {admin.email}")
    else:
        click.echo(f"Administrador existente: {admin.email}")

    demo = db.session.scalar(select(Organization).where(Organization.slug == "organizacion-demo"))
    if demo is None:
        demo = Organization(
            name="Organización Demo",
            slug="organizacion-demo",
            description="Organización inicial para validación de la plataforma.",
            created_by_id=admin.id,
            updated_by_id=admin.id,
        )
        db.session.add(demo)
        click.echo("Organización de demostración creada.")

    db.session.commit()
    click.echo("Seed completado correctamente.")


@click.command("create-admin")
@click.option("--name", prompt="Nombre", help="Nombre visible del administrador.")
@click.option("--email", prompt="Correo", help="Correo del administrador.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Contraseña temporal.",
)
@with_appcontext
def create_admin(name: str, email: str, password: str) -> None:
    """Crea un administrador mediante la consola."""
    roles = _seed_roles()
    normalized = normalize_email(email)
    existing = db.session.scalar(select(User).where(User.email_normalized == normalized))
    if existing:
        raise click.ClickException("Ya existe un usuario con ese correo.")
    try:
        password_hash = auth_service.hash_password(password)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    admin = User(
        display_name=name.strip(),
        email=email.strip(),
        email_normalized=normalized,
        password_hash=password_hash,
        must_change_password=True,
        is_active=True,
    )
    db.session.add(admin)
    db.session.flush()
    admin.role_links.append(UserRole(user_id=admin.id, role_id=roles["admin"].id))
    db.session.commit()
    click.echo(f"Administrador creado: {admin.email}")


@click.command("check-config")
@with_appcontext
def check_config() -> None:
    """Valida la configuración crítica sin mostrar secretos."""
    validate_runtime_config(current_app.config)
    click.echo(f"Aplicación: {current_app.config['APP_NAME']}")
    click.echo(f"Base de datos: {current_app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}")
    click.echo(f"Uploads: {current_app.config['UPLOAD_FOLDER']}")
    click.echo("Configuración válida.")
