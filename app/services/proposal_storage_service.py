import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

_ALLOWED_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "application/pdf"})


def _extension_for_content_type(content_type: str) -> str:
    ext = mimetypes.guess_extension(content_type, strict=True)
    if ext == ".jpe":
        return ".jpg"
    return ext or ".bin"


class ProposalStorageService:
    def __init__(self, upload_root: str | None = None, max_bytes: int | None = None) -> None:
        self._root = Path(upload_root or settings.UPLOAD_ROOT).resolve()
        self._max = max_bytes if max_bytes is not None else settings.MAX_UPLOAD_BYTES

    def persist_upload(self, upload: UploadFile, proposal_id: int) -> tuple[str, int]:
        content_type = (upload.content_type or "").split(";")[0].strip().lower()
        if content_type not in _ALLOWED_TYPES:
            raise ValueError(f"Unsupported file type: {content_type or 'unknown'}")

        now = datetime.now(timezone.utc)
        shard = self._root / "proposals" / f"{now:%Y}" / f"{now:%m}" / f"{now:%d}"
        shard.mkdir(parents=True, exist_ok=True)

        ext = _extension_for_content_type(content_type)
        name = f"{proposal_id}_{uuid.uuid4().hex}{ext}"
        dest = shard / name

        size = 0
        with dest.open("wb") as out:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > self._max:
                    dest.unlink(missing_ok=True)
                    raise ValueError(f"File exceeds maximum size of {self._max} bytes")
                out.write(chunk)

        relative = str(dest.relative_to(self._root))
        return relative, size

    def absolute_path(self, storage_relative: str) -> Path:
        candidate = (self._root / storage_relative).resolve()
        try:
            candidate.relative_to(self._root.resolve())
        except ValueError as exc:
            raise ValueError("Invalid storage path") from exc
        return candidate

    def delete_file(self, storage_relative: str) -> None:
        path = self.absolute_path(storage_relative)
        path.unlink(missing_ok=True)
