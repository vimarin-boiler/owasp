from __future__ import annotations

from collections import OrderedDict

from flask import abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from app.assessments import bp
from app.assessments.forms import (
    AssessmentForm,
    EmptyActionForm,
    EvidenceReviewForm,
    EvidenceUploadForm,
    ReopenForm,
    ResponseForm,
    ReviewForm,
    ReviewNoteForm,
)
from app.common.assessment_access import (
    can_delete_evidence,
    can_download_evidence,
    can_manage_assessment,
    can_respond,
    can_review,
    can_view_assessment,
    can_view_results,
)
from app.common.errors import DomainError
from app.common.permissions import admin_required, roles_required
from app.enums import AssessmentStatus, EvidenceValidationStatus, QuestionnaireStatus, ReviewDecision, ScoringSource
from app.extensions import db
from app.models import AssessmentReviewNote, QuestionnaireVersion
from app.repositories import assessment_repository, catalog_repository, evidence_repository, organization_repository, user_repository
from app.services import assessment_service, evidence_service, response_service, review_service


STATUS_LABELS = {
    "draft": "Borrador",
    "configured": "Configurado",
    "in_progress": "En ejecución",
    "in_review": "En revisión",
    "observed": "Con observaciones",
    "completed": "Completado",
    "published": "Publicado",
    "closed": "Cerrado",
    "cancelled": "Cancelado",
    "unanswered": "Sin responder",
    "answered": "Respondida",
    "submitted": "Enviada a revisión",
    "rejected": "Rechazada",
    "approved": "Aprobada",
}


def _published_versions() -> list[QuestionnaireVersion]:
    return [
        version
        for version in catalog_repository.questionnaire_versions()
        if version.status == QuestionnaireStatus.PUBLISHED
    ]


def _configure_assessment_form(form: AssessmentForm) -> None:
    form.organization_id.choices = [
        (organization.id, organization.name)
        for organization in organization_repository.list()
        if organization.is_active
    ]
    form.questionnaire_version_id.choices = [
        (version.id, f"{version.name} · {version.version_number}") for version in _published_versions()
    ]
    form.respondent_ids.choices = [
        (user.id, f"{user.display_name} · {user.email}") for user in user_repository.active_with_role("respondent")
    ]
    form.reviewer_ids.choices = [
        (user.id, f"{user.display_name} · {user.email}") for user in user_repository.active_with_role("reviewer")
    ]


def _resolve_version(version_id: int) -> QuestionnaireVersion | None:
    summary = next((item for item in _published_versions() if item.id == version_id), None)
    return catalog_repository.questionnaire_version_by_public_id(summary.public_id) if summary else None


def _assessment_or_404(public_id: str):
    assessment = assessment_repository.get_by_public_id(public_id)
    if assessment is None:
        abort(404)
    if not can_view_assessment(current_user, assessment):
        abort(403)
    return assessment


def _question_or_404(assessment, question_public_id: str):
    question = assessment_repository.question_by_public_id(assessment.id, question_public_id)
    if question is None:
        abort(404)
    return question


def _hierarchy(questions) -> list[dict]:
    tree: OrderedDict[str, dict] = OrderedDict()
    for question in questions:
        function = question.business_function_snapshot
        practice = question.security_practice_snapshot
        stream = question.practice_stream_snapshot
        fn_node = tree.setdefault(function["code"], {"code": function["code"], "name": function["name"], "practices": OrderedDict(), "total": 0})
        practice_node = fn_node["practices"].setdefault(practice["code"], {"code": practice["code"], "name": practice["name"], "streams": OrderedDict(), "total": 0})
        stream_node = practice_node["streams"].setdefault(stream["code"], {"code": stream["code"], "name": stream["name"], "questions": [], "total": 0})
        stream_node["questions"].append(question)
        stream_node["total"] += 1
        practice_node["total"] += 1
        fn_node["total"] += 1
    result = []
    for fn_node in tree.values():
        fn_node["practices"] = list(fn_node["practices"].values())
        for practice_node in fn_node["practices"]:
            practice_node["streams"] = list(practice_node["streams"].values())
        result.append(fn_node)
    return result


