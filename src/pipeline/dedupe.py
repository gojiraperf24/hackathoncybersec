import hashlib
from src.models import RawItem


def content_hash(item: RawItem) -> str:
    """Stable hash of the fields that define identity + content."""
    payload = f"{item.platform}|{item.native_id}|{item.text.strip().lower()}"
    return hashlib.sha256(payload.encode()).hexdigest()


def is_duplicate(item: RawItem, seen: set[str]) -> bool:
    h = content_hash(item)
    if h in seen:
        return True
    seen.add(h)
    return False
