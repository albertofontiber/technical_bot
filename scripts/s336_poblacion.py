# -*- coding: utf-8 -*-
"""s336 B4 — PASADA de población sobre la diana Notifier (v3 §1.1-1.3).

Método = el CERRADO de s322b, entero: pasada (muestra 3 docs × 3 chunks, cita
verbatim por campo, degradación por cita-en-muestra) + REPESCA dirigida a
secciones de enumeración/tablas de modelos para las filas no-alta (la ventana
inicial de s322 perdió 22/22 que la repesca recuperó — TECH_DEBT s322b).

NADA se escribe al catálogo aquí: recibo → capacidad+full-text (Sol2-1/Sol2-2)
→ gate vs GT → writer atómico. El PROMPT es copia VERBATIM del de
`s322_76_poblacion.py` (el recibo estampa sha256 de ambos para pinnar el
no-drift; una fuente importable exigiría paquete en scripts/ — declarado).

Uso: python scripts/s336_poblacion.py [--limit N] [--out ...]
     (--limit 10 = el SMOKE pre-registrado que mide el coste real)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

import anthropic  # noqa: E402

from src.http_pool import abierto  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
MODELO = "claude-fable-5"

PROMPT = """Eres el clasificador de productos de un catálogo de protección contra incendios (PCI).

PRODUCTO: {canonical} (id {pid})
DOCUMENTOS de este producto y MUESTRAS de su contenido real:
---
{muestra}
---
Pista legacy (texto libre del seed, puede estar mal): {pista}

Clasifícalo. Responde SOLO este JSON:
{{"categoria": "central|detector|pulsador|sirena|modulo|fuente|repetidor|aspiracion|barrera|retenedor|pasarela|software|accesorio",
 "categoria_cita": "fragmento VERBATIM del contenido que lo fundamenta",
 "tecnologia": "analogica|convencional|algoritmica|aspiracion|via_radio|null",
 "tecnologia_cita": "fragmento VERBATIM o null",
 "lazos": [{{"base": N, "max": N, "cita": "fragmento VERBATIM"}}] o null,
 "confianza": "alta|media|baja",
 "razon": "una frase"}}

