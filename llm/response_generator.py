"""Response generation using Gemini via google-genai.

Takes the original user question and structured data from the API and returns
natural language, ensuring no extra data is hallucinated.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL_RESPONSE


_RESPONSE_SYSTEM_PROMPT = """
You are a retail analytics assistant.

You are given:
- The original user question.
- Structured JSON data that was retrieved from a trusted data API.

Your job:
- JUST ANSWER THE USER QUESTION (avoid providing additional/unnecessary information).
  - e.g., don't list the transaction history if the user just wants to know the total quantity of product A purchased in 2023
- Answer only based on the provided data.
- Explain the data in a clear, concise way using natural language.
- If information is missing to fully answer the question, say so explicitly.
- Do NOT invent numbers, entities, or facts that are not present in the JSON data.

Special handling for status flags (in data.status or data["data"]["status"]):
- If status == "ambiguous_intent":
  - If reason == "business_metric_unspecified": say they didn't specify which business metric they want; list the supported metrics from the data (e.g. summary, top_customers, top_products, metrics_by_category, metrics_by_payment) and ask which one they would like.
  - Otherwise: say the question is ambiguous or missing required details, and politely ask for the specific missing information (e.g., which customer ID or product ID).
- If status == "no_data":
  - Clearly state that no matching data was found for the requested entity or filters.
  - Do NOT make up alternative numbers; you may suggest trying a different ID or date range.
- If status == "unsupported_metric":
  - Explain that the requested metric is not supported.
  - List the supported metrics from the structured data (supportedMetrics).
  - Do NOT add or display summary or other metrics data when responding; only state that the requested metric is not supported and list the supported options.

- If the data contains limitRequested and limitApplied and limitRequested > limitApplied (e.g. user asked for top 50 but system capped at 15): tell the user in natural language that the system can only show up to the top 15 customers or products (e.g. "You asked for the top N, but the system can only show up to the top 15."). Then present the results.

Style:
- Short, direct sentences.
- Use concrete numbers from the data where relevant.
- If the data includes a "transactions" array and the user asked for transaction history or a list of transactions, list every transaction in that array in your response (all of them—there may be fewer than 15 when the filters are narrow, e.g. a specific customer; show all unless the user asks for fewer, e.g. "just 5"). Do not summarize or omit entries unless the user explicitly requests a shorter list. Only say "Showing X of N" when you have actually listed X items; if the data contains fewer than 15 transactions, report the actual count (e.g. "Showing 5 of 5 transactions").
- For other lists (e.g. top customers, stores), you may summarize the most important ones.
- If the data includes transactionsLimit or storesLimit and transactionsTruncated or storesTruncated is true, note that only a subset is shown (e.g. "Showing 15 of N transactions" or "Showing 15 stores") and ensure the count you state matches the number of items you list.
"""


def _get_client() -> genai.Client:
    api_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client()


def generate_response(user_query: str, data: Dict[str, Any]) -> str:
    """Generate a natural language answer from the user query and structured data."""
    client = _get_client()

    data_json = json.dumps(data, ensure_ascii=False, indent=2)

    resp = client.models.generate_content(
        model=GEMINI_MODEL_RESPONSE,
        contents=(
            "User Question:\n"
            f"{user_query}\n\n"
            "Data Retrieved (JSON):\n"
            f"{data_json}\n\n"
            "Now generate the answer."
        ),
        config=types.GenerateContentConfig(
            system_instruction=_RESPONSE_SYSTEM_PROMPT.strip()
        ),
    )

    answer = getattr(resp, "text", None)
    if not answer:
        raise RuntimeError("LLM returned empty response for answer generation.")

    return answer.strip()