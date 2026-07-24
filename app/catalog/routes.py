from __future__ import annotations

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.catalog.forms import (
    AnswerSetForm,
    BusinessFunctionForm,
    ConfirmActionForm,
    DuplicateQuestionForm,
    ImportConfirmForm,
    ImportUploadForm,
    MaturityLevelForm,
    PracticeStreamForm,
    QuestionForm,
    QuestionnaireVersionForm,
    SecurityPracticeForm,
)
from app.common.errors import DomainError
from app.common.permissions import admin_required
from app.enums import CatalogImportStatus
from app.extensions import db
from app.repositories.catalog import catalog_repository
from app.services.catalog_export_service import catalog_export_service
from app.services.catalog_service import catalog_service
from app.services.questionnaire_service import questionnaire_service
from app.services.samm_import_service import catalog_import_service

bp = Blueprint("catalog", __name__, url_prefix="/catalog", template_folder="templates")


def _handle_service_error(exc: Exception) -> None:
    db.session.rollback()
    flash(str(exc), "danger")


def _handle_unexpected_error(exc: Exception) -> None:
    db.session.rollback()
    current_app.logger.exception("Unexpected catalog operation failure", exc_info=exc)
    flash("Ocurrió un error interno. Revisa la bitácora de la aplicación.", "danger")


def _function_choices() -> list[tuple[int, str]]:
    return [(item.id, f"{item.code} · {item.name}") for item in catalog_repository.business_functions(active_only=True)]


def _practice_choices() -> list[tuple[int, str]]:
    return [(item.id, f"{item.code} · {item.name}") for item in catalog_repository.security_practices(active_only=True)]


def _stream_choices() -> list[tuple[int, str]]:
    return [(item.id, f"{item.code} · {item.name}") for item in catalog_repository.practice_streams(active_only=True)]


def _level_choices() -> list[tuple[int, str]]:
    return [(item.id, f"Nivel {item.level_number} · {item.name}") for item in catalog_repository.maturity_levels(active_only=True)]


def _answer_set_choices() -> list[tuple[int, str]]:
    return [(item.id, f"{item.external_code} · {item.name}") for item in catalog_repository.answer_sets(active_only=True)]


def _configure_question_choices(form: QuestionForm) -> None:
    form.business_function_id.choices = _function_choices()
    form.security_practice_id.choices = _practice_choices()
    form.practice_stream_id.choices = _stream_choices()
    form.maturity_level_id.choices = _level_choices()
    form.answer_set_id.choices = _answer_set_choices()


@bp.route("/")
@login_required
@admin_required
def index():
    functions = catalog_repository.business_functions(active_only=False)
    practices = catalog_repository.security_practices(active_only=False)
    streams = catalog_repository.practice_streams(active_only=False)
    levels = catalog_repository.maturity_levels(active_only=False)
    questions = catalog_repository.questions()
    versions = catalog_repository.questionnaire_versions()
    return render_template(
        "catalog/index.html",
        counts={
            "functions": len(functions),
            "practices": len(practices),
            "streams": len(streams),
            "levels": len(levels),
            "questions": len(questions),
            "versions": len(versions),
        },
        latest_versions=versions[:5],
        recent_imports=catalog_repository.imports()[:5],
    )


@bp.route("/imports")
@login_required
@admin_required
def imports():
    return render_template("catalog/imports.html", imports=catalog_repository.imports())


@bp.route("/imports/new", methods=["GET", "POST"])
@login_required
@admin_required
def import_new():
    form = ImportUploadForm()
    if form.validate_on_submit():
        try:
            record = catalog_import_service.create_preview_from_upload(form.workbook.data, current_user.id)
        except (ValueError, OSError) as exc:
            _handle_service_error(exc)
        else:
            if record.status == CatalogImportStatus.INVALID:
                flash("El archivo contiene errores. Revisa el detalle antes de continuar.", "warning")
            else:
                flash("Archivo validado. Revisa la vista previa y confirma la importación.", "success")
            return redirect(url_for("catalog.import_preview", import_public_id=record.public_id))
    return render_template("catalog/import_upload.html", form=form)