Reglas: analogica INCLUYE direccionable/inteligente/addressable (uso PCI-ES estándar). Los sounder/VAD/beacon de notificación → sirena. LHD/sensor cable → detector. PAK/llaves/repuestos → accesorio. Si el doc cubre VARIAS variantes y los lazos difieren POR VARIANTE, devuelve los lazos DE ESTE producto (por su sufijo si el doc lo ancla) — si no puedes anclarlo, lazos=null. Si dos DOCS divergen (p.ej. mercados), devuelve AMBAS entradas de lazos con su cita. Sin cita verbatim → confianza baja."""

_RX_R9 = re.compile(
    r"descripci[oó]n general|\bmodelos\b|\bmodels\b|ordering information|"
    r"informaci[oó]n de pedido|referencias|\bgama\b|\bversiones\b|"
    r"table \d+[^\n]{0,60}models", re.IGNORECASE)


def _chunks(c, sf: str, limit: int, offset: int = 0) -> list[dict]:
    r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
              params={"select": "chunk_index,content",
                      "source_file": f"eq.{sf}",
                      "order": "chunk_index.asc",
                      "limit": str(limit), "offset": str(offset)})
    r.raise_for_status()
    return r.json()


def _ventana_repesca(c, docs: list[str], canonical: str) -> str:
    """Ventana DIRIGIDA (repesca s322b): chunks que contienen secciones R9 o el
    token canónico — donde viven las tablas de modelos que la muestra pierde."""
    trozos = []
    for sf in docs[:3]:
        filas, offset = [], 0
        while True:
            lote = _chunks(c, sf, 100, offset)
            filas.extend(lote)
            if len(lote) < 100:
                break
            offset += 100
        rx_can = re.compile(re.escape(canonical), re.IGNORECASE) if canonical else None
        buenos = [x for x in filas
                  if _RX_R9.search(x.get("content") or "")
                  or (rx_can and rx_can.search(x.get("content") or ""))]
        if buenos:
            trozos.append(f"[DOC: {sf} — ventana dirigida]\n" + "\n···\n".join(
                (x.get("content") or "")[:1100] for x in buenos[:6]))
    return "\n\n".join(trozos)[:9000]


def _clasifica(cliente, uso, d, muestra: str, etapa: str) -> dict:
    msg = cliente.messages.create(
        model=MODELO, max_tokens=500,
        messages=[{"role": "user", "content": PROMPT.format(
            canonical=d["canonical_model"], pid=d["id"],
            muestra=muestra, pista=d.get("pista_legacy"))}])
    uso["in"] += msg.usage.input_tokens
    uso["out"] += msg.usage.output_tokens
    texto = "".join(b.text for b in msg.content
                    if getattr(b, "type", "") == "text").strip()
    try:
        v = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])
    except Exception:                             # noqa: BLE001
        v = {"categoria": None, "confianza": "baja",
             "razon": "parse-fail", "raw": texto[:200]}
    ml = muestra.lower()

    def _ok(cita):
        # chequeo BARATO en-pasada (prefijo, heredado); la barrera REAL es la
        # verificación FULL-TEXT pre-escritura (etapa siguiente, Sol-2).
        return bool(cita) and str(cita)[:50].lower() in ml

    citas_ok = _ok(v.get("categoria_cita"))
    if v.get("tecnologia") and v.get("tecnologia") != "null":
        citas_ok = citas_ok and _ok(v.get("tecnologia_cita"))
    for lz in (v.get("lazos") or []):
        citas_ok = citas_ok and _ok(lz.get("cita"))
    if v.get("confianza") == "alta" and not citas_ok:
        v["confianza"] = "media"
        v["nota"] = "cita no verificada en muestra → degradada"
    v["etapa"] = etapa
    return {"llm": v, "citas_en_muestra": citas_ok}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    censo = json.loads((ROOT / "evals" / "s336_censo_diana_v1.json")
                       .read_text(encoding="utf-8"))["detalle"]
    if args.limit:
        censo = censo[:args.limit]
    out = args.out or str(ROOT / "evals" / (
        f"s336_poblacion_smoke{args.limit}_v1.json" if args.limit
        else "s336_poblacion_v1.json"))

    cliente = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"],
                                  timeout=120.0, max_retries=1)
    uso = {"in": 0, "out": 0}
    filas, docs_sin_chunks = [], set()
    t0 = time.perf_counter()
    with abierto(timeout=30.0) as c:
        for i, d in enumerate(censo):
            trozos = []
            for sf in d["docs"][:3]:
                muestra_doc = _chunks(c, sf, 3)
                if not muestra_doc:
                    docs_sin_chunks.add(sf)     # clase GT-09 (20/20UB): contada
                    continue
                trozos.append(f"[DOC: {sf}]\n" + "\n···\n".join(
                    (x.get("content") or "")[:900] for x in muestra_doc))
            if not trozos:
                filas.append({"id": d["id"], "canonical": d["canonical_model"],
                              "docs": d["docs"][:3],
                              "llm": {"categoria": None, "confianza": "baja",
                                      "razon": "sin chunks en ningún doc",
                                      "etapa": "sin-evidencia"},
                              "citas_en_muestra": False})
                continue
            muestra = "\n\n".join(trozos)[:7000]
            fila = {"id": d["id"], "canonical": d["canonical_model"],
                    "docs": d["docs"][:3],
                    **_clasifica(cliente, uso, d, muestra, "pasada")}
            # REPESCA dirigida (v3 §1.3) para lo no-alta
            if fila["llm"].get("confianza") != "alta":
                ventana = _ventana_repesca(c, d["docs"], d["canonical_model"])
                if ventana:
                    re_fila = _clasifica(cliente, uso, d, ventana, "repesca")
                    if re_fila["llm"].get("confianza") == "alta":
                        fila = {"id": d["id"], "canonical": d["canonical_model"],
                                "docs": d["docs"][:3], **re_fila}
            filas.append(fila)
            if (i + 1) % 20 == 0:
                print(f"  {i+1}/{len(censo)} · tokens in={uso['in']} "
                      f"out={uso['out']}", flush=True)
            if (i + 1) % 50 == 0:      # checkpoint: una pasada de 2 h no se
                Path(out + ".parcial").write_text(   # pierde por un blip
                    json.dumps({"hasta": i + 1, "detalle": filas},
                               ensure_ascii=False), encoding="utf-8")

    conf = {"alta": 0, "media": 0, "baja": 0}
    for f in filas:
        conf[f["llm"].get("confianza") or "baja"] = conf.get(
            f["llm"].get("confianza") or "baja", 0) + 1
    recibo = {
        "que_es": "s336 pasada de población (fable-5) + repesca dirigida — SIN escritura",
        "modelo": MODELO,
        "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest()[:16],
        "prompt_s322_sha256": hashlib.sha256(
            re.search(r'PROMPT = """(.*?)"""',
                      (ROOT / "scripts" / "s322_76_poblacion.py")
                      .read_text(encoding="utf-8"), re.DOTALL)
            .group(0).encode()).hexdigest()[:16],
        "n": len(filas), "confianzas": conf,
        "docs_sin_chunks": sorted(docs_sin_chunks),
        "uso_tokens": uso,
        "duracion_s": round(time.perf_counter() - t0, 1),
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "detalle": filas,
    }
    Path(out).write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print(f"\nn={len(filas)} · confianzas={conf} · docs_sin_chunks="
          f"{len(docs_sin_chunks)} · tokens={uso} · "
          f"{recibo['duracion_s']}s · recibo → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
