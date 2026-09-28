import hashlib
import hmac

from app.clients.shopee import ShopeeClient


def test_sign_matches_reference_hmac():
    client = ShopeeClient(
        partner_id="12345",
        partner_key="secret-key",
        shop_id="67890",
        access_token="token-abc",
        sandbox=True,
    )
    path = "/api/v2/product/add_item"
    timestamp = 1700000000

    expected_base = f"12345{path}{timestamp}token-abc67890"
    expected = hmac.new(b"secret-key", expected_base.encode(), hashlib.sha256).hexdigest()

    assert client.sign(path, timestamp) == expected


def test_sign_changes_with_timestamp():
    client = ShopeeClient(partner_id="1", partner_key="k", shop_id="2", access_token="t")
    assert client.sign("/api/v2/order/get_order_list", 100) != client.sign("/api/v2/order/get_order_list", 200)


def test_base_url_switches_for_sandbox():
    live = ShopeeClient(partner_id="1", partner_key="k", shop_id="2", access_token="t", sandbox=False)
    sandbox = ShopeeClient(partner_id="1", partner_key="k", shop_id="2", access_token="t", sandbox=True)
    assert live.base_url != sandbox.base_url
