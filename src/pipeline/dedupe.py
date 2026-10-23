import hashlib
from src.models import RawItem


def identity_hash(item: RawItem) -> str:
    """
    Stable hash of the post's *identity* (not its content).
    Never changes for a given post, even if the text is edited
    or redacted differently on a later run.
    """
    payload = f"{item.platform}|{item.native_id}"
    return hashlib.sha256(payload.encode()).hexdigest()


def is_duplicate(item: RawItem, seen: set[str]) -> bool:
    """Per-run short-circuit. Cheap; not a substitute for the DB constraint."""
    h = identity_hash(item)
    if h in seen:
        return True
    seen.add(h)
    return False
