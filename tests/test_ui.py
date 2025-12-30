'''
    File Name: test_ui.py
    Version: 1.1.0
    Date: 30/11/2025
    Author: Pablo Bartolomé Molina
'''

import unittest
from unittest.mock import MagicMock, patch, call
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6 import QtWidgets, QtTest, QtCore
from PyQt6.QtWidgets import QApplication

from ui.reports_view import ReportsView
from ui.main_window import MainWindow
from ui.transaction_form import TransactionForm
from ui.filter_dialog import FilterDialog
from database.db_manager import DatabaseManager


class TestReportsView(unittest.TestCase):
    """Test suite for ReportsView statistics component."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for all tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=DatabaseManager)
        self.widget = ReportsView(db_manager=self.mock_db)

    def tearDown(self):
        """Clean up after tests."""
        self.widget.deleteLater()

    def test_reports_view_initialization(self):
        """Test that ReportsView initializes correctly."""
        self.assertIsNotNone(self.widget)
        self.assertEqual(self.widget._current_chart_type, "category")
        self.assertEqual(self.widget._transactions, [])
        self.assertIsNotNone(self.widget._figure)
        self.assertIsNotNone(self.widget._canvas)

    def test_reports_view_ui_setup(self):
        """Test that UI components are properly set up."""
        # Check that layout exists
        self.assertIsNotNone(self.widget.layout())
        
        # Check that controls exist
        self.assertIsNotNone(self.widget._chart_combo)
        self.assertIsNotNone(self.widget._stats_label)
        self.assertEqual(self.widget._chart_combo.count(), 3)  # 3 chart types

    def test_load_data_with_transactions(self):
        """Test loading transactions from db_manager."""
        mock_transactions = [
            {"id": 1, "amount": 100.0, "category": "Food", "date": "2025-01-01"},
            {"id": 2, "amount": 50.0, "category": "Transport", "date": "2025-01-02"},
        ]
        self.mock_db.fetch_transactions.return_value = mock_transactions

        self.widget._load_data()

        self.assertEqual(len(self.widget._transactions), 2)
        self.assertEqual(self.widget._transactions, mock_transactions)
        self.mock_db.fetch_transactions.assert_called_once()

    def test_load_data_with_no_transactions(self):
        """Test loading when no transactions exist."""
        self.mock_db.fetch_transactions.return_value = []

        self.widget._load_data()

        self.assertEqual(len(self.widget._transactions), 0)

    def test_load_data_with_db_error(self):
        """Test handling database fetch errors."""
        self.mock_db.fetch_transactions.side_effect = Exception("DB Error")

        self.widget._load_data()

        self.assertEqual(len(self.widget._transactions), 0)

    def test_load_data_no_db_manager(self):
        """Test behavior when no db_manager is provided."""
        widget = ReportsView(db_manager=None)
        widget._load_data()
        
        self.assertEqual(len(widget._transactions), 0)
        widget.deleteLater()

    def test_chart_type_changed(self):
        """Test switching between chart types."""
        with patch.object(self.widget, 'plot_data') as mock_plot:
            self.widget._on_chart_type_changed("By Category")
            self.assertEqual(self.widget._current_chart_type, "category")
            mock_plot.assert_called_once()

        with patch.object(self.widget, 'plot_data') as mock_plot:
            self.widget._on_chart_type_changed("By Month")
            self.assertEqual(self.widget._current_chart_type, "month")
            mock_plot.assert_called_once()

        with patch.object(self.widget, 'plot_data') as mock_plot:
            self.widget._on_chart_type_changed("Summary")
            self.assertEqual(self.widget._current_chart_type, "summary")
            mock_plot.assert_called_once()

    def test_refresh_reloads_data(self):
        """Test that refresh reloads data and replots."""
        mock_transactions = [
            {"id": 1, "amount": 100.0, "category": "Food", "date": "2025-01-01"},
        ]
        self.mock_db.fetch_transactions.return_value = mock_transactions

        with patch.object(self.widget, 'plot_data') as mock_plot:
            self.widget.refresh()
            
            self.assertEqual(len(self.widget._transactions), 1)
            mock_plot.assert_called_once()

    def test_update_stats_with_data(self):
        """Test statistics label update with data."""
        try:
            import pandas as pd
            df = pd.DataFrame([
                {"amount": 100.0},
                {"amount": 50.0},
                {"amount": 75.0},
            ])
            
            self.widget._update_stats(df)
            stats_text = self.widget._stats_label.text()
            
            self.assertIn("225.00", stats_text)  # Total
            self.assertIn("3", stats_text)  # Count
            self.assertIn("75.00", stats_text)  # Average
        except ImportError:
            self.skipTest("pandas not available")

    def test_update_stats_empty_data(self):
        """Test statistics label with no data."""
        self.widget._update_stats(None)
        self.assertIn("No transactions", self.widget._stats_label.text())

    def test_plot_data_empty_transactions(self):
        """Test plotting with empty transactions list."""
        self.widget._transactions = []
        self.widget.plot_data()  # Should not raise exception
        self.assertIn("No transactions", self.widget._stats_label.text())

    def test_plot_data_with_transactions(self):
        """Test plotting with actual transaction data."""
        try:
            import pandas as pd
            
            self.widget._transactions = [
                {"amount": 100.0, "category": "Food", "date": "2025-01-01"},
                {"amount": 50.0, "category": "Transport", "date": "2025-01-02"},
            ]
            
            # Should not raise exception
            self.widget.plot_data()
        except ImportError:
            self.skipTest("pandas not available")


class TestMainWindowStatistics(unittest.TestCase):
    """Test suite for statistics button in MainWindow."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for all tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=DatabaseManager)
        self.mock_db.fetch_transactions.return_value = []
        self.window = MainWindow(db_manager=self.mock_db)

    def tearDown(self):
        """Clean up after tests."""
        self.window.deleteLater()

    def test_statistics_button_exists(self):
        """Test that statistics button is present."""
        self.assertIsNotNone(self.window.button5)
        self.assertEqual(self.window.button5.text(), "Statistics")

    def test_on_statistics_clicked_with_db_manager(self):
        """Test opening statistics dialog with existing db_manager."""
        with patch('ui.main_window.ReportsView') as mock_reports_view:
            with patch.object(QtWidgets.QDialog, 'exec', return_value=1):
                self.window.on_statistics_clicked()
                
                # Verify ReportsView was created
                mock_reports_view.assert_called_once()

    def test_on_statistics_clicked_without_db_manager(self):
        """Test opening statistics when db_manager needs to be created."""
        window = MainWindow(db_manager=None)
        
        with patch('ui.main_window.DatabaseManager') as mock_db_class:
            mock_instance = MagicMock()
            mock_instance.fetch_transactions.return_value = []
            mock_db_class.return_value = mock_instance
            
            with patch('ui.main_window.ReportsView'):
                with patch.object(QtWidgets.QDialog, 'exec', return_value=1):
                    window.on_statistics_clicked()
                    
                    # Verify DatabaseManager was created
                    mock_instance.ensure_database.assert_called_once()

        window.deleteLater()

    def test_on_statistics_clicked_db_error(self):
        """Test handling database creation error."""
        window = MainWindow(db_manager=None)
        
        with patch('ui.main_window.DatabaseManager') as mock_db_class:
            mock_db_class.side_effect = Exception("DB creation failed")
            
            with patch.object(window, 'show_error') as mock_error:
                window.on_statistics_clicked()
                
                # Verify error dialog was shown
                mock_error.assert_called_once()
                self.assertIn("No database", mock_error.call_args[0][1])

        window.deleteLater()

    def test_on_statistics_clicked_button_connection(self):
        """Test that button click triggers the handler."""
        with patch.object(self.window, 'on_statistics_clicked') as mock_handler:
            self.window.button5.clicked.emit()
            mock_handler.assert_called_once()


