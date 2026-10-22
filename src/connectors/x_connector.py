import hashlib
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt
from src.connectors.base import BaseConnector
from src.models import RawItem
from src.config import settings


def _hash_author(username: str) -> str:
    return hashlib.sha256(username.encode()).hexdigest()[:16]


class XConnector(BaseConnector):
    name = "x"

    def __init__(self, query: str, max_results: int = 100):
        self.query = query
        self.max_results = max_results
        self._url = "https://api.x.com/2/tweets/search/recent"

    @retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(5))
    async def _call(self, client: httpx.AsyncClient, params: dict) -> dict:
        r = await client.get(
            self._url,
            params=params,
            headers={"Authorization": f"Bearer {settings().x_bearer_token}"},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    async def fetch(self) -> AsyncIterator[RawItem]:
        params = {
            "query": self.query,
            "max_results": min(self.max_results, 100),
            "tweet.fields": "created_at,author_id,geo,entities,public_metrics",
            "expansions": "author_id,geo.place_id",
            "user.fields": "username,name",
            "place.fields": "full_name,geo,country_code",
            "start_time": (datetime.now(timezone.utc) - timedelta(hours=6))
                          .strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        async with httpx.AsyncClient() as client:
            data = await self._call(client, params)

        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
        places = {p["id"]: p for p in data.get("includes", {}).get("places", [])}

        for tw in data.get("data", []):
            author = users.get(tw.get("author_id", ""), {})
            entities = tw.get("entities", {})
            mentions = [f"@{m['username']}" for m in entities.get("mentions", [])]

            geo = None
            place_id = tw.get("geo", {}).get("place_id")
            if place_id and place_id in places:
                p = places[place_id]
                geo = {"place": p.get("full_name"), "country": p.get("country_code")}

            yield RawItem(
                item_id=f"x:{tw['id']}",
                platform="x",
                native_id=tw["id"],
                author_hash=_hash_author(author.get("username", "unknown")),
                text=tw.get("text", ""),
                media_urls=[],  # expand with media.fields if needed
                timestamp=datetime.fromisoformat(
                    tw["created_at"].replace("Z", "+00:00")
                ),
                geo_hint=geo,
                tagged_departments=mentions,
                engagement={
                    "likes": tw.get("public_metrics", {}).get("like_count", 0),
                    "comments": tw.get("public_metrics", {}).get("reply_count", 0),
                    "shares": tw.get("public_metrics", {}).get("retweet_count", 0),
                },
                raw=tw,
            )
