from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from app.common.errors import ConflictError, ValidationError
from app.enums import RecommendationPriority, RecommendationStatus
from app.extensions import db
from app.models import (
    Assessment,
    AssessmentQuestion,
    BusinessFunction,
    PracticeStream,
    Recommendation,
    SecurityPractice,
)
from app.models.base import utc_now
from app.repositories import recommendation_repository
from app.services.audit_service import audit_service
from app.services.scoring_service import ScoreDimension, ScoreResult

TIME_HORIZONS = ["0-30 días", "31-90 días", "3-6 meses", "6-12 meses"]
EFFORT_LEVELS = ["Bajo", "Medio", "Alto"]


class RecommendationService:
    @staticmethod
    def _clean(value: str | None) -> str | None:
        resolved = value.strip() if value else ""
        return resolved or None

    @staticmethod
    def _target(value: str | Decimal | None) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            target = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValidationError("El nivel objetivo debe ser numérico.") from exc
        if target < 0 or target > 3:
            raise ValidationError("El nivel objetivo debe estar entre 0 y 3.")
        return target

    def _resolve_dimension(self, assessment: Assessment, dimension_ref: str | None) -> dict:
        result = {
            "source_dimension_type": None,
            "source_dimension_key": None,
            "business_function_id": None,
            "security_practice_id": None,
            "practice_stream_id": None,
            "assessment_question_id": None,
        }
        if not dimension_ref:
            return result
        dimension_type, separator, key = dimension_ref.partition("|")
        if not separator or dimension_type not in {"function", "practice", "stream", "question"}:
            raise ValidationError("La dimensión seleccionada no es válida.")
        result["source_dimension_type"] = dimension_type
        result["source_dimension_key"] = key
        if dimension_type == "question":
            public_id = key.removeprefix("question:")
            question = db.session.scalar(
                select(AssessmentQuestion).where(
                    AssessmentQuestion.assessment_id == assessment.id,
                    AssessmentQuestion.public_id == public_id,
                )
            )
            if question is None:
                raise ValidationError("La pregunta seleccionada no pertenece al assessment.")
            result["assessment_question_id"] = question.id
            result["business_function_id"] = question.source_question_revision.business_function_id
            result["security_practice_id"] = question.source_question_revision.security_practice_id
            result["practice_stream_id"] = question.source_question_revision.practice_stream_id
            return result

        parts = key.split(":")
        if dimension_type == "function" and len(parts) == 2:
            function = db.session.scalar(select(BusinessFunction).where(BusinessFunction.code == parts[1]))
            if function:
                result["business_function_id"] = function.id
        elif dimension_type == "practice" and len(parts) == 3:
            function_code, practice_code = parts[1], parts[2]
            practice = db.session.scalar(
                select(SecurityPractice)
                .join(BusinessFunction)
                .where(BusinessFunction.code == function_code, SecurityPractice.code == practice_code)
            )
            if practice:
                result["business_function_id"] = practice.business_function_id
                result["security_practice_id"] = practice.id
        elif dimension_type == "stream" and len(parts) == 4:
            function_code, practice_code, stream_code = parts[1], parts[2], parts[3]
            stream = db.session.scalar(
                select(PracticeStream)
                .join(SecurityPractice)
                .join(BusinessFunction)
                .where(
                    BusinessFunction.code == function_code,
                    SecurityPractice.code == practice_code,
                    PracticeStream.code == stream_code,
                )
            )
            if stream:
                result["business_function_id"] = stream.security_practice.business_function_id
                result["security_practice_id"] = stream.security_practice_id
                result["practice_stream_id"] = stream.id
        return result

    def create(
        self,
        assessment: Assessment,
        *,
        dimension_ref: str | None,
        title: str,
        description: str,
        risk: str | None,
        priority: RecommendationPriority,
        effort: str | None,
        suggested_owner: str | None,
        time_horizon: str | None,
        due_date: date | None,
        dependencies: str | None,
        status: RecommendationStatus,
        is_quick_win: bool,
        target_maturity_level: str | Decimal | None,
        actor_id: int,
    ) -> Recommendation:
        title = title.strip()
        description = description.strip()
        if not title or not description:
            raise ValidationError("El título y la descripción son obligatorios.")
        if time_horizon and time_horizon not in TIME_HORIZONS:
            raise ValidationError("El horizonte de tiempo no es válido.")
        if effort and effort not in EFFORT_LEVELS:
            raise ValidationError("El esfuerzo seleccionado no es válido.")
        dimension = self._resolve_dimension(assessment, dimension_ref)
        item = Recommendation(
            assessment_id=assessment.id,
            title=title,
            description=description,
            risk=self._clean(risk),
            priority=priority,
            effort=self._clean(effort),
            suggested_owner=self._clean(suggested_owner),
            time_horizon=self._clean(time_horizon),
            due_date=due_date,
            dependencies=self._clean(dependencies),
            status=status,
            is_quick_win=is_quick_win,
            target_maturity_level=self._target(target_maturity_level),
            sort_order=len(recommendation_repository.for_assessment(assessment.id)) + 1,
            created_by_id=actor_id,
            updated_by_id=actor_id,
            **dimension,
        )
        if status == RecommendationStatus.COMPLETED:
            item.completed_at = utc_now()
        db.session.add(item)
        db.session.flush()
        audit_service.record(
            action="recommendation.created",
            entity_type="recommendation",
            entity_public_id=item.public_id,
            actor_user_id=actor_id,
            organization_id=assessment.organization_id,
            assessment_id=assessment.id,
            after=self.serialize(item),
        )
        db.session.commit()
        return item

    def update(self, item: Recommendation, *, actor_id: int, **values) -> Recommendation:
        if not item.is_active:
            raise ConflictError("La recomendación está desactivada.")
        before = self.serialize(item)
        dimension = self._resolve_dimension(item.assessment, values.pop("dimension_ref", None))
        title = str(values.pop("title", "")).strip()
        description = str(values.pop("description", "")).strip()
        if not title or not description:
            raise ValidationError("El título y la descripción son obligatorios.")
        item.title = title
        item.description = description
        item.risk = self._clean(values.pop("risk", None))
        item.priority = values.pop("priority")
        effort = values.pop("effort", None)
        horizon = values.pop("time_horizon", None)
        if effort and effort not in EFFORT_LEVELS:
            raise ValidationError("El esfuerzo seleccionado no es válido.")
        if horizon and horizon not in TIME_HORIZONS:
            raise ValidationError("El horizonte de tiempo no es válido.")
        item.effort = self._clean(effort)
        item.suggested_owner = self._clean(values.pop("suggested_owner", None))
        item.time_horizon = self._clean(horizon)
        item.due_date = values.pop("due_date", None)
        item.dependencies = self._clean(values.pop("dependencies", None))
        new_status = values.pop("status")
        item.completed_at = utc_now() if new_status == RecommendationStatus.COMPLETED else None
        item.status = new_status
        item.is_quick_win = bool(values.pop("is_quick_win", False))
        item.target_maturity_level = self._target(values.pop("target_maturity_level", None))
        for key, value in dimension.items():
            setattr(item, key, value)
        item.updated_by_id = actor_id
        audit_service.record(
            action="recommendation.updated",
            entity_type="recommendation",
            entity_public_id=item.public_id,
            actor_user_id=actor_id,
            organization_id=item.assessment.organization_id,
            assessment_id=item.assessment_id,
            before=before,
            after=self.serialize(item),
        )
        db.session.commit()
        return item

    def deactivate(self, item: Recommendation, *, actor_id: int) -> None:
        if not item.is_active:
            return
        before = self.serialize(item)
        item.deactivate()
        item.updated_by_id = actor_id
        audit_service.record(
            action="recommendation.deactivated",
            entity_type="recommendation",
            entity_public_id=item.public_id,
            actor_user_id=actor_id,
            organization_id=item.assessment.organization_id,
            assessment_id=item.assessment_id,
            before=before,
            after={"is_active": False},
        )
        db.session.commit()

    def change_status(
        self,
        item: Recommendation,
        *,
        status: RecommendationStatus,
        actor_id: int,
    ) -> Recommendation:
        if not item.is_active:
            raise ConflictError("La recomendación está desactivada.")
        before = item.status
        item.status = status
        item.completed_at = utc_now() if status == RecommendationStatus.COMPLETED else None
        item.updated_by_id = actor_id
        audit_service.record(
            action="recommendation.status_changed",
            entity_type="recommendation",
            entity_public_id=item.public_id,
            actor_user_id=actor_id,
            organization_id=item.assessment.organization_id,
            assessment_id=item.assessment_id,
            before={"status": before.value},
            after={"status": status.value},
        )
        db.session.commit()
        return item

    def generate_from_gaps(
        self,
        assessment: Assessment,
        score: ScoreResult,
        *,
        actor_id: int,
        minimum_gap: Decimal = Decimal("0.25"),
    ) -> int:
        existing = {
            item.source_dimension_key
            for item in recommendation_repository.for_assessment(assessment.id)
            if item.source_dimension_key
        }
        candidates = [
            item for item in score.by_type("practice")
            if item.gap is not None and item.gap >= minimum_gap and item.key not in existing
        ]
        candidates.sort(key=lambda item: (-(item.gap or Decimal("0")), item.name.casefold()))
        created = 0
        for index, dimension in enumerate(candidates[:15], start=1):
            priority, horizon = self._priority_and_horizon(dimension)
            recommendation = Recommendation(
                assessment_id=assessment.id,
                source_dimension_type="practice",
                source_dimension_key=dimension.key,
                title=f"Elevar la madurez de {dimension.name}",
                description=(
                    f"Definir e implementar un plan de mejora para cerrar la brecha de madurez de "
                    f"{dimension.gap:.2f} puntos, priorizando las preguntas pendientes y las actividades "
                    f"con menor nivel de cumplimiento dentro de esta práctica."
                ),
                risk=(
                    "La brecha detectada puede producir controles inconsistentes, baja repetibilidad y "
                    "exposición residual en el ciclo de desarrollo seguro."
                ),
                priority=priority,
                effort="Medio" if priority != RecommendationPriority.CRITICAL else "Alto",
                suggested_owner="Responsable de la práctica SAMM",
                time_horizon=horizon,
                status=RecommendationStatus.OPEN,
                is_quick_win=priority in {RecommendationPriority.HIGH, RecommendationPriority.MEDIUM} and dimension.gap <= Decimal("0.75"),
                target_maturity_level=dimension.target_score,
                sort_order=len(existing) + index,
                created_by_id=actor_id,
                updated_by_id=actor_id,
            )
            db.session.add(recommendation)
            existing.add(dimension.key)
            created += 1
        if created:
            audit_service.record(
                action="recommendation.generated_from_gaps",
                entity_type="assessment",
                entity_public_id=assessment.public_id,
                actor_user_id=actor_id,
                organization_id=assessment.organization_id,
                assessment_id=assessment.id,
                after={"created": created, "minimum_gap": str(minimum_gap)},
            )
            db.session.commit()
        return created

    @staticmethod
    def _priority_and_horizon(dimension: ScoreDimension) -> tuple[RecommendationPriority, str]:
        gap = dimension.gap or Decimal("0")
        if gap >= Decimal("1.5"):
            return RecommendationPriority.CRITICAL, "0-30 días"
        if gap >= Decimal("1.0"):
            return RecommendationPriority.HIGH, "31-90 días"
        if gap >= Decimal("0.5"):
            return RecommendationPriority.MEDIUM, "3-6 meses"
        return RecommendationPriority.LOW, "6-12 meses"

    @staticmethod
    def serialize(item: Recommendation) -> dict:
        return {
            "title": item.title,
            "description": item.description,
            "risk": item.risk,
            "priority": item.priority.value,
            "effort": item.effort,
            "suggested_owner": item.suggested_owner,
            "time_horizon": item.time_horizon,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "dependencies": item.dependencies,
            "status": item.status.value,
            "is_quick_win": item.is_quick_win,
            "target_maturity_level": str(item.target_maturity_level) if item.target_maturity_level is not None else None,
            "source_dimension_type": item.source_dimension_type,
            "source_dimension_key": item.source_dimension_key,
            "is_active": item.is_active,
        }


recommendation_service = RecommendationService()