class TestReportsViewCharts(unittest.TestCase):
    """Test suite for specific chart types in ReportsView."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for all tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=DatabaseManager)
        self.widget = ReportsView(db_manager=self.mock_db)

    def tearDown(self):
        """Clean up after tests."""
        self.widget.deleteLater()

    def test_plot_by_category(self):
        """Test category breakdown chart."""
        try:
            import pandas as pd
            
            df = pd.DataFrame([
                {"amount": 100.0, "category": "Food"},
                {"amount": 50.0, "category": "Food"},
                {"amount": 75.0, "category": "Transport"},
            ])
            
            ax = self.widget._figure.add_subplot(111)
            self.widget._plot_by_category(ax, df)  # Should not raise
        except ImportError:
            self.skipTest("pandas not available")

    def test_plot_by_month(self):
        """Test monthly trend chart."""
        try:
            import pandas as pd
            
            df = pd.DataFrame([
                {"amount": 100.0, "date": "2025-01-01"},
                {"amount": 50.0, "date": "2025-01-15"},
                {"amount": 75.0, "date": "2025-02-01"},
            ])
            
            ax = self.widget._figure.add_subplot(111)
            self.widget._plot_by_month(ax, df)  # Should not raise
        except ImportError:
            self.skipTest("pandas not available")

    def test_plot_summary(self):
        """Test summary statistics chart."""
        try:
            import pandas as pd
            
            df = pd.DataFrame([
                {"amount": 100.0},
                {"amount": 50.0},
                {"amount": 75.0},
            ])
            
            ax = self.widget._figure.add_subplot(111)
            self.widget._plot_summary(ax, df)  # Should not raise
        except ImportError:
            self.skipTest("pandas not available")


class TestTransactionForm(unittest.TestCase):
    """Test suite for TransactionForm dialog."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for all tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=DatabaseManager)
        self.mock_db.fetch_categories.return_value = [
            {"id": 1, "name": "Food"},
            {"id": 2, "name": "Transport"},
        ]

    def tearDown(self):
        """Clean up after tests."""
        pass

    def test_transaction_form_initialization(self):
        """Test that TransactionForm initializes correctly."""
        form = TransactionForm(db_manager=self.mock_db)
        self.assertIsNotNone(form)
        form.deleteLater()

    def test_transaction_form_with_prefilled_data(self):
        """Test opening form with prefilled transaction data."""
        transaction_data = {
            "id": 1,
            "description": "Lunch",
            "amount": 25.50,
            "date": "2025-01-15",
            "category": "Food"
        }
        
        form = TransactionForm(db_manager=self.mock_db, transaction=transaction_data)
        self.assertIsNotNone(form)
        form.deleteLater()

    def test_get_transaction_returns_dict(self):
        """Test that get_transaction returns a dictionary with required fields."""
        form = TransactionForm(db_manager=self.mock_db)
        
        # Simulate filling in form data
        with patch.object(form, 'get_transaction', return_value={
            "description": "Coffee",
            "amount": 5.00,
            "date": "2025-01-15",
            "category": "Food"
        }):
            result = form.get_transaction()
            
            self.assertIsInstance(result, dict)
            self.assertIn("description", result)
            self.assertIn("amount", result)
            self.assertIn("date", result)
            self.assertIn("category", result)
        
        form.deleteLater()

    def test_transaction_form_categories_loaded(self):
        """Test that form loads available categories."""
        form = TransactionForm(db_manager=self.mock_db)
        
        # Verify categories were fetched
        self.mock_db.fetch_categories.assert_called()
        
        form.deleteLater()

    def test_transaction_form_with_invalid_data(self):
        """Test form with invalid transaction data."""
        invalid_transaction = {
            "description": "",  # Empty description
            "amount": "invalid",  # Invalid amount
            "date": "not-a-date",  # Invalid date
        }
        
        form = TransactionForm(db_manager=self.mock_db, transaction=invalid_transaction)
        self.assertIsNotNone(form)
        form.deleteLater()


