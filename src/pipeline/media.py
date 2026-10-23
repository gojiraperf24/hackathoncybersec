import io
import httpx
from PIL import Image
import imagehash
from minio import Minio
from minio.error import S3Error
from src.config import settings
import structlog

log = structlog.get_logger()

# Reddit's CDN (external-preview.redd.it) rejects requests without a normal
# browser-looking User-Agent. This is the fix for the 403s you were seeing.
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


async def download_image(url: str) -> tuple[bytes, str]:
    """Return (bytes, perceptual_hash). Enforces size limit."""
    if "external-preview.redd.it" in url:
        raise ValueError(f"Hotlink-blocked CDN, skipping: {url}")
    headers = {"User-Agent": _BROWSER_UA, "Accept": "image/*,*/*;q=0.8"}
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=30, headers=headers
    ) as c:
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


# ----- MinIO / S3 -----

def _client() -> Minio:
    s = settings()
    return Minio(
        endpoint=s.s3_endpoint.replace("http://", "").replace("https://", ""),
        access_key=s.s3_access_key,
        secret_key=s.s3_secret_key,
        secure=s.s3_endpoint.startswith("https://"),
        region=s.s3_region,
    )


def ensure_bucket() -> None:
    """Create the media bucket if it doesn't exist. Safe to call every run."""
    s = settings()
    c = _client()
    try:
        if not c.bucket_exists(s.s3_bucket):
            c.make_bucket(s.s3_bucket)
            log.info("bucket_created", bucket=s.s3_bucket)
    except S3Error as e:
        # Server not reachable / bad credentials — fail loud, the run is broken.
        log.error("bucket_check_failed", bucket=s.s3_bucket, error=str(e))
        raise


def upload_to_s3(blob: bytes, key: str, content_type: str = "image/jpeg") -> bool:
    """Upload bytes to MinIO under `key`. Returns True on success."""
    s = settings()
    try:
        _client().put_object(
            bucket_name=s.s3_bucket,
            object_name=key,
            data=io.BytesIO(blob),
            length=len(blob),
            content_type=content_type,
        )
        return True
    except S3Error as e:
        log.warning("s3_upload_failed", key=key, error=str(e))
        return False
