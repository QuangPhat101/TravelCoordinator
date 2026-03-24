from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from services.crowd_forecast_service import CrowdForecastService


@dataclass(slots=True)
class DashboardAttractionRow:
    attraction_id: str
    name: str
    category: str
    area: str
    crowd_score: int
    crowd_level: str
    alert_label: str
    alert_color: str
    rating: float
    description: str
    opening_hours: str
    ticket_price: str
    estimated_capacity: int
    popularity_score: int
    indoor_outdoor: str
    tags: str
    last_updated: str
    crowd_explanation: str
    best_visit_label: str
    forecast_preview: str


def get_alert_level(score: int) -> tuple[str, str]:
    normalized = max(0, min(100, int(score)))
    if normalized <= 25:
        return "Xanh", "#2f855a"
    if normalized <= 50:
        return "Vàng", "#d69e2e"
    if normalized <= 75:
        return "Cam", "#dd6b20"
    return "Đỏ", "#c53030"


def get_crowd_level(score: int) -> str:
    normalized = max(0, min(100, int(score)))
    if normalized <= 25:
        return "low"
    if normalized <= 50:
        return "moderate"
    if normalized <= 75:
        return "high"
    return "overcrowded"


def build_dashboard_rows(
    attractions: pd.DataFrame,
    crowd_history: pd.DataFrame,
    crowd_forecast_service: CrowdForecastService | None = None,
) -> list[DashboardAttractionRow]:
    if attractions.empty:
        return []

    latest_crowd = _latest_crowd_by_attraction(crowd_history)
    merged = attractions.merge(latest_crowd, on="attraction_id", how="left")
    merged["crowd_score"] = pd.to_numeric(merged["crowd_score"], errors="coerce").fillna(0).astype(int)
    merged["avg_rating"] = pd.to_numeric(merged["avg_rating"], errors="coerce").fillna(0.0)
    merged["estimated_capacity"] = pd.to_numeric(merged["estimated_capacity"], errors="coerce").fillna(0).astype(int)
    merged["popularity_score"] = pd.to_numeric(merged["popularity_score"], errors="coerce").fillna(0).astype(int)
    merged["last_updated"] = merged["last_updated"].fillna("Chưa có dữ liệu crowd")

    rows: list[DashboardAttractionRow] = []
    sorted_frame = merged.sort_values(
        by=["crowd_score", "avg_rating", "name"],
        ascending=[False, False, True],
    )
    for record in sorted_frame.itertuples(index=False):
        current_score = int(record.crowd_score)
        crowd_explanation = "Crowd score lấy từ bản ghi lịch sử mới nhất."
        best_visit_label = "Chưa có dự báo"
        forecast_preview = "Chưa có dự báo"
        last_updated = str(record.last_updated)

        if crowd_forecast_service is not None:
            current_score = crowd_forecast_service.get_current_crowd_score(record)
            forecast_items = crowd_forecast_service.forecast_next_hours(record, hours=4)
            best_visit = crowd_forecast_service.get_best_visit_time(record)
            crowd_explanation = crowd_forecast_service.explain_crowd_score(record)
            best_visit_label = (
                f"{best_visit['datetime'].strftime('%d/%m %H:%M')} - "
                f"{best_visit['crowd_score']}% ({best_visit['level']})"
            )
            forecast_preview = ", ".join(
                f"{item['datetime'].strftime('%H:%M')} {item['crowd_score']}%"
                for item in forecast_items
            )
            last_updated = crowd_forecast_service.simulation_service.simulated_datetime.strftime("%d/%m/%Y %H:%M")

        alert_label, alert_color = get_alert_level(current_score)
        crowd_level = get_crowd_level(current_score)
        rows.append(
            DashboardAttractionRow(
                attraction_id=str(record.attraction_id),
                name=str(record.name),
                category=str(record.category),
                area=str(record.area),
                crowd_score=current_score,
                crowd_level=crowd_level,
                alert_label=alert_label,
                alert_color=alert_color,
                rating=float(record.avg_rating),
                description=str(record.description),
                opening_hours=str(record.opening_hours),
                ticket_price=str(record.ticket_price),
                estimated_capacity=int(record.estimated_capacity),
                popularity_score=int(record.popularity_score),
                indoor_outdoor=str(record.indoor_outdoor),
                tags=str(record.tags),
                last_updated=last_updated,
                crowd_explanation=crowd_explanation,
                best_visit_label=best_visit_label,
                forecast_preview=forecast_preview,
            )
        )
    return sorted(rows, key=lambda item: (-item.crowd_score, -item.rating, item.name.casefold()))


def calculate_dashboard_metrics(rows: list[DashboardAttractionRow], eco_points: int) -> dict[str, int]:
    total_attractions = len(rows)
    busy_count = sum(1 for row in rows if row.crowd_score >= 51)
    hidden_gem_count = sum(
        1
        for row in rows
        if row.crowd_score <= 50 and row.popularity_score <= 60 and row.rating >= 4.4
    )
    return {
        "total_attractions": total_attractions,
        "busy_count": busy_count,
        "hidden_gem_count": hidden_gem_count,
        "eco_points": max(0, int(eco_points)),
    }


def _latest_crowd_by_attraction(crowd_history: pd.DataFrame) -> pd.DataFrame:
    if crowd_history.empty or "attraction_id" not in crowd_history.columns:
        return pd.DataFrame(columns=["attraction_id", "crowd_score", "last_updated"])

    working = crowd_history.copy()
    if "timestamp" in working.columns:
        working["timestamp"] = pd.to_datetime(working["timestamp"], errors="coerce")
        working = working.sort_values(by=["attraction_id", "timestamp"])
        latest = working.groupby("attraction_id", as_index=False).tail(1)
        latest["last_updated"] = latest["timestamp"].dt.strftime("%d/%m/%Y %H:%M")
    else:
        latest = working.groupby("attraction_id", as_index=False).tail(1)
        latest["last_updated"] = "Không rõ thời gian"

    return latest.loc[:, ["attraction_id", "crowd_score", "last_updated"]]
