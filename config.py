'''
    File Name: config.py
    Version: 1.1.0
    Date: 25/10/2025
    Author: Pablo Bartolomé Molina
'''

from pathlib import Path
import logging

# Project paths & files
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_FILENAME = "finance.db"
DATABASE_PATH = DATA_DIR / DB_FILENAME   # Path object
SQLITE_URI = f"sqlite:///{DATABASE_PATH}"

# App metadata
APP_NAME = "Finance Tracker"
APP_VERSION = "1.1.0"

# UI / formatting
DEFAULT_CURRENCY = "EUR"
DATE_FORMAT = "%Y-%m-%d"
STYLESHEET_PATH = BASE_DIR / "resources" / "styles.qss"

# Defaults
DEFAULT_CATEGORIES = [
    "Salary", "Rent", "Food", "Transport", "Entertainment", "Utilities", "Other"
]

# Logging (simple default; modules can call logging.basicConfig(**config))
LOGGING_CONFIG = {
    "level": logging.INFO,
    "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
}

# Helpers
def ensure_data_dir():
    """
    Ensure the data directory exists. Database creation should be handled
    by the database manager (see `database.db_manager.DatabaseManager`).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
