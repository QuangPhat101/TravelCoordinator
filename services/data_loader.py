from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from config import settings
from models.attraction import Attraction
from models.crowd_record import CrowdRecord
from models.faq_item import FaqItem
from models.transport_option import TransportOption

logger = logging.getLogger(__name__)


class DataLoader:
    """Load and normalize sample CSV datasets for local desktop features."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else settings.SAMPLE_DATA_DIR
        self.attractions_file = self.data_dir / settings.SAMPLE_DATA_FILES["attractions"].name
        self.crowd_history_file = self.data_dir / settings.SAMPLE_DATA_FILES["crowd_history"].name
        self.transport_options_file = self.data_dir / settings.SAMPLE_DATA_FILES["transport_options"].name
        self.eco_rewards_file = self.data_dir / settings.SAMPLE_DATA_FILES["eco_rewards"].name
        self.faq_knowledge_base_file = self.data_dir / settings.SAMPLE_DATA_FILES["faq_knowledge_base"].name

    def load_attractions(self) -> pd.DataFrame:
        frame = self._load_dataframe(
            path=self.attractions_file,
            dataset_name="attractions",
            required_columns={"attraction_id", "name", "category"},
            optional_defaults={
                "description": "",
                "latitude": 0.0,
                "longitude": 0.0,
                "area": "",
                "opening_hours": "",
                "ticket_price": "",
                "avg_rating": 0.0,
                "estimated_capacity": 0,
                "popularity_score": 0,
                "indoor_outdoor": "",
                "tags": "",
            },
        )
        if frame.empty:
            return self._empty_attractions_frame()

        numeric_columns = {
            "latitude": 0.0,
            "longitude": 0.0,
            "avg_rating": 0.0,
            "estimated_capacity": 0,
            "popularity_score": 0,
        }
        for column_name, default_value in numeric_columns.items():
            frame[column_name] = pd.to_numeric(frame[column_name], errors="coerce").fillna(default_value)

        normalized_rows = [
            asdict(
                Attraction(
                    attraction_id=str(row.attraction_id),
                    name=str(row.name),
                    category=str(row.category),
                    description=str(row.description),
                    latitude=float(row.latitude),
                    longitude=float(row.longitude),
                    area=str(row.area),
                    opening_hours=str(row.opening_hours),
                    ticket_price=str(row.ticket_price),
                    avg_rating=float(row.avg_rating),
                    estimated_capacity=int(row.estimated_capacity),
                    popularity_score=int(row.popularity_score),
                    indoor_outdoor=str(row.indoor_outdoor),
                    tags=str(row.tags),
                )
            )
            for row in frame.itertuples(index=False)
        ]
        return pd.DataFrame(normalized_rows, columns=self._empty_attractions_frame().columns)

    def load_crowd_history(self) -> pd.DataFrame:
        frame = self._load_dataframe(
            path=self.crowd_history_file,
            dataset_name="crowd_history",
            required_columns={"timestamp", "attraction_id", "crowd_score"},
            optional_defaults={
                "weather": "",
                "temperature": 0.0,
                "rain_flag": 0,
                "holiday_flag": 0,
                "event_flag": 0,
                "day_of_week": "",
                "hour": 0,
            },
        )
        if frame.empty:
            return self._empty_crowd_history_frame()

        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
        frame["crowd_score"] = pd.to_numeric(frame["crowd_score"], errors="coerce").fillna(0).astype(int)
        frame["temperature"] = pd.to_numeric(frame["temperature"], errors="coerce").fillna(0.0)
        for flag_column in ("rain_flag", "holiday_flag", "event_flag", "hour"):
            frame[flag_column] = pd.to_numeric(frame[flag_column], errors="coerce").fillna(0).astype(int)

        normalized_rows = [
            asdict(
                CrowdRecord(
                    timestamp=row.timestamp.to_pydatetime() if pd.notna(row.timestamp) else None,
                    attraction_id=str(row.attraction_id),
                    crowd_score=int(row.crowd_score),
                    weather=str(row.weather),
                    temperature=float(row.temperature),
                    rain_flag=int(row.rain_flag),
                    holiday_flag=int(row.holiday_flag),
                    event_flag=int(row.event_flag),
                    day_of_week=str(row.day_of_week),
                    hour=int(row.hour),
                )
            )
            for row in frame.itertuples(index=False)
        ]
        normalized_frame = pd.DataFrame(normalized_rows, columns=self._empty_crowd_history_frame().columns)
        normalized_frame["timestamp"] = pd.to_datetime(normalized_frame["timestamp"], errors="coerce")
        return normalized_frame

    def load_transport_options(self) -> pd.DataFrame:
        frame = self._load_dataframe(
            path=self.transport_options_file,
            dataset_name="transport_options",
            required_columns={"origin_id", "destination_id", "transport_mode"},
            optional_defaults={
                "distance_km": 0.0,
                "duration_min": 0,
                "estimated_carbon_g": 0,
            },
        )
        if frame.empty:
            return self._empty_transport_options_frame()

        frame["distance_km"] = pd.to_numeric(frame["distance_km"], errors="coerce").fillna(0.0)
        frame["duration_min"] = pd.to_numeric(frame["duration_min"], errors="coerce").fillna(0).astype(int)
        frame["estimated_carbon_g"] = (
            pd.to_numeric(frame["estimated_carbon_g"], errors="coerce").fillna(0).astype(int)
        )

        normalized_rows = [
            asdict(
                TransportOption(
                    origin_id=str(row.origin_id),
                    destination_id=str(row.destination_id),
                    transport_mode=str(row.transport_mode),
                    distance_km=float(row.distance_km),
                    duration_min=int(row.duration_min),
                    estimated_carbon_g=int(row.estimated_carbon_g),
                )
            )
            for row in frame.itertuples(index=False)
        ]
        return pd.DataFrame(normalized_rows, columns=self._empty_transport_options_frame().columns)

    def load_eco_rewards(self) -> pd.DataFrame:
        frame = self._load_dataframe(
            path=self.eco_rewards_file,
            dataset_name="eco_rewards",
            required_columns={"rule_id", "action_type", "point_value"},
            optional_defaults={
                "condition": "",
                "description": "",
            },
        )
        if frame.empty:
            return self._empty_eco_rewards_frame()

        frame["point_value"] = pd.to_numeric(frame["point_value"], errors="coerce").fillna(0).astype(int)
        return frame.loc[:, self._empty_eco_rewards_frame().columns].copy()

    def load_faq_items(self) -> list[FaqItem]:
        frame = self._load_dataframe(
            path=self.faq_knowledge_base_file,
            dataset_name="faq_knowledge_base",
            required_columns={"question", "intent", "answer"},
            optional_defaults={"tags": ""},
        )
        if frame.empty:
            return []

        return [
            FaqItem(
                question=str(row.question),
                intent=str(row.intent),
                answer=str(row.answer),
                tags=str(row.tags),
            )
            for row in frame.itertuples(index=False)
        ]

    def get_attraction_by_id(self, attraction_id: str) -> Attraction | None:
        attractions = self.load_attractions()
        if attractions.empty:
            return None

        matched = attractions.loc[attractions["attraction_id"] == attraction_id]
        if matched.empty:
            return None

        row = matched.iloc[0]
        return Attraction(
            attraction_id=str(row["attraction_id"]),
            name=str(row["name"]),
            category=str(row["category"]),
            description=str(row["description"]),
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            area=str(row["area"]),
            opening_hours=str(row["opening_hours"]),
            ticket_price=str(row["ticket_price"]),
            avg_rating=float(row["avg_rating"]),
            estimated_capacity=int(row["estimated_capacity"]),
            popularity_score=int(row["popularity_score"]),
            indoor_outdoor=str(row["indoor_outdoor"]),
            tags=str(row["tags"]),
        )

    def get_all_categories(self) -> list[str]:
        attractions = self.load_attractions()
        if attractions.empty:
            return []
        return sorted(
            category
            for category in attractions["category"].dropna().astype(str).unique().tolist()
            if category
        )

    def _load_dataframe(
        self,
        path: Path,
        dataset_name: str,
        required_columns: set[str],
        optional_defaults: dict[str, Any],
    ) -> pd.DataFrame:
        if not path.exists():
            logger.warning("Khong tim thay file %s tai %s", dataset_name, path)
            return pd.DataFrame(columns=self._expected_columns(required_columns, optional_defaults))

        try:
            frame = pd.read_csv(path, encoding="utf-8-sig")
        except Exception as exc:  # pragma: no cover - depends on file system and malformed CSV.
            logger.warning("Khong doc duoc file %s tai %s: %s", dataset_name, path, exc)
            return pd.DataFrame(columns=self._expected_columns(required_columns, optional_defaults))

        frame.columns = [str(column).strip() for column in frame.columns]
        missing_required = [column for column in required_columns if column not in frame.columns]
        if missing_required:
            logger.warning(
                "Schema %s khong hop le. Thieu cot bat buoc: %s",
                dataset_name,
                ", ".join(sorted(missing_required)),
            )
            return pd.DataFrame(columns=self._expected_columns(required_columns, optional_defaults))

        for column_name, default_value in optional_defaults.items():
            if column_name not in frame.columns:
                logger.warning(
                    "File %s thieu cot tuy chon '%s'. Su dung gia tri mac dinh.",
                    dataset_name,
                    column_name,
                )
                frame[column_name] = default_value

        normalized = frame.loc[:, self._expected_columns(required_columns, optional_defaults)].copy()
        return normalized.fillna(value=optional_defaults)

    @staticmethod
    def _expected_columns(required_columns: set[str], optional_defaults: dict[str, Any]) -> list[str]:
        ordered_required = sorted(required_columns)
        optional_columns = [column for column in optional_defaults.keys() if column not in required_columns]
        return ordered_required + optional_columns

    @staticmethod
    def _empty_attractions_frame() -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "attraction_id",
                "name",
                "category",
                "description",
                "latitude",
                "longitude",
                "area",
                "opening_hours",
                "ticket_price",
                "avg_rating",
                "estimated_capacity",
                "popularity_score",
                "indoor_outdoor",
                "tags",
            ]
        )

    @staticmethod
    def _empty_crowd_history_frame() -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "attraction_id",
                "crowd_score",
                "weather",
                "temperature",
                "rain_flag",
                "holiday_flag",
                "event_flag",
                "day_of_week",
                "hour",
            ]
        )

    @staticmethod
    def _empty_transport_options_frame() -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "origin_id",
                "destination_id",
                "transport_mode",
                "distance_km",
                "duration_min",
                "estimated_carbon_g",
            ]
        )

    @staticmethod
    def _empty_eco_rewards_frame() -> pd.DataFrame:
        return pd.DataFrame(columns=["rule_id", "action_type", "point_value", "condition", "description"])
