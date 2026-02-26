"""Unit tests for services.query_router: _interpret_date_range and route_intent."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from schemas.intent import Intent
from services.query_router import _interpret_date_range, route_intent


class TestInterpretDateRange:
    """Tests for _interpret_date_range."""

    def test_valid_range(self) -> None:
        start, end = _interpret_date_range("2024-01-01..2024-12-31")
        assert start == "2024-01-01"
        assert end == "2024-12-31"

    def test_empty_none(self) -> None:
        assert _interpret_date_range(None) == (None, None)
        assert _interpret_date_range("") == (None, None)

    def test_whitespace_only(self) -> None:
        start, end = _interpret_date_range("   ")
        assert start is None
        assert end is None

    def test_no_double_dot_returns_none(self) -> None:
        """Current behavior: string without '..' is not parsed."""
        assert _interpret_date_range("2024-01-01") == (None, None)


class TestRouteIntentCustomer:
    """Tests for route_intent when intent is customer."""

    def test_customer_no_id_returns_ambiguous(self) -> None:
        intent = Intent(intent="customer", customer_id=None)
        result = route_intent(intent)
        assert result.data["status"] == "ambiguous_intent"
        assert result.data["reason"] == "customer_id_missing"

    @patch("services.query_router.data_service.get_customer")
    def test_customer_with_id_trims_transactions_to_15(
        self, mock_get_customer: object
    ) -> None:
        mock_get_customer.return_value = {
            "customerId": 1,
            "transactions": [{"id": i} for i in range(30)],
            "summary": {"transactionCount": 30, "totalSpend": 100.0},
            "filters": {},
        }
        intent = Intent(intent="customer", customer_id=1)
        result = route_intent(intent)
        assert len(result.data["transactions"]) == 15
        assert result.data["transactionCount"] == 30
        assert result.data["transactionsLimit"] == 15
        assert result.data["transactionsTruncated"] is True

    @patch("services.query_router.data_service.get_customer")
    def test_customer_no_data_returns_no_data_status(
        self, mock_get_customer: object
    ) -> None:
        mock_get_customer.return_value = {
            "customerId": 999,
            "transactions": [],
            "summary": None,
            "filters": {},
        }
        intent = Intent(intent="customer", customer_id=999)
        result = route_intent(intent)
        assert result.data["status"] == "no_data"
        assert result.data["reason"] == "no_customer_transactions"


class TestRouteIntentProduct:
    """Tests for route_intent when intent is product."""

    def test_product_no_id_returns_ambiguous(self) -> None:
        intent = Intent(intent="product", product_id=None)
        result = route_intent(intent)
        assert result.data["status"] == "ambiguous_intent"
        assert result.data["reason"] == "product_id_missing"

    @patch("services.query_router.data_service.get_product")
    def test_product_trims_stores_to_15(self, mock_get_product: object) -> None:
        mock_get_product.return_value = {
            "productId": "A",
            "transactions": [],
            "summary": {
                "transactionCount": 5,
                "totalQuantity": 10,
                "totalRevenue": 100.0,
                "stores": [f"Store {i}" for i in range(25)],
            },
            "filters": {},
        }
        intent = Intent(intent="product", product_id="A")
        result = route_intent(intent)
        summary = result.data["summary"]
        assert len(summary["stores"]) == 15
        assert summary["storeCount"] == 25
        assert summary["storesLimit"] == 15
        assert summary["storesTruncated"] is True


class TestRouteIntentBusinessMetric:
    """Tests for route_intent when intent is business_metric."""

    def test_business_metric_empty_returns_ambiguous(self) -> None:
        intent = Intent(intent="business_metric", metric=None)
        result = route_intent(intent)
        assert result.data["status"] == "ambiguous_intent"
        assert result.data["reason"] == "business_metric_unspecified"
        assert "supportedMetrics" in result.data

    def test_business_metric_whitespace_returns_ambiguous(self) -> None:
        intent = Intent(intent="business_metric", metric="   ")
        result = route_intent(intent)
        assert result.data["status"] == "ambiguous_intent"
        assert result.data["reason"] == "business_metric_unspecified"

    @patch("services.query_router.data_service.get_metrics_summary")
    def test_business_metric_summary_calls_summary(
        self, mock_get_summary: object
    ) -> None:
        mock_get_summary.return_value = {
            "summary": {"totalRevenue": 1000, "transactionCount": 50},
            "filters": {},
        }
        intent = Intent(intent="business_metric", metric="summary")
        result = route_intent(intent)
        assert result.data["summary"]["totalRevenue"] == 1000
        mock_get_summary.assert_called_once()

    @patch("services.query_router.data_service.get_metrics_by_category")
    def test_business_metric_metrics_by_category_calls_by_category(
        self, mock_get: object
    ) -> None:
        mock_get.return_value = {"metrics": [{"ProductCategory": "Books"}], "filters": {}}
        intent = Intent(intent="business_metric", metric="metrics_by_category")
        result = route_intent(intent)
        assert "metrics" in result.data
        mock_get.assert_called_once()

    @patch("services.query_router.data_service.get_metrics_summary")
    def test_business_metric_unknown_returns_unsupported(self, mock_summary: object) -> None:
        intent = Intent(intent="business_metric", metric="churn_rate")
        result = route_intent(intent)
        assert result.data["status"] == "unsupported_metric"
        assert result.data["reason"] == "metric_not_recognized"
        assert "supportedMetrics" in result.data
        mock_summary.assert_not_called()