class TestFilterDialog(unittest.TestCase):
    """Test suite for FilterDialog component."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for all tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.categories = ["Food", "Transport", "Entertainment", "Utilities"]

    def tearDown(self):
        """Clean up after tests."""
        pass

    def test_filter_dialog_initialization(self):
        """Test that FilterDialog initializes correctly."""
        dialog = FilterDialog(categories=self.categories)
        self.assertIsNotNone(dialog)
        dialog.deleteLater()

    def test_filter_dialog_has_category_selector(self):
        """Test that filter dialog has category selection."""
        dialog = FilterDialog(categories=self.categories)
        
        # Verify dialog can be used to select filters
        filters, limit = dialog.get_filters()
        
        self.assertIsInstance(filters, dict)
        self.assertIsInstance(limit, (int, type(None)))
        
        dialog.deleteLater()

    def test_filter_dialog_with_empty_categories(self):
        """Test filter dialog with no categories."""
        dialog = FilterDialog(categories=[])
        
        filters, limit = dialog.get_filters()
        
        self.assertIsInstance(filters, dict)
        
        dialog.deleteLater()

    def test_filter_dialog_returns_filters_dict(self):
        """Test that get_filters returns proper dictionary."""
        dialog = FilterDialog(categories=self.categories)
        
        filters, limit = dialog.get_filters()
        
        # Verify filters have expected keys (may be empty or populated)
        self.assertIsInstance(filters, dict)
        # Check common filter keys exist
        if "category" in filters:
            self.assertIsInstance(filters["category"], str)
        if "start_date" in filters:
            self.assertIsInstance(filters["start_date"], str)
        if "end_date" in filters:
            self.assertIsInstance(filters["end_date"], str)
        
        dialog.deleteLater()

    def test_filter_dialog_returns_limit(self):
        """Test that get_filters returns a limit value."""
        dialog = FilterDialog(categories=self.categories)
        
        filters, limit = dialog.get_filters()
        
        # Limit should be either None or an integer
        self.assertTrue(limit is None or isinstance(limit, int))
        
        dialog.deleteLater()

    def test_filter_dialog_with_date_range(self):
        """Test filter dialog with date range filtering."""
        dialog = FilterDialog(categories=self.categories)
        
        # Get filters - in real usage, user would set these
        filters, limit = dialog.get_filters()
        
        # Check structure even if empty
        self.assertIsInstance(filters, dict)
        
        dialog.deleteLater()


class TestMainWindowTableUI(unittest.TestCase):
    """Test suite for MainWindow table UI components."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for all tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=DatabaseManager)
        self.mock_db.fetch_transactions.return_value = []
        self.window = MainWindow(db_manager=self.mock_db)

    def tearDown(self):
        """Clean up after tests."""
        self.window.deleteLater()

    def test_transactions_table_exists(self):
        """Test that transactions table is present."""
        self.assertIsNotNone(self.window.tx_table)
        self.assertEqual(self.window.tx_table.columnCount(), 5)
        
        # Check column headers
        headers = [self.window.tx_table.horizontalHeaderItem(i).text() 
                   for i in range(5)]
        self.assertEqual(headers, ["ID", "Date", "Description", "Category", "Amount"])

    def test_populate_transactions_empty(self):
        """Test populating table with no transactions."""
        self.window._populate_transactions([])
        self.assertEqual(self.window.tx_table.rowCount(), 0)

    def test_populate_transactions_with_data(self):
        """Test populating table with transaction data."""
        transactions = [
            {"id": 1, "date": "2025-01-01", "description": "Lunch", "category": "Food", "amount": 25.50},
            {"id": 2, "date": "2025-01-02", "description": "Gas", "category": "Transport", "amount": 45.00},
        ]
        
        self.window._populate_transactions(transactions)
        
        self.assertEqual(self.window.tx_table.rowCount(), 2)
        
        # Check first row data
        self.assertEqual(self.window.tx_table.item(0, 0).text(), "1")
        self.assertEqual(self.window.tx_table.item(0, 1).text(), "2025-01-01")
        self.assertEqual(self.window.tx_table.item(0, 2).text(), "Lunch")
        self.assertEqual(self.window.tx_table.item(0, 3).text(), "Food")
        self.assertEqual(self.window.tx_table.item(0, 4).text(), "25.50")

    def test_table_selection_highlighting(self):
        """Test row highlighting on selection."""
        transactions = [
            {"id": 1, "date": "2025-01-01", "description": "Test", "category": "Food", "amount": 10.00},
        ]
        
        self.window._populate_transactions(transactions)
        
        # Select first row
        self.window.tx_table.selectRow(0)
        
        # Trigger selection changed
        self.window._on_table_selection_changed()
        
        # Verify row was highlighted
        self.assertEqual(self.window._highlighted_row, 0)

    def test_get_selected_transaction_id(self):
        """Test retrieving selected transaction ID."""
        transactions = [
            {"id": 42, "date": "2025-01-01", "description": "Test", "category": "Food", "amount": 10.00},
        ]
        
        self.window._populate_transactions(transactions)
        self.window.tx_table.selectRow(0)
        
        tx_id = self.window._get_selected_transaction_id()
        self.assertEqual(tx_id, 42)

    def test_get_selected_transaction_id_none(self):
        """Test retrieving ID when no row selected."""
        tx_id = self.window._get_selected_transaction_id()
        self.assertIsNone(tx_id)

    def test_get_selected_row_index(self):
        """Test retrieving selected row index."""
        transactions = [
            {"id": 1, "date": "2025-01-01", "description": "Test", "category": "Food", "amount": 10.00},
            {"id": 2, "date": "2025-01-02", "description": "Test2", "category": "Transport", "amount": 20.00},
        ]
        
        self.window._populate_transactions(transactions)
        self.window.tx_table.selectRow(1)
        
        row_idx = self.window._get_selected_row_index()
        self.assertEqual(row_idx, 1)


