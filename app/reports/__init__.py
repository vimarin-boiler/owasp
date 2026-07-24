from flask import Blueprint

bp = Blueprint("reports", __name__, url_prefix="/reports", template_folder="templates")

from app.reports import routes  # noqa: E402,F401
