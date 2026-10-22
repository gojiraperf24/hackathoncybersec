from sqlalchemy.orm import Session
from src.models import RawItem, SourceItemRow


def upsert_item(session: Session, item: RawItem, media_refs: list[dict]) -> bool:
    """Idempotent insert. Returns True if new, False if already present."""
    existing = session.get(SourceItemRow, item.item_id)
    if existing:
        return False
    row = SourceItemRow(
        item_id=item.item_id,
        platform=item.platform,
        native_id=item.native_id,
        author_hash=item.author_hash,
        text=item.text,
        timestamp=item.timestamp,
        geo_hint=item.geo_hint,
        tagged_departments=item.tagged_departments,
        engagement=item.engagement,
        media_refs=media_refs,
        raw=item.raw,
    )
    session.add(row)
    session.commit()
    return True
