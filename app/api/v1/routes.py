from __future__ import annotations

from flask import Blueprint, abort, current_app, jsonify, request
from flask_login import login_required

from app.common.permissions import roles_required
from app.repositories.catalog import catalog_repository
from app.version import __version__

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@bp.get("/health")
def health():
    return jsonify(status="ok", application=current_app.config["APP_NAME"], version=__version__)


@bp.get("/questions/")
@login_required
@roles_required("admin", "reviewer", "respondent")
def questions():
    search = request.args.get("q", "").strip()
    items = catalog_repository.questions(search, active_only=True)
    return jsonify(
        data=[
            {
                "id": item.public_id,
                "external_code": item.external_code,
                "canonical_name": item.canonical_name,
                "current_revision": item.current_revision_number,
                "is_active": item.is_active,
            }
            for item in items
        ],
        count=len(items),
    )


@bp.get("/questions/<uuid:question_public_id>/")
@login_required
@roles_required("admin", "reviewer", "respondent")
def question_detail(question_public_id):
    item = catalog_repository.question_by_public_id(str(question_public_id))
    if item is None or not item.is_active or item.current_revision is None:
        abort(404)
    revision = item.current_revision
    return jsonify(
        data={
            "id": item.public_id,
            "external_code": item.external_code,
            "canonical_name": item.canonical_name,
            "revision": revision.revision_number,
            "question_text": revision.question_text,
            "guidance_text": revision.guidance_text,
            "business_function": {"code": revision.business_function.code, "name": revision.business_function.name},
            "security_practice": {"code": revision.security_practice.code, "name": revision.security_practice.name},
            "practice_stream": {"code": revision.practice_stream.code, "name": revision.practice_stream.name},
            "maturity_level": revision.maturity_level.level_number,
            "quality_criteria": [criterion.criterion_text for criterion in revision.criteria],
            "answer_options": [
                {"code": option.option_code, "text": option.text, "weight": str(option.weight)}
                for option in revision.answer_set.options
                if option.is_active
            ],
        }
    )


@bp.get("/questionnaire-versions/")
@login_required
@roles_required("admin", "reviewer", "respondent")
def questionnaire_versions():
    items = catalog_repository.questionnaire_versions()
    return jsonify(
        data=[
            {
                "id": item.public_id,
                "name": item.name,
                "version_number": item.version_number,
                "status": item.status.value,
                "question_count": len(item.question_links),
                "published_at": item.published_at.isoformat() if item.published_at else None,
            }
            for item in items
        ],
        count=len(items),
    )
