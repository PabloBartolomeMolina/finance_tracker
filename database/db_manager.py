'''
    File Name: db_manager.py
    Version: 2.0.0
    Date: 30/11/2025
    Author: Pablo Bartolomé Molina
'''

import sqlite3
from pathlib import Path
import logging
from typing import Optional, List, Dict, Any
import csv

import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: Path = None):
        # prefer explicit path, otherwise config value or sensible default
        if db_path is not None:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(getattr(config, "DATABASE_PATH", "")) or (config.BASE_DIR / "data" / "finance_tracker.db")

    def _connect(self):
        """Return a new sqlite3 connection to the configured DB path."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(self.db_path))

    def ensure_database(self) -> None:
        """
        Ensure the configured SQLite database file exists and initialize schema.
        Safe to call multiple times.
        """
        logger.debug("Ensuring database exists at %s", self.db_path)

        # If file already exists, nothing to do
        if self.db_path.exists():
            logger.debug("Database file already exists: %s", self.db_path)
            return

        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    description TEXT,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL,
                    category_id INTEGER,
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                );
                """
            )
            conn.commit()
            conn.close()
            logger.info("Created and initialized database at %s", self.db_path)
        except Exception:
            logger.exception("Failed to create/initialize database at %s", self.db_path)
            raise

    # --- Category helpers ---
    def fetch_categories(self) -> List[Dict[str, Any]]:
        """Return list of categories as dicts: [{'id': int, 'name': str}, ...]"""
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM categories ORDER BY name")
            rows = cur.fetchall()
            conn.close()
            return [{"id": r[0], "name": r[1]} for r in rows]
        except Exception:
            logger.exception("Failed fetching categories")
            return []

    def _ensure_category(self, name: Optional[str]) -> Optional[int]:
        """Ensure a category with `name` exists. Return its id or None."""
        if not name:
            return None
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("SELECT id FROM categories WHERE name = ?", (name,))
            row = cur.fetchone()
            if row:
                cid = row[0]
            else:
                cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
                cid = cur.lastrowid
                conn.commit()
            conn.close()
            return cid
        except Exception:
            logger.exception("Failed ensuring category %s", name)
            return None

    # --- Transaction CRUD ---
    def fetch_transaction_by_id(self, tx_id: int) -> Optional[Dict[str, Any]]:
        """Return a single transaction dict or None if not found."""
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT t.id, t.description, t.amount, t.date, c.name
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.id = ?
                """,
                (tx_id,)
            )
            row = cur.fetchone()
            conn.close()
            if not row:
                return None
            return {"id": row[0], "description": row[1], "amount": row[2], "date": row[3], "category": row[4]}
        except Exception:
            logger.exception("Failed fetching transaction by id %s", tx_id)
            return None

    def fetch_transactions(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch transactions with optional filters.

        Supported filters: 'category' (name), 'start_date' (YYYY-MM-DD), 'end_date' (YYYY-MM-DD).
        Returns list of dicts with keys: id, description, amount, date, category.
        """
        filters = filters or {}
        params: List[Any] = []
        where_clauses: List[str] = []

        if "category" in filters and filters["category"]:
            where_clauses.append("c.name = ?")
            params.append(filters["category"])
        if "start_date" in filters and filters["start_date"]:
            where_clauses.append("t.date >= ?")
            params.append(filters["start_date"])
        if "end_date" in filters and filters["end_date"]:
            where_clauses.append("t.date <= ?")
            params.append(filters["end_date"])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        limit_sql = f"LIMIT {int(limit)}" if limit is not None else ""

        sql = f"""
            SELECT t.id, t.description, t.amount, t.date, c.name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            {where_sql}
            ORDER BY t.date DESC
            {limit_sql}
        """

        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            conn.close()
            return [
                {"id": r[0], "description": r[1], "amount": r[2], "date": r[3], "category": r[4]}
                for r in rows
            ]
        except Exception:
            logger.exception("Failed fetching transactions with filters=%s", filters)
            return []

    def add_transaction(self, tx: Dict[str, Any]) -> Optional[int]:
        """Insert a new transaction. Returns the new id on success, else None.

        Expected tx keys: description, amount, date (YYYY-MM-DD), category (name)
        """
        try:
            cid = self._ensure_category(tx.get("category"))
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO transactions (description, amount, date, category_id) VALUES (?, ?, ?, ?)",
                (tx.get("description"), float(tx.get("amount", 0)), tx.get("date"), cid),
            )
            nid = cur.lastrowid
            conn.commit()
            conn.close()
            return nid
        except Exception:
            logger.exception("Failed adding transaction %s", tx)
            return None

    def update_transaction(self, tx: Dict[str, Any]) -> bool:
        """Update an existing transaction. Expects 'id' in tx. Returns True on success."""
        if not tx or "id" not in tx:
            return False
        try:
            cid = self._ensure_category(tx.get("category"))
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                "UPDATE transactions SET description = ?, amount = ?, date = ?, category_id = ? WHERE id = ?",
                (tx.get("description"), float(tx.get("amount", 0)), tx.get("date"), cid, int(tx["id"])),
            )
            conn.commit()
            affected = cur.rowcount
            conn.close()
            return affected > 0
        except Exception:
            logger.exception("Failed updating transaction %s", tx)
            return False

    def delete_transaction(self, tx_id: int) -> bool:
        """Delete transaction by id. Returns True if a row was deleted."""
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("DELETE FROM transactions WHERE id = ?", (int(tx_id),))
            conn.commit()
            affected = cur.rowcount
            conn.close()
            return affected > 0
        except Exception:
            logger.exception("Failed deleting transaction id=%s", tx_id)
            return False

    # --- Import / Export helpers ---
    def export_to_csv(self, path: Path) -> bool:
        """Export transactions to a CSV file at `path`. Returns True on success."""
        try:
            rows = self.fetch_transactions(filters=None, limit=None)
            if not rows:
                # Still create file with header
                fieldnames = ["id", "description", "amount", "date", "category"]
            else:
                fieldnames = list(rows[0].keys())
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    writer.writerow(r)
            return True
        except Exception:
            logger.exception("Failed exporting transactions to CSV %s", path)
            return False

    def import_from_csv(self, path: Path) -> int:
        """Import transactions from a CSV file. Returns number of imported rows."""
        count = 0
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Normalize keys
                    tx = {
                        "description": row.get("description") or row.get("desc") or "",
                        "amount": float(row.get("amount") or 0),
                        "date": row.get("date") or row.get("datetime") or "",
                        "category": row.get("category") or row.get("cat") or "",
                    }
                    if self.add_transaction(tx) is not None:
                        count += 1
            return count
        except Exception:
            logger.exception("Failed importing transactions from CSV %s", path)
            return count

    def compact_transaction_ids(self) -> Dict[int, int]:
        """Rebuild the transactions table to compact/reassign sequential IDs.

        Returns a mapping of old_id -> new_id. This operation is destructive
        to the `id` values and should be used with care; consider backing up
        the DB first. The method preserves other column values and category
        relationships.
        """
        mapping: Dict[int, int] = {}
        try:
            conn = self._connect()
            cur = conn.cursor()
            # create new table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions_new (
                    id INTEGER PRIMARY KEY,
                    description TEXT,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL,
                    category_id INTEGER
                );
                """
            )

            # iterate old rows in id order and insert into new table, recording mapping
            cur.execute("SELECT id, description, amount, date, category_id FROM transactions ORDER BY id")
            rows = cur.fetchall()
            for old_id, description, amount, date, category_id in rows:
                cur.execute(
                    "INSERT INTO transactions_new (description, amount, date, category_id) VALUES (?, ?, ?, ?)",
                    (description, amount, date, category_id),
                )
                new_id = cur.lastrowid
                mapping[int(old_id)] = int(new_id)

            # Replace tables atomically
            cur.execute("DROP TABLE transactions")
            cur.execute("ALTER TABLE transactions_new RENAME TO transactions")
            conn.commit()
            conn.close()
            return mapping
        except Exception:
            logger.exception("Failed compacting transaction ids")
            try:
                conn.rollback()
            except Exception:
                pass
            return mapping
