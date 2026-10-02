from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from argon2 import PasswordHasher
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_foundation import authenticated

from hermes_api.attachment_storage import AttachmentRow, ProblemAttachmentLinkRow
from hermes_api.cli import migrate
from hermes_api.main import create_app
from hermes_api.settings import Settings
from hermes_api.storage import ProblemRow, User


def _setup(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'problem-attachments.db'}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    migrate()
    app = create_app(Settings(database_url=url, environment="test"))
    with Session(app.state.engine) as db:
        for name in ("alice", "bob"):
            db.add(
                User(
                    id=name,
                    username=name,
                    password_hash=PasswordHasher().hash("QA_TEST_password"),
                    timezone="Asia/Shanghai",
                )
            )
        db.commit()
    return app


def _ready_attachment(app, owner="alice", mime="image/png", pages=1, status="ready"):
    attachment_id = str(uuid4())
    now = datetime.now(UTC)
    with Session(app.state.engine) as db:
        db.add(
            AttachmentRow(
                id=attachment_id,
                owner_id=owner,
                storage_key=f"test/{attachment_id}",
                original_name="QA_TEST_question.png"
                if mime != "application/pdf"
                else "QA_TEST_question.pdf",
                declared_mime=mime,
                detected_mime=mime,
                byte_size=32,
                declared_size=32,
                expected_sha256=None,
                sha256="a" * 64,
                page_count=pages,
                status=status,
                failure_code=None,
                version=1,
                created_at=now,
                updated_at=now,
                expires_at=now + timedelta(days=1),
            )
        )
        db.commit()
    return attachment_id


def _create_problem(client, *, statement="QA_TEST_text", links=None, key=None):
    key = key or str(uuid4())
    body = {"operation_id": key, "statement": statement}
    if links is not None:
        body["attachment_links"] = links
    return client.post("/api/v1/problems", json=body, headers={"Idempotency-Key": key})


def test_attachment_links_ready_owner_version_idempotency_and_question_invariant(
    tmp_path, monkeypatch
):
    app = _setup(tmp_path, monkeypatch)
    alice, bob = authenticated(app), authenticated(app, "bob")
    ready = _ready_attachment(app)
    pending = _ready_attachment(app, status="uploaded")
    bob_file = _ready_attachment(app, owner="bob")

    # A textless problem is valid only when its question attachment is ready, in-owner, and inserted atomically.
    original_key = str(uuid4())
    created = _create_problem(
        alice,
        statement=None,
        links=[{"attachment_id": ready, "role": "question"}],
        key=original_key,
    )
    assert created.status_code == 201, created.text
    problem = created.json()["data"]
    assert problem["statement"] is None and problem["version"] == 1
    assert len(problem["attachment_links"]) == 1
    link = problem["attachment_links"][0]
    assert link["attachment_id"] == ready and link["original_name"] == "QA_TEST_question.png"
    replay_body = {
        "operation_id": original_key,
        "statement": None,
        "attachment_links": [{"attachment_id": ready, "role": "question"}],
    }
    # The original operation key replays its exact response without duplicating the link.
    replay = alice.post(
        "/api/v1/problems", json=replay_body, headers={"Idempotency-Key": original_key}
    )
    assert replay.status_code == 201 and replay.json()["data"] == problem
    with Session(app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(ProblemAttachmentLinkRow)) == 1

    assert alice.get(f"/api/v1/problems/{problem['id']}/attachment-links").json()["data"] == {
        "items": [link],
        "problem_version": 1,
    }
    # Clearing text remains valid while a question attachment is linked.
    clear_key = str(uuid4())
    cleared = alice.patch(
        f"/api/v1/problems/{problem['id']}",
        json={"operation_id": clear_key, "statement": None},
        headers={"Idempotency-Key": clear_key, "If-Match": '"1"'},
    )
    assert cleared.status_code == 200 and cleared.json()["data"]["version"] == 2

    # Last question link cannot be removed; a different owner cannot access the problem or file.
    delete_key = str(uuid4())
    last_unlink = alice.request(
        "DELETE",
        f"/api/v1/problems/{problem['id']}/attachment-links/{link['link_id']}",
        json={"operation_id": delete_key},
        headers={"Idempotency-Key": delete_key, "If-Match": '"2"'},
    )
    assert last_unlink.status_code == 422
    assert bob.get(f"/api/v1/problems/{problem['id']}/attachment-links").status_code == 404

    # Pending and cross-owner files fail without partially creating a problem.
    for attachment_id, expected in ((pending, 409), (bob_file, 404)):
        response = _create_problem(
            alice, statement=None, links=[{"attachment_id": attachment_id, "role": "question"}]
        )
        assert response.status_code == expected, response.text
    with Session(app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(ProblemRow)) == 1
        assert db.scalar(select(func.count()).select_from(ProblemAttachmentLinkRow)) == 1


