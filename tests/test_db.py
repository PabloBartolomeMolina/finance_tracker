'''
    File Name: test_db.py
    Version: 2.0.1
    Date: 16/09/2025
    Author: Pablo Bartolomé Molina
'''
import os
import csv
import warnings
from pathlib import Path
import pytest

from database.db_manager import DatabaseManager

# Show all warnings
warnings.filterwarnings('default')

EPSILON = 1e-6


def test_ensure_and_fetch_empty(tmp_path):
    db_path = tmp_path / "test.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    assert db_path.exists()
    assert dm.fetch_transactions() == []


def test_add_and_fetch_transaction(tmp_path):
    db_path = tmp_path / "test.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    tx = {"description": "Coffee", "amount": 2.5, "date": "2025-12-01", "category": "Food"}
    nid = dm.add_transaction(tx)
    assert isinstance(nid, int) and nid > 0
    fetched = dm.fetch_transaction_by_id(nid)
    assert fetched is not None
    assert fetched["description"] == "Coffee"
    assert abs(float(fetched["amount"]) - 2.5) < EPSILON
    assert fetched["category"] == "Food"
    all_txs = dm.fetch_transactions()
    assert any(t["id"] == nid for t in all_txs)
    cats = dm.fetch_categories()
    assert any(c["name"] == "Food" for c in cats)


def test_update_transaction(tmp_path):
    db_path = tmp_path / "test.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    tx = {"description": "Rent", "amount": 500, "date": "2025-12-01", "category": "Housing"}
    nid = dm.add_transaction(tx)
    assert nid
    updated = {"id": nid, "description": "Rent Dec", "amount": 550, "date": "2025-12-01", "category": "Housing"}
    ok = dm.update_transaction(updated)
    assert ok
    fetched = dm.fetch_transaction_by_id(nid)
    assert fetched["description"] == "Rent Dec"
    assert abs(float(fetched["amount"]) - 550) < EPSILON


def test_delete_transaction(tmp_path):
    db_path = tmp_path / "test.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    tx = {"description": "Temp", "amount": 1, "date": "2025-12-01", "category": "Misc"}
    nid = dm.add_transaction(tx)
    assert nid
    ok = dm.delete_transaction(nid)
    assert ok
    assert dm.fetch_transaction_by_id(nid) is None


def test_fetch_with_filters_and_limit(tmp_path):
    db_path = tmp_path / "test.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    txs = [
        {"description": "A", "amount": 10, "date": "2025-12-01", "category": "X"},
        {"description": "B", "amount": 20, "date": "2025-12-02", "category": "Y"},
        {"description": "C", "amount": 30, "date": "2025-12-03", "category": "X"},
    ]
    ids = []
    for t in txs:
        nid = dm.add_transaction(t)
        assert nid
        ids.append(nid)

    res = dm.fetch_transactions(filters={"category": "X"})
    assert len(res) == 2

    res2 = dm.fetch_transactions(filters={"start_date": "2025-12-02"})
    assert all(r["date"] >= "2025-12-02" for r in res2)

    res3 = dm.fetch_transactions(limit=1)
    assert len(res3) == 1


def test_export_import_csv(tmp_path):
    db_path = tmp_path / "test.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    dm.add_transaction({"description": "E", "amount": 5, "date": "2025-12-01", "category": "Z"})
    csv_path = tmp_path / "out.csv"
    ok = dm.export_to_csv(csv_path)
    assert ok and csv_path.exists()

    dm2_path = tmp_path / "import.db"
    dm2 = DatabaseManager(dm2_path)
    dm2.ensure_database()
    count = dm2.import_from_csv(csv_path)
    assert count >= 1
    all_tx = dm2.fetch_transactions()
    assert any(t["description"] == "E" for t in all_tx)


def test_compact_transaction_ids(tmp_path):
    db_path = tmp_path / "test.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    ids = [dm.add_transaction({"description": f"T{i}", "amount": i, "date": "2025-12-01", "category": "C"}) for i in range(1, 6)]
    assert all(ids)
    mapping = dm.compact_transaction_ids()
    assert isinstance(mapping, dict)
    assert len(mapping) == len(ids)
    new_ids = set(mapping.values())
    assert len(new_ids) == len(ids)
    assert min(new_ids) >= 1

