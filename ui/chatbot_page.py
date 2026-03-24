from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.chatbot_service import ChatbotService


class ChatbotPage(QWidget):
    def __init__(self, chatbot_service: ChatbotService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.chatbot_service = chatbot_service

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Nhập câu hỏi về crowd, hidden gem, planner hoặc eco reward...")
        self.status_label = QLabel("Chatbot chạy hoàn toàn offline, dùng rule-based + retrieval từ dữ liệu local.")
        self.status_label.setWordWrap(True)

        self._build_ui()
        self._append_assistant(self.chatbot_service.build_welcome_message())

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Chatbot Hybrid")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Trợ lý local cho dashboard, hidden gem, planner và eco reward.")
        subtitle.setObjectName("pageSubtitle")

        self.chat_history.setPlaceholderText("Hội thoại sẽ hiển thị ở đây.")

        input_row = QHBoxLayout()
        send_button = QPushButton("Gửi")
        send_button.clicked.connect(self._handle_send)
        self.user_input.returnPressed.connect(self._handle_send)

        input_row.addWidget(self.user_input, stretch=1)
        input_row.addWidget(send_button)

        tips = QLabel(
            "Gợi ý nhanh: 'Địa điểm nào đang đông?', 'Nên đi lúc mấy giờ?', 'Vì sao route này được chọn?'"
        )
        tips.setObjectName("pageSubtitle")
        tips.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.status_label)
        layout.addWidget(tips)
        layout.addWidget(self.chat_history, stretch=1)
        layout.addLayout(input_row)

    def _handle_send(self) -> None:
        user_message = self.user_input.text().strip()
        if not user_message:
            return

        self._append_user(user_message)
        response = self.chatbot_service.respond(user_message)
        self._append_assistant(response)
        self.user_input.clear()

    def _append_user(self, text: str) -> None:
        self.chat_history.append(f"<p><b>Bạn:</b> {escape(text)}</p>")
        self.chat_history.moveCursor(self.chat_history.textCursor().MoveOperation.End)

    def _append_assistant(self, text: str) -> None:
        safe_text = escape(text).replace("\n", "<br>")
        self.chat_history.append(f"<p><b>Trợ lý:</b><br>{safe_text}</p>")
        self.chat_history.moveCursor(self.chat_history.textCursor().MoveOperation.End)
        self.chat_history.setAlignment(Qt.AlignmentFlag.AlignLeft)
