from datetime import datetime, timezone
from src.models import RawItem
from src.pipeline.dedupe import is_duplicate, identity_hash


def _mk(native_id="1", text="pothole on MG Road"):
    return RawItem(
        item_id=f"x:{native_id}", platform="x", native_id=native_id,
        text=text, timestamp=datetime.now(timezone.utc),
    )


def test_same_item_is_duplicate():
    seen = set()
    assert not is_duplicate(_mk(), seen)
    assert is_duplicate(_mk(), seen)


def test_different_native_id_not_duplicate():
    seen = set()
    assert not is_duplicate(_mk("1"), seen)
    assert not is_duplicate(_mk("2"), seen)


def test_hash_stable():
    assert identity_hash(_mk()) == identity_hash(_mk())
