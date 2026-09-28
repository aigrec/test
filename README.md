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
   source platform/URL, weight, category ids, and `sourcing_lead_time_days`:
   how long it realistically takes to receive the item after buying it on
   Mercari/Yahoo!オークション/Amazon — e.g. 2-3 days domestic).
2. `POST /products/{id}/list/ebay` or `/list/shopee` — computes the selling
   price from cost + fees + your target margin, then publishes the listing
   with a handling time/days-to-ship that reflects that lead time (see
   "Handling the purchase → ship lag" below) instead of a fixed default.
3. Run `scripts/sync_orders.py` (or call it on a schedule) to pull new
   orders and auto-create sourcing tasks.
4. Work the sourcing task through its lifecycle as the days pass:
   - `POST /sourcing-tasks/{id}/purchased` with the actual cost, right after
     you buy it — this also stores `expected_arrival_by`.
   - `POST /sourcing-tasks/{id}/arrived` once it physically shows up.
   - `POST /sourcing-tasks/{id}/shipped` with the tracking number once you've
     repackaged and sent it to the end buyer — this pushes the fulfillment
     update back to eBay/Shopee.
5. `GET /sourcing-tasks?overdue_only=true` — tasks past their deadline
   (order time + sourcing lead time + repack/ship buffer) so a slow
   purchase doesn't quietly turn into a late-shipment strike.

## Handling the purchase → ship lag

There's an unavoidable multi-day gap between "order comes in" and "item is
in the mail to the buyer": you still have to buy it, wait for it to arrive,
then repack and ship it out. This tool doesn't shorten that gap — it makes
sure the listings and task queue are honest about it instead of silently
overpromising:

- **eBay**: handling time comes from a business policy (Seller Hub), not a
  free-form value in the API call. Create a few policies with different
  handling times (e.g. 3/7/14 days) and map them via
  `EBAY_FULFILLMENT_POLICY_MAP={"3": "policy-id-a", "7": "policy-id-b"}` in
  `.env`; the listing service picks the tightest one that still covers
  `sourcing_lead_time_days + HANDLING_BUFFER_DAYS`.
- **Shopee**: `days_to_ship` (and `pre_order` once it's over ~7 days) is set
  directly from the same calculation — no manual policy setup needed.
- **Sourcing tasks**: `expected_arrival_by` is stamped when you mark a task
  "purchased", and `GET /sourcing-tasks` reports `is_overdue`/`deadline` so
  you can see at a glance which orders are at risk of shipping late.

`HANDLING_BUFFER_DAYS` (default 2) covers inspecting, repackaging, and
dropping off the outbound international shipment — bump it up if your
overseas shipping method needs more lead time.

## Tests

```bash
python -m pytest
```

Covers the pricing math and the eBay OAuth/Shopee HMAC signing logic
against fake HTTP responses (no live API calls).
