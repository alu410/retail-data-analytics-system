"""Deterministic router from Intent -> concrete data service calls."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from schemas.intent import Intent
from services import data_service

# Unified limit for trimming list payloads (transactions, stores) sent to the LLM.
_TRIM_LIMIT = 15


class RoutingError(Exception):
    """Raised when an intent cannot be fulfilled deterministically."""


@dataclass
class RoutedResult:
    """Structured payload returned to the response generator."""

    intent: Intent
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        # Flatten intent into a dict alongside the data for easier prompting.
        return {
            "intent": self.intent.model_dump(),
            "data": self.data,
        }


def _interpret_date_range(date_range: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Turn a friendly date_range into concrete from/to strings when possible.

    For now this is intentionally conservative:
    - If date_range is already in the form 'YYYY-MM-DD..YYYY-MM-DD', split it.
    - Otherwise, return (None, None) and leave date filtering to the caller or future logic.
    """
    if not date_range:
        return None, None

    if ".." in date_range:
        start, end = date_range.split("..", 1)
        start = start.strip() or None
        end = end.strip() or None
        return start, end

    # Future: interpret values like 'last_month', '2024-Q1', etc.
    return None, None


def route_intent(intent: Intent) -> RoutedResult:
    """Route the intent to the appropriate data service call."""
    if intent.intent == "customer":
        if intent.customer_id is None:
            # Let the LLM ask for clarification instead of hard failing.
            return RoutedResult(
                intent=intent,
                data={
                    "status": "ambiguous_intent",
                    "reason": "customer_id_missing",
                },
            )

        date_from, date_to = _interpret_date_range(intent.date_range)
        payload = data_service.get_customer(
            customer_id=intent.customer_id,
            date_from=date_from,
            date_to=date_to,
        )
        if not payload or (
            isinstance(payload, dict)
            and not payload.get("transactions")
            and payload.get("summary") is None
        ):
            return RoutedResult(
                intent=intent,
                data={
                    "status": "no_data",
                    "reason": "no_customer_transactions",
                    "customerId": intent.customer_id,
                },
            )
        # Trim transactions to avoid huge payloads; inform the model via echoed fields.
        if isinstance(payload.get("transactions"), list):
            transactions = payload["transactions"]
            total = len(transactions)
            payload = dict(payload)
            payload["transactions"] = transactions[:_TRIM_LIMIT]
            payload["transactionCount"] = total
            payload["transactionsLimit"] = _TRIM_LIMIT
            payload["transactionsTruncated"] = total > _TRIM_LIMIT
        return RoutedResult(intent=intent, data=payload)

    if intent.intent == "product":
        if intent.product_id is None:
            # Let the LLM ask for clarification instead of hard failing.
            return RoutedResult(
                intent=intent,
                data={
                    "status": "ambiguous_intent",
                    "reason": "product_id_missing",
                },
            )

        date_from, date_to = _interpret_date_range(intent.date_range)
        payload = data_service.get_product(
            product_id=intent.product_id,
            date_from=date_from,
            date_to=date_to,
        )
        # To avoid sending huge payloads to the LLM (which can exhaust
        # token/quota), we keep only a compact aggregate view of the product.
        summary = payload.get("summary") or {}
        trimmed_summary: Dict[str, Any]
        if isinstance(summary, dict):
            trimmed_summary = dict(summary)
            stores = summary.get("stores")
            if isinstance(stores, list):
                total_stores = len(stores)
                trimmed_summary["storeCount"] = total_stores
                trimmed_summary["storesTruncated"] = total_stores > _TRIM_LIMIT
                trimmed_summary["storesLimit"] = _TRIM_LIMIT
                trimmed_summary["stores"] = stores[:_TRIM_LIMIT]
        else:
            trimmed_summary = summary  # fallback, unexpected shape

        # If there is effectively no data for this product, signal that.
        if not payload or trimmed_summary in (None, {}) or (
            isinstance(trimmed_summary, dict)
            and not trimmed_summary.get("transactionCount")
            and not trimmed_summary.get("totalQuantity")
            and not trimmed_summary.get("totalRevenue")
        ):
            return RoutedResult(
                intent=intent,
                data={
                    "status": "no_data",
                    "reason": "no_product_transactions",
                    "productId": intent.product_id,
                },
            )

        slim_payload: Dict[str, Any] = {
            "productId": payload.get("productId"),
            "summary": trimmed_summary,
            "filters": payload.get("filters"),
        }
        # Include a trimmed transaction list so the model can answer "transaction history" requests.
        if isinstance(payload.get("transactions"), list):
            transactions = payload["transactions"]
            total = len(transactions)
            slim_payload["transactions"] = transactions[:_TRIM_LIMIT]
            slim_payload["transactionCount"] = total
            slim_payload["transactionsLimit"] = _TRIM_LIMIT
            slim_payload["transactionsTruncated"] = total > _TRIM_LIMIT
        return RoutedResult(intent=intent, data=slim_payload)

    if intent.intent == "business_metric":
        metric = (intent.metric or "").strip().lower()
        date_from, date_to = _interpret_date_range(intent.date_range)

        # Ambiguous: user asked for "business metrics" but did not specify which one.
        if not metric:
            supported_metrics = [
                "summary",
                "top_customers",
                "top_products",
                "metrics_by_category",
                "metrics_by_payment",
            ]
            return RoutedResult(
                intent=intent,
                data={
                    "status": "ambiguous_intent",
                    "reason": "business_metric_unspecified",
                    "supportedMetrics": supported_metrics,
                },
            )

        # Known-unsupported patterns: we do not have store/location breakdowns.
        if "store" in metric or "location" in metric:
            supported_metrics = [
                "summary",
                "top_customers",
                "top_products",
                "metrics_by_category",
                "metrics_by_payment",
            ]
            return RoutedResult(
                intent=intent,
                data={
                    "status": "unsupported_metric",
                    "reason": "metric_not_supported",
                    "requestedMetric": intent.metric,
                    "supportedMetrics": supported_metrics,
                },
            )

        # Treat a variety of synonyms as a general revenue/summary request.
        summary_like = {
            "summary",
            "overview",
            "kpis",
            "revenue_summary",
            "total_revenue",
            "revenue",
        }
        if metric in summary_like:
            payload = data_service.get_metrics_summary(date_from=date_from, date_to=date_to)
            return RoutedResult(intent=intent, data=payload)

        # Revenue broken down by product category.
        if metric in {"metrics_by_category", "revenue_by_category", "category_revenue", "revenue_per_category"}:
            payload = data_service.get_metrics_by_category(date_from=date_from, date_to=date_to)
            return RoutedResult(intent=intent, data=payload)

        # Metrics (revenue, quantity, transaction count) by payment method.
        if metric in {"metrics_by_payment", "revenue_by_payment", "payment_revenue", "revenue_per_payment", "by_payment"}:
            payload = data_service.get_metrics_by_payment(date_from=date_from, date_to=date_to)
            return RoutedResult(intent=intent, data=payload)

        _TOP_N_MAX = 15
        if metric == "top_customers":
            limit = min(intent.top_n or 5, _TOP_N_MAX)
            payload = data_service.get_top_customers(
                limit=limit,
                date_from=date_from,
                date_to=date_to,
            )
            if intent.top_n is not None and intent.top_n > _TOP_N_MAX:
                payload = dict(payload)
                payload["limitRequested"] = intent.top_n
                payload["limitApplied"] = _TOP_N_MAX
            return RoutedResult(intent=intent, data=payload)

        if metric in {"top_products"}:
            limit = min(intent.top_n or 5, _TOP_N_MAX)
            payload = data_service.get_top_products(
                limit=limit,
                date_from=date_from,
                date_to=date_to,
            )
            if intent.top_n is not None and intent.top_n > _TOP_N_MAX:
                payload = dict(payload)
                payload["limitRequested"] = intent.top_n
                payload["limitApplied"] = _TOP_N_MAX
            return RoutedResult(intent=intent, data=payload)

        # Unsupported or unknown metric: let the LLM explain what's available.
        supported_metrics = [
            "summary",
            "top_customers",
            "top_products",
            "metrics_by_category",
            "metrics_by_payment",
        ]
        return RoutedResult(
            intent=intent,
            data={
                "status": "unsupported_metric",
                "reason": "metric_not_recognized",
                "requestedMetric": intent.metric,
                "supportedMetrics": supported_metrics,
            },
        )

    raise RoutingError(f"Unsupported intent type: {intent.intent}")


