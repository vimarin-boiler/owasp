from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.repositories import catalog_repository
from app.services.dashboard_service import dashboard_service

bp = Blueprint("dashboard", __name__, template_folder="templates")


@bp.route("/")
@login_required
def index():
    context = dashboard_service.build(current_user)
    if context["is_admin"]:
        context.update(
            catalog_questions=len(catalog_repository.questions(active_only=True)),
            questionnaire_versions=len(catalog_repository.questionnaire_versions()),
        )
    return render_template("dashboard/index.html", **context)
