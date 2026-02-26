"""Pytest fixtures: test database for Flask API tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from load_csv_to_sqlite import init_db


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Create a temporary SQLite DB with transactions schema and minimal test data."""
    db_path = tmp_path / "test_retail.db"
    conn = sqlite3.connect(db_path)
    try:
        init_db(conn)
        cur = conn.cursor()
        # Insert a few rows so metrics and customer/product endpoints return data
        rows = [
            (1, "A", 2, 10.0, "2024-01-15 12:00", "Cash", "Store 1", "Books", 0.0, 20.0),
            (1, "B", 1, 5.0, "2024-02-01 09:00", "Card", "Store 2", "Electronics", 10.0, 4.5),
            (2, "A", 3, 10.0, "2024-01-20 14:00", "PayPal", "Store 1", "Books", 0.0, 30.0),
        ]
        cur.executemany(
            """
            INSERT INTO transactions (
                CustomerID, ProductID, Quantity, Price, TransactionDate,
                PaymentMethod, StoreLocation, ProductCategory, DiscountAppliedPct, TotalAmount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()
    return db_path
