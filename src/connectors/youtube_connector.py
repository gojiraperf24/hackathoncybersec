import hashlib
from datetime import datetime
from typing import AsyncIterator
import httpx
from src.connectors.base import BaseConnector
from src.models import RawItem
from src.config import settings


class YouTubeConnector(BaseConnector):
    name = "youtube"

    def __init__(self, query: str, max_results: int = 25):
        self.query = query
        self.max_results = max_results
        self._url = "https://www.googleapis.com/youtube/v3/search"

    async def fetch(self) -> AsyncIterator[RawItem]:
        params = {
            "part": "snippet",
            "q": self.query,
            "type": "video",
            "maxResults": self.max_results,
            "order": "date",
            "key": settings().youtube_api_key,
        }
        async with httpx.AsyncClient() as client:
            r = await client.get(self._url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()

        for it in data.get("items", []):
            sn = it["snippet"]
            vid = it["id"]["videoId"]
            yield RawItem(
                item_id=f"yt:{vid}",
                platform="youtube",
                native_id=vid,
                author_hash=hashlib.sha256(
                    sn.get("channelId", "unknown").encode()
                ).hexdigest()[:16],
                text=sn.get("title", "") + " :: " + sn.get("description", ""),
                media_urls=[f"https://www.youtube.com/watch?v={vid}"],
                timestamp=datetime.fromisoformat(
                    sn["publishedAt"].replace("Z", "+00:00")
                ),
                geo_hint=None,
                tagged_departments=[],
                engagement={},
                raw=it,
            )
