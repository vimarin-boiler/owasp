from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from flask import current_app
from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog, ResponseHistory, Review, User
from app.repositories import assessment_repository, recommendation_repository, scoring_repository
from app.services.scoring_service import ScoreResult, scoring_service


PRIORITY_LABELS = {
    "critical": "Crítica",
    "high": "Alta",
    "medium": "Media",
    "low": "Baja",
}
STATUS_LABELS = {
    "open": "Abierta",
    "planned": "Planificada",
    "in_progress": "En progreso",
    "completed": "Completada",
    "dismissed": "Descartada",
}
RESPONSE_STATUS_LABELS = {
    "unanswered": "Sin responder",
    "draft": "Borrador",
    "answered": "Respondida",
    "submitted": "Enviada a revisión",
    "observed": "Observada",
    "rejected": "Rechazada",
    "approved": "Aprobada",
}
HORIZON_ORDER = ("0-30 días", "31-90 días", "3-6 meses", "6-12 meses", "Sin horizonte")


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _label(value: Any) -> str:
    return getattr(value, "value", str(value))


class ReportDataService:
    """Builds a serializable, presentation-neutral report payload."""

    def resolve_result(self, assessment, *, published_only: bool) -> ScoreResult:
        if published_only:
            snapshot = scoring_repository.published(assessment.id)
            if snapshot is None:
                raise LookupError("El assessment no posee un snapshot de resultados publicado.")
            return scoring_service.from_snapshot(snapshot)
        return scoring_service.calculate(assessment, persist=False)

    def build(self, assessment, *, published_only: bool = False) -> dict:
        result = self.resolve_result(assessment, published_only=published_only)
        questions = assessment_repository.questions(assessment.id)
        recommendations = recommendation_repository.for_assessment(assessment.id)
        function_items = sorted(result.by_type("function"), key=lambda item: (item.sort_order, item.name))
        practice_items = sorted(result.by_type("practice"), key=lambda item: (item.sort_order, item.name))
        stream_items = sorted(result.by_type("stream"), key=lambda item: (item.sort_order, item.name))
        level_items = sorted(result.by_type("level"), key=lambda item: (item.sort_order, item.name))

        question_rows = []
        evidence_rows = []
        observed_rows = []
        for question in questions:
            response = question.response
            status = response.status.value if response else question.current_status.value
            row = {
                "public_id": question.public_id,
                "code": question.external_code_snapshot,
                "question": question.question_text_snapshot,
                "guidance": question.guidance_snapshot or "",
                "criteria": list(question.criteria_snapshot or []),
                "function": question.business_function_snapshot.get("name", ""),
                "practice": question.security_practice_snapshot.get("name", ""),
                "stream": question.practice_stream_snapshot.get("name", ""),
                "level": question.maturity_level_snapshot.get("number"),
                "status": status,
                "status_label": RESPONSE_STATUS_LABELS.get(status, status),
                "answer": response.selected_option_text_snapshot if response else None,
                "weight": _number(response.selected_weight_snapshot) if response else None,
                "not_applicable": bool(response and response.is_not_applicable),
                "not_applicable_justification": response.not_applicable_justification if response else None,
                "respondent_comment": response.respondent_comment if response else None,
                "reviewer_comment": response.reviewer_comment if response else None,
                "respondent": response.respondent.display_name if response and response.respondent else None,
                "reviewer": response.reviewer.display_name if response and response.reviewer else None,
                "submitted_at": _iso(response.submitted_at) if response else None,
                "reviewed_at": _iso(response.reviewed_at) if response else None,
                "evidence_count": sum(1 for item in question.evidences if item.is_active),
            }
            question_rows.append(row)
            if status in {"observed", "rejected"}:
                observed_rows.append(row)
            for evidence in question.evidences:
                if not evidence.is_active:
                    continue
                evidence_rows.append({
                    "question_code": question.external_code_snapshot,
                    "question": question.question_text_snapshot,
                    "filename": evidence.original_filename,
                    "description": evidence.description or "",
                    "extension": evidence.extension,
                    "mime_type": evidence.detected_mime_type or evidence.reported_mime_type or "",
                    "size_bytes": evidence.size_bytes,
                    "sha256": evidence.sha256,
                    "uploaded_by": evidence.uploaded_by.display_name if evidence.uploaded_by else "",
                    "uploaded_at": _iso(evidence.uploaded_at),
                    "validation_status": evidence.validation_status.value,
                    "review_comment": evidence.review_comment or "",
                    "reviewed_by": evidence.reviewed_by.display_name if evidence.reviewed_by else "",
                    "reviewed_at": _iso(evidence.reviewed_at),
                })

        users = {
            user.id: user.display_name
            for user in db.session.scalars(select(User)).all()
        }
        response_ids = [question.response.id for question in questions if question.response]
        history_rows = []
        review_rows = []
        if response_ids:
            histories = db.session.scalars(
                select(ResponseHistory)
                .where(ResponseHistory.assessment_response_id.in_(response_ids))
                .order_by(ResponseHistory.changed_at)
            ).all()
            question_by_response_id = {
                question.response.id: question for question in questions if question.response
            }
            for history in histories:
                question = question_by_response_id.get(history.assessment_response_id)
                history_rows.append({
                    "question_code": question.external_code_snapshot if question else "",
                    "version": history.response_version,
                    "from": history.transition_from or "",
                    "to": history.transition_to or "",
                    "changed_by": users.get(history.changed_by_id, "Sistema"),
                    "changed_at": _iso(history.changed_at),
                    "reason": history.reason or "",
                })
            reviews = db.session.scalars(
                select(Review)
                .where(Review.assessment_response_id.in_(response_ids))
                .order_by(Review.reviewed_at)
            ).all()
            for review in reviews:
                question = question_by_response_id.get(review.assessment_response_id)
                review_rows.append({
                    "question_code": question.external_code_snapshot if question else "",
                    "response_version": review.response_version,
                    "decision": review.decision.value,
                    "reviewer": users.get(review.reviewer_id, ""),
                    "reviewed_at": _iso(review.reviewed_at),
                    "comment": review.comment or "",
                })

        audits = db.session.scalars(
            select(AuditLog)
            .where(AuditLog.assessment_id == assessment.id)
            .order_by(AuditLog.occurred_at.desc())
            .limit(1000)
        ).all()
        audit_rows = [{
            "occurred_at": _iso(item.occurred_at),
            "actor": users.get(item.actor_user_id, "Sistema"),
            "action": item.action,
            "entity_type": item.entity_type,
            "entity_public_id": item.entity_public_id or "",
            "result": item.result,
            "ip_address": item.ip_address or "",
        } for item in audits]

        assignments = [{
            "name": assignment.user.display_name,
            "email": assignment.user.email,
            "role": assignment.assignment_role.value,
            "lead": assignment.is_lead,
        } for assignment in assessment.assignments]

        recommendation_rows = []
        roadmap = defaultdict(list)
        for item in recommendations:
            horizon = item.time_horizon or "Sin horizonte"
            row = {
                "public_id": item.public_id,
                "title": item.title,
                "description": item.description,
                "risk": item.risk or "",
                "priority": item.priority.value,
                "priority_label": PRIORITY_LABELS.get(item.priority.value, item.priority.value),
                "effort": item.effort or "",
                "owner": item.suggested_owner or "",
                "horizon": horizon,
                "due_date": _iso(item.due_date),
                "dependencies": item.dependencies or "",
                "status": item.status.value,
                "status_label": STATUS_LABELS.get(item.status.value, item.status.value),
                "quick_win": item.is_quick_win,
                "target_level": _number(item.target_maturity_level),
                "dimension_type": item.source_dimension_type or "",
                "dimension_key": item.source_dimension_key or "",
            }
            recommendation_rows.append(row)
            roadmap[horizon].append(row)

        generated_at = datetime.now(timezone.utc)
        logo_path = current_app.config.get("REPORT_LOGO_PATH", "").strip()
        if logo_path:
            candidate = Path(logo_path)
            if not candidate.is_absolute():
                candidate = (Path(current_app.root_path).parent / candidate).resolve()
            logo_path = str(candidate) if candidate.is_file() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg"} else ""
        payload = {
            "schema_version": "1.0",
            "generated_at": generated_at.isoformat(),
            "branding": {
                "company_name": current_app.config.get("REPORT_COMPANY_NAME", "NTT DATA"),
                "classification": current_app.config.get("REPORT_CLASSIFICATION", "Confidencial"),
                "logo_path": logo_path,
            },
            "assessment": {
                "public_id": assessment.public_id,
                "name": assessment.name,
                "description": assessment.description or "",
                "scope": assessment.scope or "",
                "organization": assessment.organization.name,
                "organization_legal_name": assessment.organization.legal_name or "",
                "questionnaire_version": assessment.questionnaire_version.version_number,
                "status": assessment.status.value,
                "start_date": _iso(assessment.start_date),
                "target_date": _iso(assessment.target_date),
                "target_maturity_level": _number(assessment.target_maturity_level),
                "scoring_source": result.source.value,
                "results_published_at": _iso(assessment.results_published_at),
                "assignments": assignments,
            },
            "result": {
                "overall_score": _number(result.overall_score),
                "progress_percent": _number(result.progress_percent),
                "target_score": _number(result.target_score),
                "gap": _number(result.gap),
                "input_hash": result.input_hash,
                "status_summary": result.status_summary,
                "calculation_metadata": result.calculation_metadata,
                "snapshot_number": result.snapshot.snapshot_number if result.snapshot else None,
                "snapshot_public_id": result.snapshot.public_id if result.snapshot else None,
                "snapshot_calculated_at": _iso(result.snapshot.calculated_at) if result.snapshot else None,
                "published_snapshot": bool(result.snapshot and result.snapshot.is_published_snapshot),
            },
            "functions": [item.as_dict() for item in function_items],
            "practices": [item.as_dict() for item in practice_items],
            "streams": [item.as_dict() for item in stream_items],
            "streams_by_gap": [item.as_dict() for item in sorted(stream_items, key=lambda value: (-(value.gap or Decimal("0")), value.name))],
            "levels": [item.as_dict() for item in level_items],
            "questions": question_rows,
            "observed_questions": observed_rows,
            "evidences": evidence_rows,
            "recommendations": recommendation_rows,
            "roadmap": [
                {"horizon": horizon, "items": roadmap.get(horizon, [])}
                for horizon in HORIZON_ORDER
            ],
            "response_history": history_rows,
            "reviews": review_rows,
            "audit_log": audit_rows,
        }
        return payload


report_data_service = ReportDataService()
