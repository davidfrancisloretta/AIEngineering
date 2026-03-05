"""
RAVE AI Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_BASE = os.getenv("FASTAPI_URL", os.getenv("API_URL", "http://localhost:8000"))
API_TIMEOUT = 120  # Ollama model load can take 60+ seconds on first inference

# App Configuration
APP_NAME = "RAVE AI"
APP_VERSION = "1.0.0"

# Theme
THEME_COLOR_PRIMARY = "#1f77b4"
THEME_COLOR_SECONDARY = "#ff7f0e"
THEME_COLOR_SUCCESS = "#2ca02c"
THEME_COLOR_DANGER = "#d62728"
THEME_COLOR_WARNING = "#ff9896"
THEME_COLOR_INFO = "#17becf"

# Environment
ENVIRONMENT = os.getenv("REFLEX_ENV", "dev")
DEBUG = ENVIRONMENT == "dev"

# Reflex Configuration
REFLEX_HOST = os.getenv("REFLEX_HOST", "0.0.0.0")
REFLEX_PORT = int(os.getenv("REFLEX_PORT", "3000"))
