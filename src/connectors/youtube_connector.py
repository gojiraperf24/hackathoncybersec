import hashlib
from datetime import datetime
from typing import AsyncIterator
import httpx
from src.connectors.base import BaseConnector
from src.models import RawItem
from src.config import settings

class YouTubeConnector(BaseConnector):
    name = "youtube"

    def __init__(self, query: str, max_results: int = 25, max_pages: int = 1):
        self.query = query
        self.max_results = max_results
        self.max_pages = max_pages
        self._url = "https://www.googleapis.com/youtube/v3/search"

    async def fetch(self) -> AsyncIterator[RawItem]:
        # ADD THIS PRINT
        print(f"\n[DEBUG] YouTube fetch started for query: {self.query}")
        
        params = {
            "part": "snippet",
            "q": self.query,
            "type": "video",
            "maxResults": self.max_results,
            "order": "date",
            "key": settings().youtube_api_key,
        }

        async with httpx.AsyncClient() as client:
            page_token = None
            for _ in range(self.max_pages):
                if page_token:
                    params["pageToken"] = page_token

                r = await client.get(self._url, params=params, timeout=30)
                r.raise_for_status()
                data = r.json()

                items = data.get("items", [])
                # ADD THIS PRINT
                print(f"[DEBUG] YouTube API returned {len(items)} items.")

                for it in items:
                    sn = it["snippet"]
                    vid = it["id"]["videoId"]

                    thumbs = sn.get("thumbnails", {})
                    thumb_url = (
                        thumbs.get("high", {}).get("url")
                        or thumbs.get("medium", {}).get("url")
                        or thumbs.get("default", {}).get("url")
                    )

                    # ADD THIS PRINT
                    print(f"[DEBUG] Yielding video: {vid}")
                    
                    yield RawItem(
                        item_id=f"youtube:{vid}",
                        platform="youtube",
                        native_id=vid,
                        author_hash=hashlib.sha256(
                            sn.get("channelId", "unknown").encode()
                        ).hexdigest()[:16],
                        text=sn.get("title", "") + " :: " + sn.get("description", ""),
                        media_urls=[thumb_url] if thumb_url else [],
                        timestamp=datetime.fromisoformat(
                            sn["publishedAt"].replace("Z", "+00:00")
                        ),
                        geo_hint=None,
                        tagged_departments=[],
                        engagement={},
                        raw=it,
                    )

                page_token = data.get("nextPageToken")
                if not page_token:
                    break