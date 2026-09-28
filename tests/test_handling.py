import pytest

from app.handling import (
    HandlingEstimate,
    pick_ebay_fulfillment_policy,
    shopee_shipping_terms,
)


def test_handling_estimate_total_days():
    est = HandlingEstimate(sourcing_lead_time_days=3, buffer_days=2)
    assert est.total_days == 5


def test_handling_estimate_rejects_negative_days():
    with pytest.raises(ValueError):
        HandlingEstimate(sourcing_lead_time_days=-1)


def test_pick_ebay_fulfillment_policy_picks_tightest_fit():
    policy_map = {3: "fast", 7: "standard", 14: "slow"}
    assert pick_ebay_fulfillment_policy(5, policy_map) == "standard"
    assert pick_ebay_fulfillment_policy(3, policy_map) == "fast"
    assert pick_ebay_fulfillment_policy(14, policy_map) == "slow"


def test_pick_ebay_fulfillment_policy_raises_when_no_policy_covers_it():
    policy_map = {3: "fast", 7: "standard"}
    with pytest.raises(ValueError, match="no eBay fulfillment policy"):
        pick_ebay_fulfillment_policy(10, policy_map)


def test_shopee_shipping_terms_normal_order():
    days_to_ship, is_pre_order = shopee_shipping_terms(5)
    assert days_to_ship == 5
    assert is_pre_order is False


def test_shopee_shipping_terms_long_lead_time_becomes_pre_order():
    days_to_ship, is_pre_order = shopee_shipping_terms(12)
    assert days_to_ship == 12
    assert is_pre_order is True


def test_shopee_shipping_terms_clamped_to_bounds():
    days_to_ship, _ = shopee_shipping_terms(0)
    assert days_to_ship == 2
    days_to_ship, _ = shopee_shipping_terms(100)
    assert days_to_ship == 30
