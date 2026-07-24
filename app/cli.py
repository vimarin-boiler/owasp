from __future__ import annotations

import click
from pathlib import Path
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import select

from app.common.errors import DomainError
from app.common.validators import normalize_email
from config import validate_runtime_config
from app.extensions import db
from app.models import Assessment, Organization, QuestionnaireVersion, Role, User, UserRole
from app.services.auth_service import auth_service
from app.services.samm_import_service import catalog_import_service
from app.services.assessment_service import assessment_service
from app.enums import AssessmentStatus, QuestionnaireStatus, ScoringSource

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
    app.cli.add_command(import_samm)


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

    import_file = current_app.config.get("SAMM_IMPORT_FILE", "").strip()
    has_version = db.session.scalar(select(QuestionnaireVersion.id).limit(1))
    if import_file and not has_version:
        source = Path(import_file)
        if not source.is_absolute():
            source = Path(current_app.root_path).parent / source
        if not source.is_file():
            raise click.ClickException(f"SAMM_IMPORT_FILE no existe: {source}")
        record = catalog_import_service.create_preview_from_path(source, actor_id=admin.id)
        if record.status.value == "invalid":
            raise click.ClickException("El cuestionario SAMM configurado contiene errores de validación.")
        version_number = record.source_version or current_app.config["SAMM_DEFAULT_VERSION"]
        version = catalog_import_service.confirm(
            record,
            version_name=f"OWASP SAMM {version_number}",
            version_number=version_number,
            description=f"Versión inicial importada desde {record.source_name}.",
            publish=True,
            actor_id=admin.id,
        )
        click.echo(f"Cuestionario SAMM importado y publicado: {version.version_number}")
    elif has_version:
        click.echo("El catálogo SAMM ya contiene una versión; se omitió la importación inicial.")

    if current_app.config.get("CREATE_DEMO_DATA", False):
        respondent_password = current_app.config.get("DEMO_RESPONDENT_PASSWORD", "")
        reviewer_password = current_app.config.get("DEMO_REVIEWER_PASSWORD", "")
        if not respondent_password or not reviewer_password:
            raise click.ClickException(
                "DEMO_RESPONDENT_PASSWORD y DEMO_REVIEWER_PASSWORD son obligatorias cuando CREATE_DEMO_DATA=true."
            )

        def ensure_demo_user(name: str, email_value: str, password_value: str, role_code: str) -> User:
            normalized_email = normalize_email(email_value)
            user = db.session.scalar(select(User).where(User.email_normalized == normalized_email))
            if user is None:
                user = User(
                    display_name=name,
                    email=email_value,
                    email_normalized=normalized_email,
                    password_hash=auth_service.hash_password(password_value),
                    must_change_password=True,
                    is_active=True,
                )
                db.session.add(user)
                db.session.flush()
                user.role_links.append(UserRole(user_id=user.id, role_id=roles[role_code].id, assigned_by_id=admin.id))
                click.echo(f"Usuario demo creado: {user.email}")
            elif not user.has_role(role_code):
                user.role_links.append(UserRole(user_id=user.id, role_id=roles[role_code].id, assigned_by_id=admin.id))
            return user

        respondent = ensure_demo_user(
            current_app.config["DEMO_RESPONDENT_NAME"],
            current_app.config["DEMO_RESPONDENT_EMAIL"],
            respondent_password,
            "respondent",
        )
        reviewer = ensure_demo_user(
            current_app.config["DEMO_REVIEWER_NAME"],
            current_app.config["DEMO_REVIEWER_EMAIL"],
            reviewer_password,
            "reviewer",
        )
        db.session.commit()

        published_version = db.session.scalar(
            select(QuestionnaireVersion)
            .where(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED)
            .order_by(QuestionnaireVersion.published_at.desc())
        )
        demo_assessment = db.session.scalar(
            select(Assessment).where(Assessment.organization_id == demo.id, Assessment.name == "Assessment SAMM Demo")
        )
        if published_version and demo_assessment is None:
            from app.repositories.catalog import catalog_repository
            detailed_version = catalog_repository.questionnaire_version_by_public_id(published_version.public_id)
            demo_assessment = assessment_service.create(
                organization_id=demo.id,
                questionnaire_version=detailed_version,
                name="Assessment SAMM Demo",
                description="Evaluación demostrativa creada durante la inicialización.",
                scope="Alcance de demostración para validar el flujo de respuestas y revisión.",
                start_date=None,
                target_date=None,
                target_maturity_level="2",
                scoring_source=ScoringSource.APPROVED,
                respondent_ids=[respondent.id],
                reviewer_ids=[reviewer.id],
                actor_id=admin.id,
            )
            assessment_service.transition(demo_assessment, AssessmentStatus.IN_PROGRESS, admin.id)
            click.echo("Assessment de demostración creado e iniciado.")
        elif published_version is None:
            click.echo("No hay una versión publicada; se omitió el assessment de demostración.")

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


