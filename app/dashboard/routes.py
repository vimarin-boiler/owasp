from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.repositories import assessment_repository, audit_repository, catalog_repository, organization_repository, user_repository
from app.services.assessment_service import assessment_service

bp = Blueprint("dashboard", __name__, template_folder="templates")


@bp.route("/")
@login_required
def index():
    is_admin = current_user.has_role("admin")
    assigned = assessment_repository.list_all() if is_admin else assessment_repository.for_user(current_user.id)
    assessment_cards = [(item, assessment_service.progress(item)) for item in assigned[:6]]
    percentages = [progress["percentage"] for _, progress in assessment_cards]
    context = {
        "is_admin": is_admin,
        "assessment_cards": assessment_cards,
        "average_progress": round(sum(percentages) / len(percentages), 1) if percentages else 0,
        "pending_review": len(
            assessment_repository.pending_review(
                current_user.id,
                is_admin,
            )
        ) if (is_admin or current_user.has_role("reviewer")) else 0,
    }
    if is_admin:
        context.update(
            active_users=user_repository.count_active(),
            active_organizations=organization_repository.count_active(),
            recent_activity=audit_repository.recent(8),
            catalog_questions=len(catalog_repository.questions(active_only=True)),
            questionnaire_versions=len(catalog_repository.questionnaire_versions()),
            total_assessments=assessment_repository.count_all(),
            active_assessments=assessment_repository.count_active(),
        )
    return render_template("dashboard/index.html", **context)
