from __future__ import annotations

from config import settings
from database.db_service import DBService
from models.user_profile import UserProfile


class UserService:
    def __init__(self, db_service: DBService) -> None:
        self.db_service = db_service

    def bootstrap_local_user(self) -> UserProfile | None:
        self.db_service.init_db()
        self.db_service.create_default_user_if_not_exists()
        self.db_service.update_last_login(settings.DEFAULT_USER_ID)
        return self.db_service.get_current_user()

    def get_current_user(self) -> UserProfile | None:
        return self.db_service.get_current_user()

    def get_total_eco_points(self, user_id: str | None = None) -> int:
        safe_user_id = user_id or settings.DEFAULT_USER_ID
        return self.db_service.get_total_eco_points(safe_user_id)

    def add_eco_points(self, points: int, reason: str, user_id: str | None = None) -> int:
        safe_user_id = user_id or settings.DEFAULT_USER_ID
        return self.db_service.add_eco_points(user_id=safe_user_id, points=points, reason=reason)
