"""Unit tests for services.data_service: HTTP URLs and params (mocked requests)."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from services import data_service


class TestGetCustomer:
    """get_customer builds correct URL and params."""

    @patch("services.data_service.requests.get")
    def test_customer_url_and_date_params(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"customerId": 123, "transactions": [], "summary": None}
        mock_get.return_value = mock_resp

        data_service.get_customer(123, date_from="2024-01-01", date_to="2024-12-31")

        mock_get.assert_called_once()
        url = mock_get.call_args[0][0]
        assert "/api/customers/123" in url
        call_kw = mock_get.call_args[1]
        assert call_kw["params"]["from"] == "2024-01-01"
        assert call_kw["params"]["to"] == "2024-12-31"


class TestGetMetricsByPayment:
    """get_metrics_by_payment builds correct URL and params."""

    @patch("services.data_service.requests.get")
    def test_by_payment_url_and_params(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"metrics": [], "filters": {}}
        mock_get.return_value = mock_resp

        data_service.get_metrics_by_payment(
            date_from="2024-01-01", date_to="2024-12-31"
        )

        mock_get.assert_called_once()
        url = mock_get.call_args[0][0]
        assert "/api/metrics/by_payment" in url
        call_kw = mock_get.call_args[1]
        assert call_kw["params"]["from"] == "2024-01-01"
        assert call_kw["params"]["to"] == "2024-12-31"


class TestGetTopCustomers:
    """get_top_customers includes limit and date params."""

    @patch("services.data_service.requests.get")
    def test_top_customers_limit_and_dates(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"metrics": [], "filters": {}, "limit": 5}
        mock_get.return_value = mock_resp

        data_service.get_top_customers(
            limit=5, date_from="2024-01-01", date_to="2024-12-31"
        )

        mock_get.assert_called_once()
        call_kw = mock_get.call_args[1]
        assert call_kw["params"]["limit"] == 5
        assert call_kw["params"]["from"] == "2024-01-01"
        assert call_kw["params"]["to"] == "2024-12-31"
