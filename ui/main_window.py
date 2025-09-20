'''
    File Name: main_window.py
    Version: 1.1.0
    Date: 16/09/2025
    Author: Pablo Bartolomé Molina
'''
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QGroupBox
)
from PyQt5.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Finance Tracker Python app")
        self.resize(600, 400)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        main_layout.addWidget(self.text_display)

        # Transactions group
        transaction_group = QGroupBox("Transactions")
        t_layout = QHBoxLayout()
        self.button1 = QPushButton("Add")
        self.button2 = QPushButton("Edit")
        self.button3 = QPushButton("Delete")
        t_layout.addWidget(self.button1)
        t_layout.addWidget(self.button2)
        t_layout.addWidget(self.button3)
        transaction_group.setLayout(t_layout)
        main_layout.addWidget(transaction_group)

        # Reports / Utilities group
        report_group = QGroupBox("Reports & Utilities")
        r_layout = QHBoxLayout()
        self.button4 = QPushButton("Filter/Search")
        self.button5 = QPushButton("Statistics")
        self.button6 = QPushButton("Import/Export")
        r_layout.addWidget(self.button4)
        r_layout.addWidget(self.button5)
        r_layout.addWidget(self.button6)
        report_group.setLayout(r_layout)
        main_layout.addWidget(report_group)

        # Connect buttons
        for i, btn in enumerate([self.button1, self.button2, self.button3,
                                 self.button4, self.button5, self.button6], 1):
            btn.clicked.connect(lambda _, x=i: self.update_text(f"Button {x} clicked"))

        central_widget.setLayout(main_layout)

        # Optional: simple styling
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid gray;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QPushButton {
                min-width: 100px;
                padding: 5px;
            }
            QTextEdit {
                font-family: Consolas, monospace;
                font-size: 12pt;
            }
        """)

    def update_text(self, message: str):
        self.text_display.append(message)
