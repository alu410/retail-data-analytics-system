"""REST API exposing retail transaction data from a SQLite database.

Run:
    export FLASK_APP=flask_app.py
    flask run --reload

The API expects the SQLite database to already be populated via
`load_csv_to_sqlite.py`.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Tuple

from flask import Flask, jsonify, request

from config import DATABASE_PATH
from llm import intent_parser, response_generator
from schemas.intent import Intent
from services import query_router


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


app = Flask(__name__)


@app.route("/api/customers/<int:customer_id>", methods=["GET"])
def get_customer(customer_id: int):
    """Return all transactions and simple aggregates for a given customer.

    Query params: from, to (YYYY-MM-DD) to filter by transaction date.
    """
    date_from, date_to = _parse_date_range_params()
    date_where, date_params = _build_date_range_where(date_from, date_to)
    if date_where:
        customer_where = "WHERE CustomerID = ? AND " + date_where.replace("WHERE ", "")
        all_params: Tuple[Any, ...] = (customer_id,) + tuple(date_params)
    else:
        customer_where = "WHERE CustomerID = ?"
        all_params = (customer_id,)

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            f"""
            SELECT *
            FROM transactions
            {customer_where}
            ORDER BY TransactionDate ASC
            """,
            all_params,
        )
        rows = cur.fetchall()

        if not rows:
            return jsonify({
                "customerId": customer_id,
                "transactions": [],
                "summary": None,
                "filters": {"from": date_from, "to": date_to},
            }), 200

        cur.execute(
            f"""
            SELECT
                COUNT(*) AS transactionCount,
                SUM(TotalAmount) AS totalSpend,
                MIN(TransactionDate) AS firstTransaction,
                MAX(TransactionDate) AS lastTransaction
            FROM transactions
            {customer_where}
            """,
            all_params,
        )
        summary_row = cur.fetchone()

        return jsonify(
            {
                "customerId": customer_id,
                "transactions": [dict(r) for r in rows],
                "summary": dict(summary_row) if summary_row else None,
                "filters": {"from": date_from, "to": date_to},
            }
        )
    finally:
        conn.close()


@app.route("/api/products/<product_id>", methods=["GET"])
def get_product(product_id: str):
    """Return all transactions and aggregates for a product: revenue, avg discount, stores.

    Query params: from, to (YYYY-MM-DD) to filter by transaction date.
    """
    product_id = product_id.strip()
    date_from, date_to = _parse_date_range_params()
    date_where, date_params = _build_date_range_where(date_from, date_to)
    if date_where:
        product_where = "WHERE ProductID = ? AND " + date_where.replace("WHERE ", "")
        all_params: Tuple[Any, ...] = (product_id,) + tuple(date_params)
    else:
        product_where = "WHERE ProductID = ?"
        all_params = (product_id,)

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            f"""
            SELECT *
            FROM transactions
            {product_where}
            ORDER BY TransactionDate ASC
            """,
            all_params,
        )
        rows = cur.fetchall()

        if not rows:
            return jsonify({
                "productId": product_id,
                "transactions": [],
                "summary": None,
                "filters": {"from": date_from, "to": date_to},
            }), 200

        cur.execute(
            f"""
            SELECT
                COUNT(*) AS transactionCount,
                SUM(Quantity) AS totalQuantity,
                SUM(TotalAmount) AS totalRevenue,
                COUNT(DISTINCT CustomerID) AS uniqueCustomers,
                AVG(DiscountAppliedPct) AS averageDiscountPct
            FROM transactions
            {product_where}
            """,
            all_params,
        )
        summary_row = cur.fetchone()

        cur.execute(
            f"""
            SELECT DISTINCT StoreLocation
            FROM transactions
            {product_where}
            ORDER BY StoreLocation
            """,
            all_params,
        )
        stores = [r["StoreLocation"] for r in cur.fetchall()]

        summary = dict(summary_row) if summary_row else None
        if summary is not None:
            summary["stores"] = stores
            summary["storeCount"] = len(stores)

        return jsonify(
            {
                "productId": product_id,
                "transactions": [dict(r) for r in rows],
                "summary": summary,
                "filters": {"from": date_from, "to": date_to},
            }
        )
    finally:
        conn.close()


def _parse_date_range_params() -> Tuple[str | None, str | None]:
    """Parse optional from/to date query parameters (YYYY-MM-DD)."""
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    return date_from, date_to


def _build_date_range_where(
    date_from: str | None, date_to: str | None
) -> Tuple[str, List[Any]]:
    """Build WHERE clause and params for date range using TransactionDate prefix."""
    clauses: List[str] = []
    params: List[Any] = []

    # TransactionDate stored as 'YYYY-MM-DD HH:MM'
    if date_from:
        clauses.append("TransactionDate >= ?")
        params.append(f"{date_from} 00:00")
    if date_to:
        clauses.append("TransactionDate <= ?")
        params.append(f"{date_to} 23:59")

    if clauses:
        return "WHERE " + " AND ".join(clauses), params
    return "", params


@app.route("/api/metrics/summary", methods=["GET"])
def metrics_summary():
    """High-level KPIs: total revenue, transaction count, customer & product counts."""
    date_from, date_to = _parse_date_range_params()
    where_sql, params = _build_date_range_where(date_from, date_to)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT
                COUNT(*) AS transactionCount,
                SUM(TotalAmount) AS totalRevenue,
                COUNT(DISTINCT CustomerID) AS uniqueCustomers,
                COUNT(DISTINCT ProductID) AS uniqueProducts,
                MIN(TransactionDate) AS firstTransaction,
                MAX(TransactionDate) AS lastTransaction
            FROM transactions
            {where_sql}
            """,
            params,
        )
        row = cur.fetchone()

        return jsonify(
            {
                "filters": {"from": date_from, "to": date_to},
                "summary": dict(row) if row else None,
            }
        )
    finally:
        conn.close()


