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
            "CATALOG_IMPORT_FOLDER": str(tmp_path / "catalog_imports"),
            "REPORT_FOLDER": str(tmp_path / "reports"),
            "BACKUP_FOLDER": str(tmp_path / "backups"),
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

@pytest.fixture()
def reviewer_user(make_user):
    return make_user(
        "reviewer@example.com",
        display_name="Revisor",
        role_codes=("reviewer",),
    )

@pytest.fixture()
def phase4_catalog(admin_user):
    from decimal import Decimal
    from app.enums import QuestionRevisionStatus, QuestionnaireStatus
    from app.models import (
        AnswerOption,
        AnswerSet,
        BusinessFunction,
        MaturityLevel,
        Organization,
        PracticeStream,
        Question,
        QuestionnaireVersion,
        QuestionnaireVersionQuestion,
        QuestionQualityCriterion,
        QuestionRevision,
        SecurityPractice,
    )

    organization = Organization(
        name="Cliente Fase 4",
        slug="cliente-fase-4-fixture",
        created_by_id=admin_user.id,
        updated_by_id=admin_user.id,
    )
    function = BusinessFunction(code="GOV-FIX", name="Governance", sort_order=1)
    practice = SecurityPractice(code="SM-FIX", name="Strategy & Metrics", business_function=function, sort_order=1)
    stream = PracticeStream(code="A-FIX", name="Stream A", security_practice=practice, sort_order=1)
    level = MaturityLevel(level_number=1, name="Nivel 1", max_score=Decimal("1"), sort_order=1)
    answer_set = AnswerSet(external_code="AS-FIX", name="Respuesta prueba", content_hash="c" * 64)
    answer_set.options.extend([
        AnswerOption(option_code="NO", text="No implementado", weight=Decimal("0"), sort_order=1),
        AnswerOption(option_code="YES", text="Implementado", weight=Decimal("1"), sort_order=2),
    ])
    question = Question(external_code="G-SM-A-1-FIX", canonical_name="Pregunta prueba", current_revision_number=1)
    revision = QuestionRevision(
        question=question,
        revision_number=1,
        business_function=function,
        security_practice=practice,
        practice_stream=stream,
        maturity_level=level,
        answer_set=answer_set,
        question_text="¿Existe una estrategia de seguridad medible?",
        guidance_text="Revisar estrategia aprobada.",
        content_hash="d" * 64,
        status=QuestionRevisionStatus.PUBLISHED,
    )
    revision.criteria.append(QuestionQualityCriterion(criterion_text="Aprobada por la dirección", sort_order=1))
    version = QuestionnaireVersion(
        name="SAMM Test Fixture",
        version_number="test-fixture-4.0",
        status=QuestionnaireStatus.PUBLISHED,
        created_by_id=admin_user.id,
        updated_by_id=admin_user.id,
    )
    version.question_links.append(QuestionnaireVersionQuestion(question_revision=revision, sort_order=1, is_required=True))
    db.session.add_all([organization, function, practice, stream, level, answer_set, question, version])
    db.session.commit()
    return organization, version


@pytest.fixture()
def phase4_assessment(phase4_catalog, admin_user, respondent_user, reviewer_user):
    from app.enums import AssessmentStatus, ScoringSource
    from app.repositories.assessments import assessment_repository
    from app.repositories.catalog import catalog_repository
    from app.services.assessment_service import assessment_service

    organization, version_summary = phase4_catalog
    version = catalog_repository.questionnaire_version_by_public_id(version_summary.public_id)
    assessment = assessment_service.create(
        organization_id=organization.id,
        questionnaire_version=version,
        name="Assessment de prueba",
        description="Prueba de flujo",
        scope="Aplicación crítica",
        start_date=None,
        target_date=None,
        target_maturity_level="2",
        scoring_source=ScoringSource.APPROVED,
        respondent_ids=[respondent_user.id],
        reviewer_ids=[reviewer_user.id],
        actor_id=admin_user.id,
    )
    assessment_service.transition(assessment, AssessmentStatus.IN_PROGRESS, admin_user.id)
    return assessment_repository.get_by_public_id(assessment.public_id)
