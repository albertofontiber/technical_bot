# -*- coding: utf-8 -*-
"""s324d — Re-ingesta de `HLSI-TI-007_VSN-4REL` por el PIPELINE REAL (TECH_DEBT #87).

El documento vivía en el corpus con **47 chars** («Honeywell · Honeywell Life Safety Iberia») mientras su
PDF tiene 2.246 chars de texto nativo con el procedimiento de configuración del módulo VSN-4REL. La causa NO
era OCR: LlamaParse devolvió `md`=34 chars y `text`=3.708 en el mismo JSON, y la ingesta hacía `md or text`
(sólo cae a `text` si `md` es vacío). Con la guarda de `src/reingest/page_content.py` (dúo r35) el pipeline
sanea la página y el documento se re-ingesta ENTERO.

Mecánica (idéntica a la ingesta normal, sin caminos paralelos):
  1. descarga el PDF del bucket (`documents.source_url`) y verifica su **sha256 contra `source_pdf_sha256`**
     — si no casa, PARA (sería otro documento);
  2. re-parsea con LlamaParse en la config del corpus (`parse_page_with_agent` + `anthropic-sonnet-4.5`) o
     reutiliza el JSON del store si ya existe (resumable, como `extract.py`);
  3. guarda el JSON en el store duradero `data/extraction/agent_anthropic-sonnet-45/<sha>.json`;
  4. llama a `pipeline.process_file(record, supabase, dry_run)` — el MISMO camino B1-B8 de la ingesta, que
     resuelve el documento por sha (acotado a marca), contextualiza, embebe e indexa. `index_chunks` borra
     los chunks previos del documento antes de insertar, así que la operación es idempotente.

Verificación posterior EN EL MISMO TURNO: chunks, chars y presencia del procedimiento en el corpus.

Uso:  python scripts/s324d_reingesta_ti007.py [--aplicar]
Salida: evals/s324d_reingesta_ti007_<modo>_<utc>.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

import httpx  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.ingestion.supabase_client import SupabaseHTTP  # noqa: E402
from src.reingest import pipeline  # noqa: E402
from src.reingest.extract import llamaparse_extract, load_key  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
DOC_DEFECTO = "HLSI-TI-007_VSN-4REL"
MODE, MODEL = "parse_page_with_agent", "anthropic-sonnet-4.5"
STORE = ROOT / "data" / "extraction" / "agent_anthropic-sonnet-45"
# Agujas del procedimiento que HOY faltan en el corpus (verificadas en el texto nativo del PDF).
AGUJAS = ["PROG", "Z1", "VSN-4REL", "40 cm"]


def ficha(c) -> dict:
    r = c.get(f"{SB}/rest/v1/documents", headers=HS,
              params={"select": "id,source_pdf_filename,source_pdf_sha256,manufacturer,status,source_url",
                      "source_pdf_filename": f"eq.{DOC}"})
    r.raise_for_status()
    filas = r.json()
    if len(filas) != 1:
        raise SystemExit(f"se esperaba 1 fila de documents para {DOC}; hay {len(filas)}")
    return filas[0]


def chunks_actuales(c, doc_id: str) -> list[dict]:
    r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
              params={"select": "id,chunk_index,content,page_number", "document_id": f"eq.{doc_id}",
                      "order": "chunk_index.asc"})
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--doc", default=DOC_DEFECTO,
                    help="source_pdf_filename del documento a re-ingestar (por defecto, TI-007)")
    ap.add_argument("--agujas", default=None,
                    help="tokens separados por coma que DEBEN aparecer tras la re-ingesta (verificación)")
    args = ap.parse_args()
    global DOC, AGUJAS
    DOC = args.doc
    if args.agujas:
        AGUJAS = [a.strip() for a in args.agujas.split(",") if a.strip()]
    modo = "aplicar" if args.aplicar else "dry-run"
    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recibo: dict = {"que_es": __doc__.strip().splitlines()[0], "modo": modo, "utc": utc, "doc": DOC}

    with abierto(timeout=120.0) as c:
        d = ficha(c)
        antes = chunks_actuales(c, d["id"])
        recibo["documento"] = {k: d[k] for k in ("id", "manufacturer", "status", "source_pdf_sha256")}
        recibo["antes"] = {"n_chunks": len(antes), "chars": sum(len(x["content"] or "") for x in antes),
                           "contenido": [x["content"] for x in antes]}
        print(f"ANTES: {len(antes)} chunk(s), {recibo['antes']['chars']} chars")

        # 1 · PDF + verificación de identidad
        pdf_bytes = httpx.get(d["source_url"], timeout=180).content
        sha = hashlib.sha256(pdf_bytes).hexdigest()
        if sha != d["source_pdf_sha256"]:
            raise SystemExit(f"el PDF del bucket ({sha[:12]}) NO casa con documents.source_pdf_sha256 "
                             f"({(d['source_pdf_sha256'] or '')[:12]}): no es el mismo documento")
        tmp_dir = ROOT / "tmp" / "s324d"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = tmp_dir / f"{DOC}.pdf"
        pdf_path.write_bytes(pdf_bytes)
        recibo["pdf"] = {"sha256": sha, "bytes": len(pdf_bytes), "sha_casa_con_documents": True}

        # 2 · extracción (resumable: si el store ya la tiene, no se vuelve a pagar)
        STORE.mkdir(parents=True, exist_ok=True)
        destino = STORE / f"{sha}.json"
        if destino.is_file():
            record = json.loads(destino.read_text(encoding="utf-8"))
            recibo["extraccion"] = {"reutilizada_del_store": True, "job_id": record.get("job_id")}
            print(f"extracción reutilizada del store: {destino.name}")
        else:
            key = load_key()
            if not key:
                raise SystemExit("LLAMAPARSE_API_KEY no encontrada en .env")
            t0 = time.time()
            job_id, result = llamaparse_extract(str(pdf_path), key, MODE, MODEL)
            record = {"sha256": sha, "source_path": str(pdf_path), "manufacturer": d["manufacturer"],
                      "pages": len(result.get("pages") or []), "mode": MODE, "model": MODEL,
                      "job_id": job_id, "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "result": result}
            destino.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            recibo["extraccion"] = {"reutilizada_del_store": False, "job_id": job_id,
                                    "segundos": round(time.time() - t0, 1)}
            print(f"extracción nueva: job {job_id} ({recibo['extraccion']['segundos']} s)")
        paginas = (record.get("result") or {}).get("pages") or []
        recibo["extraccion"]["paginas"] = [{"page": p.get("page"), "md_chars": len(p.get("md") or ""),
                                            "text_chars": len(p.get("text") or "")} for p in paginas]

        # 3 · pipeline REAL (dry-run siempre; aplicar sólo con la bandera)
        supabase = SupabaseHTTP() if args.aplicar else None
        seco = pipeline.process_file(record, None, dry_run=True)
        recibo["dry_run"] = {k: v for k, v in seco.items() if k != "_chunks"}
        chunks_secos = seco.get("_chunks") or []
        recibo["dry_run"]["muestra"] = [c.content[:160] for c in chunks_secos[:3]]
        print(f"DRY-RUN: {seco.get('status')} · {len(chunks_secos)} chunks · {seco.get('chars')} chars "
              f"· md_degenerado {seco.get('md_degenerado', {}).get('n_paginas_afectadas')} pág.")
        texto_seco = "\n".join(c.content for c in chunks_secos)
        recibo["dry_run"]["agujas_presentes"] = {a: (a in texto_seco) for a in AGUJAS}
        print("  agujas:", recibo["dry_run"]["agujas_presentes"])

        if args.aplicar:
            res = pipeline.process_file(record, supabase, dry_run=False)
            recibo["aplicado"] = res
            print(f"APLICADO: {res.get('status')} · indexados {res.get('indexed')} · doc {res.get('document_id')}")
            # verificación EN EL MISMO TURNO, contra la DB
            despues = chunks_actuales(c, d["id"])
            texto = "\n".join(x["content"] or "" for x in despues)
            recibo["despues"] = {"n_chunks": len(despues), "chars": len(texto),
                                 "agujas_presentes": {a: (a in texto) for a in AGUJAS}}
            print(f"VERIFICACIÓN: {len(despues)} chunks · {len(texto)} chars · "
                  f"agujas {recibo['despues']['agujas_presentes']}")
            assert len(texto) > recibo["antes"]["chars"], "la re-ingesta no aumentó el texto del documento"
            assert all(recibo["despues"]["agujas_presentes"].values()), "faltan agujas del procedimiento"

    out = ROOT / "evals" / f"s324d_reingesta_ti007_{modo}_{utc}.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print("recibo:", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
