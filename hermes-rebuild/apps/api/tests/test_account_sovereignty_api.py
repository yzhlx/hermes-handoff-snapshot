"""Authenticated API checks for exports and the account deletion lifecycle (03 §9)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

pytest_plugins = ("test_foundation",)

from test_foundation import authenticated

from hermes_api.account_domain import CONFIRMATION_PHRASE
from hermes_api.account_storage import AccountDeletionRow, AccountExportRow
from hermes_api.storage import Base, ProblemRow, User


def _seed(app):
    now = datetime.now(UTC)
    with Session(app.state.engine) as db:
        for owner, pid, statement in (
            ("alice", "QA_TEST_alice_problem", "QA_TEST 左题题干"),
            ("bob", "QA_TEST_bob_problem", "QA_TEST 别人的题干"),
        ):
            db.add(
                ProblemRow(
                    id=pid,
                    owner_id=owner,
                    subject_id=None,
                    title="QA_TEST 题目",
                    statement=statement,
                    source_note=None,
                    correct_answer="QA_TEST 答案",
                    is_representative=False,
                    archived_at=None,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
            )
        db.commit()


def _write(client, method, path, body, version=None):
    headers = {"Idempotency-Key": body["operation_id"]}
    if version is not None:
        headers["If-Match"] = f'"{version}"'
    return client.request(method, f"/api/v1{path}", json=body, headers=headers)


def test_status_counts_only_the_callers_records(system):
    app, _ = system
    _seed(app)
    client = authenticated(app)
    response = client.get("/api/v1/account")
    assert response.status_code == 200, response.json()
    data = response.json()["data"]
    assert data["status"] == "active"
    assert data["username"] == "alice"
    assert data["record_count"] == 1
    assert data["deletion"] is None


def test_export_holds_only_own_records_and_no_secrets(system):
    app, _ = system
    _seed(app)
    client = authenticated(app)
    key = str(uuid4())
    created = _write(client, "POST", "/account/exports", {"operation_id": key})
    assert created.status_code == 201, created.json()
    export = created.json()["data"]
    assert export["status"] == "ready"
    assert export["byte_size"] > 0
    assert export["sha256"]
    assert export["record_counts"].get("problems") == 1

    download = client.get(f"/api/v1/account/exports/{export['id']}/download")
    assert download.status_code == 200, download.json()
    payload = download.json()["data"]
    document = payload["document"]
    assert document["format"] == "hermes-account-export/1"
    assert document["owner_id"] == "alice"
    ids = [row["id"] for row in document["tables"]["problems"]]
    assert ids == ["QA_TEST_alice_problem"]

    # The dictionary lists what left the service; secrets never appear.
    dictionary = document["data_dictionary"]
    assert "problems" in dictionary
    assert "password_hash" not in dictionary.get("users", [])
    flat = str(document)
    assert "password_hash" not in flat
    assert "object_key" not in flat
    assert "QA_TEST_bob_problem" not in flat

    raw = str(payload["document"])
    assert "token_hash" not in raw and "csrf" not in raw


def test_export_serialises_plain_dates(system):
    """A daily quote stores a plain `date`, not a timestamp.

    Found by the real browser run: opening the study room allocates today's
    quote, and the export then failed to serialise the date column.
    """
    app, _ = system
    client = authenticated(app)
    assert client.get("/api/v1/home").status_code == 200
    key = str(uuid4())
    created = _write(client, "POST", "/account/exports", {"operation_id": key})
    assert created.status_code == 201, created.json()
    download = client.get(f"/api/v1/account/exports/{created.json()['data']['id']}/download")
    assert download.status_code == 200, download.json()
    rows = download.json()["data"]["document"]["tables"].get("daily_quotes", [])
    assert rows, "the allocated daily quote should be exported"
    assert isinstance(rows[0]["local_date"], str)


def test_export_is_idempotent_and_expires(system):
    app, _ = system
    _seed(app)
    client = authenticated(app)
    key = str(uuid4())
    body = {"operation_id": key}
    first = _write(client, "POST", "/account/exports", body)
    second = _write(client, "POST", "/account/exports", body)
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]

    listing = client.get("/api/v1/account/exports")
    assert listing.status_code == 200
    assert len(listing.json()["data"]["items"]) == 1

    # Expiry is enforced on download, not merely displayed.
    with Session(app.state.engine) as db:
        row = db.get(AccountExportRow, first.json()["data"]["id"])
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    assert (
        client.get(f"/api/v1/account/exports/{first.json()['data']['id']}/download").status_code
        == 410
    )

    bob = authenticated(app, "bob")
    assert (
        bob.get(f"/api/v1/account/exports/{first.json()['data']['id']}/download").status_code == 404
    )


def test_deletion_requires_the_exact_phrase_and_only_one_pending_request(system):
    app, _ = system
    _seed(app)
    client = authenticated(app)
    key = str(uuid4())
    wrong = _write(
        client, "POST", "/account/deletion", {"operation_id": key, "confirmation": "delete"}
    )
    assert wrong.status_code == 422, wrong.json()

    key = str(uuid4())
    created = _write(
        client,
        "POST",
        "/account/deletion",
        {"operation_id": key, "confirmation": CONFIRMATION_PHRASE},
    )
    assert created.status_code == 201, created.json()
    deletion = created.json()["data"]
    assert deletion["status"] == "pending"
    assert deletion["impact"]["total_records"] == 1
    assert deletion["purge_after"] > deletion["created_at"]

    status = client.get("/api/v1/account").json()["data"]
    assert status["status"] == "deletion_pending"
    assert status["deletion"]["id"] == deletion["id"]

    key = str(uuid4())
    again = _write(
        client,
        "POST",
        "/account/deletion",
        {"operation_id": key, "confirmation": CONFIRMATION_PHRASE},
    )
    assert again.status_code == 409, again.json()


def test_pending_deletion_stops_new_writes_but_not_the_cancel(system):
    app, _ = system
    _seed(app)
    client = authenticated(app)
    key = str(uuid4())
    created = _write(
        client,
        "POST",
        "/account/deletion",
        {"operation_id": key, "confirmation": CONFIRMATION_PHRASE},
    )
    deletion = created.json()["data"]

    blocked_key = str(uuid4())
    blocked = _write(
        client, "POST", "/problems", {"operation_id": blocked_key, "statement": "QA_TEST 新题"}
    )
    assert blocked.status_code == 403, blocked.json()
    assert blocked.json()["error"]["code"] == "ACCOUNT_PENDING_DELETION"
    # Reading is still allowed while pending.
    assert client.get("/api/v1/account").status_code == 200

    cancel_key = str(uuid4())
    assert (
        client.post(
            "/api/v1/account/deletion/cancel",
            json={"operation_id": cancel_key},
            headers={"Idempotency-Key": cancel_key},
        ).status_code
        == 428
    )
    cancelled = _write(
        client,
        "POST",
        "/account/deletion/cancel",
        {"operation_id": cancel_key},
        version=deletion["version"],
    )
    assert cancelled.status_code == 200, cancelled.json()
    assert cancelled.json()["data"]["status"] == "cancelled"
    assert client.get("/api/v1/account").json()["data"]["status"] == "active"

    allowed_key = str(uuid4())
    allowed = _write(
        client, "POST", "/problems", {"operation_id": allowed_key, "statement": "QA_TEST 新题"}
    )
    assert allowed.status_code == 201, allowed.json()


def test_purge_removes_own_rows_keeps_a_tombstone_and_revokes_the_credential(system):
    app, _ = system
    _seed(app)
    client = authenticated(app)
    key = str(uuid4())
    created = _write(
        client,
        "POST",
        "/account/deletion",
        {"operation_id": key, "confirmation": CONFIRMATION_PHRASE},
    )
    deletion = created.json()["data"]

    wrong_key = str(uuid4())
    refused = _write(
        client,
        "POST",
        "/account/deletion/purge",
        {"operation_id": wrong_key, "confirmation": "yes"},
        version=deletion["version"],
    )
    assert refused.status_code == 422, refused.json()

    purge_key = str(uuid4())
    purged = _write(
        client,
        "POST",
        "/account/deletion/purge",
        {"operation_id": purge_key, "confirmation": CONFIRMATION_PHRASE},
        version=deletion["version"],
    )
    assert purged.status_code == 200, purged.json()
    assert purged.json()["data"]["status"] == "completed"

    with Session(app.state.engine) as db:
        for name in ("problems", "account_exports"):
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(Base.metadata.tables[name])
                    .where(Base.metadata.tables[name].c.owner_id == "alice")
                )
                == 0
            ), name
        # Bob is untouched.
        assert (
            db.scalar(
                select(func.count()).select_from(ProblemRow).where(ProblemRow.owner_id == "bob")
            )
            == 1
        )
        # A minimal tombstone survives.
        tombstone = db.scalar(
            select(AccountDeletionRow).where(AccountDeletionRow.owner_id == "alice")
        )
        assert tombstone is not None and tombstone.status == "completed"
        user = db.get(User, "alice")
        assert user.status == "deleted"
        assert user.username.startswith("deleted:")

    # The purged account can no longer authenticate or write.
    assert client.get("/api/v1/account").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "QA_TEST_password"}
        ).status_code
        == 401
    )
