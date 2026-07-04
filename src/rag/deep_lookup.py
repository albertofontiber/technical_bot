"""s95 Piloto D — deep-lookup agéntico para el brazo IDENTITY_FETCH=llm.

Pre-registro: evals/s95_redesign_pilots.md v2. Sustituye el selector LÉXICO del fetch
acotado (NO-OP medido s93/DEC-084 — "los appends llegan, el selector léxico no elige los
chunk-ids juzgados") por un selector LLM: recibe el OUTLINE del doc desde el extraction
store (headings + tablas por página — SIN pre-filtro por keywords de la query [D3]: un
pre-filtro léxico re-introduciría el techo DEC-085) y elige las páginas que contienen el
dato; se appendean los chunks DB de esas páginas (página exacta primero, ±1 después por
el drift store↔DB, orden estable por chunk_index, cap 6/doc, sin re-corte léxico [D4]).

Selector: Haiku 4.5 (barato/rápido; fallback Sonnet declarado en el pre-registro).
Fail-open total (cualquier error → lista vacía, el pipeline sigue).
Instrumentación D-G3: contadores de tokens/llamadas en STATS (los lee el harness).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx

from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

STORE = Path(__file__).resolve().parent.parent.parent / "data" / "extraction" / "agent_anthropic-sonnet-45"
SELECTOR_MODEL = "claude-haiku-4-5"
MAX_PAGES_PER_DOC = 3          # páginas que el selector puede elegir por doc
FETCH_PER_DOC_LLM = 6          # [D4] cap por doc (la ventana ±1 no cabe en los 3 del léxico)
MAX_OUTLINE_CHARS = 48_000     # presupuesto D-G3: <15k tokens input por doc

_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

# instrumentación D-G3 (el harness los resetea/lee)
STATS = {"llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "docs": 0, "errors": 0}

_DOC_CACHE: dict = {}


def _sha_for_doc(source_file: str) -> str | None:
    try:
        with httpx.Client(timeout=5.0) as c:
            r = c.get(f"{SUPABASE_URL}/rest/v1/{os.getenv('CHUNKS_TABLE', 'chunks_v2')}",
                      headers=_H,
                      params={"select": "extraction_sha256",
                              "source_file": f"eq.{source_file}",
                              "extraction_sha256": "not.is.null", "limit": "1"})
            rows = r.json() if r.status_code in (200, 206) else []
        return rows[0]["extraction_sha256"] if rows else None
    except Exception:
        return None


def _store_pages(sha: str) -> list:
    if sha not in _DOC_CACHE:
        p = STORE / f"{sha}.json"
        try:
            d = json.load(open(p, encoding="utf-8")) if p.is_file() else {}
        except Exception:
            d = {}
        r = d.get("result") or {}
        _DOC_CACHE[sha] = r.get("pages", []) if isinstance(r, dict) else (r if isinstance(r, list) else [])
    return _DOC_CACHE[sha]


def _item_text(it: dict) -> str:
    return it.get("md") or it.get("text") or it.get("value") or ""


def build_outline(source_file: str) -> str:
    """Outline completo del doc, una línea por página: headings + tablas (título/1ª fila).
    SIN filtrar por la query [D3] — el recall lo decide el LLM, no un ranker léxico."""
    sha = _sha_for_doc(source_file)
    if not sha:
        return ""
    pages = _store_pages(sha)
    lines: list[str] = []
    for i, page in enumerate(pages):
        parts: list[str] = []
        for it in (page.get("items") or []):
            t = it.get("type")
            if t == "heading":
                txt = _item_text(it).strip().replace("\n", " ")[:90]
                if txt:
                    parts.append(txt)
            elif t == "table":
                rows = it.get("rows") or []
                head = " | ".join(str(x) for x in (rows[0] if rows else [])[:6])[:110]
                parts.append(f"[tabla] {head}" if head else "[tabla]")
        if parts:
            lines.append(f"p.{i + 1}: " + " · ".join(parts))
    out = "\n".join(lines)
    return out[:MAX_OUTLINE_CHARS]


def select_pages_llm(query: str, source_file: str) -> list[int]:
    """Selector LLM: elige ≤MAX_PAGES_PER_DOC páginas del outline que probablemente
    contengan el dato que pide la query. Fail-open → []."""
    outline = build_outline(source_file)
    if not outline:
        return []
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=SELECTOR_MODEL,
            max_tokens=200,
            temperature=0,
            messages=[{"role": "user", "content": (
                "Eres el localizador de páginas de un buscador técnico de manuales de "
                "protección contra incendios. PREGUNTA del técnico:\n"
                f"{query}\n\n"
                f"ÍNDICE por páginas del manual «{source_file}» (headings y tablas):\n"
                f"{outline}\n\n"
                f"Devuelve SOLO un JSON con las páginas (máx {MAX_PAGES_PER_DOC}) que con "
                "más probabilidad contienen el DATO CONCRETO que responde la pregunta "
                "(specs, bornes, códigos, rangos, procedimientos). Razona la tarea del "
                "técnico, no solo palabras de la pregunta (p.ej. cambiar batería sin perder "
                "config → alimentación redundante + tipo de memoria). "
                'Formato: {"pages": [n, ...]}')}],
        )
        STATS["llm_calls"] += 1
        STATS["input_tokens"] += msg.usage.input_tokens
        STATS["output_tokens"] += msg.usage.output_tokens
        text = "".join(getattr(b, "text", "") for b in msg.content
                       if getattr(b, "type", "") == "text")
        m = re.search(r"\{.*\}", text, re.DOTALL)
        pages = json.loads(m.group(0)).get("pages", []) if m else []
        return [int(p) for p in pages][:MAX_PAGES_PER_DOC]
    except Exception:
        STATS["errors"] += 1
        return []


def fetch_pages_chunks(source_file: str, pages: list[int]) -> list[dict]:
    """[D4] Chunks DB de las páginas elegidas: página EXACTA primero, ±1 después,
    orden estable por chunk_index, cap FETCH_PER_DOC_LLM, SIN re-corte léxico.
    parent_id=is.null (invariante de no-servicio: jamás surrogates por este path)."""
    if not pages:
        return []
    exact = sorted(set(int(p) for p in pages))
    window = sorted({q for p in exact for q in (p - 1, p + 1)} - set(exact))
    out: list[dict] = []
    try:
        with httpx.Client(timeout=5.0) as c:
            for group in (exact, window):
                if not group or len(out) >= FETCH_PER_DOC_LLM:
                    continue
                r = c.get(f"{SUPABASE_URL}/rest/v1/{os.getenv('CHUNKS_TABLE', 'chunks_v2')}",
                          headers=_H,
                          params={"select": "id,content,source_file,product_model,"
                                            "page_number,language,chunk_index",
                                  "source_file": f"eq.{source_file}",
                                  "page_number": f"in.({','.join(map(str, group))})",
                                  "parent_id": "is.null",
                                  "order": "page_number.asc,chunk_index.asc"})
                if r.status_code not in (200, 206):
                    continue
                for row in r.json():
                    if len(out) >= FETCH_PER_DOC_LLM:
                        break
                    row["identity_fetch"] = "llm"
                    out.append(row)
    except Exception:
        STATS["errors"] += 1
    return out


def deep_lookup(query: str, source_file: str) -> list[dict]:
    """Camino completo por doc: outline → selector LLM → chunks de las páginas."""
    STATS["docs"] += 1
    return fetch_pages_chunks(source_file, select_pages_llm(query, source_file))
