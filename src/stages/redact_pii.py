from src.stages.base import BaseStage, StageContext
from src.models import RawItem
from src.pipeline.pii import redact


class RedactPiiStage(BaseStage):
    name = "redact_pii"

    async def process(self, item: RawItem, ctx: StageContext) -> RawItem:
        try:
            item.text = redact(item.text)
        except Exception as e:
            ctx.logger.warning("redact_failed", item_id=item.item_id, error=str(e))
        return item
