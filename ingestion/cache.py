"""Raw-response cache: every API response is written to disk exactly as received,
before any transformation. One JSON file per request, keyed by endpoint + params."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RAW_DIR = Path(__file__).parent / "raw"


def _key(endpoint: str, params: dict) -> str:
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:16]
    return f"{endpoint.strip('/').replace('/', '_')}_{digest}.json"


def cache_path(endpoint: str, params: dict) -> Path:
    return RAW_DIR / endpoint.strip("/") / _key(endpoint, params)


def load(endpoint: str, params: dict) -> dict | None:
    path = cache_path(endpoint, params)
    if path.exists():
        return json.loads(path.read_text())["response"]
    return None


def save(endpoint: str, params: dict, payload: dict) -> Path:
    path = cache_path(endpoint, params)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"request": {"endpoint": endpoint, "params": params}, "response": payload}))
    return path
