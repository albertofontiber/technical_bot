"""Document registry — lookup/insert logic for the `documents` table.

Phase 3 of the document-management refactor. This module sits between the
ingestion pipeline (ingest.py) and the `documents` Supabase table. It is
responsible for:

    1. Computing a content-stable hash of the PDF
    2. Parsing revision metadata (via revision_parser)
    3. Deciding whether this PDF is:
         - NEW (no prior version)             → insert as 'active'
         - DUPLICATE of an existing row       → return existing id
         - NEWER than an existing 'active' row → insert new as 'active',
                                                mark the old as 'superseded'
         - OLDER than an existing 'active' row → insert new as 'superseded'
                                                (we are backfilling history)
         - AMBIGUOUS (dates tie / missing)    → insert as 'needs_review'
    4. Returning the document_id so chunks can be linked to it.

Design notes:
  - Content hash = SHA-256 of the raw PDF file bytes. Stable even if the
    CMS renames the file. A re-compressed PDF will hash differently, which
    is fine — treat as a new revision.
  - Supersede decision is driven by `revision_date` when available. If no
    date is available on either side, we fall back to 'needs_review' rather
    than guessing — a wrong supersede chain is worse than a human follow-up.
  - The `documents` table has `UNIQUE (manufacturer, source_pdf_sha256)`,
    so duplicate detection is guaranteed by the DB even if two pipelines
    race.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .revision_parser import RevisionInfo, parse_revision
from .supabase_client import SupabaseHTTP

logger = logging.getLogger(__name__)


Action = Literal["new", "existing", "superseded_previous", "superseded_self", "needs_review"]


@dataclass
class RegisterResult:
    document_id: str
    action: Action
    revision_info: RevisionInfo
    sha256: str
    supersedes_id: str | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------
def compute_pdf_content_hash(pdf_path: Path) -> str:
    """Return SHA-256 of the raw PDF file bytes.

    This is content-stable — renaming the file does not change the hash.
    A re-compressed/re-generated PDF will hash differently, which is the
    correct behavior (treat as a new revision).
    """
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _fetch_by_hash(
    supabase: SupabaseHTTP, manufacturer: str, sha256: str
) -> dict | None:
    """Return the documents row matching (manufacturer, sha256) or None."""
    url = f"{supabase.url}/rest/v1/documents"
    params = {
        "manufacturer": f"eq.{manufacturer}",
        "source_pdf_sha256": f"eq.{sha256}",
        "select": "*",
        "limit": "1",
    }
    resp = supabase.client.get(url, headers=supabase.headers, params=params)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def _fetch_active_siblings(
    supabase: SupabaseHTTP,
    manufacturer: str,
    document_family: str,
    language: str | None,
) -> list[dict]:
    """Return active docs with same family+language for this manufacturer.

    These are the candidates for supersede comparison.
    """
    url = f"{supabase.url}/rest/v1/documents"
    params = {
        "manufacturer": f"eq.{manufacturer}",
        "document_family": f"eq.{document_family}",
        "status": "eq.active",
        "select": "id,revision,revision_date,source_pdf_filename",
    }
    if language is None:
        params["language"] = "is.null"
    else:
        params["language"] = f"eq.{language}"
    resp = supabase.client.get(url, headers=supabase.headers, params=params)
    resp.raise_for_status()
    return resp.json()


def _insert_document(supabase: SupabaseHTTP, row: dict) -> str:
    """Insert a documents row and return the new id."""
    url = f"{supabase.url}/rest/v1/documents"
    headers = {**supabase.headers, "Prefer": "return=representation"}
    resp = supabase.client.post(url, headers=headers, json=row)
    if resp.status_code == 409:
        # Race: another pipeline just inserted this (manufacturer, sha256)
        existing = _fetch_by_hash(supabase, row["manufacturer"], row["source_pdf_sha256"])
        if existing:
            return existing["id"]
        raise RuntimeError(
            f"409 conflict on insert but no row found for {row['source_pdf_filename']}"
        )
    resp.raise_for_status()
    return resp.json()[0]["id"]


def _mark_superseded(supabase: SupabaseHTTP, old_id: str, new_id: str) -> None:
    """Mark an existing document as superseded by a newer one."""
    url = f"{supabase.url}/rest/v1/documents"
    headers = {**supabase.headers, "Prefer": "return=minimal"}
    params = {"id": f"eq.{old_id}"}
    body = {"status": "superseded", "superseded_by_id": new_id}
    resp = supabase.client.patch(url, headers=headers, params=params, json=body)
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Main decision function
# ---------------------------------------------------------------------------
def register_document(
    supabase: SupabaseHTTP,
    pdf_path: Path,
    manufacturer: str,
    product_model: str | None,
    first_pages_text: str = "",
    dry_run: bool = False,
) -> RegisterResult:
    """Register this PDF in the `documents` table and return its id + action.

    Args:
        supabase: Supabase HTTP client
        pdf_path: Path to the PDF being ingested
        manufacturer: detected manufacturer ('Notifier', 'Detnov', ...)
        product_model: detected product model (may be None)
        first_pages_text: optional text from first ~2 pages for revision fallback
        dry_run: if True, do not write anything. Returns a synthetic id.

    Returns:
        RegisterResult with document_id, action, and the RevisionInfo used.
    """
    sha256 = compute_pdf_content_hash(pdf_path)
    info = parse_revision(pdf_path.name, first_pages_text=first_pages_text)

    if dry_run:
        return RegisterResult(
            document_id="dry-run-id",
            action="new",
            revision_info=info,
            sha256=sha256,
            notes="dry-run",
        )

    # 1. Exact duplicate by content hash?
    existing = _fetch_by_hash(supabase, manufacturer, sha256)
    if existing:
        logger.info(
            f"  document_registry: existing doc found by hash → {existing['id'][:8]}"
        )
        return RegisterResult(
            document_id=existing["id"],
            action="existing",
            revision_info=info,
            sha256=sha256,
        )

    # 2. Look for active siblings (same family + language)
    siblings = _fetch_active_siblings(
        supabase, manufacturer, info.document_family, info.language
    )

    # 3. Build the new row
    new_row = {
        "document_family": info.document_family,
        "revision": info.revision,
        "revision_date": info.revision_date.isoformat() if info.revision_date else None,
        "language": info.language,
        "doc_type": info.doc_type,
        "manufacturer": manufacturer,
        "product_model": product_model,
        "source_pdf_filename": pdf_path.name,
        "source_pdf_sha256": sha256,
        "status": "active",
    }

    if not siblings:
        # 4a. No collision — insert as active
        new_id = _insert_document(supabase, new_row)
        logger.info(f"  document_registry: NEW → {new_id[:8]} ({info.revision or 'no-rev'})")
        return RegisterResult(
            document_id=new_id,
            action="new",
            revision_info=info,
            sha256=sha256,
        )

    # 5. There's a collision — decide supersede direction by date
    decision = _decide_supersede(info, siblings)

    if decision == "newer":
        # Insert new as active, mark siblings as superseded
        new_id = _insert_document(supabase, new_row)
        for sib in siblings:
            _mark_superseded(supabase, sib["id"], new_id)
        logger.info(
            f"  document_registry: NEWER → {new_id[:8]} "
            f"supersedes {len(siblings)} prior active"
        )
        return RegisterResult(
            document_id=new_id,
            action="superseded_previous",
            revision_info=info,
            sha256=sha256,
            supersedes_id=siblings[0]["id"],
            notes=f"Superseded {len(siblings)} prior active doc(s)",
        )

    if decision == "older":
        # Insert new as superseded (we're backfilling an older rev)
        new_row["status"] = "superseded"
        new_row["superseded_by_id"] = siblings[0]["id"]
        new_row["notes"] = "Backfilled older revision; current active is " + siblings[0]["id"]
        new_id = _insert_document(supabase, new_row)
        logger.info(f"  document_registry: OLDER → {new_id[:8]} (inserted as superseded)")
        return RegisterResult(
            document_id=new_id,
            action="superseded_self",
            revision_info=info,
            sha256=sha256,
            supersedes_id=siblings[0]["id"],
        )

    # decision == "ambiguous" — insert as needs_review
    new_row["status"] = "needs_review"
    new_row["notes"] = (
        f"Ambiguous revision vs {len(siblings)} active sibling(s). "
        f"Human must decide supersede chain."
    )
    new_id = _insert_document(supabase, new_row)
    logger.warning(
        f"  document_registry: NEEDS_REVIEW → {new_id[:8]} "
        f"(vs {len(siblings)} sibling(s))"
    )
    return RegisterResult(
        document_id=new_id,
        action="needs_review",
        revision_info=info,
        sha256=sha256,
        notes=new_row["notes"],
    )


def _decide_supersede(
    new_info: RevisionInfo, siblings: list[dict]
) -> Literal["newer", "older", "ambiguous"]:
    """Compare the incoming revision against active siblings and decide.

    Rules:
      1. If BOTH the new doc and ALL siblings have revision_date:
           - new is strictly later than every sibling → "newer"
           - new is strictly earlier than every sibling → "older"
           - otherwise → "ambiguous"
      2. If date is missing on either side → "ambiguous"
    """
    if new_info.revision_date is None:
        return "ambiguous"

    from datetime import date as _date

    sib_dates: list[_date] = []
    for s in siblings:
        rd = s.get("revision_date")
        if not rd:
            return "ambiguous"
        try:
            sib_dates.append(_date.fromisoformat(rd))
        except (ValueError, TypeError):
            return "ambiguous"

    nd = new_info.revision_date
    if all(nd > sd for sd in sib_dates):
        return "newer"
    if all(nd < sd for sd in sib_dates):
        return "older"
    return "ambiguous"
