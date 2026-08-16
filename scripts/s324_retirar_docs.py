# -*- coding: utf-8 -*-
"""s324 — BAJA de corpus (documents.status='retired') de documentos adjudicados por Alberto.

Dos clases, ambas firmadas el 16-ago-2026 (`evals/s324_reglas_residuo_adjudicacion_v1.json`):
  (a) FRAGMENTOS PT con hermano ES completo (política de idiomas de s65 — «no migrado a v2:
      portugués (sufijo P)» — que estos seis esquivaron): la ingesta PT es un fragmento
      (≤6 chunks, ≤5 % del hermano ES) sin contenido propio. NO es una variante de idioma
      completa (DEC-066 las conserva y las relaciona): es limpieza de fragmento.
  (b) `ma-dt-1160`, adjudicada en s323 («eliminar del corpus: es un paper sobre ExitPoint,
      no habla de características ni de uso»).

Mecanismo: el MISMO que usan las 91 filas ya retiradas — `documents.status='retired'`. El
retriever descarta post-merge los chunks cuyo documento no está `active`
(`retriever.py` paso 4b `_filter_by_document_status`); los chunks NO se borran (reversible:
volver a `active`). Además se quitan del `doc_map` las entradas del documento retirado
(el hermano ES conserva las suyas; se verifica ANTES).

Guardas por fila (todas obligatorias; si una falla → esa fila NO se toca y se declara):
  1. la fila existe y está `active`;
  2. el nº de chunks coincide con el censado el 16-ago (deriva → parar);
  3. clase (a): el hermano ES existe, está `active` y tiene MÁS chunks que el fragmento;
  4. si el documento tiene entradas en doc_map, el hermano ES tiene las suyas propias
     (que no se pierda una atestación al retirar).

Uso:  python scripts/s324_retirar_docs.py [--aplicar]
"""
from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, write_jsonl

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
SESION = "s324"

# (source_pdf_filename, clase, chunks censados 16-ago, hermano ES, motivo)
BAJAS = [
    ("4188-1132-PT issue 4_04_2025-Qref.pdf", "fragmento-pt", 1,
     "4188-1132-ES issue 3_04_2025_Qref", "fragmento PT (1 pág.) de la Qref INSPIRE E10/E15; ES completa 18 chunks"),
    ("MIE-MI-120P.pdf", "fragmento-pt", 1,
     "MIEMI120rev05.pdf", "fragmento PT (leyenda del frontal, Rev 001) del manual VSN 2-4; ES Rev 005 con 48 chunks"),
    ("MIEMU520P.pdf", "fragmento-pt", 1,
     "MIE-MU-520rv02.pdf", "fragmento PT (1 pág.) del manual Dimension; ES con 68 chunks"),
    ("4188-1124-PT issue 4_01-2026_To.pdf", "fragmento-pt", 6,
     "4188-1124-ES issue 6_01-2026_To", "fragmento PT (6 chunks) de CLSS Configuration Tool; ES issue 6 con 116 chunks"),
    ("I56-3956-201_PT Morley Loop FAAST LT QIG.pdf", "fragmento-pt", 2,
     "I56-3956-201_ES Morley Loop FAAST LT QIG.pdf", "fragmento PT (2 chunks) de la QIG FAAST LT; ES con 22 chunks"),
    ("MNDT1003P", "fragmento-pt", 1,
     "MNDT1003", "hoja BA1 de 1 página duplicada en PT; ES propia (1 chunk) con doc_map propio"),
    ("MA-DT-1160", "adjudicacion-s323", 14, None,
     "Alberto (s323): eliminar del corpus — paper sobre ExitPoint, no habla de características ni de uso"),
]


def _get(c, path, **params):
    r = c.get(f"{SB}/rest/v1/{path}", headers=HS, params=params)
    r.raise_for_status()
    return r.json()


