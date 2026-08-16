# -*- coding: utf-8 -*-
"""s324 — helpers compartidos por los constructores de planes (lectura de Supabase + verificación
full-text). Solo lectura. Extraídos de s324_lote_firmado_plan.py para los lotes siguientes."""
from __future__ import annotations
import os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
_docs: dict[str, dict | None] = {}
_text: dict[str, str] = {}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def doc(c, nombre: str) -> dict | None:
    """Fila de `documents` por source_pdf_filename (exacto; si no, ilike prefijo entre activos)."""
    if nombre in _docs:
        return _docs[nombre]
    sel = "id,source_pdf_filename,status,product_model,manufacturer"
    r = c.get(f"{SB}/rest/v1/documents", headers=HS, params={"select": sel, "source_pdf_filename": f"eq.{nombre}"})
    r.raise_for_status(); rows = r.json()
    if len(rows) != 1:
        r = c.get(f"{SB}/rest/v1/documents", headers=HS, params={"select": sel, "source_pdf_filename": f"ilike.{nombre}*"})
        rows = [x for x in r.json() if x["status"] == "active"] if r.status_code == 200 else []
    _docs[nombre] = rows[0] if len(rows) == 1 else None
    return _docs[nombre]


def texto(c, doc_id: str) -> str:
    """Texto COMPLETO del documento (todos sus chunks, espacios normalizados)."""
    if doc_id in _text:
        return _text[doc_id]
    out, off = [], 0
    while True:
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "chunk_index,content", "document_id": f"eq.{doc_id}",
                          "order": "chunk_index.asc", "offset": str(off), "limit": "500"})
        r.raise_for_status(); rows = r.json()
        out += [x["content"] or "" for x in rows]
        if len(rows) < 500:
            break
        off += 500
    _text[doc_id] = norm(" ".join(out))
    return _text[doc_id]


def n_token(txt: str, tok: str) -> int:
    rx = re.compile(r"(?<![A-Za-z0-9-])" + re.escape(tok) + r"(?![A-Za-z0-9-])", re.I)
    return len(rx.findall(txt))


def cita_ok(txt: str, cita: str) -> bool:
    c = norm(cita).strip("«»\" ")
    return bool(c) and c[:200] in txt


def ventana(txt: str, tok: str, ancho: int = 90) -> str:
    """Cita verbatim (≤200 chars) alrededor del token exacto: la ventana con MÁS letras (evita
    separadores de tabla) recortada a límites de palabra."""
    rx = re.compile(r"(?<![A-Za-z0-9-])" + re.escape(tok) + r"(?![A-Za-z0-9-])", re.I)
    mejor, mejor_score = "", -1.0
    for m in rx.finditer(txt):
        a, b = max(0, m.start() - ancho), min(len(txt), m.end() + ancho)
        w = txt[a:b]
        score = sum(ch.isalpha() for ch in w) / max(1, len(w)) + (0.3 if "#" in w[:ancho] else 0.0)
        if score > mejor_score:
            mejor, mejor_score = w, score
    if not mejor:
        return ""
    mejor = re.sub(r"^\S*\s", "", mejor, count=1) if not mejor.startswith(("#", "*")) else mejor
    mejor = re.sub(r"\s\S*$", "", mejor, count=1)
    return mejor[:200]


def consultas_reales(c, limite: int = 5000) -> list[str]:
    """Consultas REALES de técnicos (query_logs.query) — negativos de tráfico para el censo."""
    r = c.get(f"{SB}/rest/v1/query_logs", headers=HS, params={"select": "query", "order": "created_at.desc", "limit": str(limite)})
    return [x["query"] for x in (r.json() if r.status_code == 200 else []) if x.get("query")]
