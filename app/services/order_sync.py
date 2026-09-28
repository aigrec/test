"""Pull new orders from eBay and Shopee, upsert them locally, and generate
sourcing tasks for any order that doesn't have one yet."""

from sqlalchemy.orm import Session

from ..clients.ebay import EbayClient
from ..clients.shopee import ShopeeClient
from ..models import Order, OrderItem, Product
from .sourcing import create_sourcing_tasks_for_order


def _get_or_create_order(session: Session, marketplace: str, external_order_id: str) -> tuple[Order, bool]:
    existing = (
        session.query(Order)
        .filter_by(marketplace=marketplace, external_order_id=external_order_id)
        .one_or_none()
    )
    if existing:
        return existing, False
    order = Order(marketplace=marketplace, external_order_id=external_order_id)
    session.add(order)
    session.flush()
    return order, True


def _find_product_by_sku(session: Session, sku: str) -> Product | None:
    if not sku:
        return None
    return session.query(Product).filter_by(sku=sku).one_or_none()


def sync_ebay_orders(session: Session, client: EbayClient, filter_str: str | None = None) -> list[Order]:
    payload = client.get_orders(filter_str=filter_str)
    new_orders: list[Order] = []
    for raw in payload.get("orders", []):
        order, created = _get_or_create_order(session, "ebay", raw["orderId"])
        if not created:
            continue
        buyer = raw.get("buyer", {})
        total = raw.get("pricingSummary", {}).get("total", {})
        ship_to = (raw.get("fulfillmentStartInstructions") or [{}])[0].get("shippingStep", {}).get("shipTo", {})
        order.buyer_name = buyer.get("username", "")
        order.buyer_country = ship_to.get("contactAddress", {}).get("countryCode", "")
        order.total_amount = float(total.get("value", 0) or 0)
        order.currency = total.get("currency", "")
        order.status = raw.get("orderFulfillmentStatus", "new")

        for li in raw.get("lineItems", []):
            cost = li.get("lineItemCost", {})
            item = OrderItem(
                order_id=order.id,
                sku=li.get("sku", ""),
                title=li.get("title", ""),
                quantity=int(li.get("quantity", 1)),
                unit_price=float(cost.get("value", 0) or 0),
                currency=cost.get("currency", ""),
            )
            product = _find_product_by_sku(session, item.sku)
            if product:
                item.product_id = product.id
            session.add(item)

        session.commit()
        create_sourcing_tasks_for_order(session, order)
        new_orders.append(order)

    return new_orders


def sync_shopee_orders(session: Session, client: ShopeeClient, time_from: int, time_to: int) -> list[Order]:
    listing = client.get_order_list(time_from=time_from, time_to=time_to)
    order_sns = [o["order_sn"] for o in listing.get("response", {}).get("order_list", [])]
    new_orders: list[Order] = []
    if not order_sns:
        return new_orders

    detail = client.get_order_detail(order_sns)
    for raw in detail.get("response", {}).get("order_list", []):
        order, created = _get_or_create_order(session, "shopee", raw["order_sn"])
        if not created:
            continue
        recipient = raw.get("recipient_address", {})
        order.buyer_name = raw.get("buyer_username", "")
        order.buyer_country = recipient.get("country", "")
        order.total_amount = float(raw.get("total_amount", 0) or 0)
        order.currency = raw.get("currency", "")
        order.status = raw.get("order_status", "new")

        for li in raw.get("item_list", []):
            item = OrderItem(
                order_id=order.id,
                sku=li.get("item_sku", ""),
                title=li.get("item_name", ""),
                quantity=int(li.get("model_quantity_purchased", 1)),
                unit_price=float(li.get("model_discounted_price", 0) or 0),
                currency=raw.get("currency", ""),
            )
            product = _find_product_by_sku(session, item.sku)
            if product:
                item.product_id = product.id
            session.add(item)

        session.commit()
        create_sourcing_tasks_for_order(session, order)
        new_orders.append(order)

    return new_orders
