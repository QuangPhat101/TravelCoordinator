from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import settings
from services.eco_reward_service import EcoRewardService
from services.route_optimizer import RouteOptimizer
from services.simulation_service import SimulationService, SimulationState

if TYPE_CHECKING:
    from services.chatbot_service import ChatbotService


class PlanningPage(QWidget):
    def __init__(
        self,
        route_optimizer: RouteOptimizer,
        reward_service: EcoRewardService,
        chatbot_service: ChatbotService | None = None,
        simulation_service: SimulationService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.route_optimizer = route_optimizer
        self.reward_service = reward_service
        self.chatbot_service = chatbot_service
        self.simulation_service = simulation_service
        self.current_route_result: dict[str, Any] | None = None

        self.origin_combo = QComboBox()
        self.destination_combo = QComboBox()
        self.preference_combo = QComboBox()
        self.preference_combo.addItems(["văn hóa", "thiên nhiên", "ẩm thực", "check-in", "thư giãn", "lịch sử"])
        self.transport_combo = QComboBox()
        self.transport_combo.addItems(["tự động", "đi bộ", "xe đạp", "xe bus", "taxi"])
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["ít đông nhất", "xanh nhất", "nhanh nhất", "cân bằng"])

        self.best_route_text = QTextEdit()
        self.best_route_text.setReadOnly(True)
        self.alternative_list = QListWidget()
        self.reward_preview_label = QLabel()
        self.reward_preview_label.setWordWrap(True)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("pageMeta")
        self.reward_button = QPushButton("Nhận Eco Reward")
        self.reward_button.setEnabled(False)

        self._build_ui()
        self._load_attraction_options()

        if self.simulation_service is not None:
            self.simulation_service.state_changed.connect(self._on_simulation_state_changed)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Lập kế hoạch")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Chọn điểm đi, điểm đến, mode và chiến lược tối ưu để hệ thống đề xuất tuyến tốt nhất cùng Eco Reward."
        )
        subtitle.setObjectName("pageSubtitle")

        form = QFormLayout()
        form.addRow("Điểm xuất phát", self.origin_combo)
        form.addRow("Điểm đến", self.destination_combo)
        form.addRow("Sở thích", self.preference_combo)
        form.addRow("Mode di chuyển", self.transport_combo)
        form.addRow("Chiến lược tối ưu", self.strategy_combo)

        action_row = QHBoxLayout()
        propose_button = QPushButton("Đề xuất tuyến")
        propose_button.clicked.connect(self.propose_route)
        self.reward_button.clicked.connect(self.grant_reward)
        action_row.addWidget(propose_button)
        action_row.addWidget(self.reward_button)
        action_row.addStretch(1)

        best_title = QLabel("Tuyến tốt nhất")
        best_title.setObjectName("pageSubtitle")
        alternative_title = QLabel("Phương án thay thế")
        alternative_title.setObjectName("pageSubtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(form)
        layout.addLayout(action_row)
        layout.addWidget(self.status_label)
        layout.addWidget(best_title)
        layout.addWidget(self.best_route_text, stretch=1)
        layout.addWidget(self.reward_preview_label)
        layout.addWidget(alternative_title)
        layout.addWidget(self.alternative_list, stretch=1)

    def _load_attraction_options(self) -> None:
        options = self.route_optimizer.get_attraction_options()
        self.origin_combo.clear()
        self.destination_combo.clear()

        for attraction_id, name in options:
            self.origin_combo.addItem(name, attraction_id)
            self.destination_combo.addItem(name, attraction_id)

        if len(options) > 1:
            self.origin_combo.setCurrentIndex(0)
            self.destination_combo.setCurrentIndex(1)

    def propose_route(self) -> None:
        origin_id = self.origin_combo.currentData()
        destination_id = self.destination_combo.currentData()
        if not isinstance(origin_id, str) or not isinstance(destination_id, str):
            self.status_label.setText("Chưa có dữ liệu điểm đi hoặc điểm đến trong city scope hiện tại.")
            self.reward_button.setEnabled(False)
            return

        route_result = self.route_optimizer.optimize_route(
            origin_id_or_area=origin_id,
            destination_id=destination_id,
            preference=self.preference_combo.currentText(),
            transport_mode=self.transport_combo.currentText(),
            strategy=self.strategy_combo.currentText(),
        )
        self.current_route_result = route_result
        if self.chatbot_service is not None:
            self.chatbot_service.set_last_planner_result(route_result)
        self.reward_button.setEnabled(route_result.get("best_route") is not None)
        self._render_route_result(route_result)

    def grant_reward(self) -> None:
        if not self.current_route_result or self.current_route_result.get("best_route") is None:
            self.status_label.setText("Chưa có tuyến hợp lệ để nhận Eco Reward.")
            return

        best_route = self.current_route_result["best_route"]
        reward_result = self.reward_service.grant_reward(
            user_id=settings.DEFAULT_USER_ID,
            route_result=self.current_route_result,
            reason=(
                f"Lập kế hoạch tuyến {best_route['origin_name']} -> "
                f"{best_route['destination_name']} bằng {best_route['transport_mode']}"
            ),
        )
        self.reward_preview_label.setText(
            f"Đã cộng {reward_result['total_reward_points']} điểm. "
            f"Tổng ví hiện tại: {reward_result['wallet_total']} điểm."
        )
        self.status_label.setText("Eco Reward đã được lưu vào SQLite local. Dashboard sẽ thấy điểm mới khi refresh.")
        self.reward_button.setEnabled(False)

    def _render_route_result(self, route_result: dict[str, Any]) -> None:
        self.alternative_list.clear()
        best_route = route_result.get("best_route")
        if best_route is None:
            self.best_route_text.setPlainText(route_result.get("explanation", "Chưa tìm được tuyến phù hợp."))
            self.reward_preview_label.setText("Chưa có route để tính Eco Reward.")
            self.status_label.setText("Hệ thống chưa tìm được tuyến tối ưu với dữ liệu hiện tại.")
            return

        hidden_gem_suggestion = route_result.get("hidden_gem_suggestion")
        reward_preview = self.reward_service.calculate_reward(route_result)
        best_route_text = (
            f"Tuyến: {best_route['route_name']}\n"
            f"Thời gian di chuyển: {best_route['travel_time']} phút\n"
            f"Quãng đường: {best_route['distance_km']:.1f} km\n"
            f"Carbon footprint: {best_route['estimated_carbon_g']} g CO2\n"
            f"Crowd score tại điểm đến: {best_route['crowd_score_destination']}\n"
            f"Eco score: {best_route['eco_score']}\n"
            f"Route score: {best_route['route_score']}\n"
            f"Gợi ý giờ khởi hành: {best_route['suggested_departure_time']}\n"
            f"Giải thích: {best_route['explanation']}"
        )
        if hidden_gem_suggestion:
            best_route_text += (
                f"\nHidden Gem gần đó: {hidden_gem_suggestion['name']} "
                f"({hidden_gem_suggestion['distance_km']:.1f} km, crowd {hidden_gem_suggestion['crowd_score']})"
            )
        self.best_route_text.setPlainText(best_route_text)

        self.reward_preview_label.setText(
            f"Reward preview: +{reward_preview['total_reward_points']} điểm | "
            f"Mode: {reward_preview['mode_points']} | Hidden Gem: {reward_preview['hidden_gem_bonus']} | "
            f"Giờ thấp điểm: {reward_preview['low_peak_bonus']} | Eco score bonus: {reward_preview['eco_score_bonus']}"
        )
        self.status_label.setText(
            f"Đã tạo route tối ưu trong city scope {route_result.get('city_scope', settings.ALL_CITY_SCOPE_LABEL)}."
        )

        for index, alternative in enumerate(route_result.get("alternative_routes", []), start=1):
            text = (
                f"{index}. {alternative['route_name']}\n"
                f"Thời gian: {alternative['travel_time']} phút | "
                f"Quãng đường: {alternative['distance_km']:.1f} km | "
                f"Carbon: {alternative['estimated_carbon_g']} g | "
                f"Crowd điểm đến: {alternative['crowd_score_destination']} | "
                f"Eco score: {alternative['eco_score']}\n"
                f"Giải thích: {alternative['explanation']}"
            )
            self.alternative_list.addItem(QListWidgetItem(text))

    def _on_simulation_state_changed(self, state: SimulationState) -> None:
        self._load_attraction_options()
        self.current_route_result = None
        self.best_route_text.clear()
        self.alternative_list.clear()
        self.reward_preview_label.setText("")
        self.reward_button.setEnabled(False)
        self.status_label.setText(
            f"Đã cập nhật city scope sang {state.city_scope}. Hãy đề xuất lại tuyến để dùng simulation state mới."
        )
