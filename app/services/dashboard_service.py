from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.enums import AssessmentStatus, EvidenceValidationStatus, ResponseStatus
from app.extensions import db
from app.models import Assessment, Evidence
from app.repositories import assessment_repository, audit_repository, organization_repository, user_repository
from app.services.assessment_service import assessment_service
from app.services.scoring_service import scoring_service


class DashboardService:
    def build(self, user) -> dict:
        is_admin = user.has_role("admin")
        assessments = assessment_repository.list_all() if is_admin else assessment_repository.for_user(user.id)
        all_cards = [self._card(item) for item in assessments]
        cards = all_cards[:8]
        context = {
            "is_admin": is_admin,
            "assessment_cards": cards,
            "average_progress": round(
                sum(card["progress"]["percentage"] for card in all_cards) / len(all_cards), 1
            ) if all_cards else 0,
            "pending_review": len(assessment_repository.pending_review(user.id, is_admin))
            if (is_admin or user.has_role("reviewer")) else 0,
            "respondent_summary": self._respondent_summary(all_cards),
        }
        if is_admin:
            context.update(self._admin_context(assessments))
        return context

    def _card(self, assessment: Assessment) -> dict:
        progress = assessment_service.progress(assessment)
        counts = progress["counts"]
        return {
            "assessment": assessment,
            "progress": progress,
            "pending": counts.get(ResponseStatus.UNANSWERED.value, 0) + counts.get(ResponseStatus.DRAFT.value, 0),
            "observed": counts.get(ResponseStatus.OBSERVED.value, 0),
            "rejected": counts.get(ResponseStatus.REJECTED.value, 0),
            "approved": counts.get(ResponseStatus.APPROVED.value, 0),
            "last_activity": max(
                [assessment.updated_at] + [question.updated_at for question in assessment.questions]
            ),
        }

    @staticmethod
    def _respondent_summary(cards: list[dict]) -> dict:
        return {
            "assigned": len(cards),
            "pending": sum(item["pending"] for item in cards),
            "observed": sum(item["observed"] for item in cards),
            "rejected": sum(item["rejected"] for item in cards),
            "approved": sum(item["approved"] for item in cards),
        }

    def _admin_context(self, assessments: list[Assessment]) -> dict:
        completed = sum(
            assessment.status in {AssessmentStatus.COMPLETED, AssessmentStatus.PUBLISHED, AssessmentStatus.CLOSED}
            for assessment in assessments
        )
        due_limit = date.today() + timedelta(days=14)
        due_soon = [
            assessment for assessment in assessments
            if assessment.target_date
            and date.today() <= assessment.target_date <= due_limit
            and assessment.status not in {AssessmentStatus.COMPLETED, AssessmentStatus.PUBLISHED, AssessmentStatus.CLOSED, AssessmentStatus.CANCELLED}
        ]
        evidence_pending = int(
            db.session.scalar(
                select(func.count(Evidence.id)).where(
                    Evidence.is_active.is_(True),
                    Evidence.validation_status.in_([
                        EvidenceValidationStatus.PENDING,
                        EvidenceValidationStatus.QUARANTINED,
                    ]),
                )
            ) or 0
        )
        function_scores: dict[str, list[Decimal]] = defaultdict(list)
        practice_scores: dict[str, list[Decimal]] = defaultdict(list)
        gap_scores: list[dict] = []
        score_assessments = [
            assessment for assessment in assessments
            if assessment.status not in {AssessmentStatus.DRAFT, AssessmentStatus.CANCELLED}
        ][:40]
        for assessment in score_assessments:
            result = scoring_service.calculate(assessment, persist=False)
            for item in result.by_type("function"):
                function_scores[item.name].append(item.score)
            for item in result.by_type("practice"):
                practice_scores[item.name].append(item.score)
                if item.gap is not None:
                    gap_scores.append({
                        "assessment": assessment.name,
                        "practice": item.name,
                        "gap": float(item.gap),
                    })
        average_functions = [
            {"name": name, "score": float(sum(values, Decimal("0")) / Decimal(len(values)))}
            for name, values in sorted(function_scores.items())
        ]
        average_practices = [
            {"name": name, "score": float(sum(values, Decimal("0")) / Decimal(len(values)))}
            for name, values in sorted(practice_scores.items())
        ]
        progress_distribution = {
            "0-24": 0,
            "25-49": 0,
            "50-74": 0,
            "75-99": 0,
            "100": 0,
        }
        for assessment in assessments:
            value = assessment_service.progress(assessment)["percentage"]
            key = "100" if value >= 100 else "75-99" if value >= 75 else "50-74" if value >= 50 else "25-49" if value >= 25 else "0-24"
            progress_distribution[key] += 1
        return {
            "active_users": user_repository.count_active(),
            "active_organizations": organization_repository.count_active(),
            "recent_activity": audit_repository.recent(10),
            "total_assessments": len(assessments),
            "active_assessments": sum(
                assessment.status not in {AssessmentStatus.CLOSED, AssessmentStatus.CANCELLED}
                for assessment in assessments
            ),
            "completed_assessments": completed,
            "evidence_pending": evidence_pending,
            "due_soon": due_soon,
            "average_functions": average_functions,
            "average_practices": average_practices[:15],
            "largest_gaps": sorted(gap_scores, key=lambda item: -item["gap"])[:12],
            "progress_distribution": progress_distribution,
        }


dashboard_service = DashboardService()
