"""Pricing/profit logic. Pure functions, no I/O, so they're cheap to unit test.

Margin is expressed as a fraction of cost (a markup), e.g. 0.30 means the
target profit is 30% of (cost + shipping_cost).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FeeStructure:
    fee_percent: float  # marketplace commission / final value fee, e.g. 0.1325
    fixed_fee: float = 0.0  # flat per-order fee, in the selling currency
    payment_fee_percent: float = 0.0  # extra payment-processing cut, if separate

    def __post_init__(self) -> None:
        if not (0 <= self.total_fee_percent < 1):
            raise ValueError("total_fee_percent must be in [0, 1)")

    @property
    def total_fee_percent(self) -> float:
        return self.fee_percent + self.payment_fee_percent


# Rough defaults; override per-category/per-region as needed.
EBAY_DEFAULT_FEES = FeeStructure(fee_percent=0.1325, fixed_fee=0.30)
SHOPEE_DEFAULT_FEES = FeeStructure(fee_percent=0.06, payment_fee_percent=0.02)


def convert_currency(amount: float, rate: float) -> float:
    """Convert `amount` in the source currency to the target currency using
    `rate` = target-currency-units per one source-currency-unit."""
    return amount * rate


def required_selling_price(
    cost: float,
    shipping_cost: float,
    fees: FeeStructure,
    target_margin_percent: float,
) -> float:
    """Selling price S such that, after marketplace fees, profit equals
    target_margin_percent * (cost + shipping_cost).

    Derivation: profit = S - (S*fee_percent + fixed_fee) - cost - shipping_cost
    Setting profit = margin * (cost + shipping_cost) and solving for S:
    S = (cost*(1+margin) + shipping_cost*(1+margin) + fixed_fee) / (1 - fee_percent)
    """
    if cost < 0 or shipping_cost < 0:
        raise ValueError("cost and shipping_cost must be non-negative")
    numerator = (cost + shipping_cost) * (1 + target_margin_percent) + fees.fixed_fee
    return numerator / (1 - fees.total_fee_percent)


def calculate_profit(
    selling_price: float,
    cost: float,
    shipping_cost: float,
    fees: FeeStructure,
) -> float:
    fee_amount = selling_price * fees.total_fee_percent + fees.fixed_fee
    return selling_price - fee_amount - cost - shipping_cost


def calculate_margin_percent(
    selling_price: float,
    cost: float,
    shipping_cost: float,
    fees: FeeStructure,
) -> float:
    """Realised margin as a fraction of (cost + shipping_cost)."""
    base = cost + shipping_cost
    if base <= 0:
        raise ValueError("cost + shipping_cost must be positive")
    return calculate_profit(selling_price, cost, shipping_cost, fees) / base
