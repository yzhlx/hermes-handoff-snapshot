"""End-to-end attachment transfer, validation, preview, replay, and worker recovery."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from pypdf import PdfWriter
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from test_foundation import authenticated, system

from hermes_api.attachment_object_store import make_store
from hermes_api.attachment_repository import SQLAttachmentRepository
from hermes_api.attachment_service import AttachmentService
from hermes_api.attachment_storage import AttachmentJobRow, AttachmentRow
from hermes_api.attachment_validation import ProcessFileValidator
from hermes_api.main import create_app
from hermes_api.settings import Settings


def _setup(tmp_path, monkeypatch):
    initial, url = system.__wrapped__(tmp_path, monkeypatch)
    initial.state.engine.dispose()
    settings = Settings(
        database_url=url,
        environment="test",
        attachment_local_root=str(tmp_path / "private-objects"),
    )
    return create_app(settings), settings, url


def _png_bytes(size=(8, 6), color=(120, 80, 40)):
    image = Image.new("RGB", size, color=color)
    output = BytesIO()
    image.save(output, format="PNG", optimize=False)
    return output.getvalue()


def _image_bytes(image_format, size=(12, 9), color=(100, 130, 150)):
    image = Image.new("RGB", size, color=color)
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def _pdf_bytes(page2=(240, 120), pages=2, *, encrypted=False, active=False):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    for _ in range(1, pages):
        writer.add_blank_page(width=page2[0], height=page2[1])
    if active:
        writer.add_js("app.alert('QA_TEST_active')")
    if encrypted:
        writer.encrypt("QA_TEST_password")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _initialize(client, data, declared_mime, filename="QA_TEST_input"):
    key = str(uuid4())
    response = client.post(
        "/api/v1/attachments/uploads",
        json={
            "operation_id": key,
            "filename": filename,
            "declared_mime": declared_mime,
            "byte_size": len(data),
        },
        headers={"Idempotency-Key": key},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _upload(client, attachment_id, data, key=None, *, mime):
    key = key or str(uuid4())
    response = client.put(
        f"/api/v1/attachments/{attachment_id}/content",
        content=data,
        headers={"Idempotency-Key": key, "Content-Type": mime},
    )
    return response, key


def _complete(client, attachment_id, key=None):
    key = key or str(uuid4())
    response = client.post(
        f"/api/v1/attachments/{attachment_id}/complete",
        json={"operation_id": key},
        headers={"Idempotency-Key": key},
    )
    return response, key


def _worker_once(app, settings):
    with Session(app.state.engine) as db:
        worker = AttachmentService(
            SQLAttachmentRepository(db, make_store(settings), ProcessFileValidator())
        )
        return worker.run_one()


def _upload_and_validate(client, app, settings, data, mime):
    attachment = _initialize(client, data, mime)
    uploaded, _ = _upload(client, attachment["id"], data, mime=mime)
    assert uploaded.status_code == 200, uploaded.text
    job, _ = _complete(client, attachment["id"])
    assert job.status_code == 202, job.text
    assert _worker_once(app, settings)
    return attachment["id"], job.json()["data"]["id"]


@pytest.mark.parametrize(
    ("page2_size", "expected_preview_size"),
    [((240, 120), (480, 240)), ((180, 90), (360, 180)), ((612, 792), (1224, 1584))],
)
def test_pdf_upload_page_two_preview_original_hash_and_restart(
    tmp_path, monkeypatch, page2_size, expected_preview_size
):
    app, settings, url = _setup(tmp_path, monkeypatch)
    client = authenticated(app)
    original_bytes = _pdf_bytes(page2=page2_size)
    attachment_id, validation_job_id = _upload_and_validate(
        client, app, settings, original_bytes, "application/pdf"
    )
    metadata = client.get(f"/api/v1/attachments/{attachment_id}").json()["data"]
    assert metadata["status"] == "ready" and metadata["page_count"] == 2
    assert metadata["sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert client.get(f"/api/v1/jobs/{validation_job_id}").json()["data"]["status"] == "succeeded"

    preview_key = str(uuid4())
    preview_job = client.post(
        f"/api/v1/attachments/{attachment_id}/jobs",
        json={"operation_id": preview_key, "kind": "preview", "page": 2},
        headers={"Idempotency-Key": preview_key},
    )
    assert preview_job.status_code == 202, preview_job.text

    # Simulate process restart against the same isolated DB and private object directory.
    old_engine = app.state.engine
    old_engine.dispose()
    app = create_app(
        Settings(
            database_url=url,
            environment="test",
            attachment_local_root=settings.attachment_local_root,
        )
    )
    client = authenticated(app)
    assert _worker_once(app, settings)

    saved = client.get(f"/api/v1/attachments/{attachment_id}").json()["data"]
    assert (
        saved["status"] == "ready" and saved["sha256"] == hashlib.sha256(original_bytes).hexdigest()
    )
    original = client.get(f"/api/v1/attachments/{attachment_id}/content")
    assert original.status_code == 200 and original.content == original_bytes
    assert original.headers["content-type"] == "application/octet-stream"
    assert original.headers["x-content-type-options"] == "nosniff"
    preview = client.get(f"/api/v1/attachments/{attachment_id}/preview?page=2")
    assert preview.status_code == 200 and preview.headers["content-type"] == "image/png"
    with Image.open(BytesIO(preview.content)) as rendered:
        assert rendered.size == expected_preview_size
        assert rendered.format == "PNG"
    bob = authenticated(app, "bob")
    assert bob.get(f"/api/v1/attachments/{attachment_id}").status_code == 404
    assert bob.get(f"/api/v1/attachments/{attachment_id}/content").status_code == 404
    assert bob.get(f"/api/v1/attachments/{attachment_id}/preview?page=2").status_code == 404


def _invalid_payload(case):
    if case == "encrypted_pdf":
        return "application/pdf", _pdf_bytes(encrypted=True), "PDF_ENCRYPTED"
    if case == "active_pdf_script":
        return "application/pdf", _pdf_bytes(active=True), "PDF_ACTIVE_CONTENT"
    if case == "truncated_pdf":
        return "application/pdf", _pdf_bytes()[:-35], "FILE_TYPE_MISMATCH"
    if case == "malformed_pdf_with_eof":
        return "application/pdf", b"%PDF-1.7\nnot a valid object\n%%EOF", "PDF_INVALID"
    if case == "pdf_claimed_as_png":
        return "image/png", _pdf_bytes(), "IMAGE_INVALID"
    if case == "png_claimed_as_pdf":
        return "application/pdf", _png_bytes(), "FILE_TYPE_MISMATCH"
    if case == "truncated_png":
        return "image/png", _png_bytes()[:-12], "IMAGE_INVALID"
    raise AssertionError(case)


@pytest.mark.parametrize(
    ("image_format", "mime"),
    [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")],
)
def test_supported_image_formats_validate_and_preview_as_safe_png(
    tmp_path, monkeypatch, image_format, mime
):
    app, settings, _ = _setup(tmp_path, monkeypatch)
    client = authenticated(app)
    content = _image_bytes(image_format)
    attachment_id, _ = _upload_and_validate(client, app, settings, content, mime)
    metadata = client.get(f"/api/v1/attachments/{attachment_id}").json()["data"]
    assert metadata["status"] == "ready" and metadata["detected_mime"] == mime
    preview_key = str(uuid4())
    queued = client.post(
        f"/api/v1/attachments/{attachment_id}/jobs",
        json={"operation_id": preview_key, "kind": "preview", "page": 1},
        headers={"Idempotency-Key": preview_key},
    )
    assert queued.status_code == 202
    assert _worker_once(app, settings)
    preview = client.get(f"/api/v1/attachments/{attachment_id}/preview?page=1")
    assert preview.status_code == 200 and preview.headers["content-type"] == "image/png"
    with Image.open(BytesIO(preview.content)) as image:
        assert image.format == "PNG" and image.size == (12, 9)


@pytest.mark.parametrize(
    "case",
    [
        "encrypted_pdf",
        "active_pdf_script",
        "truncated_pdf",
        "malformed_pdf_with_eof",
        "pdf_claimed_as_png",
        "png_claimed_as_pdf",
        "truncated_png",
    ],
)
def test_untrusted_file_bytes_fail_validation_and_never_become_ready(tmp_path, monkeypatch, case):
    app, settings, _ = _setup(tmp_path, monkeypatch)
    client = authenticated(app)
    mime, data, expected_error = _invalid_payload(case)
    attachment_id = _initialize(client, data, mime)["id"]
    uploaded, _ = _upload(client, attachment_id, data, mime=mime)
    assert uploaded.status_code == 200, uploaded.text
    queued, _ = _complete(client, attachment_id)
    assert queued.status_code == 202, queued.text
    job_id = queued.json()["data"]["id"]
    assert _worker_once(app, settings)
    job = client.get(f"/api/v1/jobs/{job_id}").json()["data"]
    metadata = client.get(f"/api/v1/attachments/{attachment_id}").json()["data"]
    assert job["status"] == "failed" and job["error_code"] == expected_error
    assert metadata["status"] == "rejected" and metadata["failure_code"] == expected_error
    assert client.get(f"/api/v1/attachments/{attachment_id}/content").status_code == 409
    key = str(uuid4())
    assert (
        client.post(
            f"/api/v1/attachments/{attachment_id}/jobs",
            json={"operation_id": key, "kind": "preview", "page": 1},
            headers={"Idempotency-Key": key},
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    ("scenario", "same_key", "changed_payload", "expected_statuses"),
    [
        ("same-key-identical-body", True, False, (200, 200)),
        ("same-key-different-body", True, True, (200, 409)),
        ("different-key-same-body", False, False, (200, 409)),
    ],
)
def test_upload_replay_variants_preserve_the_first_immutable_original(
    tmp_path, monkeypatch, scenario, same_key, changed_payload, expected_statuses
):
    app, settings, _ = _setup(tmp_path, monkeypatch)
    client = authenticated(app)
    first_data = _png_bytes()
    second_data = _png_bytes(color=(20, 40, 60)) if changed_payload else first_data
    assert len(first_data) == len(second_data)
    attachment_id = _initialize(client, first_data, "image/png")["id"]
    key = str(uuid4())
    first, _ = _upload(client, attachment_id, first_data, key, mime="image/png")
    assert first.status_code == expected_statuses[0], first.text
    second, _ = _upload(
        client,
        attachment_id,
        second_data,
        key if same_key else str(uuid4()),
        mime="image/png",
    )
    assert second.status_code == expected_statuses[1], f"{scenario}: {second.text}"
    if expected_statuses[1] == 200:
        assert second.json()["data"] == first.json()["data"]
    if second.status_code == 409:
        if same_key:
            assert second.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
        else:
            assert second.json()["error"]["code"] in {
                "UPLOAD_NOT_AVAILABLE",
                "UPLOAD_ALREADY_RECEIVED",
            }
    with Session(app.state.engine) as db:
        row = db.get(AttachmentRow, attachment_id)
        assert row.status == "uploaded" and row.sha256 == hashlib.sha256(first_data).hexdigest()
        storage_key = row.storage_key
        assert len(list(Path(settings.attachment_local_root).iterdir())) == 1
    downloaded, _ = _upload(client, attachment_id, first_data, key, mime="image/png")
    assert downloaded.status_code == 200
    original = client.get(f"/api/v1/attachments/{attachment_id}/content")
    # Content remains gated until validation; object bytes are checked directly meanwhile.
    assert original.status_code == 409
    with open(Path(settings.attachment_local_root) / storage_key, "rb") as stored:
        assert stored.read() == first_data


def test_concurrent_upload_same_key_returns_one_object_and_same_response(tmp_path, monkeypatch):
    app, settings, _ = _setup(tmp_path, monkeypatch)
    one, two = authenticated(app), authenticated(app)
    data = _png_bytes(color=(11, 22, 33))
    attachment_id = _initialize(one, data, "image/png")["id"]
    key = str(uuid4())

    def send(client):
        return _upload(client, attachment_id, data, key, mime="image/png")[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send, (one, two)))
    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json()["data"] == responses[1].json()["data"]
    assert len(list(Path(settings.attachment_local_root).iterdir())) == 1
    with Session(app.state.engine) as db:
        row = db.get(AttachmentRow, attachment_id)
        assert row.status == "uploaded" and row.sha256 == hashlib.sha256(data).hexdigest()
        stored_key = row.storage_key
    with open(Path(settings.attachment_local_root) / stored_key, "rb") as stored:
        assert stored.read() == data


def test_concurrent_upload_different_keys_has_one_winner_and_preserves_original(
    tmp_path, monkeypatch
):
    app, settings, _ = _setup(tmp_path, monkeypatch)
    one, two = authenticated(app), authenticated(app)
    original_data = _png_bytes(color=(10, 20, 30))
    changed_data = _png_bytes(color=(80, 90, 100))
    assert len(original_data) == len(changed_data)
    attachment_id = _initialize(one, original_data, "image/png")["id"]

    def send(args):
        client, key, data = args
        return _upload(client, attachment_id, data, key, mime="image/png")[0]

    args = ((one, str(uuid4()), original_data), (two, str(uuid4()), changed_data))
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send, args))
    assert sorted(response.status_code for response in responses) == [200, 409]
    with Session(app.state.engine) as db:
        row = db.get(AttachmentRow, attachment_id)
        assert row.status == "uploaded"
        winner = (
            original_data
            if row.sha256 == hashlib.sha256(original_data).hexdigest()
            else changed_data
        )
        assert row.sha256 == hashlib.sha256(winner).hexdigest()
        assert len(list(Path(settings.attachment_local_root).iterdir())) == 1
        storage_key = row.storage_key
    with open(Path(settings.attachment_local_root) / storage_key, "rb") as stored:
        assert stored.read() == winner


def test_complete_key_replay_and_cross_attachment_reuse_add_no_validation_jobs(
    tmp_path, monkeypatch
):
    app, settings, _ = _setup(tmp_path, monkeypatch)
    client = authenticated(app)
    data = _png_bytes()
    first_id = _initialize(client, data, "image/png")["id"]
    second_id = _initialize(client, data, "image/png")["id"]
    for attachment_id in (first_id, second_id):
        uploaded, _ = _upload(client, attachment_id, data, mime="image/png")
        assert uploaded.status_code == 200
    first, key = _complete(client, first_id)
    assert first.status_code == 202
    replay, _ = _complete(client, first_id, key)
    assert replay.status_code == 202 and replay.json()["data"] == first.json()["data"]
    conflicting, _ = _complete(client, second_id, key)
    assert conflicting.status_code == 409
    with Session(app.state.engine) as db:
        count = db.scalar(
            select(func.count())
            .select_from(AttachmentJobRow)
            .where(AttachmentJobRow.kind == "validate")
        )
        assert count == 1
    assert _worker_once(app, settings)


@pytest.mark.parametrize("replay_change", ["different-page", "different-attachment"])
def test_preview_key_replay_with_changed_request_is_409_without_more_jobs(
    tmp_path, monkeypatch, replay_change
):
    app, settings, _ = _setup(tmp_path, monkeypatch)
    client = authenticated(app)
    data = _pdf_bytes(page2=(120, 80), pages=3)
    first_id, _ = _upload_and_validate(client, app, settings, data, "application/pdf")
    second_id = None
    if replay_change == "different-attachment":
        second_id, _ = _upload_and_validate(client, app, settings, data, "application/pdf")
    key = str(uuid4())
    first = client.post(
        f"/api/v1/attachments/{first_id}/jobs",
        json={"operation_id": key, "kind": "preview", "page": 2},
        headers={"Idempotency-Key": key},
    )
    assert first.status_code == 202
    replay = client.post(
        f"/api/v1/attachments/{first_id}/jobs",
        json={"operation_id": key, "kind": "preview", "page": 2},
        headers={"Idempotency-Key": key},
    )
    assert replay.status_code == 202 and replay.json()["data"] == first.json()["data"]
    target = first_id if replay_change == "different-page" else second_id
    changed_page = 1 if replay_change == "different-page" else 2
    conflict = client.post(
        f"/api/v1/attachments/{target}/jobs",
        json={"operation_id": key, "kind": "preview", "page": changed_page},
        headers={"Idempotency-Key": key},
    )
    assert conflict.status_code == 409
    with Session(app.state.engine) as db:
        count = db.scalar(
            select(func.count())
            .select_from(AttachmentJobRow)
            .where(AttachmentJobRow.kind == "preview")
        )
        assert count == 1


@pytest.mark.parametrize(
    ("page", "error_code"), [(0, "VALIDATION_ERROR"), (3, "PAGE_OUT_OF_RANGE")]
)
def test_preview_out_of_range_pages_do_not_create_jobs(tmp_path, monkeypatch, page, error_code):
    app, settings, _ = _setup(tmp_path, monkeypatch)
    client = authenticated(app)
    attachment_id, _ = _upload_and_validate(
        client, app, settings, _pdf_bytes(pages=2), "application/pdf"
    )
    key = str(uuid4())
    invalid = client.post(
        f"/api/v1/attachments/{attachment_id}/jobs",
        json={"operation_id": key, "kind": "preview", "page": page},
        headers={"Idempotency-Key": key},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == error_code
    with Session(app.state.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(AttachmentJobRow)
                .where(AttachmentJobRow.kind == "preview")
            )
            == 0
        )


def test_expired_running_validation_lease_recovers_after_process_restart(tmp_path, monkeypatch):
    app, settings, url = _setup(tmp_path, monkeypatch)
    client = authenticated(app)
    data = _png_bytes()
    attachment_id, _ = _upload_and_validate(client, app, settings, data, "image/png")
    # Keep a separate pending validation job to model a worker killed after taking its lease.
    pending_id = _initialize(client, data, "image/png")["id"]
    uploaded, _ = _upload(client, pending_id, data, mime="image/png")
    assert uploaded.status_code == 200
    queued, _ = _complete(client, pending_id)
    assert queued.status_code == 202
    stale_time = datetime.now(UTC) - timedelta(minutes=6)
    with Session(app.state.engine) as db:
        db.execute(
            update(AttachmentJobRow)
            .where(AttachmentJobRow.id == queued.json()["data"]["id"])
            .values(status="running", locked_at=stale_time, attempt_count=1)
        )
        job = db.get(AttachmentJobRow, queued.json()["data"]["id"])
        job_id = job.id
        db.commit()
    app.state.engine.dispose()
    restarted = create_app(
        Settings(
            database_url=url,
            environment="test",
            attachment_local_root=settings.attachment_local_root,
        )
    )
    assert _worker_once(restarted, settings)
    metadata = authenticated(restarted).get(f"/api/v1/attachments/{pending_id}").json()["data"]
    assert metadata["status"] == "ready"
    with Session(restarted.state.engine) as db:
        recovered = db.get(AttachmentJobRow, job_id)
        assert recovered.status == "succeeded" and recovered.attempt_count == 2
    assert (
        authenticated(restarted)
        .get(f"/api/v1/attachments/{attachment_id}")
        .json()["data"]["status"]
        == "ready"
    )
