from datetime import datetime
from typing import List, Dict
from app.schemas.pydantic_schemas import NotificationResponse

class NotificationService:
    @staticmethod
    def get_user_notifications(user_id: int) -> List[NotificationResponse]:
        """
        Dispatches and retrieves daily guidance alerts, push notifications, and reading reminders.
        """
        return [
            NotificationResponse(
                id=1,
                title="Daily Insight Available",
                message="Your daily card guidance is ready to be drawn.",
                is_read=False,
                created_at=datetime.utcnow()
            ),
            NotificationResponse(
                id=2,
                title="Weekly Reading Reminder",
                message="Don't forget to track your life trends for this week.",
                is_read=True,
                created_at=datetime.utcnow()
            )
        ]

    @staticmethod
    def mark_as_read(notification_id: int) -> Dict[str, str]:
        return {"status": "success", "message": f"Notification {notification_id} marked as read."}