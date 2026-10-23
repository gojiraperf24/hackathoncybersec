from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models import RawItem, SourceItemRow
import structlog

log = structlog.get_logger()


def upsert_item(session: Session, item: RawItem, media_refs: list[dict]) -> bool:
    """Insert one row. Returns True if new, False if a DB constraint rejected it."""
    post_link = item.raw.get("link", "") if item.raw else ""

    row = SourceItemRow(
        item_id=item.item_id,
        platform=item.platform,
        native_id=item.native_id,
        identity_hash=item.identity_hash,
        author_hash=item.author_hash,
        text=item.text,
        timestamp=item.timestamp,
        geo_hint=item.geo_hint,
        tagged_departments=item.tagged_departments,
        engagement=item.engagement,
        media_urls=item.media_urls,
        link=post_link,
        raw=item.raw,
    )

    try:
        with session.begin_nested():
            session.add(row)
    except IntegrityError as e:
        log.debug("dup_at_db", item_id=item.item_id, constraint=str(e.orig)[:120])
        return False

    session.commit()
    return True