@app.route("/api/metrics/by_category", methods=["GET"])
def metrics_by_category():
    """Revenue and transaction count grouped by product category."""
    date_from, date_to = _parse_date_range_params()
    where_sql, params = _build_date_range_where(date_from, date_to)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT
                ProductCategory,
                COUNT(*) AS transactionCount,
                SUM(Quantity) AS totalQuantity,
                SUM(TotalAmount) AS totalRevenue
            FROM transactions
            {where_sql}
            GROUP BY ProductCategory
            ORDER BY totalRevenue DESC
            """,
            params,
        )
        rows = cur.fetchall()

        return jsonify(
            {
                "filters": {"from": date_from, "to": date_to},
                "metrics": [dict(r) for r in rows],
            }
        )
    finally:
        conn.close()


@app.route("/api/metrics/by_payment", methods=["GET"])
def metrics_by_payment():
    """Revenue, transaction count, and quantity (units) sold grouped by payment method."""
    date_from, date_to = _parse_date_range_params()
    where_sql, params = _build_date_range_where(date_from, date_to)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT
                PaymentMethod,
                COUNT(*) AS transactionCount,
                SUM(Quantity) AS totalQuantity,
                SUM(TotalAmount) AS totalRevenue
            FROM transactions
            {where_sql}
            GROUP BY PaymentMethod
            ORDER BY totalRevenue DESC
            """,
            params,
        )
        rows = cur.fetchall()

        return jsonify(
            {
                "filters": {"from": date_from, "to": date_to},
                "metrics": [dict(r) for r in rows],
            }
        )
    finally:
        conn.close()


@app.route("/api/metrics/top_customers", methods=["GET"])
def metrics_top_customers():
    """Top N customers by total revenue (max 15)."""
    try:
        requested_limit = int(request.args.get("limit", "5"))
    except ValueError:
        requested_limit = 5
    limit = max(1, min(requested_limit, 15))

    date_from, date_to = _parse_date_range_params()
    where_sql, params = _build_date_range_where(date_from, date_to)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT
                CustomerID,
                COUNT(*) AS transactionCount,
                SUM(TotalAmount) AS totalRevenue
            FROM transactions
            {where_sql}
            GROUP BY CustomerID
            ORDER BY totalRevenue DESC
            LIMIT {limit}
            """,
            params,
        )
        rows = cur.fetchall()

        out = {
            "filters": {"from": date_from, "to": date_to},
            "limit": limit,
            "metrics": [dict(r) for r in rows],
        }
        if requested_limit > 15:
            out["limitRequested"] = requested_limit
            out["limitApplied"] = 15
        return jsonify(out)
    finally:
        conn.close()


@app.route("/api/metrics/top_products", methods=["GET"])
def metrics_top_products():
    """Top N products by total revenue and quantity (max 15)."""
    try:
        requested_limit = int(request.args.get("limit", "5"))
    except ValueError:
        requested_limit = 5
    limit = max(1, min(requested_limit, 15))

    date_from, date_to = _parse_date_range_params()
    where_sql, params = _build_date_range_where(date_from, date_to)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT
                ProductID,
                COUNT(*) AS transactionCount,
                SUM(Quantity) AS totalQuantity,
                SUM(TotalAmount) AS totalRevenue
            FROM transactions
            {where_sql}
            GROUP BY ProductID
            ORDER BY totalRevenue DESC, totalQuantity DESC
            LIMIT {limit}
            """,
            params,
        )
        rows = cur.fetchall()

        out = {
            "filters": {"from": date_from, "to": date_to},
            "limit": limit,
            "metrics": [dict(r) for r in rows],
        }
        if requested_limit > 15:
            out["limitRequested"] = requested_limit
            out["limitApplied"] = 15
        return jsonify(out)
    finally:
        conn.close()


@app.route("/chat", methods=["POST"])
def chat():
    """LLM-powered chat endpoint over the retail analytics API."""
    payload = request.get_json(silent=True) or {}
    user_query = payload.get("query")

    if not isinstance(user_query, str) or not user_query.strip():
        return (
            jsonify({"error": "BadRequest", "message": "Field 'query' (non-empty string) is required."}),
            400,
        )

    user_query = user_query.strip()

    # 1) Parse intent with Gemini
    try:
        intent: Intent = intent_parser.parse_intent(user_query)
    except Exception as exc:  # noqa: BLE001
        return (
            jsonify(
                {
                    "error": "IntentParsingFailed",
                    "message": str(exc),
                }
            ),
            400,
        )

    # 2) Deterministically route to data service(s)
    try:
        routed = query_router.route_intent(intent)
    except Exception as exc:  # noqa: BLE001
        return (
            jsonify(
                {
                    "error": "RoutingFailed",
                    "message": str(exc),
                    "intent": intent.model_dump(),
                }
            ),
            400,
        )

    routed_payload = routed.to_dict()

    # 3) Generate natural language answer with Gemini
    try:
        answer = response_generator.generate_response(
            user_query=user_query,
            data=routed_payload,
        )
    except Exception as exc:  # noqa: BLE001
        # Fall back to returning structured data only
        return (
            jsonify(
                {
                    "error": "ResponseGenerationFailed",
                    "message": str(exc),
                    "intent": intent.model_dump(),
                    "data": routed_payload,
                }
            ),
            502,
        )

    return jsonify(
        {
            "intent": intent.model_dump(),
            "data": routed_payload,
            "answer": answer,
        }
    )


if __name__ == "__main__":
    # For local development without FLASK_APP env var
    app.run(debug=True)
