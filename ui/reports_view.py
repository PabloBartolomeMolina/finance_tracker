'''
    File Name: reports_view.py
    Version: 1.1.0
    Date: 30/11/2025
    Author: Pablo Bartolomé Molina
'''
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QComboBox
from PyQt6.QtCore import Qt

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT

try:
    import pandas as pd
except Exception:
    pd = None

logger = logging.getLogger(__name__)


class ReportsView(QWidget):
    """Enhanced reports view with matplotlib canvas and multiple visualization options.

    Features:
    - Multiple chart types (Category breakdown, Time-based summary)
    - Real data validation with clear empty state messaging
    - Summary statistics display
    - Dynamic figure sizing that adapts to window
    - Automatic data refresh from db_manager
    """

    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._transactions = []
        self._current_chart_type = "category"
        
        # Dynamic figure sizing
        self._figure = Figure(figsize=(10, 6), dpi=100)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._toolbar = NavigationToolbar2QT(self._canvas, self)
        
        # Create a single axis that we'll reuse for all plots
        self._ax = self._figure.add_subplot(111)

        self.setup_ui()
        
        # Load and plot initial data
        try:
            self._load_data()
            self.plot_data()
        except Exception as e:
            logger.exception("Failed to initialize ReportsView")

    def setup_ui(self) -> None:
        """Build the UI: title, chart selector, toolbar, canvas, stats display and refresh button."""
        main_layout = QVBoxLayout()
        
        # Title
        title = QLabel("Reports & Statistics")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(title)

        # Controls row
        controls_layout = QHBoxLayout()
        
        chart_label = QLabel("Chart Type:")
        self._chart_combo = QComboBox()
        self._chart_combo.addItems(["By Category", "By Month", "Summary"])
        self._chart_combo.currentTextChanged.connect(self._on_chart_type_changed)
        
        controls_layout.addWidget(chart_label)
        controls_layout.addWidget(self._chart_combo)
        controls_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        controls_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(controls_layout)

        # Toolbar and canvas
        main_layout.addWidget(self._toolbar)
        main_layout.addWidget(self._canvas)

        # Stats display
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet("padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        main_layout.addWidget(self._stats_label)

        self.setLayout(main_layout)

    def _on_chart_type_changed(self, chart_type: str) -> None:
        """Handle chart type selection change."""
        type_map = {"By Category": "category", "By Month": "month", "Summary": "summary"}
        self._current_chart_type = type_map.get(chart_type, "category")
        self.plot_data()

    def _load_data(self) -> None:
        """Load transactions from db_manager."""
        self._transactions = []
        if not getattr(self, "db_manager", None):
            logger.debug("No db_manager available for ReportsView")
            return

        fetch = getattr(self.db_manager, "fetch_transactions", None)
        if not callable(fetch):
            logger.debug("db_manager has no fetch_transactions method")
            return

        try:
            self._transactions = fetch() or []
            logger.debug("Loaded %d transactions for reports", len(self._transactions))
        except Exception:
            logger.exception("Failed to load transactions for reports")
            self._transactions = []

    def refresh(self) -> None:
        """Refresh data and re-plot."""
        try:
            self._load_data()
            self.plot_data()
        except Exception:
            logger.exception("Failed to refresh reports")

    def _update_stats(self, df=None) -> None:
        """Update statistics label with summary information."""
        if df is None or df.empty:
            self._stats_label.setText("No transactions available")
            return

        try:
            total = df["amount"].sum() if "amount" in df.columns else 0
            count = len(df)
            avg = df["amount"].mean() if "amount" in df.columns else 0
            
            stats_text = f"Total: ${total:,.2f} | Transactions: {count} | Average: ${avg:,.2f}"
            self._stats_label.setText(stats_text)
        except Exception:
            logger.exception("Failed to update statistics")

    def plot_data(self) -> None:
        """Plot based on current chart type and available data."""
        # Clear the existing axis without recreating it
        self._ax.clear()

        # Convert to DataFrame
        df = None
        if self._transactions and pd is not None:
            try:
                df = pd.DataFrame(self._transactions)
            except Exception:
                logger.exception("Failed to create DataFrame from transactions")
                df = None

        # Handle empty state
        if not self._transactions or df is None or df.empty:
            self._ax.text(0.5, 0.5, "No transactions available\nAdd transactions to see statistics", 
                   ha="center", va="center", fontsize=12, color="#666666")
            self._ax.set_xticks([])
            self._ax.set_yticks([])
            self._update_stats(None)
            self._canvas.draw()
            return

        try:
            if self._current_chart_type == "category":
                self._plot_by_category(self._ax, df)
            elif self._current_chart_type == "month":
                self._plot_by_month(self._ax, df)
            elif self._current_chart_type == "summary":
                self._plot_summary(self._ax, df)
            
            self._update_stats(df)
            self._canvas.draw()
        except Exception:
            logger.exception("Failed to plot data for chart type: %s", self._current_chart_type)
            self._ax.clear()
            self._ax.text(0.5, 0.5, "Error rendering chart", ha="center", va="center")
            self._canvas.draw()

    def _plot_by_category(self, ax, df) -> None:
        """Plot transactions grouped by category."""
        if "category" in df.columns and "amount" in df.columns:
            grouped = df.groupby("category")["amount"].sum().sort_values(ascending=False)
            
            # Handle None/null category names
            grouped.index = grouped.index.fillna("Uncategorized")
            
            colors = ["#4c72b0", "#dd8452", "#55a868", "#c44e52", "#8172b3"]
            bar_colors = [colors[i % len(colors)] for i in range(len(grouped))]
            
            ax.bar(range(len(grouped)), grouped.values, color=bar_colors)
            ax.set_xticks(range(len(grouped)))
            ax.set_xticklabels(grouped.index, rotation=45, ha="right")
            ax.set_ylabel("Amount ($)")
            ax.set_title("Spending by Category")
            ax.grid(axis="y", alpha=0.3)
        else:
            ax.text(0.5, 0.5, "Category data unavailable", ha="center", va="center")

    def _plot_by_month(self, ax, df) -> None:
        """Plot transactions aggregated by month."""
        if "date" not in df.columns or "amount" not in df.columns:
            ax.text(0.5, 0.5, "Date data unavailable", ha="center", va="center")
            return

        try:
            df_copy = df.copy()
            df_copy["date"] = pd.to_datetime(df_copy["date"])
            df_copy["month"] = df_copy["date"].dt.to_period("M")
            
            monthly = df_copy.groupby("month")["amount"].sum().sort_index()
            
            ax.plot(range(len(monthly)), monthly.values, marker="o", linewidth=2, markersize=8, color="#4c72b0")
            ax.fill_between(range(len(monthly)), monthly.values, alpha=0.3, color="#4c72b0")
            ax.set_xticks(range(len(monthly)))
            ax.set_xticklabels([str(m) for m in monthly.index], rotation=45, ha="right")
            ax.set_ylabel("Amount ($)")
            ax.set_title("Monthly Spending Trend")
            ax.grid(alpha=0.3)
        except Exception:
            logger.exception("Failed to plot monthly data")
            ax.text(0.5, 0.5, "Error processing date data", ha="center", va="center")

    def _plot_summary(self, ax, df) -> None:
        """Plot a summary with multiple metrics."""
        if "amount" not in df.columns:
            ax.text(0.5, 0.5, "Amount data unavailable", ha="center", va="center")
            return

        try:
            metrics = {
                "Total": df["amount"].sum(),
                "Average": df["amount"].mean(),
                "Max": df["amount"].max(),
                "Min": df["amount"].min(),
            }
            
            colors = ["#4c72b0", "#dd8452", "#55a868", "#c44e52"]
            bars = ax.bar(range(len(metrics)), list(metrics.values()), color=colors)
            
            # Add value labels on bars
            for i, (bar, value) in enumerate(zip(bars, metrics.values())):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                       f"${value:.2f}", ha="center", va="bottom", fontsize=10)
            
            ax.set_xticks(range(len(metrics)))
            ax.set_xticklabels(metrics.keys())
            ax.set_ylabel("Amount ($)")
            ax.set_title("Summary Statistics")
            ax.grid(axis="y", alpha=0.3)
        except Exception:
            logger.exception("Failed to plot summary data")
            ax.text(0.5, 0.5, "Error processing summary", ha="center", va="center")
