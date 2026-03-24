from pathlib import Path

APP_NAME = "Eco-Travel Coordinator"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 760

DEMO_CITY = "Đà Nẵng"
ALL_CITY_SCOPE_LABEL = "Tất cả"
DEFAULT_CITY_SCOPE = DEMO_CITY

DEFAULT_SIMULATION_WEATHER = "nắng đẹp"
SIMULATION_WEATHER_OPTIONS = [
    "nắng đẹp",
    "âm u",
    "mưa",
    "nóng cao điểm",
    "dễ chịu",
]
SIMULATION_MULTIPLIER_MIN = 0.5
SIMULATION_MULTIPLIER_MAX = 2.0
SIMULATION_MULTIPLIER_DEFAULT = 1.0
SIMULATION_MULTIPLIER_STEP = 0.05

DEFAULT_MAP_CITY = DEMO_CITY
DEFAULT_MAP_CENTER_LAT = 16.0544
DEFAULT_MAP_CENTER_LON = 108.2022
DEFAULT_MAP_ZOOM = 12

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = BASE_DIR / "database"
ASSETS_DIR = BASE_DIR / "assets"
SCRIPTS_DIR = BASE_DIR / "scripts"
NOTEBOOKS_DIR = BASE_DIR / "notebooks"
MODEL_ARTIFACTS_DIR = BASE_DIR / "models_artifacts"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
TRAINING_DATA_DIR = DATA_DIR / "training"

DATABASE_PATH = DATABASE_DIR / "eco_travel.db"
DATABASE_SCHEMA_FILE = DATABASE_DIR / "schema.sql"
HIDDEN_GEMS_FILE = DATA_DIR / "hidden_gems.json"
STYLESHEET_FILE = ASSETS_DIR / "styles" / "main.qss"
ATTRACTIONS_SAMPLE_FILE = SAMPLE_DATA_DIR / "attractions.csv"
CROWD_HISTORY_SAMPLE_FILE = SAMPLE_DATA_DIR / "crowd_history.csv"
TRANSPORT_OPTIONS_SAMPLE_FILE = SAMPLE_DATA_DIR / "transport_options.csv"
ECO_REWARDS_SAMPLE_FILE = SAMPLE_DATA_DIR / "eco_rewards.csv"
FAQ_KNOWLEDGE_BASE_FILE = SAMPLE_DATA_DIR / "faq_knowledge_base.csv"

SAMPLE_DATA_FILES = {
    "attractions": ATTRACTIONS_SAMPLE_FILE,
    "crowd_history": CROWD_HISTORY_SAMPLE_FILE,
    "transport_options": TRANSPORT_OPTIONS_SAMPLE_FILE,
    "eco_rewards": ECO_REWARDS_SAMPLE_FILE,
    "faq_knowledge_base": FAQ_KNOWLEDGE_BASE_FILE,
}

DEFAULT_USER_ID = "local_user_vn"
DEFAULT_USER_DISPLAY_NAME = "Người dùng Demo"
DEFAULT_USER_EMAIL = "demo.user@eco-travel.local"
DEFAULT_USER_AVATAR_PATH = ""

SIDEBAR_ITEMS = [
    ("dashboard", "Dashboard"),
    ("map", "Bản đồ"),
    ("planning", "Lập kế hoạch"),
    ("hidden_gem", "Hidden Gem"),
    ("eco_reward", "Eco Reward"),
    ("chatbot", "Chatbot"),
    ("admin_simulation", "Admin Simulation"),
]

CROWD_TARGET_COLUMN = "crowd_score"
CROWD_TRAINING_DATA_FILE = TRAINING_DATA_DIR / "crowd_training_dataset.csv"
CLEANED_TRAINING_DATA_FILE = TRAINING_DATA_DIR / "cleaned_training_data.csv"
CROWD_MODEL_FILE = MODEL_ARTIFACTS_DIR / "crowd_forecast_model.pkl"
CROWD_PREPROCESSOR_FILE = MODEL_ARTIFACTS_DIR / "crowd_preprocessor.pkl"
CROWD_METADATA_FILE = MODEL_ARTIFACTS_DIR / "crowd_model_metadata.json"
CROWD_MODEL_METRICS_FILE = MODEL_ARTIFACTS_DIR / "crowd_forecast_metrics.json"
CROWD_MODEL_CANDIDATES = ["random_forest", "xgboost"]
CROWD_FEATURE_COLUMNS = [
    "attraction_id",
    "city",
    "category",
    "popularity_score",
    "estimated_capacity",
    "hour",
    "day_of_week",
    "weather",
    "holiday_flag",
    "event_flag",
    "historical_crowd_score",
    "indoor_outdoor",
    "temperature",
    "rain_flag",
]
