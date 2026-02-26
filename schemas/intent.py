"""Pydantic schemas for user intent extracted from natural language."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Intent(BaseModel):
    """Structured representation of what the user is asking for."""

    intent: Literal["customer", "product", "business_metric"] = Field(
        description="High-level type of request."
    )

    # Entity identifiers
    customer_id: Optional[int] = Field(
        default=None, description="Customer ID for customer-specific queries."
    )
    product_id: Optional[str] = Field(
        default=None, description="Product ID for product-specific queries."
    )

    # Metric / operation requested
    metric: Optional[str] = Field(
        default=None,
        description=(
            "Specific metric or operation, e.g. 'summary', 'transaction_history', "
            "'stores_list' (customer/product); 'top_customers', 'top_products', "
            "'metrics_by_category', 'metrics_by_payment' (business)."
        ),
    )

    # Top-N for business metrics (top_customers, top_products)
    top_n: Optional[int] = Field(
        default=None,
        description="Requested N when user says e.g. 'top 50 customers' or 'top 25 products'; null if not specified.",
    )

    # Additional constraints
    date_range: Optional[str] = Field(
        default=None,
        description=(
            "Human-readable date range like 'last_month', '2024-Q1', or "
            "'2024-01-01..2024-01-31'. Will be interpreted deterministically "
            "by the query router."
        ),
    )