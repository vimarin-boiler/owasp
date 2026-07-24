from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.common.assessment_access import can_manage_results, can_respond, can_view_assessment, can_view_results
from app.common.errors import DomainError
from app.common.permissions import roles_required
from app.extensions import db
from app.models import Assessment, AssessmentQuestion
from app.repositories import assessment_repository, catalog_repository, evidence_repository, recommendation_repository, scoring_repository
from app.services import assessment_service, response_service, scoring_service
from app.version import __version__

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@bp.get("/health")
def health():
    return jsonify(status="ok", application=current_app.config["APP_NAME"], version=__version__)


@bp.get("/openapi.yaml")
@login_required
@roles_required("admin", "reviewer", "respondent")
def openapi_document():
    document = Path(current_app.root_path).parent / "docs" / "openapi-v1.yaml"
    return send_file(document, mimetype="application/yaml", as_attachment=False, max_age=0)


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


@bp.get("/assessments/")
@login_required
@roles_required("admin", "reviewer", "respondent")
def assessments():
    items = assessment_repository.list_all() if current_user.has_role("admin") else assessment_repository.for_user(current_user.id)
    data = []
    for item in items:
        progress = assessment_service.progress(item)
        data.append(
            {
                "id": item.public_id,
                "name": item.name,
                "organization": {"id": item.organization.public_id, "name": item.organization.name},
                "questionnaire_version": item.questionnaire_version.version_number,
                "status": item.status.value,
                "target_date": item.target_date.isoformat() if item.target_date else None,
                "progress": progress,
            }
        )
    return jsonify(data=data, count=len(data))


@bp.get("/assessments/<uuid:assessment_public_id>/")
@login_required
@roles_required("admin", "reviewer", "respondent")
def assessment_detail(assessment_public_id):
    assessment = assessment_repository.get_by_public_id(str(assessment_public_id))
    if assessment is None:
        abort(404)
    if not can_view_assessment(current_user, assessment):
        abort(403)
    return jsonify(
        data={
            "id": assessment.public_id,
            "name": assessment.name,
            "description": assessment.description,
            "scope": assessment.scope,
            "status": assessment.status.value,
            "organization": {"id": assessment.organization.public_id, "name": assessment.organization.name},
            "questionnaire_version": assessment.questionnaire_version.version_number,
            "target_maturity_level": str(assessment.target_maturity_level) if assessment.target_maturity_level is not None else None,
            "scoring_source": assessment.scoring_source.value,
            "progress": assessment_service.progress(assessment),
            "assignments": [
                {"user_id": item.user.public_id, "display_name": item.user.display_name, "role": item.assignment_role.value}
                for item in assessment.assignments
            ],
        }
    )


@bp.get("/assessments/<uuid:assessment_public_id>/questions/")
@login_required
@roles_required("admin", "reviewer", "respondent")
def assessment_questions(assessment_public_id):
    assessment = assessment_repository.get_by_public_id(str(assessment_public_id))
    if assessment is None:
        abort(404)
    if not can_view_assessment(current_user, assessment):
        abort(403)
    items = assessment_repository.questions(assessment.id)
    return jsonify(
        data=[
            {
                "id": item.public_id,
                "external_code": item.external_code_snapshot,
                "question_text": item.question_text_snapshot,
                "status": item.current_status.value,
                "maturity_level": item.maturity_level_snapshot,
                "business_function": item.business_function_snapshot,
                "security_practice": item.security_practice_snapshot,
                "practice_stream": item.practice_stream_snapshot,
                "response": {
                    "selected_option_code": item.response.selected_option_code,
                    "selected_weight": str(item.response.selected_weight_snapshot) if item.response.selected_weight_snapshot is not None else None,
                    "is_not_applicable": item.response.is_not_applicable,
                    "version": item.response.response_version,
                } if item.response else None,
            }
            for item in items
        ],
        count=len(items),
    )


