import asyncio
import uuid
import yaml
import structlog
from src.config import settings
from src.models import init_db
from src.pipeline.dedupe import is_duplicate
from src.pipeline.persist import upsert_item
from src.pipeline.pii import redact
from src.pipeline.media import download_image
from src.connectors.x_connector import XConnector
from src.connectors.youtube_connector import YouTubeConnector
from src.connectors.rss_connector import RSSConnector

log = structlog.get_logger()


def load_config(path: str = "config/sources.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


async def run_once():
    cfg = load_config()
    engine, Session = init_db(settings().database_url)

    connectors = [
        XConnector(query=cfg["x"]["query_extra"],
                   max_results=cfg["x"]["max_results"]),
    ]
    for q in cfg["youtube"]["search_queries"]:
        connectors.append(YouTubeConnector(query=q))
    for feed in cfg["rss"]["feeds"]:
        connectors.append(RSSConnector(feed_url=feed["url"],
                                       feed_name=feed["name"]))

    seen_hashes: set[str] = set()
    stats = {"new": 0, "dup": 0, "error": 0}

    with Session() as session:
        for conn in connectors:
            try:
                async for item in conn.fetch():
                    if is_duplicate(item, seen_hashes):
                        stats["dup"] += 1
                        continue

                    # PII redaction before persist
                    item.text = redact(item.text)

                    # Media download + perceptual hash (best-effort)
                    media_refs = []
                    for url in item.media_urls[:3]:  # cap for safety
                        try:
                            blob, phash = await download_image(url)
                            key = f"{item.platform}/{item.item_id}/{uuid.uuid4().hex}.jpg"
                            # TODO: upload `blob` to S3/MinIO at `key`
                            media_refs.append(
                                {"url": url, "s3_key": key, "phash": phash}
                            )
                        except Exception as e:
                            log.warning("media_failed", url=url, error=str(e))

                    if upsert_item(session, item, media_refs):
                        stats["new"] += 1
                        log.info("ingested", platform=item.platform,
                                 item_id=item.item_id)
            except Exception as e:
                stats["error"] += 1
                log.error("connector_failed", connector=conn.name, error=str(e))

    log.info("cycle_complete", **stats)


if __name__ == "__main__":
    asyncio.run(run_once())
