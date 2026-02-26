"""Unit tests for Flask API: metrics and customer/product endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def flask_client(test_db_path):
    """Flask test client with DATABASE_PATH patched to test DB."""
    with patch("flask_app.DATABASE_PATH", str(test_db_path)):
        from flask_app import app
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client


class TestMetricsSummary:
    """GET /api/metrics/summary."""

    def test_summary_returns_200_and_structure(self, flask_client) -> None:
        r = flask_client.get("/api/metrics/summary")
        assert r.status_code == 200
        data = r.get_json()
        assert "filters" in data
        assert "summary" in data
        if data["summary"]:
            assert "transactionCount" in data["summary"]
            assert "totalRevenue" in data["summary"]

    def test_summary_with_date_params_returns_200(self, flask_client) -> None:
        r = flask_client.get(
            "/api/metrics/summary",
            query_string={"from": "2024-01-01", "to": "2024-12-31"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data["filters"]["from"] == "2024-01-01"
        assert data["filters"]["to"] == "2024-12-31"


class TestMetricsByCategory:
    """GET /api/metrics/by_category."""

    def test_by_category_returns_200_and_metrics_list(self, flask_client) -> None:
        r = flask_client.get("/api/metrics/by_category")
        assert r.status_code == 200
        data = r.get_json()
        assert "metrics" in data
        assert "filters" in data


class TestMetricsTopCustomers:
    """GET /api/metrics/top_customers."""

    def test_top_customers_default_limit(self, flask_client) -> None:
        r = flask_client.get("/api/metrics/top_customers")
        assert r.status_code == 200
        data = r.get_json()
        assert "metrics" in data
        assert data["limit"] == 5
        assert len(data["metrics"]) <= 10

    def test_top_customers_with_limit_param(self, flask_client) -> None:
        r = flask_client.get("/api/metrics/top_customers", query_string={"limit": 2})
        assert r.status_code == 200
        data = r.get_json()
        assert data["limit"] == 2
        assert len(data["metrics"]) <= 2


class TestCustomerEndpoint:
    """GET /api/customers/<id>."""

    def test_customer_exists_returns_200(self, flask_client) -> None:
        r = flask_client.get("/api/customers/1")
        assert r.status_code == 200
        data = r.get_json()
        assert data["customerId"] == 1
        assert "transactions" in data
        assert "summary" in data

    def test_customer_no_transactions_returns_200_empty(self, flask_client) -> None:
        r = flask_client.get("/api/customers/99999")
        assert r.status_code == 200
        data = r.get_json()
        assert data["customerId"] == 99999
        assert data["transactions"] == []
        assert data["summary"] is None


class TestProductEndpoint:
    """GET /api/products/<id>."""

    def test_product_exists_returns_200(self, flask_client) -> None:
        r = flask_client.get("/api/products/A")
        assert r.status_code == 200
        data = r.get_json()
        assert data["productId"] == "A"
        assert "transactions" in data
        assert "summary" in data

    def test_product_not_found_returns_200_empty(self, flask_client) -> None:
        r = flask_client.get("/api/products/NonexistentID")
        assert r.status_code == 200
        data = r.get_json()
        assert data["productId"] == "NonexistentID"
        assert data["transactions"] == []
