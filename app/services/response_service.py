from __future__ import annotations

from decimal import Decimal

from app.common.errors import ConflictError, ValidationError
from app.enums import AssessmentStatus, AssignmentRole, ResponseStatus
from sqlalchemy import func, select

from app.extensions import db
from app.models import AssessmentQuestion, AssessmentResponse, ResponseHistory
from app.models.base import utc_now
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service


EDITABLE_STATUSES = {
    ResponseStatus.UNANSWERED,
    ResponseStatus.DRAFT,
    ResponseStatus.ANSWERED,
    ResponseStatus.OBSERVED,
    ResponseStatus.REJECTED,
}


class ResponseService:
    @staticmethod
    def _option(question: AssessmentQuestion, code: str | None) -> dict | None:
        if not code:
            return None
        return next(
            (option for option in question.answer_options_snapshot if str(option.get("code")) == str(code)),
            None,
        )

    @staticmethod
    def _snapshot(response: AssessmentResponse) -> dict:
        return {
            "response_version": response.response_version,
            "selected_option_code": response.selected_option_code,
            "selected_option_text": response.selected_option_text_snapshot,
            "selected_weight": str(response.selected_weight_snapshot) if response.selected_weight_snapshot is not None else None,
            "respondent_comment": response.respondent_comment,
            "reviewer_comment": response.reviewer_comment,
            "status": response.status.value,
            "is_not_applicable": response.is_not_applicable,
            "not_applicable_justification": response.not_applicable_justification,
            "respondent_id": response.respondent_id,
            "reviewer_id": response.reviewer_id,
            "submitted_at": response.submitted_at.isoformat() if response.submitted_at else None,
            "reviewed_at": response.reviewed_at.isoformat() if response.reviewed_at else None,
        }

    @staticmethod
    def _add_history(
        response: AssessmentResponse,
        *,
        previous_status: ResponseStatus | None,
        actor_id: int,
        reason: str,
    ) -> None:
        db.session.add(
            ResponseHistory(
                assessment_response=response,
                response_version=response.response_version,
                snapshot_json=ResponseService._snapshot(response),
                transition_from=previous_status.value if previous_status else None,
                transition_to=response.status.value,
                changed_by_id=actor_id,
                reason=reason,
            )
        )

    def save(
        self,
        question: AssessmentQuestion,
        *,
        actor_id: int,
        selected_option_code: str | None,
        respondent_comment: str | None,
        is_not_applicable: bool,
        not_applicable_justification: str | None,
        intent: str,
    ) -> AssessmentResponse:
        assessment = question.assessment
        if assessment.status not in {AssessmentStatus.IN_PROGRESS, AssessmentStatus.OBSERVED, AssessmentStatus.IN_REVIEW}:
            raise ConflictError("El assessment no se encuentra habilitado para responder.")
        response = question.response
        if response and response.status not in EDITABLE_STATUSES:
            raise ConflictError("La respuesta no puede editarse en su estado actual.")

        comment = respondent_comment.strip() if respondent_comment else None
        justification = not_applicable_justification.strip() if not_applicable_justification else None
        option = None if is_not_applicable else self._option(question, selected_option_code)
        if selected_option_code and not is_not_applicable and option is None:
            raise ValidationError("La alternativa seleccionada no pertenece a esta pregunta.")
        if is_not_applicable and not justification and intent in {"save", "submit"}:
            raise ValidationError("Debes justificar por qué la pregunta no aplica.")
        if intent in {"save", "submit"} and not is_not_applicable and option is None:
            raise ValidationError("Selecciona una alternativa de respuesta.")
        if intent not in {"autosave", "draft", "save", "submit"}:
            raise ValidationError("La acción solicitada no es válida.")

        previous_status = response.status if response else None
        before = self._snapshot(response) if response else None
        target_status = {
            "autosave": ResponseStatus.DRAFT,
            "draft": ResponseStatus.DRAFT,
            "save": ResponseStatus.ANSWERED,
            "submit": ResponseStatus.SUBMITTED,
        }[intent]

        if response is None:
            response = AssessmentResponse(
                assessment_question=question,
                respondent_id=actor_id,
                response_version=1,
            )
            db.session.add(response)
        else:
            candidate = {
                "selected_option_code": option.get("code") if option else None,
                "respondent_comment": comment,
                "is_not_applicable": is_not_applicable,
                "not_applicable_justification": justification,
                "status": target_status.value,
                "respondent_id": actor_id,
            }
            current = {
                "selected_option_code": response.selected_option_code,
                "respondent_comment": response.respondent_comment,
                "is_not_applicable": response.is_not_applicable,
                "not_applicable_justification": response.not_applicable_justification,
                "status": response.status.value,
                "respondent_id": response.respondent_id,
            }
            if candidate == current:
                return response
            response.response_version += 1

        response.respondent_id = actor_id
        response.selected_option_code = option.get("code") if option else None
        response.selected_option_text_snapshot = option.get("text") if option else None
        response.selected_weight_snapshot = Decimal(str(option.get("weight"))) if option else None
        response.respondent_comment = comment
        response.is_not_applicable = is_not_applicable
        response.not_applicable_justification = justification
        response.status = target_status
        response.reviewer_comment = None if target_status == ResponseStatus.SUBMITTED else response.reviewer_comment
        response.reviewer_id = None if target_status == ResponseStatus.SUBMITTED else response.reviewer_id
        response.reviewed_at = None if target_status == ResponseStatus.SUBMITTED else response.reviewed_at
        response.submitted_at = utc_now() if target_status == ResponseStatus.SUBMITTED else response.submitted_at
        question.current_status = target_status
        db.session.flush()
        self._add_history(
            response,
            previous_status=previous_status,
            actor_id=actor_id,
            reason={"autosave": "Guardado automático", "draft": "Borrador guardado", "save": "Respuesta guardada", "submit": "Enviada a revisión"}[intent],
        )
        if target_status == ResponseStatus.SUBMITTED:
            unresolved = int(
                db.session.scalar(
                    select(func.count(AssessmentQuestion.id)).where(
                        AssessmentQuestion.assessment_id == assessment.id,
                        AssessmentQuestion.current_status.in_([ResponseStatus.OBSERVED, ResponseStatus.REJECTED]),
                    )
                )
                or 0
            )
            if assessment.status == AssessmentStatus.OBSERVED and unresolved == 0:
                assessment.status = AssessmentStatus.IN_REVIEW
            for assignment in assessment.assignments:
                if assignment.assignment_role == AssignmentRole.REVIEWER:
                    notification_service.create(
                        assignment.user_id,
                        "Respuesta pendiente de revisión",
                        f"{question.external_code_snapshot} fue enviada en {assessment.name}.",
                        f"/assessments/{assessment.public_id}/review/{question.public_id}",
                    )
        audit_service.record(
            action=f"response.{intent}",
            entity_type="assessment_response",
            entity_public_id=response.public_id,
            actor_user_id=actor_id,
            organization_id=assessment.organization_id,
            assessment_id=assessment.id,
            before=before,
            after=self._snapshot(response),
        )
        db.session.commit()
        return response


response_service = ResponseService()
