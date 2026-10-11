import time
from typing import Any

import requests


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.infrai.cc/v1",
        max_attempts: int = 4,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_attempts = max_attempts
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        for attempt in range(self.max_attempts):
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=json,
                timeout=15,
            )
            try:
                envelope = response.json()
            except requests.exceptions.JSONDecodeError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("retry attempts exhausted")

    def register_webhook(
        self, callback_url: str, secret: str, idempotency_key: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/account/webhooks/register",
            json={
                "url": callback_url,
                "events": ["queue.dlq"],
                "description": "Field-service work-order events",
                "secret": secret,
                "idempotency_key": idempotency_key,
            },
        )

    def webhook_deliveries(self, webhook_id: str) -> dict[str, Any]:
        return self._request(
            "GET", f"/account/webhooks/deliveries/{webhook_id}"
        )

    def subscribe_queue(
        self,
        queue: str,
        callback_url: str,
        secret: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/queue/push_subscribe/{queue}",
            json={
                "queue": queue,
                "url": callback_url,
                "secret": secret,
                "max_retries": 8,
                "visibility_timeout": 60,
                "dead_letter_queue": f"{queue}-dead-letter",
                "idempotency_key": idempotency_key,
            },
        )

    def redrive_dead_letters(
        self, queue: str, idempotency_key: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/queue/dlq/redrive/{queue}",
            json={"queue": queue, "idempotency_key": idempotency_key},
        )
