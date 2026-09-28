"""Turn newly-synced orders into sourcing tasks for a human to fulfil by hand
on Mercari / Yahoo Auctions / Amazon. Deliberately not automated purchasing:
none of those platforms offer a public buy-side API, and automating
purchases there would risk violating their terms of service."""

from sqlalchemy.orm import Session

from ..models import Order, SourcingTask


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
