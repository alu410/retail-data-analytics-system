"""Streamlit chat UI for the Retail Analytics system.

Run with:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import requests
import streamlit as st

from config import API_BASE_URL


st.set_page_config(
    page_title="Retail Analytics Chat",
    page_icon="📊",
    layout="wide",
)


def render_info_panel() -> None:
    """Info panel explaining what the chat can do (aligned with README)."""
    st.title("📊 Retail Data Analytics Chat")

    with st.expander("🛍️ What you can ask", expanded=True):
        st.markdown(
            """
Ask questions in plain English. The system can answer questions from 3 key categories: **customer-specific**, **product-specific**, and **business-related** — no technical jargon needed.

**👤 Customer-Specific Questions** (use a customer ID, e.g. 109318)
- *Summary:* total spent, transaction count, earliest/latest transaction 
    - e.g. *“How much did C109318 spend?”* *“How many orders did C109318 have?”*
- *Transaction history:* list of purchases (up to 15)
    - e.g. *“Show purchase history for C109318”* or *“in 2023”*

**📦 Product-Specific Questions** (use a product ID, e.g. A, B, C)
- *Summary:* revenue, transaction count, quantity sold, average discount, unique customer/store count 
    - e.g. *“What’s the total revenue for product A?”* *“Average discount for product B?”*
- *Transaction history:* list of sales (up to 15)
    - e.g. *“Transaction history for product C”*
- *Stores list:* where the product is sold (up to 15)
    - e.g. *“Which stores sell product D?”*

**📊 Business-Related Questions**
- *Summary:* overall revenue, transaction count, unique customer/product count, earliest/latest transaction   
    - e.g. *“Give me a revenue summary”* *“KPIs for 2024”*
- *Top customers / top products* by revenue (shows top 5 by default, up to 15) 
    - e.g. *“Who are the top customers?”* *“Top products by revenue”*
- *Key business metrics by product category* or *by payment method* (transaction count, quantity sold, revenue)  
    - e.g. *“Business summary by product category”* *“Revenue and quantity by payment method in Q1 2024”*

**💡 Tips:** Use customer and product IDs; add a time range (year, quarter, or dates) when you want filtered results. Ask one clear question at a time.
            """
        )


def call_chat_api(query: str) -> Dict[str, Any]:
    """Call the Flask /chat endpoint and return JSON."""
    url = f"{API_BASE_URL}/chat"
    resp = requests.post(url, json={"query": query}, timeout=60)
    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        data = {"raw_text": resp.text}

    return {
        "status_code": resp.status_code,
        "data": data,
    }


def render_chat() -> None:
    """Main chat interface using Streamlit's chat components."""
    if "messages" not in st.session_state:
        st.session_state.messages: List[Dict[str, str]] = []

    # Display existing conversation
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Ask a question about customers, products, or metrics...")
    if not user_input:
        return

    # Store and show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Call backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = call_chat_api(user_input)
                status_code = result["status_code"]
                payload = result["data"]

                if status_code == 200 and isinstance(payload, dict) and "answer" in payload:
                    answer = payload["answer"]
                    st.markdown(answer)
                else:
                    # Show a compact error message and optionally details in an expander
                    st.markdown(
                        f"⚠️ There was an issue answering your question "
                        f"(status code {status_code})."
                    )
                    with st.expander("Show technical details"):
                        st.code(json.dumps(payload, ensure_ascii=False, indent=2))
                    answer = f"[Error {status_code}] See details above."
            except Exception as exc:  # noqa: BLE001
                answer = f"Error calling backend: {exc}"
                st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})


def main() -> None:
    render_info_panel()
    st.markdown("---")
    render_chat()


if __name__ == "__main__":
    main()

