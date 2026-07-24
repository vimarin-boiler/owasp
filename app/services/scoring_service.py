from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from typing import Iterable

from sqlalchemy import update

from app.common.errors import ConflictError, ValidationError
from app.enums import AssessmentStatus, ResponseStatus, ScoringSource
from app.extensions import db
from app.models import Assessment, AssessmentQuestion, AssessmentScoreItem, AssessmentScoreSnapshot
from app.models.base import utc_now
from app.repositories import assessment_repository, scoring_repository
from app.services.audit_service import audit_service

CALCULATION_VERSION = "samm-3-level-v1"
ZERO = Decimal("0")
ONE = Decimal("1")
THREE = Decimal("3")
HUNDRED = Decimal("100")
FOUR_PLACES = Decimal("0.0001")


@dataclass(slots=True)
class ScoreDimension:
    dimension_type: str
    key: str
    name: str
    parent_key: str | None
    score: Decimal
    max_score: Decimal
    normalized_percent: Decimal
    target_score: Decimal | None
    gap: Decimal | None
    applicable_count: int
    not_applicable_count: int
    pending_count: int
    sort_order: int
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "dimension_type": self.dimension_type,
            "key": self.key,
            "name": self.name,
            "parent_key": self.parent_key,
            "score": float(self.score),
            "max_score": float(self.max_score),
            "normalized_percent": float(self.normalized_percent),
            "target_score": float(self.target_score) if self.target_score is not None else None,
            "gap": float(self.gap) if self.gap is not None else None,
            "applicable_count": self.applicable_count,
            "not_applicable_count": self.not_applicable_count,
            "pending_count": self.pending_count,
            "sort_order": self.sort_order,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ScoreResult:
    assessment_id: int
    source: ScoringSource
    input_hash: str
    overall_score: Decimal
    progress_percent: Decimal
    target_score: Decimal | None
    gap: Decimal | None
    dimensions: list[ScoreDimension]
    status_summary: dict
    calculation_metadata: dict
    snapshot: AssessmentScoreSnapshot | None = None

    def by_type(self, dimension_type: str) -> list[ScoreDimension]:
        return [item for item in self.dimensions if item.dimension_type == dimension_type]

    def as_dict(self, *, include_questions: bool = False) -> dict:
        dimensions = self.dimensions if include_questions else [
            item for item in self.dimensions if item.dimension_type != "question"
        ]
        return {
            "source": self.source.value,
            "calculation_version": CALCULATION_VERSION,
            "input_hash": self.input_hash,
            "overall_score": float(self.overall_score),
            "progress_percent": float(self.progress_percent),
            "target_score": float(self.target_score) if self.target_score is not None else None,
            "gap": float(self.gap) if self.gap is not None else None,
            "status_summary": self.status_summary,
            "metadata": self.calculation_metadata,
            "dimensions": [item.as_dict() for item in dimensions],
            "snapshot": {
                "id": self.snapshot.public_id,
                "number": self.snapshot.snapshot_number,
                "calculated_at": self.snapshot.calculated_at.isoformat(),
                "published": self.snapshot.is_published_snapshot,
            } if self.snapshot else None,
        }


@dataclass(slots=True)
class _QuestionPoint:
    question: AssessmentQuestion
    eligible: bool
    not_applicable: bool
    score: Decimal
    pending: bool


