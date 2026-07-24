from __future__ import annotations

from app.enums import RecommendationPriority, RecommendationStatus
from app.repositories import recommendation_repository
from app.services import recommendation_service, scoring_service


def test_create_update_and_deactivate_recommendation(phase4_assessment, admin_user):
    result = scoring_service.calculate(phase4_assessment)
    practice = result.by_type("practice")[0]
    item = recommendation_service.create(
        phase4_assessment,
        dimension_ref=f"practice|{practice.key}",
        title="Formalizar estrategia",
        description="Definir una estrategia medible y aprobada.",
        risk="Falta de dirección y priorización.",
        priority=RecommendationPriority.HIGH,
        effort="Medio",
        suggested_owner="CISO",
        time_horizon="31-90 días",
        due_date=None,
        dependencies=None,
        status=RecommendationStatus.OPEN,
        is_quick_win=False,
        target_maturity_level="2",
        actor_id=admin_user.id,
    )
    assert item.source_dimension_type == "practice"
    assert item.security_practice_id is not None
    assert recommendation_repository.for_assessment(phase4_assessment.id)[0].id == item.id

    recommendation_service.change_status(
        item,
        status=RecommendationStatus.COMPLETED,
        actor_id=admin_user.id,
    )
    assert item.completed_at is not None
    recommendation_service.deactivate(item, actor_id=admin_user.id)
    assert recommendation_repository.for_assessment(phase4_assessment.id) == []


def test_generate_recommendations_from_gaps_is_idempotent(phase4_assessment, admin_user):
    result = scoring_service.calculate(phase4_assessment)
    created = recommendation_service.generate_from_gaps(
        phase4_assessment,
        result,
        actor_id=admin_user.id,
    )
    repeated = recommendation_service.generate_from_gaps(
        phase4_assessment,
        result,
        actor_id=admin_user.id,
    )
    assert created == 1
    assert repeated == 0
