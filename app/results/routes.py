from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.common.assessment_access import (
    can_manage_recommendations,
    can_manage_results,
    can_view_assessment,
    can_view_results,
)
from app.common.errors import DomainError
from app.common.permissions import admin_required
from app.enums import RecommendationPriority, RecommendationStatus
from app.extensions import db
from app.repositories import assessment_repository, recommendation_repository, scoring_repository
from app.results import bp
from app.results.forms import EmptyResultActionForm, RecommendationForm, RecommendationStatusForm
from app.services import recommendation_service, scoring_service

PRIORITY_LABELS = {
    "critical": "Crítica",
    "high": "Alta",
    "medium": "Media",
    "low": "Baja",
}
STATUS_LABELS = {
    "open": "Abierta",
    "planned": "Planificada",
    "in_progress": "En progreso",
    "completed": "Completada",
    "dismissed": "Descartada",
}
HORIZON_ORDER = ["0-30 días", "31-90 días", "3-6 meses", "6-12 meses", "Sin horizonte"]


def _assessment_or_404(public_id: str):
    assessment = assessment_repository.get_by_public_id(public_id)
    if assessment is None:
        abort(404)
    if not can_view_assessment(current_user, assessment):
        abort(403)
    return assessment


def _result_for_user(assessment):
    if not can_view_results(current_user, assessment):
        abort(403)
    if current_user.has_role("admin") or can_manage_results(current_user, assessment):
        return scoring_service.calculate(
            assessment,
            persist=True,
            actor_id=current_user.id,
            force_snapshot=False,
        )
    snapshot = scoring_repository.published(assessment.id)
    if snapshot is None:
        abort(404)
    return scoring_service.from_snapshot(snapshot)


def _dimension_choices(result) -> list[tuple[str, str]]:
    choices = [("", "Assessment completo")]
    for dimension_type, label in [
        ("function", "Función"),
        ("practice", "Práctica"),
        ("stream", "Flujo"),
        ("question", "Pregunta"),
    ]:
        items = result.by_type(dimension_type)
        for item in sorted(items, key=lambda value: (value.sort_order, value.name.casefold())):
            if dimension_type == "question":
                display = item.metadata.get("external_code", item.name.split(" · ", 1)[0])
                choices.append((f"{dimension_type}|{item.key}", f"{label}: {display}"))
            else:
                choices.append((f"{dimension_type}|{item.key}", f"{label}: {item.name}"))
    return choices


def _configure_form(form: RecommendationForm, result) -> None:
    form.dimension_ref.choices = _dimension_choices(result)


def _current_dimension_ref(item) -> str:
    if item.source_dimension_type and item.source_dimension_key:
        return f"{item.source_dimension_type}|{item.source_dimension_key}"
    return ""


def _chart_payload(result) -> dict:
    functions = sorted(result.by_type("function"), key=lambda item: item.sort_order)
    practices = sorted(result.by_type("practice"), key=lambda item: (-(item.gap or Decimal("0")), item.name))
    streams = sorted(result.by_type("stream"), key=lambda item: item.sort_order)
    statuses = result.status_summary.get("statuses", {})
    target = float(result.target_score) if result.target_score is not None else None
    return {
        "radar": {
            "labels": [item.name for item in functions],
            "current": [float(item.score) for item in functions],
            "target": [float(item.target_score) if item.target_score is not None else None for item in functions],
        },
        "practices": {
            "labels": [item.name for item in practices],
            "current": [float(item.score) for item in practices],
            "target": [float(item.target_score) if item.target_score is not None else None for item in practices],
        },
        "distribution": {
            "labels": ["Aprobadas", "En revisión", "Observadas", "Rechazadas", "Respondidas", "Borrador", "Pendientes"],
            "values": [
                statuses.get("approved", 0),
                statuses.get("submitted", 0),
                statuses.get("observed", 0),
                statuses.get("rejected", 0),
                statuses.get("answered", 0),
                statuses.get("draft", 0),
                statuses.get("unanswered", 0),
            ],
        },
        "comparison": {
            "labels": ["Madurez actual", "Nivel objetivo"],
            "values": [float(result.overall_score), target],
        },
        "heatmap": [
            {
                "name": item.name,
                "score": float(item.score),
                "target": float(item.target_score) if item.target_score is not None else None,
                "gap": float(item.gap) if item.gap is not None else None,
                "practice": item.metadata.get("practice_name"),
                "function": item.metadata.get("function_name"),
            }
            for item in streams
        ],
    }