class ScoringService:
    @staticmethod
    def _q(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)

    @staticmethod
    def _clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
        return min(max(value, minimum), maximum)

    @staticmethod
    def _source_eligible(question: AssessmentQuestion, source: ScoringSource) -> bool:
        response = question.response
        if response is None:
            return False
        if source == ScoringSource.DECLARED:
            return response.status in {
                ResponseStatus.ANSWERED,
                ResponseStatus.SUBMITTED,
                ResponseStatus.OBSERVED,
                ResponseStatus.REJECTED,
                ResponseStatus.APPROVED,
            }
        if source == ScoringSource.REVIEWED:
            return response.reviewed_at is not None and response.status in {
                ResponseStatus.OBSERVED,
                ResponseStatus.REJECTED,
                ResponseStatus.APPROVED,
            }
        return response.status == ResponseStatus.APPROVED

    def _point(self, question: AssessmentQuestion, source: ScoringSource) -> _QuestionPoint:
        response = question.response
        eligible = self._source_eligible(question, source)
        not_applicable = bool(eligible and response and response.is_not_applicable)
        selected = ZERO
        if eligible and not not_applicable and response and response.selected_weight_snapshot is not None:
            selected = self._clamp(Decimal(response.selected_weight_snapshot), ZERO, ONE)
        pending = not eligible
        return _QuestionPoint(
            question=question,
            eligible=eligible,
            not_applicable=not_applicable,
            score=selected,
            pending=pending,
        )

    @staticmethod
    def _snapshot_value(snapshot: dict, key: str, fallback: str = "") -> str:
        value = snapshot.get(key, fallback)
        return str(value) if value is not None else fallback

    def input_hash(self, assessment: Assessment, questions: Iterable[AssessmentQuestion], source: ScoringSource) -> str:
        payload = {
            "calculation_version": CALCULATION_VERSION,
            "assessment_id": assessment.id,
            "source": source.value,
            "target": str(assessment.target_maturity_level) if assessment.target_maturity_level is not None else None,
            "questions": [],
        }
        for question in sorted(questions, key=lambda item: (item.sort_order, item.id)):
            response = question.response
            payload["questions"].append({
                "id": question.id,
                "required": question.is_required,
                "level": question.maturity_level_snapshot.get("number"),
                "status": question.current_status.value,
                "response_version": response.response_version if response else None,
                "weight": str(response.selected_weight_snapshot) if response and response.selected_weight_snapshot is not None else None,
                "not_applicable": response.is_not_applicable if response else False,
                "reviewed_at": response.reviewed_at.isoformat() if response and response.reviewed_at else None,
            })
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _target_for_level(self, target: Decimal | None, level: int) -> Decimal | None:
        if target is None:
            return None
        return self._q(self._clamp(target - Decimal(level - 1), ZERO, ONE))

    def _dimension(
        self,
        *,
        dimension_type: str,
        key: str,
        name: str,
        parent_key: str | None,
        score: Decimal,
        max_score: Decimal,
        target_score: Decimal | None,
        applicable_count: int,
        not_applicable_count: int,
        pending_count: int,
        sort_order: int,
        metadata: dict | None = None,
    ) -> ScoreDimension:
        score = self._q(score)
        max_score = self._q(max_score)
        normalized = self._q((score / max_score) * HUNDRED) if max_score > ZERO else ZERO
        gap = self._q(max(target_score - score, ZERO)) if target_score is not None else None
        return ScoreDimension(
            dimension_type=dimension_type,
            key=key,
            name=name,
            parent_key=parent_key,
            score=score,
            max_score=max_score,
            normalized_percent=normalized,
            target_score=self._q(target_score) if target_score is not None else None,
            gap=gap,
            applicable_count=applicable_count,
            not_applicable_count=not_applicable_count,
            pending_count=pending_count,
            sort_order=sort_order,
            metadata=metadata or {},
        )

    def calculate(
        self,
        assessment: Assessment,
        *,
        source: ScoringSource | None = None,
        persist: bool = False,
        actor_id: int | None = None,
        force_snapshot: bool = False,
        commit: bool = True,
    ) -> ScoreResult:
        resolved_source = source or assessment.scoring_source
        questions = assessment_repository.questions(assessment.id)
        target = Decimal(assessment.target_maturity_level) if assessment.target_maturity_level is not None else None
        points = [self._point(question, resolved_source) for question in questions]
        input_hash = self.input_hash(assessment, questions, resolved_source)
        progress = self._progress_summary(questions, points)
        dimensions: list[ScoreDimension] = []
        order = 0

        # Question and level dimensions.
        level_groups: dict[tuple[str, str, str, int], list[_QuestionPoint]] = defaultdict(list)
        names: dict[tuple[str, str, str, int], tuple[str, str, str, str]] = {}
        for point in points:
            question = point.question
            function_code = self._snapshot_value(question.business_function_snapshot, "code")
            practice_code = self._snapshot_value(question.security_practice_snapshot, "code")
            stream_code = self._snapshot_value(question.practice_stream_snapshot, "code")
            level = int(question.maturity_level_snapshot.get("number", 0) or 0)
            function_name = self._snapshot_value(question.business_function_snapshot, "name", function_code)
            practice_name = self._snapshot_value(question.security_practice_snapshot, "name", practice_code)
            stream_name = self._snapshot_value(question.practice_stream_snapshot, "name", stream_code)
            key_tuple = (function_code, practice_code, stream_code, level)
            names[key_tuple] = (function_name, practice_name, stream_name, question.maturity_level_snapshot.get("name", f"Nivel {level}"))
            level_groups[key_tuple].append(point)
            q_key = f"question:{question.public_id}"
            level_key = f"level:{function_code}:{practice_code}:{stream_code}:{level}"
            order += 1
            dimensions.append(self._dimension(
                dimension_type="question",
                key=q_key,
                name=f"{question.external_code_snapshot} · {question.question_text_snapshot}",
                parent_key=level_key,
                score=point.score,
                max_score=ONE if not point.not_applicable else ZERO,
                target_score=self._target_for_level(target, level),
                applicable_count=0 if point.not_applicable else 1,
                not_applicable_count=1 if point.not_applicable else 0,
                pending_count=1 if point.pending else 0,
                sort_order=order,
                metadata={
                    "external_code": question.external_code_snapshot,
                    "question_public_id": question.public_id,
                    "status": question.current_status.value,
                    "function_code": function_code,
                    "practice_code": practice_code,
                    "stream_code": stream_code,
                    "level": level,
                },
            ))

        level_dimensions: dict[tuple[str, str, str, int], ScoreDimension] = {}
        for key_tuple in sorted(level_groups, key=lambda item: (item[0], item[1], item[2], item[3])):
            function_code, practice_code, stream_code, level = key_tuple
            group = level_groups[key_tuple]
            applicable = [point for point in group if not point.not_applicable]
            score = sum((point.score for point in applicable), ZERO) / Decimal(len(applicable)) if applicable else ZERO
            function_name, practice_name, stream_name, level_name = names[key_tuple]
            level_key = f"level:{function_code}:{practice_code}:{stream_code}:{level}"
            stream_key = f"stream:{function_code}:{practice_code}:{stream_code}"
            order += 1
            dimension = self._dimension(
                dimension_type="level",
                key=level_key,
                name=f"{stream_name} · Nivel {level}",
                parent_key=stream_key,
                score=score,
                max_score=ONE if applicable else ZERO,
                target_score=self._target_for_level(target, level),
                applicable_count=len(applicable),
                not_applicable_count=sum(point.not_applicable for point in group),
                pending_count=sum(point.pending for point in applicable),
                sort_order=order,
                metadata={
                    "function_code": function_code,
                    "function_name": function_name,
                    "practice_code": practice_code,
                    "practice_name": practice_name,
                    "stream_code": stream_code,
                    "stream_name": stream_name,
                    "level": level,
                    "level_name": str(level_name),
                },
            )
            level_dimensions[key_tuple] = dimension
            dimensions.append(dimension)

        # Stream maturity is normalized back to a comparable 0..3 scale.
        stream_groups: dict[tuple[str, str, str], list[ScoreDimension]] = defaultdict(list)
        for (function_code, practice_code, stream_code, _), dimension in level_dimensions.items():
            stream_groups[(function_code, practice_code, stream_code)].append(dimension)
        stream_dimensions: dict[tuple[str, str, str], ScoreDimension] = {}
        for key_tuple in sorted(stream_groups):
            function_code, practice_code, stream_code = key_tuple
            group = stream_groups[key_tuple]
            applicable_levels = [item for item in group if item.max_score > ZERO]
            raw = sum((item.score for item in applicable_levels), ZERO)
            normalized_score = (raw / Decimal(len(applicable_levels))) * THREE if applicable_levels else ZERO
            sample = group[0].metadata
            stream_key = f"stream:{function_code}:{practice_code}:{stream_code}"
            practice_key = f"practice:{function_code}:{practice_code}"
            order += 1
            dimension = self._dimension(
                dimension_type="stream",
                key=stream_key,
                name=sample["stream_name"],
                parent_key=practice_key,
                score=normalized_score,
                max_score=THREE if applicable_levels else ZERO,
                target_score=target,
                applicable_count=sum(item.applicable_count for item in group),
                not_applicable_count=sum(item.not_applicable_count for item in group),
                pending_count=sum(item.pending_count for item in group),
                sort_order=order,
                metadata={
                    "function_code": function_code,
                    "function_name": sample["function_name"],
                    "practice_code": practice_code,
                    "practice_name": sample["practice_name"],
                    "stream_code": stream_code,
                    "stream_name": sample["stream_name"],
                },
            )
            stream_dimensions[key_tuple] = dimension
            dimensions.append(dimension)

        practice_groups: dict[tuple[str, str], list[ScoreDimension]] = defaultdict(list)
        for (function_code, practice_code, _), dimension in stream_dimensions.items():
            practice_groups[(function_code, practice_code)].append(dimension)
        practice_dimensions: dict[tuple[str, str], ScoreDimension] = {}
        for key_tuple in sorted(practice_groups):
            function_code, practice_code = key_tuple
            group = practice_groups[key_tuple]
            applicable_group = [item for item in group if item.max_score > ZERO]
            score = sum((item.score for item in applicable_group), ZERO) / Decimal(len(applicable_group)) if applicable_group else ZERO
            sample = group[0].metadata
            practice_key = f"practice:{function_code}:{practice_code}"
            function_key = f"function:{function_code}"
            order += 1
            dimension = self._dimension(
                dimension_type="practice",
                key=practice_key,
                name=sample["practice_name"],
                parent_key=function_key,
                score=score,
                max_score=THREE if applicable_group else ZERO,
                target_score=target,
                applicable_count=sum(item.applicable_count for item in group),
                not_applicable_count=sum(item.not_applicable_count for item in group),
                pending_count=sum(item.pending_count for item in group),
                sort_order=order,
                metadata={
                    "function_code": function_code,
                    "function_name": sample["function_name"],
                    "practice_code": practice_code,
                    "practice_name": sample["practice_name"],
                },
            )
            practice_dimensions[key_tuple] = dimension
            dimensions.append(dimension)

        function_groups: dict[str, list[ScoreDimension]] = defaultdict(list)
        for (function_code, _), dimension in practice_dimensions.items():
            function_groups[function_code].append(dimension)
        function_dimensions: list[ScoreDimension] = []
        for function_code in sorted(function_groups):
            group = function_groups[function_code]
            applicable_group = [item for item in group if item.max_score > ZERO]
            score = sum((item.score for item in applicable_group), ZERO) / Decimal(len(applicable_group)) if applicable_group else ZERO
            function_name = group[0].metadata["function_name"]
            function_key = f"function:{function_code}"
            order += 1
            dimension = self._dimension(
                dimension_type="function",
                key=function_key,
                name=function_name,
                parent_key="overall",
                score=score,
                max_score=THREE if applicable_group else ZERO,
                target_score=target,
                applicable_count=sum(item.applicable_count for item in group),
                not_applicable_count=sum(item.not_applicable_count for item in group),
                pending_count=sum(item.pending_count for item in group),
                sort_order=order,
                metadata={"function_code": function_code, "function_name": function_name},
            )
            function_dimensions.append(dimension)
            dimensions.append(dimension)

        applicable_functions = [item for item in function_dimensions if item.max_score > ZERO]
        overall_score = (
            sum((item.score for item in applicable_functions), ZERO) / Decimal(len(applicable_functions))
            if applicable_functions else ZERO
        )
        overall = self._dimension(
            dimension_type="overall",
            key="overall",
            name="Madurez general",
            parent_key=None,
            score=overall_score,
            max_score=THREE if applicable_functions else ZERO,
            target_score=target,
            applicable_count=sum(item.applicable_count for item in function_dimensions),
            not_applicable_count=sum(item.not_applicable_count for item in function_dimensions),
            pending_count=sum(item.pending_count for item in function_dimensions),
            sort_order=0,
            metadata={},
        )
        dimensions.insert(0, overall)

        result = ScoreResult(
            assessment_id=assessment.id,
            source=resolved_source,
            input_hash=input_hash,
            overall_score=overall.score,
            progress_percent=self._q(Decimal(str(progress["progress_percent"]))),
            target_score=overall.target_score,
            gap=overall.gap,
            dimensions=dimensions,
            status_summary=progress,
            calculation_metadata={
                "calculation_version": CALCULATION_VERSION,
                "scale": "0-3",
                "not_applicable_policy": "excluded_from_denominator",
                "pending_policy": "included_as_zero",
                "source_policy": self._source_policy(resolved_source),
            },
        )
        if persist:
            result.snapshot = self._persist(
                assessment,
                result,
                actor_id=actor_id,
                force=force_snapshot,
                commit=commit,
            )
        return result

    def _progress_summary(self, questions: list[AssessmentQuestion], points: list[_QuestionPoint]) -> dict:
        statuses = {status.value: 0 for status in ResponseStatus}
        evidence_pending = 0
        evidence_valid = 0
        evidence_rejected = 0
        for question in questions:
            statuses[question.current_status.value] += 1
            for evidence in question.evidences:
                if not evidence.is_active:
                    continue
                state = evidence.validation_status.value
                if state == "valid":
                    evidence_valid += 1
                elif state == "rejected":
                    evidence_rejected += 1
                else:
                    evidence_pending += 1
        total = len(questions)
        completed = sum(
            statuses[value]
            for value in ["answered", "submitted", "observed", "rejected", "approved"]
        )
        return {
            "total_questions": total,
            "completed_questions": completed,
            "progress_percent": round((completed / total) * 100, 2) if total else 0.0,
            "applicable_questions": sum(not point.not_applicable for point in points),
            "not_applicable_questions": sum(point.not_applicable for point in points),
            "pending_for_source": sum(point.pending and not point.not_applicable for point in points),
            "statuses": statuses,
            "evidences": {
                "pending": evidence_pending,
                "valid": evidence_valid,
                "rejected": evidence_rejected,
            },
        }

    @staticmethod
    def _source_policy(source: ScoringSource) -> str:
        return {
            ScoringSource.DECLARED: "answered_or_later",
            ScoringSource.REVIEWED: "reviewed_response",
            ScoringSource.APPROVED: "approved_only",
        }[source]

    def _persist(
        self,
        assessment: Assessment,
        result: ScoreResult,
        *,
        actor_id: int | None,
        force: bool,
        commit: bool,
    ) -> AssessmentScoreSnapshot:
        latest = scoring_repository.latest(assessment.id, result.source)
        if latest and latest.input_hash == result.input_hash and not force:
            return latest
        snapshot = AssessmentScoreSnapshot(
            assessment_id=assessment.id,
            snapshot_number=scoring_repository.next_number(assessment.id),
            scoring_source=result.source,
            calculated_by_id=actor_id,
            overall_score=result.overall_score,
            progress_percent=result.progress_percent,
            calculation_version=CALCULATION_VERSION,
            input_hash=result.input_hash,
            status_summary=result.status_summary,
            calculation_metadata=result.calculation_metadata,
            is_published_snapshot=False,
        )
        for item in result.dimensions:
            snapshot.items.append(AssessmentScoreItem(
                dimension_type=item.dimension_type,
                dimension_key=item.key,
                dimension_name=item.name[:240],
                parent_key=item.parent_key,
                sort_order=item.sort_order,
                dimension_metadata=item.metadata,
                score=item.score,
                max_score=item.max_score,
                normalized_percent=item.normalized_percent,
                target_score=item.target_score,
                gap=item.gap,
                applicable_count=item.applicable_count,
                not_applicable_count=item.not_applicable_count,
                pending_count=item.pending_count,
            ))
        db.session.add(snapshot)
        db.session.flush()
        audit_service.record(
            action="assessment.score_calculated",
            entity_type="assessment_score_snapshot",
            entity_public_id=snapshot.public_id,
            actor_user_id=actor_id,
            organization_id=assessment.organization_id,
            assessment_id=assessment.id,
            after={
                "snapshot_number": snapshot.snapshot_number,
                "source": result.source.value,
                "overall_score": str(result.overall_score),
                "progress_percent": str(result.progress_percent),
                "input_hash": result.input_hash,
            },
        )
        if commit:
            db.session.commit()
        return snapshot

    def publish(self, assessment: Assessment, *, actor_id: int) -> AssessmentScoreSnapshot:
        if assessment.status not in {AssessmentStatus.COMPLETED, AssessmentStatus.PUBLISHED}:
            raise ConflictError("Los resultados solo pueden publicarse cuando el assessment está completado.")
        result = self.calculate(
            assessment,
            source=assessment.scoring_source,
            persist=True,
            actor_id=actor_id,
            force_snapshot=True,
            commit=False,
        )
        if result.snapshot is None:
            raise ValidationError("No fue posible generar el snapshot de resultados.")
        db.session.execute(
            update(AssessmentScoreSnapshot)
            .where(
                AssessmentScoreSnapshot.assessment_id == assessment.id,
                AssessmentScoreSnapshot.id != result.snapshot.id,
            )
            .values(is_published_snapshot=False)
        )
        result.snapshot.is_published_snapshot = True
        assessment.status = AssessmentStatus.PUBLISHED
        assessment.results_published_at = utc_now()
        assessment.updated_by_id = actor_id
        audit_service.record(
            action="assessment.results_published",
            entity_type="assessment",
            entity_public_id=assessment.public_id,
            actor_user_id=actor_id,
            organization_id=assessment.organization_id,
            assessment_id=assessment.id,
            after={
                "snapshot": result.snapshot.public_id,
                "snapshot_number": result.snapshot.snapshot_number,
                "source": assessment.scoring_source.value,
                "overall_score": str(result.overall_score),
            },
        )
        db.session.commit()
        return result.snapshot

    def from_snapshot(self, snapshot: AssessmentScoreSnapshot) -> ScoreResult:
        dimensions = [
            ScoreDimension(
                dimension_type=item.dimension_type,
                key=item.dimension_key,
                name=item.dimension_name,
                parent_key=item.parent_key,
                score=Decimal(item.score),
                max_score=Decimal(item.max_score),
                normalized_percent=Decimal(item.normalized_percent),
                target_score=Decimal(item.target_score) if item.target_score is not None else None,
                gap=Decimal(item.gap) if item.gap is not None else None,
                applicable_count=item.applicable_count,
                not_applicable_count=item.not_applicable_count,
                pending_count=item.pending_count,
                sort_order=item.sort_order,
                metadata=item.dimension_metadata or {},
            )
            for item in sorted(snapshot.items, key=lambda value: (value.sort_order, value.id))
        ]
        overall = next((item for item in dimensions if item.dimension_type == "overall"), None)
        return ScoreResult(
            assessment_id=snapshot.assessment_id,
            source=snapshot.scoring_source,
            input_hash=snapshot.input_hash,
            overall_score=Decimal(snapshot.overall_score),
            progress_percent=Decimal(snapshot.progress_percent),
            target_score=overall.target_score if overall else None,
            gap=overall.gap if overall else None,
            dimensions=dimensions,
            status_summary=snapshot.status_summary or {},
            calculation_metadata=snapshot.calculation_metadata or {},
            snapshot=snapshot,
        )


scoring_service = ScoringService()
