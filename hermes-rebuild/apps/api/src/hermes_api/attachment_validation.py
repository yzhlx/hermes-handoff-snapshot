"""Bounded content inspection and safe image/PDF preview generation."""

import hashlib
import warnings
from pathlib import Path

from .attachment_domain import (
    IMAGE_TYPES,
    MAX_IMAGE_PIXELS,
    MAX_PDF_PAGES,
    MAX_PREVIEW_PIXELS,
    PDF_TYPE,
)

FORBIDDEN_PDF_KEYS = {
    "/JavaScript",
    "/JS",
    "/AA",
    "/OpenAction",
    "/A",
    "/Next",
    "/URI",
    "/Launch",
    "/GoToR",
    "/GoToE",
    "/SubmitForm",
    "/ImportData",
    "/EmbeddedFiles",
    "/EmbeddedFile",
    "/RichMedia",
    "/XFA",
    "/Rendition",
    "/Sound",
    "/Movie",
}
FORBIDDEN_ACTIONS = {
    "/JavaScript",
    "/Launch",
    "/URI",
    "/GoToR",
    "/GoToE",
    "/SubmitForm",
    "/ImportData",
    "/Rendition",
    "/Sound",
    "/Movie",
    "/ResetForm",
    "/Hide",
}


class AttachmentValidationError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _pdf_safe(reader):
    from pypdf.generic import ArrayObject, DictionaryObject

    pending = [reader.trailer]
    seen = set()
    visited = 0
    while pending:
        value = pending.pop()
        identity = id(value)
        if identity in seen:
            continue
        seen.add(identity)
        visited += 1
        if visited > 100_000 or len(pending) > 25_000:
            raise AttachmentValidationError("PDF_COMPLEXITY_LIMIT")
        try:
            value = value.get_object()
        except Exception:
            raise AttachmentValidationError("PDF_INVALID") from None
        if isinstance(value, DictionaryObject):
            if any(str(key) in FORBIDDEN_PDF_KEYS for key in value):
                raise AttachmentValidationError("PDF_ACTIVE_CONTENT")
            action = value.get("/S")
            if str(action) in FORBIDDEN_ACTIONS:
                raise AttachmentValidationError("PDF_ACTIVE_CONTENT")
            pending.extend(value.values())
        elif isinstance(value, ArrayObject):
            pending.extend(value)


def inspect_file(path, declared_mime):
    path = Path(path)
    size = path.stat().st_size
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(128 * 1024):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    with open(path, "rb") as stream:
        header = stream.read(16)
    if declared_mime == PDF_TYPE:
        if not header.startswith(b"%PDF-") or b"%%EOF" not in path.read_bytes()[-2048:]:
            raise AttachmentValidationError("FILE_TYPE_MISMATCH")
        from pypdf import PdfReader

        try:
            reader = PdfReader(str(path), strict=True)
            if reader.is_encrypted:
                raise AttachmentValidationError("PDF_ENCRYPTED")
            _pdf_safe(reader)
            pages = len(reader.pages)
            if pages < 1 or pages > MAX_PDF_PAGES:
                raise AttachmentValidationError("PDF_PAGE_LIMIT")
            # Enforce sane page dimensions before invoking the renderer.
            for page in reader.pages:
                box = page.mediabox
                width, height = float(box.width), float(box.height)
                if not (1 <= width <= 14400 and 1 <= height <= 14400):
                    raise AttachmentValidationError("PDF_PAGE_GEOMETRY")
        except AttachmentValidationError:
            raise
        except Exception:
            raise AttachmentValidationError("PDF_INVALID") from None
        return {"detected_mime": PDF_TYPE, "byte_size": size, "sha256": digest, "page_count": pages}
    if declared_mime not in IMAGE_TYPES:
        raise AttachmentValidationError("UNSUPPORTED_MEDIA_TYPE")
    from PIL import Image, ImageFile

    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                fmt = image.format
                detected = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(fmt)
                if detected != declared_mime:
                    raise AttachmentValidationError("FILE_TYPE_MISMATCH")
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise AttachmentValidationError("IMAGE_PIXEL_LIMIT")
                image.verify()
            with Image.open(path) as image:
                image.load()
    except AttachmentValidationError:
        raise
    except Exception:
        raise AttachmentValidationError("IMAGE_INVALID") from None
    return {"detected_mime": detected, "byte_size": size, "sha256": digest, "page_count": 1}


