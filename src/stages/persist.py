"""
PersistStage: write one RawItem to the source_items table.

This is the only stage that touches the database. It wraps the same logic
that lived in src/pipeline/persist.py until Commit 2, but exposes it through
the BaseStage interface so the orchestrator can call it uniformly.
"""
from sqlalchemy.exc import IntegrityError

from src.stages.base import BaseStage, StageContext
from src.models import RawItem, SourceItemRow


class PersistStage(BaseStage):
    name = "persist"

    async def process(self, item: RawItem, ctx: StageContext) -> RawItem:
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
            media_urls=item.media_refs,   # DB column stores refs, not URLs
            link=post_link,
            raw=item.raw,
        )

        try:
            with ctx.session.begin_nested():
                ctx.session.add(row)
            ctx.session.commit()
            ctx.stats["new"] = ctx.stats.get("new", 0) + 1
            ctx.logger.info("ingested", platform=item.platform, item_id=item.item_id)
        except IntegrityError as e:
            ctx.logger.debug(
                "dup_at_db",
                item_id=item.item_id,
                constraint=str(e.orig)[:120],
            )
            ctx.stats["dup"] = ctx.stats.get("dup", 0) + 1

        return item
