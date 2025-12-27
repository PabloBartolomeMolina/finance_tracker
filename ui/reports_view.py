'''
    File Name: reports_view.py
    Version: 1.0.0
    Date: 16/09/2025
    Author: Pablo Bartolomé Molina
'''
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT

try:
    import pandas as pd
except Exception:
    pd = None


class ReportsView(QWidget):
    """Simple reports view with a matplotlib canvas and a refresh button.

    The view is intentionally lightweight: if a `db_manager` with a
    `fetch_transactions()` method is provided it will attempt to read
    transaction rows and plot a small summary. Otherwise a placeholder
    example chart is shown.
    """

    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._figure = Figure(figsize=(5, 3))
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._toolbar = NavigationToolbar2QT(self._canvas, self)

        self.setup_ui()
        # Initial plot
        try:
            self.plot_example()
        except Exception:
            # keep UI resilient if plotting fails
            pass

    def setup_ui(self) -> None:
        """Build the simple UI: title label, toolbar, canvas and refresh button."""
        layout = QVBoxLayout()
        title = QLabel("Reports & Statistics")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)

        layout.addWidget(title)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._canvas)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)

    def refresh(self) -> None:
        """Public method to refresh the report (re-plot)."""
        try:
            self.plot_example()
        except Exception:
            # swallow exceptions to avoid crashing the UI; callers may inspect logs
            pass

    def plot_example(self, transactions=None) -> None:
        """Plot a simple summary from `transactions` or from `db_manager`.

        Expected `transactions` format: iterable of dict-like objects with at
        least an `amount` numeric field and optionally a `date` or `category`.
        The method is defensive and falls back to a sample chart if data is
        missing or invalid.
        """
        # Acquire data
        txs = transactions
        if txs is None and getattr(self, "db_manager", None) is not None:
            fetch = getattr(self.db_manager, "fetch_transactions", None)
            if callable(fetch):
                try:
                    txs = fetch()
                except Exception:
                    txs = None

        # Fallback sample data
        if not txs:
            txs = [
                {"label": "Sample A", "amount": 120},
                {"label": "Sample B", "amount": 80},
                {"label": "Sample C", "amount": 200},
            ]

        # Normalize into DataFrame if pandas available
        df = None
        if pd is not None:
            try:
                df = pd.DataFrame(txs)
            except Exception:
                df = None

        ax = self._figure.subplots()
        ax.clear()

        try:
            if df is not None and "amount" in df.columns:
                # If 'label' or 'category' exists, aggregate by it; otherwise sum all
                if "label" in df.columns:
                    grouped = df.groupby("label")["amount"].sum()
                    labels = list(grouped.index.astype(str))
                    values = list(grouped.values)
                elif "category" in df.columns:
                    grouped = df.groupby("category")["amount"].sum()
                    labels = list(grouped.index.astype(str))
                    values = list(grouped.values)
                else:
                    # fall back to simple indexed bars
                    values = df["amount"].tolist()
                    labels = [str(i + 1) for i in range(len(values))]

                ax.bar(labels, values, color="#4c72b0")
                ax.set_ylabel("Amount")
                ax.set_title("Amounts summary")
                ax.set_xticklabels(labels, rotation=45, ha="right")
            else:
                # Plain sample plot (no pandas or unable to parse data)
                labels = [str(x.get("label", idx + 1)) for idx, x in enumerate(txs)]
                values = [float(x.get("amount", 0)) for x in txs]
                ax.bar(labels, values, color="#4c72b0")
                ax.set_ylabel("Amount")
                ax.set_title("Sample report")

            self._figure.tight_layout()
            self._canvas.draw()
        except Exception:
            # Last-resort: clear figure and show text
            ax.clear()
            ax.text(0.5, 0.5, "Unable to render report", ha="center", va="center")
            self._canvas.draw()
