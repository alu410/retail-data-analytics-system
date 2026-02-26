# Retail Data Analytics Chat System

This project provides a **data layer** (SQLite + REST API) and an **LLM-powered chat** that lets users ask questions about retail transactions in natural language. The system uses Google Gemini to parse intent and generate answers, with deterministic routing to a Flask API over the same data.

[**DEMO VIDEO LINK**](<https://youtu.be/opP-y_CYOUE>) 

---

## Table of contents

- [Sample queries](#sample-queries)
- [Prerequisites](#prerequisites)
- [Setup for local run](#setup-for-local-run)
- [Dataset download and setup](#dataset-download-and-setup)
- [Environment variables](#environment-variables)
- [Running the system](#running-the-system)
- [Code structure](#code-structure)
- [REST API reference](#rest-api-reference)
- [Database schema](#database-schema)
- [Testing](#testing)
- [Supported metrics (intent → router)](#supported-metrics-intent--router)

---

## Sample queries

You can try these in the Streamlit chat UI or via `POST /chat` with `{"query": "..."}`.

### 1. Business metrics (summary & breakdowns)

- Can you provide me a summary of KPIs for 2024?
- Can you summarize sales volume by product category for 2024?
- Can you break down revenue by payment method for 2023?

### 2. Top N (customers & products)

- What was the top revenue-generating product in 2024?
- Who were the top 3 revenue-generating customers in Q3 2023?
- What are the top 50 selling products?

### 3. Customer- and product-specific

- Can you give me the purchase history of C32895?
- What's the average discount for product A in May 2023?
- Which stores sold product D in January 2024?

---

## Prerequisites

- **Python 3.10+** (required by `google-genai`; tested on 3.12.7)
- **Google Gemini API key** — required for the chat (intent parsing and answer generation). Get one at [Google AI Studio](https://aistudio.google.com/apikey).
- **Retail transaction CSV** — the project expects a CSV named `Retail_Transaction_Dataset.csv` (see [Dataset download and setup](#dataset-download-and-setup)).

---

## Setup for local run

1. **Clone or download the project** and open a terminal in the project root.

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables** (see [Environment variables](#environment-variables)). At minimum, set `GEMINI_API_KEY` for the chat. Create a `.env` file in the project root or export variables in your shell.

5. **Download the dataset and load it into SQLite** (see [Dataset download and setup](#dataset-download-and-setup)):
   ```bash
   python load_csv_to_sqlite.py
   ```

6. **Start the Flask API:**
   ```bash
   export FLASK_APP=flask_app.py
   flask run --reload
   ```
   Or alternatively, run `python flask_app.py`. The API listens at `http://127.0.0.1:5000` by default.

7. **(Optional) Start the Streamlit chat UI** in a second terminal (with the API running):
   ```bash
   streamlit run streamlit_app.py
   ```
   Open the URL shown (e.g. `http://localhost:8501`).

---

## Dataset download and setup

- The app expects a retail transaction CSV named **`Retail_Transaction_Dataset.csv`** in a **`data/`** directory at the project root.
- **Where to get the CSV:** Download the dataset from [Kaggle: Retail Transaction Dataset](https://www.kaggle.com/datasets/fahadrehman07/retail-transaction-dataset/data) (or use any CSV with the same column names: `CustomerID`, `ProductID`, `Quantity`, `Price`, `TransactionDate`, `PaymentMethod`, `StoreLocation`, `ProductCategory`, `DiscountApplied(%)`, `TotalAmount`). If your file has a different name, set `RETAIL_CSV_PATH` in `.env` to its path.
- **Setup steps:**
  1. Create a `data/` folder in the project root if it doesn’t exist.
  2. Place `Retail_Transaction_Dataset.csv` inside `data/`.
  3. Run the loader once (or after the CSV changes):
     ```bash
     python load_csv_to_sqlite.py
     ```
     This creates `data/retail.db` and populates the `transactions` table. The script creates `data/` if missing. Progress is printed in batches (~100k rows).

---

## Environment variables

Create a **`.env`** file in the project root (or export in your shell). The app loads `.env` via `python-dotenv` in `config.py`.

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `GEMINI_API_KEY` | **Yes** (for chat) | Google Gemini API key. Get one at [Google AI Studio](https://aistudio.google.com/apikey). | — |
| `RETAIL_DB_PATH` | No | Path to SQLite database file. | `data/retail.db` |
| `RETAIL_CSV_PATH` | No | Path to the retail transaction CSV. | `data/Retail_Transaction_Dataset.csv` |
| `RETAIL_API_BASE_URL` | No | Base URL of the Flask API (used by Streamlit and data service). | `http://127.0.0.1:5000` |
| `GEMINI_MODEL_INTENT` | No | Model for intent parsing. | `gemini-2.5-flash` |
| `GEMINI_MODEL_RESPONSE` | No | Model for answer generation. | `gemini-3-flash-preview` |

**Example `.env`:**
```env
GEMINI_API_KEY=your_gemini_api_key_here
RETAIL_DB_PATH=data/retail.db
RETAIL_CSV_PATH=data/Retail_Transaction_Dataset.csv
RETAIL_API_BASE_URL=http://127.0.0.1:5000
```

---

## Running the system

- **Data + API only:** Run `load_csv_to_sqlite.py` once, then `flask run`. Use the REST endpoints directly or `curl`.
- **Chat (programmatic):** Same as above; send `POST /chat` with `{"query": "..."}` to get intent + data + natural-language answer.
- **Chat (UI):** Start Flask (`flask run` with `FLASK_APP=flask_app.py`), then `streamlit run streamlit_app.py`. Use the sidebar for guidelines and the main area for the chat.

---

## Code structure

High-level layout:

```
Retail Data Analytics Chat System/
├── config.py              # Central config (paths, Gemini, API URL); loads .env
├── load_csv_to_sqlite.py  # ETL: CSV → SQLite (transactions table + indexes)
├── flask_app.py           # Flask app: REST API + POST /chat orchestration
├── streamlit_app.py       # Streamlit chat UI (calls Flask /chat)
├── requirements.txt       # Python dependencies
├── .env                   # Optional env vars (e.g. GEMINI_API_KEY)
├── data/                  # Data directory: CSV + SQLite DB
│   ├── Retail_Transaction_Dataset.csv   # Place the Kaggle CSV here
│   └── retail.db          # Created by load_csv_to_sqlite.py
│
├── schemas/
│   └── intent.py          # Pydantic Intent model (intent, customer_id, product_id, metric, date_range)
│
├── llm/
│   ├── intent_parser.py   # Gemini: user query → JSON intent (with date_range as YYYY-MM-DD..YYYY-MM-DD)
│   └── response_generator.py  # Gemini: user query + structured data → natural-language answer
│
└── services/
    ├── data_service.py    # HTTP client for Flask API (customers, products, metrics endpoints)
    └── query_router.py    # Deterministic routing: Intent → data_service calls; handles no_data/ambiguous/unsupported
```

### Responsibilities

| Component | Role |
|-----------|------|
| **config.py** | Loads `.env`; exposes `DATABASE_PATH`, `CSV_PATH`, `API_BASE_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL_*`. |
| **load_csv_to_sqlite.py** | Parses CSV (handles quoted multi-line fields); creates `transactions` table and indexes; batch-inserts rows; normalizes date to ISO. |
| **flask_app.py** | Flask app: serves `/api/customers/<id>`, `/api/products/<id>`, `/api/metrics/*` (summary, by_category, by_payment, top_customers, top_products). All of these support optional time filtering via `from` and `to` query params (YYYY-MM-DD). Also `POST /chat`: parse intent → route → fetch data → generate answer. |
| **schemas/intent.py** | Pydantic `Intent`: `intent` (customer \| product \| business_metric), `customer_id`, `product_id`, `metric`, `date_range`. Validates LLM output. |
| **llm/intent_parser.py** | Calls Gemini with system prompt that defines schema + canonical metrics + date_range as `YYYY-MM-DD..YYYY-MM-DD`; returns validated `Intent`. |
| **llm/response_generator.py** | Calls Gemini with user query + structured data; prompt instructs to answer only from data and handle status flags (no_data, ambiguous_intent, unsupported_metric). |
| **services/data_service.py** | Functions that `requests.get` the Flask API: `get_customer`, `get_product`, `get_metrics_summary`, `get_metrics_by_category`, `get_metrics_by_payment`, `get_top_customers`, `get_top_products`. |
| **services/query_router.py** | `route_intent(intent)` → `RoutedResult`: maps intent/metric to data_service calls; interprets `date_range` (e.g. `2023-01-01..2023-12-31`) to `from`/`to`; returns status payloads for no_data, ambiguous_intent, unsupported_metric; trims product payload (e.g. stores list) for LLM. |
| **streamlit_app.py** | Renders sidebar with usage guidelines (customer/product/business metrics); chat UI posts to `/chat` and displays the `answer` (or error). |

### Chat flow (POST /chat)

1. Request body: `{"query": "user question"}`.
2. **Intent parsing:** `intent_parser.parse_intent(query)` → Gemini returns JSON → validate with `Intent`.
3. **Routing:** `query_router.route_intent(intent)` → one or more data_service calls → structured data (or status payload).
4. **Response generation:** `response_generator.generate_response(query, {intent, data})` → Gemini returns natural-language answer.
5. Response: `{"intent": {...}, "data": {...}, "answer": "..."}` or 400/502 with error details.

---

## REST API reference

All endpoints below support optional time filtering via query params **`from`** and **`to`** (YYYY-MM-DD).

### Customer

- **`GET /api/customers/<customer_id>`**  
  All transactions for that customer + summary (transaction count, total spent, earliest/latest transaction).  
  Example: `GET /api/customers/109318`

### Product

- **`GET /api/products/<product_id>`**  
  All transactions for that product + summary (transaction count, total quantity, total revenue, unique customer/store count, average discount, stores list).  
  Example: `GET /api/products/A`

### Business metrics

| Endpoint | Description |
|----------|-------------|
| `GET /api/metrics/summary` | Total revenue, transaction count, unique customer/product count, earliest/latest transaction. |
| `GET /api/metrics/by_category` | Metrics by product category: transaction count, quantity (units) sold, total revenue. |
| `GET /api/metrics/by_payment` | Metrics by payment method: transaction count, quantity (units) sold, total revenue. |
| `GET /api/metrics/top_customers` | Top N by revenue (with ID, transaction count, total spent); param `limit` (default 5, max 15). |
| `GET /api/metrics/top_products` | Top N products ordered by **total revenue** (desc), with total quantity as tiebreaker. Returns ID, transaction count, quantity sold, total revenue; param `limit` (default 5, max 15). |

### Chat

- **`POST /chat`**  
  Body: `{"query": "natural language question"}`.  
  Returns: `{"intent": {...}, "data": {...}, "answer": "..."}` or error payload.

---

## Database schema

**Table: `transactions`**

| Column             | Type    | Description                    |
|--------------------|---------|--------------------------------|
| id                 | INTEGER | Auto-increment primary key     |
| CustomerID         | INTEGER | Customer identifier            |
| ProductID          | TEXT    | Product code (e.g. A, B, C, D) |
| Quantity           | INTEGER | Units in transaction           |
| Price              | REAL    | Unit price                     |
| TransactionDate    | TEXT    | ISO-style date/time            |
| PaymentMethod      | TEXT    | Cash, PayPal, Debit Card, etc. |
| StoreLocation      | TEXT    | Full address (may be multi-line) |
| ProductCategory    | TEXT    | Books, Electronics, etc.       |
| DiscountAppliedPct | REAL    | Discount percentage            |
| TotalAmount        | REAL    | Transaction total              |

Indexes: `CustomerID`, `ProductID`, `TransactionDate`, `ProductCategory`, `PaymentMethod`.

---

## Testing

- **Manual API:** Use `curl` or any HTTP client against the endpoints above.
- **Unit tests:** In the `tests/` directory, pytest is used for core logic. Run from the project root:
  ```bash
  python -m pytest tests/ -v
  ```
  Tests cover: `test_query_router.py` (date parsing, routing, trimming), `test_intent_parser.py` (parse_intent with mocked Gemini), `test_flask_app.py` (metrics and customer/product endpoints with a temporary DB), `test_data_service.py` (HTTP URLs and params with mocked requests), `test_schemas_intent.py` (Intent validation).

---

## Supported metrics (intent → router)

**Summary:** The chat uses **canonical intent labels** (listed below) so the parser can map many phrasings to the same backend call. For **customer** and **product** intents, the router calls a single endpoint and receives the **full API payload** (transactions, counts, totals, dates, etc.). The response generator uses that full payload to answer—so questions like “How many orders did they have?”, “When was their first purchase?”, “Which stores sell this product?”, or “What’s the total revenue for this product?” are all supported even though they share the same intent labels. For **business** intents, each label maps to a specific metrics endpoint. All intents support optional **date_range** (e.g. “in 2023”, “Q1 2024”), which the router converts to `from`/`to` and passes to the API.

**Canonical metrics (what the parser outputs):**

- **Customer** (requires `customer_id`): `summary`, `transaction_history`.  
  The API returns: all transactions, transaction count, total spent, earliest/latest transaction. The chat can answer questions about any of these (e.g. order count, date range, spend).

- **Product** (requires `product_id`): `summary`, `transaction_history`, `stores_list`.  
  The API returns: transactions, transaction count, quantity sold, total revenue, unique customers/stores, average discount, stores list. The chat can answer questions about any of these (e.g. revenue, units sold, which stores, discount).

- **Business:** `summary`, `top_customers`, `top_products` (by revenue, quantity as tiebreaker), `metrics_by_category`, `metrics_by_payment`.  
  Each maps to the corresponding metrics endpoint (summary, by_category, by_payment, top_customers, top_products).

**Date range:** The intent parser is instructed to output `date_range` as `YYYY-MM-DD..YYYY-MM-DD` when the user specifies a year, quarter, or range, so the router can pass `from`/`to` to the API.
