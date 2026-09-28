# Dropship Ops (eBay / Shopee)

Backend for a no-inventory reselling operation: list products on eBay and
Shopee via their official seller APIs, price them automatically from your
sourcing cost, and turn incoming orders into a manual sourcing task queue.

## What this does — and deliberately does not do

- **Listing & inventory sync (eBay, Shopee)**: fully automated via each
  platform's official Seller/Open Platform API.
- **Pricing**: selling price is computed from cost + shipping + fees to hit
  a target margin (see `app/pricing.py`).
- **Order → sourcing task**: when an eBay/Shopee order comes in, a
  `SourcingTask` is created automatically.
- **Sourcing (Mercari / Yahoo!オークション / Amazon)**: **manual, by
  design.** None of these three publish a public API for third parties to
  place purchases, so automating that step would mean scraping/bot
  automation against their terms of service. On top of that, eBay's own
  policy prohibits "drop shipping" from another online retailer/marketplace
  that ships directly to the buyer — so even if automated purchasing were
  technically possible, using it to fulfill eBay orders would risk account
  suspension. Reselling secondhand goods sourced this way as a business may
  also require a 古物商許可 (secondhand dealer license) in Japan.
  → This tool surfaces a task queue (`/sourcing-tasks`) that a human works
  through by hand; once you mark a task "shipped" with a tracking number,
  it automatically notifies eBay/Shopee so the order shows as fulfilled.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your eBay/Shopee credentials
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive API.

Run the order sync (put this on a cron job, e.g. every 15 minutes):

```bash
python scripts/sync_orders.py
```

## Credentials you need

- **eBay**: a developer account, an app (client id/secret), and a user
  refresh token obtained once via eBay's OAuth consent flow
  (`sell.inventory` + `sell.fulfillment` scopes).
- **Shopee**: a Partner account, `partner_id`/`partner_key`, and a shop
  access token from the Open Platform authorization flow.

## Workflow

1. `POST /products` — register a product you plan to source (title, cost,
   source platform/URL, weight, category ids).
2. `POST /products/{id}/list/ebay` or `/list/shopee` — computes the selling
   price from cost + fees + your target margin, then publishes the listing.
3. Run `scripts/sync_orders.py` (or call it on a schedule) to pull new
   orders and auto-create sourcing tasks.
4. Buy the item yourself on Mercari/Yahoo!オークション/Amazon, then:
   - `POST /sourcing-tasks/{id}/purchased` with the actual cost.
   - `POST /sourcing-tasks/{id}/shipped` with the tracking number — this
     pushes the fulfillment update back to eBay/Shopee.

## Tests

```bash
python -m pytest
```

Covers the pricing math and the eBay OAuth/Shopee HMAC signing logic
against fake HTTP responses (no live API calls).