def test_attachment_link_version_gate_pages_duplicate_and_new_link_idempotency(
    tmp_path, monkeypatch
):
    app = _setup(tmp_path, monkeypatch)
    alice = authenticated(app)
    pdf = _ready_attachment(app, mime="application/pdf", pages=3)
    problem = _create_problem(alice).json()["data"]

    def link(body, version="1"):
        key = str(uuid4())
        return alice.post(
            f"/api/v1/problems/{problem['id']}/attachment-links",
            json={"operation_id": key, **body},
            headers={"Idempotency-Key": key, "If-Match": f'"{version}"'},
        )

    assert (
        link({"attachment_id": pdf, "role": "source", "page_start": 1, "page_end": 4}).status_code
        == 422
    )
    assert link({"attachment_id": pdf, "role": "source", "page_start": 2}).status_code == 422
    first = link({"attachment_id": pdf, "role": "question", "page_start": 1, "page_end": 2})
    assert first.status_code == 201, first.text
    assert first.json()["data"]["problem_version"] == 2
    missing_version_key = str(uuid4())
    missing_version = alice.post(
        f"/api/v1/problems/{problem['id']}/attachment-links",
        json={"operation_id": missing_version_key, "attachment_id": pdf, "role": "source"},
        headers={"Idempotency-Key": missing_version_key},
    )
    assert missing_version.status_code == 428
    stale = link({"attachment_id": pdf, "role": "source"}, version="1")
    assert stale.status_code == 409 and stale.json()["error"]["current_version"] == 2
    duplicate = link(
        {"attachment_id": pdf, "role": "question", "page_start": 1, "page_end": 2}, version="2"
    )
    assert duplicate.status_code == 409

    clear_key = str(uuid4())
    cleared = alice.patch(
        f"/api/v1/problems/{problem['id']}",
        json={"operation_id": clear_key, "statement": None},
        headers={"Idempotency-Key": clear_key, "If-Match": '"2"'},
    )
    assert cleared.status_code == 200
    delete_key = str(uuid4())
    removed = alice.request(
        "DELETE",
        f"/api/v1/problems/{problem['id']}/attachment-links/{first.json()['data']['link']['link_id']}",
        json={"operation_id": delete_key},
        headers={"Idempotency-Key": delete_key, "If-Match": '"3"'},
    )
    assert removed.status_code == 422


def test_concurrent_attachment_links_same_key_replay_and_distinct_keys_conflict(
    tmp_path, monkeypatch
):
    app = _setup(tmp_path, monkeypatch)
    one, two = authenticated(app), authenticated(app)
    image = _ready_attachment(app)
    problem = _create_problem(one).json()["data"]

    def submit(client, key, role, version="1"):
        return client.post(
            f"/api/v1/problems/{problem['id']}/attachment-links",
            json={"operation_id": key, "attachment_id": image, "role": role},
            headers={"Idempotency-Key": key, "If-Match": f'"{version}"'},
        )

    shared_key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        same_one, same_two = list(
            pool.map(lambda client: submit(client, shared_key, "question"), (one, two))
        )
    assert same_one.status_code == same_two.status_code == 201
    assert same_one.json()["data"] == same_two.json()["data"]
    with Session(app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(ProblemAttachmentLinkRow)) == 1

    # Two different writes against the same snapshot cannot both advance it.
    distinct_keys = (str(uuid4()), str(uuid4()))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda args: submit(args[0], args[1], "source", "2"),
                ((one, distinct_keys[0]), (two, distinct_keys[1])),
            )
        )
    assert sorted(response.status_code for response in results) == [201, 409]
