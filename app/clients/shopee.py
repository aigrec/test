"""Minimal Shopee Open Platform v2 client (product + order + logistics APIs).

Signing scheme per https://open.shopee.com/documents (shop-level APIs):
sign = HMAC-SHA256(partner_id + api_path + timestamp + access_token + shop_id, partner_key)
"""

import hashlib
import hmac
import time

import requests


class ShopeeApiError(Exception):
    def __init__(self, error_code: str, message: str):
        super().__init__(f"Shopee API error {error_code}: {message}")
        self.error_code = error_code
        self.message = message


class ShopeeClient:
    BASE_URL_LIVE = "https://partner.shopeemobile.com"
    BASE_URL_SANDBOX = "https://partner.test-stable.shopeemobile.com"

    def __init__(
        self,
        partner_id: str,
        partner_key: str,
        shop_id: str,
        access_token: str,
        sandbox: bool = True,
        session: requests.Session | None = None,
    ):
        self.partner_id = partner_id
        self.partner_key = partner_key
        self.shop_id = shop_id
        self.access_token = access_token
        self.sandbox = sandbox
        self._session = session or requests.Session()

    @property
    def base_url(self) -> str:
        return self.BASE_URL_SANDBOX if self.sandbox else self.BASE_URL_LIVE

    def sign(self, path: str, timestamp: int) -> str:
        base_string = f"{self.partner_id}{path}{timestamp}{self.access_token}{self.shop_id}"
        return hmac.new(
            self.partner_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _request(self, method: str, path: str, json_body: dict | None = None, extra_params: dict | None = None) -> dict:
        timestamp = int(time.time())
        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "access_token": self.access_token,
            "shop_id": self.shop_id,
            "sign": self.sign(path, timestamp),
        }
        if extra_params:
            params.update(extra_params)
        url = f"{self.base_url}{path}"
        resp = self._session.request(method, url, params=params, json=json_body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise ShopeeApiError(data["error"], data.get("message", ""))
        return data

    # ---- Product API -------------------------------------------------

    def add_item(
        self,
        item_name: str,
        description: str,
        price: float,
        stock: int,
        category_id: int,
        image_id_list: list[str],
        weight_kg: float,
        days_to_ship: int = 2,
        is_pre_order: bool = False,
    ) -> dict:
        body = {
            "item_name": item_name,
            "description": description,
            "original_price": price,
            "normal_stock": stock,
            "category_id": category_id,
            "image": {"image_id_list": image_id_list},
            "weight": weight_kg,
            "pre_order": {"is_pre_order": is_pre_order, "days_to_ship": days_to_ship},
        }
        return self._request("POST", "/api/v2/product/add_item", json_body=body)

    def update_stock(self, item_id: int, stock: int, model_id: int = 0) -> dict:
        body = {
            "item_id": item_id,
            "stock_list": [{"model_id": model_id, "normal_stock": stock}],
        }
        return self._request("POST", "/api/v2/product/update_stock", json_body=body)

    def update_price(self, item_id: int, price: float, model_id: int = 0) -> dict:
        body = {
            "item_id": item_id,
            "price_list": [{"model_id": model_id, "original_price": price}],
        }
        return self._request("POST", "/api/v2/product/update_price", json_body=body)

    # ---- Order API -------------------------------------------------

    def get_order_list(self, time_from: int, time_to: int, cursor: str = "", page_size: int = 20) -> dict:
        params = {
            "time_range_field": "create_time",
            "time_from": time_from,
            "time_to": time_to,
            "page_size": page_size,
            "cursor": cursor,
        }
        return self._request("GET", "/api/v2/order/get_order_list", extra_params=params)

    def get_order_detail(self, order_sn_list: list[str]) -> dict:
        params = {"order_sn_list": ",".join(order_sn_list)}
        return self._request("GET", "/api/v2/order/get_order_detail", extra_params=params)

    # ---- Logistics API -------------------------------------------------

    def ship_order(self, order_sn: str, tracking_number: str, package_number: str | None = None) -> dict:
        body: dict = {"order_sn": order_sn, "tracking_number": tracking_number}
        if package_number:
            body["package_number"] = package_number
        return self._request("POST", "/api/v2/logistics/ship_order", json_body=body)
