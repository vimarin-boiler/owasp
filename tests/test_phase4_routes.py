from __future__ import annotations

from uuid import uuid4


def test_respondent_cannot_open_unassigned_assessment(client, login, respondent_user, phase4_assessment, make_user):
    outsider = make_user("other-respondent@example.com", role_codes=("respondent",))
    login(outsider.email)
    response = client.get(f"/assessments/{phase4_assessment.public_id}")
    assert response.status_code == 403


def test_assigned_respondent_can_open_questionnaire(client, login, respondent_user, phase4_assessment):
    login(respondent_user.email)
    response = client.get(f"/assessments/{phase4_assessment.public_id}/questionnaire")
    assert response.status_code == 200
    assert b"Assessment de prueba" in response.data


def test_unknown_assessment_uuid_is_not_found(client, login, admin_user):
    login(admin_user.email)
    assert client.get(f"/assessments/{uuid4()}").status_code == 404
