"""Minimal eBay Sell API client (Inventory API + Fulfillment API).

Uses the OAuth2 refresh-token grant: you obtain a user refresh token once
via eBay's consent flow (https://developer.ebay.com/api-docs/static/oauth-tokens.html)
and this client exchanges it for short-lived access tokens as needed.
"""

import time

import requests


class EbayAuthError(Exception):
    pass


class EbayApiError(Exception):
    def __init__(self, status_code: int, body: str):
        super().__init__(f"eBay API error {status_code}: {body}")
        self.status_code = status_code
        self.body = body


DEFAULT_SCOPES = [
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
]


class EbayClient:
    SANDBOX_API_BASE = "https://api.sandbox.ebay.com"
    PROD_API_BASE = "https://api.ebay.com"
    SANDBOX_TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    PROD_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        sandbox: bool = True,
        scopes: list[str] | None = None,
        session: requests.Session | None = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.sandbox = sandbox
        self.scopes = scopes or DEFAULT_SCOPES
        self._session = session or requests.Session()
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    @property
    def base_url(self) -> str:
        return self.SANDBOX_API_BASE if self.sandbox else self.PROD_API_BASE

    @property
    def token_url(self) -> str:
        return self.SANDBOX_TOKEN_URL if self.sandbox else self.PROD_TOKEN_URL

    def _refresh_access_token(self) -> None:
        resp = self._session.post(
            self.token_url,
            auth=(self.client_id, self.client_secret),
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "scope": " ".join(self.scopes),
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise EbayAuthError(f"failed to refresh eBay token: {resp.status_code} {resp.text}")
        payload = resp.json()
        self._access_token = payload["access_token"]
        self._expires_at = time.time() + payload.get("expires_in", 7200) - 60

    def get_access_token(self) -> str:
        if not self._access_token or time.time() >= self._expires_at:
            self._refresh_access_token()
        assert self._access_token is not None
        return self._access_token

    def _headers(self, content_language: str = "en-US") -> dict:
        return {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json",
            "Content-Language": content_language,
        }

    def _check(self, resp: requests.Response) -> requests.Response:
        if resp.status_code >= 400:
            raise EbayApiError(resp.status_code, resp.text)
        return resp

    # ---- Inventory API -------------------------------------------------

    def upsert_inventory_item(
        self,
        sku: str,
        title: str,
        description: str,
        quantity: int,
        image_urls: list[str],
        condition: str = "NEW",
        aspects: dict | None = None,
    ) -> None:
        url = f"{self.base_url}/sell/inventory/v1/inventory_item/{sku}"
        body = {
            "availability": {"shipToLocationAvailability": {"quantity": quantity}},
            "condition": condition,
            "product": {
                "title": title,
                "description": description,
                "imageUrls": image_urls,
                "aspects": aspects or {},
            },
        }
        self._check(self._session.put(url, json=body, headers=self._headers(), timeout=30))

    def create_offer(
        self,
        sku: str,
        marketplace_id: str,
        category_id: str,
        price: float,
        currency: str,
        quantity: int,
        listing_policies: dict,
        merchant_location_key: str,
    ) -> str:
        url = f"{self.base_url}/sell/inventory/v1/offer"
        body = {
            "sku": sku,
            "marketplaceId": marketplace_id,
            "format": "FIXED_PRICE",
            "availableQuantity": quantity,
            "categoryId": category_id,
            "listingPolicies": listing_policies,
            "merchantLocationKey": merchant_location_key,
            "pricingSummary": {"price": {"value": f"{price:.2f}", "currency": currency}},
        }
        resp = self._check(self._session.post(url, json=body, headers=self._headers(), timeout=30))
        return resp.json()["offerId"]

    def publish_offer(self, offer_id: str) -> dict:
        url = f"{self.base_url}/sell/inventory/v1/offer/{offer_id}/publish"
        resp = self._check(self._session.post(url, headers=self._headers(), timeout=30))
        return resp.json()

    def update_price_quantity(self, sku: str, price: float, currency: str, quantity: int) -> dict:
        url = f"{self.base_url}/sell/inventory/v1/bulk_update_price_quantity"
        body = {
            "requests": [
                {
                    "sku": sku,
                    "shipToLocationAvailability": {"quantity": quantity},
                    "price": {"value": f"{price:.2f}", "currency": currency},
                }
            ]
        }
        resp = self._check(self._session.post(url, json=body, headers=self._headers(), timeout=30))
        return resp.json()

    # ---- Fulfillment API -------------------------------------------------

    def get_orders(self, filter_str: str | None = None, limit: int = 50) -> dict:
        url = f"{self.base_url}/sell/fulfillment/v1/order"
        params: dict = {"limit": limit}
        if filter_str:
            params["filter"] = filter_str
        resp = self._check(self._session.get(url, headers=self._headers(), params=params, timeout=30))
        return resp.json()

    def create_shipping_fulfillment(
        self,
        order_id: str,
        line_items: list[dict],
        tracking_number: str,
        carrier_code: str,
        shipped_date: str | None = None,
    ) -> dict:
        url = f"{self.base_url}/sell/fulfillment/v1/order/{order_id}/shipping_fulfillment"
        body = {
            "lineItems": line_items,
            "shippingCarrierCode": carrier_code,
            "trackingNumber": tracking_number,
        }
        if shipped_date:
            body["shippedDate"] = shipped_date
        resp = self._check(self._session.post(url, json=body, headers=self._headers(), timeout=30))
        return resp.json()
