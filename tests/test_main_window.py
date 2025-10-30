import time
from pathlib import Path

import pytest

from PyQt6 import QtCore

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
    # Status bar default message
    assert mw.status.currentMessage() == "Ready"


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

    mw.load_transactions()
    qtbot.waitUntil(lambda: len(captured) == 1, timeout=2000)
    assert captured[0] == [{"id": 1, "amount": 100}]