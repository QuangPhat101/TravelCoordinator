from app.main_window import MainWindow
from config import settings
from services.chatbot_service import ChatbotService
from services.sample_data_service import SampleDataService


def test_main_window_loads(qt_app) -> None:
    window = MainWindow()
    assert settings.APP_NAME in window.windowTitle()
    assert window.sidebar_widget.item_count() == len(settings.SIDEBAR_ITEMS)
    assert window.page_stack.count() == len(settings.SIDEBAR_ITEMS)
    assert settings.ATTRACTIONS_SAMPLE_FILE.exists()
    assert settings.CROWD_HISTORY_SAMPLE_FILE.exists()


def test_chatbot_service_local_response() -> None:
    service = ChatbotService(SampleDataService())
    response = service.respond("Địa điểm nào đang đông?")
    assert "đông" in response.casefold()
