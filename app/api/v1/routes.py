from flask import Blueprint, current_app, jsonify

from app.version import __version__

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@bp.get("/health")
def health():
    return jsonify(
        status="ok",
        application=current_app.config["APP_NAME"],
        version=__version__,
    )
