import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

_AVATAR_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
_MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MiB


def _extension_for_content_type(content_type: str) -> str:
    ext = mimetypes.guess_extension(content_type, strict=True)
    if ext == ".jpe":
        return ".jpg"
    return ext or ".bin"


class ProfileStorageService:
    def __init__(self, upload_root: str | None = None) -> None:
        self._root = Path(upload_root or settings.UPLOAD_ROOT).resolve()

    def persist_avatar(self, upload: UploadFile, user_id: int) -> tuple[str, str]:
        content_type = (upload.content_type or "").split(";")[0].strip().lower()
        if content_type not in _AVATAR_TYPES:
            raise ValueError(
                f"Unsupported avatar type: {content_type or 'unknown'}; use JPEG, PNG, or WebP"
            )

        now = datetime.now(timezone.utc)
        shard = self._root / "profiles" / f"{now:%Y}" / f"{now:%m}"
        shard.mkdir(parents=True, exist_ok=True)

        ext = _extension_for_content_type(content_type)
        name = f"user_{user_id}_{uuid.uuid4().hex}{ext}"
        dest = shard / name

        size = 0
        with dest.open("wb") as out:
            while True:
                chunk = upload.file.read(1024 * 64)
                if not chunk:
                    break
                size += len(chunk)
                if size > _MAX_AVATAR_BYTES:
                    dest.unlink(missing_ok=True)
                    raise ValueError(f"Avatar exceeds maximum size of {_MAX_AVATAR_BYTES} bytes")
                out.write(chunk)

        relative = str(dest.relative_to(self._root))
        return relative, content_type

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
