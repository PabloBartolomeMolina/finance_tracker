'''
    File Name: main_window.py
    Version: 1.3.1
    Date: 16/09/2025
    Author: Pablo Bartolomé Molina
'''
from pathlib import Path
import logging
from typing import Any, Callable, Optional

from PyQt5 import QtWidgets, QtGui, QtCore

from config import APP_NAME, APP_VERSION, STYLESHEET_PATH, ensure_data_dir

logger = logging.getLogger(__name__)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, db_manager: Optional[Any] = None, **kwargs):
        super().__init__(*args, **kwargs)

        # Ensure runtime data dir exists (safe)
        try:
            ensure_data_dir()
        except Exception:
            logger.exception("Failed ensuring data directory")

        # Window metadata and status bar
        try:
            self.setWindowTitle(f"{APP_NAME} — {APP_VERSION}")
        except Exception:
            logger.exception("Failed to set window title")

        self.status = self.statusBar()
        self.status.showMessage("Ready")

        # DB manager may be injected by the app
        self.db_manager = db_manager

        # Thread pool for background tasks
        self._pool = QtCore.QThreadPool.globalInstance()

        # Apply stylesheet if present (non-fatal)
        try:
            self._apply_stylesheet()
        except Exception:
            logger.exception("Failed to apply stylesheet")

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Text display
        self.text_display = QtWidgets.QTextEdit()
        self.text_display.setReadOnly(True)
        main_layout.addWidget(self.text_display)

        # Transactions group
        transaction_group = QtWidgets.QGroupBox("Transactions")
        t_layout = QtWidgets.QHBoxLayout()
        self.button1 = QtWidgets.QPushButton("Add")
        self.button2 = QtWidgets.QPushButton("Edit")
        self.button3 = QtWidgets.QPushButton("Delete")
        t_layout.addWidget(self.button1)
        t_layout.addWidget(self.button2)
        t_layout.addWidget(self.button3)
        transaction_group.setLayout(t_layout)
        main_layout.addWidget(transaction_group)

        # Reports / Utilities group
        report_group = QtWidgets.QGroupBox("Reports & Utilities")
        r_layout = QtWidgets.QHBoxLayout()
        self.button4 = QtWidgets.QPushButton("Filter/Search")
        self.button5 = QtWidgets.QPushButton("Statistics")
        self.button6 = QtWidgets.QPushButton("Import/Export")
        r_layout.addWidget(self.button4)
        r_layout.addWidget(self.button5)
        r_layout.addWidget(self.button6)
        report_group.setLayout(r_layout)
        main_layout.addWidget(report_group)

        # Connect buttons -- TODO: update actions once they are properly coded to interact with DB and files.
        for i, btn in enumerate([self.button1, self.button2, self.button3,
                                 self.button4, self.button5, self.button6], 1):
            btn.clicked.connect(lambda _, x=i: self.update_text(f"Button {x} clicked"))

        central_widget.setLayout(main_layout)

        # Restore/Set initial window size (remember last state with QSettings)
        try:
            settings = QtCore.QSettings("pbm", APP_NAME)
            geom = settings.value("geometry")
            if isinstance(geom, QtCore.QByteArray) and not geom.isEmpty():
                self.restoreGeometry(geom)
            else:
                # Default startup size
                self.resize(1200, 800)
                self.setMinimumSize(800, 600)
        except Exception:
            logger.exception("Failed to restore/set window geometry")

    def _apply_stylesheet(self) -> None:
        """Load and apply a stylesheet if the file exists; otherwise skip quietly."""
        path = Path(STYLESHEET_PATH)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
                logger.debug("Applied stylesheet: %s", path)
            except Exception:
                logger.exception("Error reading/applying stylesheet")
        else:
            logger.debug("Stylesheet not found at %s; skipping", path)

    def show_error(self, title: str, message: str, exc: Optional[Exception] = None) -> None:
        """Log and present a critical message box to the user."""
        if exc:
            logger.exception("%s: %s", title, message)
        else:
            logger.error("%s: %s", title, message)
        QtWidgets.QMessageBox.critical(self, title, message)

    def run_db_task(self, fn: Callable[..., Any], on_done: Optional[Callable[[Any], None]] = None, *args, **kwargs) -> None:
        """
        Run a blocking function in a background thread and call on_done(result) in the main thread.
        Usage: self.run_db_task(self.db_manager.fetch_transactions, self._on_transactions_loaded)
        """
        class _Signals(QtCore.QObject):
            finished = QtCore.pyqtSignal(object)
            error = QtCore.pyqtSignal(object)

        class _Runner(QtCore.QRunnable):
            def __init__(self, func, a, kw):
                super().__init__()
                self.func = func
                self.args = a
                self.kwargs = kw
                self.signals = _Signals()

            @QtCore.pyqtSlot()
            def run(self):
                try:
                    res = self.func(*self.args, **self.kwargs)
                    self.signals.finished.emit(res)
                except Exception as e:
                    self.signals.error.emit(e)

        runner = _Runner(fn, args, kwargs)

        if on_done:
            # ensure callback runs in main thread
            runner.signals.finished.connect(on_done)

        def _on_err(e):
            # show and log
            self.show_error("Background task error", str(e), exc=e)
        runner.signals.error.connect(_on_err)

        self._pool.start(runner)

    def load_transactions(self) -> None:
        """Example: load transactions using db_manager without blocking UI."""
        if not getattr(self, "db_manager", None):
            logger.warning("No db_manager available to load transactions")
            self.status.showMessage("No database available")
            return

        self.status.showMessage("Loading transactions...")

        def _on_loaded(result):
            if isinstance(result, Exception):
                self.show_error("Load failed", "Failed to load transactions", result)
                self.status.showMessage("Load failed")
                return

            # If the class defines a _populate_transactions method, use it.
            if hasattr(self, "_populate_transactions"):
                try:
                    self._populate_transactions(result)
                    self.status.showMessage("Transactions loaded")
                except Exception as e:
                    self.show_error("UI update failed", "Failed updating UI with transactions", e)
            else:
                logger.debug("No _populate_transactions found; result ignored")
                self.status.showMessage("Transactions loaded (no UI handler)")

        self.run_db_task(self.db_manager.fetch_transactions, _on_loaded)

    def update_text(self, message: str):
        self.text_display.append(message)

    def closeEvent(self, event):
        try:
            settings = QtCore.QSettings("pbm", APP_NAME)
            settings.setValue("geometry", self.saveGeometry())
        except Exception:
            logger.exception("Failed to save window geometry")
        super().closeEvent(event)
