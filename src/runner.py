import asyncio
import uuid
import yaml
import structlog
from src.config import settings
from src.models import init_db, SourceItemRow
from src.pipeline.dedupe import is_duplicate, identity_hash
from src.stages.base import StageContext
from src.stages.enrich_reddit import EnrichRedditStage
from src.stages.redact_pii import RedactPiiStage
from src.stages.persist import PersistStage
from src.pipeline.media import download_image, ensure_bucket, upload_to_s3
from src.connectors.youtube_connector import YouTubeConnector
from src.connectors.rss_connector import RSSConnector

log = structlog.get_logger()


def load_config(path: str = "config/sources.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


async def run_once():
    cfg = load_config()
    engine, Session = init_db(settings().database_url)
    ensure_bucket()

    connectors = []
    for feed in cfg["rss"]["feeds"]:
        connectors.append(RSSConnector(feed_url=feed["url"], feed_name=feed["name"]))

    yt_cfg = cfg.get("youtube", {})
    for q in yt_cfg.get("queries", []):
        connectors.append(YouTubeConnector(query=q))

    seen_hashes: set[str] = set()
    stats = {"new": 0, "dup": 0, "error": 0, "scraped": 0}

    with Session() as session:
        ctx = StageContext(session=session, logger=log, stats=stats, settings=settings())
        enrich_reddit = EnrichRedditStage()
        redact_pii = RedactPiiStage()
        persist_stage = PersistStage()

        for conn in connectors:
            try:
                async for item in conn.fetch():
                    try:
                        if is_duplicate(item, seen_hashes):
                            stats["dup"] += 1
                            continue
                        if session.get(SourceItemRow, item.item_id) is not None:
                            stats["dup"] += 1
                            continue

                        # Stage 1: enrichment (mutates text, media_urls)
                        await enrich_reddit.process(item, ctx)

                        # Stage 2: PII redaction (mutates text)
                        await redact_pii.process(item, ctx)

                        # Pin identity AFTER all stages that might replace item,
                        # immediately before persisting.  This survives the
                        # `item = await stage.process(...)` reassignment pattern.
                        item.identity_hash = identity_hash(item)

                        # Stage 3: media download + upload to MinIO
                        media_refs = []
                        for url in item.media_urls[:3]:
                            try:
                                blob, phash = await download_image(url)
                                safe_id = item.identity_hash[:16]
                                key = f"{item.platform}/{safe_id}/{uuid.uuid4().hex}.jpg"
                                if upload_to_s3(blob, key):
                                    media_refs.append({
                                        "url": url,
                                        "s3_key": key,
                                        "phash": phash,
                                        "bytes": len(blob),
                                    })
                            except Exception as e:
                                log.warning("media_failed", url=url, error=str(e))

                        item.media_refs = media_refs

                        # Stage 4: persist (unique constraint handles cross-run dup)
                        await persist_stage.process(item, ctx)

                    except Exception as e:
                        stats["error"] += 1
                        log.error("item_failed", item_id=item.item_id, error=str(e))

            except Exception as e:
                stats["error"] += 1
                log.error("connector_failed", connector=conn.name, error=str(e))

    log.info("cycle_complete", **stats)


if __name__ == "__main__":
    asyncio.run(run_once())