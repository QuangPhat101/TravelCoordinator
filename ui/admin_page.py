from __future__ import annotations

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import settings
from services.crowd_control_service import CrowdControlService
from services.simulation_service import SimulationService, SimulationState


class AdminPage(QWidget):
    def __init__(
        self,
        crowd_service: CrowdControlService,
        simulation_service: SimulationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.crowd_service = crowd_service
        self.simulation_service = simulation_service

        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.datetime_edit.setCalendarPopup(True)

        self.weather_combo = QComboBox()
        self.weather_combo.addItems(settings.SIMULATION_WEATHER_OPTIONS)

        self.city_combo = QComboBox()
        self.city_combo.setMinimumWidth(220)

        self.event_checkbox = QCheckBox("Có sự kiện")
        self.holiday_checkbox = QCheckBox("Ngày nghỉ / lễ")

        self.multiplier_spinbox = QDoubleSpinBox()
        self.multiplier_spinbox.setRange(
            settings.SIMULATION_MULTIPLIER_MIN,
            settings.SIMULATION_MULTIPLIER_MAX,
        )
        self.multiplier_spinbox.setSingleStep(settings.SIMULATION_MULTIPLIER_STEP)
        self.multiplier_spinbox.setDecimals(2)

        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setObjectName("pageMeta")

        self.state_label = QLabel()
        self.state_label.setWordWrap(True)
        self.state_label.setObjectName("pageMeta")

        self.zone_combo = QComboBox()
        self.zone_combo.addItems(list(self.crowd_service.default_zones))

        self.snapshot_level_combo = QComboBox()
        self.snapshot_level_combo.addItems(["20", "35", "50", "65", "80", "95"])
        self.snapshot_level_combo.setCurrentText("50")

        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(["Thời gian", "Khu vực", "Mật độ", "Khuyến nghị"])
        self.history_table.horizontalHeader().setStretchLastSection(True)

        self._build_ui()
        self._load_city_options()
        self._load_state_into_controls()
        self.refresh_history()

        self.simulation_service.state_changed.connect(self._on_simulation_state_changed)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Admin / Simulation")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Điều khiển trạng thái mô phỏng dùng chung cho Dashboard, Map, Planner, Hidden Gem và Chatbot."
        )
        subtitle.setObjectName("pageSubtitle")

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Thời gian giả lập", self.datetime_edit)
        form.addRow("Weather", self.weather_combo)
        form.addRow("City scope", self.city_combo)
        form.addRow("Holiday flag", self.holiday_checkbox)
        form.addRow("Event flag", self.event_checkbox)
        form.addRow("Global crowd multiplier", self.multiplier_spinbox)

        actions = QHBoxLayout()
        apply_button = QPushButton("Áp dụng mô phỏng")
        apply_button.clicked.connect(self.apply_simulation_state)
        reset_button = QPushButton("Reset mặc định")
        reset_button.clicked.connect(self.reset_simulation_state)
        actions.addWidget(apply_button)
        actions.addWidget(reset_button)
        actions.addStretch(1)

        snapshot_row = QHBoxLayout()
        save_button = QPushButton("Lưu snapshot khu vực")
        save_button.clicked.connect(self.save_simulation_snapshot)
        refresh_button = QPushButton("Tải lại lịch sử")
        refresh_button.clicked.connect(self.refresh_history)
        snapshot_row.addWidget(self.zone_combo, stretch=2)
        snapshot_row.addWidget(self.snapshot_level_combo, stretch=1)
        snapshot_row.addWidget(save_button)
        snapshot_row.addWidget(refresh_button)

        snapshot_hint = QLabel(
            "Snapshot khu vực giúp demo phần điều phối thủ công mà không ảnh hưởng tới simulation state toàn cục."
        )
        snapshot_hint.setObjectName("pageMeta")
        snapshot_hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.state_label)
        layout.addWidget(self.feedback_label)
        layout.addWidget(snapshot_hint)
        layout.addLayout(snapshot_row)
        layout.addWidget(self.history_table, stretch=1)

    def _load_city_options(self) -> None:
        city_options = self.simulation_service.get_city_options()
        self.city_combo.clear()
        for city in city_options:
            self.city_combo.addItem(city, city)

    def _load_state_into_controls(self) -> None:
        state = self.simulation_service.get_state()
        self.datetime_edit.setDateTime(QDateTime.fromSecsSinceEpoch(int(state.simulated_datetime.timestamp())))
        self.weather_combo.setCurrentText(state.weather)
        self.holiday_checkbox.setChecked(state.holiday_flag)
        self.event_checkbox.setChecked(state.event_flag)
        self.multiplier_spinbox.setValue(state.global_crowd_multiplier)

        city_index = self.city_combo.findData(state.city_scope)
        if city_index >= 0:
            self.city_combo.setCurrentIndex(city_index)
        self._render_state_summary(state)

    def apply_simulation_state(self) -> None:
        selected_city = self.city_combo.currentData()
        state = self.simulation_service.update_state(
            simulated_datetime=self.datetime_edit.dateTime().toPython(),
            weather=self.weather_combo.currentText(),
            holiday_flag=self.holiday_checkbox.isChecked(),
            event_flag=self.event_checkbox.isChecked(),
            global_crowd_multiplier=self.multiplier_spinbox.value(),
            city_scope=selected_city if isinstance(selected_city, str) else settings.DEFAULT_CITY_SCOPE,
        )
        self.feedback_label.setText(
            "Đã cập nhật simulation state dùng chung. Dashboard và Map sẽ phản ánh ngay; Planner, Hidden Gem và Chatbot sẽ dùng state mới ở lần tương tác tiếp theo."
        )
        self._render_state_summary(state)

    def reset_simulation_state(self) -> None:
        state = self.simulation_service.reset_to_defaults()
        self._load_city_options()
        self._load_state_into_controls()
        self.feedback_label.setText("Đã reset simulation state về mặc định an toàn.")
        self._render_state_summary(state)

    def save_simulation_snapshot(self) -> None:
        zone = self.zone_combo.currentText().strip() or settings.DEFAULT_CITY_SCOPE
        level = int(self.snapshot_level_combo.currentText())
        result = self.crowd_service.save_manual_simulation(zone=zone, level=level)
        self.feedback_label.setText(
            f'Đã lưu snapshot "{result["zone"]}" ở mức {result["level"]}% - {result["recommendation"]}'
        )
        self.refresh_history()

    def refresh_history(self) -> None:
        history = self.crowd_service.recent_simulations(limit=15)
        self.history_table.setRowCount(len(history))

        for row_index, item in enumerate(history):
            self.history_table.setItem(row_index, 0, QTableWidgetItem(str(item["created_at"])))
            self.history_table.setItem(row_index, 1, QTableWidgetItem(str(item["zone"])))
            self.history_table.setItem(row_index, 2, QTableWidgetItem(f'{item["level"]}%'))
            self.history_table.setItem(row_index, 3, QTableWidgetItem(str(item["recommendation"])))

    def _on_simulation_state_changed(self, state: SimulationState) -> None:
        self._load_city_options()
        self._render_state_summary(state)

    def _render_state_summary(self, state: SimulationState | None = None) -> None:
        current_state = state or self.simulation_service.get_state()
        self.state_label.setText(
            f"Simulation state hiện tại: {current_state.simulated_datetime.strftime('%d/%m/%Y %H:%M')} | "
            f"Weather: {current_state.weather} | "
            f"Holiday: {'Có' if current_state.holiday_flag else 'Không'} | "
            f"Event: {'Có' if current_state.event_flag else 'Không'} | "
            f"Hệ số crowd: {current_state.global_crowd_multiplier:.2f} | "
            f"City scope: {current_state.city_scope}"
        )
