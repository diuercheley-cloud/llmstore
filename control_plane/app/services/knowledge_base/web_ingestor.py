# Owner: agent-platform
import logging
from typing import Any

import requests
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class WebIngestor:
    """
    Scrapes text and metadata from web URLs.
    """

    def __init__(self):
        self.settings = get_settings()

    async def ingest(self, url: str) -> dict[str, Any]:
        """
        Fetches URL content and extracts main text.
        URL ingestion is disabled by default for security.
        """
        if not getattr(self.settings, "kb_url_ingestion_enabled", False):
            raise PermissionError("URL ingestion is disabled by platform policy.")

        try:
            # Mock implementation. In real use, use BeautifulSoup or Trafilatura.
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            text = f"Simulated extracted text from URL: {url}"
            return {"text": text, "metadata": {"url": url, "status_code": response.status_code}}
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {e}")
            raise ValueError(f"Failed to ingest URL: {e}")
