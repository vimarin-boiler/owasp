from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from flask import g, has_request_context, request
from flask_login import current_user

from app.extensions import db
from app.models import AuditLog

SENSITIVE_KEY_MARKERS = (
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "csrf",
)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key).casefold().replace("-", "_")
    return any(marker in normalized for marker in SENSITIVE_KEY_MARKERS)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _is_sensitive_key(key) else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value


class AuditService:
    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_public_id: str | None = None,
        actor_user_id: int | None = None,
        organization_id: int | None = None,
        assessment_id: int | None = None,
        before: dict | None = None,
        after: dict | None = None,
        result: str = "success",
        error_code: str | None = None,
    ) -> AuditLog:
        if actor_user_id is None and has_request_context() and current_user.is_authenticated:
            actor_user_id = current_user.id

        ip_address = None
        user_agent = None
        correlation_id = None
        if has_request_context():
            ip_address = request.remote_addr
            user_agent = request.user_agent.string[:500]
            correlation_id = getattr(g, "correlation_id", None)

        event = AuditLog(
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            assessment_id=assessment_id,
            action=action,
            entity_type=entity_type,
            entity_public_id=entity_public_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_json=_sanitize(before) if before else None,
            after_json=_sanitize(after) if after else None,
            result=result,
            error_code=error_code,
            correlation_id=correlation_id,
        )
        db.session.add(event)
        return event


audit_service = AuditService()
