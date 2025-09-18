'''
    File Name: main_window.py
    Version: 1.1.0
    Date: 16/09/2025
    Author: Pablo Bartolomé Molina
'''
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QTextEdit


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyQt Main Window Example")

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()

        # Text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        layout.addWidget(self.text_display)

        # Buttons
        self.button1 = QPushButton("Add transaction")
        self.button2 = QPushButton("Edit transaction")
        self.button3 = QPushButton("Delete transaction")
        self.button4 = QPushButton("Filter/Searh transactions")
        self.button5 = QPushButton("View Statistics")
        self.button6 = QPushButton("Import/Export")

        layout.addWidget(self.button1)
        layout.addWidget(self.button2)
        layout.addWidget(self.button3)
        layout.addWidget(self.button4)
        layout.addWidget(self.button5)
        layout.addWidget(self.button6)

        # Connect buttons to methods
        self.button1.clicked.connect(lambda: self.update_text("Button 1 clicked"))
        self.button2.clicked.connect(lambda: self.update_text("Button 2 clicked"))
        self.button3.clicked.connect(lambda: self.update_text("Button 3 clicked"))

        # Set layout
        central_widget.setLayout(layout)

    def update_text(self, message: str):
        """Append a message to the text display."""
        self.text_display.append(message)
