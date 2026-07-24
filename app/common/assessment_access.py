from __future__ import annotations

from app.enums import AssignmentRole
from app.models import Assessment, AssessmentQuestion, Evidence, User


def assignment_roles(user: User, assessment: Assessment) -> set[AssignmentRole]:
    return {
        assignment.assignment_role
        for assignment in assessment.assignments
        if assignment.user_id == user.id
    }


def can_view_assessment(user: User, assessment: Assessment) -> bool:
    if not user.is_authenticated or not user.is_active:
        return False
    if user.has_role("admin"):
        return True
    roles = assignment_roles(user, assessment)
    return bool(roles) and (
        (AssignmentRole.RESPONDENT in roles and user.has_role("respondent"))
        or (AssignmentRole.REVIEWER in roles and user.has_role("reviewer"))
    )


def can_respond(user: User, assessment: Assessment) -> bool:
    if not user.is_authenticated or not user.is_active:
        return False
    if user.has_role("admin"):
        return False
    return user.has_role("respondent") and AssignmentRole.RESPONDENT in assignment_roles(user, assessment)


def can_review(user: User, assessment: Assessment) -> bool:
    if not user.is_authenticated or not user.is_active:
        return False
    if user.has_role("admin"):
        return True
    return user.has_role("reviewer") and AssignmentRole.REVIEWER in assignment_roles(user, assessment)


def can_manage_assessment(user: User, assessment: Assessment) -> bool:
    return bool(user.is_authenticated and user.is_active and user.has_role("admin"))


def can_download_evidence(user: User, evidence: Evidence) -> bool:
    return can_view_assessment(user, evidence.assessment_question.assessment)


def can_delete_evidence(user: User, evidence: Evidence) -> bool:
    if user.has_role("admin"):
        return True
    assessment = evidence.assessment_question.assessment
    if not can_respond(user, assessment):
        return False
    response = evidence.assessment_question.response
    if response and response.status.value in {"submitted", "approved"}:
        return False
    return evidence.uploaded_by_id == user.id


def question_belongs_to_assessment(question: AssessmentQuestion, assessment: Assessment) -> bool:
    return question.assessment_id == assessment.id
