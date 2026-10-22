import hashlib
from datetime import datetime, timezone
from typing import AsyncIterator
import feedparser
import re
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

            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            
            # Check if RSS says there's an image (even a thumbnail)
            has_image = '<img' in summary or hasattr(entry, 'media_thumbnail')
            
            # Filter: Skip if no image AND title is too short (< 30 words)
            word_count = len(title.split()) + len(summary.split())
            if not has_image and word_count < 30:
                continue 

            # Parse timestamp
            ts = entry.get("published_parsed") or entry.get("updated_parsed")
            timestamp = (
                datetime(*ts[:6], tzinfo=timezone.utc)
                if ts else datetime.now(timezone.utc)
            )

            # We pass the link in the raw data so Stage 2 can use it
            post_link = entry.get("link", "")

            yield RawItem(
                item_id=f"rss:{self.feed_name}:{native_id}",
                platform="rss",
                native_id=native_id,
                author_hash=hashlib.sha256(
                    (entry.get("author", "") + self.feed_name).encode()
                ).hexdigest()[:16],
                text=title + "\n" + summary,
                media_urls=[], # Leave empty! Stage 2 will fill this
                timestamp=timestamp,
                geo_hint=None,
                tagged_departments=[],
                engagement={},
                raw={"link": post_link, "title": title},
            )