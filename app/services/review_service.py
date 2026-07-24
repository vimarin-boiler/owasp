from __future__ import annotations

from app.common.errors import ConflictError, ValidationError
from app.enums import AssessmentStatus, AssignmentRole, EvidenceValidationStatus, ResponseStatus, ReviewDecision
from sqlalchemy import func, select

from app.extensions import db
from app.models import AssessmentQuestion, AssessmentReviewNote, AssessmentResponse, Evidence, ResponseHistory, Review
from app.models.base import utc_now
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service
from app.services.response_service import ResponseService


class ReviewService:
    def decide(
        self,
        response: AssessmentResponse,
        *,
        decision: ReviewDecision,
        comment: str | None,
        reviewer_id: int,
    ) -> AssessmentResponse:
        if response.status != ResponseStatus.SUBMITTED:
            raise ConflictError("Solo se pueden revisar respuestas enviadas.")
        clean_comment = comment.strip() if comment else None
        if decision in {ReviewDecision.OBSERVED, ReviewDecision.REJECTED} and not clean_comment:
            raise ValidationError("La observación del revisor es obligatoria para observar o rechazar.")
        if decision not in {ReviewDecision.APPROVED, ReviewDecision.OBSERVED, ReviewDecision.REJECTED}:
            raise ValidationError("La decisión de revisión no es válida.")

        before = ResponseService._snapshot(response)
        reviewed_version = response.response_version
        previous_status = response.status
        target = {
            ReviewDecision.APPROVED: ResponseStatus.APPROVED,
            ReviewDecision.OBSERVED: ResponseStatus.OBSERVED,
            ReviewDecision.REJECTED: ResponseStatus.REJECTED,
        }[decision]
        db.session.add(
            Review(
                assessment_response=response,
                response_version=reviewed_version,
                reviewer_id=reviewer_id,
                decision=decision,
                comment=clean_comment,
            )
        )
        response.response_version += 1
        response.status = target
        response.reviewer_id = reviewer_id
        response.reviewer_comment = clean_comment
        response.reviewed_at = utc_now()
        response.assessment_question.current_status = target
        db.session.add(
            ResponseHistory(
                assessment_response=response,
                response_version=response.response_version,
                snapshot_json=ResponseService._snapshot(response),
                transition_from=previous_status.value,
                transition_to=target.value,
                changed_by_id=reviewer_id,
                reason=f"Revisión: {decision.value}",
            )
        )
        assessment = response.assessment_question.assessment
        if target in {ResponseStatus.OBSERVED, ResponseStatus.REJECTED}:
            assessment.status = AssessmentStatus.OBSERVED
        else:
            unresolved = int(
                db.session.scalar(
                    select(func.count(AssessmentQuestion.id)).where(
                        AssessmentQuestion.assessment_id == assessment.id,
                        AssessmentQuestion.current_status.in_([ResponseStatus.OBSERVED, ResponseStatus.REJECTED]),
                    )
                )
                or 0
            )
            assessment.status = AssessmentStatus.OBSERVED if unresolved else AssessmentStatus.IN_REVIEW
        if response.respondent_id:
            notification_service.create(
                response.respondent_id,
                "Respuesta revisada",
                f"{response.assessment_question.external_code_snapshot} fue marcada como {target.value}.",
                f"/assessments/{assessment.public_id}/questions/{response.assessment_question.public_id}",
            )
        audit_service.record(
            action=f"review.{decision.value}",
            entity_type="assessment_response",
            entity_public_id=response.public_id,
            actor_user_id=reviewer_id,
            organization_id=assessment.organization_id,
            assessment_id=assessment.id,
            before=before,
            after=ResponseService._snapshot(response),
        )
        db.session.commit()
        return response

    def reopen(self, response: AssessmentResponse, *, comment: str, reviewer_id: int) -> AssessmentResponse:
        if response.status != ResponseStatus.APPROVED:
            raise ConflictError("Solo una respuesta aprobada puede reabrirse.")
        clean_comment = comment.strip()
        if not clean_comment:
            raise ValidationError("Debes indicar el motivo de reapertura.")
        before = ResponseService._snapshot(response)
        reviewed_version = response.response_version
        response.response_version += 1
        response.status = ResponseStatus.OBSERVED
        response.reviewer_id = reviewer_id
        response.reviewer_comment = clean_comment
        response.reviewed_at = utc_now()
        response.assessment_question.current_status = ResponseStatus.OBSERVED
        response.assessment_question.assessment.status = AssessmentStatus.OBSERVED
        db.session.add(
            Review(
                assessment_response=response,
                response_version=reviewed_version,
                reviewer_id=reviewer_id,
                decision=ReviewDecision.REOPENED,
                comment=clean_comment,
            )
        )
        db.session.add(
            ResponseHistory(
                assessment_response=response,
                response_version=response.response_version,
                snapshot_json=ResponseService._snapshot(response),
                transition_from=ResponseStatus.APPROVED.value,
                transition_to=ResponseStatus.OBSERVED.value,
                changed_by_id=reviewer_id,
                reason="Respuesta reabierta",
            )
        )
        assessment = response.assessment_question.assessment
        audit_service.record(
            action="review.reopened",
            entity_type="assessment_response",
            entity_public_id=response.public_id,
            actor_user_id=reviewer_id,
            organization_id=assessment.organization_id,
            assessment_id=assessment.id,
            before=before,
            after=ResponseService._snapshot(response),
        )
        db.session.commit()
        return response

    def review_evidence(
        self,
        evidence: Evidence,
        *,
        status: EvidenceValidationStatus,
        comment: str | None,
        reviewer_id: int,
    ) -> Evidence:
        if status not in {EvidenceValidationStatus.VALID, EvidenceValidationStatus.REJECTED}:
            raise ValidationError("El estado de validación de la evidencia no es válido.")
        clean_comment = comment.strip() if comment else None
        if status == EvidenceValidationStatus.REJECTED and not clean_comment:
            raise ValidationError("Debes explicar por qué la evidencia fue rechazada.")
        before = {"status": evidence.validation_status, "comment": evidence.review_comment}
        evidence.validation_status = status
        evidence.review_comment = clean_comment
        evidence.reviewed_by_id = reviewer_id
        evidence.reviewed_at = utc_now()
        assessment = evidence.assessment_question.assessment
        audit_service.record(
            action=f"evidence.{status.value}",
            entity_type="evidence",
            entity_public_id=evidence.public_id,
            actor_user_id=reviewer_id,
            organization_id=assessment.organization_id,
            assessment_id=assessment.id,
            before=before,
            after={"status": status, "comment": clean_comment},
        )
        db.session.commit()
        return evidence

    def add_note(self, assessment, *, body: str, author_id: int) -> AssessmentReviewNote:
        clean_body = body.strip()
        if not clean_body:
            raise ValidationError("La observación general no puede estar vacía.")
        note = AssessmentReviewNote(assessment=assessment, author_id=author_id, body=clean_body)
        db.session.add(note)
        db.session.flush()
        for assignment in assessment.assignments:
            if assignment.assignment_role == AssignmentRole.RESPONDENT:
                notification_service.create(
                    assignment.user_id,
                    "Nueva observación general",
                    f"Se agregó una observación en {assessment.name}.",
                    f"/assessments/{assessment.public_id}",
                )
        audit_service.record(
            action="assessment.review_note_added",
            entity_type="assessment_review_note",
            entity_public_id=note.public_id,
            actor_user_id=author_id,
            organization_id=assessment.organization_id,
            assessment_id=assessment.id,
            after={"body": clean_body},
        )
        db.session.commit()
        return note

    def resolve_note(self, note: AssessmentReviewNote, *, actor_id: int) -> AssessmentReviewNote:
        if note.is_resolved:
            return note
        note.is_resolved = True
        note.resolved_at = utc_now()
        note.resolved_by_id = actor_id
        audit_service.record(
            action="assessment.review_note_resolved",
            entity_type="assessment_review_note",
            entity_public_id=note.public_id,
            actor_user_id=actor_id,
            organization_id=note.assessment.organization_id,
            assessment_id=note.assessment_id,
            after={"is_resolved": True},
        )
        db.session.commit()
        return note


review_service = ReviewService()
