import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from config import settings
from ui.style import load_stylesheet


def create_application(argv: list[str] | None = None) -> tuple[QApplication, MainWindow]:
    """Create QApplication and main window with project styling."""
    args = argv if argv is not None else sys.argv
    app = QApplication(args)
    app.setApplicationName(settings.APP_NAME)
    app.setApplicationDisplayName(settings.APP_NAME)
    app.setStyleSheet(load_stylesheet())

    window = MainWindow()
    return app, window


def run() -> int:
    app, window = create_application()
    window.show()
    return app.exec()
