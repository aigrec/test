from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    """A sourceable product. Sourcing itself stays a manual, human task —
    see SourcingTask — because none of Mercari/Yahoo Auctions/Amazon expose
    a public purchasing API for third-party automation."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(4000), default="")
    source_platform: Mapped[str] = mapped_column(String(32))  # mercari | yahoo_auctions | amazon | other
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    cost_jpy: Mapped[float] = mapped_column(Float)
    shipping_cost_jpy: Mapped[float] = mapped_column(Float, default=0.0)
    weight_g: Mapped[int] = mapped_column(Integer, default=0)
    category_id_ebay: Mapped[str] = mapped_column(String(32), default="")
    category_id_shopee: Mapped[str] = mapped_column(String(32), default="")
    image_urls: Mapped[str] = mapped_column(String(4000), default="")  # comma-separated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    listings: Mapped[list["Listing"]] = relationship(back_populates="product")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    marketplace: Mapped[str] = mapped_column(String(16))  # ebay | shopee
    external_item_id: Mapped[str] = mapped_column(String(64), default="")
    external_offer_id: Mapped[str] = mapped_column(String(64), default="")  # eBay offerId
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft | active | ended
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="listings")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marketplace: Mapped[str] = mapped_column(String(16))  # ebay | shopee
    external_order_id: Mapped[str] = mapped_column(String(64), index=True)
    buyer_name: Mapped[str] = mapped_column(String(255), default="")
    buyer_country: Mapped[str] = mapped_column(String(8), default="")
    status: Mapped[str] = mapped_column(String(24), default="new")
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    sku: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="")

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product | None"] = relationship()
    sourcing_task: Mapped["SourcingTask | None"] = relationship(back_populates="order_item", uselist=False)


class SourcingTask(Base):
    """Represents the human task of buying the item on Mercari/Yahoo
    Auctions/Amazon and shipping it out. Deliberately not automated."""

    __tablename__ = "sourcing_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id"), unique=True)
    status: Mapped[str] = mapped_column(String(24), default="pending_purchase")
    # pending_purchase -> purchased -> shipped (or cancelled)
    source_platform: Mapped[str] = mapped_column(String(32), default="")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    estimated_cost_jpy: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost_jpy: Mapped[float | None] = mapped_column(Float, nullable=True)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tracking_number: Mapped[str] = mapped_column(String(128), default="")
    carrier_code: Mapped[str] = mapped_column(String(64), default="")
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    order_item: Mapped["OrderItem"] = relationship(back_populates="sourcing_task")
