from src.work_order_events import DispatchStatus, WorkOrderEvent, decide_follow_up


def test_completed_work_order_without_photos_needs_follow_up() -> None:
    event = WorkOrderEvent(
        event_id="evt-104",
        event_type="work_order.updated",
        work_order_id="wo-812",
        technician_id="tech-9",
        dispatch_status=DispatchStatus.COMPLETED,
        photo_count=0,
    )

    decision = decide_follow_up(event)

    assert decision.follow_up_required is True
    assert decision.reason == "completed_without_photos"
    assert decision.work_order_id == "wo-812"


def test_completed_work_order_with_photo_closes_cleanly() -> None:
    event = WorkOrderEvent(
        event_id="evt-105",
        event_type="work_order.photo_added",
        work_order_id="wo-812",
        technician_id="tech-9",
        dispatch_status=DispatchStatus.COMPLETED,
        photo_count=2,
    )

    decision = decide_follow_up(event)

    assert decision.follow_up_required is False
    assert decision.reason == "photo_record_complete"