def render_pdf_page(path, page_number, output):
    try:
        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(path)
        if page_number < 1 or page_number > len(document):
            raise AttachmentValidationError("PAGE_OUT_OF_RANGE")
        page = document[page_number - 1]
        width, height = page.get_size()
        pixels = int(width * height)
        scale = min(2.0, (MAX_PREVIEW_PIXELS / max(pixels, 1)) ** 0.5)
        if pixels <= 0 or pixels > 100_000_000:
            raise AttachmentValidationError("PDF_PAGE_GEOMETRY")
        bitmap = page.render(scale=scale, rev_byteorder=True)
        image = bitmap.to_pil()
        if image.width * image.height > MAX_PREVIEW_PIXELS:
            raise AttachmentValidationError("PREVIEW_PIXEL_LIMIT")
        dimensions = (image.width, image.height)
        image.save(output, format="PNG", optimize=False)
        image.close()
        page.close()
        document.close()
        return {"width": dimensions[0], "height": dimensions[1], "mime": "image/png"}
    except AttachmentValidationError:
        raise
    except Exception:
        raise AttachmentValidationError("PDF_PREVIEW_FAILED") from None


def render_image_preview(path, output):
    try:
        from PIL import Image, ImageOps

        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        with Image.open(path) as source:
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
            if image.width * image.height > MAX_PREVIEW_PIXELS:
                raise AttachmentValidationError("PREVIEW_PIXEL_LIMIT")
            dimensions = (image.width, image.height)
            image.save(output, format="PNG", optimize=False)
            image.close()
        return {"width": dimensions[0], "height": dimensions[1], "mime": "image/png"}
    except AttachmentValidationError:
        raise
    except Exception:
        raise AttachmentValidationError("IMAGE_PREVIEW_FAILED") from None


class ProcessFileValidator:
    """Runs native parsers in a bounded child process with a hard wall timeout."""

    def __init__(self, timeout=20):
        self.timeout = timeout

    def _run(self, args):
        import json
        import os
        import signal
        import subprocess
        import sys

        def child_limits():
            if os.name == "posix":
                import resource

                resource.setrlimit(resource.RLIMIT_CPU, (18, 20))
                memory_limit = 768 * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))

        process_options = {"preexec_fn": child_limits} if os.name == "posix" else {}

        try:
            result = subprocess.run(
                [sys.executable, "-m", "hermes_api.attachment_worker", *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(Path(__file__).resolve().parents[3]),
                **process_options,
            )
        except subprocess.TimeoutExpired:
            raise AttachmentValidationError("PROCESSING_TIMEOUT") from None
        if result.returncode != 0 or len(result.stdout) > 4096:
            code = "PROCESSING_FAILED"
            try:
                payload = json.loads(result.stdout[:4096])
            except json.JSONDecodeError:
                payload = {}
            code = payload.get("error", code)
            if result.returncode in (
                -getattr(signal, "SIGXCPU", -999),
                128 + getattr(signal, "SIGXCPU", -999),
            ):
                code = "PROCESSING_TIMEOUT"
            raise AttachmentValidationError(code)
        try:
            return json.loads(result.stdout)
        except Exception:
            raise AttachmentValidationError("PROCESSING_FAILED") from None

    def inspect(self, path, declared_mime):
        return self._run(["--inspect", path, declared_mime])

    def render_pdf_page(self, path, page, output):
        return self._run(["--render", path, str(page), output])

    def render_image_preview(self, path, output):
        return self._run(["--render-image", path, output])
