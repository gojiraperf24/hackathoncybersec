import httpx
from bs4 import BeautifulSoup
import structlog

log = structlog.get_logger()

async def scrape_reddit_post(url: str) -> dict:
    """Visits a Reddit post URL and extracts the high-res image and top comments."""
    result = {"full_image": None, "comments": []}
    
    # Reddit blocks default Python requests, so we use a real browser User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # 1. Find the full-resolution image
            # Reddit usually puts the main image in an <img> tag with id="post-image" or inside a specific div
            img_tag = soup.find("img", id="post-image") or soup.find("img", class_="media-image")
            if img_tag and img_tag.get("src"):
                result["full_image"] = img_tag["src"]

            # 2. Find comments (This will get the top few visible comments)
            # Reddit uses <p> tags inside a div with class="md" for comment text
            comment_elements = soup.find_all("div", class_="md")
            for el in comment_elements[:5]: # Just grab top 5 to keep it fast
                text = el.get_text(strip=True)
                if text and len(text) > 10:
                    result["comments"].append(text)

    except Exception as e:
        log.warning("scrape_failed", url=url, error=str(e))

    return result