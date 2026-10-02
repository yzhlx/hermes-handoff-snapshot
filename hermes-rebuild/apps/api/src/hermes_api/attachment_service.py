"""Application service coordinating attachment use cases through a repository port."""

from datetime import UTC, datetime

from .attachment_domain import supported_limit
from .attachment_ports import AttachmentRepository
from .domain import PolicyError


class AttachmentService:
    def __init__(self, repository: AttachmentRepository):
        self.repository = repository

    def initialize(self, owner, body, key):
        # Validate portable business constraints before the persistence adapter runs.
        limit = supported_limit(body["declared_mime"])
        if body["byte_size"] < 1 or body["byte_size"] > limit:
            raise PolicyError("UPLOAD_TOO_LARGE", "The file exceeds the allowed size.", 413)
        if len(body["filename"].strip()) == 0:
            raise PolicyError("VALIDATION_ERROR", "Filename is required.", 422)
        return self.repository.initialize(owner, body, key)

    async def upload(self, owner, attachment_id, chunks, mime, key):
        current = self.repository.upload_policy(owner, attachment_id)
        if not key:
            raise PolicyError("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", 422)
        if mime != current["declared_mime"]:
            raise PolicyError(
                "FILE_TYPE_MISMATCH", "Content-Type does not match the declared type.", 415
            )
        if current["status"] == "pending_upload" and current["expires_at"] < datetime.now(UTC):
            raise PolicyError("UPLOAD_NOT_AVAILABLE", "This upload is no longer available.", 409)
        return await self.repository.upload(owner, attachment_id, chunks, mime, key)

    def complete(self, owner, attachment_id, operation_id, key):
        current = self.repository.get_attachment(owner, attachment_id)
        if not key or str(operation_id) != key:
            raise PolicyError(
                "IDEMPOTENCY_KEY_REQUIRED", "Use operation_id as Idempotency-Key.", 422
            )
        if current["status"] not in (
            "uploaded",
            "validating",
        ) and not self.repository.find_validation_job(owner, attachment_id):
            raise PolicyError("UPLOAD_NOT_COMPLETE", "Upload content before validation.", 409)
        return self.repository.complete(owner, attachment_id, operation_id, key)

    def create_preview_job(self, owner, attachment_id, operation_id, kind, page, key):
        if not key or str(operation_id) != key:
            raise PolicyError(
                "IDEMPOTENCY_KEY_REQUIRED", "Use operation_id as Idempotency-Key.", 422
            )
        if kind != "preview":
            raise PolicyError("UNSUPPORTED_OPERATION", "Recognition is not available.", 422)
        current = self.repository.get_attachment(owner, attachment_id)
        if current["status"] != "ready":
            raise PolicyError("ATTACHMENT_NOT_READY", "Attachment is not ready.", 409)
        if page < 1 or page > (current.get("page_count") or 1):
            raise PolicyError("PAGE_OUT_OF_RANGE", "Requested page is outside the attachment.", 422)
        return self.repository.create_preview_job(
            owner, attachment_id, operation_id, kind, page, key
        )

    def get_job(self, owner, job_id):
        return self.repository.get_job(owner, job_id)

    def get_attachment(self, owner, attachment_id):
        return self.repository.get_attachment(owner, attachment_id)

    def open_original(self, owner, attachment_id):
        return self.repository.open_original(owner, attachment_id)

    def open_preview(self, owner, attachment_id, page):
        return self.repository.open_preview(owner, attachment_id, page)

    def run_one(self):
        return self.repository.run_one()

    @property
    def store(self):
        return self.repository.store
