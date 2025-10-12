from typing import Protocol, Tuple
import os
from app.core import config

class StorageService(Protocol):
    def save(self, file_bytes: bytes, filename: str) -> Tuple[str, str]:
        """Save bytes and return (url_or_path, key)."""
        ...

class LocalStorageService:
    base_dir: str = os.getenv("LOCAL_UPLOAD_DIR", "uploaded_resumes")

    def save(self, file_bytes: bytes, filename: str) -> Tuple[str, str]:
        os.makedirs(self.base_dir, exist_ok=True)
        safe_name = filename or "upload.bin"
        dest_path = os.path.join(self.base_dir, safe_name)
        with open(dest_path, "wb") as f:
            f.write(file_bytes)
        return dest_path, dest_path

class FirebaseStorageService:
    def __init__(self):
        # Lazy import; in real impl, initialize SDK with service account envs
        self.bucket = config.FIREBASE_STORAGE_BUCKET

    def save(self, file_bytes: bytes, filename: str) -> Tuple[str, str]:
        # Stub: Replace with firebase_admin storage client
        # For now, fall back to local while returning a URL-like string
        local = LocalStorageService()
        path, key = local.save(file_bytes, filename)
        return f"firebase://{self.bucket}/{os.path.basename(path)}", key


def get_storage_service() -> StorageService:
    if config.USE_FIREBASE and config.FIREBASE_STORAGE_BUCKET:
        return FirebaseStorageService()
    return LocalStorageService()
