Personal Finance Tracker
====================================================

Description
-------------
A desktop application to track your personal income and expenses.
Built with Python and PyQt6, with data stored in a local SQLite database.
It allows you to add, edit, delete, and categorize transactions, and view reports with charts.

Features
----------
- Add, edit, and delete transactions
- Categorize transactions (Food, Rent, Salary, Entertainment, etc.)
- View transactions in a table with sorting and filtering
- Charts showing expenses by category and monthly trends
- Import and export transactions via CSV
- Simple and intuitive GUI

Requirements
-------------
- Python 3.10+
- PyQt6
- matplotlib
- pandas
- sqlite3 (built-in)

Installation
-------------
1. Clone or download the project folder.
2. Create a virtual environment (optional but recommended):
   python -m venv venv
3. Activate the virtual environment:
   - Windows: venv\Scripts\activate
   - Mac/Linux: source venv/bin/activate
4. Install dependencies:
   pip install -r requirements.txt
5. Run the application:
   python main.py

Project Structure
------------------

```
finance_tracker/
│
├── main.py                  # Entry point
├── config.py                # App configuration
├── database/                # Database manager and schema
├── models/                  # Data models
├── ui/                      # GUI windows and dialogs
├── resources/               # Icons and styles
├── data/                    # SQLite database file
├── tests/                   # Unit tests
├── README.md                # This file
└── requirements.txt         # Python dependencies
```

Usage
-------
- Launch the app via main.py
- Add transactions via the form
- View transactions in the main table
- Check reports in the Reports tab
- Export/Import transactions using the File menu

License
---------
This project is free to use and modify.
