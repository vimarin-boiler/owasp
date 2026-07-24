from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from app.common.errors import ConflictError, ValidationError
from app.enums import AssessmentStatus, AssignmentRole, QuestionnaireStatus, ResponseStatus, ScoringSource
from app.extensions import db
from app.models import Assessment, AssessmentQuestion, AssessmentUser, Organization, QuestionnaireVersion, User
from app.repositories.assessments import assessment_repository
from app.services.audit_service import audit_service


ALLOWED_TRANSITIONS: dict[AssessmentStatus, set[AssessmentStatus]] = {
    AssessmentStatus.DRAFT: {AssessmentStatus.CONFIGURED, AssessmentStatus.CANCELLED},
    AssessmentStatus.CONFIGURED: {AssessmentStatus.DRAFT, AssessmentStatus.IN_PROGRESS, AssessmentStatus.CANCELLED},
    AssessmentStatus.IN_PROGRESS: {AssessmentStatus.IN_REVIEW, AssessmentStatus.OBSERVED, AssessmentStatus.CANCELLED},
    AssessmentStatus.IN_REVIEW: {AssessmentStatus.IN_PROGRESS, AssessmentStatus.OBSERVED, AssessmentStatus.COMPLETED, AssessmentStatus.CANCELLED},
    AssessmentStatus.OBSERVED: {AssessmentStatus.IN_PROGRESS, AssessmentStatus.IN_REVIEW, AssessmentStatus.CANCELLED},
    AssessmentStatus.COMPLETED: {AssessmentStatus.IN_REVIEW, AssessmentStatus.PUBLISHED, AssessmentStatus.CLOSED},
    AssessmentStatus.PUBLISHED: {AssessmentStatus.IN_REVIEW, AssessmentStatus.CLOSED},
    AssessmentStatus.CLOSED: set(),
    AssessmentStatus.CANCELLED: set(),
}