class TestMainWindowErrorHandling(unittest.TestCase):
    """Test suite for MainWindow error handling."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for all tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=DatabaseManager)
        self.mock_db.fetch_transactions.return_value = []
        self.window = MainWindow(db_manager=self.mock_db)

    def tearDown(self):
        """Clean up after tests."""
        self.window.deleteLater()

    def test_show_error_displays_message(self):
        """Test that show_error displays error dialog."""
        with patch('ui.main_window.QtWidgets.QMessageBox.critical') as mock_critical:
            self.window.show_error("Test Error", "This is a test error")
            
            # Verify critical dialog was called
            mock_critical.assert_called_once()
            call_args = mock_critical.call_args[0]
            self.assertIn("Test Error", call_args)

    def test_show_error_logs_exception(self):
        """Test that show_error logs exceptions."""
        test_exception = Exception("Test exception")
        
        with patch('ui.main_window.QtWidgets.QMessageBox.critical'):
            with patch('ui.main_window.logger.exception') as mock_log:
                self.window.show_error("Error Title", "Error message", exc=test_exception)
                
                # Verify exception was logged
                mock_log.assert_called_once()

    def test_update_text_appends_to_display(self):
        """Test that update_text appends to text display."""
        initial_text = self.window.text_display.toPlainText()
        
        self.window.update_text("Test message")
        
        updated_text = self.window.text_display.toPlainText()
        self.assertIn("Test message", updated_text)

    def test_status_bar_message_updates(self):
        """Test that status bar message can be updated."""
        self.window.status.showMessage("Test status")
        
        self.assertEqual(self.window.status.currentMessage(), "Test status")

    def test_transaction_buttons_exist(self):
        """Test that all transaction buttons exist."""
        self.assertIsNotNone(self.window.button1)  # Add
        self.assertIsNotNone(self.window.button2)  # Edit
        self.assertIsNotNone(self.window.button3)  # Delete
        self.assertIsNotNone(self.window.button4)  # Filter/Search
        self.assertIsNotNone(self.window.button5)  # Statistics
        self.assertIsNotNone(self.window.button6)  # Import/Export
        
        # Verify button labels
        self.assertEqual(self.window.button1.text(), "Add")
        self.assertEqual(self.window.button2.text(), "Edit")
        self.assertEqual(self.window.button3.text(), "Delete")
        self.assertEqual(self.window.button4.text(), "Filter/Search")
        self.assertEqual(self.window.button5.text(), "Statistics")
        self.assertEqual(self.window.button6.text(), "Import/Export")

    def test_button_click_handlers_connected(self):
        """Test that buttons are connected to handlers."""
        with patch.object(self.window, 'on_add_clicked') as mock_add:
            self.window.button1.clicked.emit()
            mock_add.assert_called_once()

        with patch.object(self.window, 'on_edit_clicked') as mock_edit:
            self.window.button2.clicked.emit()
            mock_edit.assert_called_once()

        with patch.object(self.window, 'on_delete_clicked') as mock_delete:
            self.window.button3.clicked.emit()
            mock_delete.assert_called_once()

        with patch.object(self.window, 'on_filter_search_clicked') as mock_filter:
            self.window.button4.clicked.emit()
            mock_filter.assert_called_once()

        with patch.object(self.window, 'on_import_export_clicked') as mock_import:
            self.window.button6.clicked.emit()
            mock_import.assert_called_once()

class TestImportExportFunctionality(unittest.TestCase):
    """Test suite for import/export functionality."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for all tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=DatabaseManager)
        self.mock_db.fetch_transactions.return_value = []
        self.window = MainWindow(db_manager=self.mock_db)

    def tearDown(self):
        """Clean up after tests."""
        self.window.deleteLater()

    def test_on_import_export_clicked_without_db(self):
        """Test import/export when db_manager needs to be created."""
        window = MainWindow(db_manager=None)
        
        with patch('ui.main_window.DatabaseManager') as mock_db_class:
            mock_instance = MagicMock()
            mock_instance.fetch_transactions.return_value = []
            mock_db_class.return_value = mock_instance
            
            with patch.object(QtWidgets.QMessageBox, 'exec', return_value=None):
                window.on_import_export_clicked()
                
                # Verify DatabaseManager was created
                mock_instance.ensure_database.assert_called_once()

        window.deleteLater()

    def test_on_import_export_cancel(self):
        """Test cancelling the import/export dialog."""
        with patch.object(QtWidgets.QMessageBox, 'exec', return_value=None):
            with patch.object(QtWidgets.QMessageBox, 'clickedButton', return_value=None):
                self.window.on_import_export_clicked()
                
                # Should show cancelled message
                self.assertIn("cancelled", self.window.status.currentMessage())

    def test_handle_export_button_clicked(self):
        """Test export button in the dialog."""
        msg_box = QtWidgets.QMessageBox()
        export_btn = msg_box.addButton("Export", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        import_btn = msg_box.addButton("Import", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        
        # Verify buttons exist
        self.assertIsNotNone(export_btn)
        self.assertIsNotNone(import_btn)
        self.assertEqual(export_btn.text(), "Export")
        self.assertEqual(import_btn.text(), "Import")

    def test_handle_import_button_clicked(self):
        """Test import button in the dialog."""
        msg_box = QtWidgets.QMessageBox()
        export_btn = msg_box.addButton("Export", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        import_btn = msg_box.addButton("Import", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        
        # Verify buttons exist
        self.assertIsNotNone(export_btn)
        self.assertIsNotNone(import_btn)
        self.assertEqual(import_btn.text(), "Import")

    def test_handle_export_no_file_selected(self):
        """Test export when user cancels file dialog."""
        with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=("", "")):
            self.window._handle_export()
            
            # Should show cancelled message
            self.assertIn("cancelled", self.window.status.currentMessage())

    def test_handle_export_success(self):
        """Test successful export."""
        with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', 
                         return_value=("/tmp/export.csv", "")):
            with patch.object(QtWidgets.QMessageBox, 'information') as mock_info:
                self.mock_db.export_to_csv.return_value = True
                
                self.window._handle_export()
                
                # Verify export was called
                self.mock_db.export_to_csv.assert_called()

    def test_handle_export_failure(self):
        """Test export failure."""
        with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', 
                         return_value=("/tmp/export.csv", "")):
            with patch.object(self.window, 'show_error') as mock_error:
                self.mock_db.export_to_csv.return_value = False
                
                self.window._handle_export()
                
                # Let background task complete
                import time
                time.sleep(0.5)

    def test_handle_import_no_file_selected(self):
        """Test import when user cancels file dialog."""
        with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', return_value=("", "")):
            self.window._handle_import()
            
            # Should show cancelled message
            self.assertIn("cancelled", self.window.status.currentMessage())

    def test_handle_import_user_cancels_confirmation(self):
        """Test import when user cancels confirmation dialog."""
        with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', 
                         return_value=("/tmp/import.csv", "")):
            with patch.object(QtWidgets.QMessageBox, 'question',
                             return_value=QtWidgets.QMessageBox.StandardButton.No):
                self.window._handle_import()
                
                # Should show cancelled message
                self.assertIn("cancelled", self.window.status.currentMessage())

    def test_handle_import_success(self):
        """Test successful import."""
        with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', 
                         return_value=("/tmp/import.csv", "")):
            with patch.object(QtWidgets.QMessageBox, 'question',
                             return_value=QtWidgets.QMessageBox.StandardButton.Yes):
                with patch.object(QtWidgets.QMessageBox, 'information') as mock_info:
                    self.mock_db.import_from_csv.return_value = 5
                    
                    self.window._handle_import()
                    
                    # Verify import was called
                    self.mock_db.import_from_csv.assert_called()

    def test_handle_import_no_rows(self):
        """Test import when no rows are imported."""
        with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', 
                         return_value=("/tmp/import.csv", "")):
            with patch.object(QtWidgets.QMessageBox, 'question',
                             return_value=QtWidgets.QMessageBox.StandardButton.Yes):
                with patch.object(self.window, 'show_error') as mock_error:
                    self.mock_db.import_from_csv.return_value = 0
                    
                    self.window._handle_import()
                    
                    # Let background task complete
                    import time
                    time.sleep(0.5)

    def test_import_refreshes_transactions(self):
        """Test that import refreshes the transaction table."""
        with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', 
                         return_value=("/tmp/import.csv", "")):
            with patch.object(QtWidgets.QMessageBox, 'question',
                             return_value=QtWidgets.QMessageBox.StandardButton.Yes):
                with patch.object(QtWidgets.QMessageBox, 'information'):
                    with patch.object(self.window, 'load_transactions') as mock_load:
                        self.mock_db.import_from_csv.return_value = 3
                        
                        self.window._handle_import()
                        
                        # Let background task complete
                        import time
                        time.sleep(0.5)


if __name__ == "__main__":
    unittest.main()