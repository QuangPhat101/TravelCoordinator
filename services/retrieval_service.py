from __future__ import annotations

from dataclasses import asdict
import math
import re
from typing import Any

import pandas as pd

from config import settings
from models.faq_item import FaqItem
from services.crowd_forecast_service import CrowdForecastService
from services.data_loader import DataLoader
from services.eco_reward_service import EcoRewardService
from services.hidden_gem_service import HiddenGemService
from services.simulation_service import SimulationService


class RetrievalService:
    def __init__(
        self,
        data_loader: DataLoader,
        crowd_forecast_service: CrowdForecastService | None = None,
        hidden_gem_service: HiddenGemService | None = None,
        eco_reward_service: EcoRewardService | None = None,
        simulation_service: SimulationService | None = None,
    ) -> None:
        self.data_loader = data_loader
        self.crowd_forecast_service = crowd_forecast_service
        self.hidden_gem_service = hidden_gem_service
        self.eco_reward_service = eco_reward_service
        self.simulation_service = simulation_service

    def search_faq(self, query: str, intent: str | None = None) -> FaqItem | None:
        faq_items = self.data_loader.load_faq_items()
        if not faq_items:
            return None

        normalized_query = query.casefold()
        query_tokens = self._tokens(query)
        best_item: FaqItem | None = None
        best_score = 0

        for item in faq_items:
            score = 0
            question_text = item.question.casefold()

            if question_text in normalized_query or normalized_query in question_text:
                score += 8
            if intent and item.intent.casefold() == intent.casefold():
                score += 4

            score += len(query_tokens & self._tokens(item.question)) * 2
            score += len(query_tokens & self._tokens(item.tags))

            if score > best_score:
                best_score = score
                best_item = item

        return best_item if best_score >= 3 else None

    def find_attraction(self, query: str) -> dict[str, Any] | None:
        attractions = self._scoped_attractions()
        if attractions.empty:
            return None

        normalized_query = query.casefold()
        query_tokens = self._tokens(query)
        best_match: dict[str, Any] | None = None
        best_score = 0

        for row in attractions.itertuples(index=False):
            data = row._asdict()
            name_text = str(data["name"]).casefold()
            searchable = " ".join(
                [
                    str(data["name"]),
                    str(data["category"]),
                    str(data["area"]),
                    str(data["tags"]),
                ]
            )

            if name_text and name_text in normalized_query:
                return data

            score = len(query_tokens & self._tokens(searchable))
            if str(data["category"]).casefold() in normalized_query:
                score += 1
            if str(data["area"]).casefold() in normalized_query:
                score += 1

            if score > best_score:
                best_score = score
                best_match = data

        return best_match if best_score >= 2 else None

    def get_attraction_by_id(self, attraction_id: str) -> dict[str, Any] | None:
        attraction = self.data_loader.get_attraction_by_id(attraction_id)
        if attraction is None:
            return None
        attraction_data = asdict(attraction)
        if not self._is_in_current_scope(attraction_data):
            return None
        return attraction_data

    def get_current_crowd_score(self, attraction: dict[str, Any]) -> int:
        if self.crowd_forecast_service is not None:
            return self.crowd_forecast_service.get_current_crowd_score(attraction)
        return int(float(attraction.get("popularity_score", 0) or 0))

    def get_best_visit_time(self, attraction: dict[str, Any]) -> dict[str, Any]:
        if self.crowd_forecast_service is None:
            current_score = self.get_current_crowd_score(attraction)
            return {
                "datetime": None,
                "crowd_score": current_score,
                "level": self.classify_crowd(current_score),
            }
        return self.crowd_forecast_service.get_best_visit_time(attraction)

    def explain_crowd_score(self, attraction: dict[str, Any]) -> str:
        if self.crowd_forecast_service is None:
            return "Hệ thống đang dùng popularity score làm tham chiếu crowd vì chưa có engine mô phỏng."
        return self.crowd_forecast_service.explain_crowd_score(attraction)

    def get_crowded_places(self, limit: int = 3) -> list[dict[str, Any]]:
        attractions = self._scoped_attractions()
        if attractions.empty:
            return []

        rows: list[dict[str, Any]] = []
        for row in attractions.itertuples(index=False):
            data = row._asdict()
            crowd_score = self.get_current_crowd_score(data)
            data["crowd_score"] = crowd_score
            data["crowd_level"] = self.level_vi(crowd_score)
            rows.append(data)

        ranked = sorted(rows, key=lambda item: (-item["crowd_score"], -float(item.get("avg_rating", 0.0))))
        filtered = [item for item in ranked if item["crowd_score"] >= 51]
        return (filtered or ranked)[: max(1, int(limit))]

    def get_low_crowd_places(self, limit: int = 3, area: str | None = None) -> list[dict[str, Any]]:
        attractions = self._scoped_attractions()
        if attractions.empty:
            return []

        working = attractions.copy()
        if area:
            matched_area = working["area"].astype(str).str.casefold() == area.casefold()
            if matched_area.any():
                working = working.loc[matched_area].copy()

        rows: list[dict[str, Any]] = []
        for row in working.itertuples(index=False):
            data = row._asdict()
            crowd_score = self.get_current_crowd_score(data)
            data["crowd_score"] = crowd_score
            data["crowd_level"] = self.level_vi(crowd_score)
            rows.append(data)

        ranked = sorted(rows, key=lambda item: (item["crowd_score"], -float(item.get("avg_rating", 0.0))))
        return ranked[: max(1, int(limit))]

    def get_hidden_gems(
        self,
        source_attraction: dict[str, Any],
        preference: str | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        source_id = str(source_attraction.get("attraction_id", "")).strip()
        if not source_id:
            return []

        if self.hidden_gem_service is not None:
            results = self.hidden_gem_service.get_hidden_gems_for(
                attraction_id=source_id,
                preference=preference,
                top_k=top_k,
            )
            if results:
                return results

        fallback = self.get_low_crowd_places(limit=top_k * 2, area=str(source_attraction.get("area", "")))
        filtered: list[dict[str, Any]] = []
        source_score = self.get_current_crowd_score(source_attraction)
        for item in fallback:
            if str(item.get("attraction_id")) == source_id:
                continue
            if item["crowd_score"] >= source_score:
                continue
            filtered.append(
                {
                    "attraction_id": str(item["attraction_id"]),
                    "name": str(item["name"]),
                    "category": str(item["category"]),
                    "distance_km": self.estimate_distance_km(source_attraction, item),
                    "crowd_score": int(item["crowd_score"]),
                    "rating": float(item.get("avg_rating", 0.0)),
                    "reason": (
                        f"Gợi ý vì cùng khu vực {item.get('area', 'gần đó')}, crowd thấp hơn "
                        f"và rating {float(item.get('avg_rating', 0.0)):.1f}."
                    ),
                }
            )
            if len(filtered) >= top_k:
                break
        return filtered

    def get_reward_rules(self) -> list[dict[str, Any]]:
        rewards = self.data_loader.load_eco_rewards()
        if rewards.empty:
            return []
        return rewards.to_dict(orient="records")

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

    def _is_in_current_scope(self, attraction: dict[str, Any]) -> bool:
        city_scope = self._current_city_scope()
        if not city_scope or city_scope == settings.ALL_CITY_SCOPE_LABEL:
            return True
        attraction_city = str(
            attraction.get("city")
            or attraction.get("province")
            or attraction.get("destination_city")
            or settings.DEFAULT_CITY_SCOPE
        )
        return attraction_city.casefold() == city_scope.casefold()

    @staticmethod
    def classify_crowd(score: int) -> str:
        if score <= 25:
            return "low"
        if score <= 50:
            return "moderate"
        if score <= 75:
            return "high"
        return "overcrowded"

    @staticmethod
    def level_vi(score: int) -> str:
        if score <= 25:
            return "thấp"
        if score <= 50:
            return "vừa"
        if score <= 75:
            return "cao"
        return "quá tải"

    @staticmethod
    def estimate_distance_km(source: dict[str, Any], candidate: dict[str, Any]) -> float:
        lat1 = float(source.get("latitude", 0.0) or 0.0)
        lon1 = float(source.get("longitude", 0.0) or 0.0)
        lat2 = float(candidate.get("latitude", 0.0) or 0.0)
        lon2 = float(candidate.get("longitude", 0.0) or 0.0)

        if not any([lat1, lon1, lat2, lon2]):
            return 0.0

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
        return round(radius * c, 1)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token for token in re.findall(r"\w+", text.casefold(), flags=re.UNICODE) if len(token) >= 2}
