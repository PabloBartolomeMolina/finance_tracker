'''
    File Name: main.py
    Version: 1.1.0
    Date: 16/09/2025
    Author: Pablo Bartolomé Molina
'''
import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
