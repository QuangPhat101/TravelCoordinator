from datetime import datetime

from database.db_service import DBService
from services.crowd_forecast_service import CrowdForecastService
from services.sample_data_service import SampleDataService


class CrowdControlService:
    default_zones = (
        "Trung tâm sông Hàn",
        "Sơn Trà ven biển",
        "Ngũ Hành Sơn",
        "Làng nghề ngoại ô",
        "Khu ẩm thực địa phương",
    )

    def __init__(
        self,
        database_manager: DBService,
        sample_data_service: SampleDataService,
        crowd_forecast_service: CrowdForecastService | None = None,
    ) -> None:
        self.database_manager = database_manager
        self.sample_data_service = sample_data_service
        self.crowd_forecast_service = crowd_forecast_service

        attractions = self.sample_data_service.load_attractions()
        if not attractions.empty and "area" in attractions.columns:
            areas = [value for value in attractions["area"].dropna().unique().tolist() if value]
            if areas:
                self.default_zones = tuple(areas)

    def generate_live_overview(self) -> list[dict[str, str | int]]:
        attractions = self.sample_data_service.load_attractions()
        crowd_history = self.sample_data_service.load_crowd_history()

        if attractions.empty:
            return [
                {
                    "zone": zone,
                    "level": 40,
                    "status": self._status(40),
                    "recommendation": self._recommendation(40),
                }
                for zone in self.default_zones
            ]

        if self.crowd_forecast_service is not None:
            self.crowd_forecast_service.refresh_reference_data()
            working = attractions.copy()
            working["crowd_score"] = working.apply(
                self.crowd_forecast_service.get_current_crowd_score,
                axis=1,
            )
            working["last_updated"] = self.crowd_forecast_service.simulation_service.simulated_datetime.strftime(
                "%d/%m/%Y %H:%M"
            )
            merged = working.loc[:, ["area", "name", "crowd_score", "last_updated"]].sort_values(
                by="crowd_score",
                ascending=False,
            )
        else:
            if crowd_history.empty:
                return [
                    {
                        "zone": zone,
                        "level": 40,
                        "status": self._status(40),
                        "recommendation": self._recommendation(40),
                    }
                    for zone in self.default_zones
                ]

            latest_timestamp = crowd_history["timestamp"].max()
            latest_rows = crowd_history.loc[crowd_history["timestamp"] == latest_timestamp].copy()
            merged = latest_rows.merge(
                attractions[["attraction_id", "area", "name"]],
                on="attraction_id",
                how="left",
            )
            merged = merged.sort_values(by="crowd_score", ascending=False)

        grouped = (
            merged.groupby("area", as_index=False)
            .agg(
                average_crowd=("crowd_score", "mean"),
                hotspot=("name", "first"),
            )
            .sort_values(by="average_crowd", ascending=False)
        )

        overview: list[dict[str, str | int]] = []
        for row in grouped.itertuples(index=False):
            level = int(round(float(row.average_crowd)))
            recommendation = self._recommendation(level)
            if getattr(row, "hotspot", ""):
                recommendation = f"{recommendation} Điểm nổi bật hiện tại: {row.hotspot}."
            overview.append(
                {
                    "zone": str(row.area),
                    "level": level,
                    "status": self._status(level),
                    "recommendation": recommendation,
                }
            )
        return overview

    def save_manual_simulation(self, zone: str, level: int) -> dict[str, str | int]:
        normalized_level = max(0, min(100, int(level)))
        recommendation = self._recommendation(normalized_level)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.database_manager.save_crowd_snapshot(
            zone=zone,
            level=normalized_level,
            recommendation=recommendation,
            created_at=timestamp,
        )
        return {
            "zone": zone,
            "level": normalized_level,
            "recommendation": recommendation,
            "created_at": timestamp,
        }

    def recent_simulations(self, limit: int = 15) -> list[dict[str, str | int]]:
        rows = self.database_manager.get_recent_crowd_snapshots(limit=limit)
        return [
            {
                "created_at": row["created_at"],
                "zone": row["zone"],
                "level": row["level"],
                "recommendation": row["recommendation"],
            }
            for row in rows
        ]

    @staticmethod
    def _status(level: int) -> str:
        if level >= 80:
            return "Rất đông"
        if level >= 60:
            return "Đông"
        if level >= 35:
            return "Ổn định"
        return "Thông thoáng"

    @staticmethod
    def _recommendation(level: int) -> str:
        if level >= 80:
            return "Giới hạn khách mới và chuyển hướng sang điểm thay thế."
        if level >= 60:
            return "Khuyến nghị khách đặt lịch theo khung giờ lệch đỉnh."
        if level >= 35:
            return "Duy trì luồng hiện tại, theo dõi thêm."
        return "Có thể quảng bá thêm để phân tán dòng khách."
