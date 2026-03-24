from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, QUrl
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from services.map_service import MapService
from services.simulation_service import SimulationService, SimulationState

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except Exception:  # pragma: no cover - depends on local Qt WebEngine runtime.
    QWebEngineView = None


class MapPage(QWidget):
    def __init__(
        self,
        map_service: MapService,
        simulation_service: SimulationService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.map_service = map_service
        self.simulation_service = simulation_service
        self.city_combo = QComboBox()
        self.city_combo.currentIndexChanged.connect(self._handle_city_changed)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setObjectName("pageMeta")

        if QWebEngineView is not None:
            self.map_view: QWidget = QWebEngineView()
        else:
            fallback_view = QTextBrowser()
            fallback_view.setOpenExternalLinks(True)
            self.map_view = fallback_view

        self._build_ui()
        self._load_city_options()
        if self.simulation_service is not None:
            self.simulation_service.state_changed.connect(self._on_simulation_state_changed)
        self.refresh_map()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Bản đồ")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Map View dùng Leaflet + OpenStreetMap để hiển thị điểm du lịch và crowd level hiện tại."
        )
        subtitle.setObjectName("pageSubtitle")

        controls = QHBoxLayout()
        controls.setSpacing(12)

        city_label = QLabel("City scope")
        city_label.setObjectName("pageSubtitle")
        refresh_button = QPushButton("Làm mới bản đồ")
        refresh_button.clicked.connect(self.refresh_map)

        controls.addWidget(city_label)
        controls.addWidget(self.city_combo, stretch=0)
        controls.addStretch(1)
        controls.addWidget(refresh_button)

        hint_label = QLabel(
            "Màu marker: xanh dương nhạt = thấp, vàng = vừa, cam = cao, đỏ = rất đông."
        )
        hint_label.setObjectName("pageMeta")
        hint_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(controls)
        layout.addWidget(hint_label)
        layout.addWidget(self.info_label)
        layout.addWidget(self.map_view, stretch=1)

    def _load_city_options(self) -> None:
        options = self.map_service.get_available_cities()
        with QSignalBlocker(self.city_combo):
            current_scope = self._current_city_scope()
            self.city_combo.clear()
            for city in options:
                self.city_combo.addItem(city, city)

            target_scope = current_scope if current_scope in options else (options[0] if options else "")
            target_index = self.city_combo.findData(target_scope)
            if target_index >= 0:
                self.city_combo.setCurrentIndex(target_index)

    def refresh_map(self) -> None:
        selected_city = self.city_combo.currentData()
        city_value = selected_city if isinstance(selected_city, str) and selected_city.strip() else None
        context = self.map_service.get_map_context(city=city_value)

        self.info_label.setText(
            f"Đang hiển thị {context['point_count']} địa điểm cho phạm vi {context['selected_city']}."
        )

        html = str(context["html"])
        if QWebEngineView is not None and hasattr(self.map_view, "setHtml"):
            self.map_view.setHtml(html, QUrl("https://local.map/"))
            return

        if isinstance(self.map_view, QTextBrowser):
            self.map_view.setHtml(
                "<div style='font-family:Segoe UI, Arial, sans-serif; padding:18px; color:#16324f;'>"
                "<h3>Chưa bật được QWebEngineView</h3>"
                "<p>Bản đồ Leaflet cần Qt WebEngine để hiển thị tương tác bên trong desktop app.</p>"
                f"<p>Phạm vi hiện tại: <b>{context['selected_city']}</b> với <b>{context['point_count']}</b> địa điểm.</p>"
                "<p>Sau khi cài đầy đủ PySide6 WebEngine, trang này sẽ hiển thị marker OpenStreetMap ngay trong app.</p>"
                "</div>"
            )

    def _handle_city_changed(self) -> None:
        if self.simulation_service is None:
            self.refresh_map()
            return

        selected_city = self.city_combo.currentData()
        if isinstance(selected_city, str) and selected_city != self.simulation_service.city_scope:
            self.simulation_service.update_state(city_scope=selected_city)
        else:
            self.refresh_map()

    def _on_simulation_state_changed(self, state: SimulationState) -> None:
        self._load_city_options()
        current_index = self.city_combo.findData(state.city_scope)
        if current_index >= 0:
            with QSignalBlocker(self.city_combo):
                self.city_combo.setCurrentIndex(current_index)
        self.refresh_map()

    def _current_city_scope(self) -> str:
        if self.simulation_service is not None:
            return self.simulation_service.city_scope
        current_data = self.city_combo.currentData()
        return current_data if isinstance(current_data, str) else ""
