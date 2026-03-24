from dataclasses import dataclass


@dataclass(slots=True)
class TripPlan:
    title: str
    start: str
    end: str
    preference: str
    stops: list[str]
    estimated_duration_minutes: int
    estimated_co2_saved_kg: float

    def to_text(self) -> str:
        stop_lines = "\n".join(f"- {stop}" for stop in self.stops)
        return (
            f"{self.title}\n"
            f"Ưu tiên: {self.preference}\n"
            f"Thời gian dự kiến: {self.estimated_duration_minutes} phút\n"
            f"CO2 giảm ước tính: {self.estimated_co2_saved_kg:.1f} kg\n"
            "\n"
            "Các điểm trung gian:\n"
            f"{stop_lines}"
        )
