from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from config import settings


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("prepare_training_data")


ATTRACTIONS_REQUIRED_COLUMNS = {
    "attraction_id",
    "name",
    "category",
    "estimated_capacity",
    "popularity_score",
    "indoor_outdoor",
}
HISTORY_REQUIRED_COLUMNS = {
    "timestamp",
    "attraction_id",
    "crowd_score",
    "weather",
    "holiday_flag",
    "event_flag",
    "day_of_week",
    "hour",
}


def load_csv_safe(file_path: Path, required_columns: set[str], dataset_name: str) -> pd.DataFrame:
    if not file_path.exists():
        LOGGER.warning("Khong tim thay file %s: %s", dataset_name, file_path)
        return pd.DataFrame()

    dataframe = pd.read_csv(file_path)
    missing_columns = sorted(required_columns - set(dataframe.columns))
    if missing_columns:
        LOGGER.warning(
            "Dataset %s thieu cot bat buoc: %s",
            dataset_name,
            ", ".join(missing_columns),
        )
        return pd.DataFrame()

    return dataframe


def ensure_support_directories() -> None:
    settings.TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.MODEL_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    settings.NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)


def normalize_city_column(attractions: pd.DataFrame) -> pd.DataFrame:
    frame = attractions.copy()

    if "city" not in frame.columns:
        frame["city"] = settings.DEFAULT_CITY_SCOPE

    frame["city"] = (
        frame["city"]
        .fillna(settings.DEFAULT_CITY_SCOPE)
        .astype(str)
        .str.strip()
        .replace({"": settings.DEFAULT_CITY_SCOPE})
    )
    return frame


def prepare_training_dataframe(
    attractions: pd.DataFrame,
    crowd_history: pd.DataFrame,
) -> pd.DataFrame:
    attractions_frame = normalize_city_column(attractions)
    history_frame = crowd_history.copy()

    history_frame["timestamp"] = pd.to_datetime(history_frame["timestamp"], errors="coerce")
    history_frame = history_frame.dropna(subset=["timestamp", "attraction_id", "crowd_score"])
    history_frame = history_frame.sort_values(["attraction_id", "timestamp"]).reset_index(drop=True)

    if "day_of_week" not in history_frame.columns:
        history_frame["day_of_week"] = history_frame["timestamp"].dt.day_name()
    if "hour" not in history_frame.columns:
        history_frame["hour"] = history_frame["timestamp"].dt.hour

    history_frame["historical_crowd_score"] = (
        history_frame.groupby("attraction_id")["crowd_score"].shift(1)
    )
    history_frame["historical_crowd_score"] = history_frame["historical_crowd_score"].fillna(
        history_frame["crowd_score"]
    )

    merged = history_frame.merge(
        attractions_frame[
            [
                "attraction_id",
                "city",
                "name",
                "category",
                "estimated_capacity",
                "popularity_score",
                "indoor_outdoor",
            ]
        ],
        how="left",
        on="attraction_id",
    )

    merged["city"] = merged["city"].fillna(settings.DEFAULT_CITY_SCOPE)
    merged["category"] = merged["category"].fillna("khong_ro")
    merged["indoor_outdoor"] = merged["indoor_outdoor"].fillna("khong_ro")
    merged["weather"] = merged["weather"].fillna("khong_ro")
    merged["day_of_week"] = merged["day_of_week"].fillna(merged["timestamp"].dt.day_name())

    numeric_defaults = {
        "estimated_capacity": 0,
        "popularity_score": 0,
        "hour": 0,
        "holiday_flag": 0,
        "event_flag": 0,
        "historical_crowd_score": 0,
        "temperature": 0,
        "rain_flag": 0,
        "crowd_score": 0,
    }

    for column_name, default_value in numeric_defaults.items():
        if column_name not in merged.columns:
            merged[column_name] = default_value
        merged[column_name] = pd.to_numeric(merged[column_name], errors="coerce").fillna(default_value)

    output_columns = [
        "timestamp",
        "attraction_id",
        "name",
        "city",
        "category",
        "popularity_score",
        "estimated_capacity",
        "hour",
        "day_of_week",
        "weather",
        "holiday_flag",
        "event_flag",
        "historical_crowd_score",
        "indoor_outdoor",
        "temperature",
        "rain_flag",
        "crowd_score",
    ]

    prepared = merged[output_columns].copy()
    prepared["crowd_score"] = prepared["crowd_score"].clip(lower=0, upper=100)
    prepared["historical_crowd_score"] = prepared["historical_crowd_score"].clip(lower=0, upper=100)
    prepared["hour"] = prepared["hour"].astype(int).clip(lower=0, upper=23)
    prepared["holiday_flag"] = prepared["holiday_flag"].astype(int).clip(lower=0, upper=1)
    prepared["event_flag"] = prepared["event_flag"].astype(int).clip(lower=0, upper=1)
    prepared["rain_flag"] = prepared["rain_flag"].astype(int).clip(lower=0, upper=1)
    return prepared


def save_training_dataframe(training_frame: pd.DataFrame) -> list[Path]:
    output_paths = [
        settings.CROWD_TRAINING_DATA_FILE,
        settings.CLEANED_TRAINING_DATA_FILE,
    ]

    for output_path in output_paths:
        training_frame.to_csv(output_path, index=False, encoding="utf-8-sig")

    return output_paths


def main() -> None:
    ensure_support_directories()

    attractions = load_csv_safe(
        settings.ATTRACTIONS_SAMPLE_FILE,
        ATTRACTIONS_REQUIRED_COLUMNS,
        "attractions",
    )
    crowd_history = load_csv_safe(
        settings.CROWD_HISTORY_SAMPLE_FILE,
        HISTORY_REQUIRED_COLUMNS,
        "crowd_history",
    )

    if attractions.empty or crowd_history.empty:
        LOGGER.warning("Khong du du lieu de tao training dataset.")
        empty_frame = pd.DataFrame(
            columns=[
                "timestamp",
                "attraction_id",
                "name",
                "city",
                "category",
                "popularity_score",
                "estimated_capacity",
                "hour",
                "day_of_week",
                "weather",
                "holiday_flag",
                "event_flag",
                "historical_crowd_score",
                "indoor_outdoor",
                "temperature",
                "rain_flag",
                "crowd_score",
            ]
        )
        output_paths = save_training_dataframe(empty_frame)
        for output_path in output_paths:
            LOGGER.info("Da tao file rong an toan tai %s", output_path)
        return

    training_frame = prepare_training_dataframe(attractions, crowd_history)
    output_paths = save_training_dataframe(training_frame)

    for output_path in output_paths:
        LOGGER.info("Da tao training dataset tai %s", output_path)
    LOGGER.info("So dong: %s", len(training_frame))
    LOGGER.info("So attraction: %s", training_frame["attraction_id"].nunique())
    LOGGER.info("So city: %s", training_frame["city"].nunique())


if __name__ == "__main__":
    main()
