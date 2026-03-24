from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from config import settings
from models.user_profile import UserProfile

logger = logging.getLogger(__name__)


class DBService:
    def __init__(
        self,
        db_path: Path | str = settings.DATABASE_PATH,
        schema_path: Path | str = settings.DATABASE_SCHEMA_FILE,
    ) -> None:
        self.db_path = Path(db_path)
        self.schema_path = Path(schema_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection

    def init_db(self) -> None:
        schema_sql = self._load_schema_sql()
        try:
            with self.connect() as connection:
                connection.executescript(schema_sql)
                connection.commit()
        except sqlite3.Error as exc:
            logger.warning("Khong the khoi tao database tai %s: %s", self.db_path, exc)

    def create_default_user_if_not_exists(self) -> None:
        now = self._now_sql()
        try:
            with self.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO user_profile(
                        user_id,
                        display_name,
                        email,
                        avatar_path,
                        created_at,
                        last_login_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO NOTHING
                    """,
                    (
                        settings.DEFAULT_USER_ID,
                        settings.DEFAULT_USER_DISPLAY_NAME,
                        settings.DEFAULT_USER_EMAIL,
                        settings.DEFAULT_USER_AVATAR_PATH,
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO eco_wallet(user_id, total_eco_points, updated_at)
                    VALUES(?, 0, ?)
                    ON CONFLICT(user_id) DO NOTHING
                    """,
                    (settings.DEFAULT_USER_ID, now),
                )
                connection.commit()
        except sqlite3.Error as exc:
            logger.warning("Khong the tao user mac dinh: %s", exc)

    def get_current_user(self) -> UserProfile | None:
        try:
            with self.connect() as connection:
                row = connection.execute(
                    """
                    SELECT user_id, display_name, email, avatar_path, created_at, last_login_at
                    FROM user_profile
                    WHERE user_id = ?
                    """,
                    (settings.DEFAULT_USER_ID,),
                ).fetchone()
        except sqlite3.Error as exc:
            logger.warning("Khong the doc current user: %s", exc)
            return None

        if row is None:
            return None

        return UserProfile(
            user_id=str(row["user_id"]),
            display_name=str(row["display_name"]),
            email=str(row["email"]),
            avatar_path=str(row["avatar_path"] or ""),
            created_at=str(row["created_at"]),
            last_login_at=str(row["last_login_at"]),
        )

    def get_total_eco_points(self, user_id: str) -> int:
        try:
            with self.connect() as connection:
                row = connection.execute(
                    """
                    SELECT total_eco_points
                    FROM eco_wallet
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            logger.warning("Khong the doc total eco points cho user %s: %s", user_id, exc)
            return 0

        return int(row["total_eco_points"]) if row else 0

    def add_eco_points(self, user_id: str, points: int, reason: str) -> int:
        safe_points = int(points)
        safe_reason = reason.strip() or "Cap nhat eco points"
        now = self._now_sql()

        try:
            with self.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO eco_wallet(user_id, total_eco_points, updated_at)
                    VALUES(?, 0, ?)
                    ON CONFLICT(user_id) DO NOTHING
                    """,
                    (user_id, now),
                )
                connection.execute(
                    """
                    INSERT INTO reward_transactions(user_id, points, reason, created_at)
                    VALUES(?, ?, ?, ?)
                    """,
                    (user_id, safe_points, safe_reason, now),
                )
                connection.execute(
                    """
                    UPDATE eco_wallet
                    SET total_eco_points = total_eco_points + ?,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (safe_points, now, user_id),
                )
                row = connection.execute(
                    """
                    SELECT total_eco_points
                    FROM eco_wallet
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ).fetchone()
                connection.commit()
        except sqlite3.Error as exc:
            logger.warning("Khong the cong eco points cho user %s: %s", user_id, exc)
            return self.get_total_eco_points(user_id)

        return int(row["total_eco_points"]) if row else 0

    def update_last_login(self, user_id: str) -> None:
        try:
            with self.connect() as connection:
                connection.execute(
                    """
                    UPDATE user_profile
                    SET last_login_at = ?
                    WHERE user_id = ?
                    """,
                    (self._now_sql(), user_id),
                )
                connection.commit()
        except sqlite3.Error as exc:
            logger.warning("Khong the cap nhat last_login_at cho user %s: %s", user_id, exc)

    def get_recent_reward_actions(self, user_id: str, limit: int) -> list[sqlite3.Row]:
        try:
            with self.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT reason AS action_name, points, created_at
                    FROM reward_transactions
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()
                return list(rows)
        except sqlite3.Error as exc:
            logger.warning("Khong the doc reward transactions cho user %s: %s", user_id, exc)
            return []

    def save_crowd_snapshot(
        self,
        zone: str,
        level: int,
        recommendation: str,
        created_at: str,
    ) -> None:
        try:
            with self.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO crowd_snapshots(zone, level, recommendation, created_at)
                    VALUES(?, ?, ?, ?)
                    """,
                    (zone, level, recommendation, created_at),
                )
                connection.commit()
        except sqlite3.Error as exc:
            logger.warning("Khong the luu crowd snapshot: %s", exc)

    def get_recent_crowd_snapshots(self, limit: int) -> list[sqlite3.Row]:
        try:
            with self.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT zone, level, recommendation, created_at
                    FROM crowd_snapshots
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                return list(rows)
        except sqlite3.Error as exc:
            logger.warning("Khong the doc crowd snapshots: %s", exc)
            return []

    def get_reward_points(self, user_id: str) -> int:
        return self.get_total_eco_points(user_id)

    def add_reward_points(self, user_id: str, action_name: str, points: int) -> int:
        return self.add_eco_points(user_id=user_id, points=points, reason=action_name)

    def _load_schema_sql(self) -> str:
        if self.schema_path.exists():
            return self.schema_path.read_text(encoding="utf-8")

        logger.warning("Khong tim thay schema.sql tai %s. Su dung schema du phong.", self.schema_path)
        return """
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            email TEXT NOT NULL,
            avatar_path TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            last_login_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS eco_wallet (
            user_id TEXT PRIMARY KEY,
            total_eco_points INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reward_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            points INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS crowd_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone TEXT NOT NULL,
            level INTEGER NOT NULL,
            recommendation TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """

    @staticmethod
    def _now_sql() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
