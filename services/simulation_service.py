from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, Signal

from config import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SimulationState:
    simulated_datetime: datetime
    weather: str
    global_crowd_multiplier: float
    event_flag: bool
    holiday_flag: bool
    city_scope: str


class SimulationService(QObject):
    state_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._city_options: list[str] = [settings.DEFAULT_CITY_SCOPE]
        self._state = SimulationState(
            simulated_datetime=datetime.now().replace(minute=0, second=0, microsecond=0),
            weather=settings.DEFAULT_SIMULATION_WEATHER,
            global_crowd_multiplier=settings.SIMULATION_MULTIPLIER_DEFAULT,
            event_flag=False,
            holiday_flag=False,
            city_scope=settings.DEFAULT_CITY_SCOPE,
        )

    @property
    def simulated_datetime(self) -> datetime:
        return self._state.simulated_datetime

    @property
    def weather(self) -> str:
        return self._state.weather

    @property
    def global_crowd_multiplier(self) -> float:
        return self._state.global_crowd_multiplier

    @property
    def event_flag(self) -> bool:
        return self._state.event_flag

    @property
    def holiday_flag(self) -> bool:
        return self._state.holiday_flag

    @property
    def city_scope(self) -> str:
        return self._state.city_scope

    def get_state(self) -> SimulationState:
        return SimulationState(
            simulated_datetime=self._state.simulated_datetime,
            weather=self._state.weather,
            global_crowd_multiplier=self._state.global_crowd_multiplier,
            event_flag=self._state.event_flag,
            holiday_flag=self._state.holiday_flag,
            city_scope=self._state.city_scope,
        )

    def get_city_options(self) -> list[str]:
        return list(self._city_options)

    def set_city_options(self, city_options: list[str]) -> list[str]:
        cleaned = [city.strip() for city in city_options if city and city.strip()]
        ordered: list[str] = [settings.ALL_CITY_SCOPE_LABEL]
        for city in cleaned:
            if city not in ordered:
                ordered.append(city)

        if len(ordered) == 1 and settings.DEFAULT_CITY_SCOPE not in ordered:
            ordered.append(settings.DEFAULT_CITY_SCOPE)

        self._city_options = ordered
        if self._state.city_scope not in self._city_options:
            fallback_scope = settings.ALL_CITY_SCOPE_LABEL if settings.ALL_CITY_SCOPE_LABEL in self._city_options else self._city_options[0]
            self._state.city_scope = fallback_scope
            self.state_changed.emit(self.get_state())
        return self.get_city_options()

    def update_state(
        self,
        simulated_datetime: datetime | None = None,
        weather: str | None = None,
        global_crowd_multiplier: float | None = None,
        event_flag: bool | None = None,
        holiday_flag: bool | None = None,
        city_scope: str | None = None,
    ) -> SimulationState:
        try:
            if simulated_datetime is not None:
                self._state.simulated_datetime = simulated_datetime.replace(minute=0, second=0, microsecond=0)
            if weather is not None and weather.strip():
                self._state.weather = weather.strip()
            if global_crowd_multiplier is not None:
                self._state.global_crowd_multiplier = max(
                    settings.SIMULATION_MULTIPLIER_MIN,
                    min(settings.SIMULATION_MULTIPLIER_MAX, float(global_crowd_multiplier)),
                )
            if event_flag is not None:
                self._state.event_flag = bool(event_flag)
            if holiday_flag is not None:
                self._state.holiday_flag = bool(holiday_flag)
            if city_scope is not None and city_scope.strip():
                normalized_city = city_scope.strip()
                if normalized_city not in self._city_options:
                    logger.warning("City scope '%s' chưa có trong danh sách, dùng giá trị hiện tại.", normalized_city)
                else:
                    self._state.city_scope = normalized_city
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Không thể cập nhật simulation state: %s", exc)
        self.state_changed.emit(self.get_state())
        return self.get_state()

    def shift_hours(self, hours: int) -> SimulationState:
        self._state.simulated_datetime = self._state.simulated_datetime + timedelta(hours=int(hours))
        self.state_changed.emit(self.get_state())
        return self.get_state()

    def reset_to_defaults(self) -> SimulationState:
        self._state.simulated_datetime = datetime.now().replace(minute=0, second=0, microsecond=0)
        self._state.weather = settings.DEFAULT_SIMULATION_WEATHER
        self._state.global_crowd_multiplier = settings.SIMULATION_MULTIPLIER_DEFAULT
        self._state.event_flag = False
        self._state.holiday_flag = False
        self._state.city_scope = (
            settings.ALL_CITY_SCOPE_LABEL
            if settings.ALL_CITY_SCOPE_LABEL in self._city_options
            else self._city_options[0]
        )
        self.state_changed.emit(self.get_state())
        return self.get_state()

    def reset_to_now(self) -> SimulationState:
        return self.reset_to_defaults()
