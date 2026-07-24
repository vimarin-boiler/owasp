from __future__ import annotations

from datetime import datetime, timezone
from flask import abort, make_response, render_template, send_file
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.common.assessment_access import can_manage_results, can_view_assessment, can_view_results
from app.extensions import db, limiter
from app.repositories import assessment_repository
from app.reports import bp
from app.services.audit_service import audit_service
from app.services.report_data_service import report_data_service
from app.services.report_excel_service import report_excel_service
from app.services.report_pdf_service import report_pdf_service


def _assessment_or_404(public_id: str):
    assessment = assessment_repository.get_by_public_id(public_id)
    if assessment is None:
        abort(404)
    if not can_view_assessment(current_user, assessment) or not can_view_results(current_user, assessment):
        abort(403)
    return assessment


def _published_only(assessment) -> bool:
    return not can_manage_results(current_user, assessment)


def _payload(assessment) -> dict:
    try:
        return report_data_service.build(assessment, published_only=_published_only(assessment))
    except LookupError:
        abort(404)


def _filename(assessment, extension: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    base = secure_filename(f"{assessment.organization.name}-{assessment.name}")[:100].strip("-_")
    return f"{base or 'assessment-samm'}-{stamp}.{extension}"


def _audit(assessment, action: str, *, format_name: str) -> None:
    audit_service.record(
        action=action,
        entity_type="assessment_report",
        entity_public_id=assessment.public_id,
        actor_user_id=current_user.id,
        organization_id=assessment.organization_id,
        assessment_id=assessment.id,
        after={"format": format_name, "published_only": _published_only(assessment)},
    )
    db.session.commit()


@bp.get("/assessments/<uuid:assessment_public_id>")
@login_required
def index(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    payload = _payload(assessment)
    return render_template("reports/index.html", assessment=assessment, payload=payload)


@bp.get("/assessments/<uuid:assessment_public_id>/print")
@login_required
def printable(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    payload = _payload(assessment)
    _audit(assessment, "report.viewed", format_name="html")
    response = make_response(render_template("reports/printable.html", assessment=assessment, payload=payload))
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@bp.get("/assessments/<uuid:assessment_public_id>/excel")
@login_required
@limiter.limit("10 per minute")
def excel(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    payload = _payload(assessment)
    output = report_excel_service.build(payload)
    _audit(assessment, "report.generated", format_name="xlsx")
    response = send_file(
        output,
        as_attachment=True,
        download_name=_filename(assessment, "xlsx"),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.get("/assessments/<uuid:assessment_public_id>/pdf")
@login_required
@limiter.limit("6 per minute")
def pdf(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    payload = _payload(assessment)
    output = report_pdf_service.build(payload)
    _audit(assessment, "report.generated", format_name="pdf")
    response = send_file(
        output,
        as_attachment=True,
        download_name=_filename(assessment, "pdf"),
        mimetype="application/pdf",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "sandbox"
    return response
