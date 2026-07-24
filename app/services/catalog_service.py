from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from app.common.errors import DomainError
from app.enums import QuestionRevisionStatus
from app.extensions import db
from app.models import (
    AnswerOption,
    AnswerSet,
    BusinessFunction,
    MaturityLevel,
    PracticeStream,
    Question,
    QuestionQualityCriterion,
    QuestionRevision,
    SecurityPractice,
)
from app.services.audit_service import audit_service


def _hash_payload(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CatalogService:
    def create_business_function(self, *, code: str, name: str, description: str | None, sort_order: int, actor_id: int) -> BusinessFunction:
        normalized = code.strip().upper()
        if db.session.scalar(select(BusinessFunction).where(BusinessFunction.code == normalized)):
            raise DomainError("Ya existe una función con ese código.")
        entity = BusinessFunction(code=normalized, name=name.strip(), description=(description or "").strip() or None, sort_order=sort_order, created_by_id=actor_id, updated_by_id=actor_id)
        db.session.add(entity)
        self._commit_audit("catalog.business_function.create", entity, actor_id)
        return entity

    def update_business_function(self, entity: BusinessFunction, *, code: str, name: str, description: str | None, sort_order: int, is_active: bool, actor_id: int) -> BusinessFunction:
        normalized = code.strip().upper()
        used = db.session.scalar(select(func.count(QuestionRevision.id)).where(QuestionRevision.business_function_id == entity.id)) or 0
        if used and (normalized != entity.code or name.strip() != entity.name):
            raise DomainError("La función ya forma parte de revisiones. Su código y nombre son inmutables; puedes ajustar descripción, orden o estado.")
        duplicate = db.session.scalar(select(BusinessFunction).where(BusinessFunction.code == normalized, BusinessFunction.id != entity.id))
        if duplicate:
            raise DomainError("Ya existe una función con ese código.")
        before = self._master_snapshot(entity)
        entity.code = normalized
        entity.name = name.strip()
        entity.description = (description or "").strip() or None
        entity.sort_order = sort_order
        entity.is_active = is_active
        entity.updated_by_id = actor_id
        self._commit_audit("catalog.business_function.update", entity, actor_id, before)
        return entity

    def create_security_practice(self, *, business_function_id: int, code: str, name: str, description: str | None, sort_order: int, actor_id: int) -> SecurityPractice:
        normalized = code.strip().upper()
        duplicate = db.session.scalar(select(SecurityPractice).where(SecurityPractice.business_function_id == business_function_id, SecurityPractice.code == normalized))
        if duplicate:
            raise DomainError("Ya existe una práctica con ese código dentro de la función.")
        entity = SecurityPractice(business_function_id=business_function_id, code=normalized, name=name.strip(), description=(description or "").strip() or None, sort_order=sort_order, created_by_id=actor_id, updated_by_id=actor_id)
        db.session.add(entity)
        self._commit_audit("catalog.security_practice.create", entity, actor_id)
        return entity

    def update_security_practice(self, entity: SecurityPractice, *, business_function_id: int, code: str, name: str, description: str | None, sort_order: int, is_active: bool, actor_id: int) -> SecurityPractice:
        normalized = code.strip().upper()
        used = db.session.scalar(select(func.count(QuestionRevision.id)).where(QuestionRevision.security_practice_id == entity.id)) or 0
        if used and (business_function_id != entity.business_function_id or normalized != entity.code or name.strip() != entity.name):
            raise DomainError("La práctica ya forma parte de revisiones. Su función, código y nombre son inmutables.")
        duplicate = db.session.scalar(select(SecurityPractice).where(SecurityPractice.business_function_id == business_function_id, SecurityPractice.code == normalized, SecurityPractice.id != entity.id))
        if duplicate:
            raise DomainError("Ya existe una práctica con ese código dentro de la función.")
        before = self._master_snapshot(entity)
        entity.business_function_id = business_function_id
        entity.code = normalized
        entity.name = name.strip()
        entity.description = (description or "").strip() or None
        entity.sort_order = sort_order
        entity.is_active = is_active
        entity.updated_by_id = actor_id
        self._commit_audit("catalog.security_practice.update", entity, actor_id, before)
        return entity

    def create_practice_stream(self, *, security_practice_id: int, code: str, name: str, description: str | None, sort_order: int, actor_id: int) -> PracticeStream:
        normalized = code.strip().upper()
        duplicate = db.session.scalar(select(PracticeStream).where(PracticeStream.security_practice_id == security_practice_id, PracticeStream.code == normalized))
        if duplicate:
            raise DomainError("Ya existe un flujo con ese código dentro de la práctica.")
        entity = PracticeStream(security_practice_id=security_practice_id, code=normalized, name=name.strip(), description=(description or "").strip() or None, sort_order=sort_order, created_by_id=actor_id, updated_by_id=actor_id)
        db.session.add(entity)
        self._commit_audit("catalog.practice_stream.create", entity, actor_id)
        return entity

    def update_practice_stream(self, entity: PracticeStream, *, security_practice_id: int, code: str, name: str, description: str | None, sort_order: int, is_active: bool, actor_id: int) -> PracticeStream:
        normalized = code.strip().upper()
        used = db.session.scalar(select(func.count(QuestionRevision.id)).where(QuestionRevision.practice_stream_id == entity.id)) or 0
        if used and (security_practice_id != entity.security_practice_id or normalized != entity.code or name.strip() != entity.name):
            raise DomainError("El flujo ya forma parte de revisiones. Su práctica, código y nombre son inmutables.")
        duplicate = db.session.scalar(select(PracticeStream).where(PracticeStream.security_practice_id == security_practice_id, PracticeStream.code == normalized, PracticeStream.id != entity.id))
        if duplicate:
            raise DomainError("Ya existe un flujo con ese código dentro de la práctica.")
        before = self._master_snapshot(entity)
        entity.security_practice_id = security_practice_id
        entity.code = normalized
        entity.name = name.strip()
        entity.description = (description or "").strip() or None
        entity.sort_order = sort_order
        entity.is_active = is_active
        entity.updated_by_id = actor_id
        self._commit_audit("catalog.practice_stream.update", entity, actor_id, before)
        return entity

    def create_maturity_level(self, *, level_number: int, name: str, description: str | None, max_score: Decimal, sort_order: int, actor_id: int) -> MaturityLevel:
        if db.session.scalar(select(MaturityLevel).where(MaturityLevel.level_number == level_number)):
            raise DomainError("Ya existe ese nivel de madurez.")
        entity = MaturityLevel(level_number=level_number, name=name.strip(), description=(description or "").strip() or None, max_score=max_score, sort_order=sort_order, created_by_id=actor_id, updated_by_id=actor_id)
        db.session.add(entity)
        self._commit_audit("catalog.maturity_level.create", entity, actor_id)
        return entity

    def update_maturity_level(self, entity: MaturityLevel, *, level_number: int, name: str, description: str | None, max_score: Decimal, sort_order: int, is_active: bool, actor_id: int) -> MaturityLevel:
        used = db.session.scalar(select(func.count(QuestionRevision.id)).where(QuestionRevision.maturity_level_id == entity.id)) or 0
        if used and (level_number != entity.level_number or name.strip() != entity.name or Decimal(max_score) != entity.max_score):
            raise DomainError("El nivel ya forma parte de revisiones. Su número, nombre y puntaje máximo son inmutables.")
        duplicate = db.session.scalar(select(MaturityLevel).where(MaturityLevel.level_number == level_number, MaturityLevel.id != entity.id))
        if duplicate:
            raise DomainError("Ya existe ese nivel de madurez.")
        before = self._master_snapshot(entity)
        entity.level_number = level_number
        entity.name = name.strip()
        entity.description = (description or "").strip() or None
        entity.max_score = max_score
        entity.sort_order = sort_order
        entity.is_active = is_active
        entity.updated_by_id = actor_id
        self._commit_audit("catalog.maturity_level.update", entity, actor_id, before)
        return entity

    def create_answer_set(self, *, external_code: str, name: str, description: str | None, options: list[dict[str, Any]], actor_id: int) -> AnswerSet:
        normalized = external_code.strip().upper()
        if db.session.scalar(select(AnswerSet).where(AnswerSet.external_code == normalized)):
            raise DomainError("Ya existe un conjunto con ese código.")
        content_hash = _hash_payload(options)
        entity = AnswerSet(external_code=normalized, name=name.strip(), description=(description or "").strip() or None, content_hash=content_hash, created_by_id=actor_id, updated_by_id=actor_id)
        db.session.add(entity)
        db.session.flush()
        self._replace_options(entity, options, actor_id)
        self._commit_audit("catalog.answer_set.create", entity, actor_id)
        return entity

    def update_answer_set(self, entity: AnswerSet, *, external_code: str, name: str, description: str | None, options: list[dict[str, Any]], is_active: bool, actor_id: int) -> AnswerSet:
        used = db.session.scalar(select(func.count(QuestionRevision.id)).where(QuestionRevision.answer_set_id == entity.id)) or 0
        if used:
            raise DomainError("El conjunto ya está asociado a revisiones. Duplica el conjunto para preservar el historial.")
        normalized = external_code.strip().upper()
        duplicate = db.session.scalar(select(AnswerSet).where(AnswerSet.external_code == normalized, AnswerSet.id != entity.id))
        if duplicate:
            raise DomainError("Ya existe un conjunto con ese código.")
        before = {**self._master_snapshot(entity), "options": self._option_snapshot(entity)}
        entity.external_code = normalized
        entity.name = name.strip()
        entity.description = (description or "").strip() or None
        entity.content_hash = _hash_payload(options)
        entity.is_active = is_active
        entity.updated_by_id = actor_id
        self._replace_options(entity, options, actor_id)
        audit_service.record(action="catalog.answer_set.update", entity_type="AnswerSet", entity_public_id=entity.public_id, actor_user_id=actor_id, before=before, after={**self._master_snapshot(entity), "options": options})
        db.session.commit()
        return entity

    def create_question(self, *, external_code: str, canonical_name: str | None, business_function_id: int, security_practice_id: int, practice_stream_id: int, maturity_level_id: int, answer_set_id: int, question_text: str, guidance_text: str | None, criteria: list[str], change_reason: str | None, actor_id: int) -> Question:
        normalized = external_code.strip().upper()
        if db.session.scalar(select(Question).where(Question.external_code == normalized)):
            raise DomainError("Ya existe una pregunta con ese identificador.")
        self._validate_hierarchy(business_function_id, security_practice_id, practice_stream_id)
        question = Question(external_code=normalized, canonical_name=(canonical_name or question_text)[:240], current_revision_number=1, created_by_id=actor_id, updated_by_id=actor_id)
        db.session.add(question)
        db.session.flush()
        self._create_revision(question, revision_number=1, business_function_id=business_function_id, security_practice_id=security_practice_id, practice_stream_id=practice_stream_id, maturity_level_id=maturity_level_id, answer_set_id=answer_set_id, question_text=question_text, guidance_text=guidance_text, criteria=criteria, change_reason=change_reason or "Creación manual", actor_id=actor_id, supersedes_revision_id=None)
        audit_service.record(action="catalog.question.create", entity_type="Question", entity_public_id=question.public_id, actor_user_id=actor_id, after={"external_code": normalized, "revision": 1})
        db.session.commit()
        return question

    def revise_question(self, question: Question, *, canonical_name: str | None, business_function_id: int, security_practice_id: int, practice_stream_id: int, maturity_level_id: int, answer_set_id: int, question_text: str, guidance_text: str | None, criteria: list[str], change_reason: str, is_active: bool, actor_id: int) -> QuestionRevision:
        if not change_reason.strip():
            raise DomainError("Debes indicar el motivo de la nueva revisión.")
        self._validate_hierarchy(business_function_id, security_practice_id, practice_stream_id)
        current = question.current_revision
        next_number = (db.session.scalar(select(func.max(QuestionRevision.revision_number)).where(QuestionRevision.question_id == question.id)) or 0) + 1
        revision = self._create_revision(question, revision_number=next_number, business_function_id=business_function_id, security_practice_id=security_practice_id, practice_stream_id=practice_stream_id, maturity_level_id=maturity_level_id, answer_set_id=answer_set_id, question_text=question_text, guidance_text=guidance_text, criteria=criteria, change_reason=change_reason.strip(), actor_id=actor_id, supersedes_revision_id=current.id if current else None)
        question.current_revision_number = next_number
        question.canonical_name = (canonical_name or question_text)[:240]
        question.is_active = is_active
        question.updated_by_id = actor_id
        audit_service.record(action="catalog.question.revise", entity_type="Question", entity_public_id=question.public_id, actor_user_id=actor_id, before={"revision": current.revision_number if current else None}, after={"revision": next_number, "change_reason": change_reason})
        db.session.commit()
        return revision

    def duplicate_question(self, source: Question, *, new_external_code: str, actor_id: int) -> Question:
        revision = source.current_revision
        if revision is None:
            raise DomainError("La pregunta origen no tiene una revisión vigente.")
        return self.create_question(
            external_code=new_external_code,
            canonical_name=f"Copia de {source.canonical_name or source.external_code}",
            business_function_id=revision.business_function_id,
            security_practice_id=revision.security_practice_id,
            practice_stream_id=revision.practice_stream_id,
            maturity_level_id=revision.maturity_level_id,
            answer_set_id=revision.answer_set_id,
            question_text=revision.question_text,
            guidance_text=revision.guidance_text,
            criteria=[criterion.criterion_text for criterion in revision.criteria],
            change_reason=f"Duplicada desde {source.external_code}",
            actor_id=actor_id,
        )

    def _create_revision(self, question: Question, *, revision_number: int, business_function_id: int, security_practice_id: int, practice_stream_id: int, maturity_level_id: int, answer_set_id: int, question_text: str, guidance_text: str | None, criteria: list[str], change_reason: str, actor_id: int, supersedes_revision_id: int | None) -> QuestionRevision:
        payload = {
            "business_function_id": business_function_id,
            "security_practice_id": security_practice_id,
            "practice_stream_id": practice_stream_id,
            "maturity_level_id": maturity_level_id,
            "answer_set_id": answer_set_id,
            "question_text": question_text.strip(),
            "guidance_text": (guidance_text or "").strip() or None,
            "criteria": criteria,
        }
        revision = QuestionRevision(
            question_id=question.id,
            revision_number=revision_number,
            business_function_id=business_function_id,
            security_practice_id=security_practice_id,
            practice_stream_id=practice_stream_id,
            maturity_level_id=maturity_level_id,
            answer_set_id=answer_set_id,
            question_text=payload["question_text"],
            guidance_text=payload["guidance_text"],
            content_hash=_hash_payload(payload),
            supersedes_revision_id=supersedes_revision_id,
            change_reason=change_reason,
            status=QuestionRevisionStatus.DRAFT,
            created_by_id=actor_id,
            updated_by_id=actor_id,
        )
        db.session.add(revision)
        db.session.flush()
        for order, text in enumerate(criteria, start=1):
            cleaned = text.strip()
            if cleaned:
                db.session.add(QuestionQualityCriterion(question_revision_id=revision.id, criterion_text=cleaned, sort_order=order, created_by_id=actor_id, updated_by_id=actor_id))
        return revision

    @staticmethod
    def _replace_options(entity: AnswerSet, options: list[dict[str, Any]], actor_id: int) -> None:
        for existing in list(entity.options):
            db.session.delete(existing)
        db.session.flush()
        seen: set[str] = set()
        for order, option in enumerate(options, start=1):
            code = str(option["option_code"]).strip().upper()
            if not code or code in seen:
                raise DomainError("Los códigos de alternativa deben ser únicos y no vacíos.")
            seen.add(code)
            weight = Decimal(str(option["weight"]))
            if weight < 0 or weight > 1:
                raise DomainError("Las ponderaciones deben estar entre 0 y 1.")
            db.session.add(AnswerOption(answer_set_id=entity.id, option_code=code, text=str(option["text"]).strip(), weight=weight, sort_order=order, created_by_id=actor_id, updated_by_id=actor_id))

    @staticmethod
    def _validate_hierarchy(function_id: int, practice_id: int, stream_id: int) -> None:
        practice = db.session.get(SecurityPractice, practice_id)
        stream = db.session.get(PracticeStream, stream_id)
        if practice is None or practice.business_function_id != function_id:
            raise DomainError("La práctica no pertenece a la función seleccionada.")
        if stream is None or stream.security_practice_id != practice_id:
            raise DomainError("El flujo no pertenece a la práctica seleccionada.")

    @staticmethod
    def _master_snapshot(entity) -> dict[str, Any]:
        return {key: getattr(entity, key, None) for key in ("code", "external_code", "name", "description", "sort_order", "is_active") if hasattr(entity, key)}

    @staticmethod
    def _option_snapshot(entity: AnswerSet) -> list[dict[str, Any]]:
        return [{"option_code": option.option_code, "text": option.text, "weight": str(option.weight)} for option in entity.options]

    def _commit_audit(self, action: str, entity, actor_id: int, before: dict[str, Any] | None = None) -> None:
        db.session.flush()
        audit_service.record(action=action, entity_type=type(entity).__name__, entity_public_id=entity.public_id, actor_user_id=actor_id, before=before, after=self._master_snapshot(entity))
        db.session.commit()


catalog_service = CatalogService()
