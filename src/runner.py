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
from src.pipeline.scraper import scrape_reddit_post # <-- NEW IMPORT
from src.connectors.youtube_connector import YouTubeConnector
from src.connectors.rss_connector import RSSConnector

log = structlog.get_logger()

def load_config(path: str = "config/sources.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)

async def run_once():
    cfg = load_config()
    engine, Session = init_db(settings().database_url)

    connectors = []
    for feed in cfg["rss"]["feeds"]:
        connectors.append(RSSConnector(feed_url=feed["url"], feed_name=feed["name"]))

    seen_hashes: set[str] = set()
    stats = {"new": 0, "dup": 0, "error": 0, "scraped": 0}

    with Session() as session:
        for conn in connectors:
            try:
                async for item in conn.fetch():
                    if is_duplicate(item, seen_hashes):
                        stats["dup"] += 1
                        continue

                    # STAGE 2 SCRAPING LOGIC HERE
                    post_link = item.raw.get("link", "") if item.raw else ""
                    if "reddit.com" in post_link:
                        log.info("scraping_post", url=post_link)
                        scraped_data = await scrape_reddit_post(post_link)
                        
                        # Add full image if we found one
                        if scraped_data["full_image"]:
                            item.media_urls.append(scraped_data["full_image"])
                            
                        # Append comments to the text so they get saved!
                        if scraped_data["comments"]:
                            comments_text = "\n\n--- Comments ---\n" + "\n".join(scraped_data["comments"])
                            item.text += comments_text
                            stats["scraped"] += 1
                            
                        # Be nice to Reddit's servers so we don't get IP banned
                        await asyncio.sleep(2) 

                    # Redact PII after scraping (so we redact comments too)
                    item.text = redact(item.text)

                    # Media download (now it will download the full image!)
                    media_refs = []
                    for url in item.media_urls[:3]: 
                        try:
                            blob, phash = await download_image(url)
                            key = f"{item.platform}/{item.item_id}/{uuid.uuid4().hex}.jpg"
                            # TODO: upload blob to S3
                            media_refs.append({"url": url, "s3_key": key, "phash": phash})
                        except Exception as e:
                            log.warning("media_failed", url=url, error=str(e))

                    if upsert_item(session, item, media_refs):
                        stats["new"] += 1
                        log.info("ingested", platform=item.platform, item_id=item.item_id)
            except Exception as e:
                stats["error"] += 1
                log.error("connector_failed", connector=conn.name, error=str(e))

    log.info("cycle_complete", **stats)

if __name__ == "__main__":
    asyncio.run(run_once())