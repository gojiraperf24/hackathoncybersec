import io
import httpx
from PIL import Image
import imagehash
from src.config import settings


async def download_image(url: str) -> tuple[bytes, str]:
    """Return (bytes, perceptual_hash). Enforces size limit."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as c:
        async with c.stream("GET", url) as r:
            r.raise_for_status()
            buf = bytearray()
            async for chunk in r.aiter_bytes():
                buf.extend(chunk)
                if len(buf) > settings().max_media_bytes:
                    raise ValueError(f"Media exceeds limit: {url}")
    try:
        img = Image.open(io.BytesIO(buf)).convert("RGB")
        phash = str(imagehash.phash(img))
    except Exception:
        phash = ""
    return bytes(buf), phash
