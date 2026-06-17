#!/usr/bin/env python3
"""corpus_grep.py — busca término(s) en el CONTENIDO de chunks_v2 (TODO el corpus, no solo el
manual objetivo del gold). Para el audit/diagnóstico de CORPUS-GAP: ¿el valor de un hecho está
EN ALGÚN chunk del corpus? Si lo está en OTRO manual (o en el objetivo pero el predicado léxico
lo perdió por es-en/OCR/paráfrasis), entonces NO es un corpus-gap real sino un FN/retrieval-miss.

ILIKE (case-insensitive, NO accent-insensitive → pasa variantes: 'ohm'/'Ω', 'k'/'K'). Un término
por término distintivo (evita comas/paréntesis: rompen el filtro PostgREST). Devuelve por chunk:
source_file, page, product_model + snippet del match.

Uso:
  python scripts/corpus_grep.py "<term>" ["<term2>" ...] [--limit N] [--full]
    --full  imprime el contenido completo del chunk (no solo el snippet).
"""
from __future__ import annotations
import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
CH = f"{SUPABASE_URL}/rest/v1/chunks_v2"


def search(term: str, limit: int = 60) -> list[dict]:
    """ILIKE *term* sobre content. httpx percent-encodea el valor."""
    r = httpx.get(CH, headers=H, params={
        "select": "id,source_file,page_number,product_model,content",
        "content": f"ilike.*{term}*", "limit": str(limit)}, timeout=60)
    r.raise_for_status()
    return r.json()


def snippet(content: str, term: str, width: int = 160) -> str:
    nc = content or ""
    i = nc.lower().find(term.lower())
    if i < 0:
        return " ".join(nc.split())[:width]
    a = max(0, i - width // 2)
    b = min(len(nc), i + len(term) + width // 2)
    return ("…" if a > 0 else "") + " ".join(nc[a:b].split()) + ("…" if b < len(nc) else "")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = sys.argv[1:]
    full = "--full" in args
    limit = 60
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    terms = [a for a in args if not a.startswith("--")]
    if not terms:
        sys.exit("uso: corpus_grep.py \"<term>\" [\"<term2>\" ...] [--limit N] [--full]")
    seen: dict = {}
    for t in terms:
        try:
            rows = search(t, limit)
        except Exception as e:
            print(f"!! término {t!r} falló: {e}")
            continue
        for row in rows:
            rid = row.get("id")
            if rid not in seen:
                seen[rid] = {"sf": row.get("source_file"), "pg": row.get("page_number"),
                             "pm": row.get("product_model"), "term": t,
                             "snip": row.get("content") if full else snippet(row.get("content"), t)}
    rows = list(seen.values())
    print(f"=== corpus_grep {terms} (limit {limit}/término) → {len(rows)} chunks únicos ===\n")
    for r in sorted(rows, key=lambda x: (x["sf"] or "", x["pg"] or 0)):
        print(f"[{r['sf']} · p{r['pg']} · pm={r['pm']}] «{r['term']}»\n    {r['snip']}\n")
    print(f"({len(rows)} chunks únicos sobre {len(terms)} término(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
