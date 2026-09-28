"""Track a SourcingTask through purchased -> arrived -> shipped, and push the
tracking number back to the marketplace once it ships so the eBay/Shopee
order shows as fulfilled."""

from datetime import timedelta

from sqlalchemy.orm import Session

from ..clients.ebay import EbayClient
from ..clients.shopee import ShopeeClient
from ..models import SourcingTask
from ..timeutil import utcnow


def mark_purchased(session: Session, task: SourcingTask, actual_cost_jpy: float) -> SourcingTask:
    task.status = "purchased"
    task.actual_cost_jpy = actual_cost_jpy
    now = utcnow()
    task.purchased_at = now

    product = task.order_item.product
    lead_time_days = product.sourcing_lead_time_days if product else 3
    task.expected_arrival_by = now + timedelta(days=lead_time_days)

    session.commit()
    return task


def mark_arrived(session: Session, task: SourcingTask) -> SourcingTask:
    """Call this once the item you bought on Mercari/Yahoo/Amazon has
    physically arrived, before it goes back out to the end buyer."""
    task.status = "arrived"
    task.arrived_at = utcnow()
    session.commit()
    return task


def mark_shipped_and_notify(
    session: Session,
    task: SourcingTask,
    tracking_number: str,
    carrier_code: str,
    ebay_client: EbayClient | None = None,
    shopee_client: ShopeeClient | None = None,
) -> SourcingTask:
    task.tracking_number = tracking_number
    task.carrier_code = carrier_code
    task.status = "shipped"
    task.shipped_at = utcnow()

    order = task.order_item.order
    if order.marketplace == "ebay":
        if ebay_client is None:
            raise ValueError("ebay_client is required to notify an eBay order")
        ebay_client.create_shipping_fulfillment(
            order_id=order.external_order_id,
            line_items=[{"lineItemId": task.order_item.sku, "quantity": task.order_item.quantity}],
            tracking_number=tracking_number,
            carrier_code=carrier_code,
        )
    elif order.marketplace == "shopee":
        if shopee_client is None:
            raise ValueError("shopee_client is required to notify a Shopee order")
        shopee_client.ship_order(order_sn=order.external_order_id, tracking_number=tracking_number)
    else:
        raise ValueError(f"unknown marketplace: {order.marketplace}")

    session.commit()
    return task
