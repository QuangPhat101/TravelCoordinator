from __future__ import annotations

from typing import Any

from config import settings
from database.db_service import DBService
from services.sample_data_service import SampleDataService


class EcoRewardService:
    def __init__(
        self,
        database_manager: DBService,
        sample_data_service: SampleDataService,
    ) -> None:
        self.database_manager = database_manager
        self.sample_data_service = sample_data_service

    def get_points(self, user_id: str = settings.DEFAULT_USER_ID) -> int:
        return self.database_manager.get_reward_points(user_id=user_id)

    def calculate_reward(self, route_result: dict[str, Any]) -> dict[str, Any]:
        best_route = route_result.get("best_route") or {}
        transport_mode = str(best_route.get("transport_mode", ""))
        distance_km = float(best_route.get("distance_km", route_result.get("distance_km", 0.0)) or 0.0)
        eco_score = int(best_route.get("eco_score", route_result.get("eco_score", 0)) or 0)

        mode_points = 0
        if transport_mode == "đi bộ":
            mode_points = max(4, int(round(distance_km * 4)))
        elif transport_mode == "xe đạp":
            mode_points = max(3, int(round(distance_km * 3)))
        elif transport_mode == "xe bus":
            mode_points = max(5, 6 + int(round(distance_km * 0.5)))
        elif transport_mode == "taxi":
            mode_points = max(0, int(round(distance_km * 0.2)))

        hidden_gem_bonus = 5 if route_result.get("hidden_gem_bonus_eligible") else 0
        low_peak_bonus = 4 if route_result.get("low_peak_bonus_eligible") else 0
        eco_score_bonus = 5 if eco_score >= 70 else 2 if eco_score >= 50 else 0

        total_reward = mode_points + hidden_gem_bonus + low_peak_bonus + eco_score_bonus
        return {
            "transport_mode": transport_mode,
            "distance_km": round(distance_km, 1),
            "mode_points": mode_points,
            "hidden_gem_bonus": hidden_gem_bonus,
            "low_peak_bonus": low_peak_bonus,
            "eco_score_bonus": eco_score_bonus,
            "total_reward_points": total_reward,
            "eco_score": eco_score,
        }

    def grant_reward(
        self,
        user_id: str,
        route_result: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        reward_breakdown = self.calculate_reward(route_result)
        safe_user_id = user_id or settings.DEFAULT_USER_ID
        reward_reason = reason.strip() or "Planner Eco Reward"
        total_points = self.database_manager.add_eco_points(
            user_id=safe_user_id,
            points=reward_breakdown["total_reward_points"],
            reason=reward_reason,
        )
        reward_breakdown["wallet_total"] = total_points
        reward_breakdown["reason"] = reward_reason
        return reward_breakdown

    def get_wallet_summary(self, user_id: str = settings.DEFAULT_USER_ID) -> dict[str, Any]:
        total_points = self.database_manager.get_total_eco_points(user_id)
        recent_actions = self.recent_actions(limit=8, user_id=user_id)
        return {
            "user_id": user_id,
            "total_points": total_points,
            "recent_actions": recent_actions,
        }

    def register_green_action(
        self,
        action_name: str,
        points: int | None = None,
        user_id: str = settings.DEFAULT_USER_ID,
    ) -> int:
        resolved_points = int(points) if points is not None else self.point_for_action(action_name)
        return self.database_manager.add_reward_points(
            user_id=user_id,
            action_name=action_name,
            points=resolved_points,
        )

    def recent_actions(
        self,
        limit: int = 10,
        user_id: str = settings.DEFAULT_USER_ID,
    ) -> list[dict[str, str | int]]:
        rows = self.database_manager.get_recent_reward_actions(user_id=user_id, limit=limit)
        return [
            {
                "created_at": row["created_at"],
                "action_name": row["action_name"],
                "points": row["points"],
            }
            for row in rows
        ]

    def available_actions(self) -> list[str]:
        rules = self.sample_data_service.load_eco_rewards()
        if rules.empty:
            return [
                "Đi xe bus",
                "Mang bình nước cá nhân",
                "Check-in không dùng nhựa một lần",
            ]
        return rules["action_type"].dropna().astype(str).tolist()

    def point_for_action(self, action_name: str) -> int:
        rules = self.sample_data_service.load_eco_rewards()
        if rules.empty:
            return 5

        matched = rules.loc[rules["action_type"].str.casefold() == action_name.casefold()]
        if matched.empty:
            return 5
        return int(matched.iloc[0]["point_value"])