@click.command("import-samm")
@click.option("--file", "file_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=__import__("pathlib").Path), help="Archivo SAMM .xlsx.")
@click.option("--name", "version_name", default=None, help="Nombre de la versión a crear.")
@click.option("--version", "version_number", default=None, help="Número de versión único.")
@click.option("--description", default=None, help="Descripción de la versión.")
@click.option("--publish/--draft", default=False, help="Publicar la versión al terminar.")
@click.option("--dry-run", is_flag=True, help="Solo valida y muestra el resumen.")
@with_appcontext
def import_samm(file_path, version_name: str | None, version_number: str | None, description: str | None, publish: bool, dry_run: bool) -> None:
    """Valida e importa un cuestionario OWASP SAMM desde Excel."""
    actor = db.session.scalar(select(User).join(UserRole).join(Role).where(Role.code == "admin").order_by(User.id))
    record = catalog_import_service.create_preview_from_path(file_path, actor_id=actor.id if actor else None)
    summary = record.summary_json
    click.echo(f"Archivo: {record.source_name}")
    click.echo(f"SHA-256: {record.source_file_hash}")
    click.echo(f"Funciones: {summary.get('business_functions', 0)}")
    click.echo(f"Prácticas: {summary.get('security_practices', 0)}")
    click.echo(f"Flujos: {summary.get('practice_streams', 0)}")
    click.echo(f"Niveles: {summary.get('maturity_levels', 0)}")
    click.echo(f"Preguntas: {summary.get('questions', 0)}")
    click.echo(f"Conjuntos de respuesta: {summary.get('answer_sets', 0)}")
    if record.errors_json:
        for issue in record.errors_json:
            location = f"{issue.get('sheet')}:{issue.get('row')}" if issue.get('row') else issue.get('sheet')
            click.echo(f"[{issue.get('severity', 'error').upper()}] {location} - {issue.get('message')}")
    if record.status.value == "invalid":
        raise click.ClickException("El archivo contiene errores y no fue importado.")
    if dry_run:
        click.echo("Validación completada; no se modificó el catálogo.")
        return
    resolved_version = version_number or record.source_version or current_app.config["SAMM_DEFAULT_VERSION"]
    resolved_name = version_name or f"OWASP SAMM {resolved_version}"
    try:
        version = catalog_import_service.confirm(
            record,
            version_name=resolved_name,
            version_number=resolved_version,
            description=description or f"Importada desde {record.source_name}.",
            publish=publish,
            actor_id=actor.id if actor else None,
        )
    except (DomainError, ValueError, OSError) as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - protección de último recurso
        current_app.logger.exception("CLI SAMM import failed", exc_info=exc)
        raise click.ClickException(
            "Ocurrió un error interno durante la importación. Consulta los logs de la aplicación."
        ) from exc
    click.echo(f"Versión creada: {version.version_number} ({version.status.value})")
