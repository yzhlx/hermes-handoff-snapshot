"""Authenticated API checks for correcting implausible timer spans (03 §3, FR-026/049)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

pytest_plugins = ("test_foundation",)

from test_foundation import authenticated

from hermes_api.storage import SessionRow, SessionTimeSegmentRow

T0 = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)  # 20:00 in Shanghai
OVERNIGHT_END = T0 + timedelta(hours=9)


def _ended_session_with_overnight_span(app, owner="alice"):
    """A closed session whose single span ran overnight and is far too long."""
    segment_id = str(uuid4())
    session_id = str(uuid4())
    with Session(app.state.engine) as db:
        db.add(
            SessionRow(
                id=session_id,
                owner_id=owner,
                goal="QA_TEST 隔夜计时",
                subject_id=None,
                knowledge_point_id=None,
                status="ended",
                version=1,
                started_at=T0,
                ended_at=OVERNIGHT_END,
                day_timezone="Asia/Shanghai",
                learning_date="2026-09-30",
                timing_enabled=True,
                method_id=None,
                kind="reading",
                previous_session_id=None,
                resume_note=None,
            )
        )
        db.flush()
        db.add(
            SessionTimeSegmentRow(
                id=segment_id,
                owner_id=owner,
                session_id=session_id,
                started_at=T0,
                ended_at=OVERNIGHT_END,
            )
        )
        db.commit()
    return session_id, segment_id


def _correct(client, session_id, segment_id, body, version):
    key = body["operation_id"]
    return client.patch(
        f"/api/v1/learning-sessions/{session_id}/time-segments/{segment_id}",
        json=body,
        headers={"Idempotency-Key": key, "If-Match": f'"{version}"'},
    )


def test_an_overnight_span_is_surfaced_and_not_silently_counted(system):
    app, _ = system
    client = authenticated(app)
    session_id, segment_id = _ended_session_with_overnight_span(app)

    response = client.get(f"/api/v1/learning-sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["timing_review_required"] is True
    segment = data["time_segments"][0]
    assert segment["id"] == segment_id
    assert "excessive_span" in segment["anomalies"]
    assert "crosses_local_day" in segment["anomalies"]
    assert segment["review_required"] is True
    assert segment["excluded"] is False
    # The raw count is still reported; it is flagged, not hidden.
    assert data["effective_duration_seconds"] == 9 * 3600


def test_shortening_a_span_is_recorded_with_the_original_end(system):
    app, _ = system
    client = authenticated(app)
    session_id, segment_id = _ended_session_with_overnight_span(app)

    shorter = T0 + timedelta(minutes=30)
    response = _correct(
        client,
        session_id,
        segment_id,
        {
            "operation_id": str(uuid4()),
            "ended_at": shorter.isoformat(),
            "correction_note": "QA_TEST 中途睡着了",
        },
        1,
    )
    assert response.status_code == 200, response.json()
    data = response.json()["data"]
    assert data["version"] == 2  # the correction advances the session version
    segment = data["time_segments"][0]
    assert segment["duration_seconds"] == 1800
    assert segment["original_ended_at"] == OVERNIGHT_END.isoformat()
    assert segment["correction_note"] == "QA_TEST 中途睡着了"
    assert segment["anomalies"] == []
    assert data["timing_review_required"] is False
    assert data["effective_duration_seconds"] == 1800


def test_excluding_a_span_removes_it_from_the_counted_duration(system):
    app, _ = system
    client = authenticated(app)
    session_id, segment_id = _ended_session_with_overnight_span(app)

    response = _correct(
        client,
        session_id,
        segment_id,
        {"operation_id": str(uuid4()), "exclude": True, "correction_note": "QA_TEST 忘记停止计时"},
        1,
    )
    assert response.status_code == 200, response.json()
    data = response.json()["data"]
    segment = data["time_segments"][0]
    assert segment["excluded"] is True
    assert segment["duration_seconds"] == 0
    assert data["effective_duration_seconds"] == 0
    # An excluded span no longer asks for review.
    assert data["timing_review_required"] is False

    restored = _correct(
        client,
        session_id,
        segment_id,
        {"operation_id": str(uuid4()), "exclude": False},
        2,
    )
    assert restored.status_code == 200
    restored_data = restored.json()["data"]
    assert restored_data["time_segments"][0]["excluded"] is False
    assert restored_data["effective_duration_seconds"] == 9 * 3600
    assert restored_data["timing_review_required"] is True


def test_corrections_require_if_match_and_report_conflicts(system):
    app, _ = system
    client = authenticated(app)
    session_id, segment_id = _ended_session_with_overnight_span(app)

    key = str(uuid4())
    missing = client.patch(
        f"/api/v1/learning-sessions/{session_id}/time-segments/{segment_id}",
        json={"operation_id": key, "exclude": True},
        headers={"Idempotency-Key": key},
    )
    assert missing.status_code == 428

    key = str(uuid4())
    stale = client.patch(
        f"/api/v1/learning-sessions/{session_id}/time-segments/{segment_id}",
        json={"operation_id": key, "exclude": True},
        headers={"Idempotency-Key": key, "If-Match": '"9"'},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["current_version"] == 1


def test_a_correction_cannot_extend_a_span_or_run_into_the_future(system):
    app, _ = system
    client = authenticated(app)
    session_id, segment_id = _ended_session_with_overnight_span(app)

    for label, proposed in (
        ("extends the span", (OVERNIGHT_END + timedelta(seconds=1)).isoformat()),
        ("ends before it started", (T0 - timedelta(seconds=1)).isoformat()),
    ):
        key = str(uuid4())
        response = _correct(
            client,
            session_id,
            segment_id,
            {"operation_id": key, "ended_at": proposed},
            1,
        )
        assert response.status_code == 422, (label, response.json())


def test_an_open_span_has_no_end_to_correct(system):
    app, _ = system
    client = authenticated(app)
    key = str(uuid4())
    created = client.post(
        "/api/v1/learning-sessions",
        json={"operation_id": key, "kind": "reading", "timing_enabled": True},
        headers={"Idempotency-Key": key},
    )
    assert created.status_code == 201
    session = created.json()["data"]
    segment_id = session["time_segments"][0]["id"]

    key = str(uuid4())
    response = _correct(
        client,
        session["id"],
        segment_id,
        {"operation_id": key, "ended_at": datetime.now(UTC).isoformat()},
        session["version"],
    )
    assert response.status_code == 422, response.json()
    # Excluding the running span is still allowed and honest.
    key = str(uuid4())
    excluded = _correct(
        client,
        session["id"],
        segment_id,
        {"operation_id": key, "exclude": True},
        session["version"],
    )
    assert excluded.status_code == 200
    assert excluded.json()["data"]["time_segments"][0]["excluded"] is True


def test_correction_is_idempotent_and_owner_isolated(system):
    app, _ = system
    client = authenticated(app)
    session_id, segment_id = _ended_session_with_overnight_span(app)

    key = str(uuid4())
    body = {"operation_id": key, "exclude": True}
    first = _correct(client, session_id, segment_id, body, 1)
    second = _correct(client, session_id, segment_id, body, 1)
    assert first.status_code == 200 and second.status_code == 200
    assert second.json()["data"]["version"] == first.json()["data"]["version"]

    mismatch = client.patch(
        f"/api/v1/learning-sessions/{session_id}/time-segments/{segment_id}",
        json={"operation_id": key, "exclude": True},
        headers={"Idempotency-Key": str(uuid4()), "If-Match": '"2"'},
    )
    assert mismatch.status_code == 422

    bob = authenticated(app, "bob")
    key = str(uuid4())
    foreign = bob.patch(
        f"/api/v1/learning-sessions/{session_id}/time-segments/{segment_id}",
        json={"operation_id": key, "exclude": True},
        headers={"Idempotency-Key": key, "If-Match": '"1"'},
    )
    assert foreign.status_code == 404


def test_unknown_segment_and_empty_correction_are_rejected(system):
    app, _ = system
    client = authenticated(app)
    session_id, segment_id = _ended_session_with_overnight_span(app)

    key = str(uuid4())
    unknown = _correct(client, session_id, str(uuid4()), {"operation_id": key, "exclude": True}, 1)
    assert unknown.status_code == 404

    key = str(uuid4())
    empty = client.patch(
        f"/api/v1/learning-sessions/{session_id}/time-segments/{segment_id}",
        json={"operation_id": key},
        headers={"Idempotency-Key": key, "If-Match": '"1"'},
    )
    assert empty.status_code == 422


def test_a_plausible_session_is_not_flagged(system):
    app, _ = system
    client = authenticated(app)
    key = str(uuid4())
    created = client.post(
        "/api/v1/learning-sessions",
        json={"operation_id": key, "kind": "reading", "timing_enabled": True},
        headers={"Idempotency-Key": key},
    )
    assert created.status_code == 201
    data = created.json()["data"]
    assert data["timing_review_required"] is False
    assert data["time_segments"][0]["anomalies"] == []
    assert data["time_segments"][0]["review_required"] is False
