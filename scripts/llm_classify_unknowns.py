#!/usr/bin/env python3
"""LLM pass: classify unknown-model Notifier PDFs via Claude Sonnet.

Reads the dry-run results JSON, filters files with product_model='unknown',
extracts the first 2 pages of text from each PDF, and asks Claude to identify
the product model from the content. Writes two outputs:

  - _llm_overrides2.json       high-confidence mappings (>=0.7) — ready to paste
                              into NOTIFIER_SOURCE_FILE_TO_MODEL
  - _llm_unknowns_review.json  low-confidence results for manual review

Usage:
    python scripts/llm_classify_unknowns.py Manuales_Notifier_Privado Notifier
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from src.ingestion.pdf_parser import enrich_with_vision, parse_pdf  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

MODEL = "claude-sonnet-4-5"
MAX_CHARS_PER_PAGE = 3000   # cap each page to keep token budget tight
CONF_THRESHOLD = 0.7

PROMPT = """You are classifying a Notifier (Honeywell) fire-alarm product manual.

Below are the first pages of a PDF manual. Identify:
  - product_model: the specific product model designation (e.g. "AM-8200", "SD-851E",
    "ID3000", "NFS-320", "LPB-620"). Use the exact casing/hyphenation from the manual.
    If the manual covers a clear FAMILY (e.g. "400 Series Bases"), return the family name.
    If you cannot determine a specific model with confidence, return "unknown".
  - confidence: 0.0-1.0 on how sure you are.
  - reasoning: one short sentence citing the evidence you used.

Return ONLY valid JSON, no prose:
{"product_model": "...", "confidence": 0.9, "reasoning": "..."}

Filename: {filename}

--- PDF TEXT (first pages) ---
{text}
"""


def extract_text(pdf_path: Path) -> str:
    parsed = parse_pdf(pdf_path)
    # If the document has no extractable text (scanned), force Vision
    total = sum(len((p.full_text or "").strip()) for p in parsed.pages)
    if total < 50 and parsed.pages:
        # Only process first 2 pages via Vision (cost-sensitive)
        first_two = [p.page_number for p in parsed.pages[:2]]
        enrich_with_vision(parsed, page_numbers=first_two)
    pages = parsed.pages[:2] if parsed.pages else []
    chunks = []
    for p in pages:
        t = (p.full_text or p.table_text or p.vision_text or "").strip()
        if t:
            chunks.append(t[:MAX_CHARS_PER_PAGE])
    return "\n\n".join(chunks)


def classify(client: anthropic.Anthropic, filename: str, text: str) -> dict:
    prompt = PROMPT.replace("{filename}", filename).replace("{text}", text or "(no extractable text)")
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    # strip ```json fences if present
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # try to find a json object inside
        import re
        m = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        data = json.loads(m.group(0)) if m else {"product_model": "unknown", "confidence": 0.0, "reasoning": f"parse_error: {raw[:80]}"}
    data["_usage"] = {
        "in": resp.usage.input_tokens,
        "out": resp.usage.output_tokens,
    }
    return data


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python scripts/llm_classify_unknowns.py <dir> <manufacturer>")
        return 2
    folder = ROOT / sys.argv[1]
    mfr = sys.argv[2]
    if mfr != "Notifier":
        print(f"[!] This script currently only targets Notifier overrides, got {mfr}")
        return 2

    use_rescue = "--from-rescue" in sys.argv
    if use_rescue:
        results_path = folder / "_vision_rescue_results.json"
    else:
        results_path = folder / "_dry_run_results.json"
    if not results_path.exists():
        print(f"[!] Missing {results_path}")
        return 2

    dry = json.loads(results_path.read_text(encoding="utf-8"))
    unknowns = [r for r in dry if r.get("product_model") == "unknown"]
    print(f"Unknown PDFs to classify: {len(unknowns)} (source: {results_path.name})")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[!] ANTHROPIC_API_KEY missing in .env")
        return 1
    client = anthropic.Anthropic(api_key=api_key)

    high: dict[str, str] = {}
    low: list[dict] = []
    total_in = total_out = 0
    t0 = time.time()

    for i, r in enumerate(unknowns, 1):
        fname = r["file"]
        pdf_path = folder / fname
        stem = pdf_path.stem
        try:
            text = extract_text(pdf_path)
        except Exception as e:
            low.append({"file": fname, "stem": stem, "error": f"extract:{type(e).__name__}:{e}"})
            print(f"  [{i:3d}/{len(unknowns)}] EXTRACT-ERR {fname}: {e}")
            continue

        if not text.strip():
            low.append({"file": fname, "stem": stem, "product_model": "unknown", "confidence": 0.0, "reasoning": "no text extractable (likely scanned)"})
            print(f"  [{i:3d}/{len(unknowns)}] NO-TEXT {fname}")
            continue

        try:
            data = classify(client, fname, text)
        except Exception as e:
            low.append({"file": fname, "stem": stem, "error": f"llm:{type(e).__name__}:{e}"})
            print(f"  [{i:3d}/{len(unknowns)}] LLM-ERR {fname}: {e}")
            time.sleep(2)
            continue

        pm = data.get("product_model", "unknown")
        conf = float(data.get("confidence", 0.0))
        usage = data.pop("_usage", {})
        total_in += usage.get("in", 0)
        total_out += usage.get("out", 0)

        tag = "OK " if (conf >= CONF_THRESHOLD and pm and pm != "unknown") else "LOW"
        print(f"  [{i:3d}/{len(unknowns)}] {tag} conf={conf:.2f} {str(pm)[:22]:22s}  {fname[:55]}")

        entry = {"file": fname, "stem": stem, **data, "confidence": conf}
        if conf >= CONF_THRESHOLD and pm and pm != "unknown":
            high[stem] = pm
        else:
            low.append(entry)

        if i % 10 == 0:
            # save progress
            (folder / "_llm_overrides2.json").write_text(json.dumps(high, indent=2, ensure_ascii=False), encoding="utf-8")
            (folder / "_llm_unknowns_review.json").write_text(json.dumps(low, indent=2, ensure_ascii=False), encoding="utf-8")

    (folder / "_llm_overrides2.json").write_text(json.dumps(high, indent=2, ensure_ascii=False), encoding="utf-8")
    (folder / "_llm_unknowns_review.json").write_text(json.dumps(low, indent=2, ensure_ascii=False), encoding="utf-8")

    elapsed = time.time() - t0
    # Sonnet 4.5 pricing: $3/MTok in, $15/MTok out
    cost = total_in / 1_000_000 * 3 + total_out / 1_000_000 * 15
    print("\n" + "=" * 70)
    print(f"Classified:           {len(unknowns)}")
    print(f"  High confidence:    {len(high)}  -> _llm_overrides2.json")
    print(f"  Low / review:       {len(low)}   -> _llm_unknowns_review.json")
    print(f"Tokens:  in={total_in:,}  out={total_out:,}")
    print(f"Cost:    ~${cost:.2f}")
    print(f"Elapsed: {elapsed:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
