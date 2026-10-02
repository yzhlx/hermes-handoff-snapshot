"""Attachment orchestration, persistence, quota, and worker job lifecycle."""

import hashlib
import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, or_, select, update

from .attachment_domain import job_data, metadata, safe_filename, supported_limit
from .attachment_storage import AttachmentJobRow, AttachmentRow
from .domain import PolicyError


def now():
    return datetime.now(UTC)


class SQLAttachmentRepository:
    def __init__(self, db, store, validator, max_pending=10):
        self.db, self.store, self.validator, self.max_pending = db, store, validator, max_pending

    def _lock_owner(self, owner):
        from .storage import User

        self.db.execute(update(User).where(User.id == owner).values(timezone=User.timezone))

    def _get(self, owner, attachment_id, refresh=False):
        statement = select(AttachmentRow).where(
            AttachmentRow.owner_id == owner, AttachmentRow.id == attachment_id
        )
        if refresh:
            statement = statement.execution_options(populate_existing=True)
        row = self.db.scalar(statement)
        if not row:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return row

    def initialize(self, owner, body, key):
        if not key or str(body["operation_id"]) != key:
            raise PolicyError(
                "IDEMPOTENCY_KEY_REQUIRED", "Use operation_id as Idempotency-Key.", 422
            )
        fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        from .storage import Operation

        self._lock_owner(owner)
        prior = self.db.scalar(
            select(Operation).where(
                Operation.owner_id == owner,
                Operation.operation == "attachment_upload_init",
                Operation.key == key,
            )
        )
        if prior:
            if prior.fingerprint != fingerprint:
                raise PolicyError("IDEMPOTENCY_KEY_REUSED", "Operation key was reused.", 409)
            self.db.commit()
            return json.loads(prior.response)
        mime, size = body["declared_mime"], body["byte_size"]
        limit = supported_limit(mime)
        if size < 1 or size > limit:
            raise PolicyError("UPLOAD_TOO_LARGE", "The file exceeds the allowed size.", 413)
        pending = (
            self.db.scalar(
                select(func.count())
                .select_from(AttachmentRow)
                .where(
                    AttachmentRow.owner_id == owner,
                    or_(
                        AttachmentRow.status == "validating",
                        (AttachmentRow.status.in_(["pending_upload", "uploaded"]))
                        & (AttachmentRow.expires_at > now()),
                    ),
                )
            )
            or 0
        )
        if pending >= self.max_pending:
            raise PolicyError(
                "ATTACHMENT_QUOTA_EXCEEDED", "Too many files are awaiting validation.", 429
            )
        if body.get("sha256") and (
            len(body["sha256"]) != 64
            or any(ch not in "0123456789abcdef" for ch in body["sha256"].lower())
        ):
            raise PolicyError("VALIDATION_ERROR", "SHA-256 must be 64 hexadecimal characters.", 422)
        from .attachment_object_store import new_storage_key

        row = AttachmentRow(
            id=str(uuid4()),
            owner_id=owner,
            storage_key=new_storage_key(),
            original_name=safe_filename(body["filename"]),
            declared_mime=mime,
            declared_size=size,
            expected_sha256=body.get("sha256"),
            status="pending_upload",
            version=1,
            created_at=now(),
            updated_at=now(),
            expires_at=now() + timedelta(hours=1),
        )
        self.db.add(row)
        result = metadata(row)
        self.db.add(
            Operation(
                owner_id=owner,
                operation="attachment_upload_init",
                key=key,
                fingerprint=fingerprint,
                response=json.dumps(result),
            )
        )
        self.db.commit()
        return result

    async def upload(self, owner, attachment_id, chunks, mime, key):
        self._lock_owner(owner)
        row = self._get(owner, attachment_id, refresh=True)
        if mime != row.declared_mime:
            raise PolicyError(
                "FILE_TYPE_MISMATCH", "Content-Type does not match the declared type.", 415
            )
        if not key:
            raise PolicyError("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", 422)
        # Spool to bounded disk so retries can be compared by full body hash without
        # writing over an immutable object or retaining user bytes in memory.
        digest = hashlib.sha256()
        total = 0
        with tempfile.TemporaryFile() as spool:
            async for chunk in chunks:
                if not chunk:
                    continue
                total += len(chunk)
                if total > row.declared_size:
                    raise PolicyError(
                        "UPLOAD_TOO_LARGE", "The file exceeds the declared size.", 413
                    )
                digest.update(chunk)
                spool.write(chunk)
            if not total:
                raise PolicyError("UPLOAD_EMPTY", "The uploaded file is empty.", 422)
            fingerprint = hashlib.sha256(
                f"{attachment_id}:{mime}:{total}:{digest.hexdigest()}".encode()
            ).hexdigest()
            from .storage import Operation

            prior = self.db.scalar(
                select(Operation).where(
                    Operation.owner_id == owner,
                    Operation.operation == "attachment_upload_content",
                    Operation.key == key,
                )
            )
            if prior:
                if prior.fingerprint != fingerprint:
                    raise PolicyError("IDEMPOTENCY_KEY_REUSED", "Operation key was reused.", 409)
                result = json.loads(prior.response)
                self.db.commit()
                return result
            expiry = (
                row.expires_at.replace(tzinfo=UTC)
                if row.expires_at.tzinfo is None
                else row.expires_at
            )
            if row.status != "pending_upload" or expiry < now():
                raise PolicyError(
                    "UPLOAD_NOT_AVAILABLE", "This upload is no longer available.", 409
                )
            if row.status == "uploaded":
                raise PolicyError(
                    "UPLOAD_ALREADY_RECEIVED", "Upload content was already received.", 409
                )
            if total != row.declared_size or (
                row.expected_sha256 and digest.hexdigest().lower() != row.expected_sha256.lower()
            ):
                raise PolicyError(
                    "UPLOAD_MISMATCH", "Uploaded content did not match its declaration.", 422
                )
            spool.seek(0)

            def reread():
                while data := spool.read(128 * 1024):
                    yield data

            # Each attempt has a new key. A failed O_EXCL collision can therefore
            # never cause cleanup of an object created by another request.
            from .attachment_object_store import new_storage_key

            storage_key = new_storage_key()
            created = False
            try:
                actual_size, stored_digest = self.store.put_stream(
                    storage_key, reread(), row.declared_size
                )
                created = True
                if actual_size != total or stored_digest != digest.hexdigest():
                    raise PolicyError(
                        "UPLOAD_MISMATCH", "Uploaded content did not match its declaration.", 422
                    )
                row.storage_key = storage_key
                row.byte_size, row.sha256, row.status = actual_size, stored_digest, "uploaded"
                row.updated_at, row.version = now(), row.version + 1
                result = metadata(row)
                self.db.add(
                    Operation(
                        owner_id=owner,
                        operation="attachment_upload_content",
                        key=key,
                        fingerprint=fingerprint,
                        response=json.dumps(result),
                    )
                )
                self.db.commit()
                return result
            except Exception:
                if created:
                    self.store.delete(storage_key)
                self.db.rollback()
                raise

    def complete(self, owner, attachment_id, operation_id, key):
        self._lock_owner(owner)
        row = self._get(owner, attachment_id, refresh=True)
        if not key or str(operation_id) != key:
            raise PolicyError(
                "IDEMPOTENCY_KEY_REQUIRED", "Use operation_id as Idempotency-Key.", 422
            )
        from .storage import Operation

        fingerprint = hashlib.sha256(f"{attachment_id}:validate".encode()).hexdigest()
        prior = self.db.scalar(
            select(Operation).where(
                Operation.owner_id == owner,
                Operation.operation == "attachment_complete",
                Operation.key == key,
            )
        )
        if prior:
            if prior.fingerprint != fingerprint:
                raise PolicyError("IDEMPOTENCY_KEY_REUSED", "Operation key was reused.", 409)
            result = json.loads(prior.response)
            self.db.commit()
            return result
        if row.status not in ("uploaded", "validating"):
            raise PolicyError("UPLOAD_NOT_COMPLETE", "Upload content before validation.", 409)
        existing = self.db.scalar(
            select(AttachmentJobRow)
            .where(
                AttachmentJobRow.owner_id == owner,
                AttachmentJobRow.attachment_id == row.id,
                AttachmentJobRow.kind == "validate",
            )
            .order_by(AttachmentJobRow.created_at.desc())
        )
        if existing:
            result = job_data(existing)
            self.db.add(
                Operation(
                    owner_id=owner,
                    operation="attachment_complete",
                    key=key,
                    fingerprint=fingerprint,
                    response=json.dumps(result),
                )
            )
            self.db.commit()
            return result
        if row.status != "uploaded":
            raise PolicyError("UPLOAD_NOT_COMPLETE", "Upload content before validation.", 409)
        row.status = "validating"
        job = AttachmentJobRow(
            id=str(uuid4()),
            owner_id=owner,
            attachment_id=row.id,
            kind="validate",
            status="queued",
            input_version=row.version,
            page=None,
            attempt_count=0,
            available_at=now(),
            created_at=now(),
        )
        self.db.add(job)
        result = job_data(job)
        self.db.add(
            Operation(
                owner_id=owner,
                operation="attachment_complete",
                key=key,
                fingerprint=fingerprint,
                response=json.dumps(result),
            )
        )
        self.db.commit()
        return result

    def create_preview_job(self, owner, attachment_id, operation_id, kind, page, key):
        if kind != "preview":
            raise PolicyError("UNSUPPORTED_OPERATION", "Recognition is not available.", 422)
        self._lock_owner(owner)
        row = self._get(owner, attachment_id, refresh=True)
        if not key or str(operation_id) != key:
            raise PolicyError(
                "IDEMPOTENCY_KEY_REQUIRED", "Use operation_id as Idempotency-Key.", 422
            )
        from .storage import Operation

        fingerprint = hashlib.sha256(f"{attachment_id}:{kind}:{page}".encode()).hexdigest()
        prior = self.db.scalar(
            select(Operation).where(
                Operation.owner_id == owner,
                Operation.operation == "attachment_preview",
                Operation.key == key,
            )
        )
        if prior:
            if prior.fingerprint != fingerprint:
                raise PolicyError("IDEMPOTENCY_KEY_REUSED", "Operation key was reused.", 409)
            result = json.loads(prior.response)
            self.db.commit()
            return result
        if row.status != "ready":
            raise PolicyError("ATTACHMENT_NOT_READY", "Attachment is not ready.", 409)
        if page < 1 or page > (row.page_count or 1):
            raise PolicyError("PAGE_OUT_OF_RANGE", "Requested page is outside the attachment.", 422)
        done = self.db.scalar(
            select(AttachmentJobRow)
            .where(
                AttachmentJobRow.owner_id == owner,
                AttachmentJobRow.attachment_id == row.id,
                AttachmentJobRow.kind == "preview",
                AttachmentJobRow.page == page,
                AttachmentJobRow.status.in_(["queued", "running", "succeeded"]),
            )
            .order_by(AttachmentJobRow.created_at.desc())
        )
        if done:
            result = job_data(done)
            self.db.add(
                Operation(
                    owner_id=owner,
                    operation="attachment_preview",
                    key=key,
                    fingerprint=fingerprint,
                    response=json.dumps(result),
                )
            )
            self.db.commit()
            return result
        job = AttachmentJobRow(
            id=str(uuid4()),
            owner_id=owner,
            attachment_id=row.id,
            kind="preview",
            status="queued",
            input_version=row.version,
            page=page,
            attempt_count=0,
            available_at=now(),
            created_at=now(),
        )
        self.db.add(job)
        result = job_data(job)
        self.db.add(
            Operation(
                owner_id=owner,
                operation="attachment_preview",
                key=key,
                fingerprint=fingerprint,
                response=json.dumps(result),
            )
        )
        self.db.commit()
        return result

    def get_job(self, owner, job_id):
        row = self.db.scalar(
            select(AttachmentJobRow).where(
                AttachmentJobRow.owner_id == owner, AttachmentJobRow.id == job_id
            )
        )
        if not row:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return job_data(row)

    def find_validation_job(self, owner, attachment_id):
        row = self.db.scalar(
            select(AttachmentJobRow)
            .where(
                AttachmentJobRow.owner_id == owner,
                AttachmentJobRow.attachment_id == attachment_id,
                AttachmentJobRow.kind == "validate",
            )
            .order_by(AttachmentJobRow.created_at.desc())
        )
        return job_data(row) if row else None

    def get_attachment(self, owner, attachment_id):
        return metadata(self._get(owner, attachment_id))

    def upload_policy(self, owner, attachment_id):
        self._lock_owner(owner)
        row = self._get(owner, attachment_id, refresh=True)
        expiry = (
            row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at
        )
        return {"declared_mime": row.declared_mime, "status": row.status, "expires_at": expiry}

    def get_ready_row(self, owner, attachment_id):
        row = self._get(owner, attachment_id)
        if row.status != "ready":
            raise PolicyError("ATTACHMENT_NOT_READY", "Attachment is not ready.", 409)
        return row

    def open_original(self, owner, attachment_id):
        row = self.get_ready_row(owner, attachment_id)
        return self._open_object(row.storage_key), row.original_name

    def _open_object(self, key):
        try:
            return self.store.open(key)
        except Exception as error:
            raise PolicyError(
                "OBJECT_UNAVAILABLE", "Stored file is currently unavailable.", 503
            ) from error

    def open_preview(self, owner, attachment_id, page):
        row = self.get_ready_row(owner, attachment_id)
        if page < 1 or page > (row.page_count or 1):
            raise PolicyError("PAGE_OUT_OF_RANGE", "Requested page is outside the attachment.", 422)
        job = self.db.scalar(
            select(AttachmentJobRow)
            .where(
                AttachmentJobRow.owner_id == owner,
                AttachmentJobRow.attachment_id == row.id,
                AttachmentJobRow.kind == "preview",
                AttachmentJobRow.page == page,
                AttachmentJobRow.status == "succeeded",
                AttachmentJobRow.input_version == row.version,
            )
            .order_by(AttachmentJobRow.created_at.desc())
        )
        if not job:
            raise PolicyError("PREVIEW_NOT_READY", "Preview is not ready.", 409)
        key = json.loads(job.result_json or "{}").get("preview_key")
        if not key:
            raise PolicyError("PREVIEW_NOT_READY", "Preview is not ready.", 409)
        return self._open_object(key)

    def run_one(self):
        """Claim one durable job, do bounded parsing, persist result; safe across restarts."""
        lease_expired = AttachmentJobRow.locked_at < now() - timedelta(minutes=5)
        row = self.db.scalar(
            select(AttachmentJobRow)
            .where(
                or_(
                    AttachmentJobRow.status == "queued",
                    (AttachmentJobRow.status == "running") & lease_expired,
                ),
                AttachmentJobRow.available_at <= now(),
            )
            .order_by(AttachmentJobRow.available_at, AttachmentJobRow.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not row:
            return False
        old_status, old_locked = row.status, row.locked_at
        conditions = [AttachmentJobRow.id == row.id, AttachmentJobRow.status == old_status]
        conditions.append(
            AttachmentJobRow.locked_at.is_(None)
            if old_locked is None
            else AttachmentJobRow.locked_at == old_locked
        )
        if row.attempt_count >= 3:
            exhausted = self.db.execute(
                update(AttachmentJobRow)
                .where(*conditions, AttachmentJobRow.attempt_count == row.attempt_count)
                .values(status="failed", error_code="WORKER_RETRY_LIMIT", completed_at=now())
            )
            if exhausted.rowcount != 1:
                self.db.rollback()
                return False
            if row.kind == "validate":
                attachment = self._get(row.owner_id, row.attachment_id)
                if attachment.status == "validating" and attachment.version == row.input_version:
                    attachment.status, attachment.failure_code = "rejected", "WORKER_RETRY_LIMIT"
                    attachment.version += 1
            self.db.commit()
            return True
        claim_time, claim_token = now(), str(uuid4())
        claimed = self.db.execute(
            update(AttachmentJobRow)
            .where(*conditions)
            .values(
                status="running",
                locked_at=claim_time,
                lease_token=claim_token,
                attempt_count=AttachmentJobRow.attempt_count + 1,
            )
        )
        if claimed.rowcount != 1:
            self.db.rollback()
            return False
        self.db.commit()
        row = self.db.scalar(
            select(AttachmentJobRow)
            .where(AttachmentJobRow.id == row.id)
            .execution_options(populate_existing=True)
        )
        attachment = self._get(row.owner_id, row.attachment_id, refresh=True)
        if row.input_version != attachment.version:
            self.db.execute(
                update(AttachmentJobRow)
                .where(
                    AttachmentJobRow.id == row.id,
                    AttachmentJobRow.lease_token == claim_token,
                    AttachmentJobRow.status == "running",
                )
                .values(status="failed", error_code="STALE_INPUT", completed_at=now())
            )
            self.db.commit()
            return True
        with tempfile.TemporaryDirectory(prefix="hermes-attachment-") as scratch:
            created_preview_key = None
            try:
                source = Path(scratch) / "source.bin"
                with self.store.open(attachment.storage_key) as stream, source.open("wb") as out:
                    total = 0
                    while chunk := stream.read(128 * 1024):
                        total += len(chunk)
                        if total > attachment.declared_size:
                            raise ValueError("Stored upload exceeds declared size")
                        out.write(chunk)
                if row.kind == "validate":
                    result = self.validator.inspect(str(source), attachment.declared_mime)
                    if (
                        result["sha256"] != attachment.sha256
                        or result["byte_size"] != attachment.declared_size
                    ):
                        raise PolicyError(
                            "FILE_INTEGRITY_MISMATCH", "Stored content changed after upload.", 409
                        )
                    attachment.detected_mime, attachment.byte_size = (
                        result["detected_mime"],
                        result["byte_size"],
                    )
                    attachment.sha256, attachment.page_count = (
                        result["sha256"],
                        result["page_count"],
                    )
                    attachment.status, attachment.failure_code = "ready", None
                    attachment.version += 1
                else:
                    preview = Path(scratch) / "preview.png"
                    if attachment.detected_mime == "application/pdf":
                        result = self.validator.render_pdf_page(str(source), row.page, str(preview))
                    elif row.page == 1:
                        result = self.validator.render_image_preview(str(source), str(preview))
                    else:
                        raise PolicyError(
                            "PAGE_OUT_OF_RANGE", "Requested page is outside the attachment.", 422
                        )
                    from .attachment_object_store import new_storage_key

                    preview_key = new_storage_key()
                    self.store.put_file(preview_key, str(preview))
                    created_preview_key = preview_key
                    result["preview_key"] = preview_key
                row.result_json = json.dumps(result)
                row.status, row.completed_at, row.error_code = "succeeded", now(), None
            except Exception as error:
                code = getattr(
                    error,
                    "code",
                    "OBJECT_READ_FAILED" if not source.exists() else "PROCESSING_FAILED",
                )
                row.status, row.completed_at, row.error_code = "failed", now(), code
                if row.kind == "validate":
                    attachment.status, attachment.failure_code = "rejected", code
                    attachment.version += 1
            # A cached ORM token cannot detect a replacement worker's lease. Publish
            # through a DB compare-and-swap before flushing attachment mutations.
            job_id, owner, attachment_id = row.id, row.owner_id, row.attachment_id
            with self.db.no_autoflush:
                current_input = (
                    select(AttachmentRow.version)
                    .where(AttachmentRow.id == attachment_id, AttachmentRow.owner_id == owner)
                    .scalar_subquery()
                )
                finalized = self.db.execute(
                    update(AttachmentJobRow)
                    .where(
                        AttachmentJobRow.id == job_id,
                        AttachmentJobRow.lease_token == claim_token,
                        AttachmentJobRow.status == "running",
                        AttachmentJobRow.input_version == current_input,
                    )
                    .values(
                        status=row.status,
                        completed_at=row.completed_at,
                        error_code=row.error_code,
                        result_json=row.result_json,
                    )
                    .execution_options(synchronize_session=False)
                )
            if finalized.rowcount != 1:
                self.db.rollback()
                # If we still own the lease, it was the input version that changed.
                self.db.execute(
                    update(AttachmentJobRow)
                    .where(
                        AttachmentJobRow.id == job_id,
                        AttachmentJobRow.lease_token == claim_token,
                        AttachmentJobRow.status == "running",
                    )
                    .values(status="failed", error_code="STALE_INPUT", completed_at=now())
                )
                self.db.commit()
                if created_preview_key:
                    self.store.delete(created_preview_key)
                return True
            self.db.commit()
        return True
