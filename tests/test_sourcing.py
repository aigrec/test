from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Order, OrderItem, Product
from app.services.fulfillment import mark_arrived, mark_purchased
from app.services.sourcing import create_sourcing_tasks_for_order, is_task_overdue, task_deadline
from app.timeutil import utcnow


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_order_with_item(session, created_at, lead_time_days=3):
    product = Product(
        sku="SKU-1",
        title="Widget",
        source_platform="mercari",
        cost_jpy=3000,
        sourcing_lead_time_days=lead_time_days,
    )
    session.add(product)
    session.flush()

    order = Order(marketplace="ebay", external_order_id="ORDER-1", created_at=created_at)
    session.add(order)
    session.flush()

    item = OrderItem(order_id=order.id, product_id=product.id, sku=product.sku, title=product.title, quantity=1)
    session.add(item)
    session.commit()
    return order, item


def test_create_sourcing_tasks_for_order(session):
    order, item = _make_order_with_item(session, utcnow())
    tasks = create_sourcing_tasks_for_order(session, order)
    assert len(tasks) == 1
    assert tasks[0].status == "pending_purchase"
    assert tasks[0].source_platform == "mercari"


def test_task_not_overdue_before_deadline(session):
    now = utcnow()
    order, item = _make_order_with_item(session, now, lead_time_days=3)
    task = create_sourcing_tasks_for_order(session, order)[0]

    assert task_deadline(task) > now
    assert not is_task_overdue(task, reference_time=now)


def test_task_overdue_after_deadline(session):
    old = utcnow() - timedelta(days=30)
    order, item = _make_order_with_item(session, old, lead_time_days=3)
    task = create_sourcing_tasks_for_order(session, order)[0]

    assert is_task_overdue(task)


def test_shipped_task_is_never_overdue(session):
    old = utcnow() - timedelta(days=30)
    order, item = _make_order_with_item(session, old, lead_time_days=3)
    task = create_sourcing_tasks_for_order(session, order)[0]
    task.status = "shipped"
    session.commit()

    assert not is_task_overdue(task)


def test_mark_purchased_sets_expected_arrival_from_product_lead_time(session):
    order, item = _make_order_with_item(session, utcnow(), lead_time_days=4)
    task = create_sourcing_tasks_for_order(session, order)[0]

    before = utcnow()
    mark_purchased(session, task, actual_cost_jpy=2900)

    assert task.status == "purchased"
    assert task.expected_arrival_by is not None
    delta = task.expected_arrival_by - before
    assert timedelta(days=3, hours=23) < delta < timedelta(days=4, hours=1)


def test_mark_arrived_sets_status_and_timestamp(session):
    order, item = _make_order_with_item(session, utcnow())
    task = create_sourcing_tasks_for_order(session, order)[0]
    mark_purchased(session, task, actual_cost_jpy=2900)

    mark_arrived(session, task)

    assert task.status == "arrived"
    assert task.arrived_at is not None
