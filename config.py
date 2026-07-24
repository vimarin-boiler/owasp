from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"La variable {name} debe ser un entero.") from exc


class BaseConfig:
    APP_NAME = os.getenv("APP_NAME", "NTT DevSecOps Assessment")
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'samm_assessment.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH_MB = env_int("MAX_CONTENT_LENGTH_MB", 20)
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = {
        item.strip().lower()
        for item in os.getenv(
            "ALLOWED_EXTENSIONS", "pdf,docx,xlsx,pptx,txt,csv,png,jpg,jpeg,zip"
        ).split(",")
        if item.strip()
    }
    MAX_EVIDENCE_FILES_PER_QUESTION = env_int("MAX_EVIDENCE_FILES_PER_QUESTION", 10)

    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "samm_session")
    SESSION_COOKIE_HTTPONLY = env_bool("SESSION_COOKIE_HTTPONLY", True)
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    SESSION_REFRESH_EACH_REQUEST = True
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=env_int("SESSION_ABSOLUTE_TIMEOUT_MINUTES", 480)
    )
    SESSION_IDLE_TIMEOUT_MINUTES = env_int("SESSION_IDLE_TIMEOUT_MINUTES", 30)
    SESSION_ABSOLUTE_TIMEOUT_MINUTES = env_int("SESSION_ABSOLUTE_TIMEOUT_MINUTES", 480)

    LOGIN_MAX_FAILED_ATTEMPTS = env_int("LOGIN_MAX_FAILED_ATTEMPTS", 5)
    LOGIN_LOCKOUT_MINUTES = env_int("LOGIN_LOCKOUT_MINUTES", 15)
    PASSWORD_MIN_LENGTH = env_int("PASSWORD_MIN_LENGTH", 12)

    INITIAL_ADMIN_NAME = os.getenv("INITIAL_ADMIN_NAME", "Administrador")
    INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
    INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "")

    ASSESSMENT_AUTOSAVE_SECONDS = env_int("ASSESSMENT_AUTOSAVE_SECONDS", 30)
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per day;50 per hour")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    FORCE_HTTPS = env_bool("FORCE_HTTPS", False)
    TRUST_PROXY_HEADERS = env_bool("TRUST_PROXY_HEADERS", True)
    _TRUSTED_HOSTS_RAW = os.getenv("TRUSTED_HOSTS", "").strip()
    TRUSTED_HOSTS = (
        [host.strip() for host in _TRUSTED_HOSTS_RAW.split(",") if host.strip()]
        if _TRUSTED_HOSTS_RAW
        else None
    )
    PREFERRED_URL_SCHEME = "https" if FORCE_HTTPS else "http"

    WTF_CSRF_TIME_LIMIT = timedelta(hours=2)
    WTF_CSRF_SSL_STRICT = True

    @classmethod
    def validate(cls) -> None:
        if not cls.SECRET_KEY or cls.SECRET_KEY == "change-me":
            raise RuntimeError(
                "SECRET_KEY no está configurada o conserva un valor inseguro."
            )


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)


class TestingConfig(BaseConfig):
    TESTING = True
    SECRET_KEY = "test-secret-key-only"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    LOGIN_MAX_FAILED_ATTEMPTS = 3
    LOGIN_LOCKOUT_MINUTES = 5

    @classmethod
    def validate(cls) -> None:
        return None


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    FORCE_HTTPS = True


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def validate_runtime_config(config: dict) -> None:
    secret_key = config.get("SECRET_KEY", "")
    insecure_examples = {"change-me", "replace-with-at-least-32-random-bytes"}
    if not secret_key or secret_key in insecure_examples or len(secret_key) < 32:
        raise RuntimeError(
            "SECRET_KEY debe estar configurada con al menos 32 caracteres y no usar valores de ejemplo."
        )
    if config.get("FORCE_HTTPS") and not config.get("SESSION_COOKIE_SECURE"):
        raise RuntimeError(
            "SESSION_COOKIE_SECURE debe estar habilitada cuando FORCE_HTTPS está activo."
        )
