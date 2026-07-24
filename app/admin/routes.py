from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.admin.forms import OrganizationForm, ResetPasswordForm, UserCreateForm, UserEditForm
from app.common.errors import DomainError
from app.common.permissions import admin_required
from app.extensions import db
from app.repositories import audit_repository, organization_repository, user_repository
from app.services import organization_service, user_service

bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="templates")


def _role_choices() -> list[tuple[int, str]]:
    return [(role.id, role.name) for role in user_repository.roles()]


@bp.route("/users")
@login_required
@admin_required
def users():
    search = request.args.get("q", "").strip()
    return render_template("admin/users.html", users=user_repository.list(search), search=search)


@bp.route("/users/new", methods=["GET", "POST"])
@login_required
@admin_required
def user_create():
    form = UserCreateForm()
    form.role_ids.choices = _role_choices()
    if form.validate_on_submit():
        try:
            user_service.create_user(
                display_name=form.display_name.data,
                email=form.email.data,
                password=form.password.data,
                role_ids=form.role_ids.data,
                actor_id=current_user.id,
                is_active=form.is_active.data,
                must_change_password=form.must_change_password.data,
            )
        except DomainError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Usuario creado correctamente.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, title="Nuevo usuario", mode="create")


@bp.route("/users/<uuid:user_public_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def user_edit(user_public_id):
    user = user_repository.get_by_public_id(str(user_public_id))
    if user is None:
        abort(404)
    form = UserEditForm(obj=user)
    form.role_ids.choices = _role_choices()
    if request.method == "GET":
        form.role_ids.data = [link.role_id for link in user.role_links]
    if form.validate_on_submit():
        try:
            user_service.update_user(
                user,
                display_name=form.display_name.data,
                email=form.email.data,
                role_ids=form.role_ids.data,
                is_active=form.is_active.data,
                must_change_password=form.must_change_password.data,
                actor_id=current_user.id,
            )
        except DomainError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Usuario actualizado correctamente.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, title="Editar usuario", mode="edit", user=user)


@bp.route("/users/<uuid:user_public_id>/reset-password", methods=["GET", "POST"])
@login_required
@admin_required
def user_reset_password(user_public_id):
    user = user_repository.get_by_public_id(str(user_public_id))
    if user is None:
        abort(404)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        try:
            user_service.reset_password(user, form.password.data, current_user.id)
        except DomainError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Contraseña restablecida. El usuario deberá cambiarla al ingresar.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/reset_password.html", form=form, user=user)


@bp.route("/organizations")
@login_required
@admin_required
def organizations():
    search = request.args.get("q", "").strip()
    return render_template(
        "admin/organizations.html",
        organizations=organization_repository.list(search),
        search=search,
    )


@bp.route("/organizations/new", methods=["GET", "POST"])
@login_required
@admin_required
def organization_create():
    form = OrganizationForm()
    if form.validate_on_submit():
        try:
            organization_service.create(
                name=form.name.data,
                legal_name=form.legal_name.data,
                tax_identifier=form.tax_identifier.data,
                description=form.description.data,
                actor_id=current_user.id,
                is_active=form.is_active.data,
            )
        except DomainError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Organización creada correctamente.", "success")
            return redirect(url_for("admin.organizations"))
    return render_template("admin/organization_form.html", form=form, title="Nueva organización", mode="create")


@bp.route("/organizations/<uuid:organization_public_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def organization_edit(organization_public_id):
    organization = organization_repository.get_by_public_id(str(organization_public_id))
    if organization is None:
        abort(404)
    form = OrganizationForm(obj=organization)
    if form.validate_on_submit():
        try:
            organization_service.update(
                organization,
                name=form.name.data,
                legal_name=form.legal_name.data,
                tax_identifier=form.tax_identifier.data,
                description=form.description.data,
                is_active=form.is_active.data,
                actor_id=current_user.id,
            )
        except DomainError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Organización actualizada correctamente.", "success")
            return redirect(url_for("admin.organizations"))
    return render_template(
        "admin/organization_form.html",
        form=form,
        title="Editar organización",
        mode="edit",
        organization=organization,
    )


@bp.route("/audit")
@login_required
@admin_required
def audit():
    return render_template("admin/audit.html", events=audit_repository.recent(100))
