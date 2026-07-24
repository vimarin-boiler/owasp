from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog
from app.services.audit_service import audit_service


def test_audit_redacts_sensitive_keys(app, admin_user):
    with app.app_context():
        audit_service.record(
            action="test.redaction",
            entity_type="test",
            actor_user_id=admin_user.id,
            after={"password": "NeverStoreMe", "safe": "visible"},
        )
        db.session.commit()
        event = db.session.scalar(select(AuditLog).where(AuditLog.action == "test.redaction"))
        assert event.after_json["password"] == "[REDACTED]"
        assert event.after_json["safe"] == "visible"
