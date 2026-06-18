from pathlib import Path

from .base import *  # noqa: F401, F403

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Use SQLite for local development and testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",
    }
}

# Disable password validators in tests for easier test data creation
AUTH_PASSWORD_VALIDATORS = []

DEBUG = True
