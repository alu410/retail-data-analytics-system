"""Intent parsing using Gemini via google-genai.

This module is responsible for turning a raw user question into a structured
Intent object, validated by Pydantic.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from google import genai
from google.genai import types
from pydantic import ValidationError

from config import GEMINI_API_KEY, GEMINI_MODEL_INTENT
from schemas.intent import Intent


class IntentParsingError(Exception):
    """Raised when the LLM output cannot be parsed or validated."""


_INTENT_SYSTEM_PROMPT = """
You are an intent extraction engine for a retail analytics system.

Your job is to read a user's question about customers, products, or business metrics
and output a SINGLE JSON object that matches this schema:

{
  "intent": "customer" | "product" | "business_metric",
  "customer_id": number | null,
  "product_id": string | null,
  "metric": string | null,
  "top_n": number | null,
  "date_range": string | null
}

Rules:
- Only use one of the allowed intents: "customer", "product", "business_metric".
- If the user clearly refers to a customer, set intent="customer" and extract customer_id if present.
- If the user clearly refers to a product, set intent="product" and extract product_id if present.
- If the user asks about overall KPIs or segments, set intent="business_metric".
- For customer IDs like "customer 123" or "C123", extract the numeric part as customer_id (e.g. 123).
- For product IDs like "product A" or "P1234", keep the full token as product_id (e.g. "A", "P1234").
- If a field is not applicable, set it to null.

Use the `metric` field to encode the specific operation. The supported canonical
metric strings are:
- Customer and Product (unified): "summary", "transaction_history"; Product only: "stores_list".
  - "summary": aggregate view (totals, counts, dates; for product also average discount, etc.).
  - "transaction_history": the list of transactions (purchases for customer; transactions for product).
  - "stores_list": which stores sell this product (product intent only).
- Business metrics:
  - "summary"
  - "top_customers"
  - "top_products"
  - "metrics_by_category"
  - "metrics_by_payment"

Mapping for customer/product: If the user asks for totals, spend, counts, or an overview, use "summary".
If they ask for the list of purchases/orders/transactions, use "transaction_history". If they ask which
stores sell the product (product only), use "stores_list".

Business metrics (intent="business_metric"):
- If the user asks vaguely for "a metric", "some metrics", "tell me about a metric", or similar without naming one of the supported metrics (summary, top_customers, top_products, metrics_by_category, metrics_by_payment), set metric to null.
- If the user asks for something that sounds like a synonym for overall summary (e.g. "total revenue", "revenue summary", "revenue overview", "KPIs"), use "summary".
- Metrics (revenue, quantity, transaction count) broken down by product category -> "metrics_by_category". By payment method -> "metrics_by_payment". (User may say "revenue by product category" or "business metrics by payment method"; map to these.)
- We only support breakdown by category and by payment method. If the user asks for breakdown by store, store location, or any other dimension (e.g. "average revenue by store location", "revenue by store"), do NOT use "summary". Set metric to a descriptive string that is not in the supported list (e.g. "revenue_by_store", "revenue_by_store_location") so the system can respond that it is not supported.
- For "top_customers" or "top_products": if the user specifies a number (e.g. "top 50 customers"), set `top_n` to that number; otherwise set `top_n` to null.

For the `date_range` field:
- When the user provides an explicit year, quarter, or date span, convert it into a
  string of the form "YYYY-MM-DD..YYYY-MM-DD" that covers the full inclusive range.
  Examples:
  - "in 2023" -> "2023-01-01..2023-12-31"
  - "in 2024" -> "2024-01-01..2024-12-31"
  - "Q1 2024" or "in Q1 2024" -> "2024-01-01..2024-03-31"
  - "between January and March 2024" -> "2024-01-01..2024-03-31"
- If you cannot confidently infer exact start/end dates, set `date_range` to null.

Output:
- Return ONLY a valid JSON object.
- Do not wrap the JSON in markdown.
- Do not include any explanations or extra text.
"""


def _get_client() -> genai.Client:
    # Prefer GEMINI_API_KEY loaded via .env; fall back to default client config.
    api_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client()


def parse_intent(user_query: str) -> Intent:
    """Call Gemini to parse user intent and return a validated Intent object."""
    client = _get_client()

    resp = client.models.generate_content(
        model=GEMINI_MODEL_INTENT,
        contents=user_query,
        config=types.GenerateContentConfig(
            system_instruction=_INTENT_SYSTEM_PROMPT.strip()
        ),
    )

    # The google-genai response exposes .text for simple text content.
    raw_text = getattr(resp, "text", None)
    if not raw_text:
        raise IntentParsingError("LLM returned empty response while parsing intent.")

    try:
        candidate: Dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise IntentParsingError(f"LLM output was not valid JSON: {raw_text}") from exc

    try:
        intent = Intent.model_validate(candidate)
    except ValidationError as exc:
        raise IntentParsingError(f"LLM output failed schema validation: {candidate}") from exc

    return intent


