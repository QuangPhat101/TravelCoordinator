from __future__ import annotations

from datetime import datetime

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.db_service import DBService
from services.crowd_forecast_service import CrowdForecastService
from services.crowd_utils import DashboardAttractionRow, build_dashboard_rows, calculate_dashboard_metrics
from services.data_loader import DataLoader
from services.simulation_service import SimulationService


class DashboardPage(QWidget):
    def __init__(
        self,
        data_loader: DataLoader,
        database_manager: DBService | None = None,
        crowd_forecast_service: CrowdForecastService | None = None,
        simulation_service: SimulationService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.data_loader = data_loader
        self.database_manager = database_manager
        self.crowd_forecast_service = crowd_forecast_service
        self.simulation_service = simulation_service
        self.dashboard_rows: list[DashboardAttractionRow] = []
        self.stat_cards: dict[str, dict[str, QLabel | QFrame]] = {}

        self.updated_label = QLabel()
        self.updated_label.setObjectName("pageMeta")
        self.empty_state_label = QLabel("Đang nạp dữ liệu dashboard...")
        self.total_points_card = self._create_stat_card("Tổng số điểm du lịch", "#2563eb")
        self.busy_points_card = self._create_stat_card("Số điểm đang đông", "#1d4ed8")
        self.hidden_gem_card = self._create_stat_card("Hidden gem tiềm năng", "#3b82f6")
        self.eco_points_card = self._create_stat_card("Tổng eco points hiện tại", "#1e40af")
        self.table = QTableWidget(0, 6)
        self.detail_title = QLabel("Chọn một địa điểm để xem chi tiết")
        self.detail_title.setObjectName("pageTitle")
        self.detail_summary = QLabel("Bảng bên trái sẽ cập nhật thông tin realtime từ dữ liệu mẫu.")
        self.detail_summary.setWordWrap(True)
        self.detail_summary.setObjectName("pageSubtitle")
        self.detail_meta = QLabel()
        self.detail_meta.setWordWrap(True)
        self.detail_meta.setObjectName("pageMeta")
        self.detail_description = QLabel()
        self.detail_description.setWordWrap(True)
        self.detail_description.setObjectName("pageMeta")
        self.detail_tags = QLabel()
        self.detail_tags.setWordWrap(True)
        self.detail_tags.setObjectName("pageMeta")

        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 20, 24, 20)
        root_layout.setSpacing(16)

        header_row = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Bảng điều phối trung tâm cho demo Eco-Travel Coordinator.")
        subtitle.setObjectName("pageSubtitle")

        title_block = QVBoxLayout()
        title_block.setSpacing(4)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)

        refresh_button = QPushButton("Refresh dữ liệu")
        refresh_button.clicked.connect(self.refresh_data)

        header_row.addLayout(title_block)
        header_row.addStretch(1)
        header_row.addWidget(refresh_button)

        root_layout.addLayout(header_row)
        root_layout.addWidget(self.updated_label)
        root_layout.addLayout(self._build_cards_layout())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_table_panel())
        splitter.addWidget(self._build_detail_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root_layout.addWidget(splitter, stretch=1)

    def _build_cards_layout(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)
        layout.addWidget(self.total_points_card, 0, 0)
        layout.addWidget(self.busy_points_card, 0, 1)
        layout.addWidget(self.hidden_gem_card, 0, 2)
        layout.addWidget(self.eco_points_card, 0, 3)
        return layout

    def _build_table_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.NoFrame)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        table_title = QLabel("Danh sách địa điểm")
        table_title.setObjectName("pageSubtitle")

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels(
            ["Tên địa điểm", "Loại hình", "Khu vực", "Crowd score hiện tại", "Mức cảnh báo", "Rating"]
        )
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.itemSelectionChanged.connect(self._handle_selection_changed)

        self.empty_state_label.setObjectName("pageSubtitle")
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(table_title)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.empty_state_label)
        return panel

    def _build_detail_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("dashboardDetailPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        section_title = QLabel("Chi tiết nhanh")
        section_title.setObjectName("pageSubtitle")

        for widget in (self.detail_title, self.detail_summary, self.detail_meta, self.detail_description, self.detail_tags):
            widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(section_title)
        layout.addWidget(self.detail_title)
        layout.addWidget(self.detail_summary)
        layout.addWidget(self.detail_meta)
        layout.addWidget(self.detail_description)
        layout.addWidget(self.detail_tags)
        layout.addStretch(1)
        return panel

    def _create_stat_card(self, title: str, accent_color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("statCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("statCardTitle")
        value_label = QLabel("0")
        value_label.setObjectName("statCardValue")
        value_label.setStyleSheet(f"color: {accent_color};")
        hint_label = QLabel("Đang đồng bộ từ dữ liệu mẫu")
        hint_label.setObjectName("statCardHint")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(hint_label)

        self.stat_cards[title] = {
            "card": card,
            "title_label": title_label,
            "value_label": value_label,
            "hint_label": hint_label,
        }
        return card

    def refresh_data(self) -> None:
        attractions = self._scoped_attractions(self.data_loader.load_attractions())
        crowd_history = self.data_loader.load_crowd_history()
        eco_points = self._load_eco_points()

        if self.crowd_forecast_service is not None:
            self.crowd_forecast_service.refresh_reference_data()
        self.dashboard_rows = build_dashboard_rows(
            attractions,
            crowd_history,
            self.crowd_forecast_service,
        )
        metrics = calculate_dashboard_metrics(self.dashboard_rows, eco_points)

        self._update_card(self.total_points_card, metrics["total_attractions"], "Tổng số điểm trong city scope hiện tại")
        self._update_card(self.busy_points_card, metrics["busy_count"], "Crowd score từ 51 trở lên")
        self._update_card(self.hidden_gem_card, metrics["hidden_gem_count"], "Điểm rating tốt, ít áp lực khách")
        self._update_card(self.eco_points_card, metrics["eco_points"], "Lấy từ database local nếu có")

        self._populate_table()
        self._update_timestamp(crowd_history)

        has_rows = bool(self.dashboard_rows)
        self.empty_state_label.setVisible(not has_rows)
        if has_rows:
            self.empty_state_label.setText("")
            self.table.selectRow(0)
            self._show_row_detail(0)
        else:
            self.empty_state_label.setText("Chưa có dữ liệu phù hợp với city scope hiện tại. Dashboard vẫn hoạt động an toàn.")
            self._show_empty_detail()

    def _scoped_attractions(self, attractions: pd.DataFrame) -> pd.DataFrame:
        if attractions.empty or self.simulation_service is None:
            return attractions

        city_scope = self.simulation_service.city_scope
        if not city_scope or city_scope == settings.ALL_CITY_SCOPE_LABEL:
            return attractions

        city_series = self._resolve_city_series(attractions)
        filtered = attractions.loc[city_series.astype(str).str.casefold() == city_scope.casefold()].copy()
        return filtered if not filtered.empty else attractions

    @staticmethod
    def _resolve_city_series(attractions: pd.DataFrame) -> pd.Series:
        for column_name in ("city", "province", "destination_city"):
            if column_name in attractions.columns:
                return attractions[column_name].fillna(settings.DEFAULT_CITY_SCOPE).astype(str)
        return pd.Series([settings.DEFAULT_CITY_SCOPE] * len(attractions.index), index=attractions.index, dtype="object")

    def _populate_table(self) -> None:
        self.table.clearContents()
        self.table.setRowCount(len(self.dashboard_rows))

        for row_index, row in enumerate(self.dashboard_rows):
            self._set_table_item(row_index, 0, row.name)
            self._set_table_item(row_index, 1, row.category)
            self._set_table_item(row_index, 2, row.area)
            self._set_table_item(row_index, 3, str(row.crowd_score))

            alert_item = self._set_table_item(row_index, 4, row.alert_label)
            alert_item.setForeground(QColor("#ffffff"))
            alert_item.setBackground(QColor(row.alert_color))

            self._set_table_item(row_index, 5, f"{row.rating:.1f}")

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

    def _set_table_item(self, row_index: int, column_index: int, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        if column_index in {3, 4, 5}:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_index, column_index, item)
        return item

    def _handle_selection_changed(self) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            self._show_empty_detail()
            return

        selected_row = selected_items[0].row()
        self._show_row_detail(selected_row)

    def _show_row_detail(self, row_index: int) -> None:
        if row_index < 0 or row_index >= len(self.dashboard_rows):
            self._show_empty_detail()
            return

        row = self.dashboard_rows[row_index]
        self.detail_title.setText(row.name)
        self.detail_summary.setText(
            f"Loại hình: {row.category} | Khu vực: {row.area}\n"
            f"Crowd score hiện tại: {row.crowd_score} | Cấp độ: {row.crowd_level} | Cảnh báo: {row.alert_label} | Rating: {row.rating:.1f}"
        )
        self.detail_meta.setText(
            f"Giờ mở cửa: {row.opening_hours or 'Chưa rõ'}\n"
            f"Giá vé: {row.ticket_price or 'Chưa cập nhật'}\n"
            f"Sức chứa ước tính: {row.estimated_capacity}\n"
            f"Popularity score: {row.popularity_score}\n"
            f"Loại không gian: {row.indoor_outdoor or 'Chưa rõ'}\n"
            f"Khung giờ nên đi: {row.best_visit_label}\n"
            f"Dự báo 4 giờ tới: {row.forecast_preview}\n"
            f"Cập nhật crowd gần nhất: {row.last_updated}"
        )
        self.detail_description.setText(
            f"Mô tả: {row.description or 'Chưa có mô tả.'}\n"
            f"Giải thích crowd: {row.crowd_explanation}"
        )
        self.detail_tags.setText(f"Tags: {row.tags or 'Không có'}")

    def _show_empty_detail(self) -> None:
        self.detail_title.setText("Chưa có địa điểm được chọn")
        self.detail_summary.setText("Khi bạn chọn một dòng trong bảng, thông tin chi tiết sẽ hiển thị ở đây.")
        self.detail_meta.setText("Không có dữ liệu chi tiết để hiển thị.")
        self.detail_description.setText("Mô tả: Chưa có dữ liệu.")
        self.detail_tags.setText("Tags: Không có")

    def _update_card(self, card: QFrame, value: int, hint_text: str) -> None:
        matched_widgets = next(
            (widgets for widgets in self.stat_cards.values() if widgets["card"] is card),
            None,
        )
        if matched_widgets is None:
            return

        matched_widgets["value_label"].setText(str(value))
        matched_widgets["hint_label"].setText(hint_text)

    def _update_timestamp(self, crowd_history: pd.DataFrame) -> None:
        refreshed_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        latest_data_time = "Chưa có dữ liệu crowd"
        simulation_text = ""
        if not crowd_history.empty and "timestamp" in crowd_history.columns:
            valid_timestamps = crowd_history["timestamp"].dropna()
            if not valid_timestamps.empty:
                latest_timestamp = valid_timestamps.max()
                latest_data_time = latest_timestamp.strftime("%d/%m/%Y %H:%M")
        if self.crowd_forecast_service is not None:
            simulation_state = self.crowd_forecast_service.simulation_service.get_state()
            simulation_text = (
                f" | Mô phỏng: {simulation_state.simulated_datetime.strftime('%d/%m/%Y %H:%M')}"
                f" | Weather: {simulation_state.weather}"
                f" | Event: {'Có' if simulation_state.event_flag else 'Không'}"
                f" | Holiday: {'Có' if simulation_state.holiday_flag else 'Không'}"
                f" | Hệ số: {simulation_state.global_crowd_multiplier:.2f}"
                f" | City scope: {simulation_state.city_scope}"
            )
        self.updated_label.setText(
            f"Dữ liệu dashboard làm mới lúc: {refreshed_at} | Crowd history mới nhất: {latest_data_time}{simulation_text}"
        )

    def _load_eco_points(self) -> int:
        if self.database_manager is None:
            return 0
        try:
            return self.database_manager.get_total_eco_points(settings.DEFAULT_USER_ID)
        except Exception:
            return 0