@bp.route("/imports/<uuid:import_public_id>", methods=["GET", "POST"])
@login_required
@admin_required
def import_preview(import_public_id):
    record = catalog_repository.import_by_public_id(str(import_public_id))
    if record is None:
        abort(404)
    form = ImportConfirmForm()
    if request.method == "GET":
        source_version = record.source_version or "1.0.0"
        form.version_name.data = f"OWASP SAMM {source_version}"
        form.version_number.data = source_version
        form.description.data = f"Importada desde {record.source_name}."
    if form.validate_on_submit():
        try:
            version = catalog_import_service.confirm(
                record,
                version_name=form.version_name.data,
                version_number=form.version_number.data,
                description=form.description.data,
                publish=form.publish.data,
                actor_id=current_user.id,
            )
        except (DomainError, ValueError, OSError) as exc:
            _handle_service_error(exc)
        except Exception as exc:  # pragma: no cover - protección de último recurso
            _handle_unexpected_error(exc)
        else:
            flash("Catálogo importado correctamente.", "success")
            return redirect(url_for("catalog.version_detail", version_public_id=version.public_id))
    preview = record.preview_json or {}
    return render_template("catalog/import_preview.html", record=record, preview=preview, form=form)


@bp.route("/functions")
@login_required
@admin_required
def functions():
    return render_template("catalog/functions.html", items=catalog_repository.business_functions(active_only=False))


