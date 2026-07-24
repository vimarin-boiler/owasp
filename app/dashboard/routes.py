from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.repositories import audit_repository, organization_repository, user_repository

bp = Blueprint("dashboard", __name__, template_folder="templates")


@bp.route("/")
@login_required
def index():
    context = {"is_admin": current_user.has_role("admin")}
    if context["is_admin"]:
        context.update(
            active_users=user_repository.count_active(),
            active_organizations=organization_repository.count_active(),
            recent_activity=audit_repository.recent(8),
        )
    return render_template("dashboard/index.html", **context)
