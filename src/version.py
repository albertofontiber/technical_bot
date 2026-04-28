"""
Bot version resolution.

Resolves the version identifier for the running bot, used to tag every
query_log row so we can correlate behavior changes with code changes.

Resolution order (first hit wins, cached for the lifetime of the process):
  1. BOT_VERSION env var (explicit override, e.g. tag like "v0.4.1")
  2. RAILWAY_GIT_COMMIT_SHA env var (Railway injects this on deploy)
  3. `git rev-parse --short HEAD` (local dev)
  4. "unknown" (fallback — tooling should treat as missing data)
"""

import os
import subprocess
from functools import lru_cache


@lru_cache(maxsize=1)
def get_bot_version() -> str:
    """Return a short version identifier for this bot process."""
    explicit = os.getenv("BOT_VERSION", "").strip()
    if explicit:
        return explicit

    railway_sha = os.getenv("RAILWAY_GIT_COMMIT_SHA", "").strip()
    if railway_sha:
        return railway_sha[:7]

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            if sha:
                return sha
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "unknown"
