"""Unit tests for schemas.intent: Intent validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.intent import Intent


class TestIntentValidation:
    """Intent.model_validate accepts valid payloads and rejects invalid ones."""

    def test_valid_customer_intent(self) -> None:
        payload = {
            "intent": "customer",
            "customer_id": 123,
            "product_id": None,
            "metric": "summary",
            "date_range": None,
        }
        intent = Intent.model_validate(payload)
        assert intent.intent == "customer"
        assert intent.customer_id == 123
        assert intent.metric == "summary"

    def test_valid_business_metric_intent(self) -> None:
        payload = {
            "intent": "business_metric",
            "customer_id": None,
            "product_id": None,
            "metric": "metrics_by_category",
            "date_range": "2024-01-01..2024-12-31",
        }
        intent = Intent.model_validate(payload)
        assert intent.intent == "business_metric"
        assert intent.metric == "metrics_by_category"
        assert intent.date_range == "2024-01-01..2024-12-31"

    def test_invalid_intent_literal_raises(self) -> None:
        payload = {
            "intent": "invalid_type",
            "customer_id": None,
            "product_id": None,
            "metric": None,
            "date_range": None,
        }
        with pytest.raises(ValidationError):
            Intent.model_validate(payload)

    def test_missing_intent_raises(self) -> None:
        payload = {
            "customer_id": None,
            "product_id": None,
            "metric": None,
            "date_range": None,
        }
        with pytest.raises(ValidationError):
            Intent.model_validate(payload)
