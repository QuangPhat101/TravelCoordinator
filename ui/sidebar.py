from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class Sidebar(QWidget):
    """Navigation sidebar for switching pages."""

    navigation_requested = Signal(str)

    def __init__(self, items: Sequence[tuple[str, str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items = list(items)
        self.menu = QListWidget()
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("sidebar")
        self.setMinimumWidth(240)
        self.setMaximumWidth(260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        brand = QLabel("Eco Travel\nCoordinator")
        brand.setObjectName("sidebarBrand")
        brand.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(brand)

        self.menu.setObjectName("sidebarMenu")
        self.menu.setSpacing(6)
        for key, label in self._items:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.menu.addItem(item)

        self.menu.currentItemChanged.connect(self._on_item_changed)
        layout.addWidget(self.menu, stretch=1)

        if self.menu.count() > 0:
            self.menu.setCurrentRow(0)

    def _on_item_changed(self, current: QListWidgetItem | None) -> None:
        if current is None:
            return
        page_key = current.data(Qt.ItemDataRole.UserRole)
        if isinstance(page_key, str):
            self.navigation_requested.emit(page_key)

    def item_count(self) -> int:
        return self.menu.count()

    def item_text(self, index: int) -> str:
        item = self.menu.item(index)
        return item.text() if item is not None else ""
