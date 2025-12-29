'''
    File Name: test_db.py
    Version: 2.0.1
    Date: 16/09/2025
    Author: Pablo Bartolomé Molina
'''
import os
import csv
from pathlib import Path
import pytest

from database.db_manager import DatabaseManager

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
