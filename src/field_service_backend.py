import hashlib
import hmac
import os

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .infrai_client import InfraiError
from .work_order_events import FollowUpDecision, WorkOrderEvent, decide_follow_up


app = FastAPI(title="Field-service event receiver")


def valid_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    supplied = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, supplied)


@app.post("/events/work-orders", response_model=FollowUpDecision)
async def receive_work_order_event(
    request: Request,
    x_infrai_signature: str = Header(alias="X-Infrai-Signature"),
) -> FollowUpDecision:
    body = await request.body()
    secret = os.environ.get("WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="WEBHOOK_SECRET is required")
    if not valid_signature(body, x_infrai_signature, secret):
        raise HTTPException(status_code=401, detail="invalid webhook signature")
    event = WorkOrderEvent.model_validate_json(body)
    return decide_follow_up(event)


@app.exception_handler(InfraiError)
async def handle_infrai_error(_request: Request, error: InfraiError) -> JSONResponse:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return JSONResponse(
        status_code=status,
        content={"error": {"code": error.code, "detail": error.detail}},
    )