def ficha(c, nombre):
    rows = _get(c, "documents", select="id,source_pdf_filename,status,product_model,notes",
                source_pdf_filename=f"eq.{nombre}")
    if len(rows) != 1:
        return None
    d = rows[0]
    n = _get(c, "chunks_v2", select="id", document_id=f"eq.{d['id']}")
    d["n_chunks"] = len(n)
    return d


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args(); modo = "aplicar" if args.aplicar else "dry-run"
    doc_map = _read_jsonl(CATALOG_DIR / "doc_map.jsonl")
    dm_por_doc = {r["document_id"]: r for r in doc_map}
    dm_por_sf = {r["source_file"].lower(): r for r in doc_map}

    plan, rechazadas, backup = [], [], []
    with abierto(timeout=30.0) as c:
        for nombre, clase, n_esp, hermano, motivo in BAJAS:
            d = ficha(c, nombre)
            fallos = []
            if not d:
                rechazadas.append({"doc": nombre, "fallo": "no existe o no es única"}); continue
            if d["status"] != "active":
                fallos.append(f"status={d['status']} (no active)")
            if n_esp is not None and d["n_chunks"] != n_esp:
                fallos.append(f"chunks {d['n_chunks']} != censados {n_esp} (deriva)")
            h = None
            if clase == "fragmento-pt":
                h = ficha(c, hermano)
                if not h or h["status"] != "active":
                    fallos.append("hermano ES ausente o no active")
                elif h["n_chunks"] < d["n_chunks"]:
                    fallos.append(f"hermano ES con MENOS chunks ({h['n_chunks']} < {d['n_chunks']})")
            dm = dm_por_doc.get(d["id"]) or dm_por_sf.get(nombre.lower())
            if dm and clase == "fragmento-pt":
                hdm = (dm_por_doc.get(h["id"]) if h else None) or dm_por_sf.get((hermano or "").lower())
                if not hdm:
                    fallos.append("el fragmento tiene doc_map y el hermano ES NO: se perdería la atestación")
            if fallos:
                rechazadas.append({"doc": nombre, "fallo": "; ".join(fallos)}); continue
            plan.append({"doc": nombre, "document_id": d["id"], "clase": clase, "motivo": motivo,
                         "chunks": d["n_chunks"], "product_model": d["product_model"],
                         "hermano_es": (h and {"doc": h["source_pdf_filename"], "chunks": h["n_chunks"]}),
                         "doc_map_entries_a_quitar": (dm and [e["id"] for e in dm.get("entries") or []]) or []})
            backup.append({"document_id": d["id"], "status_prev": d["status"], "notes_prev": d.get("notes"),
                           "doc_map_prev": dm})

        print(f"{modo}: {len(plan)} bajas planificadas · {len(rechazadas)} rechazadas por guarda")
        for p in plan:
            print(f"  RETIRAR {p['doc']!r} ({p['chunks']} chunks) — {p['motivo']}"
                  + (f" · doc_map −{len(p['doc_map_entries_a_quitar'])}" if p["doc_map_entries_a_quitar"] else ""))
        for r in rechazadas:
            print(f"  NO TOCAR {r['doc']!r}: {r['fallo']}")

        aplicado = []
        if args.aplicar and plan:
            utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for p, b in zip(plan, backup):
                nota = (b["notes_prev"] + " | " if b["notes_prev"] else "") + \
                       f"{SESION} {utc}: retirado — {p['motivo']}"
                r = c.patch(f"{SB}/rest/v1/documents", headers={**HS, "Prefer": "return=representation"},
                            params={"id": f"eq.{p['document_id']}"},
                            json={"status": "retired", "notes": nota})
                r.raise_for_status()
                aplicado.append({"document_id": p["document_id"], "status": r.json()[0]["status"]})
            quitar = {p["document_id"] for p in plan if p["doc_map_entries_a_quitar"]}
            if quitar:
                write_jsonl("doc_map", [r for r in doc_map if r["document_id"] not in quitar])
            # verificación EN EL MISMO TURNO
            for p in plan:
                d = ficha(c, p["doc"])
                assert d and d["status"] == "retired", f"{p['doc']}: status tras aplicar = {d and d['status']}"

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recibo = {"que_es": __doc__.strip().splitlines()[0], "modo": modo, "utc": utc,
              "plan": plan, "rechazadas": rechazadas, "backup": backup, "aplicado": aplicado,
              "reversion": "PATCH documents set status=<status_prev> por document_id; doc_map: restaurar doc_map_prev"}
    out = ROOT / "evals" / f"s324_retirar_docs_{modo}_{utc}.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print("recibo:", out.relative_to(ROOT))
    return 0 if not rechazadas or not args.aplicar else 0


if __name__ == "__main__":
    sys.exit(main())