class AssessmentService:
    @staticmethod
    def _clean(value: str | None) -> str | None:
        value = value.strip() if value else ""
        return value or None

    @staticmethod
    def _target_level(value: str | Decimal | None) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            result = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValidationError("El nivel objetivo debe ser numérico.") from exc
        if result < 0 or result > 3:
            raise ValidationError("El nivel objetivo debe estar entre 0 y 3.")
        return result

    @staticmethod
    def _validate_dates(start_date: date | None, target_date: date | None) -> None:
        if start_date and target_date and target_date < start_date:
            raise ValidationError("La fecha objetivo no puede ser anterior a la fecha de inicio.")

    @staticmethod
    def _validate_users(user_ids: list[int], role_code: str) -> list[User]:
        if not user_ids:
            return []
        users = list(db.session.scalars(select(User).where(User.id.in_(set(user_ids)), User.is_active.is_(True))))
        if len(users) != len(set(user_ids)):
            raise ValidationError("Uno o más usuarios asignados no existen o están inactivos.")
        invalid = [user.display_name for user in users if not user.has_role(role_code)]
        if invalid:
            raise ValidationError(
                f"Los siguientes usuarios no tienen el rol {role_code}: {', '.join(sorted(invalid))}."
            )
        return users

    @staticmethod
    def _snapshot_question(assessment: Assessment, link) -> AssessmentQuestion:
        revision = link.question_revision
        return AssessmentQuestion(
            assessment=assessment,
            source_question_revision_id=revision.id,
            external_code_snapshot=revision.question.external_code,
            question_text_snapshot=revision.question_text,
            guidance_snapshot=revision.guidance_text,
            criteria_snapshot=[
                {"text": criterion.criterion_text, "sort_order": criterion.sort_order}
                for criterion in sorted(revision.criteria, key=lambda item: (item.sort_order, item.id))
            ],
            answer_options_snapshot=[
                {
                    "code": option.option_code,
                    "text": option.text,
                    "weight": str(option.weight),
                    "sort_order": option.sort_order,
                }
                for option in sorted(revision.answer_set.options, key=lambda item: (item.sort_order, item.id))
                if option.is_active
            ],
            business_function_snapshot={"code": revision.business_function.code, "name": revision.business_function.name},
            security_practice_snapshot={"code": revision.security_practice.code, "name": revision.security_practice.name},
            practice_stream_snapshot={"code": revision.practice_stream.code, "name": revision.practice_stream.name},
            maturity_level_snapshot={
                "number": revision.maturity_level.level_number,
                "name": revision.maturity_level.name,
            },
            sort_order=link.sort_order,
            is_required=link.is_required,
            current_status=ResponseStatus.UNANSWERED,
        )

    def _replace_questions(self, assessment: Assessment, version: QuestionnaireVersion) -> None:
        if any(question.response is not None for question in assessment.questions):
            raise ConflictError("No se puede cambiar la versión porque el assessment ya tiene respuestas.")
        assessment.questions.clear()
        for link in sorted(version.question_links, key=lambda item: (item.sort_order, item.id)):
            assessment.questions.append(self._snapshot_question(assessment, link))

    def _sync_assignments(
        self,
        assessment: Assessment,
        respondent_ids: list[int],
        reviewer_ids: list[int],
        actor_id: int,
    ) -> None:
        respondents = self._validate_users(respondent_ids, "respondent")
        reviewers = self._validate_users(reviewer_ids, "reviewer")
        assessment.assignments.clear()
        for index, user in enumerate(sorted(respondents, key=lambda item: item.display_name.casefold())):
            assessment.assignments.append(
                AssessmentUser(
                    user_id=user.id,
                    assignment_role=AssignmentRole.RESPONDENT,
                    is_lead=index == 0,
                    assigned_by_id=actor_id,
                )
            )
        for index, user in enumerate(sorted(reviewers, key=lambda item: item.display_name.casefold())):
            assessment.assignments.append(
                AssessmentUser(
                    user_id=user.id,
                    assignment_role=AssignmentRole.REVIEWER,
                    is_lead=index == 0,
                    assigned_by_id=actor_id,
                )
            )

    def create(
        self,
        *,
        organization_id: int,
        questionnaire_version: QuestionnaireVersion,
        name: str,
        description: str | None,
        scope: str | None,
        start_date: date | None,
        target_date: date | None,
        target_maturity_level: str | Decimal | None,
        scoring_source: ScoringSource,
        respondent_ids: list[int],
        reviewer_ids: list[int],
        actor_id: int,
    ) -> Assessment:
        if not name.strip():
            raise ValidationError("El nombre del assessment es obligatorio.")
        organization = db.session.get(Organization, organization_id)
        if organization is None or not organization.is_active:
            raise ValidationError("La organización seleccionada no existe o está inactiva.")
        if questionnaire_version.status != QuestionnaireStatus.PUBLISHED:
            raise ValidationError("Solo se pueden crear assessments usando una versión publicada.")
        if not questionnaire_version.question_links:
            raise ValidationError("La versión seleccionada no contiene preguntas.")
        self._validate_dates(start_date, target_date)
        assessment = Assessment(
            organization_id=organization_id,
            questionnaire_version_id=questionnaire_version.id,
            name=name.strip(),
            description=self._clean(description),
            scope=self._clean(scope),
            start_date=start_date,
            target_date=target_date,
            target_maturity_level=self._target_level(target_maturity_level),
            scoring_source=scoring_source,
            status=AssessmentStatus.DRAFT,
            settings_snapshot={"questionnaire_version": questionnaire_version.version_number},
            created_by_id=actor_id,
            updated_by_id=actor_id,
        )
        db.session.add(assessment)
        self._replace_questions(assessment, questionnaire_version)
        self._sync_assignments(assessment, respondent_ids, reviewer_ids, actor_id)
        if respondent_ids:
            assessment.status = AssessmentStatus.CONFIGURED
        db.session.flush()
        audit_service.record(
            action="assessment.created",
            entity_type="assessment",
            entity_public_id=assessment.public_id,
            actor_user_id=actor_id,
            organization_id=organization_id,
            assessment_id=assessment.id,
            after={
                "name": assessment.name,
                "status": assessment.status,
                "questionnaire_version": questionnaire_version.version_number,
                "questions": len(assessment.questions),
                "respondents": respondent_ids,
                "reviewers": reviewer_ids,
            },
        )
        db.session.commit()
        return assessment

    def update(
        self,
        assessment: Assessment,
        *,
        organization_id: int,
        questionnaire_version: QuestionnaireVersion,
        name: str,
        description: str | None,
        scope: str | None,
        start_date: date | None,
        target_date: date | None,
        target_maturity_level: str | Decimal | None,
        scoring_source: ScoringSource,
        respondent_ids: list[int],
        reviewer_ids: list[int],
        actor_id: int,
    ) -> Assessment:
        if assessment.status in {AssessmentStatus.CLOSED, AssessmentStatus.CANCELLED}:
            raise ConflictError("Un assessment cerrado o cancelado no puede editarse.")
        if not name.strip():
            raise ValidationError("El nombre del assessment es obligatorio.")
        organization = db.session.get(Organization, organization_id)
        if organization is None or not organization.is_active:
            raise ValidationError("La organización seleccionada no existe o está inactiva.")
        self._validate_dates(start_date, target_date)
        before = self.serialize(assessment)
        if questionnaire_version.id != assessment.questionnaire_version_id:
            if assessment.status not in {AssessmentStatus.DRAFT, AssessmentStatus.CONFIGURED}:
                raise ConflictError("La versión solo puede cambiarse mientras el assessment está en borrador o configurado.")
            if questionnaire_version.status != QuestionnaireStatus.PUBLISHED:
                raise ValidationError("Solo puede seleccionarse una versión publicada.")
            assessment.questionnaire_version_id = questionnaire_version.id
            assessment.questionnaire_version = questionnaire_version
            self._replace_questions(assessment, questionnaire_version)
        assessment.organization_id = organization_id
        assessment.name = name.strip()
        assessment.description = self._clean(description)
        assessment.scope = self._clean(scope)
        assessment.start_date = start_date
        assessment.target_date = target_date
        assessment.target_maturity_level = self._target_level(target_maturity_level)
        assessment.scoring_source = scoring_source
        assessment.updated_by_id = actor_id
        self._sync_assignments(assessment, respondent_ids, reviewer_ids, actor_id)
        if assessment.status == AssessmentStatus.DRAFT and respondent_ids:
            assessment.status = AssessmentStatus.CONFIGURED
        if assessment.status == AssessmentStatus.CONFIGURED and not respondent_ids:
            assessment.status = AssessmentStatus.DRAFT
        audit_service.record(
            action="assessment.updated",
            entity_type="assessment",
            entity_public_id=assessment.public_id,
            actor_user_id=actor_id,
            organization_id=organization_id,
            assessment_id=assessment.id,
            before=before,
            after=self.serialize(assessment),
        )
        db.session.commit()
        return assessment

    def transition(self, assessment: Assessment, target: AssessmentStatus, actor_id: int) -> Assessment:
        if target not in ALLOWED_TRANSITIONS.get(assessment.status, set()):
            raise ConflictError(f"No es posible cambiar de {assessment.status.value} a {target.value}.")
        questions = assessment_repository.questions(assessment.id)
        respondent_count = sum(
            1 for assignment in assessment.assignments if assignment.assignment_role == AssignmentRole.RESPONDENT
        )
        if target == AssessmentStatus.CONFIGURED and (not questions or not respondent_count):
            raise ValidationError("Para configurar el assessment debe tener preguntas y al menos un respondedor.")
        if target == AssessmentStatus.IN_PROGRESS and not respondent_count:
            raise ValidationError("No se puede iniciar sin usuarios respondedores asignados.")
        if target == AssessmentStatus.IN_REVIEW and not any(
            question.current_status == ResponseStatus.SUBMITTED for question in questions
        ):
            raise ValidationError("No existen respuestas enviadas a revisión.")
        if target == AssessmentStatus.COMPLETED:
            pending = [
                question for question in questions
                if question.is_required and question.current_status != ResponseStatus.APPROVED
            ]
            if pending:
                raise ValidationError(
                    f"No se puede completar: quedan {len(pending)} preguntas requeridas sin aprobar."
                )
        before_status = assessment.status
        assessment.status = target
        assessment.updated_by_id = actor_id
        if target == AssessmentStatus.PUBLISHED:
            from app.models.base import utc_now
            assessment.results_published_at = utc_now()
        if target == AssessmentStatus.CLOSED:
            from app.models.base import utc_now
            assessment.closed_at = utc_now()
        audit_service.record(
            action="assessment.status_changed",
            entity_type="assessment",
            entity_public_id=assessment.public_id,
            actor_user_id=actor_id,
            organization_id=assessment.organization_id,
            assessment_id=assessment.id,
            before={"status": before_status},
            after={"status": target},
        )
        db.session.commit()
        return assessment

    @staticmethod
    def serialize(assessment: Assessment) -> dict:
        return {
            "name": assessment.name,
            "organization_id": assessment.organization_id,
            "questionnaire_version_id": assessment.questionnaire_version_id,
            "description": assessment.description,
            "scope": assessment.scope,
            "start_date": assessment.start_date,
            "target_date": assessment.target_date,
            "target_maturity_level": assessment.target_maturity_level,
            "scoring_source": assessment.scoring_source,
            "status": assessment.status,
            "assignments": [
                {"user_id": item.user_id, "role": item.assignment_role, "is_lead": item.is_lead}
                for item in assessment.assignments
            ],
        }

    @staticmethod
    def progress(assessment: Assessment) -> dict:
        questions = assessment.questions
        total = len(questions)
        counts = {status.value: 0 for status in ResponseStatus}
        not_applicable = 0
        evidence_count = 0
        for question in questions:
            counts[question.current_status.value] += 1
            evidence_count += sum(1 for evidence in question.evidences if evidence.is_active)
            if question.response and question.response.is_not_applicable:
                not_applicable += 1
        completed_statuses = {
            ResponseStatus.ANSWERED.value,
            ResponseStatus.SUBMITTED.value,
            ResponseStatus.OBSERVED.value,
            ResponseStatus.REJECTED.value,
            ResponseStatus.APPROVED.value,
        }
        completed = sum(counts[status] for status in completed_statuses)
        return {
            "total": total,
            "completed": completed,
            "percentage": round((completed / total) * 100, 1) if total else 0.0,
            "counts": counts,
            "not_applicable": not_applicable,
            "evidences": evidence_count,
        }


assessment_service = AssessmentService()
