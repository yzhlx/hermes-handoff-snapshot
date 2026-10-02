from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy.orm import Session
from test_foundation import authenticated, system

from hermes_api.attachment_object_store import make_store
from hermes_api.attachment_repository import SQLAttachmentRepository
from hermes_api.attachment_service import AttachmentService
from hermes_api.attachment_validation import ProcessFileValidator
from hermes_api.settings import Settings


def png_bytes():
    image = Image.new("RGB", (8, 6), color=(120, 80, 40))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_private_image_upload_validation_and_safe_download(tmp_path, monkeypatch):
    old_app, url = system.__wrapped__(tmp_path, monkeypatch)
    old_app.state.engine.dispose()
    config = Settings(
        database_url=url, environment="test", attachment_local_root=str(tmp_path / "private")
    )
    from hermes_api.main import create_app

    app = create_app(config)
    client = authenticated(app)
    content = png_bytes()
    key = str(uuid4())
    initialized = client.post(
        "/api/v1/attachments/uploads",
        json={
            "operation_id": key,
            "filename": "../QA_TEST_图.png",
            "declared_mime": "image/png",
            "byte_size": len(content),
        },
        headers={"Idempotency-Key": key},
    )
    assert initialized.status_code == 201, initialized.text
    attachment = initialized.json()["data"]
    assert attachment["original_name"] == "QA_TEST_图.png"
    assert "storage_key" not in attachment
    attachment_id = attachment["id"]

    upload_key = str(uuid4())
    uploaded = client.put(
        f"/api/v1/attachments/{attachment_id}/content",
        content=content,
        headers={"Idempotency-Key": upload_key, "Content-Type": "image/png"},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["data"]["status"] == "uploaded"
    replay = client.put(
        f"/api/v1/attachments/{attachment_id}/content",
        content=content,
        headers={"Idempotency-Key": upload_key, "Content-Type": "image/png"},
    )
    assert replay.json()["data"] == uploaded.json()["data"]

    complete_key = str(uuid4())
    job = client.post(
        f"/api/v1/attachments/{attachment_id}/complete",
        json={"operation_id": complete_key},
        headers={"Idempotency-Key": complete_key},
    )
    assert job.status_code == 202, job.text
    assert job.json()["data"]["status"] == "queued"
    with Session(app.state.engine) as db:
        worker = AttachmentService(
            SQLAttachmentRepository(db, make_store(config), ProcessFileValidator())
        )
        assert worker.run_one()
    metadata = client.get(f"/api/v1/attachments/{attachment_id}").json()["data"]
    assert metadata["status"] == "ready"
    assert metadata["detected_mime"] == "image/png"
    original = client.get(f"/api/v1/attachments/{attachment_id}/content")
    assert original.status_code == 200
    assert original.headers["content-type"] == "application/octet-stream"
    assert original.headers["x-content-type-options"] == "nosniff"
    assert original.content == content


def test_attachment_upload_csrf_and_cross_account_404(tmp_path, monkeypatch):
    app, _ = system.__wrapped__(tmp_path, monkeypatch)
    alice = authenticated(app)
    bob = authenticated(app, "bob")
    key = str(uuid4())
    response = alice.post(
        "/api/v1/attachments/uploads",
        json={
            "operation_id": key,
            "filename": "QA_TEST.png",
            "declared_mime": "image/png",
            "byte_size": 10,
        },
        headers={"Idempotency-Key": key},
    )
    assert response.status_code == 201, response.text
    attachment_id = response.json()["data"]["id"]
    assert bob.get(f"/api/v1/attachments/{attachment_id}").status_code == 404
    alice.headers.pop("X-CSRF-Token")
    rejected = alice.post(
        f"/api/v1/attachments/{attachment_id}/complete", json={"operation_id": str(uuid4())}
    )
    assert rejected.status_code == 403


def test_local_private_store_refuses_overwrite_and_symlink(tmp_path):
    store = make_store(
        Settings(environment="test", attachment_local_root=str(tmp_path / "objects"))
    )
    store.put_stream("opaque-key", [b"first"], 10)
    try:
        store.put_stream("opaque-key", [b"second"], 10)
    except FileExistsError:
        pass
    else:
        raise AssertionError("immutable object key was overwritten")
    target = tmp_path / "outside"
    target.write_bytes(b"secret")
    link = tmp_path / "objects" / "linked"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("This Windows test account lacks the OS privilege to create symlink fixtures.")
    try:
        store.open("linked")
    except (FileNotFoundError, OSError):
        pass
    else:
        raise AssertionError("symlink object should not be read")
