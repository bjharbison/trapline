"""Synthetic-only, offline blob storage tests."""
import hashlib
import pytest

from trapline_api.blob_store import BlobStore


def test_round_trip_dedup_and_private_permissions(tmp_path):
    store = BlobStore(tmp_path)
    digest = store.put(b"synthetic evidence only")
    assert digest == hashlib.sha256(b"synthetic evidence only").hexdigest()
    assert store.put(b"synthetic evidence only") == digest
    assert store.get(digest) == b"synthetic evidence only"
    assert store._path(digest).stat().st_mode & 0o777 == 0o600


def test_limit_and_invalid_digest(tmp_path):
    store = BlobStore(tmp_path, max_bytes=3)
    with pytest.raises(ValueError):
        store.put(b"1234")
    for digest in ("../x", "f" * 63, "G" * 64):
        with pytest.raises(ValueError):
            store.get(digest)


def test_tamper_and_symlink_rejected(tmp_path):
    store = BlobStore(tmp_path)
    digest = store.put(b"abc")
    store._path(digest).write_bytes(b"changed")
    with pytest.raises(ValueError):
        store.get(digest)
    store._path(digest).unlink()
    store._path(digest).symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ValueError):
        store.put(b"abc")


def test_empty_blob(tmp_path):
    store = BlobStore(tmp_path)
    assert store.get(store.put(b"")) == b""