@bp.put("/responses/<uuid:assessment_question_public_id>/")
@login_required
@roles_required("respondent")
def save_response(assessment_question_public_id):
    question = db.session.scalar(
        select(AssessmentQuestion)
        .options(
            selectinload(AssessmentQuestion.assessment).selectinload(Assessment.assignments),
            selectinload(AssessmentQuestion.response),
        )
        .where(AssessmentQuestion.public_id == str(assessment_question_public_id))
    )
    if question is None:
        abort(404)
    if not can_respond(current_user, question.assessment):
        abort(403)
    payload = request.get_json(silent=True) or {}
    try:
        response = response_service.save(
            question,
            actor_id=current_user.id,
            selected_option_code=payload.get("selected_option_code"),
            respondent_comment=payload.get("respondent_comment"),
            is_not_applicable=bool(payload.get("is_not_applicable")),
            not_applicable_justification=payload.get("not_applicable_justification"),
            intent=payload.get("intent", "save"),
        )
    except DomainError as exc:
        db.session.rollback()
        return jsonify(error={"code": "validation_error", "message": str(exc)}), 409
    return jsonify(
        data={
            "id": response.public_id,
            "status": response.status.value,
            "version": response.response_version,
            "updated_at": response.updated_at.isoformat(),
        }
    )


@bp.get("/evidences/<uuid:evidence_public_id>/")
@login_required
@roles_required("admin", "reviewer", "respondent")
def evidence_detail(evidence_public_id):
    evidence = evidence_repository.get_active_by_public_id(str(evidence_public_id))
    if evidence is None:
        abort(404)
    if not can_view_assessment(current_user, evidence.assessment_question.assessment):
        abort(403)
    return jsonify(
        data={
            "id": evidence.public_id,
            "filename": evidence.original_filename,
            "mime_type": evidence.detected_mime_type,
            "extension": evidence.extension,
            "size_bytes": evidence.size_bytes,
            "sha256": evidence.sha256,
            "validation_status": evidence.validation_status.value,
            "uploaded_at": evidence.uploaded_at.isoformat(),
            "download_url": f"/assessments/evidences/{evidence.public_id}/download",
        }
    )


@bp.get("/results/<uuid:assessment_public_id>/")
@login_required
@roles_required("admin", "reviewer", "respondent")
def assessment_results(assessment_public_id):
    assessment = assessment_repository.get_by_public_id(str(assessment_public_id))
    if assessment is None:
        abort(404)
    if not can_view_results(current_user, assessment):
        abort(403)
    if can_manage_results(current_user, assessment):
        result = scoring_service.calculate(
            assessment,
            persist=True,
            actor_id=current_user.id,
        )
    else:
        snapshot = scoring_repository.published(assessment.id)
        if snapshot is None:
            abort(404)
        result = scoring_service.from_snapshot(snapshot)
    return jsonify(data=result.as_dict(include_questions=False))


@bp.get("/recommendations/")
@login_required
@roles_required("admin", "reviewer", "respondent")
def recommendations():
    assessment_public_id = request.args.get("assessment_id", "").strip()
    if not assessment_public_id:
        return jsonify(error={"code": "missing_parameter", "message": "assessment_id es obligatorio."}), 400
    assessment = assessment_repository.get_by_public_id(assessment_public_id)
    if assessment is None:
        abort(404)
    if not can_view_results(current_user, assessment):
        abort(403)
    items = recommendation_repository.for_assessment(assessment.id)
    return jsonify(
        data=[
            {
                "id": item.public_id,
                "title": item.title,
                "description": item.description,
                "risk": item.risk,
                "priority": item.priority.value,
                "effort": item.effort,
                "suggested_owner": item.suggested_owner,
                "time_horizon": item.time_horizon,
                "due_date": item.due_date.isoformat() if item.due_date else None,
                "dependencies": item.dependencies,
                "status": item.status.value,
                "is_quick_win": item.is_quick_win,
                "target_maturity_level": str(item.target_maturity_level) if item.target_maturity_level is not None else None,
                "source_dimension_type": item.source_dimension_type,
                "source_dimension_key": item.source_dimension_key,
            }
            for item in items
        ],
        count=len(items),
    )


@bp.get("/reports/<uuid:assessment_public_id>/")
@login_required
@roles_required("admin", "reviewer", "respondent")
def report_links(assessment_public_id):
    assessment = assessment_repository.get_by_public_id(str(assessment_public_id))
    if assessment is None:
        abort(404)
    if not can_view_results(current_user, assessment):
        abort(403)
    return jsonify(
        data={
            "assessment_id": assessment.public_id,
            "published_only": not can_manage_results(current_user, assessment),
            "formats": {
                "html": url_for("reports.printable", assessment_public_id=assessment.public_id),
                "xlsx": url_for("reports.excel", assessment_public_id=assessment.public_id),
                "pdf": url_for("reports.pdf", assessment_public_id=assessment.public_id),
            },
        }
    )
