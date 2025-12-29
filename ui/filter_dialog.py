'''
    File Name: filter_dialog.py
    Version: 1.0.0
    Date: 29/12/2025
    Author: Pablo Bartolomé Molina
'''
from typing import Iterable, List, Optional, Tuple
from PyQt6 import QtWidgets, QtCore


class FilterDialog(QtWidgets.QDialog):
    """Simple dialog to collect filter/search criteria for transactions.

    Returns a tuple of (filters_dict, limit) from `get_filters()` where
    `filters_dict` may contain 'category', 'start_date', 'end_date'.
    """

    def __init__(self, parent=None, categories: Optional[Iterable[str]] = None):
        super().__init__(parent)
        self.setWindowTitle("Filter / Search Transactions")
        self.resize(420, 180)

        layout = QtWidgets.QVBoxLayout()
        form = QtWidgets.QFormLayout()

        self.category = QtWidgets.QComboBox()
        self.category.addItem("")
        if categories:
            for c in categories:
                try:
                    self.category.addItem(str(c))
                except Exception:
                    # ignore malformed category entries
                    pass

        self.start_date = QtWidgets.QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        # default to one month ago
        self.start_date.setDate(QtCore.QDate.currentDate().addMonths(-1))

        self.end_date = QtWidgets.QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QtCore.QDate.currentDate())

        self.limit = QtWidgets.QSpinBox()
        self.limit.setRange(0, 100000)
        self.limit.setValue(100)
        self.limit.setSpecialValueText("No limit")

        form.addRow("Category:", self.category)
        form.addRow("Start date:", self.start_date)
        form.addRow("End date:", self.end_date)
        form.addRow("Limit (0 = no limit):", self.limit)

        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_filters(self) -> Tuple[dict, Optional[int]]:
        """Return (filters, limit).

        `filters` contains only keys with non-empty values.
        """
        f = {}
        try:
            cat = self.category.currentText().strip()
            if cat:
                f["category"] = cat
        except Exception:
            pass

        try:
            sd = self.start_date.date().toString("yyyy-MM-dd")
            ed = self.end_date.date().toString("yyyy-MM-dd")
            if sd:
                f["start_date"] = sd
            if ed:
                f["end_date"] = ed
        except Exception:
            pass

        lim = self.limit.value()
        if lim == 0:
            lim = None

        return f, lim
