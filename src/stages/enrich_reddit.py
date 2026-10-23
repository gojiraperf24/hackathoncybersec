import asyncio

from src.stages.base import BaseStage, StageContext
from src.models import RawItem
from src.pipeline.scraper import scrape_reddit_post


class EnrichRedditStage(BaseStage):
    name = "enrich_reddit"

    async def process(self, item: RawItem, ctx: StageContext) -> RawItem:
        link = item.raw.get("link", "") if item.raw else ""
        if "reddit.com" not in link:
            return item   # not a Reddit item, skip silently

        try:
            ctx.logger.info("scraping_post", url=link)
            scraped = await scrape_reddit_post(link)

            if scraped.get("full_image"):
                item.media_urls.append(scraped["full_image"])

            if scraped.get("comments"):
                comments_text = "\n\n--- Comments ---\n" + "\n".join(scraped["comments"])
                item.text += comments_text
                ctx.stats["scraped"] = ctx.stats.get("scraped", 0) + 1

            await asyncio.sleep(2)   # be nice to Reddit
        except Exception as e:
            ctx.logger.warning("scrape_failed", url=link, error=str(e))

        return item
