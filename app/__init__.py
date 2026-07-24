from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from uuid import uuid4

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from flask_login import current_user, logout_user
from flask_wtf.csrf import CSRFError
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from werkzeug.middleware.proxy_fix import ProxyFix

from config import CONFIG_BY_NAME, validate_runtime_config
from app.common.logging import configure_logging
from app.common.security_headers import register_security_headers
from app.extensions import csrf, db, limiter, login_manager, migrate
from app.version import __version__


@event.listens_for(Engine, "connect")
def _configure_sqlite(dbapi_connection, connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def create_app(config_name: str | None = None, config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    selected = config_name or __import__("os").getenv("FLASK_ENV", "development")
    config_class = CONFIG_BY_NAME.get(selected, CONFIG_BY_NAME["development"])
    app.config.from_object(config_class)
    app.config["CONFIG_CLASS"] = config_class
    if config_overrides:
        app.config.update(config_overrides)
    if not app.testing:
        validate_runtime_config(app.config)

    configure_logging(app.config["LOG_LEVEL"])
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["CATALOG_IMPORT_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["REPORT_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["BACKUP_FOLDER"]).mkdir(parents=True, exist_ok=True)

    if app.config.get("TRUST_PROXY_HEADERS", True):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Debes iniciar sesión para acceder a esta página."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"

    from app import models  # noqa: F401
    from app.admin import bp as admin_bp
    from app.api import v1_bp
    from app.auth import bp as auth_bp
    from app.assessments import bp as assessments_bp
    from app.catalog import bp as catalog_bp
    from app.dashboard import bp as dashboard_bp
    from app.results import bp as results_bp
    from app.reports import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(assessments_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(v1_bp)

    from app.cli import register_cli

    register_cli(app)
    register_security_headers(app)
    _register_login_loader()
    _register_request_hooks(app)
    _register_error_handlers(app)
    _register_template_context(app)
    return app


def _register_login_loader() -> None:
    from app.models import User

    @login_manager.user_loader
    def load_user(public_id: str):
        return db.session.scalar(
            select(User).where(User.public_id == public_id, User.is_active.is_(True))
        )


def _register_request_hooks(app: Flask) -> None:
    @app.before_request
    def request_context_and_session_security():
        g.correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))[:36]
        if request.endpoint == "static":
            return None
        if not current_user.is_authenticated:
            return None

        now = time.time()
        idle_limit = app.config["SESSION_IDLE_TIMEOUT_MINUTES"] * 60
        absolute_limit = app.config["SESSION_ABSOLUTE_TIMEOUT_MINUTES"] * 60
        last_activity = session.get("last_activity", now)
        login_at = session.get("login_at", now)
        if now - last_activity > idle_limit or now - login_at > absolute_limit:
            logout_user()
            session.clear()
            flash("La sesión expiró por seguridad. Inicia sesión nuevamente.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        session["last_activity"] = now

        allowed = {"auth.change_password", "auth.logout", "static"}
        if current_user.must_change_password and request.endpoint not in allowed:
            flash("Debes cambiar tu contraseña antes de continuar.", "warning")
            return redirect(url_for("auth.change_password"))
        return None

    @app.after_request
    def correlation_header(response):
        response.headers["X-Correlation-ID"] = getattr(g, "correlation_id", "")
        return response


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(CSRFError)
    def handle_csrf(error):
        app.logger.warning("CSRF rechazado: %s", error.description)
        return render_template("errors/csrf.html", reason=error.description), 400

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def request_too_large(error):
        return render_template(
            "errors/413.html",
            maximum_mb=app.config.get("MAX_REQUEST_CONTENT_LENGTH_MB", 200),
        ), 413

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.exception("Error interno no controlado", exc_info=error)
        return render_template("errors/500.html"), 500


def _register_template_context(app: Flask) -> None:
    @app.context_processor
    def inject_globals():
        return {
            "app_name": app.config["APP_NAME"],
            "app_version": __version__,
            "chart_js_url": app.config["CHART_JS_URL"],
        }
