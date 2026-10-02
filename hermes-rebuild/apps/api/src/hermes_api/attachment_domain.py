"""Attachment rules and safe metadata shape, independent of HTTP/storage."""

from dataclasses import dataclass

from .domain import PolicyError

IMAGE_TYPES = {
    "image/jpeg": 10 * 1024 * 1024,
    "image/png": 10 * 1024 * 1024,
    "image/webp": 10 * 1024 * 1024,
}
PDF_TYPE = "application/pdf"
MAX_PDF_BYTES = 30 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_IMAGE_PIXELS = 40_000_000
MAX_PREVIEW_PIXELS = 20_000_000


def supported_limit(mime):
    if mime in IMAGE_TYPES:
        return IMAGE_TYPES[mime]
    if mime == PDF_TYPE:
        return MAX_PDF_BYTES
    raise PolicyError(
        "UNSUPPORTED_MEDIA_TYPE", "Only JPEG, PNG, WebP, and PDF files are accepted.", 415
    )


def safe_filename(value):
    value = value.replace("\\", "/").split("/")[-1]
    value = "".join(ch for ch in value if ch.isprintable() and ch not in '"<>|:*?')[:180].strip(
        " ."
    )
    return value or "attachment"


def metadata(row):
    return {
        "id": row.id,
        "version": row.version,
        "status": row.status,
        "original_name": row.original_name,
        "detected_mime": row.detected_mime,
        "byte_size": row.byte_size,
        "sha256": row.sha256,
        "page_count": row.page_count,
        "failure_code": row.failure_code,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "expires_at": row.expires_at.isoformat(),
    }


def job_data(row):
    return {
        "id": row.id,
        "attachment_id": row.attachment_id,
        "kind": row.kind,
        "status": row.status,
        "input_version": row.input_version,
        "attempt_count": row.attempt_count,
        "error_code": row.error_code,
    }


@dataclass(frozen=True)
class ValidationResult:
    detected_mime: str
    byte_size: int
    sha256: str
    page_count: int | None
