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
            
            # 1. Extract the image URL from the RSS summary HTML
            image_urls = []
            img_match = re.search(r'<img[^>]+src="([^">]+)"', summary)
            if img_match:
                image_urls.append(img_match.group(1))
                
            if hasattr(entry, 'media_thumbnail'):
                for thumb in entry.media_thumbnail:
                    if thumb['url'] not in image_urls:
                        image_urls.append(thumb['url'])

            has_image = len(image_urls) > 0
            
            # 2. FILTER LOGIC: Count words ONLY in the body/summary, not the title
            # We strip out HTML tags first so we are counting actual words
            clean_summary = re.sub(r'<[^>]+>', ' ', summary)
            body_word_count = len(clean_summary.split())
            
            # Skip if no image AND body is shorter than 30 words
            if not has_image and body_word_count < 30:
                continue 

            # Parse timestamp
            ts = entry.get("published_parsed") or entry.get("updated_parsed")
            timestamp = (
                datetime(*ts[:6], tzinfo=timezone.utc)
                if ts else datetime.now(timezone.utc)
            )

            post_link = entry.get("link", "")

            yield RawItem(
                item_id=f"rss:{self.feed_name}:{native_id}",
                platform="rss",
                native_id=native_id,
                author_hash=hashlib.sha256(
                    (entry.get("author", "") + self.feed_name).encode()
                ).hexdigest()[:16],
                text=title + "\n\n" + summary, # I added double newline for better spacing
                media_urls=image_urls, 
                timestamp=timestamp,
                geo_hint=None,
                tagged_departments=[],
                engagement={},
                raw={"link": post_link, "title": title},
            )
