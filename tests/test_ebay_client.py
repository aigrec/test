from app.clients.ebay import EbayClient


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text or str(json_data)

    def json(self):
        return self._json


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if url.endswith("/oauth2/token"):
            return FakeResponse(200, {"access_token": "tok-1", "expires_in": 7200})
        if url.endswith("/publish"):
            return FakeResponse(200, {"listingId": "999"})
        if url.endswith("/offer"):
            return FakeResponse(200, {"offerId": "offer-1"})
        return FakeResponse(200, {})

    def put(self, url, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        return FakeResponse(200, {})

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return FakeResponse(200, {"orders": []})


def make_client():
    session = FakeSession()
    client = EbayClient(
        client_id="cid",
        client_secret="csecret",
        refresh_token="rtoken",
        sandbox=True,
        session=session,
    )
    return client, session


def test_get_access_token_fetches_and_caches():
    client, session = make_client()
    token1 = client.get_access_token()
    token2 = client.get_access_token()
    assert token1 == "tok-1"
    assert token2 == "tok-1"
    token_calls = [c for c in session.calls if c[1].endswith("/oauth2/token")]
    assert len(token_calls) == 1  # cached, not re-fetched


def test_get_access_token_refreshes_when_expired():
    client, session = make_client()
    client.get_access_token()
    client._expires_at = 0  # force expiry
    client.get_access_token()
    token_calls = [c for c in session.calls if c[1].endswith("/oauth2/token")]
    assert len(token_calls) == 2


def test_create_offer_and_publish_uses_bearer_token():
    client, session = make_client()
    offer_id = client.create_offer(
        sku="SKU-1",
        marketplace_id="EBAY_US",
        category_id="12345",
        price=19.99,
        currency="USD",
        quantity=1,
        listing_policies={},
        merchant_location_key="loc-1",
    )
    assert offer_id == "offer-1"
    result = client.publish_offer(offer_id)
    assert result == {"listingId": "999"}

    offer_call = next(c for c in session.calls if c[1].endswith("/offer"))
    assert offer_call[2]["headers"]["Authorization"] == "Bearer tok-1"


def test_sandbox_flag_picks_sandbox_base_url():
    client, _ = make_client()
    assert "sandbox" in client.base_url
    assert "sandbox" in client.token_url
