"""Student-designed HW1 tool: order_history_summary (no LLM, no API keys)."""

from __future__ import annotations

import sqlite3

from agent import tools
from agent.auth import AuthContext

SHOPPER_1 = AuthContext(user_id=1, role="shopper")
MERCHANT_STORE_2 = AuthContext(user_id=9002, role="merchant", store_id=2)
SUPPORT = AuthContext(user_id=9501, role="support")


def test_shopper_gets_real_total_beyond_the_20_order_listing(world: dict) -> None:
    conn = sqlite3.connect(world["db"])
    try:
        expected_total = conn.execute("SELECT count(*) FROM orders WHERE user_id = 1").fetchone()[0]
    finally:
        conn.close()

    result = tools.order_history_summary(SHOPPER_1)
    assert result["ok"] is True
    assert result["total_orders"] == expected_total
    assert expected_total > tools.list_my_orders(SHOPPER_1)["count"]
    assert sum(result["by_status"].values()) == expected_total
    assert sum(p["orders"] for p in result["products"]) == expected_total


def test_products_carry_names_and_unit_counts(world: dict) -> None:
    result = tools.order_history_summary(SHOPPER_1)
    vase = next(p for p in result["products"] if p["product_id"] == 1)
    # Orders 4127, 3980, and 4455 all reference product 1.
    assert vase["title"] == "Heavy-Duty Vase"
    assert vase["orders"] >= 3
    assert vase["units"] >= vase["orders"]


def test_merchant_sees_only_their_store(world: dict) -> None:
    conn = sqlite3.connect(world["db"])
    try:
        expected_total = conn.execute("SELECT count(*) FROM orders WHERE store_id = 2").fetchone()[0]
    finally:
        conn.close()

    result = tools.order_history_summary(MERCHANT_STORE_2)
    assert result["ok"] is True
    assert result["total_orders"] == expected_total


def test_support_has_no_history_of_its_own(world: dict) -> None:
    result = tools.order_history_summary(SUPPORT)
    assert result["ok"] is False
    assert result["error"] == "invalid_argument"
