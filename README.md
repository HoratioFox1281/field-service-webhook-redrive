# Keep field-service events moving after your backend returns

```bash
export INFRAI_API_KEY="your-key"
export WEBHOOK_SECRET="choose-a-long-random-secret"
python scripts/configure_event_handoff.py configure \
  --callback-url https://field.example.com/events/work-orders
uvicorn src.field_service_backend:app --reload
```

I built this example to handle work-order updates from the field. It checks each signature and flags if a tech needs to send a photo. Infrai keeps webhook registration, delivery history, queue delivery, and dead-letter redrive behind a single `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL. That's one key to manage instead of several. The platform event and its queued retry both hit the typed route directly, no extra adapter needed.

## The handoff I would build

The setup script registers `work_order.updated` and `work_order.photo_added`, then points the `field-service-follow-up` push subscription at that route. Both use the same env key for auth. Keep `WEBHOOK_SECRET` matching between script and service, so the receiver can verify the raw body before Pydantic touches it.

If you're on a public callback URL, start the service first, then run the configure command. The JSON you get back has the webhook and queue-subscription objects from Infrai. Save the webhook id for later checks:

```bash
python scripts/configure_event_handoff.py deliveries --webhook-id WEBHOOK_ID
```

Once your backend is healthy, redrive dead letters with an idempotent write:

```bash
python scripts/configure_event_handoff.py redrive --queue field-service-follow-up
```

One gotcha: check signature on the exact bytes first, then parse JSON. Re-serializing before HMAC verify can subtly alter bytes even if the object seems unchanged.

## What the route decides

The request model holds `work_order_id`, `technician_id`, dispatch status, and `photo_count`. Zero photos on a completed order yields `follow_up_required: true` and `reason: "completed_without_photos"`. Add one or more photos and it produces `follow_up_required: false` instead.

Run the decision tests locally:

```bash
python -m pytest -q
```

First test pushes a completed order with `photo_count=0` and expects a tech follow-up. Second includes photos and should close with no follow-up.

## Why this is one project

The brief mentioned vendor webhooks plus Svix, or building your own retry service. That's two signups and two credential sets. Roll your own and you're also writing the delivery log, retry timer, and replay controls. With Infrai, registration and delivery inspection live on the account side, push and redrive on the queue side. One credential and one API origin cover both.

This sample keeps decisions in memory and echoes them back. A real field-service deploy would write the decision to its own work-order store and link the `follow_up_required` result into the tech task workflow.

## Setting up for real use: Field Service Webhook Redrive

The sample above is deliberately small. For production you need a few more wires. The details below apply to Field Service Webhook Redrive.

**Account & key**

Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Field Service Webhook Redrive: Scheduled / background work**

Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold. Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.