from __future__ import annotations

from app.enums import AssessmentStatus, ReviewDecision
from app.repositories import assessment_repository
from app.services import assessment_service, response_service, review_service, scoring_service


def test_admin_can_preview_results(client, login, admin_user, phase4_assessment):
    login(admin_user.email)
    response = client.get(f"/assessments/{phase4_assessment.public_id}/results")
    assert response.status_code == 200
    assert b"Resultados de madurez" in response.data


def test_respondent_cannot_see_unpublished_results(client, login, respondent_user, phase4_assessment):
    login(respondent_user.email)
    response = client.get(f"/assessments/{phase4_assessment.public_id}/results")
    assert response.status_code == 403


def test_respondent_can_see_published_snapshot(
    client,
    login,
    admin_user,
    respondent_user,
    reviewer_user,
    phase4_assessment,
):
    question = phase4_assessment.questions[0]
    response_service.save(
        question,
        actor_id=respondent_user.id,
        selected_option_code="YES",
        respondent_comment="Implementado.",
        is_not_applicable=False,
        not_applicable_justification=None,
        intent="submit",
    )
    review_service.decide(
        question.response,
        decision=ReviewDecision.APPROVED,
        comment="Aprobado.",
        reviewer_id=reviewer_user.id,
    )
    assessment = assessment_repository.get_by_public_id(phase4_assessment.public_id)
    assessment_service.transition(assessment, AssessmentStatus.COMPLETED, admin_user.id)
    scoring_service.publish(assessment, actor_id=admin_user.id)

    client.post("/auth/logout")
    login(respondent_user.email)
    response = client.get(f"/assessments/{phase4_assessment.public_id}/results")
    assert response.status_code == 200
    assert b"Snapshot #" in response.data


def test_results_api_honors_publication(client, login, respondent_user, phase4_assessment):
    login(respondent_user.email)
    response = client.get(f"/api/v1/results/{phase4_assessment.public_id}/")
    assert response.status_code == 403


def test_admin_can_open_recommendations_and_roadmap(client, login, admin_user, phase4_assessment):
    login(admin_user.email)
    recommendations = client.get(f"/assessments/{phase4_assessment.public_id}/recommendations")
    roadmap = client.get(f"/assessments/{phase4_assessment.public_id}/roadmap")
    assert recommendations.status_code == 200
    assert roadmap.status_code == 200
    assert b"Recomendaciones" in recommendations.data
    assert b"Roadmap" in roadmap.data


def test_recommendations_api_requires_result_access(client, login, respondent_user, phase4_assessment):
    login(respondent_user.email)
    response = client.get(f"/api/v1/recommendations/?assessment_id={phase4_assessment.public_id}")
    assert response.status_code == 403
