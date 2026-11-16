"""Local content-addressed blob storage; no database or network operations.

Callers must commit metadata separately and reconcile orphaned blobs after crashes.
The root must be a trusted, private local directory, not writable by other users.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

MAX_BLOB_BYTES = 16 * 1024 * 1024


class BlobStore:
    def __init__(self, root: Path, max_bytes: int = MAX_BLOB_BYTES):
        if not 0 < max_bytes <= MAX_BLOB_BYTES:
            raise ValueError("invalid blob limit")
        self.root = Path(root)
        if self.root.is_symlink():
            raise ValueError("symlink blob root")
        self.max_bytes = max_bytes

    def _path(self, digest: str) -> Path:
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("invalid SHA-256 digest")
        return self.root / digest[:2] / digest[2:4] / digest

    def put(self, content: bytes) -> str:
        if not isinstance(content, bytes):
            raise TypeError("content must be bytes")
        if len(content) > self.max_bytes:
            raise ValueError("blob exceeds size limit")
        digest = hashlib.sha256(content).hexdigest()
        target = self._path(digest)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if any(part.is_symlink() for part in (self.root, target.parent.parent, target.parent)):
            raise ValueError("symlink blob directory")
        if target.is_symlink():
            raise ValueError("symlink blob destination")
        if target.exists():
            if self.get(digest) != content:
                raise ValueError("existing blob checksum mismatch")
            return digest
        fd, tmp_name = tempfile.mkstemp(prefix=".incoming-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as out:
                os.fchmod(out.fileno(), 0o600)
                out.write(content)
                out.flush()
                os.fsync(out.fileno())
            # Never overwrite an existing digest target, including symlinks.
            os.link(tmp_name, target, follow_symlinks=False)
        except FileExistsError:
            if self.get(digest) != content:
                raise ValueError("existing blob checksum mismatch")
        finally:
            Path(tmp_name).unlink(missing_ok=True)
        return digest

    def get(self, digest: str) -> bytes:
        target = self._path(digest)
        if any(part.is_symlink() for part in (self.root, target.parent.parent, target.parent, target)):
            raise ValueError("symlink blob path")
        with target.open("rb") as f:
            content = f.read(self.max_bytes + 1)
        if len(content) > self.max_bytes or hashlib.sha256(content).hexdigest() != digest:
            raise ValueError("blob integrity check failed")
        return content
