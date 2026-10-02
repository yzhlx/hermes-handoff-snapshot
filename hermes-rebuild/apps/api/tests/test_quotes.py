"""Daily quote contract tests on an isolated, migrated SQLite database."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hermes_api.cli import migrate
from hermes_api.domain import PolicyError
from hermes_api.quotes import create_quotes_router
from hermes_api.quotes_storage import (
    DailyQuoteRow,
    QuoteOperationRow,
    QuotePreferenceRow,
    QuoteQueueRow,
    QuoteRepository,
    QuoteRoundRow,
    QuoteRow,
)
from hermes_api.storage import Base, User, make_engine


@pytest.fixture
def quotes_system(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'quotes-isolated.db'}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)

    migrate()
    engine = make_engine(url)
    with Session(engine) as db:
        db.add_all(
            [
                User(
                    id="alice",
                    username="QA_TEST_alice",
                    password_hash="unused",
                    timezone="Asia/Shanghai",
                ),
                User(
                    id="bob",
                    username="QA_TEST_bob",
                    password_hash="unused",
                    timezone="Asia/Shanghai",
                ),
            ]
        )
        db.commit()

    clock = {"now": datetime(2026, 9, 30, 8, 0, tzinfo=UTC)}

    def now():
        return clock["now"]

    def deterministic_shuffle(items):
        items.reverse()

    app = FastAPI()

    @app.middleware("http")
    async def request_id(request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        return response

    @app.exception_handler(PolicyError)
    async def policy_error(request, error):
        return JSONResponse(
            {
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "request_id": request.state.request_id,
                    **(
                        {"current_version": error.current_version}
                        if hasattr(error, "current_version")
                        else {}
                    ),
                }
            },
            status_code=error.status,
        )

    def database():
        with Session(engine) as db:
            yield db

    def identity(db: Session = Depends(database)):  # noqa: B008
        return db.get(User, "alice"), SimpleNamespace(csrf="test")

    def authorized_write(auth=Depends(identity)):  # noqa: B008
        return auth

    app.include_router(
        create_quotes_router(
            database, identity, authorized_write, now=now, shuffle=deterministic_shuffle
        )
    )
    return app, engine, clock, now, deterministic_shuffle


def test_exact_catalog_is_seeded_without_fabricated_authors(quotes_system):
    _app, engine, *_ = quotes_system
    with Session(engine) as db:
        rows = list(db.scalars(select(QuoteRow).order_by(QuoteRow.id)))
    source = Path(__file__).resolve().parents[3] / "原始需求.md"
    specification = source.read_text(encoding="utf-8")
    section = specification.split("## 6.3 金句示例", maxsplit=1)[1].split("---", maxsplit=1)[0]
    exact_texts = [line[2:] for line in section.splitlines() if line.startswith("> ")]
    assert len(exact_texts) == 23
    assert [row.text for row in rows] == exact_texts
    assert all(row.author is None for row in rows)


def test_quote_orm_matches_the_migrated_schema(quotes_system):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    _app, engine, *_ = quotes_system
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    quote_tables = {
        "quotes",
        "quote_preferences",
        "quote_rounds",
        "quote_round_items",
        "daily_quotes",
        "quote_operations",
    }
    quote_differences = []
    for difference in differences:
        table = next((item.table.name for item in difference[1:] if hasattr(item, "table")), None)
        if table in quote_tables:
            quote_differences.append(difference)
    assert quote_differences == []


def test_same_day_refreshes_and_service_restart_reuse_one_assignment(quotes_system):
    app, engine, _clock, now, shuffle = quotes_system
    first_client = TestClient(app)
    first = first_client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]
    # A new repository/session reads the saved server assignment, not a client cache.
    with Session(engine) as db:
        second = QuoteRepository(db, now=now, shuffle=shuffle).today("alice", "Asia/Shanghai")[
            "daily_quote"
        ]
        db.commit()
    assert second == first
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(DailyQuoteRow)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(QuoteQueueRow)
                .where(QuoteQueueRow.consumed_at.is_not(None))
            )
            == 1
        )


def test_twenty_three_day_cycle_never_repeats_then_starts_next_round(quotes_system):
    app, engine, clock, _now, _shuffle = quotes_system
    client = TestClient(app)
    displayed = []
    for offset in range(23):
        clock["now"] = datetime(2026, 9, 30, 8, tzinfo=UTC) + timedelta(days=offset)
        result = client.get("/api/v1/quotes/today")
        assert result.status_code == 200
        displayed.append(result.json()["data"]["daily_quote"]["quote"]["id"])
    assert len(set(displayed)) == 23
    clock["now"] += timedelta(days=1)
    next_round = client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]
    assert next_round["quote"] is not None
    with Session(engine) as db:
        rounds = list(db.scalars(select(QuoteRoundRow).where(QuoteRoundRow.owner_id == "alice")))
        assert [row.round_number for row in rounds] == [1, 2]


def test_dislike_hides_current_day_without_allocating_a_replacement(quotes_system):
    app, engine, _clock, _now, _shuffle = quotes_system
    client = TestClient(app)
    today = client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]
    quote_id = today["quote"]["id"]
    key = str(uuid4())
    response = client.put(
        f"/api/v1/quotes/{quote_id}/preference",
        json={"favorited": True, "disliked": True},
        headers={"Idempotency-Key": key, "If-None-Match": "*"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["daily_quote"]["quote"] is None
    hidden = client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]
    assert hidden["quote"] is None and hidden["reason"] == "disliked_today"
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(DailyQuoteRow)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(QuoteQueueRow)
                .where(QuoteQueueRow.consumed_at.is_not(None))
            )
            == 1
        )
    library = client.get("/api/v1/quotes/favorites").json()["data"]
    assert library["items"][0]["disliked"] is True
    assert library["disliked"][0]["favorited"] is True


def test_undislike_restores_an_unconsumed_quote_to_the_current_round(quotes_system):
    app, _engine, clock, *_ = quotes_system
    client = TestClient(app)
    today = client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]
    assert today["quote"]["id"] == "q23"
    blocked = client.put(
        "/api/v1/quotes/q22/preference",
        json={"favorited": False, "disliked": True},
        headers={"Idempotency-Key": str(uuid4()), "If-None-Match": "*"},
    )
    assert blocked.status_code == 200
    restored = client.put(
        "/api/v1/quotes/q22/preference",
        json={"favorited": False, "disliked": False},
        headers={"Idempotency-Key": str(uuid4()), "If-Match": '"1"'},
    )
    assert restored.status_code == 200
    clock["now"] += timedelta(days=1)
    next_day = client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]
    assert next_day["quote"]["id"] == "q22"


def test_undislike_never_repeats_a_quote_already_consumed_this_round(quotes_system):
    app, _engine, clock, *_ = quotes_system
    client = TestClient(app)
    assert client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]["quote"]["id"] == "q23"
    client.put(
        "/api/v1/quotes/q23/preference",
        json={"favorited": False, "disliked": True},
        headers={"Idempotency-Key": str(uuid4()), "If-None-Match": "*"},
    )
    client.put(
        "/api/v1/quotes/q23/preference",
        json={"favorited": False, "disliked": False},
        headers={"Idempotency-Key": str(uuid4()), "If-Match": '"1"'},
    )
    next_22 = []
    for offset in range(1, 23):
        clock["now"] = datetime(2026, 9, 30, 8, tzinfo=UTC) + timedelta(days=offset)
        next_22.append(
            client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]["quote"]["id"]
        )
    assert "q23" not in next_22
    clock["now"] = datetime(2026, 9, 30, 8, tzinfo=UTC) + timedelta(days=23)
    assert client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]["quote"]["id"] == "q23"


def test_preference_if_match_idempotency_independence_and_owner_isolation(quotes_system):
    app, engine, _clock, _now, _shuffle = quotes_system
    client = TestClient(app)
    quote_id = "q01"
    key = str(uuid4())
    payload = {"favorited": True, "disliked": False}
    headers = {"Idempotency-Key": key, "If-None-Match": "*"}
    missing_initial_guard = client.put(
        f"/api/v1/quotes/{quote_id}/preference",
        json=payload,
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert missing_initial_guard.status_code == 428
    first = client.put(f"/api/v1/quotes/{quote_id}/preference", json=payload, headers=headers)
    assert first.status_code == 200
    replay = client.put(f"/api/v1/quotes/{quote_id}/preference", json=payload, headers=headers)
    assert replay.json()["data"] == first.json()["data"]
    assert (
        client.put(
            f"/api/v1/quotes/{quote_id}/preference",
            json={"favorited": False, "disliked": False},
            headers=headers,
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/v1/quotes/{quote_id}/preference",
            json=payload,
            headers={"Idempotency-Key": str(uuid4())},
        ).status_code
        == 428
    )
    assert (
        client.put(
            f"/api/v1/quotes/{quote_id}/preference",
            json=payload,
            headers={"Idempotency-Key": str(uuid4()), "If-Match": '"0"'},
        ).status_code
        == 409
    )
    changed = client.put(
        f"/api/v1/quotes/{quote_id}/preference",
        json={"favorited": False, "disliked": True},
        headers={"Idempotency-Key": str(uuid4()), "If-Match": '"1"'},
    )
    assert changed.status_code == 200 and changed.json()["data"]["preference"]["version"] == 2
    assert client.get("/api/v1/quotes/favorites").json()["data"]["items"] == []
    assert (
        client.get("/api/v1/quotes/favorites").json()["data"]["disliked"][0]["quote_id"] == quote_id
    )
    with Session(engine) as db:
        assert (
            db.scalar(
                select(QuotePreferenceRow).where(QuotePreferenceRow.owner_id == "alice")
            ).version
            == 2
        )
        assert (
            db.scalar(select(QuotePreferenceRow).where(QuotePreferenceRow.owner_id == "bob"))
            is None
        )
        db.add(
            QuoteOperationRow(
                id=str(uuid4()),
                owner_id="bob",
                quote_id=quote_id,
                key="QA_TEST_cross_owner",
                fingerprint="0" * 64,
                response="{}",
                created_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_all_quotes_disliked_returns_honest_empty_state(quotes_system):
    app, _engine, _clock, _now, _shuffle = quotes_system
    client = TestClient(app)
    with Session(quotes_system[1]) as db:
        ids = list(db.scalars(select(QuoteRow.id)))
    for quote_id in ids:
        response = client.put(
            f"/api/v1/quotes/{quote_id}/preference",
            json={"favorited": False, "disliked": True},
            headers={"Idempotency-Key": str(uuid4()), "If-None-Match": "*"},
        )
        assert response.status_code == 200
    daily = client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]
    assert daily["quote"] is None and daily["reason"] == "no_eligible_quotes"


def test_timezone_change_keeps_same_local_date_snapshot(quotes_system):
    app, engine, _clock, _now, _shuffle = quotes_system
    client = TestClient(app)
    first = client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]
    assert first["day_timezone"] == "Asia/Shanghai"
    with Session(engine) as db:
        db.execute(update(User).where(User.id == "alice").values(timezone="Asia/Tokyo"))
        db.commit()
    second = client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]
    assert second["local_date"] == first["local_date"]
    assert second["day_timezone"] == "Asia/Shanghai"
    assert second["quote"] == first["quote"]


def test_concurrent_first_access_consumes_only_one_queue_item(quotes_system):
    app, engine, _clock, _now, _shuffle = quotes_system
    clients = [TestClient(app), TestClient(app)]

    def fetch(client):
        return client.get("/api/v1/quotes/today").json()["data"]["daily_quote"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(fetch, clients))
    assert results[0] == results[1]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(DailyQuoteRow)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(QuoteQueueRow)
                .where(QuoteQueueRow.consumed_at.is_not(None))
            )
            == 1
        )
