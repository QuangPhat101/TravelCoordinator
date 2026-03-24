from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd

from config import settings
from models.destination import Destination
from services.crowd_forecast_service import CrowdForecastService
from services.data_loader import DataLoader
from services.simulation_service import SimulationService


class HiddenGemService:
    def __init__(
        self,
        data_loader: DataLoader,
        crowd_forecast_service: CrowdForecastService | None = None,
        simulation_service: SimulationService | None = None,
    ) -> None:
        self.data_loader = data_loader
        self.crowd_forecast_service = crowd_forecast_service
        self.simulation_service = simulation_service

    def list_hidden_gems(self) -> list[Destination]:
        attractions = self._scoped_attractions()
        if attractions.empty:
            return self._fallback_or_json_gems()

        ranked_gems = attractions.copy()
        ranked_gems["current_crowd_score"] = ranked_gems.apply(self._current_crowd_score, axis=1)
        ranked_gems = ranked_gems.loc[
            (ranked_gems["avg_rating"] >= 4.4)
            & (ranked_gems["current_crowd_score"] <= 45)
            & (ranked_gems["popularity_score"] <= 68)
        ].sort_values(
            by=["current_crowd_score", "popularity_score", "avg_rating"],
            ascending=[True, True, False],
        )

        if ranked_gems.empty:
            return self._fallback_or_json_gems()

        current_city = self._current_city_scope()
        return [
            Destination(
                name=str(item.name),
                province=current_city,
                description=(
                    f"{item.description} Khu vực: {item.area}. "
                    f"Giờ mở cửa: {item.opening_hours}. Giá vé: {item.ticket_price}. "
                    f"Crowd hiện tại: {int(item.current_crowd_score)}."
                ),
                eco_tip=self._build_eco_tip(str(item.indoor_outdoor), str(item.tags)),
            )
            for item in ranked_gems.head(6).itertuples(index=False)
        ]

    def get_hidden_gems_for(
        self,
        attraction_id: str,
        preference: str | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        attractions = self._scoped_attractions()
        if attractions.empty:
            return []

        source_frame = attractions.loc[attractions["attraction_id"] == attraction_id]
        if source_frame.empty:
            return []
        source = source_frame.iloc[0]
        source_score = self._current_crowd_score(source)

        scored = attractions.copy()
        scored["current_crowd_score"] = scored.apply(self._current_crowd_score, axis=1)
        scored = scored.loc[scored["attraction_id"] != attraction_id].copy()
        scored["distance_km"] = scored.apply(lambda row: self._estimate_distance_km(source, row), axis=1)
        scored["tag_similarity"] = scored.apply(
            lambda row: self._tag_similarity(str(source["tags"]), str(row["tags"])),
            axis=1,
        )
        scored["crowd_gap"] = source_score - scored["current_crowd_score"]
        scored["same_category"] = scored["category"] == source["category"]
        scored["rating_ok"] = scored["avg_rating"] >= max(3.8, float(source["avg_rating"]) - 0.5)

        candidates = scored.loc[
            scored["same_category"]
            & scored["rating_ok"]
            & (scored["crowd_gap"] >= 8)
        ].copy()

        if candidates.empty:
            candidates = scored.loc[
                scored["rating_ok"]
                & (scored["tag_similarity"] >= 1)
                & (scored["crowd_gap"] >= 10)
            ].copy()

        if candidates.empty:
            candidates = scored.loc[
                scored["rating_ok"]
                & (scored["crowd_gap"] >= 12)
            ].copy()

        if candidates.empty:
            return []

        candidates["recommendation_score"] = candidates.apply(
            lambda row: self._recommendation_score(source, row, preference),
            axis=1,
        )
        candidates = candidates.sort_values(
            by=["recommendation_score", "current_crowd_score", "distance_km", "avg_rating"],
            ascending=[False, True, True, False],
        )

        results: list[dict[str, Any]] = []
        for row in candidates.head(max(1, int(top_k))).itertuples(index=False):
            candidate = row._asdict()
            results.append(
                {
                    "attraction_id": str(candidate["attraction_id"]),
                    "name": str(candidate["name"]),
                    "category": str(candidate["category"]),
                    "distance_km": round(float(candidate["distance_km"]), 1),
                    "crowd_score": int(candidate["current_crowd_score"]),
                    "rating": float(candidate["avg_rating"]),
                    "reason": self.explain_hidden_gem_recommendation(source.to_dict(), candidate),
                }
            )
        return results

    def explain_hidden_gem_recommendation(self, source: Any, candidate: Any) -> str:
        source_data = self._normalize_row(source)
        candidate_data = self._normalize_row(candidate)

        reasons: list[str] = []
        if source_data.get("category") == candidate_data.get("category"):
            reasons.append(f"cùng loại hình {candidate_data['category']}")

        overlap_count = self._tag_similarity(
            str(source_data.get("tags", "")),
            str(candidate_data.get("tags", "")),
        )
        if overlap_count > 0:
            reasons.append("có tags tương tự")

        distance_km = self._estimate_distance_km(source_data, candidate_data)
        reasons.append(f"cách khoảng {distance_km:.1f} km")

        source_score = self._current_crowd_score(source_data)
        candidate_score = self._current_crowd_score(candidate_data)
        if candidate_score < source_score:
            reasons.append(f"crowd thấp hơn {max(0, source_score - candidate_score)} điểm")

        reasons.append(f"rating {float(candidate_data.get('avg_rating', 0.0)):.1f}")
        return "Gợi ý vì " + ", ".join(reasons) + "."

    def get_source_options(self) -> list[tuple[str, str]]:
        attractions = self._scoped_attractions()
        if attractions.empty:
            return []
        return [
            (str(row.attraction_id), str(row.name))
            for row in attractions.sort_values(by="name", ascending=True).itertuples(index=False)
        ]

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

    def _fallback_or_json_gems(self) -> list[Destination]:
        if not settings.HIDDEN_GEMS_FILE.exists():
            return self._fallback_gems()

        raw_data = json.loads(settings.HIDDEN_GEMS_FILE.read_text(encoding="utf-8"))
        return [
            Destination(
                name=item["name"],
                province=item["province"],
                description=item["description"],
                eco_tip=item["eco_tip"],
            )
            for item in raw_data
        ]

    @staticmethod
    def _fallback_gems() -> list[Destination]:
        return [
            Destination(
                name="Làng chài Thanh Bình",
                province="Khánh Hòa",
                description="Khu làng nhỏ ven biển với mật độ khách thấp, phù hợp khám phá văn hóa địa phương.",
                eco_tip="Sử dụng bình nước cá nhân và hạn chế rác nhựa dùng một lần.",
            ),
            Destination(
                name="Đồi chè Phúc Xuân",
                province="Thái Nguyên",
                description="Cảnh quan xanh mát, đường đi bộ nhẹ nhàng, ít áp lực du lịch đại trà.",
                eco_tip="Ưu tiên đi nhóm nhỏ để giảm tác động lên hệ sinh thái.",
            ),
        ]

    @staticmethod
    def _build_eco_tip(indoor_outdoor: str, tags: str) -> str:
        normalized_tags = tags.casefold()
        if "biển" in normalized_tags or indoor_outdoor == "outdoor":
            return "Nên đi buổi sáng, mang nước cá nhân và giữ sạch không gian ngoài trời."
        if "làng nghề" in normalized_tags:
            return "Ưu tiên mua hàng thủ công địa phương và hạn chế dùng túi nylon."
        return "Đi theo nhóm nhỏ, tôn trọng không gian địa phương và ưu tiên phương tiện công cộng."

    def _current_crowd_score(self, attraction: Any) -> int:
        if self.crowd_forecast_service is not None:
            return self.crowd_forecast_service.get_current_crowd_score(attraction)
        attraction_data = self._normalize_row(attraction)
        return int(float(attraction_data.get("popularity_score", 40)))

    def _recommendation_score(self, source: Any, candidate: Any, preference: str | None) -> float:
        source_data = self._normalize_row(source)
        candidate_data = self._normalize_row(candidate)

        distance_km = self._estimate_distance_km(source_data, candidate_data)
        crowd_gap = max(0, self._current_crowd_score(source_data) - self._current_crowd_score(candidate_data))
        rating = float(candidate_data.get("avg_rating", 0.0))
        tag_overlap = self._tag_similarity(str(source_data.get("tags", "")), str(candidate_data.get("tags", "")))
        same_category_bonus = 18 if source_data.get("category") == candidate_data.get("category") else 0
        distance_component = max(0.0, 18.0 - distance_km * 2.1)
        tag_component = min(18.0, tag_overlap * 6.0)
        rating_component = rating * 8.0
        crowd_component = crowd_gap * 0.85

        preference_bonus = 0.0
        normalized_preference = (preference or "").casefold()
        if "gần" in normalized_preference:
            preference_bonus += max(0.0, 10.0 - distance_km)
        if "yên tĩnh" in normalized_preference or "ít đông" in normalized_preference:
            preference_bonus += crowd_gap * 0.45
        if "thiên nhiên" in normalized_preference and candidate_data.get("category") == "thiên nhiên":
            preference_bonus += 8.0

        return same_category_bonus + distance_component + tag_component + rating_component + crowd_component + preference_bonus

    @staticmethod
    def _tag_similarity(source_tags: str, candidate_tags: str) -> int:
        source_set = {tag.strip().casefold() for tag in source_tags.split("|") if tag.strip()}
        candidate_set = {tag.strip().casefold() for tag in candidate_tags.split("|") if tag.strip()}
        return len(source_set & candidate_set)

    @staticmethod
    def _estimate_distance_km(source: Any, candidate: Any) -> float:
        source_data = HiddenGemService._normalize_row(source)
        candidate_data = HiddenGemService._normalize_row(candidate)

        lat1 = float(source_data.get("latitude", 0.0) or 0.0)
        lon1 = float(source_data.get("longitude", 0.0) or 0.0)
        lat2 = float(candidate_data.get("latitude", 0.0) or 0.0)
        lon2 = float(candidate_data.get("longitude", 0.0) or 0.0)

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
    def _normalize_row(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return item
        if hasattr(item, "to_dict"):
            try:
                return item.to_dict()
            except TypeError:
                pass
        if hasattr(item, "_asdict"):
            return item._asdict()
        return {
            "attraction_id": getattr(item, "attraction_id", ""),
            "name": getattr(item, "name", ""),
            "category": getattr(item, "category", ""),
            "description": getattr(item, "description", ""),
            "latitude": getattr(item, "latitude", 0.0),
            "longitude": getattr(item, "longitude", 0.0),
            "area": getattr(item, "area", ""),
            "opening_hours": getattr(item, "opening_hours", ""),
            "ticket_price": getattr(item, "ticket_price", ""),
            "avg_rating": getattr(item, "avg_rating", 0.0),
            "estimated_capacity": getattr(item, "estimated_capacity", 0),
            "popularity_score": getattr(item, "popularity_score", 0),
            "indoor_outdoor": getattr(item, "indoor_outdoor", ""),
            "tags": getattr(item, "tags", ""),
            "current_crowd_score": getattr(item, "current_crowd_score", 0),
        }
