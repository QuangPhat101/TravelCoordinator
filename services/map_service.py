from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd

from config import settings
from services.crowd_forecast_service import CrowdForecastService
from services.data_loader import DataLoader
from services.simulation_service import SimulationService


class MapService:
    def __init__(
        self,
        data_loader: DataLoader,
        crowd_forecast_service: CrowdForecastService | None = None,
        simulation_service: SimulationService | None = None,
        default_city: str | None = None,
    ) -> None:
        self.data_loader = data_loader
        self.crowd_forecast_service = crowd_forecast_service
        self.simulation_service = simulation_service
        self.default_city = (default_city or settings.DEFAULT_MAP_CITY).strip()

    def get_available_cities(self) -> list[str]:
        attractions = self._load_enriched_attractions()
        if attractions.empty:
            return [settings.ALL_CITY_SCOPE_LABEL, self.default_city] if self.default_city else [settings.ALL_CITY_SCOPE_LABEL]

        cities = [
            value
            for value in attractions["resolved_city"].dropna().astype(str).unique().tolist()
            if value.strip()
        ]
        ordered = [settings.ALL_CITY_SCOPE_LABEL]
        for city in sorted(cities):
            if city not in ordered:
                ordered.append(city)
        return ordered

    def filter_attractions_by_city(self, city: str | None = None) -> pd.DataFrame:
        attractions = self._load_enriched_attractions()
        if attractions.empty:
            return attractions

        normalized_city = (city or self._current_city_scope()).strip().casefold()
        if not normalized_city or normalized_city == settings.ALL_CITY_SCOPE_LABEL.casefold():
            return attractions

        filtered = attractions.loc[
            attractions["resolved_city"].astype(str).str.casefold() == normalized_city
        ].copy()
        return filtered if not filtered.empty else attractions

    def get_map_context(self, city: str | None = None) -> dict[str, Any]:
        frame = self.filter_attractions_by_city(city)
        selected_city = self._resolve_selected_city(frame, city)
        point_count = int(len(frame.index))
        html = self.generate_map_html(frame, selected_city)

        return {
            "html": html,
            "selected_city": selected_city,
            "point_count": point_count,
            "available_cities": self.get_available_cities(),
        }

    def generate_map_html(self, attractions: pd.DataFrame, city: str | None = None) -> str:
        try:
            import folium
        except ImportError:
            return self._build_message_html(
                "Chưa có thư viện folium",
                "Hãy cài lại requirements để bật bản đồ Leaflet + OpenStreetMap trong app.",
            )

        center_lat = settings.DEFAULT_MAP_CENTER_LAT
        center_lon = settings.DEFAULT_MAP_CENTER_LON
        zoom_start = settings.DEFAULT_MAP_ZOOM

        if not attractions.empty:
            valid_coords = attractions.loc[
                attractions["latitude"].notna()
                & attractions["longitude"].notna()
            ].copy()
            if not valid_coords.empty:
                center_lat = float(valid_coords["latitude"].mean())
                center_lon = float(valid_coords["longitude"].mean())

        map_object = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            control_scale=True,
            tiles="OpenStreetMap",
        )

        title_html = (
            f"<div style='position: fixed; top: 12px; left: 50px; z-index: 9999; "
            f"background: rgba(255,255,255,0.94); border: 1px solid #c9d8eb; border-radius: 10px; "
            f"padding: 10px 14px; color: #16324f; font-family: Segoe UI, Arial, sans-serif;'>"
            f"<div style='font-size: 15px; font-weight: 700;'>Bản đồ du lịch</div>"
            f"<div style='font-size: 12px; color: #5c7592;'>"
            f"{escape(city or self._current_city_scope() or self.default_city or 'Dữ liệu hiện tại')} | Marker theo crowd level hiện tại"
            f"</div></div>"
        )
        map_object.get_root().html.add_child(folium.Element(title_html))

        if attractions.empty:
            return map_object.get_root().render()

        bounds: list[list[float]] = []
        for record in attractions.itertuples(index=False):
            if pd.isna(record.latitude) or pd.isna(record.longitude):
                continue

            lat = float(record.latitude)
            lon = float(record.longitude)
            bounds.append([lat, lon])

            popup_html = self._build_popup_html(record)
            marker_color = self._marker_color(int(record.crowd_score))
            folium.CircleMarker(
                location=[lat, lon],
                radius=9,
                color=marker_color,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.9,
                weight=2,
                tooltip=str(record.name),
                popup=folium.Popup(popup_html, max_width=340),
            ).add_to(map_object)

        if len(bounds) > 1:
            map_object.fit_bounds(bounds, padding=(28, 28))
        elif len(bounds) == 1:
            map_object.location = bounds[0]
            map_object.zoom_start = 14

        return map_object.get_root().render()

    def _load_enriched_attractions(self) -> pd.DataFrame:
        attractions = self.data_loader.load_attractions().copy()
        if attractions.empty:
            return attractions

        if self.crowd_forecast_service is not None:
            self.crowd_forecast_service.refresh_reference_data()
            attractions["crowd_score"] = attractions.apply(
                self.crowd_forecast_service.get_current_crowd_score,
                axis=1,
            )
            attractions["best_visit_time"] = attractions.apply(
                self._best_visit_label,
                axis=1,
            )
        else:
            attractions["crowd_score"] = pd.to_numeric(
                attractions.get("popularity_score", 0),
                errors="coerce",
            ).fillna(0).astype(int)
            attractions["best_visit_time"] = ""

        attractions["resolved_city"] = self._resolve_city_series(attractions)
        attractions["crowd_label"] = attractions["crowd_score"].apply(self._crowd_label)
        return attractions

    def _best_visit_label(self, attraction: pd.Series) -> str:
        if self.crowd_forecast_service is None:
            return ""

        best_visit = self.crowd_forecast_service.get_best_visit_time(attraction)
        best_datetime = best_visit.get("datetime")
        if best_datetime is None:
            return ""
        return f"{best_datetime.strftime('%d/%m %H:%M')} ({best_visit['crowd_score']}/100)"

    def _resolve_city_series(self, attractions: pd.DataFrame) -> pd.Series:
        for column_name in ("city", "province", "destination_city"):
            if column_name in attractions.columns:
                return attractions[column_name].fillna(self.default_city).astype(str)
        return pd.Series([self.default_city] * len(attractions.index), index=attractions.index, dtype="object")

    def _resolve_selected_city(self, frame: pd.DataFrame, city: str | None) -> str:
        explicit_city = (city or self._current_city_scope()).strip()
        if explicit_city:
            return explicit_city
        if not frame.empty:
            return str(frame.iloc[0]["resolved_city"])
        return self.default_city

    def _current_city_scope(self) -> str:
        if self.simulation_service is not None:
            return self.simulation_service.city_scope
        return settings.ALL_CITY_SCOPE_LABEL

    @staticmethod
    def _crowd_label(score: int) -> str:
        normalized = max(0, min(100, int(score)))
        if normalized <= 25:
            return "Thấp"
        if normalized <= 50:
            return "Vừa"
        if normalized <= 75:
            return "Cao"
        return "Rất đông"

    @staticmethod
    def _marker_color(score: int) -> str:
        normalized = max(0, min(100, int(score)))
        if normalized <= 25:
            return "#60a5fa"
        if normalized <= 50:
            return "#facc15"
        if normalized <= 75:
            return "#fb923c"
        return "#ef4444"

    @staticmethod
    def _build_popup_html(record: Any) -> str:
        best_visit = str(getattr(record, "best_visit_time", "") or "").strip()
        best_visit_row = (
            f"<div><b>Khung giờ nên đi:</b> {escape(best_visit)}</div>"
            if best_visit
            else ""
        )
        return (
            "<div style='font-family: Segoe UI, Arial, sans-serif; color: #16324f; min-width: 220px;'>"
            f"<div style='font-size: 15px; font-weight: 700; margin-bottom: 6px;'>{escape(str(record.name))}</div>"
            f"<div><b>Loại hình:</b> {escape(str(record.category))}</div>"
            f"<div><b>Khu vực:</b> {escape(str(getattr(record, 'area', '') or 'Chưa rõ'))}</div>"
            f"<div><b>Thành phố:</b> {escape(str(getattr(record, 'resolved_city', '') or 'Chưa rõ'))}</div>"
            f"<div><b>Crowd score:</b> {int(getattr(record, 'crowd_score', 0))}/100 ({escape(str(getattr(record, 'crowd_label', '')))} )</div>"
            f"<div><b>Rating:</b> {float(getattr(record, 'avg_rating', 0.0)):.1f}</div>"
            f"{best_visit_row}"
            "</div>"
        )

    @staticmethod
    def _build_message_html(title: str, body: str) -> str:
        return (
            "<html><body style='margin:0; background:#f4f8fd; font-family:Segoe UI, Arial, sans-serif;'>"
            "<div style='height:100%; display:flex; align-items:center; justify-content:center; padding:24px;'>"
            "<div style='background:#ffffff; border:1px solid #c9d8eb; border-radius:16px; "
            "padding:24px; max-width:480px; color:#16324f;'>"
            f"<div style='font-size:20px; font-weight:700; margin-bottom:8px;'>{escape(title)}</div>"
            f"<div style='font-size:14px; color:#5c7592;'>{escape(body)}</div>"
            "</div></div></body></html>"
        )
