"""Run periodically (e.g. via cron every 15 minutes) to pull new orders from
eBay and Shopee and turn them into sourcing tasks.

    python scripts/sync_orders.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.clients.ebay import EbayClient  # noqa: E402
from app.clients.shopee import ShopeeClient  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import get_session, init_db  # noqa: E402
from app.services.order_sync import sync_ebay_orders, sync_shopee_orders  # noqa: E402


def main() -> None:
    init_db()
    session = get_session()
    try:
        if settings.ebay_refresh_token:
            ebay = EbayClient(
                client_id=settings.ebay_client_id,
                client_secret=settings.ebay_client_secret,
                refresh_token=settings.ebay_refresh_token,
                sandbox=settings.ebay_sandbox,
            )
            new_ebay_orders = sync_ebay_orders(session, ebay)
            print(f"eBay: {len(new_ebay_orders)} new order(s)")

        if settings.shopee_access_token:
            shopee = ShopeeClient(
                partner_id=settings.shopee_partner_id,
                partner_key=settings.shopee_partner_key,
                shop_id=settings.shopee_shop_id,
                access_token=settings.shopee_access_token,
                sandbox=settings.shopee_sandbox,
            )
            now = int(time.time())
            new_shopee_orders = sync_shopee_orders(session, shopee, time_from=now - 3600, time_to=now)
            print(f"Shopee: {len(new_shopee_orders)} new order(s)")
    finally:
        session.close()


if __name__ == "__main__":
    main()
