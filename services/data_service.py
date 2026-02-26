"""Data service that calls the existing Flask REST API over HTTP.

This keeps all HTTP details in one place so the query router only deals with
structured Python objects.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from config import API_BASE_URL


class DataServiceError(Exception):
    """Raised when data retrieval from the API fails."""


def _handle_response(resp: requests.Response) -> Dict[str, Any]:
    if not resp.ok:
        raise DataServiceError(f"API request failed: {resp.status_code} {resp.text}")
    try:
        return resp.json()
    except ValueError as exc:
        raise DataServiceError("API response was not valid JSON") from exc


def get_customer(
    customer_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/api/customers/{customer_id}"
    params = {}
    if date_from:
        params["from"] = date_from
    if date_to:
        params["to"] = date_to
    resp = requests.get(url, params=params or None, timeout=10)
    return _handle_response(resp)


def get_product(
    product_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/api/products/{product_id}"
    params = {}
    if date_from:
        params["from"] = date_from
    if date_to:
        params["to"] = date_to
    resp = requests.get(url, params=params or None, timeout=10)
    return _handle_response(resp)


def get_metrics_summary(date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/api/metrics/summary"
    params = {}
    if date_from:
        params["from"] = date_from
    if date_to:
        params["to"] = date_to
    resp = requests.get(url, params=params or None, timeout=10)
    return _handle_response(resp)


def get_metrics_by_category(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/api/metrics/by_category"
    params = {}
    if date_from:
        params["from"] = date_from
    if date_to:
        params["to"] = date_to
    resp = requests.get(url, params=params or None, timeout=10)
    return _handle_response(resp)


def get_metrics_by_payment(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/api/metrics/by_payment"
    params = {}
    if date_from:
        params["from"] = date_from
    if date_to:
        params["to"] = date_to
    resp = requests.get(url, params=params or None, timeout=10)
    return _handle_response(resp)


def get_top_customers(
    limit: int = 5,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/api/metrics/top_customers"
    params = {"limit": limit}
    if date_from:
        params["from"] = date_from
    if date_to:
        params["to"] = date_to
    resp = requests.get(url, params=params, timeout=10)
    return _handle_response(resp)


def get_top_products(
    limit: int = 5,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/api/metrics/top_products"
    params = {"limit": limit}
    if date_from:
        params["from"] = date_from
    if date_to:
        params["to"] = date_to
    resp = requests.get(url, params=params, timeout=10)
    return _handle_response(resp)