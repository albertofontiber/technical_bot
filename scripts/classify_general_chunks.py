#!/usr/bin/env python3
"""Classify documents currently in category='General' using Claude Sonnet.

For each unique source_file with General chunks, fetches a sample of its
chunks (up to 3, prefering middle-of-document content) and asks Claude
to classify it into one of the unified taxonomy categories.

Output: JSON file at logs/general_classification_proposal.json with
    [{source_file, manufacturer, product_model, current_category,
      proposed_category, confidence, reasoning, n_chunks}, ...]

Human review required before applying. To apply, see:
    scripts/apply_general_classification.py (Script B, written after review)

Usage:
    python scripts/classify_general_chunks.py             # dry run, default
    python scripts/classify_general_chunks.py --limit 5   # only first 5 files (for quick test)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

from anthropic import Anthropic  # noqa: E402
from src.ingestion.supabase_client import get_supabase  # noqa: E402

MODEL = "claude-sonnet-4-6"  # match bot's main LLM (src/config.py LLM_MODEL)

# Closed list of valid categories — must match _CATEGORY_KEYWORDS in chunker.py
VALID_CATEGORIES = [
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
    "General",  # explicit fallback if even Claude can't decide
]

CATEGORY_GUIDANCE = """\
Each category covers:
- Centrales de incendios: control panels — fire alarm panels AND gas detection panels (e.g. PL4, AM-8200G), repeaters, networked panels, GSM/IP transmitters tied to a panel. (We treat "central" broadly: any control unit for detection systems, whether fire or gas.)
- Detectores puntuales: smoke/heat/CO/gas point detectors (NOT linear, NOT aspirating)
- Detectores lineales: beam detectors, linear heat detection, flame detectors at distance
- Detectores de aspiración: VESDA, FAAST, ICAM, aspiration smoke detection
- Pulsadores: manual call points, pull stations
- Sirenas y balizas: sounders, beacons, voice evacuation speakers, horns, strobes
- Módulos de lazo: loop modules (input/output/relay/monitor), isolators, addressable interface modules
- Fuentes de alimentación: power supplies, battery chargers, PSUs
- Sistemas de extinción: clean agent, sprinkler, suppression release controls
- Software y programación: configuration tools, programming software, technical guides for software
- Accesorios y cableado: sockets, mounting plates, test equipment, diagnostic tools, cabling, remote indicators
- General: ONLY if you genuinely cannot determine from the content (avoid this)
"""


def fetch_general_files(supabase) -> list[dict]:
    """Get the list of (source_file, manufacturer, product_model) tuples
    for every document where ALL chunks are category='General'."""
    url = f"{supabase.url}/rest/v1/chunks"
    out: dict[str, dict] = {}
    offset = 0
    while True:
        params = {
            "select": "source_file,manufacturer,product_model",
            "category": "eq.General",
            "limit": "1000",
            "offset": str(offset),
            "order": "id",
        }
        resp = supabase.client.get(url, headers=supabase.headers, params=params)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        for r in rows:
            sf = r["source_file"]
            if sf not in out:
                out[sf] = {
                    "source_file": sf,
                    "manufacturer": r.get("manufacturer"),
                    "product_model": r.get("product_model"),
                }
        if len(rows) < 1000:
            break
        offset += 1000
    return list(out.values())


def fetch_sample_chunks(supabase, source_file: str, n: int = 3) -> list[str]:
    """Fetch up to n chunks for this source_file, prioritizing middle-of-doc.

    Skips very short chunks (<100 chars). Returns chunk texts truncated
    at 1500 chars each to keep prompt size reasonable.
    """
    url = f"{supabase.url}/rest/v1/chunks"
    params = {
        "select": "content,page_number",
        "source_file": f"eq.{source_file}",
        "order": "page_number.asc",
        "limit": "30",  # fetch a window, we'll pick the best n
    }
    resp = supabase.client.get(url, headers=supabase.headers, params=params)
    resp.raise_for_status()
    rows = resp.json()
    # Filter usable chunks
    usable = [r for r in rows if r.get("content") and len(r["content"]) >= 100]
    if not usable:
        # Fall back to any chunks
        usable = [r for r in rows if r.get("content")]
    if not usable:
        return []
    # Pick: first chunk + middle chunk + last (capped at n)
    if len(usable) >= n:
        idxs = [0, len(usable) // 2, len(usable) - 1][:n]
    else:
        idxs = list(range(len(usable)))
    samples = [usable[i]["content"][:1500] for i in idxs]
    return samples


def classify_with_claude(client: Anthropic, source_file: str, manufacturer: str,
                         product_model: str, samples: list[str]) -> dict:
    """Ask Claude Sonnet to classify the document. Returns dict with
    category, confidence ('high'|'medium'|'low'), and reasoning."""
    samples_block = "\n\n---\n\n".join(
        f"[Chunk {i+1}]\n{s}" for i, s in enumerate(samples)
    ) if samples else "(no usable content samples)"

    prompt = f"""You are classifying a fire-protection (PCI) product document into a fixed taxonomy.

