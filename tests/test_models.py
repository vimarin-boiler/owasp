from app.extensions import db


def test_complete_phase_two_schema_is_registered(app):
    expected = {
        "users", "roles", "user_roles", "organizations", "organization_memberships",
        "business_functions", "security_practices", "practice_streams", "maturity_levels",
        "questions", "question_revisions", "question_quality_criteria", "answer_sets",
        "answer_options", "questionnaire_versions", "questionnaire_version_questions",
        "assessments", "assessment_users", "assessment_questions", "assessment_responses",
        "response_history", "evidences", "reviews", "recommendations", "audit_logs",
        "application_settings", "notifications", "assessment_score_snapshots",
        "assessment_score_items",
    }
    assert expected == set(db.metadata.tables)
