from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.hidden_gem_service import HiddenGemService
from services.simulation_service import SimulationService, SimulationState


class HiddenGemPage(QWidget):
    def __init__(
        self,
        hidden_gem_service: HiddenGemService,
        simulation_service: SimulationService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.hidden_gem_service = hidden_gem_service
        self.simulation_service = simulation_service

        self.source_combo = QComboBox()
        self.preference_input = QLineEdit()
        self.preference_input.setPlaceholderText("Ví dụ: gần, ít đông, thiên nhiên")
        self.result_list = QListWidget()
        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setObjectName("pageMeta")

        self._build_ui()
        self._load_source_options()
        self.recommend_hidden_gems()

        if self.simulation_service is not None:
            self.simulation_service.state_changed.connect(self._on_simulation_state_changed)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Hidden Gem")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Nếu một điểm đang đông, hệ thống sẽ gợi ý các địa điểm tương tự nhưng ít đông hơn trong phạm vi mô phỏng hiện tại."
        )
        subtitle.setObjectName("pageSubtitle")

        form = QFormLayout()
        form.addRow("Địa điểm gốc", self.source_combo)
        form.addRow("Ưu tiên thêm", self.preference_input)

        recommend_button = QPushButton("Đề xuất Hidden Gem")
        recommend_button.clicked.connect(self.recommend_hidden_gems)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(form)
        layout.addWidget(recommend_button)
        layout.addWidget(self.feedback_label)
        layout.addWidget(self.result_list, stretch=1)

    def _load_source_options(self) -> None:
        self.source_combo.clear()
        options = self.hidden_gem_service.get_source_options()
        for attraction_id, name in options:
            self.source_combo.addItem(name, attraction_id)

        if not options:
            self.feedback_label.setText("Chưa có dữ liệu địa điểm phù hợp trong city scope hiện tại để tạo gợi ý Hidden Gem.")

    def recommend_hidden_gems(self) -> None:
        self.result_list.clear()
        attraction_id = self.source_combo.currentData()
        if not isinstance(attraction_id, str) or not attraction_id:
            self.feedback_label.setText("Chưa chọn được địa điểm gốc phù hợp.")
            return

        preference = self.preference_input.text().strip() or None
        recommendations = self.hidden_gem_service.get_hidden_gems_for(
            attraction_id=attraction_id,
            preference=preference,
            top_k=3,
        )

        if not recommendations:
            self.feedback_label.setText("Chưa tìm được hidden gem phù hợp với điểm gốc hiện tại.")
            return

        self.feedback_label.setText("Đã tìm thấy hidden gem phù hợp trong phạm vi mô phỏng hiện tại.")
        for index, item in enumerate(recommendations, start=1):
            text = (
                f"{index}. {item['name']}\n"
                f"Category: {item['category']}\n"
                f"Khoảng cách ước tính: {item['distance_km']:.1f} km\n"
                f"Crowd score hiện tại: {item['crowd_score']}\n"
                f"Rating: {item['rating']:.1f}\n"
                f"Lý do gợi ý: {item['reason']}"
            )
            self.result_list.addItem(QListWidgetItem(text))

    def _on_simulation_state_changed(self, state: SimulationState) -> None:
        self._load_source_options()
        self.result_list.clear()
        self.feedback_label.setText(
            f"Đã cập nhật city scope sang {state.city_scope}. Hãy chọn lại điểm gốc để xem Hidden Gem phù hợp."
        )
