"""Turn newly-synced orders into sourcing tasks for a human to fulfil by hand
on Mercari / Yahoo Auctions / Amazon. Deliberately not automated purchasing:
none of those platforms offer a public buy-side API, and automating
purchases there would risk violating their terms of service."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Order, SourcingTask
from ..timeutil import utcnow

_TERMINAL_STATUSES = {"shipped", "cancelled"}


def create_sourcing_tasks_for_order(session: Session, order: Order) -> list[SourcingTask]:
    tasks = []
    for item in order.items:
        if item.sourcing_task is not None:
            continue
        product = item.product
        task = SourcingTask(
            order_item_id=item.id,
            status="pending_purchase",
            source_platform=product.source_platform if product else "unknown",
            source_url=product.source_url if product else "",
            estimated_cost_jpy=product.cost_jpy if product else None,
        )
        session.add(task)
        tasks.append(task)
    session.commit()
    return tasks


def task_deadline(task: SourcingTask) -> datetime:
    """The point by which the item should realistically be in the mail to
    the buyer, given the marketplace order time and this product's expected
    sourcing lead time (see Product.sourcing_lead_time_days)."""
    if task.expected_arrival_by is not None:
        return task.expected_arrival_by + timedelta(days=settings.handling_buffer_days)
    product = task.order_item.product
    lead_time_days = product.sourcing_lead_time_days if product else 3
    total_days = lead_time_days + settings.handling_buffer_days
    return task.order_item.order.created_at + timedelta(days=total_days)


def is_task_overdue(task: SourcingTask, reference_time: datetime | None = None) -> bool:
    if task.status in _TERMINAL_STATUSES:
        return False
    now = reference_time or utcnow()
    return now > task_deadline(task)
