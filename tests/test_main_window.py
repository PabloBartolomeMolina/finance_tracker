import time
from pathlib import Path

import pytest

from PyQt6 import QtCore, QtWidgets

import config
from ui.main_window import MainWindow


@pytest.fixture(autouse=True)
def ensure_qapp(qtbot):
    """Ensure a QApplication exists (provided by pytest-qt via qtbot)."""
    return qtbot


def test_window_title_and_statusbar(qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    # Title contains app name and version
    assert config.APP_NAME in mw.windowTitle()
    assert config.APP_VERSION in mw.windowTitle()
    # Status bar shows a message (may be "Ready" or "Loading transactions...")
    assert mw.status.currentMessage() in ["Ready", "Loading transactions..."]


def test_apply_stylesheet_applies_content(qtbot, tmp_path, monkeypatch):
    # Create a temporary stylesheet and point config to it
    qss = tmp_path / "test_styles.qss"
    qss.write_text("QWidget { background-color: rgb(18,52,86); }", encoding="utf-8")

    # Ensure config.STYLESHEET_PATH is a Path-like value that MainWindow will read
    monkeypatch.setattr(config, "STYLESHEET_PATH", qss)

    mw = MainWindow()
    qtbot.addWidget(mw)

    # The stylesheet should be applied (some content should appear in widget stylesheet)
    assert "background-color" in mw.styleSheet()


def test_run_db_task_executes_and_calls_on_done(qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)

    results = []

    def done(res):
        results.append(res)

    # Simple background task
    mw.run_db_task(lambda: 1 + 2, on_done=done)

    qtbot.waitUntil(lambda: len(results) == 1, timeout=2000)
    assert results[0] == 3


def test_load_transactions_no_db_manager_shows_message(qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)

    mw.db_manager = None
    mw.load_transactions()
    assert mw.status.currentMessage() == "No database available"


def test_load_transactions_with_db_manager_calls_populate(qtbot):
    class FakeDB:
        def fetch_transactions(self):
            # simulate some quick work
            return [{"id": 1, "amount": 100}]

    mw = MainWindow()
    qtbot.addWidget(mw)

    captured = []

    def _populate(result):
        captured.append(result)

    # Provide the UI handler and a fake DB manager
    mw._populate_transactions = _populate
    mw.db_manager = FakeDB()

    # Mock run_db_task to execute synchronously
    def sync_run_db_task(fn, on_done=None, *args, **kwargs):
        result = fn(*args, **kwargs)
        if on_done:
            on_done(result)

    mw.run_db_task = sync_run_db_task

    mw.load_transactions()
    qtbot.waitUntil(lambda: len(captured) == 1, timeout=2000)
    assert captured[0] == [{"id": 1, "amount": 100}]


def test_on_add_clicked_saves_transaction_and_updates_ui(qtbot, monkeypatch):
    mw = MainWindow()
    qtbot.addWidget(mw)

    # Fake dialog that returns a transaction when accepted
    class FakeDlg:
        def __init__(self, parent=None, db_manager=None, transaction=None):
            pass

        def exec(self):
            return True

        def get_transaction(self):
            return {"description": "Test Add", "amount": 12.34, "date": "2025-01-01", "category": "Test"}

    monkeypatch.setattr("ui.main_window.TransactionForm", FakeDlg)

    # Provide a fake DB manager and synchronous run_db_task
    class FakeDB:
        def __init__(self):
            self.added = []

        def add_transaction(self, tx):
            self.added.append(tx)
            return 123

    fake_db = FakeDB()
    mw.db_manager = fake_db

    # Make run_db_task call synchronously and invoke the on_done callback
    def sync_run(fn, on_done=None, *args, **kwargs):
        res = fn(*args, **kwargs)
        if on_done:
            on_done(res)

    mw.run_db_task = sync_run
    # Prevent load_transactions side-effects
    mw.load_transactions = lambda: None

    mw.on_add_clicked()

    # verify db called and UI updated
    assert fake_db.added
    assert "Transaction added (id=123)" in mw.text_display.toPlainText()
    # Status message should contain "Saving transaction" or "Transaction saved"
    status_msg = mw.status.currentMessage().lower()
    assert "transaction" in status_msg or "saving" in status_msg


def test_on_delete_clicked_confirms_and_deletes(qtbot, monkeypatch):
    mw = MainWindow()
    qtbot.addWidget(mw)

    # Provide fake DB manager
    class FakeDB:
        def delete_transaction(self, tid):
            return True

    mw.db_manager = FakeDB()

    # Monkeypatch input dialog to return id 10 and accepted
    monkeypatch.setattr("ui.main_window.QtWidgets.QInputDialog.getInt", lambda *a, **k: (10, True))
    # Monkeypatch confirmation dialog to return Yes
    monkeypatch.setattr(
        "ui.main_window.QtWidgets.QMessageBox.question",
        lambda *a, **k: QtWidgets.QMessageBox.StandardButton.Yes,
    )

    # synchronous run
    def sync_run(fn, on_done=None, *args, **kwargs):
        res = fn(*args, **kwargs)
        if on_done:
            on_done(res)

    mw.run_db_task = sync_run
    mw.load_transactions = lambda: None

    mw.on_delete_clicked()

    assert "Transaction deleted (id=10)" in mw.text_display.toPlainText()
    # Status message should contain "Deleting transaction" or similar
    status_msg = mw.status.currentMessage().lower()
    assert "transaction" in status_msg or "deleting" in status_msg


def test_table_selection_and_edit_flow(qtbot, monkeypatch):
    mw = MainWindow()
    qtbot.addWidget(mw)

    # Clear any existing rows in the table
    mw.tx_table.setRowCount(0)

    # Populate the table with one transaction row
    rows = [{"id": 5, "date": "2025-01-01", "description": "Old", "category": "X", "amount": 1.0}]
    mw._populate_transactions(rows)
    qtbot.wait(50)

    # Select the first row
    mw.tx_table.selectRow(0)
    qtbot.wait(50)

    # Verify selected id helper
    assert mw._get_selected_transaction_id() == 5

    # Fake fetch and update flow
    class FakeDB:
        def fetch_transaction_by_id(self, tid):
            return {"id": tid, "description": "Old", "amount": 1.0, "date": "2025-01-01", "category": "X"}

        def update_transaction(self, tx):
            return True

    mw.db_manager = FakeDB()

    # Fake TransactionForm to accept updated data
    class FakeEditDlg:
        def __init__(self, parent=None, db_manager=None, transaction=None):
            pass

        def exec(self):
            return True

        def get_transaction(self):
            return {"description": "New", "amount": 2.0, "date": "2025-02-02", "category": "Y"}

    monkeypatch.setattr("ui.main_window.TransactionForm", FakeEditDlg)

    # synchronous runner
    def sync_run(fn, on_done=None, *args, **kwargs):
        res = fn(*args, **kwargs)
        if on_done:
            on_done(res)

    mw.run_db_task = sync_run
    mw.load_transactions = lambda: None

    mw.on_edit_clicked()

    assert "Transaction updated (id=5)" in mw.text_display.toPlainText()
    # Status message should contain transaction-related text
    status_msg = mw.status.currentMessage().lower()
    assert "transaction" in status_msg or "updated" in status_msg or "editing" in status_msg