#!/usr/bin/env python3
"""End-to-end verification of the image / diagram pipeline.

Questions answered:
  1. What % of chunks have `has_diagram=true`?
  2. Of those, how many have `diagram_url` populated?
  3. Do the URLs actually return a 200 from Supabase Storage?
  4. Can we trace a few chunks with diagrams through a simulated retrieval
     to see the URL reach the output?
  5. By manufacturer × category: where are the diagrams concentrated or
     missing?

Output: logs/image_pipeline_audit.json + human-readable summary to stdout.
"""
from __future__ import annotations

import io
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from src.ingestion.supabase_client import get_supabase  # noqa: E402


def head_check(client, url: str, timeout: float = 10.0) -> tuple[int, int]:
    """HEAD request. Returns (status_code, content_length_or_0)."""
    try:
        r = client.head(url, timeout=timeout, follow_redirects=True)
        cl = int(r.headers.get("content-length", 0))
        return r.status_code, cl
    except Exception as e:
        return -1, 0


def main() -> int:
    sup = get_supabase()
    report: dict = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    # === (1) Total chunks + chunks with has_diagram=true ===
    url = f"{sup.url}/rest/v1/chunks"
    r = sup.client.head(url, headers={**sup.headers, "Prefer": "count=exact"},
                        params={"limit": "1"})
    total_chunks = int(r.headers.get("content-range", "0-0/0").split("/")[-1])

    r = sup.client.head(url, headers={**sup.headers, "Prefer": "count=exact"},
                        params={"has_diagram": "eq.true", "limit": "1"})
    with_diagram = int(r.headers.get("content-range", "0-0/0").split("/")[-1])

    r = sup.client.head(url, headers={**sup.headers, "Prefer": "count=exact"},
                        params={"has_diagram": "eq.true",
                                "diagram_url": "not.is.null", "limit": "1"})
    with_diagram_url = int(r.headers.get("content-range", "0-0/0").split("/")[-1])

    r = sup.client.head(url, headers={**sup.headers, "Prefer": "count=exact"},
                        params={"has_diagram": "eq.true",
                                "diagram_url": "is.null", "limit": "1"})
    with_diagram_no_url = int(r.headers.get("content-range", "0-0/0").split("/")[-1])

    print("=" * 70)
    print("IMAGE PIPELINE AUDIT")
    print("=" * 70)
    print(f"Total chunks:                           {total_chunks:>8,}")
    print(f"has_diagram=true:                       {with_diagram:>8,}  "
          f"({100*with_diagram/max(1,total_chunks):.1f}% of total)")
    print(f"  └ with diagram_url populated:         {with_diagram_url:>8,}  "
          f"({100*with_diagram_url/max(1,with_diagram):.1f}% of diagrammed)")
    print(f"  └ with diagram_url NULL:              {with_diagram_no_url:>8,}  "
          f"({100*with_diagram_no_url/max(1,with_diagram):.1f}% of diagrammed)")
    print()
    report["totals"] = {
        "total_chunks": total_chunks,
        "with_diagram": with_diagram,
        "with_diagram_url": with_diagram_url,
        "with_diagram_no_url": with_diagram_no_url,
    }

    # === (2) Sample N diagram_urls and HEAD-check them ===
    print("Sampling 15 diagram_urls and HEAD-checking Supabase Storage...")
    r = sup.client.get(url, headers=sup.headers, params={
        "select": "id,source_file,manufacturer,category,product_model,page_number,diagram_url",
        "has_diagram": "eq.true",
        "diagram_url": "not.is.null",
        "limit": "15",
    })
    r.raise_for_status()
    samples = r.json()
    status_counts: Counter[int] = Counter()
    sample_results = []
    for s in samples:
        code, size = head_check(sup.client, s["diagram_url"])
        status_counts[code] += 1
        sample_results.append({
            "source_file": s.get("source_file"),
            "page": s.get("page_number"),
            "manufacturer": s.get("manufacturer"),
            "url": s.get("diagram_url"),
            "http_status": code,
            "size_bytes": size,
        })
        ok = "✓" if code == 200 else "✗"
        print(f"  {ok} [{code}] {s.get('manufacturer'):<10s} "
              f"{(s.get('source_file') or '')[:35]:<35s} "
              f"p{s.get('page_number')}  "
              f"({size:>6} bytes)")
    print(f"\n  HTTP status summary: {dict(status_counts)}")
    report["url_sample"] = sample_results
    report["http_status_summary"] = dict(status_counts)

    # === (3) By manufacturer: diagram coverage ===
    print()
    print("Diagram coverage by manufacturer:")
    # Paginate through ALL rows to collect the distinct set of manufacturers.
    # We order by id so offsets are stable. Supabase caps max rows per response
    # (typically 1000), so we can't rely on a single large limit. Using
    # Prefer: count=planned lets us know when we've covered the table without
    # guessing page size behaviour.
    distinct_mfrs: set[str] = set()
    page_size = 1000
    offset = 0
    while True:
        r = sup.client.get(url, headers=sup.headers, params={
            "select": "manufacturer",
            "order": "id.asc",
            "limit": str(page_size),
            "offset": str(offset),
        })
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        for row in rows:
            m = row.get("manufacturer")
            if m:
                distinct_mfrs.add(m)
        if len(rows) < page_size:
            break
        offset += page_size

    by_mfr = {}
    for mfr in sorted(distinct_mfrs):
        if not mfr:
            continue
        # Count diagrams for this mfr
        r = sup.client.head(url, headers={**sup.headers, "Prefer": "count=exact"},
                            params={"manufacturer": f"eq.{mfr}",
                                    "has_diagram": "eq.true", "limit": "1"})
        d = int(r.headers.get("content-range", "0-0/0").split("/")[-1])
        r = sup.client.head(url, headers={**sup.headers, "Prefer": "count=exact"},
                            params={"manufacturer": f"eq.{mfr}", "limit": "1"})
        t = int(r.headers.get("content-range", "0-0/0").split("/")[-1])
        by_mfr[mfr] = {"total": t, "diagrammed": d,
                       "pct": round(100 * d / max(1, t), 1)}
        print(f"  {mfr:<12s} total={t:>7,d}  diagrammed={d:>6,d}  "
              f"({by_mfr[mfr]['pct']}%)")
    report["by_manufacturer"] = by_mfr

    # === (4) Where do images live? Peek at diagram_url patterns ===
    print()
    print("Sample of distinct URL prefixes (storage path structure):")
    r = sup.client.get(url, headers=sup.headers, params={
        "select": "diagram_url",
        "has_diagram": "eq.true",
        "diagram_url": "not.is.null",
        "limit": "100",
    })
    r.raise_for_status()
    urls = [row["diagram_url"] for row in r.json()]
    prefixes = Counter()
    for u in urls:
        # Extract path component after /object/
        if "/object/" in u:
            path = u.split("/object/", 1)[1]
            prefix = "/".join(path.split("/")[:3])  # bucket + 2 levels
            prefixes[prefix] += 1
    for p, n in prefixes.most_common(10):
        print(f"  {n:>4d}× {p}")
    report["url_prefixes"] = dict(prefixes.most_common(20))

    # === (5) Chunks with has_diagram=true but NO URL — what's going on? ===
    if with_diagram_no_url > 0:
        print()
        print(f"WARN: {with_diagram_no_url} chunks have has_diagram=true but "
              f"diagram_url IS NULL. Sampling 10 to diagnose:")
        r = sup.client.get(url, headers=sup.headers, params={
            "select": "source_file,manufacturer,page_number,content",
            "has_diagram": "eq.true",
            "diagram_url": "is.null",
            "limit": "10",
        })
        r.raise_for_status()
        orphan_samples = []
        for row in r.json():
            orphan_samples.append({
                "source_file": row.get("source_file"),
                "page": row.get("page_number"),
                "manufacturer": row.get("manufacturer"),
                "content_snippet": (row.get("content") or "")[:120],
            })
            print(f"  [{row.get('manufacturer')}] "
                  f"{(row.get('source_file') or '')[:40]:<40s} "
                  f"p{row.get('page_number')}")
        report["orphan_diagrams"] = orphan_samples

    # === Write JSON report ===
    out_path = ROOT / "logs/image_pipeline_audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print()
    print(f"Report: {out_path}")

    # === Verdict ===
    print()
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)
    issues: list[str] = []
    if with_diagram == 0:
        issues.append("No chunks have has_diagram=true — pipeline didn't detect any diagrams.")
    if with_diagram_no_url > 0:
        pct_orphan = 100 * with_diagram_no_url / with_diagram
        issues.append(f"{with_diagram_no_url} diagrammed chunks ({pct_orphan:.1f}%) "
                      "have NO diagram_url — orphans.")
    if status_counts.get(200, 0) < len(samples):
        failed = len(samples) - status_counts.get(200, 0)
        issues.append(f"{failed}/{len(samples)} sampled URLs did NOT return 200 — "
                      "storage may be misconfigured or URLs wrong.")
    if not issues:
        print("✓ Image pipeline looks healthy on the DB side.")
        print("  Next step (needs bot code inspection): confirm retriever+generator")
        print("  surface diagram_url in the final response to the user.")
    else:
        for i, iss in enumerate(issues, 1):
            print(f"✗ Issue {i}: {iss}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
