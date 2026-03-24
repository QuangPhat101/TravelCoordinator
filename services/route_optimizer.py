from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import pandas as pd

from config import settings
from services.crowd_forecast_service import CrowdForecastService
from services.data_loader import DataLoader
from services.hidden_gem_service import HiddenGemService
from services.simulation_service import SimulationService


class RouteOptimizer:
    STRATEGY_WEIGHTS = {
        "ít đông nhất": {"time": 0.20, "crowd": 0.45, "carbon": 0.15, "detour": 0.10, "preference": 0.10},
        "xanh nhất": {"time": 0.15, "crowd": 0.15, "carbon": 0.45, "detour": 0.10, "preference": 0.15},
        "nhanh nhất": {"time": 0.50, "crowd": 0.15, "carbon": 0.10, "detour": 0.15, "preference": 0.10},
        "cân bằng": {"time": 0.25, "crowd": 0.25, "carbon": 0.20, "detour": 0.15, "preference": 0.15},
    }

    TRANSPORT_PRIORITY = ["đi bộ", "xe đạp", "xe bus", "taxi"]

    def __init__(
        self,
        data_loader: DataLoader,
        crowd_forecast_service: CrowdForecastService,
        hidden_gem_service: HiddenGemService | None = None,
        simulation_service: SimulationService | None = None,
    ) -> None:
        self.data_loader = data_loader
        self.crowd_forecast_service = crowd_forecast_service
        self.hidden_gem_service = hidden_gem_service
        self.simulation_service = simulation_service

    def get_attraction_options(self) -> list[tuple[str, str]]:
        attractions = self._scoped_attractions()
        if attractions.empty:
            return []
        return [
            (str(row.attraction_id), str(row.name))
            for row in attractions.sort_values(by="name", ascending=True).itertuples(index=False)
        ]

    def optimize_route(
        self,
        origin_id_or_area: str,
        destination_id: str,
        preference: str,
        transport_mode: str,
        strategy: str,
    ) -> dict[str, Any]:
        attractions = self._scoped_attractions()
        transport_options = self.data_loader.load_transport_options()
        self.crowd_forecast_service.refresh_reference_data()

        if attractions.empty:
            return self._empty_result("Chưa có dữ liệu attractions để tối ưu tuyến trong city scope hiện tại.")

        origin = self._resolve_origin(attractions, origin_id_or_area)
        destination = self._resolve_destination(attractions, destination_id)
        if origin is None or destination is None:
            return self._empty_result("Không xác định được điểm xuất phát hoặc điểm đến trong phạm vi mô phỏng hiện tại.")

        if str(origin["attraction_id"]) == str(destination["attraction_id"]):
            return self._empty_result("Điểm xuất phát và điểm đến đang trùng nhau.")

        candidates = self._build_candidates(
            transport_options=transport_options,
            origin=origin,
            destination=destination,
            transport_mode=transport_mode,
            preference=preference,
        )
        if not candidates:
            return self._empty_result("Không tìm được tuyến phù hợp với dữ liệu transport hiện có.")

        normalized = self._normalize_candidate_metrics(candidates)
        weights = self.STRATEGY_WEIGHTS.get(strategy, self.STRATEGY_WEIGHTS["cân bằng"])

        for candidate in normalized:
            optimization_value = (
                weights["time"] * candidate["normalized_travel_time"]
                + weights["crowd"] * candidate["normalized_crowd"]
                + weights["carbon"] * candidate["normalized_carbon"]
                + weights["detour"] * candidate["normalized_detour_penalty"]
                - weights["preference"] * candidate["normalized_preference_match_score"]
            )
            candidate["optimization_value"] = optimization_value
            candidate["route_score"] = round(max(0.0, 100.0 - optimization_value * 100.0), 1)
            candidate["eco_score"] = self._calculate_eco_score(candidate)
            candidate["suggested_departure_time"] = self._suggest_departure_time(destination, strategy)
            candidate["explanation"] = self._build_explanation(candidate, strategy)

        ranked = sorted(
            normalized,
            key=lambda item: (-item["route_score"], item["travel_time"], item["estimated_carbon_g"]),
        )
        best_route = ranked[0]
        alternatives = ranked[1:4]

        hidden_gem_suggestion = None
        if self.hidden_gem_service is not None and best_route["crowd_score_destination"] >= 55:
            hidden_gems = self.hidden_gem_service.get_hidden_gems_for(
                attraction_id=str(destination["attraction_id"]),
                preference=preference,
                top_k=1,
            )
            hidden_gem_suggestion = hidden_gems[0] if hidden_gems else None

        return {
            "origin": {"id": str(origin["attraction_id"]), "name": str(origin["name"]), "area": str(origin["area"])},
            "destination": {
                "id": str(destination["attraction_id"]),
                "name": str(destination["name"]),
                "area": str(destination["area"]),
                "category": str(destination["category"]),
            },
            "preference": preference,
            "transport_mode": transport_mode,
            "strategy": strategy,
            "best_route": best_route,
            "alternative_routes": alternatives,
            "travel_time": int(best_route["travel_time"]),
            "distance_km": float(best_route["distance_km"]),
            "estimated_carbon_g": int(best_route["estimated_carbon_g"]),
            "eco_score": int(best_route["eco_score"]),
            "suggested_departure_time": best_route["suggested_departure_time"],
            "crowd_score_destination": int(best_route["crowd_score_destination"]),
            "explanation": best_route["explanation"],
            "hidden_gem_suggestion": hidden_gem_suggestion,
            "hidden_gem_bonus_eligible": bool(hidden_gem_suggestion)
            or (int(destination["popularity_score"]) <= 60 and int(best_route["crowd_score_destination"]) <= 50),
            "low_peak_bonus_eligible": int(best_route["crowd_score_destination"]) <= 40,
            "destination_popularity_score": int(destination["popularity_score"]),
            "city_scope": self._current_city_scope(),
        }

    def _scoped_attractions(self) -> pd.DataFrame:
        attractions = self.data_loader.load_attractions().copy()
        if attractions.empty:
            return attractions

        city_scope = self._current_city_scope()
        if not city_scope or city_scope == settings.ALL_CITY_SCOPE_LABEL:
            return attractions

        city_series = self._resolve_city_series(attractions)
        filtered = attractions.loc[city_series.astype(str).str.casefold() == city_scope.casefold()].copy()
        return filtered if not filtered.empty else attractions

    @staticmethod
    def _resolve_city_series(attractions: pd.DataFrame) -> pd.Series:
        for column_name in ("city", "province", "destination_city"):
            if column_name in attractions.columns:
                return attractions[column_name].fillna(settings.DEFAULT_CITY_SCOPE).astype(str)
        return pd.Series([settings.DEFAULT_CITY_SCOPE] * len(attractions.index), index=attractions.index, dtype="object")

    def _current_city_scope(self) -> str:
        if self.simulation_service is not None:
            return self.simulation_service.city_scope
        return settings.ALL_CITY_SCOPE_LABEL

    def _build_candidates(
        self,
        transport_options: pd.DataFrame,
        origin: pd.Series,
        destination: pd.Series,
        transport_mode: str,
        preference: str,
    ) -> list[dict[str, Any]]:
        modes = self.TRANSPORT_PRIORITY if transport_mode == "tự động" else [transport_mode]
        candidates: list[dict[str, Any]] = []

        for mode in modes:
            direct = transport_options.loc[
                (transport_options["origin_id"] == origin["attraction_id"])
                & (transport_options["destination_id"] == destination["attraction_id"])
                & (transport_options["transport_mode"] == mode)
            ]
            if direct.empty:
                direct = transport_options.loc[
                    (transport_options["origin_id"] == destination["attraction_id"])
                    & (transport_options["destination_id"] == origin["attraction_id"])
                    & (transport_options["transport_mode"] == mode)
                ]

            if not direct.empty:
                row = direct.sort_values(by=["duration_min", "estimated_carbon_g"], ascending=[True, True]).iloc[0]
                candidate = self._candidate_from_transport_row(row, origin, destination, preference, fallback=False)
            else:
                candidate = self._fallback_candidate(origin, destination, mode, preference)
            candidates.append(candidate)

        return candidates

    def _candidate_from_transport_row(
        self,
        row: pd.Series,
        origin: pd.Series,
        destination: pd.Series,
        preference: str,
        fallback: bool,
    ) -> dict[str, Any]:
        destination_crowd = self.crowd_forecast_service.get_current_crowd_score(destination)
        origin_crowd = self.crowd_forecast_service.get_current_crowd_score(origin)
        preference_match = self._preference_match_score(destination, preference)
        return {
            "route_name": f"{origin['name']} -> {destination['name']} bằng {row['transport_mode']}",
            "origin_name": str(origin["name"]),
            "destination_name": str(destination["name"]),
            "transport_mode": str(row["transport_mode"]),
            "travel_time": int(row["duration_min"]),
            "distance_km": float(row["distance_km"]),
            "estimated_carbon_g": int(row["estimated_carbon_g"]),
            "crowd_score_destination": int(destination_crowd),
            "average_crowd": int(round((destination_crowd + origin_crowd) / 2)),
            "detour_penalty": 0.18 if fallback else 0.02,
            "preference_match_score": preference_match,
            "is_fallback_route": fallback,
        }

    def _fallback_candidate(
        self,
        origin: pd.Series,
        destination: pd.Series,
        transport_mode: str,
        preference: str,
    ) -> dict[str, Any]:
        distance = self._estimate_distance_km(origin, destination)
        if transport_mode == "đi bộ":
            duration = max(12, int(distance / 4.8 * 60))
            carbon = 0
        elif transport_mode == "xe đạp":
            duration = max(8, int(distance / 12.0 * 60))
            carbon = 0
        elif transport_mode == "xe bus":
            duration = max(12, int(distance / 18.0 * 60) + 8)
            carbon = int(distance * 28)
        else:
            duration = max(8, int(distance / 24.0 * 60) + 6)
            carbon = int(distance * 170)

        fallback_row = pd.Series(
            {
                "transport_mode": transport_mode,
                "distance_km": round(distance, 2),
                "duration_min": duration,
                "estimated_carbon_g": carbon,
            }
        )
        return self._candidate_from_transport_row(fallback_row, origin, destination, preference, fallback=True)

    def _normalize_candidate_metrics(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        time_values = [candidate["travel_time"] for candidate in candidates]
        crowd_values = [candidate["average_crowd"] for candidate in candidates]
        carbon_values = [candidate["estimated_carbon_g"] for candidate in candidates]
        detour_values = [candidate["detour_penalty"] for candidate in candidates]
        preference_values = [candidate["preference_match_score"] for candidate in candidates]

        for candidate in candidates:
            candidate["normalized_travel_time"] = self._normalize(candidate["travel_time"], time_values)
            candidate["normalized_crowd"] = self._normalize(candidate["average_crowd"], crowd_values)
            candidate["normalized_carbon"] = self._normalize(candidate["estimated_carbon_g"], carbon_values)
            candidate["normalized_detour_penalty"] = self._normalize(candidate["detour_penalty"], detour_values)
            candidate["normalized_preference_match_score"] = self._normalize(
                candidate["preference_match_score"],
                preference_values,
            )
        return candidates

    @staticmethod
    def _calculate_eco_score(candidate: dict[str, Any]) -> int:
        carbon_penalty = min(45.0, candidate["estimated_carbon_g"] / 15.0)
        crowd_penalty = candidate["crowd_score_destination"] * 0.18
        preference_bonus = candidate["preference_match_score"] * 18.0
        green_mode_bonus = {
            "đi bộ": 26,
            "xe đạp": 22,
            "xe bus": 16,
            "taxi": 4,
        }.get(candidate["transport_mode"], 6)
        score = 58 + green_mode_bonus + preference_bonus - carbon_penalty - crowd_penalty
        return max(0, min(100, int(round(score))))

    def _suggest_departure_time(self, destination: pd.Series, strategy: str) -> str:
        best_visit = self.crowd_forecast_service.get_best_visit_time(destination)
        current_time = self.crowd_forecast_service.simulation_service.simulated_datetime

        if strategy == "ít đông nhất" or best_visit["crowd_score"] + 8 < self.crowd_forecast_service.get_current_crowd_score(destination):
            return best_visit["datetime"].strftime("%d/%m %H:%M")
        return current_time.strftime("%d/%m %H:%M")

    @staticmethod
    def _build_explanation(candidate: dict[str, Any], strategy: str) -> str:
        return (
            f"Tuyến này phù hợp chiến lược {strategy} vì đi bằng {candidate['transport_mode']}, "
            f"thời gian khoảng {candidate['travel_time']} phút, crowd tại điểm đến {candidate['crowd_score_destination']}, "
            f"phát thải ước tính {candidate['estimated_carbon_g']} g CO2 và mức khớp sở thích {candidate['preference_match_score']:.2f}."
        )

    def _resolve_origin(self, attractions: pd.DataFrame, origin_id_or_area: str) -> pd.Series | None:
        exact = attractions.loc[attractions["attraction_id"] == origin_id_or_area]
        if not exact.empty:
            return exact.iloc[0]

        exact_name = attractions.loc[attractions["name"].str.casefold() == origin_id_or_area.casefold()]
        if not exact_name.empty:
            return exact_name.iloc[0]

        same_area = attractions.loc[attractions["area"].str.casefold() == origin_id_or_area.casefold()].copy()
        if same_area.empty:
            return None

        same_area["current_crowd_score"] = same_area.apply(self.crowd_forecast_service.get_current_crowd_score, axis=1)
        same_area = same_area.sort_values(by=["current_crowd_score", "avg_rating"], ascending=[True, False])
        return same_area.iloc[0]

    @staticmethod
    def _resolve_destination(attractions: pd.DataFrame, destination_id: str) -> pd.Series | None:
        exact = attractions.loc[attractions["attraction_id"] == destination_id]
        if not exact.empty:
            return exact.iloc[0]

        exact_name = attractions.loc[attractions["name"].str.casefold() == destination_id.casefold()]
        if not exact_name.empty:
            return exact_name.iloc[0]
        return None

    @staticmethod
    def _preference_match_score(destination: pd.Series, preference: str) -> float:
        normalized_preference = preference.casefold()
        destination_category = str(destination["category"]).casefold()
        tags = str(destination["tags"]).casefold()

        if normalized_preference in {"văn hóa", "thiên nhiên", "ẩm thực", "check-in"}:
            return 1.0 if destination_category == normalized_preference else 0.2
        if normalized_preference == "lịch sử":
            return 1.0 if destination_category in {"văn hóa", "bảo tàng"} or "lịch sử" in tags else 0.25
        if normalized_preference == "thư giãn":
            return 1.0 if any(tag in tags for tag in ["biển", "công viên", "ven sông"]) else 0.35
        return 0.3

    @staticmethod
    def _normalize(value: float, all_values: list[float]) -> float:
        min_value = min(all_values)
        max_value = max(all_values)
        if math.isclose(min_value, max_value):
            return 0.0
        return (value - min_value) / (max_value - min_value)

    @staticmethod
    def _estimate_distance_km(origin: pd.Series, destination: pd.Series) -> float:
        lat1 = float(origin["latitude"])
        lon1 = float(origin["longitude"])
        lat2 = float(destination["latitude"])
        lon2 = float(destination["longitude"])

        radius = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius * c

    @staticmethod
    def _empty_result(message: str) -> dict[str, Any]:
        now = datetime.now().strftime("%d/%m %H:%M")
        return {
            "origin": {},
            "destination": {},
            "preference": "",
            "transport_mode": "",
            "strategy": "",
            "best_route": None,
            "alternative_routes": [],
            "travel_time": 0,
            "distance_km": 0.0,
            "estimated_carbon_g": 0,
            "eco_score": 0,
            "suggested_departure_time": now,
            "crowd_score_destination": 0,
            "explanation": message,
            "hidden_gem_suggestion": None,
            "hidden_gem_bonus_eligible": False,
            "low_peak_bonus_eligible": False,
            "destination_popularity_score": 0,
            "city_scope": settings.ALL_CITY_SCOPE_LABEL,
        }