@bp.get("/assessments/<uuid:assessment_public_id>/results")
@login_required
def overview(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    result = _result_for_user(assessment)
    recommendations = recommendation_repository.for_assessment(assessment.id)
    return render_template(
        "results/overview.html",
        assessment=assessment,
        result=result,
        chart_payload=_chart_payload(result),
        functions=result.by_type("function"),
        practices=sorted(result.by_type("practice"), key=lambda item: (item.sort_order, item.name)),
        streams=sorted(result.by_type("stream"), key=lambda item: (item.sort_order, item.name)),
        recommendations=recommendations[:5],
        can_manage=can_manage_results(current_user, assessment),
        action_form=EmptyResultActionForm(),
    )


@bp.post("/assessments/<uuid:assessment_public_id>/results/recalculate")
@login_required
def recalculate(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_manage_results(current_user, assessment):
        abort(403)
    form = EmptyResultActionForm()
    if not form.validate_on_submit():
        abort(400)
    try:
        result = scoring_service.calculate(
            assessment,
            persist=True,
            actor_id=current_user.id,
            force_snapshot=True,
        )
    except DomainError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    else:
        flash(f"Resultados recalculados. Madurez general: {result.overall_score:.2f}.", "success")
    return redirect(url_for("results.overview", assessment_public_id=assessment.public_id))


@bp.post("/assessments/<uuid:assessment_public_id>/results/publish")
@login_required
@admin_required
def publish(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    form = EmptyResultActionForm()
    if not form.validate_on_submit():
        abort(400)
    try:
        snapshot = scoring_service.publish(assessment, actor_id=current_user.id)
    except DomainError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    else:
        flash(f"Resultados publicados usando el snapshot #{snapshot.snapshot_number}.", "success")
    return redirect(url_for("results.overview", assessment_public_id=assessment.public_id))


@bp.get("/assessments/<uuid:assessment_public_id>/recommendations")
@login_required
def recommendations(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_view_results(current_user, assessment):
        abort(403)
    priority_value = request.args.get("priority", "")
    status_value = request.args.get("status", "")
    try:
        priority = RecommendationPriority(priority_value) if priority_value else None
        status = RecommendationStatus(status_value) if status_value else None
    except ValueError:
        abort(400)
    items = recommendation_repository.for_assessment(
        assessment.id,
        priority=priority,
        status=status,
    )
    return render_template(
        "results/recommendations.html",
        assessment=assessment,
        recommendations=items,
        priority_labels=PRIORITY_LABELS,
        status_labels=STATUS_LABELS,
        can_manage=can_manage_recommendations(current_user, assessment),
        action_form=EmptyResultActionForm(),
        status_form=RecommendationStatusForm(),
    )


@bp.route("/assessments/<uuid:assessment_public_id>/recommendations/create", methods=["GET", "POST"])
@login_required
def recommendation_create(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_manage_recommendations(current_user, assessment):
        abort(403)
    result = scoring_service.calculate(assessment, persist=False)
    form = RecommendationForm()
    _configure_form(form, result)
    if request.method == "GET":
        dimension = request.args.get("dimension", "")
        if dimension and any(value == dimension for value, _ in form.dimension_ref.choices):
            form.dimension_ref.data = dimension
        form.priority.data = "high"
        form.status.data = "open"
        form.target_maturity_level.data = assessment.target_maturity_level
    if form.validate_on_submit():
        try:
            item = recommendation_service.create(
                assessment,
                dimension_ref=form.dimension_ref.data,
                title=form.title.data,
                description=form.description.data,
                risk=form.risk.data,
                priority=RecommendationPriority(form.priority.data),
                effort=form.effort.data,
                suggested_owner=form.suggested_owner.data,
                time_horizon=form.time_horizon.data,
                due_date=form.due_date.data,
                dependencies=form.dependencies.data,
                status=RecommendationStatus(form.status.data),
                is_quick_win=form.is_quick_win.data,
                target_maturity_level=form.target_maturity_level.data,
                actor_id=current_user.id,
            )
        except (ValueError, DomainError) as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Recomendación creada correctamente.", "success")
            return redirect(url_for("results.recommendation_edit", assessment_public_id=assessment.public_id, recommendation_public_id=item.public_id))
    return render_template("results/recommendation_form.html", assessment=assessment, form=form, title="Nueva recomendación", mode="create")


@bp.route("/assessments/<uuid:assessment_public_id>/recommendations/<uuid:recommendation_public_id>/edit", methods=["GET", "POST"])
@login_required
def recommendation_edit(assessment_public_id, recommendation_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_manage_recommendations(current_user, assessment):
        abort(403)
    item = recommendation_repository.get_for_assessment(assessment.id, str(recommendation_public_id))
    if item is None or not item.is_active:
        abort(404)
    result = scoring_service.calculate(assessment, persist=False)
    form = RecommendationForm(obj=item)
    _configure_form(form, result)
    if request.method == "GET":
        form.dimension_ref.data = _current_dimension_ref(item)
        form.priority.data = item.priority.value
        form.status.data = item.status.value
    if form.validate_on_submit():
        try:
            recommendation_service.update(
                item,
                actor_id=current_user.id,
                dimension_ref=form.dimension_ref.data,
                title=form.title.data,
                description=form.description.data,
                risk=form.risk.data,
                priority=RecommendationPriority(form.priority.data),
                effort=form.effort.data,
                suggested_owner=form.suggested_owner.data,
                time_horizon=form.time_horizon.data,
                due_date=form.due_date.data,
                dependencies=form.dependencies.data,
                status=RecommendationStatus(form.status.data),
                is_quick_win=form.is_quick_win.data,
                target_maturity_level=form.target_maturity_level.data,
            )
        except (ValueError, DomainError) as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Recomendación actualizada.", "success")
            return redirect(url_for("results.recommendations", assessment_public_id=assessment.public_id))
    return render_template("results/recommendation_form.html", assessment=assessment, form=form, title="Editar recomendación", mode="edit", recommendation=item)


@bp.post("/assessments/<uuid:assessment_public_id>/recommendations/<uuid:recommendation_public_id>/status")
@login_required
def recommendation_status(assessment_public_id, recommendation_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_manage_recommendations(current_user, assessment):
        abort(403)
    item = recommendation_repository.get_for_assessment(assessment.id, str(recommendation_public_id))
    if item is None or not item.is_active:
        abort(404)
    form = RecommendationStatusForm()
    if not form.validate_on_submit():
        abort(400)
    try:
        recommendation_service.change_status(
            item,
            status=RecommendationStatus(form.status.data),
            actor_id=current_user.id,
        )
    except (ValueError, DomainError) as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    else:
        flash("Estado de la recomendación actualizado.", "success")
    return redirect(url_for("results.recommendations", assessment_public_id=assessment.public_id))


@bp.post("/assessments/<uuid:assessment_public_id>/recommendations/<uuid:recommendation_public_id>/deactivate")
@login_required
def recommendation_deactivate(assessment_public_id, recommendation_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_manage_recommendations(current_user, assessment):
        abort(403)
    item = recommendation_repository.get_for_assessment(assessment.id, str(recommendation_public_id))
    if item is None:
        abort(404)
    form = EmptyResultActionForm()
    if not form.validate_on_submit():
        abort(400)
    recommendation_service.deactivate(item, actor_id=current_user.id)
    flash("Recomendación desactivada.", "success")
    return redirect(url_for("results.recommendations", assessment_public_id=assessment.public_id))


@bp.post("/assessments/<uuid:assessment_public_id>/recommendations/generate")
@login_required
def generate_recommendations(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_manage_recommendations(current_user, assessment):
        abort(403)
    form = EmptyResultActionForm()
    if not form.validate_on_submit():
        abort(400)
    result = scoring_service.calculate(assessment, persist=True, actor_id=current_user.id)
    created = recommendation_service.generate_from_gaps(assessment, result, actor_id=current_user.id)
    flash(
        f"Se generaron {created} recomendaciones a partir de las brechas."
        if created else "No se encontraron nuevas brechas para generar recomendaciones.",
        "success" if created else "info",
    )
    return redirect(url_for("results.recommendations", assessment_public_id=assessment.public_id))


@bp.get("/assessments/<uuid:assessment_public_id>/roadmap")
@login_required
def roadmap(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_view_results(current_user, assessment):
        abort(403)
    items = recommendation_repository.for_assessment(assessment.id)
    grouped = defaultdict(list)
    for item in items:
        grouped[item.time_horizon or "Sin horizonte"].append(item)
    columns = [(horizon, grouped.get(horizon, [])) for horizon in HORIZON_ORDER]
    totals = {
        "all": len(items),
        "quick_wins": sum(item.is_quick_win for item in items),
        "completed": sum(item.status == RecommendationStatus.COMPLETED for item in items),
        "critical": sum(item.priority == RecommendationPriority.CRITICAL for item in items),
    }
    return render_template(
        "results/roadmap.html",
        assessment=assessment,
        columns=columns,
        totals=totals,
        priority_labels=PRIORITY_LABELS,
        status_labels=STATUS_LABELS,
        can_manage=can_manage_recommendations(current_user, assessment),
    )