Document metadata:
- Filename: {source_file}
- Manufacturer: {manufacturer}
- Detected product model: {product_model or "unknown"}

Content samples from the document:
{samples_block}

Valid categories (you MUST pick exactly one):
{chr(10).join(f"  - {c}" for c in VALID_CATEGORIES)}

{CATEGORY_GUIDANCE}

Respond in this exact JSON format (no other text, no markdown fence):
{{"category": "<one of the valid categories>", "confidence": "<high|medium|low>", "reasoning": "<one sentence>"}}
"""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    # Strip markdown fence if Claude added it
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return {"category": "General", "confidence": "low",
                "reasoning": f"Parse error: {e}. Raw: {text[:200]}"}
    # Validate category
    if data.get("category") not in VALID_CATEGORIES:
        data["confidence"] = "low"
        data["reasoning"] = f"Invalid category '{data.get('category')}' returned. " + data.get("reasoning", "")
        data["category"] = "General"
    return data


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None,
                   help="Only process first N files (for quick test)")
    p.add_argument("--output", type=str,
                   default="logs/general_classification_proposal.json",
                   help="Output JSON path")
    args = p.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        return 1

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    supabase = get_supabase()
    client = Anthropic()

    print(f"Model: {MODEL}")
    print(f"Output: {output_path}")
    print()
    print("Fetching files with category='General'...")
    files = fetch_general_files(supabase)
    print(f"  {len(files)} unique source_files")
    if args.limit:
        files = files[: args.limit]
        print(f"  --limit {args.limit}: processing first {len(files)} only")
    print()

    results = []
    t_start = time.time()
    for i, f in enumerate(files, 1):
        sf = f["source_file"]
        mfr = f["manufacturer"] or "unknown"
        model = f["product_model"] or "unknown"

        print(f"[{i}/{len(files)}] {sf[:55]:55s} mfr={mfr:<10s} model={model[:20]:20s} ", end="", flush=True)

        try:
            samples = fetch_sample_chunks(supabase, sf, n=3)
            if not samples:
                print("→ NO SAMPLES, skipping")
                results.append({
                    "source_file": sf, "manufacturer": mfr, "product_model": model,
                    "current_category": "General",
                    "proposed_category": "General",
                    "confidence": "low",
                    "reasoning": "no usable content samples in DB",
                    "n_samples": 0,
                })
                continue

            decision = classify_with_claude(client, sf, mfr, model, samples)
            print(f"→ {decision['category']:<28s} ({decision['confidence']})")
            results.append({
                "source_file": sf,
                "manufacturer": mfr,
                "product_model": model,
                "current_category": "General",
                "proposed_category": decision["category"],
                "confidence": decision["confidence"],
                "reasoning": decision["reasoning"],
                "n_samples": len(samples),
            })
        except Exception as e:
            print(f"→ ERROR {type(e).__name__}: {e}")
            results.append({
                "source_file": sf, "manufacturer": mfr, "product_model": model,
                "current_category": "General",
                "proposed_category": "General",
                "confidence": "low",
                "reasoning": f"exception: {type(e).__name__}: {e}",
                "n_samples": 0,
            })

    elapsed = time.time() - t_start
    print()
    print(f"Done in {elapsed:.1f}s")

    # Write JSON
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    print(f"Written: {output_path}")
    print()

    # Summary
    by_cat: dict[str, int] = {}
    by_conf: dict[str, int] = {}
    for r in results:
        by_cat[r["proposed_category"]] = by_cat.get(r["proposed_category"], 0) + 1
        by_conf[r["confidence"]] = by_conf.get(r["confidence"], 0) + 1

    print("Proposed categories:")
    for c, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {c:<30s} {n:>3d}")
    print()
    print("Confidence distribution:")
    for c, n in sorted(by_conf.items(), key=lambda x: -x[1]):
        print(f"  {c:<10s} {n:>3d}")
    print()
    print(f"Next step: review {output_path.relative_to(ROOT)} and approve/correct.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
