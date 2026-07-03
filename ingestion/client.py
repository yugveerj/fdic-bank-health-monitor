"""HTTP client for the FDIC BankFind Suite API.

Mechanics verified live 2026-07-03 (see docs/fdic_swagger.yaml):
- pagination is limit/offset where offset counts RECORDS (not pages); max limit 10,000
- responses: {meta: {total, ...}, data: [{data: {...fields}, score}], totals}
- every raw response is cached to ingestion/raw/ before any transformation
"""

from __future__ import annotations

import logging
import time

import httpx

from ingestion import cache
from ingestion.config import BASE_URL

log = logging.getLogger(__name__)

MAX_PAGE_SIZE = 10_000  # documented maximum; 400 above this
PAUSE_SECONDS = 0.4  # no documented rate limit; be polite anyway
USER_AGENT = "fdic-bank-health-monitor (https://github.com/yugveerj/fdic-bank-health-monitor)"


class FdicClient:
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self._http = httpx.Client(
            base_url=BASE_URL, timeout=60, headers={"User-Agent": USER_AGENT}
        )

    def get_json(self, endpoint: str, params: dict) -> dict:
        """One request, cache-first. Retries transient failures with backoff."""
        if self.use_cache:
            cached = cache.load(endpoint, params)
            if cached is not None:
                return cached
        payload = self._request_with_retries(endpoint, params)
        cache.save(endpoint, params, payload)
        return payload

    def _request_with_retries(self, endpoint: str, params: dict, attempts: int = 4) -> dict:
        for attempt in range(attempts):
            try:
                resp = self._http.get(endpoint, params=params)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError(
                        f"retryable status {resp.status_code}", request=resp.request, response=resp
                    )
                resp.raise_for_status()
                time.sleep(PAUSE_SECONDS)
                return resp.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                is_retryable = isinstance(exc, httpx.TransportError) or (
                    exc.response.status_code in (429, 500, 502, 503, 504)
                )
                if not is_retryable or attempt == attempts - 1:
                    raise
                wait = 2**attempt
                log.warning("retrying %s in %ss after %s", endpoint, wait, exc)
                time.sleep(wait)
        raise RuntimeError("unreachable")

    def fetch_all(
        self,
        endpoint: str,
        *,
        fields: list[str],
        filters: str | None = None,
        sort_by: str = "CERT",
        page_size: int = MAX_PAGE_SIZE,
    ) -> list[dict]:
        """All matching rows, paginated. Returns the inner field dicts."""
        rows: list[dict] = []
        offset = 0
        total: int | None = None
        while total is None or len(rows) < total:
            params: dict = {
                "fields": ",".join(fields),
                "sort_by": sort_by,
                "sort_order": "ASC",
                "limit": page_size,
                "offset": offset,
            }
            if filters:
                params["filters"] = filters
            payload = self.get_json(endpoint, params)
            total = payload["meta"]["total"]
            page = [item["data"] for item in payload["data"]]
            if not page and len(rows) < total:
                raise RuntimeError(
                    f"{endpoint}: empty page at offset {offset} but total={total}"
                )
            rows.extend(page)
            offset += page_size
        return rows

    def close(self) -> None:
        self._http.close()
