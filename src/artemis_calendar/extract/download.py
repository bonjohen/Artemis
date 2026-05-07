"""HTTP download module with metadata capture and retry logic."""

import hashlib
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from artemis_calendar.config.settings import CHECKSUM_ALGORITHM, DOWNLOAD_BACKOFF_SECONDS, DOWNLOAD_MAX_RETRIES


class DownloadError(Exception):
    """Raised when download fails after all retries."""

    def __init__(self, url: str, status_code: int | None, message: str):
        self.url = url
        self.status_code = status_code
        super().__init__(message)


@dataclass
class DownloadResult:
    content: bytes
    status_code: int
    headers: dict[str, str]
    downloaded_at: str
    url: str
    checksum: str = ""

    def compute_checksum(self) -> str:
        self.checksum = hashlib.new(CHECKSUM_ALGORITHM, self.content).hexdigest()
        return self.checksum


def download_artifact(
    url: str,
    max_retries: int = DOWNLOAD_MAX_RETRIES,
    backoff_seconds: float = DOWNLOAD_BACKOFF_SECONDS,
    timeout: float = 120.0,
) -> DownloadResult:
    """Download a URL with retry on transient failures.

    Returns DownloadResult with content, metadata, and UTC timestamp.
    Raises DownloadError after retries exhausted on non-2xx responses.
    """
    last_status = None
    for attempt in range(max_retries + 1):
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
                last_status = response.status_code

                if 200 <= response.status_code < 300:
                    result = DownloadResult(
                        content=response.content,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        downloaded_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        url=url,
                    )
                    result.compute_checksum()
                    return result

                if response.status_code >= 500 and attempt < max_retries:
                    time.sleep(backoff_seconds * (2**attempt))
                    continue

                raise DownloadError(url, response.status_code, f"HTTP {response.status_code} from {url}")

        except httpx.TimeoutException as err:
            if attempt < max_retries:
                time.sleep(backoff_seconds * (2**attempt))
                continue
            raise DownloadError(url, None, f"Timeout downloading {url} after {max_retries + 1} attempts") from err

    raise DownloadError(url, last_status, f"Download failed after {max_retries + 1} attempts: {url}")


def compute_checksum(data: bytes) -> str:
    """Compute SHA-256 hex digest of bytes."""
    return hashlib.new(CHECKSUM_ALGORITHM, data).hexdigest()
