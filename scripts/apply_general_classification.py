#!/usr/bin/env python3
"""Apply the reviewed proposal from logs/general_classification_proposal.json
to the `chunks` table.

Safety:
  - Dry-run by default. Must pass --apply to actually UPDATE.
  - Writes a rollback file (logs/general_classification_rollback_<ts>.json) BEFORE
    any UPDATE, containing the exact (chunk_id, original_category) pairs needed
    to revert.
  - Idempotent: only touches rows where category='General' AND source_file matches.
    Running twice is a no-op on the second run.
  - Skips rows where proposed_category == 'General' (would be a no-op anyway).

Valid categories are asserted against chunker.py's _CATEGORY_KEYWORDS to catch
any typo in the proposal JSON before hitting the DB.

Usage:
    python scripts/apply_general_classification.py              # dry run
    python scripts/apply_general_classification.py --apply      # execute
    python scripts/apply_general_classification.py --input <path>  # custom proposal file
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from src.ingestion.supabase_client import get_supabase  # noqa: E402

# Mirror of _CATEGORY_KEYWORDS keys in src/ingestion/chunker.py.
# Keep this in sync if the taxonomy changes.
VALID_CATEGORIES = {
    "Centrales de incendios",
    "Detectores puntuales",
    "Detectores lineales",
    "Detectores de aspiración",
    "Pulsadores",
    "Sirenas y balizas",
    "Módulos de lazo",
    "Fuentes de alimentación",
    "Sistemas de extinción",
    "Software y programación",
    "Accesorios y cableado",
    "General",  # allowed as no-op target
}


def load_proposal(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    # Sanity-validate schema
    required = {"source_file", "current_category", "proposed_category"}
    for i, r in enumerate(data):
        missing = required - r.keys()
        if missing:
            raise ValueError(f"Row {i} missing keys: {missing}. source_file={r.get('source_file')}")
        if r["proposed_category"] not in VALID_CATEGORIES:
            raise ValueError(
                f"Row {i} ({r['source_file']}): invalid proposed_category "
                f"'{r['proposed_category']}'. Valid: {sorted(VALID_CATEGORIES)}"
            )
    return data


def fetch_chunks_for_file(sup, source_file: str) -> list[dict]:
    """Fetch only chunks currently in General for this source_file.
    Returns list of {id, category}."""
    url = f"{sup.url}/rest/v1/chunks"
    params = {
        "select": "id,category",
        "source_file": f"eq.{source_file}",
        "category": "eq.General",
        "limit": "10000",  # any single doc is much smaller
    }
    resp = sup.client.get(url, headers=sup.headers, params=params)
    resp.raise_for_status()
    return resp.json()


_RETRY_STATUSES = {500, 502, 503, 504}
_RETRY_MAX_ATTEMPTS = 4
_RETRY_BASE_DELAY = 2.0  # seconds, doubled each attempt


def update_chunks_category(sup, source_file: str, new_category: str) -> int:
    """UPDATE chunks SET category=$new WHERE source_file=$sf AND category='General'.
    Returns number of rows affected (via Prefer: return=representation).

    Retries on transient 5xx responses with exponential backoff.
    """
    url = f"{sup.url}/rest/v1/chunks"
    params = {
        "source_file": f"eq.{source_file}",
        "category": "eq.General",
    }
    headers = {**sup.headers, "Prefer": "return=representation"}

    last_exc: Exception | None = None
    for attempt in range(_RETRY_MAX_ATTEMPTS):
        try:
            resp = sup.client.patch(url, headers=headers, params=params,
                                    json={"category": new_category})
            if resp.status_code in _RETRY_STATUSES:
                last_exc = RuntimeError(
                    f"{resp.status_code} from PATCH {source_file}: {resp.text[:200]}"
                )
                if attempt < _RETRY_MAX_ATTEMPTS - 1:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    print(f"    retry {attempt+1}/{_RETRY_MAX_ATTEMPTS-1} after "
                          f"{resp.status_code} ({delay}s)...")
                    time.sleep(delay)
                    continue
                raise last_exc
            resp.raise_for_status()
            return len(resp.json())
        except Exception as e:
            # Only retry transient network errors; re-raise others immediately
            import httpx
            if isinstance(e, (httpx.TransportError, httpx.TimeoutException)):
                last_exc = e
                if attempt < _RETRY_MAX_ATTEMPTS - 1:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    print(f"    retry {attempt+1}/{_RETRY_MAX_ATTEMPTS-1} after "
                          f"{type(e).__name__} ({delay}s)...")
                    time.sleep(delay)
                    continue
            raise
    # Shouldn't reach here — the loop either returns or raises
    raise last_exc or RuntimeError("exhausted retries")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="logs/general_classification_proposal.json",
                    help="Proposal JSON path")
    ap.add_argument("--apply", action="store_true",
                    help="Actually execute UPDATEs. Without this, dry run only.")
    args = ap.parse_args()

    proposal_path = ROOT / args.input
    if not proposal_path.exists():
        print(f"ERROR: proposal file not found: {proposal_path}")
        return 1

    proposal = load_proposal(proposal_path)
    print(f"Loaded {len(proposal)} rows from {proposal_path}")
    print(f"Mode: {'APPLY (will UPDATE)' if args.apply else 'DRY-RUN (no writes)'}")
    print()

    sup = get_supabase()

    # Build plan
    plan = []
    skipped_noop = 0
    for r in proposal:
        sf = r["source_file"]
        new_cat = r["proposed_category"]
        if new_cat == "General":
            skipped_noop += 1
            continue
        plan.append(r)

    # Show plan summary
    by_cat: dict[str, int] = {}
    for r in plan:
        by_cat[r["proposed_category"]] = by_cat.get(r["proposed_category"], 0) + 1
    print(f"Will migrate {len(plan)} source_files out of General:")
    for c, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {c:<30s} {n:>3d}")
    print(f"  (skipped {skipped_noop} row(s) with proposed='General')")
    print()

    # Build rollback snapshot (fetch current IDs + categories BEFORE any change)
    rollback: list[dict] = []
    total_chunks = 0
    missing_files: list[str] = []
    print("Fetching current chunk IDs for rollback snapshot...")
    t0 = time.time()
    for i, r in enumerate(plan, 1):
        sf = r["source_file"]
        chunks = fetch_chunks_for_file(sup, sf)
        if not chunks:
            missing_files.append(sf)
            continue
        total_chunks += len(chunks)
        rollback.append({
            "source_file": sf,
            "new_category": r["proposed_category"],
            "chunks": [{"id": c["id"], "original_category": c["category"]} for c in chunks],
        })
        if i % 10 == 0 or i == len(plan):
            print(f"  [{i}/{len(plan)}] snapshot built, {total_chunks} chunks so far")

    print(f"Snapshot done in {time.time()-t0:.1f}s: {total_chunks} chunks across "
          f"{len(rollback)} files will be updated.")
    if missing_files:
        print(f"  WARN: {len(missing_files)} source_file(s) had no chunks in General "
              "(already applied, or typo). Will skip:")
        for sf in missing_files[:10]:
            print(f"    - {sf}")
        if len(missing_files) > 10:
            print(f"    ... and {len(missing_files)-10} more")
    print()

    if not args.apply:
        print("DRY-RUN: no writes performed. Re-run with --apply to execute.")
        return 0

    # Write rollback file BEFORE touching anything
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rollback_path = ROOT / f"logs/general_classification_rollback_{ts}.json"
    rollback_path.parent.mkdir(parents=True, exist_ok=True)
    rollback_path.write_text(
        json.dumps({"timestamp_utc": ts, "total_chunks": total_chunks,
                    "entries": rollback}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Rollback snapshot written: {rollback_path.name}")
    print()

    # Apply updates
    print("Applying UPDATEs...")
    t0 = time.time()
    total_updated = 0
    errors: list[tuple[str, str]] = []
    for i, r in enumerate(plan, 1):
        sf = r["source_file"]
        new_cat = r["proposed_category"]
        try:
            n = update_chunks_category(sup, sf, new_cat)
            total_updated += n
            if i % 10 == 0 or i == len(plan):
                print(f"  [{i}/{len(plan)}] {sf[:40]:40s} -> {new_cat:<28s} ({n} chunks)")
        except Exception as e:
            errors.append((sf, f"{type(e).__name__}: {e}"))
            print(f"  [{i}/{len(plan)}] {sf} FAILED: {type(e).__name__}: {e}")

    elapsed = time.time() - t0
    print()
    print(f"Done in {elapsed:.1f}s. Updated {total_updated} chunks across "
          f"{len(plan)-len(errors)}/{len(plan)} files.")
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for sf, msg in errors:
            print(f"  - {sf}: {msg}")
        print()
        print(f"To rollback successful updates, use: {rollback_path.name}")
        return 1
    print()
    print("All good. Verify with:")
    print("  SELECT category, COUNT(*) FROM chunks GROUP BY category ORDER BY 2 DESC;")
    return 0


if __name__ == "__main__":
    sys.exit(main())
