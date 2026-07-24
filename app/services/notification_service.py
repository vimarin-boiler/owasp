from __future__ import annotations

from app.extensions import db
from app.models import Notification


class NotificationService:
    def create(self, user_id: int, title: str, body: str, link: str | None = None) -> Notification:
        notification = Notification(user_id=user_id, title=title[:220], body=body, link=link)
        db.session.add(notification)
        return notification


notification_service = NotificationService()
