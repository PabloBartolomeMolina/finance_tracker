'''
    File Name: db_manager.py
    Version: 2.0.0
    Date: 30/11/2025
    Author: Pablo Bartolomé Molina
'''

import sqlite3
from pathlib import Path
import logging

import config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.BASE_DIR / "data" / "finance_tracker.db"

    def ensure_database(self) -> None:
        """
        Ensure the configured SQLite database file exists.
        If missing, create the file and initialize a minimal schema (transactions & categories).
        Safe to call multiple times.
        """
        db_path = Path(getattr(config, "DATABASE_PATH", None))
        logger.debug("Ensuring database exists at %s", db_path)

        # Ensure parent directories exist
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # If file already exists, nothing to do
        if db_path.exists():
            logger.debug("Database file already exists: %s", db_path)
            return

        # Create and initialize the database
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            # Minimal, idempotent schema
            cur.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL,
                    category_id INTEGER,
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                );
            """)
            conn.commit()
            conn.close()
            logger.info("Created and initialized database at %s", db_path)
        except Exception:
            logger.exception("Failed to create/initialize database at %s", db_path)
            raise
