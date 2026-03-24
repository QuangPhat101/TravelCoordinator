from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from services.data_loader import DataLoader
from services.simulation_service import SimulationService


class CrowdForecastService:
    def __init__(self, data_loader: DataLoader, simulation_service: SimulationService) -> None:
        self.data_loader = data_loader
        self.simulation_service = simulation_service
        self._crowd_history_cache = pd.DataFrame()

    def refresh_reference_data(self) -> None:
        self._crowd_history_cache = self.data_loader.load_crowd_history()

    def get_current_crowd_score(self, attraction: Any) -> int:
        attraction_data = self._normalize_attraction(attraction)
        state = self.simulation_service.get_state()
        score, _ = self._simulate_score(attraction_data, state.simulated_datetime)
        return score

    def forecast_next_hours(self, attraction: Any, hours: int = 4) -> list[dict[str, Any]]:
        attraction_data = self._normalize_attraction(attraction)
        start_time = self.simulation_service.simulated_datetime
        forecasts: list[dict[str, Any]] = []

        for offset in range(max(1, int(hours))):
            forecast_time = start_time + timedelta(hours=offset)
            score, _ = self._simulate_score(attraction_data, forecast_time)
            forecasts.append(
                {
                    "datetime": forecast_time,
                    "crowd_score": score,
                    "level": self._classify(score),
                }
            )
        return forecasts

    def get_best_visit_time(self, attraction: Any) -> dict[str, Any]:
        candidates = self.forecast_next_hours(attraction, hours=8)
        if not candidates:
            return {
                "datetime": self.simulation_service.simulated_datetime,
                "crowd_score": 0,
                "level": "low",
            }
        return min(candidates, key=lambda item: (item["crowd_score"], item["datetime"]))

    def explain_crowd_score(self, attraction: Any) -> str:
        attraction_data = self._normalize_attraction(attraction)
        _, factors = self._simulate_score(attraction_data, self.simulation_service.simulated_datetime)

        reasons = [
            f"Độ phổ biến nền {factors['popularity_component']} điểm",
            f"sức chứa đóng góp {factors['capacity_component']} điểm",
            f"khung giờ {factors['hour_component']} điểm",
            f"thời tiết {factors['weather_component']} điểm",
            f"event {factors['event_component']} điểm",
            f"holiday {factors['holiday_component']} điểm",
            f"noise ổn định {factors['noise_component']} điểm",
        ]
        return " | ".join(reasons)

    def _simulate_score(self, attraction_data: dict[str, Any], target_datetime: datetime) -> tuple[int, dict[str, int]]:
        history = self._get_crowd_history()
        popularity_score = int(float(attraction_data.get("popularity_score", 0) or 0))
        estimated_capacity = int(float(attraction_data.get("estimated_capacity", 0) or 0))
        indoor_outdoor = str(attraction_data.get("indoor_outdoor", "")).casefold()
        category = str(attraction_data.get("category", "")).casefold()

        historical_reference = self._historical_reference(attraction_data, target_datetime, history)
        popularity_component = round(popularity_score * 0.34)
        capacity_component = min(18, round(estimated_capacity / 320))
        hour_component = self._hour_component(category, target_datetime.hour)
        day_component = 8 if target_datetime.weekday() >= 5 else 0
        weather_component = self._weather_component(self.simulation_service.weather, indoor_outdoor, category)
        event_component = self._event_component(category) if self.simulation_service.event_flag else 0
        holiday_component = 7 if self.simulation_service.holiday_flag else 0
        noise_component = self._stable_noise(
            attraction_id=str(attraction_data.get("attraction_id", "")),
            target_datetime=target_datetime,
        )

        if historical_reference is not None:
            base_score = round(historical_reference * 0.58 + (popularity_component + capacity_component) * 0.42)
        else:
            base_score = popularity_component + capacity_component

        raw_score = (
            base_score
            + hour_component
            + day_component
            + weather_component
            + event_component
            + holiday_component
            + noise_component
        )
        normalized_score = int(round(raw_score * self.simulation_service.global_crowd_multiplier))
        normalized_score = max(0, min(100, normalized_score))

        factor_map = {
            "popularity_component": popularity_component,
            "capacity_component": capacity_component,
            "hour_component": hour_component + day_component,
            "weather_component": weather_component,
            "event_component": event_component,
            "holiday_component": holiday_component,
            "noise_component": noise_component,
        }
        return normalized_score, factor_map

    def _historical_reference(
        self,
        attraction_data: dict[str, Any],
        target_datetime: datetime,
        history: pd.DataFrame,
    ) -> float | None:
        if history.empty:
            return None

        attraction_id = str(attraction_data.get("attraction_id", ""))
        if not attraction_id:
            return None

        working = history.loc[history["attraction_id"] == attraction_id].copy()
        if working.empty:
            return None

        weekday_name = target_datetime.strftime("%A")
        same_hour_same_day = working.loc[
            (working["hour"] == target_datetime.hour) & (working["day_of_week"] == weekday_name)
        ]
        if not same_hour_same_day.empty:
            return float(same_hour_same_day["crowd_score"].mean())

        same_hour = working.loc[working["hour"] == target_datetime.hour]
        if not same_hour.empty:
            return float(same_hour["crowd_score"].mean())

        return float(working["crowd_score"].mean())

    @staticmethod
    def _hour_component(category: str, hour: int) -> int:
        if category == "ẩm thực" and hour in {11, 12, 18, 19, 20}:
            return 14
        if category == "check-in" and hour in {17, 18, 19, 20}:
            return 12
        if category == "thiên nhiên" and hour in {6, 7, 8, 15, 16, 17}:
            return 13
        if category == "bảo tàng" and hour in {9, 10, 14, 15}:
            return 9
        if category == "văn hóa" and hour in {8, 9, 16, 17}:
            return 8
        if category == "làng nghề" and hour in {9, 10, 14, 15}:
            return 6
        return 2 if 18 <= hour <= 20 else 0

    @staticmethod
    def _weather_component(weather: str, indoor_outdoor: str, category: str) -> int:
        normalized_weather = weather.casefold()
        if "mưa" in normalized_weather:
            return 6 if indoor_outdoor == "indoor" else -12
        if "nhiều mây" in normalized_weather:
            return -2 if indoor_outdoor == "outdoor" else 1
        if "nắng" in normalized_weather and indoor_outdoor == "outdoor":
            return 5 if category in {"thiên nhiên", "check-in"} else 2
        return 0

    @staticmethod
    def _event_component(category: str) -> int:
        if category in {"check-in", "ẩm thực", "văn hóa"}:
            return 11
        if category == "thiên nhiên":
            return 6
        return 4

    @staticmethod
    def _stable_noise(attraction_id: str, target_datetime: datetime) -> int:
        seed = f"{attraction_id}|{target_datetime:%Y%m%d%H}|simulation"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        return int(digest[:2], 16) % 9 - 4

    def _get_crowd_history(self) -> pd.DataFrame:
        if self._crowd_history_cache.empty:
            self.refresh_reference_data()
        return self._crowd_history_cache

    @staticmethod
    def _classify(score: int) -> str:
        if score <= 25:
            return "low"
        if score <= 50:
            return "moderate"
        if score <= 75:
            return "high"
        return "overcrowded"

    @staticmethod
    def _normalize_attraction(attraction: Any) -> dict[str, Any]:
        if isinstance(attraction, dict):
            return attraction
        if isinstance(attraction, pd.Series):
            return attraction.to_dict()
        if hasattr(attraction, "_asdict"):
            return attraction._asdict()
        return {
            "attraction_id": getattr(attraction, "attraction_id", ""),
            "name": getattr(attraction, "name", ""),
            "category": getattr(attraction, "category", ""),
            "description": getattr(attraction, "description", ""),
            "area": getattr(attraction, "area", ""),
            "opening_hours": getattr(attraction, "opening_hours", ""),
            "ticket_price": getattr(attraction, "ticket_price", ""),
            "avg_rating": getattr(attraction, "avg_rating", 0.0),
            "estimated_capacity": getattr(attraction, "estimated_capacity", 0),
            "popularity_score": getattr(attraction, "popularity_score", 0),
            "indoor_outdoor": getattr(attraction, "indoor_outdoor", ""),
            "tags": getattr(attraction, "tags", ""),
        }
