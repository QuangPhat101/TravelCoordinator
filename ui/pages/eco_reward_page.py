from PySide6.QtWidgets import QComboBox, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from services.eco_reward_service import EcoRewardService


class EcoRewardPage(QWidget):
    def __init__(self, reward_service: EcoRewardService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.reward_service = reward_service

        self.points_label = QLabel()
        self.actions_combo = QComboBox()
        self.history_list = QListWidget()

        self._build_ui()
        self._load_actions()
        self.refresh_data()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Eco Reward")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Theo dõi điểm thưởng xanh và lịch sử hành động thân thiện môi trường.")
        subtitle.setObjectName("pageSubtitle")
        self.points_label.setObjectName("pointBadge")

        add_action_button = QPushButton("Ghi nhận hành vi xanh (+10 điểm)")
        add_action_button.clicked.connect(self.add_green_action)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.points_label)
        layout.addWidget(self.actions_combo)
        layout.addWidget(add_action_button)
        layout.addWidget(self.history_list, stretch=1)

    def _load_actions(self) -> None:
        self.actions_combo.clear()
        self.actions_combo.addItems(self.reward_service.available_actions())

    def add_green_action(self) -> None:
        action_name = self.actions_combo.currentText()
        self.reward_service.register_green_action(action_name=action_name)
        self.refresh_data()

    def refresh_data(self) -> None:
        points = self.reward_service.get_points()
        self.points_label.setText(f"Tổng điểm hiện tại: {points}")

        self.history_list.clear()
        for record in self.reward_service.recent_actions(limit=12):
            line = f'{record["created_at"]} | {record["action_name"]} | +{record["points"]} điểm'
            self.history_list.addItem(QListWidgetItem(line))
