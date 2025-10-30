'''
    File Name: main.py
    Version: 2.0.0
    Date: 30/10/2025
    Author: Pablo Bartolomé Molina
'''
import sys
import logging

from PyQt6 import QtWidgets, QtCore

from config import APP_NAME, APP_VERSION, ensure_data_dir
from ui.main_window import MainWindow

# Logging config from config.py; fall back to a sensible default
try:
    from config import LOGGING_CONFIG  # type: ignore
except Exception:
    LOGGING_CONFIG = {
        "level": logging.INFO,
        "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    }

logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def main() -> int:
    # Ensure runtime dirs exist early
    try:
        ensure_data_dir()
    except Exception:
        logger.exception("Failed to ensure data directory exists")

    # Enable high DPI scaling for modern displays
    try:
        QtCore.QCoreApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True
        )
        QtCore.QCoreApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True
        )
    except Exception:
        logger.debug("Could not set high DPI attributes (older Qt).")

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # Friendly global exception hook that logs and shows a dialog
    def _excepthook(exc_type, exc_value, exc_tb):
        logger.exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
        try:
            QtWidgets.QMessageBox.critical(None, "Unhandled Exception", str(exc_value))
        except Exception:
            # If UI is not available or message box fails, silently continue after logging
            pass
        # Delegate to default handler as well
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    window = MainWindow()
    # Show window (MainWindow restores geometry / default size)
    window.show()

    # Use exec() (PyQt6) and return exit code
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