@bp.route("/functions/new", methods=["GET", "POST"])
@login_required
@admin_required
def function_new():
    form = BusinessFunctionForm()
    if form.validate_on_submit():
        try:
            catalog_service.create_business_function(code=form.code.data, name=form.name.data, description=form.description.data, sort_order=form.sort_order.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Función creada correctamente.", "success")
            return redirect(url_for("catalog.functions"))
    return render_template("catalog/master_form.html", form=form, title="Nueva función", subtitle="Funciones de negocio", back_endpoint="catalog.functions")


@bp.route("/functions/<uuid:item_public_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def function_edit(item_public_id):
    item = catalog_repository.business_function_by_public_id(str(item_public_id))
    if item is None:
        abort(404)
    form = BusinessFunctionForm(obj=item)
    if form.validate_on_submit():
        try:
            catalog_service.update_business_function(item, code=form.code.data, name=form.name.data, description=form.description.data, sort_order=form.sort_order.data, is_active=form.is_active.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Función actualizada.", "success")
            return redirect(url_for("catalog.functions"))
    return render_template("catalog/master_form.html", form=form, title="Editar función", subtitle="Funciones de negocio", back_endpoint="catalog.functions")


@bp.route("/practices")
@login_required
@admin_required
def practices():
    return render_template("catalog/practices.html", items=catalog_repository.security_practices(active_only=False))


@bp.route("/practices/new", methods=["GET", "POST"])
@login_required
@admin_required
def practice_new():
    form = SecurityPracticeForm()
    form.business_function_id.choices = _function_choices()
    if form.validate_on_submit():
        try:
            catalog_service.create_security_practice(business_function_id=form.business_function_id.data, code=form.code.data, name=form.name.data, description=form.description.data, sort_order=form.sort_order.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Práctica creada correctamente.", "success")
            return redirect(url_for("catalog.practices"))
    return render_template("catalog/master_form.html", form=form, title="Nueva práctica", subtitle="Prácticas de seguridad", back_endpoint="catalog.practices")


@bp.route("/practices/<uuid:item_public_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def practice_edit(item_public_id):
    item = catalog_repository.security_practice_by_public_id(str(item_public_id))
    if item is None:
        abort(404)
    form = SecurityPracticeForm(obj=item)
    form.business_function_id.choices = _function_choices()
    if form.validate_on_submit():
        try:
            catalog_service.update_security_practice(item, business_function_id=form.business_function_id.data, code=form.code.data, name=form.name.data, description=form.description.data, sort_order=form.sort_order.data, is_active=form.is_active.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Práctica actualizada.", "success")
            return redirect(url_for("catalog.practices"))
    return render_template("catalog/master_form.html", form=form, title="Editar práctica", subtitle="Prácticas de seguridad", back_endpoint="catalog.practices")


@bp.route("/streams")
@login_required
@admin_required
def streams():
    return render_template("catalog/streams.html", items=catalog_repository.practice_streams(active_only=False))


@bp.route("/streams/new", methods=["GET", "POST"])
@login_required
@admin_required
def stream_new():
    form = PracticeStreamForm()
    form.security_practice_id.choices = _practice_choices()
    if form.validate_on_submit():
        try:
            catalog_service.create_practice_stream(security_practice_id=form.security_practice_id.data, code=form.code.data, name=form.name.data, description=form.description.data, sort_order=form.sort_order.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Flujo creado correctamente.", "success")
            return redirect(url_for("catalog.streams"))
    return render_template("catalog/master_form.html", form=form, title="Nuevo flujo", subtitle="Flujos o subcategorías", back_endpoint="catalog.streams")


@bp.route("/streams/<uuid:item_public_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def stream_edit(item_public_id):
    item = catalog_repository.practice_stream_by_public_id(str(item_public_id))
    if item is None:
        abort(404)
    form = PracticeStreamForm(obj=item)
    form.security_practice_id.choices = _practice_choices()
    if form.validate_on_submit():
        try:
            catalog_service.update_practice_stream(item, security_practice_id=form.security_practice_id.data, code=form.code.data, name=form.name.data, description=form.description.data, sort_order=form.sort_order.data, is_active=form.is_active.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Flujo actualizado.", "success")
            return redirect(url_for("catalog.streams"))
    return render_template("catalog/master_form.html", form=form, title="Editar flujo", subtitle="Flujos o subcategorías", back_endpoint="catalog.streams")


@bp.route("/levels")
@login_required
@admin_required
def levels():
    return render_template("catalog/levels.html", items=catalog_repository.maturity_levels(active_only=False))


@bp.route("/levels/new", methods=["GET", "POST"])
@login_required
@admin_required
def level_new():
    form = MaturityLevelForm()
    if form.validate_on_submit():
        try:
            catalog_service.create_maturity_level(level_number=form.level_number.data, name=form.name.data, description=form.description.data, max_score=form.max_score.data, sort_order=form.sort_order.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Nivel creado correctamente.", "success")
            return redirect(url_for("catalog.levels"))
    return render_template("catalog/master_form.html", form=form, title="Nuevo nivel", subtitle="Niveles de madurez", back_endpoint="catalog.levels")


@bp.route("/levels/<uuid:item_public_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def level_edit(item_public_id):
    item = catalog_repository.maturity_level_by_public_id(str(item_public_id))
    if item is None:
        abort(404)
    form = MaturityLevelForm(obj=item)
    if form.validate_on_submit():
        try:
            catalog_service.update_maturity_level(item, level_number=form.level_number.data, name=form.name.data, description=form.description.data, max_score=form.max_score.data, sort_order=form.sort_order.data, is_active=form.is_active.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Nivel actualizado.", "success")
            return redirect(url_for("catalog.levels"))
    return render_template("catalog/master_form.html", form=form, title="Editar nivel", subtitle="Niveles de madurez", back_endpoint="catalog.levels")


@bp.route("/answer-sets")
@login_required
@admin_required
def answer_sets():
    return render_template("catalog/answer_sets.html", items=catalog_repository.answer_sets(active_only=False))


def _populate_answer_set_form(form: AnswerSetForm, item) -> None:
    options = sorted(item.options, key=lambda option: option.sort_order)
    fields = (("a", 0), ("b", 1), ("c", 2), ("d", 3))
    for suffix, index in fields:
        if index < len(options):
            getattr(form, f"option_{suffix}_text").data = options[index].text
            getattr(form, f"option_{suffix}_weight").data = options[index].weight


@bp.route("/answer-sets/new", methods=["GET", "POST"])
@login_required
@admin_required
def answer_set_new():
    form = AnswerSetForm()
    if form.validate_on_submit():
        try:
            catalog_service.create_answer_set(external_code=form.external_code.data, name=form.name.data, description=form.description.data, options=form.options_payload(), actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Conjunto de respuestas creado.", "success")
            return redirect(url_for("catalog.answer_sets"))
    return render_template("catalog/answer_set_form.html", form=form, title="Nuevo conjunto", back_endpoint="catalog.answer_sets")


@bp.route("/answer-sets/<uuid:item_public_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def answer_set_edit(item_public_id):
    item = catalog_repository.answer_set_by_public_id(str(item_public_id))
    if item is None:
        abort(404)
    form = AnswerSetForm(obj=item)
    if request.method == "GET":
        _populate_answer_set_form(form, item)
    if form.validate_on_submit():
        try:
            catalog_service.update_answer_set(item, external_code=form.external_code.data, name=form.name.data, description=form.description.data, options=form.options_payload(), is_active=form.is_active.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Conjunto de respuestas actualizado.", "success")
            return redirect(url_for("catalog.answer_sets"))
    return render_template("catalog/answer_set_form.html", form=form, title="Editar conjunto", item=item, back_endpoint="catalog.answer_sets")


@bp.route("/questions")
@login_required
@admin_required
def questions():
    search = request.args.get("q", "").strip()
    return render_template("catalog/questions.html", items=catalog_repository.questions(search), search=search)


@bp.route("/questions/new", methods=["GET", "POST"])
@login_required
@admin_required
def question_new():
    form = QuestionForm()
    _configure_question_choices(form)
    if form.validate_on_submit():
        try:
            question = catalog_service.create_question(external_code=form.external_code.data, canonical_name=form.canonical_name.data, business_function_id=form.business_function_id.data, security_practice_id=form.security_practice_id.data, practice_stream_id=form.practice_stream_id.data, maturity_level_id=form.maturity_level_id.data, answer_set_id=form.answer_set_id.data, question_text=form.question_text.data, guidance_text=form.guidance_text.data, criteria=form.criteria(), change_reason=form.change_reason.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Pregunta creada en revisión 1.", "success")
            return redirect(url_for("catalog.question_detail", question_public_id=question.public_id))
    return render_template("catalog/question_form.html", form=form, title="Nueva pregunta", creating=True)


@bp.route("/questions/<uuid:question_public_id>")
@login_required
@admin_required
def question_detail(question_public_id):
    question = catalog_repository.question_by_public_id(str(question_public_id))
    if question is None:
        abort(404)
    return render_template("catalog/question_detail.html", question=question, duplicate_form=DuplicateQuestionForm())


@bp.route("/questions/<uuid:question_public_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def question_edit(question_public_id):
    question = catalog_repository.question_by_public_id(str(question_public_id))
    if question is None or question.current_revision is None:
        abort(404)
    revision = question.current_revision
    form = QuestionForm()
    _configure_question_choices(form)
    if request.method == "GET":
        form.external_code.data = question.external_code
        form.external_code.render_kw = {"readonly": True}
        form.canonical_name.data = question.canonical_name
        form.business_function_id.data = revision.business_function_id
        form.security_practice_id.data = revision.security_practice_id
        form.practice_stream_id.data = revision.practice_stream_id
        form.maturity_level_id.data = revision.maturity_level_id
        form.answer_set_id.data = revision.answer_set_id
        form.question_text.data = revision.question_text
        form.guidance_text.data = revision.guidance_text
        form.criteria_text.data = "\n".join(item.criterion_text for item in revision.criteria)
        form.is_active.data = question.is_active
    if form.validate_on_submit():
        try:
            catalog_service.revise_question(question, canonical_name=form.canonical_name.data, business_function_id=form.business_function_id.data, security_practice_id=form.security_practice_id.data, practice_stream_id=form.practice_stream_id.data, maturity_level_id=form.maturity_level_id.data, answer_set_id=form.answer_set_id.data, question_text=form.question_text.data, guidance_text=form.guidance_text.data, criteria=form.criteria(), change_reason=form.change_reason.data or "", is_active=form.is_active.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Se creó una nueva revisión sin modificar el historial anterior.", "success")
            return redirect(url_for("catalog.question_detail", question_public_id=question.public_id))
    return render_template("catalog/question_form.html", form=form, title=f"Nueva revisión de {question.external_code}", question=question, creating=False)


@bp.route("/questions/<uuid:question_public_id>/duplicate", methods=["POST"])
@login_required
@admin_required
def question_duplicate(question_public_id):
    question = catalog_repository.question_by_public_id(str(question_public_id))
    if question is None:
        abort(404)
    form = DuplicateQuestionForm()
    if form.validate_on_submit():
        try:
            duplicate = catalog_service.duplicate_question(question, new_external_code=form.new_external_code.data, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Pregunta duplicada correctamente.", "success")
            return redirect(url_for("catalog.question_detail", question_public_id=duplicate.public_id))
    else:
        flash("El nuevo identificador no es válido.", "danger")
    return redirect(url_for("catalog.question_detail", question_public_id=question.public_id))


@bp.route("/versions")
@login_required
@admin_required
def versions():
    return render_template("catalog/versions.html", items=catalog_repository.questionnaire_versions())


@bp.route("/versions/new", methods=["GET", "POST"])
@login_required
@admin_required
def version_new():
    form = QuestionnaireVersionForm()
    existing = catalog_repository.questionnaire_versions()
    form.source_version_id.choices = [(0, "Usar revisiones vigentes del catálogo")] + [(item.id, f"{item.version_number} · {item.name}") for item in existing]
    if form.validate_on_submit():
        try:
            version = questionnaire_service.create_version(name=form.name.data, version_number=form.version_number.data, description=form.description.data, actor_id=current_user.id, source_version_id=form.source_version_id.data or None)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Versión en borrador creada.", "success")
            return redirect(url_for("catalog.version_detail", version_public_id=version.public_id))
    return render_template("catalog/version_form.html", form=form)


@bp.route("/versions/<uuid:version_public_id>")
@login_required
@admin_required
def version_detail(version_public_id):
    version = catalog_repository.questionnaire_version_by_public_id(str(version_public_id))
    if version is None:
        abort(404)
    return render_template("catalog/version_detail.html", version=version, action_form=ConfirmActionForm())


@bp.route("/versions/<uuid:version_public_id>/publish", methods=["POST"])
@login_required
@admin_required
def version_publish(version_public_id):
    version = catalog_repository.questionnaire_version_by_public_id(str(version_public_id))
    if version is None:
        abort(404)
    form = ConfirmActionForm()
    if form.validate_on_submit():
        try:
            questionnaire_service.publish(version, actor_id=current_user.id)
        except DomainError as exc:
            _handle_service_error(exc)
        else:
            flash("Versión publicada. La versión publicada anterior fue archivada.", "success")
    return redirect(url_for("catalog.version_detail", version_public_id=version.public_id))


@bp.route("/versions/<uuid:version_public_id>/archive", methods=["POST"])
@login_required
@admin_required
def version_archive(version_public_id):
    version = catalog_repository.questionnaire_version_by_public_id(str(version_public_id))
    if version is None:
        abort(404)
    form = ConfirmActionForm()
    if form.validate_on_submit():
        questionnaire_service.archive(version, actor_id=current_user.id)
        flash("Versión archivada.", "success")
    return redirect(url_for("catalog.version_detail", version_public_id=version.public_id))


@bp.route("/versions/<uuid:version_public_id>/export")
@login_required
@admin_required
def version_export(version_public_id):
    version = catalog_repository.questionnaire_version_by_public_id(str(version_public_id))
    if version is None:
        abort(404)
    output = catalog_export_service.build_workbook(version)
    return send_file(output, as_attachment=True, download_name=f"SAMM_{version.version_number}.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
