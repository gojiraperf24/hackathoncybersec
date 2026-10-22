import hashlib
from datetime import datetime, timezone
from typing import AsyncIterator
import feedparser
from src.connectors.base import BaseConnector
from src.models import RawItem


class RSSConnector(BaseConnector):
    name = "rss"

    def __init__(self, feed_url: str, feed_name: str):
        self.feed_url = feed_url
        self.feed_name = feed_name

    async def fetch(self) -> AsyncIterator[RawItem]:
        parsed = feedparser.parse(self.feed_url)
        for entry in parsed.entries:
            native_id = entry.get("id") or entry.get("link")
            if not native_id:
                continue
            ts = entry.get("published_parsed") or entry.get("updated_parsed")
            timestamp = (
                datetime(*ts[:6], tzinfo=timezone.utc)
                if ts else datetime.now(timezone.utc)
            )
            yield RawItem(
                item_id=f"rss:{self.feed_name}:{native_id}",
                platform="rss",
                native_id=native_id,
                author_hash=hashlib.sha256(
                    (entry.get("author", "") + self.feed_name).encode()
                ).hexdigest()[:16],
                text=entry.get("title", "") + "\n" + entry.get("summary", ""),
                media_urls=[l["href"] for l in entry.get("links", [])
                            if l.get("rel") == "enclosure"],
                timestamp=timestamp,
                geo_hint=None,
                tagged_departments=[],
                engagement={},
                raw={k: entry.get(k) for k in ("title", "link", "author")},
            )