def _unique_snapshots(questions, attribute: str) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for question in questions:
        snapshot = getattr(question, attribute)
        code = str(snapshot.get("code", ""))
        if code and code not in seen:
            seen.add(code)
            result.append(snapshot)
    return result


def _filter_questions(questions):
    text = request.args.get("q", "").strip().casefold()
    function_code = request.args.get("function", "").strip()
    practice_code = request.args.get("practice", "").strip()
    stream_code = request.args.get("stream", "").strip()
    state = request.args.get("state", "").strip()
    filtered = []
    for item in questions:
        if text and text not in f"{item.external_code_snapshot} {item.question_text_snapshot}".casefold():
            continue
        if function_code and item.business_function_snapshot.get("code") != function_code:
            continue
        if practice_code and item.security_practice_snapshot.get("code") != practice_code:
            continue
        if stream_code and item.practice_stream_snapshot.get("code") != stream_code:
            continue
        if state and item.current_status.value != state:
            continue
        filtered.append(item)
    return filtered


@bp.get("/")
@login_required
def index():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    if current_user.has_role("admin"):
        assessments = assessment_repository.list_all(search, status)
    else:
        assessments = assessment_repository.for_user(current_user.id)
        if search:
            assessments = [item for item in assessments if search.casefold() in item.name.casefold() or search.casefold() in item.organization.name.casefold()]
        if status:
            assessments = [item for item in assessments if item.status.value == status]
    cards = [(item, assessment_service.progress(item)) for item in assessments]
    return render_template(
        "assessments/index.html",
        cards=cards,
        search=search,
        selected_status=status,
        status_labels=STATUS_LABELS,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def create():
    form = AssessmentForm()
    _configure_assessment_form(form)
    if form.validate_on_submit():
        version = _resolve_version(form.questionnaire_version_id.data)
        if version is None:
            flash("La versión seleccionada no está disponible.", "danger")
        else:
            try:
                assessment = assessment_service.create(
                    organization_id=form.organization_id.data,
                    questionnaire_version=version,
                    name=form.name.data,
                    description=form.description.data,
                    scope=form.scope.data,
                    start_date=form.start_date.data,
                    target_date=form.target_date.data,
                    target_maturity_level=form.target_maturity_level.data,
                    scoring_source=ScoringSource(form.scoring_source.data),
                    respondent_ids=form.respondent_ids.data,
                    reviewer_ids=form.reviewer_ids.data,
                    actor_id=current_user.id,
                )
            except DomainError as exc:
                db.session.rollback()
                flash(str(exc), "danger")
            else:
                flash("Assessment creado y cuestionario instanciado correctamente.", "success")
                return redirect(url_for("assessments.detail", assessment_public_id=assessment.public_id))
    return render_template("assessments/form.html", form=form, title="Nuevo assessment", mode="create")


@bp.route("/<uuid:assessment_public_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    form = AssessmentForm(obj=assessment)
    _configure_assessment_form(form)
    if request.method == "GET":
        form.organization_id.data = assessment.organization_id
        form.questionnaire_version_id.data = assessment.questionnaire_version_id
        form.scoring_source.data = assessment.scoring_source.value
        form.respondent_ids.data = [item.user_id for item in assessment.assignments if item.assignment_role.value == "respondent"]
        form.reviewer_ids.data = [item.user_id for item in assessment.assignments if item.assignment_role.value == "reviewer"]
    if form.validate_on_submit():
        version = _resolve_version(form.questionnaire_version_id.data)
        if version is None:
            flash("La versión seleccionada no está disponible.", "danger")
        else:
            try:
                assessment_service.update(
                    assessment,
                    organization_id=form.organization_id.data,
                    questionnaire_version=version,
                    name=form.name.data,
                    description=form.description.data,
                    scope=form.scope.data,
                    start_date=form.start_date.data,
                    target_date=form.target_date.data,
                    target_maturity_level=form.target_maturity_level.data,
                    scoring_source=ScoringSource(form.scoring_source.data),
                    respondent_ids=form.respondent_ids.data,
                    reviewer_ids=form.reviewer_ids.data,
                    actor_id=current_user.id,
                )
            except DomainError as exc:
                db.session.rollback()
                flash(str(exc), "danger")
            else:
                flash("Assessment actualizado correctamente.", "success")
                return redirect(url_for("assessments.detail", assessment_public_id=assessment.public_id))
    return render_template("assessments/form.html", form=form, title="Editar assessment", mode="edit", assessment=assessment)


@bp.get("/<uuid:assessment_public_id>")
@login_required
def detail(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    progress = assessment_service.progress(assessment)
    return render_template(
        "assessments/detail.html",
        assessment=assessment,
        progress=progress,
        status_labels=STATUS_LABELS,
        can_respond=can_respond(current_user, assessment),
        can_review=can_review(current_user, assessment),
        can_manage=can_manage_assessment(current_user, assessment),
        can_view_results=can_view_results(current_user, assessment),
        transition_form=EmptyActionForm(),
        note_form=ReviewNoteForm(prefix="note"),
    )


@bp.post("/<uuid:assessment_public_id>/status/<target_status>")
@login_required
@admin_required
def transition(assessment_public_id, target_status):
    assessment = _assessment_or_404(str(assessment_public_id))
    form = EmptyActionForm()
    if not form.validate_on_submit():
        abort(400)
    try:
        assessment_service.transition(assessment, AssessmentStatus(target_status), current_user.id)
    except (ValueError, DomainError) as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    else:
        flash("Estado del assessment actualizado.", "success")
    return redirect(url_for("assessments.detail", assessment_public_id=assessment.public_id))


@bp.get("/<uuid:assessment_public_id>/questionnaire")
@login_required
def questionnaire(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    questions = assessment_repository.questions(assessment.id)
    filtered = _filter_questions(questions)
    return render_template(
        "assessments/questionnaire.html",
        assessment=assessment,
        questions=filtered,
        all_questions=questions,
        hierarchy=_hierarchy(questions),
        progress=assessment_service.progress(assessment),
        status_labels=STATUS_LABELS,
        filter_functions=_unique_snapshots(questions, "business_function_snapshot"),
        filter_practices=_unique_snapshots(questions, "security_practice_snapshot"),
        filter_streams=_unique_snapshots(questions, "practice_stream_snapshot"),
    )


@bp.route("/<uuid:assessment_public_id>/questions/<uuid:question_public_id>", methods=["GET", "POST"])
@login_required
def question(assessment_public_id, question_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    item = _question_or_404(assessment, str(question_public_id))
    response_form = ResponseForm(prefix="response")
    response_form.selected_option_code.choices = [
        (str(option.get("code")), f"{option.get('text')} · {option.get('weight')}")
        for option in item.answer_options_snapshot
    ]
    if request.method == "GET" and item.response:
        response_form.selected_option_code.data = item.response.selected_option_code
        response_form.respondent_comment.data = item.response.respondent_comment
        response_form.is_not_applicable.data = item.response.is_not_applicable
        response_form.not_applicable_justification.data = item.response.not_applicable_justification
    if request.method == "POST":
        if not can_respond(current_user, assessment):
            abort(403)
        if response_form.validate_on_submit():
            intent = "submit" if response_form.submit_review.data else "save" if response_form.save.data else "draft"
            try:
                response_service.save(
                    item,
                    actor_id=current_user.id,
                    selected_option_code=response_form.selected_option_code.data,
                    respondent_comment=response_form.respondent_comment.data,
                    is_not_applicable=response_form.is_not_applicable.data,
                    not_applicable_justification=response_form.not_applicable_justification.data,
                    intent=intent,
                )
            except DomainError as exc:
                db.session.rollback()
                flash(str(exc), "danger")
            else:
                flash("Respuesta enviada a revisión." if intent == "submit" else "Respuesta guardada.", "success")
                return redirect(url_for("assessments.question", assessment_public_id=assessment.public_id, question_public_id=item.public_id))
    questions = assessment_repository.questions(assessment.id)
    index = next(index for index, question in enumerate(questions) if question.id == item.id)
    previous_item = questions[index - 1] if index > 0 else None
    next_item = questions[index + 1] if index + 1 < len(questions) else None
    return render_template(
        "assessments/question.html",
        assessment=assessment,
        question=item,
        questions=questions,
        hierarchy=_hierarchy(questions),
        progress=assessment_service.progress(assessment),
        response_form=response_form,
        evidence_form=EvidenceUploadForm(prefix="evidence"),
        previous_item=previous_item,
        next_item=next_item,
        status_labels=STATUS_LABELS,
        can_respond=can_respond(current_user, assessment),
        can_review=can_review(current_user, assessment),
    )


@bp.post("/<uuid:assessment_public_id>/questions/<uuid:question_public_id>/autosave")
@login_required
def autosave(assessment_public_id, question_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_respond(current_user, assessment):
        abort(403)
    item = _question_or_404(assessment, str(question_public_id))
    payload = request.get_json(silent=True) or {}
    try:
        response = response_service.save(
            item,
            actor_id=current_user.id,
            selected_option_code=payload.get("selected_option_code"),
            respondent_comment=payload.get("respondent_comment"),
            is_not_applicable=bool(payload.get("is_not_applicable")),
            not_applicable_justification=payload.get("not_applicable_justification"),
            intent="autosave",
        )
    except DomainError as exc:
        db.session.rollback()
        return jsonify(ok=False, message=str(exc)), 409
    return jsonify(ok=True, saved_at=response.updated_at.isoformat(), version=response.response_version)


@bp.post("/<uuid:assessment_public_id>/questions/<uuid:question_public_id>/evidences")
@login_required
def upload_evidences(assessment_public_id, question_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_respond(current_user, assessment):
        abort(403)
    item = _question_or_404(assessment, str(question_public_id))
    form = EvidenceUploadForm(prefix="evidence")
    if not form.validate_on_submit():
        flash("Selecciona al menos un archivo de evidencia.", "danger")
    else:
        uploaded = 0
        errors = []
        for file in form.evidences.data:
            try:
                evidence_service.upload(item, file, description=form.description.data, actor_id=current_user.id)
                uploaded += 1
            except DomainError as exc:
                db.session.rollback()
                errors.append(f"{file.filename}: {exc}")
        if uploaded:
            flash(f"Se adjuntaron {uploaded} evidencias correctamente.", "success")
        for error in errors:
            flash(error, "danger")
    return redirect(url_for("assessments.question", assessment_public_id=assessment.public_id, question_public_id=item.public_id))


@bp.get("/evidences/<uuid:evidence_public_id>/download")
@login_required
def download_evidence(evidence_public_id):
    evidence = evidence_repository.get_active_by_public_id(str(evidence_public_id))
    if evidence is None:
        abort(404)
    if not can_download_evidence(current_user, evidence):
        abort(403)
    try:
        path = evidence_service.record_download(evidence, actor_id=current_user.id)
    except DomainError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("assessments.detail", assessment_public_id=evidence.assessment_question.assessment.public_id))
    response = send_file(
        path,
        as_attachment=True,
        download_name=evidence.original_filename,
        mimetype="application/octet-stream",
        conditional=True,
        etag=False,
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "sandbox"
    return response


@bp.post("/evidences/<uuid:evidence_public_id>/delete")
@login_required
def delete_evidence(evidence_public_id):
    evidence = evidence_repository.get_active_by_public_id(str(evidence_public_id))
    if evidence is None:
        abort(404)
    if not can_delete_evidence(current_user, evidence):
        abort(403)
    assessment = evidence.assessment_question.assessment
    question = evidence.assessment_question
    form = EmptyActionForm()
    if not form.validate_on_submit():
        abort(400)
    try:
        evidence_service.delete(evidence, actor_id=current_user.id)
    except DomainError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    else:
        flash("Evidencia eliminada.", "success")
    return redirect(url_for("assessments.question", assessment_public_id=assessment.public_id, question_public_id=question.public_id))


@bp.get("/reviews")
@login_required
@roles_required("admin", "reviewer")
def review_queue():
    items = assessment_repository.pending_review(current_user.id, current_user.has_role("admin"))
    return render_template("assessments/review_queue.html", questions=items, status_labels=STATUS_LABELS)


@bp.route("/<uuid:assessment_public_id>/review/<uuid:question_public_id>", methods=["GET", "POST"])
@login_required
@roles_required("admin", "reviewer")
def review_question(assessment_public_id, question_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_review(current_user, assessment):
        abort(403)
    item = _question_or_404(assessment, str(question_public_id))
    if item.response is None:
        abort(404)
    form = ReviewForm(prefix="review")
    reopen_form = ReopenForm(prefix="reopen")
    if form.validate_on_submit():
        try:
            review_service.decide(
                item.response,
                decision=ReviewDecision(form.decision.data),
                comment=form.comment.data,
                reviewer_id=current_user.id,
            )
        except DomainError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Revisión registrada correctamente.", "success")
            return redirect(url_for("assessments.review_queue"))
    return render_template(
        "assessments/review_question.html",
        assessment=assessment,
        question=item,
        form=form,
        reopen_form=reopen_form,
        evidence_review_form=EvidenceReviewForm(prefix="evidence_review"),
        status_labels=STATUS_LABELS,
    )


@bp.post("/<uuid:assessment_public_id>/review/<uuid:question_public_id>/reopen")
@login_required
@roles_required("admin", "reviewer")
def reopen_question(assessment_public_id, question_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_review(current_user, assessment):
        abort(403)
    item = _question_or_404(assessment, str(question_public_id))
    if item.response is None:
        abort(404)
    form = ReopenForm(prefix="reopen")
    if form.validate_on_submit():
        try:
            review_service.reopen(item.response, comment=form.comment.data, reviewer_id=current_user.id)
        except DomainError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Pregunta reabierta y enviada al respondedor.", "success")
    return redirect(url_for("assessments.review_question", assessment_public_id=assessment.public_id, question_public_id=item.public_id))


@bp.post("/evidences/<uuid:evidence_public_id>/review")
@login_required
@roles_required("admin", "reviewer")
def review_evidence(evidence_public_id):
    evidence = evidence_repository.get_active_by_public_id(str(evidence_public_id))
    if evidence is None:
        abort(404)
    assessment = evidence.assessment_question.assessment
    if not can_review(current_user, assessment):
        abort(403)
    form = EvidenceReviewForm(prefix="evidence_review", meta={"csrf": False})
    if form.validate_on_submit() and form.evidence_public_id.data == evidence.public_id:
        try:
            review_service.review_evidence(
                evidence,
                status=EvidenceValidationStatus(form.validation_status.data),
                comment=form.comment.data,
                reviewer_id=current_user.id,
            )
        except (ValueError, DomainError) as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Validación de evidencia actualizada.", "success")
    else:
        flash("No fue posible validar la evidencia.", "danger")
    return redirect(url_for("assessments.review_question", assessment_public_id=assessment.public_id, question_public_id=evidence.assessment_question.public_id))


@bp.post("/<uuid:assessment_public_id>/review-notes")
@login_required
@roles_required("admin", "reviewer")
def add_review_note(assessment_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_review(current_user, assessment):
        abort(403)
    form = ReviewNoteForm(prefix="note")
    if form.validate_on_submit():
        try:
            review_service.add_note(assessment, body=form.body.data, author_id=current_user.id)
        except DomainError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Observación general registrada.", "success")
    return redirect(url_for("assessments.detail", assessment_public_id=assessment.public_id))


@bp.post("/<uuid:assessment_public_id>/review-notes/<uuid:note_public_id>/resolve")
@login_required
@roles_required("admin", "reviewer")
def resolve_review_note(assessment_public_id, note_public_id):
    assessment = _assessment_or_404(str(assessment_public_id))
    if not can_review(current_user, assessment):
        abort(403)
    note = db.session.scalar(
        select(AssessmentReviewNote).where(
            AssessmentReviewNote.public_id == str(note_public_id),
            AssessmentReviewNote.assessment_id == assessment.id,
        )
    )
    if note is None:
        abort(404)
    form = EmptyActionForm()
    if not form.validate_on_submit():
        abort(400)
    review_service.resolve_note(note, actor_id=current_user.id)
    flash("Observación marcada como resuelta.", "success")
    return redirect(url_for("assessments.detail", assessment_public_id=assessment.public_id))