def test_export_to_csv_empty_database(tmp_path):
    """Test exporting from an empty database creates file with headers."""
    db_path = tmp_path / "empty.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    
    csv_path = tmp_path / "export_empty.csv"
    ok = dm.export_to_csv(csv_path)
    
    assert ok
    assert csv_path.exists()
    
    # Check that file has at least the header row
    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert len(rows) >= 1
        assert 'id' in rows[0]
        assert 'amount' in rows[0]


def test_export_to_csv_multiple_transactions(tmp_path):
    """Test exporting multiple transactions to CSV."""
    db_path = tmp_path / "multi.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    
    # Add multiple transactions
    transactions = [
        {"description": "Lunch", "amount": 15.50, "date": "2025-01-01", "category": "Food"},
        {"description": "Gas", "amount": 50.00, "date": "2025-01-02", "category": "Transport"},
        {"description": "Movie", "amount": 12.00, "date": "2025-01-03", "category": "Entertainment"},
    ]
    
    for tx in transactions:
        dm.add_transaction(tx)
    
    csv_path = tmp_path / "export_multi.csv"
    ok = dm.export_to_csv(csv_path)
    
    assert ok
    assert csv_path.exists()
    
    # Verify CSV contains all transactions
    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 3
        descriptions = [r['description'] for r in rows]
        assert 'Lunch' in descriptions
        assert 'Gas' in descriptions
        assert 'Movie' in descriptions


def test_import_from_csv_creates_transactions(tmp_path):
    """Test importing transactions from CSV file."""
    # Create a CSV file
    csv_path = tmp_path / "import.csv"
    rows = [
        {"id": "1", "description": "Import Test", "amount": "99.99", "date": "2025-01-01", "category": "Test"},
        {"id": "2", "description": "Another", "amount": "25.50", "date": "2025-01-02", "category": "Other"},
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'description', 'amount', 'date', 'category'])
        writer.writeheader()
        writer.writerows(rows)
    
    # Import into database
    db_path = tmp_path / "import.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    
    count = dm.import_from_csv(csv_path)
    
    assert count == 2
    all_txs = dm.fetch_transactions()
    assert len(all_txs) == 2
    assert any(t['description'] == 'Import Test' for t in all_txs)


def test_import_from_csv_with_missing_fields(tmp_path):
    """Test importing CSV with missing optional fields."""
    csv_path = tmp_path / "import_missing.csv"
    rows = [
        {"description": "No amount", "date": "2025-01-01"},
        {"amount": "50.00", "date": "2025-01-02"},  # No description
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['description', 'amount', 'date'])
        writer.writeheader()
        writer.writerows(rows)
    
    db_path = tmp_path / "import_missing.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    
    # Should handle missing fields gracefully
    count = dm.import_from_csv(csv_path)
    
    # At least one should be imported
    assert count >= 1


def test_import_from_csv_invalid_file(tmp_path):
    """Test importing from a file that doesn't exist."""
    db_path = tmp_path / "test.db"
    dm = DatabaseManager(db_path)
    dm.ensure_database()
    
    count = dm.import_from_csv(tmp_path / "nonexistent.csv")
    
    # Should return 0 without crashing
    assert count == 0


def test_import_export_roundtrip(tmp_path):
    """Test exporting and then importing data."""
    # Create and populate first database
    db1_path = tmp_path / "db1.db"
    dm1 = DatabaseManager(db1_path)
    dm1.ensure_database()
    
    tx_data = [
        {"description": "Coffee", "amount": 3.50, "date": "2025-01-01", "category": "Food"},
        {"description": "Bus", "amount": 2.50, "date": "2025-01-02", "category": "Transport"},
        {"description": "Movie", "amount": 10.00, "date": "2025-01-03", "category": "Entertainment"},
    ]
    
    for tx in tx_data:
        dm1.add_transaction(tx)
    
    # Export to CSV
    csv_path = tmp_path / "roundtrip.csv"
    export_ok = dm1.export_to_csv(csv_path)
    assert export_ok
    
    # Import into second database
    db2_path = tmp_path / "db2.db"
    dm2 = DatabaseManager(db2_path)
    dm2.ensure_database()
    
    import_count = dm2.import_from_csv(csv_path)
    assert import_count == 3
    
    # Verify data matches
    txs1 = dm1.fetch_transactions()
    txs2 = dm2.fetch_transactions()
    
    assert len(txs1) == len(txs2)
    
    # Check descriptions match
    descs1 = sorted([t['description'] for t in txs1])
    descs2 = sorted([t['description'] for t in txs2])
    assert descs1 == descs2