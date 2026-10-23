from datetime import datetime, timezone
from src.models import RawItem, init_db
from src.pipeline.dedupe import identity_hash
from src.pipeline.persist import upsert_item


def _make_item(**overrides) -> RawItem:
    item = RawItem(
        item_id="rss:reddit-bangalore:https://reddit.com/r/bangalore/new/t3_abc",
        platform="rss",
        native_id="https://reddit.com/r/bangalore/new/t3_abc",
        timestamp=datetime.now(timezone.utc),
        text="pothole on MG Road",
    )
    item.identity_hash = identity_hash(item)
    for k, v in overrides.items():
        setattr(item, k, v)
    return item


def test_second_run_skips_duplicate(tmp_path):
    engine, Session = init_db(f"sqlite:///{tmp_path / 'test.db'}")

    with Session() as s:
        item = _make_item()
        assert upsert_item(s, item, media_refs=[]) is True

    with Session() as s:
        item = _make_item()   # fresh instance, same identity
        assert upsert_item(s, item, media_refs=[]) is False


def test_same_content_different_native_id_is_allowed(tmp_path):
    """Two posts on different platforms with the same text should both insert."""
    engine, Session = init_db(f"sqlite:///{tmp_path / 'test.db'}")

    with Session() as s:
        a = _make_item(item_id="x:1", platform="rss", native_id="a", text="same text")
        b = _make_item(item_id="x:2", platform="rss", native_id="b", text="same text")
        a.identity_hash = identity_hash(a)
        b.identity_hash = identity_hash(b)
        assert upsert_item(s, a, media_refs=[]) is True
        assert upsert_item(s, b, media_refs=[]) is True
