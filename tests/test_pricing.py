import pytest

from app.pricing import (
    FeeStructure,
    calculate_margin_percent,
    calculate_profit,
    convert_currency,
    required_selling_price,
)


def test_convert_currency():
    assert convert_currency(1000, 0.0067) == pytest.approx(6.7)


def test_required_selling_price_matches_target_margin():
    fees = FeeStructure(fee_percent=0.10, fixed_fee=0.30)
    cost = 20.0
    shipping = 5.0
    margin = 0.30

    price = required_selling_price(cost, shipping, fees, margin)
    profit = calculate_profit(price, cost, shipping, fees)

    assert profit == pytest.approx(margin * (cost + shipping), rel=1e-9)


def test_calculate_profit_accounts_for_fixed_and_percent_fees():
    fees = FeeStructure(fee_percent=0.1325, fixed_fee=0.30)
    profit = calculate_profit(selling_price=50.0, cost=20.0, shipping_cost=5.0, fees=fees)
    expected = 50.0 - (50.0 * 0.1325 + 0.30) - 20.0 - 5.0
    assert profit == pytest.approx(expected)


def test_calculate_margin_percent_round_trip():
    fees = FeeStructure(fee_percent=0.06, payment_fee_percent=0.02)
    cost, shipping, margin = 1000.0, 100.0, 0.25
    price = required_selling_price(cost, shipping, fees, margin)
    assert calculate_margin_percent(price, cost, shipping, fees) == pytest.approx(margin, rel=1e-9)


def test_fee_structure_rejects_fee_percent_over_one():
    with pytest.raises(ValueError):
        FeeStructure(fee_percent=0.9, payment_fee_percent=0.2)


def test_required_selling_price_rejects_negative_cost():
    fees = FeeStructure(fee_percent=0.1)
    with pytest.raises(ValueError):
        required_selling_price(-1, 0, fees, 0.1)
