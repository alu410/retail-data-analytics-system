"""Unit tests for llm.intent_parser: parse_intent with mocked Gemini."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from llm.intent_parser import IntentParsingError, parse_intent
from schemas.intent import Intent


class TestParseIntent:
    """Tests for parse_intent with mocked LLM."""

    @patch("llm.intent_parser._get_client")
    def test_valid_json_returns_intent(self, mock_get_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.text = '{"intent": "customer", "customer_id": 123, "product_id": null, "metric": "summary", "date_range": null}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_get_client.return_value = mock_client

        result = parse_intent("How much did customer 123 spend?")
        assert isinstance(result, Intent)
        assert result.intent == "customer"
        assert result.customer_id == 123
        assert result.metric == "summary"

    @patch("llm.intent_parser._get_client")
    def test_invalid_json_raises_intent_parsing_error(
        self, mock_get_client: MagicMock
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.text = "not valid json at all"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_get_client.return_value = mock_client

        with pytest.raises(IntentParsingError) as exc_info:
            parse_intent("anything")
        assert "not valid JSON" in str(exc_info.value) or "valid JSON" in str(exc_info.value)

    @patch("llm.intent_parser._get_client")
    def test_json_failing_schema_raises_intent_parsing_error(
        self, mock_get_client: MagicMock
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.text = '{"intent": "invalid_type", "customer_id": null, "product_id": null, "metric": null, "date_range": null}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_get_client.return_value = mock_client

        with pytest.raises(IntentParsingError):
            parse_intent("anything")

    @patch("llm.intent_parser._get_client")
    def test_empty_llm_response_raises_intent_parsing_error(
        self, mock_get_client: MagicMock
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.text = None
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_get_client.return_value = mock_client

        with pytest.raises(IntentParsingError) as exc_info:
            parse_intent("anything")
        assert "empty" in str(exc_info.value).lower()
