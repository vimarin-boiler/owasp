from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.enums import AssessmentStatus, AssignmentRole, ResponseStatus
from app.extensions import db
from app.models import Assessment, AssessmentQuestion, AssessmentReviewNote, AssessmentUser, Evidence, Organization
from app.repositories.base import BaseRepository


class AssessmentRepository(BaseRepository[Assessment]):
    model = Assessment

    @staticmethod
    def _detail_options():
        return (
            selectinload(Assessment.organization),
            selectinload(Assessment.questionnaire_version),
            selectinload(Assessment.assignments).selectinload(AssessmentUser.user),
            selectinload(Assessment.questions).selectinload(AssessmentQuestion.response),
            selectinload(Assessment.questions).selectinload(AssessmentQuestion.evidences),
            selectinload(Assessment.review_notes).selectinload(AssessmentReviewNote.author),
            selectinload(Assessment.review_notes).selectinload(AssessmentReviewNote.resolved_by),
        )

    def get_by_public_id(self, public_id: str) -> Assessment | None:
        stmt = select(Assessment).options(*self._detail_options()).where(Assessment.public_id == public_id)
        return db.session.scalar(stmt)

    def list_all(self, search: str = "", status: str = "") -> list[Assessment]:
        stmt = select(Assessment).options(*self._detail_options())
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.join(Organization, Organization.id == Assessment.organization_id).where(
                or_(Assessment.name.ilike(pattern), Organization.name.ilike(pattern))
            )
        if status:
            try:
                resolved_status = AssessmentStatus(status)
            except ValueError:
                return []
            stmt = stmt.where(Assessment.status == resolved_status)
        stmt = stmt.order_by(Assessment.target_date.asc().nullslast(), Assessment.created_at.desc())
        return list(db.session.scalars(stmt).unique())

    def for_user(self, user_id: int, assignment_role: AssignmentRole | None = None) -> list[Assessment]:
        stmt = (
            select(Assessment)
            .join(AssessmentUser, AssessmentUser.assessment_id == Assessment.id)
            .options(*self._detail_options())
            .where(AssessmentUser.user_id == user_id)
        )
        if assignment_role is not None:
            stmt = stmt.where(AssessmentUser.assignment_role == assignment_role)
        stmt = stmt.order_by(Assessment.target_date.asc().nullslast(), Assessment.created_at.desc())
        return list(db.session.scalars(stmt).unique())

    def question_by_public_id(self, assessment_id: int, question_public_id: str) -> AssessmentQuestion | None:
        stmt = (
            select(AssessmentQuestion)
            .options(
                selectinload(AssessmentQuestion.assessment).selectinload(Assessment.assignments).selectinload(AssessmentUser.user),
                selectinload(AssessmentQuestion.response),
                selectinload(AssessmentQuestion.evidences).selectinload(Evidence.uploaded_by),
                selectinload(AssessmentQuestion.evidences).selectinload(Evidence.reviewed_by),
            )
            .where(
                AssessmentQuestion.assessment_id == assessment_id,
                AssessmentQuestion.public_id == question_public_id,
            )
        )
        return db.session.scalar(stmt)

    def questions(self, assessment_id: int) -> list[AssessmentQuestion]:
        stmt = (
            select(AssessmentQuestion)
            .options(
                selectinload(AssessmentQuestion.response),
                selectinload(AssessmentQuestion.evidences),
            )
            .where(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.sort_order, AssessmentQuestion.id)
        )
        return list(db.session.scalars(stmt).unique())

    def pending_review(self, user_id: int | None = None, is_admin: bool = False) -> list[AssessmentQuestion]:
        stmt = (
            select(AssessmentQuestion)
            .join(Assessment, Assessment.id == AssessmentQuestion.assessment_id)
            .options(
                selectinload(AssessmentQuestion.assessment).selectinload(Assessment.organization),
                selectinload(AssessmentQuestion.assessment).selectinload(Assessment.assignments),
                selectinload(AssessmentQuestion.response),
                selectinload(AssessmentQuestion.evidences),
            )
            .where(AssessmentQuestion.current_status == ResponseStatus.SUBMITTED)
        )
        if not is_admin:
            stmt = stmt.join(AssessmentUser, AssessmentUser.assessment_id == Assessment.id).where(
                AssessmentUser.user_id == user_id,
                AssessmentUser.assignment_role == AssignmentRole.REVIEWER,
            )
        stmt = stmt.order_by(AssessmentQuestion.updated_at.asc())
        return list(db.session.scalars(stmt).unique())

    def count_all(self) -> int:
        return int(db.session.scalar(select(func.count(Assessment.id))) or 0)

    def count_active(self) -> int:
        return int(
            db.session.scalar(
                select(func.count(Assessment.id)).where(
                    Assessment.status.notin_([AssessmentStatus.CLOSED, AssessmentStatus.CANCELLED])
                )
            )
            or 0
        )


assessment_repository = AssessmentRepository()
