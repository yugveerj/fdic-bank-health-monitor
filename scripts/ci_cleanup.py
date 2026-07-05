"""Delete the ephemeral ci_* BigQuery datasets a CI run created. Every name
is validated against the ci_ prefix before deletion — this script must be
incapable of touching a real dataset no matter what env it inherits.

Usage: uv run python -m scripts.ci_cleanup ci_raw_123 ci_marts_123 ...
"""

from __future__ import annotations

import logging
import os
import sys

from google.cloud import bigquery

log = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    project = os.environ.get("GCP_PROJECT")
    if not project:
        raise SystemExit("GCP_PROJECT is not set")
    names = sys.argv[1:]
    bad = [n for n in names if not n.startswith("ci_")]
    if bad or not names:
        raise SystemExit(f"refusing: every dataset must start with ci_ (got {names})")
    client = bigquery.Client(project=project)
    try:
        for name in names:
            client.delete_dataset(name, delete_contents=True, not_found_ok=True)
            log.info("deleted %s", name)
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
