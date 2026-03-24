from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CrowdRecord:
    timestamp: datetime | None
    attraction_id: str
    crowd_score: int
    weather: str = ""
    temperature: float = 0.0
    rain_flag: int = 0
    holiday_flag: int = 0
    event_flag: int = 0
    day_of_week: str = ""
    hour: int = 0
