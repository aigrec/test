from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .clients.ebay import EbayClient
from .clients.shopee import ShopeeClient
from .config import settings
from .db import get_session, init_db
from .models import Product, SourcingTask
from .services.fulfillment import mark_purchased, mark_shipped_and_notify
from .services.listing import list_on_ebay, list_on_shopee

app = FastAPI(title="Dropship Ops")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def db_session():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def ebay_client() -> EbayClient:
    return EbayClient(
        client_id=settings.ebay_client_id,
        client_secret=settings.ebay_client_secret,
        refresh_token=settings.ebay_refresh_token,
        sandbox=settings.ebay_sandbox,
    )


def shopee_client() -> ShopeeClient:
    return ShopeeClient(
        partner_id=settings.shopee_partner_id,
        partner_key=settings.shopee_partner_key,
        shop_id=settings.shopee_shop_id,
        access_token=settings.shopee_access_token,
        sandbox=settings.shopee_sandbox,
    )


class ProductIn(BaseModel):
    sku: str
    title: str
    description: str = ""
    source_platform: str  # mercari | yahoo_auctions | amazon | other
    source_url: str = ""
    cost_jpy: float
    shipping_cost_jpy: float = 0.0
    weight_g: int = 0
    category_id_ebay: str = ""
    category_id_shopee: str = ""
    image_urls: str = ""


@app.post("/products")
def create_product(payload: ProductIn, session: Session = Depends(db_session)):
    product = Product(**payload.model_dump())
    session.add(product)
    session.commit()
    session.refresh(product)
    return {"id": product.id, "sku": product.sku}


@app.get("/products")
def list_products(session: Session = Depends(db_session)):
    return [
        {"id": p.id, "sku": p.sku, "title": p.title, "cost_jpy": p.cost_jpy}
        for p in session.query(Product).all()
    ]


class EbayListingPolicies(BaseModel):
    fulfillmentPolicyId: str
    paymentPolicyId: str
    returnPolicyId: str


@app.post("/products/{product_id}/list/ebay")
def create_ebay_listing(
    product_id: int,
    target_margin_percent: float | None = None,
    session: Session = Depends(db_session),
    client: EbayClient = Depends(ebay_client),
):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "product not found")
    policies = {
        "fulfillmentPolicyId": settings.ebay_fulfillment_policy_id,
        "paymentPolicyId": settings.ebay_payment_policy_id,
        "returnPolicyId": settings.ebay_return_policy_id,
    }
    listing = list_on_ebay(session, product, client, policies, target_margin_percent=target_margin_percent)
    return {"listing_id": listing.id, "price": listing.price, "currency": listing.currency}


@app.post("/products/{product_id}/list/shopee")
def create_shopee_listing(
    product_id: int,
    image_id_list: list[str],
    target_margin_percent: float | None = None,
    session: Session = Depends(db_session),
    client: ShopeeClient = Depends(shopee_client),
):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "product not found")
    listing = list_on_shopee(session, product, client, image_id_list, target_margin_percent=target_margin_percent)
    return {"listing_id": listing.id, "price": listing.price, "currency": listing.currency}


@app.get("/sourcing-tasks")
def list_sourcing_tasks(status: str | None = None, session: Session = Depends(db_session)):
    query = session.query(SourcingTask)
    if status:
        query = query.filter_by(status=status)
    return [
        {
            "id": t.id,
            "status": t.status,
            "source_platform": t.source_platform,
            "source_url": t.source_url,
            "estimated_cost_jpy": t.estimated_cost_jpy,
        }
        for t in query.all()
    ]


class PurchaseIn(BaseModel):
    actual_cost_jpy: float


@app.post("/sourcing-tasks/{task_id}/purchased")
def purchase_sourcing_task(task_id: int, payload: PurchaseIn, session: Session = Depends(db_session)):
    task = session.get(SourcingTask, task_id)
    if not task:
        raise HTTPException(404, "sourcing task not found")
    mark_purchased(session, task, payload.actual_cost_jpy)
    return {"id": task.id, "status": task.status}


class ShipIn(BaseModel):
    tracking_number: str
    carrier_code: str


@app.post("/sourcing-tasks/{task_id}/shipped")
def ship_sourcing_task(
    task_id: int,
    payload: ShipIn,
    session: Session = Depends(db_session),
    ebay: EbayClient = Depends(ebay_client),
    shopee: ShopeeClient = Depends(shopee_client),
):
    task = session.get(SourcingTask, task_id)
    if not task:
        raise HTTPException(404, "sourcing task not found")
    mark_shipped_and_notify(
        session,
        task,
        tracking_number=payload.tracking_number,
        carrier_code=payload.carrier_code,
        ebay_client=ebay,
        shopee_client=shopee,
    )
    return {"id": task.id, "status": task.status}
