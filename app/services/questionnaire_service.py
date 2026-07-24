from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.common.errors import DomainError
from app.enums import QuestionRevisionStatus, QuestionnaireStatus
from app.extensions import db
from app.models import Question, QuestionnaireVersion, QuestionnaireVersionQuestion, QuestionRevision
from app.models.base import utc_now
from app.services.audit_service import audit_service


class QuestionnaireService:
    def create_version(self, *, name: str, version_number: str, description: str | None, actor_id: int, source_version_id: int | None = None) -> QuestionnaireVersion:
        normalized = version_number.strip()
        if db.session.scalar(select(QuestionnaireVersion).where(QuestionnaireVersion.version_number == normalized)):
            raise DomainError("Ya existe una versión con ese número.")
        version = QuestionnaireVersion(name=name.strip(), version_number=normalized, description=(description or "").strip() or None, status=QuestionnaireStatus.DRAFT, created_by_id=actor_id, updated_by_id=actor_id)
        db.session.add(version)
        db.session.flush()

        if source_version_id:
            source = db.session.scalar(select(QuestionnaireVersion).options(selectinload(QuestionnaireVersion.question_links)).where(QuestionnaireVersion.id == source_version_id))
            if source is None:
                raise DomainError("La versión de origen no existe.")
            links = sorted(source.question_links, key=lambda item: item.sort_order)
            for link in links:
                db.session.add(QuestionnaireVersionQuestion(questionnaire_version_id=version.id, question_revision_id=link.question_revision_id, sort_order=link.sort_order, is_required=link.is_required, weight_override=link.weight_override))
        else:
            questions = list(db.session.scalars(select(Question).where(Question.is_active.is_(True), Question.current_revision_number.is_not(None)).order_by(Question.external_code)))
            for order, question in enumerate(questions, start=1):
                revision = db.session.scalar(select(QuestionRevision).where(QuestionRevision.question_id == question.id, QuestionRevision.revision_number == question.current_revision_number))
                if revision:
                    db.session.add(QuestionnaireVersionQuestion(questionnaire_version_id=version.id, question_revision_id=revision.id, sort_order=order, is_required=True))
        audit_service.record(action="catalog.questionnaire_version.create", entity_type="QuestionnaireVersion", entity_public_id=version.public_id, actor_user_id=actor_id, after={"version_number": version.version_number})
        db.session.commit()
        return version

    def publish(self, version: QuestionnaireVersion, *, actor_id: int) -> QuestionnaireVersion:
        if version.status != QuestionnaireStatus.DRAFT:
            raise DomainError("Solo se puede publicar una versión en borrador.")
        if not version.question_links:
            raise DomainError("La versión no contiene preguntas.")
        for existing in db.session.scalars(select(QuestionnaireVersion).where(QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED, QuestionnaireVersion.id != version.id)):
            existing.status = QuestionnaireStatus.ARCHIVED
            existing.updated_by_id = actor_id
        for link in version.question_links:
            if link.question_revision.status == QuestionRevisionStatus.DRAFT:
                link.question_revision.status = QuestionRevisionStatus.PUBLISHED
                link.question_revision.updated_by_id = actor_id
        version.status = QuestionnaireStatus.PUBLISHED
        version.published_at = utc_now()
        version.published_by_id = actor_id
        version.updated_by_id = actor_id
        audit_service.record(action="catalog.questionnaire_version.publish", entity_type="QuestionnaireVersion", entity_public_id=version.public_id, actor_user_id=actor_id, after={"version_number": version.version_number, "questions": len(version.question_links)})
        db.session.commit()
        return version

    def archive(self, version: QuestionnaireVersion, *, actor_id: int) -> QuestionnaireVersion:
        if version.status == QuestionnaireStatus.ARCHIVED:
            return version
        version.status = QuestionnaireStatus.ARCHIVED
        version.updated_by_id = actor_id
        audit_service.record(action="catalog.questionnaire_version.archive", entity_type="QuestionnaireVersion", entity_public_id=version.public_id, actor_user_id=actor_id, after={"version_number": version.version_number})
        db.session.commit()
        return version


questionnaire_service = QuestionnaireService()
