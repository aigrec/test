import json
import os

from dotenv import load_dotenv

load_dotenv()


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./dropship.db")

    # eBay
    ebay_client_id: str = os.getenv("EBAY_CLIENT_ID", "")
    ebay_client_secret: str = os.getenv("EBAY_CLIENT_SECRET", "")
    ebay_refresh_token: str = os.getenv("EBAY_REFRESH_TOKEN", "")
    ebay_sandbox: bool = _bool(os.getenv("EBAY_SANDBOX"), True)
    ebay_marketplace_id: str = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US")
    ebay_merchant_location_key: str = os.getenv("EBAY_MERCHANT_LOCATION_KEY", "")
    ebay_fulfillment_policy_id: str = os.getenv("EBAY_FULFILLMENT_POLICY_ID", "")
    ebay_payment_policy_id: str = os.getenv("EBAY_PAYMENT_POLICY_ID", "")
    ebay_return_policy_id: str = os.getenv("EBAY_RETURN_POLICY_ID", "")
    # JSON object mapping {"<max handling days>": "<business policy id>"}, e.g.
    # {"3": "policy-fast", "7": "policy-standard", "14": "policy-slow"}.
    # Each policy must already exist in Seller Hub with that handling time.
    ebay_fulfillment_policy_map: dict[int, str] = {
        int(k): v for k, v in json.loads(os.getenv("EBAY_FULFILLMENT_POLICY_MAP", "{}")).items()
    }

    # Shopee
    shopee_partner_id: str = os.getenv("SHOPEE_PARTNER_ID", "")
    shopee_partner_key: str = os.getenv("SHOPEE_PARTNER_KEY", "")
    shopee_shop_id: str = os.getenv("SHOPEE_SHOP_ID", "")
    shopee_access_token: str = os.getenv("SHOPEE_ACCESS_TOKEN", "")
    shopee_sandbox: bool = _bool(os.getenv("SHOPEE_SANDBOX"), True)

    # Pricing
    default_target_margin_percent: float = float(os.getenv("DEFAULT_TARGET_MARGIN_PERCENT", "0.30"))
    default_fx_jpy_to_usd: float = float(os.getenv("DEFAULT_FX_JPY_TO_USD", "0.0067"))
    default_fx_jpy_to_myr: float = float(os.getenv("DEFAULT_FX_JPY_TO_MYR", "0.030"))

    # Days added on top of a product's sourcing lead time for inspection,
    # repackaging, and dropping off the outbound (international) shipment.
    handling_buffer_days: int = int(os.getenv("HANDLING_BUFFER_DAYS", "2"))


settings = Settings()
