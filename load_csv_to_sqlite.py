"""Load the Kaggle retail transactions CSV into a SQLite database.

Usage:
    python load_csv_to_sqlite.py

This will:
- Read the CSV file (handling quoted multi-line fields like StoreLocation)
- Create a `transactions` table in the SQLite database
- Insert all rows
- Create useful indexes for querying
"""

import csv
import datetime as dt
import sqlite3
from pathlib import Path

from config import CSV_PATH, DATABASE_PATH


def parse_transaction_date(raw: str) -> str:
    """Parse the CSV TransactionDate into ISO 'YYYY-MM-DD HH:MM' string.

    The CSV appears to use 'MM/DD/YYYY H:MM' (24-hour) format, sometimes with
    '0:00' for midnight. We normalize to ISO format for easier querying.
    """
    raw = raw.strip()
    # Example: 12/26/2023 12:32 or 8/5/2023 0:00
    dt_obj = dt.datetime.strptime(raw, "%m/%d/%Y %H:%M")
    return dt_obj.strftime("%Y-%m-%d %H:%M")


def init_db(conn: sqlite3.Connection) -> None:
    """Create the transactions table (dropping if exists) and indexes."""
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS transactions")

    cur.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            CustomerID INTEGER NOT NULL,
            ProductID TEXT NOT NULL,
            Quantity INTEGER NOT NULL,
            Price REAL NOT NULL,
            TransactionDate TEXT NOT NULL,
            PaymentMethod TEXT NOT NULL,
            StoreLocation TEXT NOT NULL,
            ProductCategory TEXT NOT NULL,
            DiscountAppliedPct REAL NOT NULL,
            TotalAmount REAL NOT NULL
        )
        """
    )

    # Basic indexes to support common queries
    cur.execute("CREATE INDEX idx_transactions_customer ON transactions(CustomerID)")
    cur.execute("CREATE INDEX idx_transactions_product ON transactions(ProductID)")
    cur.execute(
        "CREATE INDEX idx_transactions_date ON transactions(TransactionDate)"
    )
    cur.execute(
        "CREATE INDEX idx_transactions_category ON transactions(ProductCategory)"
    )
    cur.execute(
        "CREATE INDEX idx_transactions_payment ON transactions(PaymentMethod)"
    )

    conn.commit()


def load_csv(conn: sqlite3.Connection, csv_path: Path) -> None:
    """Load all rows from the CSV into the transactions table."""
    cur = conn.cursor()

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        expected_fields = [
            "CustomerID",
            "ProductID",
            "Quantity",
            "Price",
            "TransactionDate",
            "PaymentMethod",
            "StoreLocation",
            "ProductCategory",
            "DiscountApplied(%)",
            "TotalAmount",
        ]
        missing = [c for c in expected_fields if c not in reader.fieldnames]
        if missing:
            raise RuntimeError(
                f"CSV is missing expected columns: {', '.join(missing)}; "
                f"found: {reader.fieldnames}"
            )

        rows = []
        batch_size = 2000
        total = 0

        for row in reader:
            try:
                customer_id = int(row["CustomerID"])
                product_id = row["ProductID"].strip()
                quantity = int(row["Quantity"])
                price = float(row["Price"])
                tx_date = parse_transaction_date(row["TransactionDate"])
                payment_method = row["PaymentMethod"].strip()
                store_location = row["StoreLocation"].strip()
                product_category = row["ProductCategory"].strip()
                discount_pct = float(row["DiscountApplied(%)"])
                total_amount = float(row["TotalAmount"])
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(f"Failed to parse row: {row}") from exc

            rows.append(
                (
                    customer_id,
                    product_id,
                    quantity,
                    price,
                    tx_date,
                    payment_method,
                    store_location,
                    product_category,
                    discount_pct,
                    total_amount,
                )
            )

            if len(rows) >= batch_size:
                cur.executemany(
                    """
                    INSERT INTO transactions (
                        CustomerID,
                        ProductID,
                        Quantity,
                        Price,
                        TransactionDate,
                        PaymentMethod,
                        StoreLocation,
                        ProductCategory,
                        DiscountAppliedPct,
                        TotalAmount
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                conn.commit()
                total += len(rows)
                rows.clear()
                print(f"Inserted {total} rows...")

        if rows:
            cur.executemany(
                """
                INSERT INTO transactions (
                    CustomerID,
                    ProductID,
                    Quantity,
                    Price,
                    TransactionDate,
                    PaymentMethod,
                    StoreLocation,
                    ProductCategory,
                    DiscountAppliedPct,
                    TotalAmount
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
            total += len(rows)

    print(f"Finished inserting {total} rows into transactions.")


def main() -> None:
    csv_path = Path(CSV_PATH)
    db_path = Path(DATABASE_PATH)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found at {csv_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Using CSV: {csv_path}")
    print(f"Creating SQLite DB at: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        init_db(conn)
        load_csv(conn, csv_path)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

