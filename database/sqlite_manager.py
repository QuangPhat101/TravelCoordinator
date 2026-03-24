import sqlite3
from pathlib import Path

from config import settings


class DatabaseManager:
    def __init__(self, db_path: Path | str = settings.DATABASE_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS reward_wallet (
            user_id TEXT PRIMARY KEY,
            points INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS reward_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            action_name TEXT NOT NULL,
            points INTEGER NOT NULL,
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
        with self.connect() as connection:
            connection.executescript(schema)
            connection.execute(
                """
                INSERT INTO reward_wallet(user_id, points)
                VALUES(?, 0)
                ON CONFLICT(user_id) DO NOTHING
                """,
                (settings.DEFAULT_USER_ID,),
            )
            connection.commit()

    def get_reward_points(self, user_id: str) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT points FROM reward_wallet WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return int(row["points"]) if row else 0

    def add_reward_points(self, user_id: str, action_name: str, points: int) -> int:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO reward_wallet(user_id, points)
                VALUES(?, ?)
                ON CONFLICT(user_id) DO UPDATE SET points = points + excluded.points
                """,
                (user_id, points),
            )
            connection.execute(
                """
                INSERT INTO reward_actions(user_id, action_name, points, created_at)
                VALUES(?, ?, ?, datetime('now', 'localtime'))
                """,
                (user_id, action_name, points),
            )
            row = connection.execute(
                "SELECT points FROM reward_wallet WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            connection.commit()
            return int(row["points"]) if row else 0

    def get_recent_reward_actions(self, user_id: str, limit: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT action_name, points, created_at
                FROM reward_actions
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return list(rows)

    def save_crowd_snapshot(
        self,
        zone: str,
        level: int,
        recommendation: str,
        created_at: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO crowd_snapshots(zone, level, recommendation, created_at)
                VALUES(?, ?, ?, ?)
                """,
                (zone, level, recommendation, created_at),
            )
            connection.commit()

    def get_recent_crowd_snapshots(self, limit: int) -> list[sqlite3.Row]:
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
