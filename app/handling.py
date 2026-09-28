"""Turn a product's sourcing lead time into commitments the marketplaces can
enforce: eBay's handling time (set via a pre-configured business/fulfillment
policy) and Shopee's per-item days-to-ship / pre-order flag.

None of this shortens the real-world lag (buy -> arrives -> repack -> ship);
it just makes sure the listing tells the buyer/platform the truth about it,
so a slow-but-honest listing doesn't turn into a late-shipment strike.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class HandlingEstimate:
    sourcing_lead_time_days: int  # time to receive the item from Mercari/Yahoo/Amazon
    buffer_days: int = 2  # time to inspect, repack, and drop off outbound shipping

    def __post_init__(self) -> None:
        if self.sourcing_lead_time_days < 0 or self.buffer_days < 0:
            raise ValueError("days must be non-negative")

    @property
    def total_days(self) -> int:
        return self.sourcing_lead_time_days + self.buffer_days


def pick_ebay_fulfillment_policy(total_days: int, policy_map: dict[int, str]) -> str:
    """eBay's Inventory API takes a fulfillmentPolicyId, not a raw handling
    time — the handling time itself lives on a business policy you create in
    Seller Hub. `policy_map` maps {max_handling_days: policy_id}; this picks
    the tightest policy whose handling time still covers `total_days`."""
    candidates = sorted((days, pid) for days, pid in policy_map.items() if days >= total_days)
    if not candidates:
        raise ValueError(
            f"no eBay fulfillment policy configured with handling time >= {total_days} days. "
            "Create one in Seller Hub > Business Policies with a matching handling time, "
            "then add it to EBAY_FULFILLMENT_POLICY_MAP."
        )
    return candidates[0][1]


# Shopee's product.add_item accepts days_to_ship directly (2-30). Beyond a
# platform-specific threshold it must be flagged as a pre-order item.
SHOPEE_MAX_NORMAL_DAYS_TO_SHIP = 7
SHOPEE_MAX_DAYS_TO_SHIP = 30


def shopee_shipping_terms(total_days: int) -> tuple[int, bool]:
    """Returns (days_to_ship, is_pre_order) clamped to what Shopee accepts."""
    days_to_ship = max(2, min(total_days, SHOPEE_MAX_DAYS_TO_SHIP))
    is_pre_order = total_days > SHOPEE_MAX_NORMAL_DAYS_TO_SHIP
    return days_to_ship, is_pre_order
