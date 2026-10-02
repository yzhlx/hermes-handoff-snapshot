"""A worker that lost its lease must never publish an obsolete parser result."""

from sqlalchemy import update
from sqlalchemy.orm import Session
from test_attachment_workflows_review import _complete, _initialize, _png_bytes, _setup, _upload
from test_foundation import authenticated

from hermes_api.attachment_object_store import make_store
from hermes_api.attachment_repository import SQLAttachmentRepository
from hermes_api.attachment_storage import AttachmentJobRow, AttachmentRow
from hermes_api.attachment_validation import ProcessFileValidator


def test_replaced_worker_lease_does_not_commit_old_validation_result(tmp_path, monkeypatch):
    app, config, _ = _setup(tmp_path, monkeypatch)
    client = authenticated(app)
    content = _png_bytes()
    attachment_id = _initialize(client, content, "image/png")["id"]
    uploaded, _ = _upload(client, attachment_id, content, mime="image/png")
    assert uploaded.status_code == 200
    completed, _ = _complete(client, attachment_id)
    job_id = completed.json()["data"]["id"]

    class LeaseReplacedValidator:
        def inspect(self, path, declared_mime):
            result = ProcessFileValidator().inspect(path, declared_mime)
            # Model a replacement worker taking the persisted lease while decoding ran.
            with Session(app.state.engine) as replacement:
                replacement.execute(
                    update(AttachmentJobRow)
                    .where(AttachmentJobRow.id == job_id)
                    .values(lease_token="QA_TEST_replacement_worker")
                )
                replacement.commit()
            return result

    with Session(app.state.engine) as db:
        assert SQLAttachmentRepository(db, make_store(config), LeaseReplacedValidator()).run_one()
    with Session(app.state.engine) as db:
        job = db.get(AttachmentJobRow, job_id)
        assert job.lease_token == "QA_TEST_replacement_worker"
        assert job.status == "running" and job.result_json is None
        attachment = db.get(AttachmentRow, attachment_id)
        assert attachment.status == "validating" and attachment.version == 2
    assert client.get(f"/api/v1/attachments/{attachment_id}/content").status_code == 409


def test_input_changed_during_validation_discards_obsolete_result(tmp_path, monkeypatch):
    app, config, _ = _setup(tmp_path, monkeypatch)
    client = authenticated(app)
    content = _png_bytes()
    attachment_id = _initialize(client, content, "image/png")["id"]
    assert _upload(client, attachment_id, content, mime="image/png")[0].status_code == 200
    completed, _ = _complete(client, attachment_id)
    job_id = completed.json()["data"]["id"]

    class InputChangedValidator:
        def inspect(self, path, declared_mime):
            result = ProcessFileValidator().inspect(path, declared_mime)
            with Session(app.state.engine) as replacement:
                replacement.execute(
                    update(AttachmentRow)
                    .where(AttachmentRow.id == attachment_id)
                    .values(version=3, status="rejected", failure_code="QA_TEST_CHANGED")
                )
                replacement.commit()
            return result

    with Session(app.state.engine) as db:
        assert SQLAttachmentRepository(db, make_store(config), InputChangedValidator()).run_one()
    with Session(app.state.engine) as db:
        job = db.get(AttachmentJobRow, job_id)
        attachment = db.get(AttachmentRow, attachment_id)
        assert job.status == "failed" and job.error_code == "STALE_INPUT"
        assert job.result_json is None
        assert attachment.status == "rejected" and attachment.version == 3
        assert attachment.failure_code == "QA_TEST_CHANGED"


def test_missing_ready_object_returns_stable_error_without_internal_path(tmp_path, monkeypatch):
    app, config, _ = _setup(tmp_path, monkeypatch)
    client = authenticated(app)
    content = _png_bytes()
    attachment_id = _initialize(client, content, "image/png")["id"]
    assert _upload(client, attachment_id, content, mime="image/png")[0].status_code == 200
    _complete(client, attachment_id)
    store = make_store(config)
    with Session(app.state.engine) as db:
        assert SQLAttachmentRepository(db, store, ProcessFileValidator()).run_one()
        key = db.get(AttachmentRow, attachment_id).storage_key
    store.delete(key)
    response = client.get(f"/api/v1/attachments/{attachment_id}/content")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "OBJECT_UNAVAILABLE"
    assert key not in response.text and str(tmp_path) not in response.text
