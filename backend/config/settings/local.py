from pathlib import Path

from decouple import config

from .base import *  # noqa: F401, F403

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.sqlite3"),
        "NAME": config("DB_NAME", default=str(BASE_DIR / "test_db.sqlite3")),
        "USER": config("DB_USER", default=""),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default=""),
        "PORT": config("DB_PORT", default=""),
    }
}

# Disable password validators in tests for easier test data creation
AUTH_PASSWORD_VALIDATORS = []

DEBUG = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
