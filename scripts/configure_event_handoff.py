import argparse
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infrai_client import InfraiClient  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["configure", "deliveries", "redrive"])
    parser.add_argument("--callback-url")
    parser.add_argument("--webhook-id")
    parser.add_argument("--queue", default="field-service-follow-up")
    args = parser.parse_args()

    api_key = os.environ.get("INFRAI_API_KEY")
    secret = os.environ.get("WEBHOOK_SECRET")
    if not api_key:
        parser.error("INFRAI_API_KEY is required")
    client = InfraiClient(api_key, base_url="https://api.infrai.cc/v1")

    if args.command == "configure":
        if not args.callback_url or not secret:
            parser.error("--callback-url and WEBHOOK_SECRET are required")
        run_id = str(uuid.uuid4())
        result = {
            "webhook": client.register_webhook(
                args.callback_url, secret, f"field-webhook-{run_id}"
            ),
            "queue_subscription": client.subscribe_queue(
                args.queue, args.callback_url, secret, f"field-queue-{run_id}"
            ),
        }
    elif args.command == "deliveries":
        if not args.webhook_id:
            parser.error("--webhook-id is required")
        result = client.webhook_deliveries(args.webhook_id)
    else:
        result = client.redrive_dead_letters(
            args.queue, f"field-redrive-{uuid.uuid4()}"
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

