from __future__ import annotations

from decimal import Decimal

from app.enums import ResponseStatus, ReviewDecision, ScoringSource
from app.repositories import assessment_repository, scoring_repository
from app.services import response_service, review_service, scoring_service


def test_scoring_source_declared_reviewed_and_approved(
    phase4_assessment, respondent_user, reviewer_user
):
    question = phase4_assessment.questions[0]
    response_service.save(
        question,
        actor_id=respondent_user.id,
        selected_option_code="YES",
        respondent_comment="Control implementado.",
        is_not_applicable=False,
        not_applicable_justification=None,
        intent="submit",
    )
    phase4_assessment = assessment_repository.get_by_public_id(phase4_assessment.public_id)

    declared = scoring_service.calculate(phase4_assessment, source=ScoringSource.DECLARED)
    reviewed = scoring_service.calculate(phase4_assessment, source=ScoringSource.REVIEWED)
    approved = scoring_service.calculate(phase4_assessment, source=ScoringSource.APPROVED)

    assert declared.overall_score == Decimal("3.0000")
    assert reviewed.overall_score == Decimal("0.0000")
    assert approved.overall_score == Decimal("0.0000")
    assert reviewed.status_summary["pending_for_source"] == 1

    review_service.decide(
        question.response,
        decision=ReviewDecision.APPROVED,
        comment="Respuesta validada.",
        reviewer_id=reviewer_user.id,
    )
    phase4_assessment = assessment_repository.get_by_public_id(phase4_assessment.public_id)
    reviewed = scoring_service.calculate(phase4_assessment, source=ScoringSource.REVIEWED)
    approved = scoring_service.calculate(phase4_assessment, source=ScoringSource.APPROVED)
    assert reviewed.overall_score == Decimal("3.0000")
    assert approved.overall_score == Decimal("3.0000")


def test_not_applicable_is_excluded_from_denominator(phase4_assessment, respondent_user, reviewer_user):
    question = phase4_assessment.questions[0]
    response_service.save(
        question,
        actor_id=respondent_user.id,
        selected_option_code=None,
        respondent_comment="Fuera del alcance.",
        is_not_applicable=True,
        not_applicable_justification="El componente no procesa software propio.",
        intent="submit",
    )
    review_service.decide(
        question.response,
        decision=ReviewDecision.APPROVED,
        comment="No aplicabilidad aceptada.",
        reviewer_id=reviewer_user.id,
    )
    assessment = assessment_repository.get_by_public_id(phase4_assessment.public_id)
    result = scoring_service.calculate(assessment, source=ScoringSource.APPROVED)
    assert result.overall_score == Decimal("0.0000")
    assert result.status_summary["not_applicable_questions"] == 1
    assert result.status_summary["applicable_questions"] == 0
    assert result.by_type("overall")[0].max_score == Decimal("0.0000")


def test_snapshot_is_reused_when_inputs_do_not_change(phase4_assessment, admin_user):
    first = scoring_service.calculate(
        phase4_assessment,
        source=ScoringSource.APPROVED,
        persist=True,
        actor_id=admin_user.id,
    )
    second = scoring_service.calculate(
        phase4_assessment,
        source=ScoringSource.APPROVED,
        persist=True,
        actor_id=admin_user.id,
    )
    assert first.snapshot is not None
    assert second.snapshot is not None
    assert first.snapshot.id == second.snapshot.id
    assert scoring_repository.latest(phase4_assessment.id).snapshot_number == 1


def test_pending_questions_count_as_zero(phase4_assessment):
    result = scoring_service.calculate(phase4_assessment, source=ScoringSource.APPROVED)
    assert result.overall_score == Decimal("0.0000")
    assert result.status_summary["pending_for_source"] == 1
    assert result.by_type("overall")[0].pending_count == 1
