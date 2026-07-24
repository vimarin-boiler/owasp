from __future__ import annotations

from decimal import Decimal
from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from app.common.assessment_access import can_respond, can_review, can_view_assessment
from app.common.errors import ConflictError
from app.enums import (
    AssessmentStatus,
    EvidenceValidationStatus,
    QuestionRevisionStatus,
    QuestionnaireStatus,
    ResponseStatus,
    ReviewDecision,
    ScoringSource,
)
from app.extensions import db
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
from app.repositories.assessments import assessment_repository
from app.services.assessment_service import assessment_service
from app.services.evidence_service import evidence_service
from app.services.response_service import response_service
from app.services.review_service import review_service


@pytest.fixture()
def published_questionnaire(admin_user):
    organization = Organization(
        name="Cliente Fase 4",
        slug="cliente-fase-4",
        created_by_id=admin_user.id,
        updated_by_id=admin_user.id,
    )
    function = BusinessFunction(code="GOV", name="Governance", sort_order=1)
    practice = SecurityPractice(code="SM", name="Strategy & Metrics", business_function=function, sort_order=1)
    stream = PracticeStream(code="A", name="Stream A", security_practice=practice, sort_order=1)
    level = MaturityLevel(level_number=1, name="Nivel 1", max_score=Decimal("1"), sort_order=1)
    answer_set = AnswerSet(external_code="AS-TEST", name="Respuesta prueba", content_hash="a" * 64)
    answer_set.options.extend(
        [
            AnswerOption(option_code="NO", text="No implementado", weight=Decimal("0"), sort_order=1),
            AnswerOption(option_code="YES", text="Implementado", weight=Decimal("1"), sort_order=2),
        ]
    )
    question = Question(external_code="G-SM-A-1-TEST", canonical_name="Pregunta prueba", current_revision_number=1)
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
        content_hash="b" * 64,
        status=QuestionRevisionStatus.PUBLISHED,
    )
    revision.criteria.append(QuestionQualityCriterion(criterion_text="Aprobada por la dirección", sort_order=1))
    version = QuestionnaireVersion(
        name="SAMM Test",
        version_number="test-4.0",
        status=QuestionnaireStatus.PUBLISHED,
        created_by_id=admin_user.id,
        updated_by_id=admin_user.id,
    )
    version.question_links.append(QuestionnaireVersionQuestion(question_revision=revision, sort_order=1, is_required=True))
    db.session.add_all([organization, function, practice, stream, level, answer_set, question, version])
    db.session.commit()
    return organization, version


@pytest.fixture()
def phase4_assessment(published_questionnaire, admin_user, respondent_user, reviewer_user):
    organization, version_summary = published_questionnaire
    from app.repositories.catalog import catalog_repository

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


def test_assessment_creation_snapshots_catalog(phase4_assessment):
    assessment = phase4_assessment
    assert assessment.status == AssessmentStatus.IN_PROGRESS
    assert len(assessment.questions) == 1
    snapshot = assessment.questions[0]
    assert snapshot.external_code_snapshot == "G-SM-A-1-TEST"
    assert snapshot.question_text_snapshot.startswith("¿Existe")
    assert snapshot.criteria_snapshot[0]["text"] == "Aprobada por la dirección"
    assert snapshot.answer_options_snapshot[1]["weight"] == "1.0000"


def test_assignment_based_access_isolated(phase4_assessment, respondent_user, reviewer_user, make_user):
    outsider = make_user("outsider@example.com", role_codes=("respondent",))
    assert can_view_assessment(respondent_user, phase4_assessment)
    assert can_respond(respondent_user, phase4_assessment)
    assert can_review(reviewer_user, phase4_assessment)
    assert not can_view_assessment(outsider, phase4_assessment)
    assert not can_respond(outsider, phase4_assessment)


def test_response_submit_review_and_reopen(phase4_assessment, respondent_user, reviewer_user):
    question = phase4_assessment.questions[0]
    response = response_service.save(
        question,
        actor_id=respondent_user.id,
        selected_option_code="YES",
        respondent_comment="Existe una estrategia formal.",
        is_not_applicable=False,
        not_applicable_justification=None,
        intent="submit",
    )
    assert response.status == ResponseStatus.SUBMITTED
    assert response.selected_weight_snapshot == Decimal("1")
    assert len(response.history) == 1

    response = review_service.decide(
        response,
        decision=ReviewDecision.OBSERVED,
        comment="Adjuntar aprobación del directorio.",
        reviewer_id=reviewer_user.id,
    )
    assert response.status == ResponseStatus.OBSERVED
    assert phase4_assessment.status == AssessmentStatus.OBSERVED

    response = response_service.save(
        question,
        actor_id=respondent_user.id,
        selected_option_code="YES",
        respondent_comment="Se adjunta la aprobación requerida.",
        is_not_applicable=False,
        not_applicable_justification=None,
        intent="submit",
    )
    response = review_service.decide(
        response,
        decision=ReviewDecision.APPROVED,
        comment="Evidencia suficiente.",
        reviewer_id=reviewer_user.id,
    )
    assert response.status == ResponseStatus.APPROVED
    assert len(response.reviews) == 2
    assert len(response.history) == 4

    response = review_service.reopen(
        response,
        comment="Se requiere reevaluación por cambio de alcance.",
        reviewer_id=reviewer_user.id,
    )
    assert response.status == ResponseStatus.OBSERVED
    assert response.response_version == 5


def test_evidence_upload_hash_download_and_delete(app, phase4_assessment, respondent_user):
    question = phase4_assessment.questions[0]
    file = FileStorage(
        stream=BytesIO(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"),
        filename="evidencia.pdf",
        content_type="application/pdf",
    )
    evidence = evidence_service.upload(
        question,
        file,
        description="Aprobación formal",
        actor_id=respondent_user.id,
    )
    assert evidence.validation_status == EvidenceValidationStatus.PENDING
    assert evidence.sha256
    path = evidence_service.record_download(evidence, actor_id=respondent_user.id)
    assert path.is_file()
    assert str(path).startswith(str(app.config["UPLOAD_FOLDER"]))
    evidence_service.delete(evidence, actor_id=respondent_user.id)
    assert not evidence.is_active
    assert not path.exists()


def test_duplicate_evidence_is_rejected(phase4_assessment, respondent_user):
    question = phase4_assessment.questions[0]
    content = b"%PDF-1.4\n%%EOF"
    evidence_service.upload(
        question,
        FileStorage(stream=BytesIO(content), filename="one.pdf", content_type="application/pdf"),
        description=None,
        actor_id=respondent_user.id,
    )
    with pytest.raises(ConflictError):
        evidence_service.upload(
            question,
            FileStorage(stream=BytesIO(content), filename="two.pdf", content_type="application/pdf"),
            description=None,
            actor_id=respondent_user.id,
        )
