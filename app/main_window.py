from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from config import settings
from database.db_service import DBService
from services.chatbot_service import ChatbotService
from services.crowd_control_service import CrowdControlService
from services.crowd_forecast_service import CrowdForecastService
from services.data_loader import DataLoader
from services.eco_reward_service import EcoRewardService
from services.hidden_gem_service import HiddenGemService
from services.intent_router import IntentRouter
from services.map_service import MapService
from services.retrieval_service import RetrievalService
from services.route_optimizer import RouteOptimizer
from services.sample_data_service import SampleDataService
from services.simulation_service import SimulationService, SimulationState
from services.user_service import UserService
from ui.dashboard_page import DashboardPage
from ui.pages import (
    AdminSimulationPage,
    ChatbotPage,
    EcoRewardPage,
    HiddenGemPage,
    MapPage,
    PlanningPage,
)
from ui.sidebar import Sidebar


class MainWindow(QMainWindow):
    """Main shell window with sidebar navigation and stacked pages."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{settings.APP_NAME} | Eco-Travel Coordinator & Crowd Control")
        self.resize(settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)

        self.db_service = DBService()
        self.user_service = UserService(self.db_service)
        self.current_user = self.user_service.bootstrap_local_user()
        self.data_loader = DataLoader()
        self.sample_data_service = SampleDataService()
        self.simulation_service = SimulationService()
        self.crowd_forecast_service = CrowdForecastService(self.data_loader, self.simulation_service)
        self.hidden_gem_service = HiddenGemService(
            self.data_loader,
            self.crowd_forecast_service,
            self.simulation_service,
        )
        self.route_optimizer = RouteOptimizer(
            self.data_loader,
            self.crowd_forecast_service,
            self.hidden_gem_service,
            self.simulation_service,
        )
        self.map_service = MapService(
            data_loader=self.data_loader,
            crowd_forecast_service=self.crowd_forecast_service,
            simulation_service=self.simulation_service,
            default_city=settings.DEFAULT_MAP_CITY,
        )
        self.simulation_service.set_city_options(self.map_service.get_available_cities())

        self.crowd_service = CrowdControlService(
            self.db_service,
            self.sample_data_service,
            self.crowd_forecast_service,
        )
        self.reward_service = EcoRewardService(self.db_service, self.sample_data_service)
        self.intent_router = IntentRouter()
        self.retrieval_service = RetrievalService(
            data_loader=self.data_loader,
            crowd_forecast_service=self.crowd_forecast_service,
            hidden_gem_service=self.hidden_gem_service,
            eco_reward_service=self.reward_service,
            simulation_service=self.simulation_service,
        )
        self.chatbot_service = ChatbotService(
            data_loader=self.data_loader,
            crowd_forecast_service=self.crowd_forecast_service,
            hidden_gem_service=self.hidden_gem_service,
            eco_reward_service=self.reward_service,
            intent_router=self.intent_router,
            retrieval_service=self.retrieval_service,
        )

        self.pages: dict[str, QWidget] = {}
        self.sidebar_widget: Sidebar
        self.page_stack: QStackedWidget

        self._build_layout()
        self._build_pages()
        self._wire_events()
        self._connect_simulation_updates()
        if self.current_user is not None:
            self.statusBar().showMessage(f"Sẵn sàng điều phối du lịch xanh cho {self.current_user.display_name}.")
        else:
            self.statusBar().showMessage("Sẵn sàng điều phối du lịch xanh.")

    def _build_layout(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar_widget = Sidebar(settings.SIDEBAR_ITEMS)
        self.page_stack = QStackedWidget()

        root_layout.addWidget(self.sidebar_widget, stretch=0)
        root_layout.addWidget(self.page_stack, stretch=1)

    def _build_pages(self) -> None:
        page_definitions = [
            (
                "dashboard",
                DashboardPage(
                    self.data_loader,
                    self.db_service,
                    self.crowd_forecast_service,
                    self.simulation_service,
                ),
            ),
            ("map", MapPage(self.map_service, self.simulation_service)),
            ("planning", PlanningPage(self.route_optimizer, self.reward_service, self.chatbot_service, self.simulation_service)),
            ("hidden_gem", HiddenGemPage(self.hidden_gem_service, self.simulation_service)),
            ("eco_reward", EcoRewardPage(self.reward_service)),
            ("chatbot", ChatbotPage(self.chatbot_service)),
            ("admin_simulation", AdminSimulationPage(self.crowd_service, self.simulation_service)),
        ]

        for page_key, page_widget in page_definitions:
            self.pages[page_key] = page_widget
            self.page_stack.addWidget(page_widget)

        default_page_key = settings.SIDEBAR_ITEMS[0][0]
        self._switch_page(default_page_key)

    def _wire_events(self) -> None:
        self.sidebar_widget.navigation_requested.connect(self._switch_page)

    def _connect_simulation_updates(self) -> None:
        self.simulation_service.state_changed.connect(self._handle_simulation_state_changed)

    def _handle_simulation_state_changed(self, state: SimulationState) -> None:
        dashboard_page = self.pages.get("dashboard")
        if isinstance(dashboard_page, DashboardPage):
            dashboard_page.refresh_data()

        self.statusBar().showMessage(
            f"Mô phỏng cập nhật: {state.simulated_datetime.strftime('%d/%m %H:%M')} | "
            f"{state.weather} | city scope: {state.city_scope} | hệ số: {state.global_crowd_multiplier:.2f}"
        )

    def _switch_page(self, page_key: str) -> None:
        page_widget = self.pages.get(page_key)
        if page_widget is None:
            return
        self.page_stack.setCurrentWidget(page_widget)
        self.statusBar().showMessage(f"Đang mở trang: {page_key}")
