"""Private immutable local and S3-compatible object storage adapters."""

import hashlib
import os
import secrets
import stat
from pathlib import Path


class LocalPrivateStore:
    def __init__(self, root):
        requested = Path(root).expanduser().absolute()
        if requested.is_symlink():
            raise ValueError("Attachment root cannot be a symbolic link")
        self.root = requested
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.root.is_symlink():
            raise ValueError("Attachment root cannot be a symbolic link")
        self.root = self.root.resolve(strict=True)

    def _path(self, key):
        if not key or "/" in key or "\\" in key or key in {".", ".."}:
            raise ValueError("Invalid opaque object key")
        path = self.root / key
        if path.parent.resolve() != self.root:
            raise ValueError("Invalid object path")
        return path

    def put_stream(self, key, chunks, max_bytes):
        path = self._path(key)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        total, digest = 0, hashlib.sha256()
        try:
            with os.fdopen(fd, "wb") as output:
                for chunk in chunks:
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("UPLOAD_TOO_LARGE")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if not total:
                raise ValueError("UPLOAD_EMPTY")
            return total, digest.hexdigest()
        except Exception:
            try:
                path.unlink()
            except OSError:
                pass
            raise

    def open(self, key):
        path = self._path(key)
        if path.is_symlink():
            raise FileNotFoundError
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise FileNotFoundError
        return os.fdopen(fd, "rb")

    def delete(self, key):
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            pass

    def put_file(self, key, source):
        with open(source, "rb") as stream:
            self.put_stream(key, iter(lambda: stream.read(128 * 1024), b""), 25 * 1024 * 1024)


class S3PrivateStore:
    def __init__(self, bucket, endpoint, region, access_key, secret_key):
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            region_name=region or None,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            config=Config(
                connect_timeout=5, read_timeout=15, retries={"max_attempts": 2, "mode": "standard"}
            ),
        )

    def put_stream(self, key, chunks, max_bytes):
        # Bounded spooling allows SDK upload without loading user data into memory.
        import tempfile

        total, digest = 0, hashlib.sha256()
        with tempfile.TemporaryFile() as spool:
            for chunk in chunks:
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("UPLOAD_TOO_LARGE")
                digest.update(chunk)
                spool.write(chunk)
            if not total:
                raise ValueError("UPLOAD_EMPTY")
            spool.seek(0)
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=spool,
                IfNoneMatch="*",
                ServerSideEncryption="AES256",
            )
        return total, digest.hexdigest()

    def open(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"]

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def put_file(self, key, source):
        with open(source, "rb") as stream:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=stream,
                IfNoneMatch="*",
                ServerSideEncryption="AES256",
            )


def make_store(settings):
    if settings.attachment_storage == "s3":
        if not settings.attachment_s3_bucket:
            raise ValueError("Private S3 bucket is required")
        return S3PrivateStore(
            settings.attachment_s3_bucket,
            settings.attachment_s3_endpoint,
            settings.attachment_s3_region,
            settings.attachment_s3_access_key.get_secret_value(),
            settings.attachment_s3_secret_key.get_secret_value(),
        )
    if settings.environment == "production":
        raise ValueError("Local attachment storage is disabled in production")
    root = settings.attachment_local_root or str(Path.cwd() / ".local" / "attachments")
    return LocalPrivateStore(root)


def new_storage_key():
    return secrets.token_urlsafe(32)
