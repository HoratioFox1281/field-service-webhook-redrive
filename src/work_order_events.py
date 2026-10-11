from enum import Enum

from pydantic import BaseModel, Field


class DispatchStatus(str, Enum):
    DISPATCHED = "dispatched"
    ON_SITE = "on_site"
    COMPLETED = "completed"


class WorkOrderEvent(BaseModel):
    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    work_order_id: str = Field(min_length=1)
    technician_id: str = Field(min_length=1)
    dispatch_status: DispatchStatus
    photo_count: int = Field(ge=0)


class FollowUpDecision(BaseModel):
    work_order_id: str
    dispatch_status: DispatchStatus
    photo_count: int
    follow_up_required: bool
    reason: str


def decide_follow_up(event: WorkOrderEvent) -> FollowUpDecision:
    missing_completion_photos = (
        event.dispatch_status == DispatchStatus.COMPLETED and event.photo_count == 0
    )
    return FollowUpDecision(
        work_order_id=event.work_order_id,
        dispatch_status=event.dispatch_status,
        photo_count=event.photo_count,
        follow_up_required=missing_completion_photos,
        reason=(
            "completed_without_photos"
            if missing_completion_photos
            else "photo_record_complete"
        ),
    )

