'''
    File Name: main_window.py
    Version: 2.1.0
    Date: 30/11/2025
    Author: Pablo Bartolomé Molina
'''
from pathlib import Path
import logging
from typing import Any, Callable, Optional

from PyQt6 import QtWidgets, QtGui, QtCore
from config import APP_NAME, APP_VERSION, STYLESHEET_PATH, ensure_data_dir

# Local UI components
from .transaction_form import TransactionForm
from .filter_dialog import FilterDialog
from database.db_manager import DatabaseManager

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
        # If caller provided a db_manager, ensure the DB file exists / is initialized.
        self.ensure_db_ready()

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

        # Transactions table (select rows to edit/delete)
        self.tx_table = QtWidgets.QTableWidget(0, 5)
        self.tx_table.setHorizontalHeaderLabels(["ID", "Date", "Description", "Category", "Amount"])
        self.tx_table.horizontalHeader().setStretchLastSection(True)
        self.tx_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tx_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tx_table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.tx_table)
        # Connect row selection to highlight
        self.tx_table.selectionModel().selectionChanged.connect(self._on_table_selection_changed)

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

        # Connect buttons to their dedicated handlers
        self.button1.clicked.connect(self.on_add_clicked)
        self.button2.clicked.connect(self.on_edit_clicked)
        self.button3.clicked.connect(self.on_delete_clicked)
        self.button4.clicked.connect(self.on_filter_search_clicked)
        self.button5.clicked.connect(self.on_statistics_clicked)
        self.button6.clicked.connect(self.on_import_export_clicked)

        central_widget.setLayout(main_layout)

        # If a database exists, attach it and load transactions immediately so
        # the table shows existing data on startup. Do NOT create a new DB here.
        try:
            if not getattr(self, "db_manager", None):
                dm = DatabaseManager()
                if dm.db_path.exists():
                    self.db_manager = dm
            if getattr(self, "db_manager", None):
                # load existing transactions into the table
                try:
                    self.load_transactions()
                except Exception:
                    logger.exception("Failed loading transactions on startup")
        except Exception:
            logger.exception("Failed to attach existing DatabaseManager on startup")

        # Restore/Set initial window size (remember last state with QSettings)
        try:
            settings = QtCore.QSettings("pbm", APP_NAME)
            geom = settings.value("geometry", None)
            if geom:
                # value() may return bytes or QByteArray depending on platform/binding
                if isinstance(geom, (bytes, bytearray)):
                    geom = QtCore.QByteArray(bytes(geom))
                if isinstance(geom, QtCore.QByteArray) and not geom.isEmpty():
                    self.restoreGeometry(geom)
                else:
                    self.resize(1200, 800)
                    self.setMinimumSize(800, 600)
            else:
                # Default startup size
                self.resize(1200, 800)
                self.setMinimumSize(800, 600)
        except Exception:
            logger.exception("Failed to restore/set window geometry")

        # track highlighted row for edit visual cue
        self._highlighted_row = None

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

            # Populate transactions table
            try:
                self._populate_transactions(result)
                self.status.showMessage("Transactions loaded")
            except Exception as e:
                # fall back if method missing or fails
                if hasattr(self, "_populate_transactions"):
                    self.show_error("UI update failed", "Failed updating UI with transactions", e)
                else:
                    logger.debug("No _populate_transactions found; result ignored")
                    self.status.showMessage("Transactions loaded (no UI handler)")
            else:
                logger.debug("No _populate_transactions found; result ignored")
                self.status.showMessage("Transactions loaded (no UI handler)")

        self.run_db_task(self.db_manager.fetch_transactions, _on_loaded)

    def update_text(self, message: str):
        self.text_display.append(message)

    def _populate_transactions(self, rows):
        """Populate the transactions table with a list of dict-like rows."""
        try:
            if not rows:
                # clear table
                self.tx_table.setRowCount(0)
                return

            self.tx_table.setRowCount(len(rows))
            for r_idx, r in enumerate(rows):
                tid = r.get("id")
                date = r.get("date", "")
                desc = r.get("description", "")
                cat = r.get("category", "")
                amt = r.get("amount", 0)

                self.tx_table.setItem(r_idx, 0, QtWidgets.QTableWidgetItem(str(tid)))
                self.tx_table.setItem(r_idx, 1, QtWidgets.QTableWidgetItem(str(date)))
                self.tx_table.setItem(r_idx, 2, QtWidgets.QTableWidgetItem(str(desc)))
                self.tx_table.setItem(r_idx, 3, QtWidgets.QTableWidgetItem(str(cat)))
                self.tx_table.setItem(r_idx, 4, QtWidgets.QTableWidgetItem(f"{amt:.2f}"))

            # Resize columns reasonably
            self.tx_table.resizeColumnsToContents()
        except Exception:
            logger.exception("Failed populating transactions table")

    def _get_selected_transaction_id(self) -> Optional[int]:
        """Return the transaction ID for the currently selected row, or None."""
        sel = self.tx_table.selectionModel().selectedRows()
        if not sel:
            return None
        try:
            row = sel[0].row()
            item = self.tx_table.item(row, 0)
            if item:
                return int(item.text())
        except Exception:
            logger.exception("Failed reading selected transaction id")
        return None

    def _get_selected_row_index(self) -> Optional[int]:
        sel = self.tx_table.selectionModel().selectedRows()
        if not sel:
            return None
        return sel[0].row()

    def _on_table_selection_changed(self):
        """Highlight the selected row whenever selection changes."""
        row_idx = self._get_selected_row_index()
        if row_idx is None:
            return
        try:
            # Clear previous highlight
            if self._highlighted_row is not None and self._highlighted_row != row_idx:
                for col in range(self.tx_table.columnCount()):
                    item = self.tx_table.item(self._highlighted_row, col)
                    if item:
                        item.setBackground(QtGui.QBrush())
            # Apply new highlight
            brush = QtGui.QBrush(QtGui.QColor(173, 216, 230))  # light blue
            for col in range(self.tx_table.columnCount()):
                item = self.tx_table.item(row_idx, col)
                if item:
                    item.setBackground(brush)
            self._highlighted_row = row_idx
        except Exception:
            logger.exception("Failed highlighting selected row")

    def closeEvent(self, event):
        try:
            settings = QtCore.QSettings("pbm", APP_NAME)
            settings.setValue("geometry", self.saveGeometry())
        except Exception:
            logger.exception("Failed to save window geometry")
        super().closeEvent(event)

    def on_add_clicked(self) -> None:
        """Handle Add button clicked (open transaction form / create new entry)."""
        logger.debug("on_add_clicked")
        self.status.showMessage("Adding transaction...")
        # Ensure a DatabaseManager exists (create DB if needed) before opening form
        if not getattr(self, "db_manager", None):
            try:
                dm = DatabaseManager()
                dm.ensure_database()
                self.db_manager = dm
            except Exception:
                logger.exception("Failed creating/initializing DatabaseManager")
                self.show_error("No database", "No database available to save transaction")
                return

        # Open the transaction form dialog and persist via db_manager if accepted
        try:
            dlg = TransactionForm(self, db_manager=self.db_manager)
        except Exception:
            logger.exception("Failed creating TransactionForm")
            self.show_error("Error", "Unable to open transaction form")
            return

        if dlg.exec():
            tx = dlg.get_transaction()
            if not tx:
                self.status.showMessage("No transaction data")
                return

            if not getattr(self, "db_manager", None):
                self.show_error("No database", "No database available to save transaction")
                return

            def _on_saved(res):
                # res expected to be new id or False/None on failure
                if isinstance(res, Exception) or not res:
                    self.show_error("Save failed", "Failed to save transaction")
                    self.status.showMessage("Save failed")
                    return
                self.update_text(f"Transaction added (id={res})")
                self.status.showMessage("Transaction saved")
                # refresh transactions view if implemented
                try:
                    self.load_transactions()
                except Exception:
                    logger.exception("Failed reloading transactions after save")

            # Run DB save in background to avoid blocking UI
            try:
                self.run_db_task(self.db_manager.add_transaction, _on_saved, tx)
                self.status.showMessage("Saving transaction...")
            except Exception:
                logger.exception("Failed to start background save task")
                # fallback to synchronous save
                try:
                    nid = self.db_manager.add_transaction(tx)
                    if nid:
                        self.update_text(f"Transaction added (id={nid})")
                        self.load_transactions()
                        self.status.showMessage("Transaction saved")
                    else:
                        self.show_error("Save failed", "Failed to save transaction")
                        self.status.showMessage("Save failed")
                except Exception as e:
                    logger.exception("Synchronous save failed")
                    self.show_error("Save failed", str(e))

    def on_edit_clicked(self) -> None:
        logger.debug("on_edit_clicked")
        self.status.showMessage("Editing transaction...")

        # Ensure DB present
        if not getattr(self, "db_manager", None):
            try:
                dm = DatabaseManager()
                dm.ensure_database()
                self.db_manager = dm
            except Exception:
                logger.exception("Failed creating/initializing DatabaseManager for edit")
                self.show_error("No database", "No database available to edit transaction")
                return

        tx_id = self._get_selected_transaction_id()
        row_idx = self._get_selected_row_index()
        if tx_id is None or row_idx is None:
            QtWidgets.QMessageBox.information(self, "Select transaction", "Please select a transaction to edit from the table.")
            self.status.showMessage("No transaction selected")
            return

        # (row is already highlighted by _on_table_selection_changed)

        def _on_fetched(res):
            if isinstance(res, Exception) or not res:
                self.show_error("Load failed", "Failed to load transaction for editing")
                self.status.showMessage("Load failed")
                return

            try:
                # open transaction form prefilled
                dlg = TransactionForm(self, db_manager=self.db_manager, transaction=res)
                if dlg.exec():
                    updated = dlg.get_transaction()
                    if not updated:
                        self.status.showMessage("No changes made")
                        return

                    def _on_updated(r2):
                        if isinstance(r2, Exception) or not r2:
                            self.show_error("Update failed", "Failed to update transaction")
                            self.status.showMessage("Update failed")
                            return
                        self.update_text(f"Transaction updated (id={tx_id})")
                        self.status.showMessage("Transaction updated")
                        try:
                            self.load_transactions()
                        except Exception:
                            logger.exception("Failed reloading transactions after update")

                    # Ensure id included for update
                    updated["id"] = tx_id
                    try:
                        self.run_db_task(self.db_manager.update_transaction, _on_updated, updated)
                    except Exception:
                        ok = self.db_manager.update_transaction(updated)
                        if ok:
                            self.update_text(f"Transaction updated (id={tx_id})")
                            self.load_transactions()
                            self.status.showMessage("Transaction updated")
                        else:
                            self.show_error("Update failed", "Failed to update transaction")
            except Exception:
                logger.exception("Failed handling fetched transaction for edit")

        # fetch transaction by id in background
        try:
            self.run_db_task(self.db_manager.fetch_transaction_by_id, _on_fetched, tx_id)
            self.status.showMessage("Loading transaction...")
        except Exception:
            logger.exception("Failed to start background fetch task")
            res = self.db_manager.fetch_transaction_by_id(tx_id)
            _on_fetched(res)

    def on_delete_clicked(self) -> None:
        """Handle Delete button clicked (remove selected transaction)."""
        logger.debug("on_delete_clicked")
        self.status.showMessage("Deleting transaction...")
        # If no DB manager, ensure one exists (create DB if necessary)
        if not getattr(self, "db_manager", None):
            try:
                dm = DatabaseManager()
                dm.ensure_database()
                self.db_manager = dm
            except Exception:
                logger.exception("Failed creating/initializing DatabaseManager for delete")
                self.show_error("No database", "No database available to delete transaction")
                return

        # Prompt user for transaction id to delete (fallback when no selection UI exists)
        try:
            tid, ok = QtWidgets.QInputDialog.getInt(self, "Delete transaction", "Transaction ID:", min=1)
        except Exception:
            logger.exception("Failed showing input dialog for delete")
            return

        if not ok:
            self.status.showMessage("Delete cancelled")
            return

        # Confirm
        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm delete",
            f"Are you sure you want to delete transaction id={tid}?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            self.status.showMessage("Delete cancelled")
            return

        def _on_deleted(res):
            if isinstance(res, Exception) or not res:
                self.show_error("Delete failed", "Failed to delete transaction")
                self.status.showMessage("Delete failed")
                return
            self.update_text(f"Transaction deleted (id={tid})")
            self.status.showMessage("Transaction deleted")
            try:
                self.load_transactions()
            except Exception:
                logger.exception("Failed reloading transactions after delete")

        try:
            self.run_db_task(self.db_manager.delete_transaction, _on_deleted, tid)
            self.status.showMessage("Deleting transaction...")
        except Exception:
            logger.exception("Failed to start background delete task")
            # fallback to synchronous delete
            try:
                ok = self.db_manager.delete_transaction(tid)
                if ok:
                    self.update_text(f"Transaction deleted (id={tid})")
                    self.load_transactions()
                    self.status.showMessage("Transaction deleted")
                else:
                    self.show_error("Delete failed", "Failed to delete transaction")
                    self.status.showMessage("Delete failed")
            except Exception as e:
                logger.exception("Synchronous delete failed")
                self.show_error("Delete failed", str(e))

    def on_filter_search_clicked(self) -> None:
        """Handle Filter/Search button clicked (open search/filter UI)."""
        logger.debug("on_filter_search_clicked")
        self.status.showMessage("Opening filter/search...")

        # Ensure DB present (create if necessary) so we can fetch categories and perform filtered queries
        if not getattr(self, "db_manager", None):
            try:
                dm = DatabaseManager()
                dm.ensure_database()
                self.db_manager = dm
            except Exception:
                logger.exception("Failed creating/initializing DatabaseManager for filter/search")
                self.show_error("No database", "No database available for filtering/searching")
                return

        # Try to gather existing categories to populate dialog (best-effort)
        categories = []
        try:
            fetch_cats = getattr(self.db_manager, "fetch_categories", None)
            if callable(fetch_cats):
                try:
                    categories = [c.get("name") for c in self.db_manager.fetch_categories()] or []
                except Exception:
                    logger.exception("Failed fetching categories for filter dialog")
        except Exception:
            logger.exception("Unexpected error while preparing filter dialog")

        # Open dialog
        try:
            dlg = FilterDialog(self, categories=categories)
        except Exception:
            logger.exception("Failed creating FilterDialog")
            self.show_error("Error", "Unable to open filter/search dialog")
            return

        if dlg.exec():
            filters, limit = dlg.get_filters()
            self.status.showMessage("Applying filters...")

            def _on_loaded(result):
                if isinstance(result, Exception):
                    self.show_error("Filter failed", "Failed to fetch filtered transactions", result)
                    self.status.showMessage("Filter failed")
                    return

                try:
                    self._populate_transactions(result)
                    self.status.showMessage("Filter applied")
                except Exception as e:
                    if hasattr(self, "_populate_transactions"):
                        self.show_error("UI update failed", "Failed updating UI with filtered results", e)
                    else:
                        logger.debug("No _populate_transactions found; result ignored")
                        self.status.showMessage("Filter applied (no UI handler)")

            # Run filtered fetch in background
            try:
                self.run_db_task(self.db_manager.fetch_transactions, _on_loaded, filters, limit)
            except Exception:
                logger.exception("Failed to start background filter task")
                # fallback to synchronous
                try:
                    res = self.db_manager.fetch_transactions(filters, limit)
                    _on_loaded(res)
                except Exception as e:
                    logger.exception("Synchronous filter failed")
                    self.show_error("Filter failed", str(e))

    def on_statistics_clicked(self) -> None:
        """Handle Statistics button clicked (show reports/graphs)."""
        logger.debug("on_statistics_clicked")
        self.status.showMessage("Showing statistics...")

        # Ensure DB present (create if necessary) so we can fetch transactions for the report
        if not getattr(self, "db_manager", None):
            try:
                dm = DatabaseManager()
                dm.ensure_database()
                self.db_manager = dm
            except Exception:
                logger.exception("Failed creating/initializing DatabaseManager for statistics")
                self.show_error("No database", "No database available to generate statistics")
                return

        # Create and display the reports view in a dialog
        try:
            from .reports_view import ReportsView
            
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Reports & Statistics")
            dialog.setGeometry(100, 100, 1000, 600)
            
            # Create the reports view with the database manager
            reports_view = ReportsView(parent=dialog, db_manager=self.db_manager)
            
            # Add the reports view to the dialog
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(reports_view)
            dialog.setLayout(layout)
            
            # Show the dialog
            dialog.exec()
            self.status.showMessage("Statistics dialog closed")
        except Exception:
            logger.exception("Failed creating/displaying statistics view")
            self.show_error("Error", "Unable to open statistics view")

    def on_import_export_clicked(self) -> None:
        """Handle Import/Export button clicked (import or export data)."""
        logger.debug("on_import_export_clicked")
        self.status.showMessage("Import / Export...")

        # Ensure DB present (create if necessary)
        if not getattr(self, "db_manager", None):
            try:
                dm = DatabaseManager()
                dm.ensure_database()
                self.db_manager = dm
            except Exception:
                logger.exception("Failed creating/initializing DatabaseManager for import/export")
                self.show_error("No database", "No database available for import/export")
                return

        # Create dialog with custom buttons
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("Import or Export")
        msg_box.setText("What would you like to do?")
        msg_box.setIcon(QtWidgets.QMessageBox.Icon.Question)
        
        export_btn = msg_box.addButton("Export", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        import_btn = msg_box.addButton("Import", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        cancel_btn = msg_box.addButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        
        msg_box.exec()
        
        clicked_btn = msg_box.clickedButton()
        
        if clicked_btn == cancel_btn or clicked_btn is None:
            self.status.showMessage("Import/Export cancelled")
            return
        elif clicked_btn == export_btn:
            self._handle_export()
        elif clicked_btn == import_btn:
            self._handle_import()

    def _handle_export(self) -> None:
        """Handle exporting transactions to CSV file."""
        logger.debug("_handle_export")
        
        # Ask user for file location
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Transactions",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )

        if not file_path:
            self.status.showMessage("Export cancelled")
            return

        def _on_export_done(result):
            if isinstance(result, Exception) or not result:
                self.show_error("Export failed", "Failed to export transactions")
                self.status.showMessage("Export failed")
                return
            self.update_text(f"Transactions exported to {file_path}")
            self.status.showMessage("Export successful")
            QtWidgets.QMessageBox.information(self, "Success", f"Transactions exported to:\n{file_path}")

        try:
            from pathlib import Path
            self.run_db_task(self.db_manager.export_to_csv, _on_export_done, Path(file_path))
            self.status.showMessage("Exporting transactions...")
        except Exception:
            logger.exception("Failed to start background export task")
            # Fallback to synchronous export
            try:
                from pathlib import Path
                success = self.db_manager.export_to_csv(Path(file_path))
                if success:
                    self.update_text(f"Transactions exported to {file_path}")
                    self.status.showMessage("Export successful")
                    QtWidgets.QMessageBox.information(self, "Success", f"Transactions exported to:\n{file_path}")
                else:
                    self.show_error("Export failed", "Failed to export transactions")
                    self.status.showMessage("Export failed")
            except Exception as e:
                logger.exception("Synchronous export failed")
                self.show_error("Export failed", str(e))

    def _handle_import(self) -> None:
        """Handle importing transactions from CSV file."""
        logger.debug("_handle_import")
        
        # Ask user for file to import
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import Transactions",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )

        if not file_path:
            self.status.showMessage("Import cancelled")
            return

        # Confirm import with user
        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm Import",
            f"Import transactions from:\n{file_path}\n\nThis will add transactions to your database.",
            QtWidgets.QMessageBox.StandardButton.Yes |
            QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            self.status.showMessage("Import cancelled")
            return

        def _on_import_done(result):
            if isinstance(result, Exception):
                self.show_error("Import failed", f"Failed to import transactions: {str(result)}")
                self.status.showMessage("Import failed")
                return
            
            if result == 0:
                self.show_error("Import warning", "No transactions were imported from the file")
                self.status.showMessage("Import completed with no rows")
                return
            
            self.update_text(f"Imported {result} transaction(s) from {file_path}")
            self.status.showMessage(f"Import successful ({result} transactions)")
            
            # Refresh table to show imported data
            try:
                self.load_transactions()
            except Exception:
                logger.exception("Failed reloading transactions after import")
            
            QtWidgets.QMessageBox.information(
                self,
                "Success",
                f"Successfully imported {result} transaction(s)"
            )

        try:
            from pathlib import Path
            self.run_db_task(self.db_manager.import_from_csv, _on_import_done, Path(file_path))
            self.status.showMessage("Importing transactions...")
        except Exception:
            logger.exception("Failed to start background import task")
            # Fallback to synchronous import
            try:
                from pathlib import Path
                count = self.db_manager.import_from_csv(Path(file_path))
                if count > 0:
                    self.update_text(f"Imported {count} transaction(s) from {file_path}")
                    self.status.showMessage(f"Import successful ({count} transactions)")
                    self.load_transactions()
                    QtWidgets.QMessageBox.information(
                        self,
                        "Success",
                        f"Successfully imported {count} transaction(s)"
                    )
                else:
                    self.show_error("Import warning", "No transactions were imported from the file")
                    self.status.showMessage("Import completed with no rows")
            except Exception as e:
                logger.exception("Synchronous import failed")
                self.show_error("Import failed", str(e))
    
    def ensure_db_ready(self) -> None:
        """Ensure the database file exists and is initialized."""
        if self.db_manager is not None:
            try:
                # prefer a method on the db_manager instance
                if hasattr(self.db_manager, "ensure_database"):
                    self.db_manager.ensure_database()
                else:
                    # fallback: try module-level helper
                    from database.db_manager import DatabaseManager as _DM
                    # if caller passed another implementation, we won't override it
                    logger.debug("Injected db_manager has no ensure_database(); not creating DB")
            except Exception:
                logger.exception("Failed to ensure database exists via injected db_manager")
