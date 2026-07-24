from __future__ import annotations

from urllib.parse import urljoin, urlparse

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth.forms import ChangePasswordForm, LoginForm
from app.extensions import db, limiter
from app.services import audit_service, auth_service

bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="templates")


def _is_safe_redirect(target: str | None) -> bool:
    if not target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in {"http", "https"} and host_url.netloc == redirect_url.netloc


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        destination = "auth.change_password" if current_user.must_change_password else "dashboard.index"
        return redirect(url_for(destination))

    form = LoginForm()
    if form.validate_on_submit():
        result = auth_service.authenticate(form.email.data, form.password.data)
        if result.user:
            session.clear()
            login_user(result.user, remember=form.remember.data, fresh=True)
            session.permanent = True
            now = __import__("time").time()
            session["login_at"] = now
            session["last_activity"] = now
            next_url = request.args.get("next")
            if result.user.must_change_password:
                flash("Por seguridad debes cambiar tu contraseña inicial.", "warning")
                return redirect(url_for("auth.change_password"))
            flash(f"Bienvenido, {result.user.display_name}.", "success")
            return redirect(next_url if _is_safe_redirect(next_url) else url_for("dashboard.index"))
        flash(result.error or "No fue posible iniciar sesión.", "danger")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    user_public_id = current_user.public_id
    user_id = current_user.id
    audit_service.record(
        action="auth.logout",
        entity_type="user",
        entity_public_id=user_public_id,
        actor_user_id=user_id,
    )
    db.session.commit()
    logout_user()
    session.clear()
    flash("La sesión se cerró correctamente.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        user = current_user._get_current_object()
        try:
            auth_service.change_password(
                user, form.current_password.data, form.new_password.data
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            session.clear()
            login_user(user, fresh=True)
            session.permanent = True
            now = __import__("time").time()
            session["login_at"] = now
            session["last_activity"] = now
            flash("La contraseña fue actualizada correctamente.", "success")
            next_url = request.args.get("next")
            return redirect(next_url if _is_safe_redirect(next_url) else url_for("dashboard.index"))
    return render_template("auth/change_password.html", form=form)
