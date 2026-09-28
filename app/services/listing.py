"""Create/update listings on eBay and Shopee from a Product, using the
pricing module to derive the selling price."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..clients.ebay import EbayClient
from ..clients.shopee import ShopeeClient
from ..config import settings
from ..models import Listing, Product
from ..pricing import (
    EBAY_DEFAULT_FEES,
    SHOPEE_DEFAULT_FEES,
    convert_currency,
    required_selling_price,
)


def _image_urls(product: Product) -> list[str]:
    return [u.strip() for u in product.image_urls.split(",") if u.strip()]


def list_on_ebay(
    session: Session,
    product: Product,
    client: EbayClient,
    listing_policies: dict,
    target_margin_percent: float | None = None,
    fx_rate: float | None = None,
) -> Listing:
    margin = target_margin_percent if target_margin_percent is not None else settings.default_target_margin_percent
    rate = fx_rate if fx_rate is not None else settings.default_fx_jpy_to_usd
    cost = convert_currency(product.cost_jpy, rate)
    shipping = convert_currency(product.shipping_cost_jpy, rate)
    price = round(required_selling_price(cost, shipping, EBAY_DEFAULT_FEES, margin), 2)

    client.upsert_inventory_item(
        sku=product.sku,
        title=product.title,
        description=product.description,
        quantity=1,
        image_urls=_image_urls(product),
    )
    offer_id = client.create_offer(
        sku=product.sku,
        marketplace_id=settings.ebay_marketplace_id,
        category_id=product.category_id_ebay,
        price=price,
        currency="USD",
        quantity=1,
        listing_policies=listing_policies,
        merchant_location_key=settings.ebay_merchant_location_key,
    )
    client.publish_offer(offer_id)

    listing = Listing(
        product_id=product.id,
        marketplace="ebay",
        external_offer_id=offer_id,
        price=price,
        currency="USD",
        quantity=1,
        status="active",
        last_synced_at=datetime.now(timezone.utc),
    )
    session.add(listing)
    session.commit()
    return listing


def list_on_shopee(
    session: Session,
    product: Product,
    client: ShopeeClient,
    image_id_list: list[str],
    target_margin_percent: float | None = None,
    fx_rate: float | None = None,
) -> Listing:
    margin = target_margin_percent if target_margin_percent is not None else settings.default_target_margin_percent
    rate = fx_rate if fx_rate is not None else settings.default_fx_jpy_to_myr
    cost = convert_currency(product.cost_jpy, rate)
    shipping = convert_currency(product.shipping_cost_jpy, rate)
    price = round(required_selling_price(cost, shipping, SHOPEE_DEFAULT_FEES, margin), 2)

    result = client.add_item(
        item_name=product.title,
        description=product.description,
        price=price,
        stock=1,
        category_id=int(product.category_id_shopee or 0),
        image_id_list=image_id_list,
        weight_kg=max(product.weight_g, 1) / 1000.0,
    )
    item_id = result["response"]["item_id"]

    listing = Listing(
        product_id=product.id,
        marketplace="shopee",
        external_item_id=str(item_id),
        price=price,
        currency="MYR",
        quantity=1,
        status="active",
        last_synced_at=datetime.now(timezone.utc),
    )
    session.add(listing)
    session.commit()
    return listing
