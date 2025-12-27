'''
    File Name: transaction_form.py
    Version: 1.0.1
    Date: 30/10/2025
    Author: Pablo Bartolomé Molina
'''
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QDateEdit,
    QComboBox,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
)
from PyQt6.QtCore import QDate


class TransactionForm(QDialog):
    """Dialog to create or edit a transaction.

    Usage:
        dlg = TransactionForm(parent, db_manager=maybe_db)
        if dlg.exec():
            tx = dlg.get_transaction()

    If a `db_manager` with `add_transaction()` or `save_transaction()` is
    provided, `save_transaction()` will attempt to persist the new entry.
    """

    def __init__(self, parent=None, db_manager=None, transaction=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._transaction = transaction

        self.setWindowTitle("Transaction")
        self.setup_ui()

        if transaction:
            # populate fields for editing
            self._load_transaction(transaction)

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        form = QFormLayout()

        self.description = QLineEdit()
        form.addRow("Description:", self.description)

        self.amount = QDoubleSpinBox()
        self.amount.setMinimum(-1_000_000_000)
        self.amount.setMaximum(1_000_000_000)
        self.amount.setDecimals(2)
        form.addRow("Amount:", self.amount)

        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDate(QDate.currentDate())
        form.addRow("Date:", self.date)

        self.category = QComboBox()
        self.category.setEditable(True)
        form.addRow("Category:", self.category)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Connections
        self.save_btn.clicked.connect(self.save_transaction)
        self.cancel_btn.clicked.connect(self.reject)

        # Try to load categories from db_manager if available
        self._load_categories()

    def _load_transaction(self, tx: dict) -> None:
        try:
            self.description.setText(str(tx.get("description", "")))
            amt = tx.get("amount", 0)
            try:
                self.amount.setValue(float(amt))
            except Exception:
                self.amount.setValue(0.0)
            date_val = tx.get("date")
            if date_val:
                try:
                    # assume ISO string 'YYYY-MM-DD' or QDate
                    if isinstance(date_val, QDate):
                        self.date.setDate(date_val)
                    else:
                        parts = [int(p) for p in str(date_val).split("-")]
                        if len(parts) >= 3:
                            self.date.setDate(QDate(parts[0], parts[1], parts[2]))
                except Exception:
                    pass
            cat = tx.get("category")
            if cat is not None:
                idx = self.category.findText(str(cat))
                if idx >= 0:
                    self.category.setCurrentIndex(idx)
                else:
                    self.category.setEditText(str(cat))
        except Exception:
            # Keep dialog usable even if loading fails
            pass

    def _load_categories(self) -> None:
        if not getattr(self, "db_manager", None):
            return
        fetch = getattr(self.db_manager, "fetch_categories", None)
        if not callable(fetch):
            return
        try:
            cats = fetch()
            # Expecting iterable of dict-like with 'name' or simple strings
            self.category.clear()
            for c in cats:
                if isinstance(c, dict):
                    name = c.get("name") or c.get("label")
                else:
                    name = str(c)
                if name:
                    self.category.addItem(str(name))
        except Exception:
            # ignore failures to keep form functional
            pass

    def save_transaction(self) -> None:
        """Validate and optionally persist the transaction, then accept dialog."""
        desc = self.description.text().strip()
        amt = float(self.amount.value())
        date = self.date.date().toString("yyyy-MM-dd")
        cat = self.category.currentText().strip()

        # Basic validation: amount should not be zero and description non-empty
        if amt == 0:
            QMessageBox.warning(self, "Validation", "Amount must not be zero.")
            return

        tx = {"description": desc, "amount": amt, "date": date, "category": cat}

        # Try to persist using db_manager if available
        if getattr(self, "db_manager", None) is not None:
            saver = getattr(self.db_manager, "add_transaction", None) or getattr(self.db_manager, "save_transaction", None)
            if callable(saver):
                try:
                    saver(tx)
                except Exception:
                    QMessageBox.critical(self, "Save failed", "Failed to save transaction.")
                    return

        # store last transaction and close dialog as accepted
        self._transaction = tx
        self.accept()

    def get_transaction(self) -> dict:
        return self._transaction or {}
