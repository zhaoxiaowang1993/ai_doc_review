from dataclasses import dataclass
import hashlib
from pathlib import Path

from config.config import settings


@dataclass(frozen=True)
class StoredObject:
    storage_provider: str
    storage_key: str
    mime_type: str
    size_bytes: int
    sha256: str


class LocalStorageProvider:
    def __init__(self, base_dir: str | None = None) -> None:
        self._root = Path(base_dir or settings.local_docs_dir).resolve()
        self._objects_dir = (self._root / "objects").resolve()
        self._objects_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "local"

    def put_pdf(self, *, doc_id: str, data: bytes) -> StoredObject:
        sha256 = hashlib.sha256(data).hexdigest()
        storage_key = f"objects/{doc_id}.pdf"
        path = self._resolve_storage_key(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredObject(
            storage_provider=self.name,
            storage_key=storage_key,
            mime_type="application/pdf",
            size_bytes=len(data),
            sha256=sha256,
        )

    def open(self, storage_key: str) -> Path:
        path = self._resolve_storage_key(storage_key)
        if not path.exists():
            raise FileNotFoundError(storage_key)
        return path

    def delete(self, storage_key: str) -> None:
        path = self._resolve_storage_key(storage_key)
        if path.exists():
            path.unlink()

    def _resolve_storage_key(self, storage_key: str) -> Path:
        candidate = (self._root / storage_key).resolve()
        if candidate == self._root or self._root not in candidate.parents:
            raise ValueError("Invalid storage_key")
        return candidate
