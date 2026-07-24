from flask import Blueprint

bp = Blueprint("assessments", __name__, url_prefix="/assessments", template_folder="templates")

from app.assessments import routes  # noqa: E402, F401
