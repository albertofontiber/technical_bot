#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fase DERIVADOS de la ingesta (s315/#68): enunciados + hyq para un LOTE nuevo.

POR QUÉ. Los dos canales derivados están VIVOS en producción (ENUNCIADOS_MULTIVECTOR
DEC-090, HYQ_TABLE DEC-099) pero `ingest_new.py` no los genera: todo lote nuevo entra
como corpus de segunda clase (lote Casmar s314: 1.091 chunks con 0/0 — TECH_DEBT #68).
Este driver orquesta la fase para UN lote, reusando los generadores/gates canónicos:

  E1 enunciados: `enunciados_pass.py --docs <lote> --to-dump` (QA in-run `qa_statement`,
     ledger+resume, Haiku vintage h1 = el GO de DEC-102, budget duro)
  E2 carga: `s104_a3_load.py --dumps ... --only-source-files ... --rewrite-batch-tag
     enunciados-v1:<tag>:h1 --ledger-check --ids-out` (el camino acotado s273, estrenado aquí)
  H  hyq: `hyq_lote_pipeline.py` (vintage POR LOTE append-seguro; parse/embed pineados)
  V  verificación en DB: cobertura por doc en AMBAS tablas + recibo JSON

DÓNDE. Máquina con claves (.env: ANTHROPIC, VOYAGE, SUPABASE) y con el extraction
store del lote (bajo --data-root de ingest_new, normalmente OneDrive). Dry-run por
defecto: imprime plan + coste estimado y NO llama a ninguna API.

Uso típico (lote Casmar s314):
  python scripts/derive_channels_lote.py --since 2026-08-08 --tag casmar314 \
      --data-root "C:\\...\\Technical Bot"            # dry-run
  ... mismo comando + --aplicar                        # ejecuta E1→E2→H→V
Selección alternativa: --docs-file <fichero con un source_file por línea>.
Reanudable: cada herramienta subyacente ya reanuda; re-lanzar continúa donde iba.
Post-carga: VACUUM (fantasmas HNSW, DEC-088) — el recibo lo recuerda.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import httpx  # noqa: E402

from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL  # noqa: E402

HEADERS = {"apikey": SUPABASE_SERVICE_KEY,
           "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
ENUN_MODEL = "claude-haiku-4-5-20251001"   # GO de G0 (DEC-102): mejor QA y 4× más barato
COSTE_HYQ_POR_CHUNK = 0.004
COSTE_ENUN_POR_DOC = (0.05, 0.15)          # banda observada T2 (DEC-102: $9.7 / 81 docs)


def _docs_del_lote(client: httpx.Client, since: str) -> list[dict]:
    """Docs con ingested_at >= since y su nº de chunks (fuente: DB, no memoria)."""
    r = client.get(f"{SUPABASE_URL}/rest/v1/documents", headers=HEADERS,
                   params={"select": "id,source_pdf_filename,ingested_at",
                           "ingested_at": f"gte.{since}", "limit": "2000",
                           "order": "ingested_at.asc"})
    r.raise_for_status()
    docs = r.json()
    out = []
    for d in docs:
        rc = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                        headers={**HEADERS, "Prefer": "count=exact", "Range": "0-0"},
                        params={"select": "id", "document_id": f"eq.{d['id']}"})
        n = int((rc.headers.get("content-range") or "/0").split("/")[-1])
        # source_file de los CHUNKS (clave de selección de los generadores): puede
        # diferir del filename de documents en extensión — tomar el real
        rs = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=HEADERS,
                        params={"select": "source_file",
                                "document_id": f"eq.{d['id']}", "limit": "1"})
        rows = rs.json()
        if n and rows:
            out.append({"document_id": d["id"], "source_file": rows[0]["source_file"],
                        "chunks": n})
    return out


def _cobertura(client: httpx.Client, doc_ids: list[str]) -> dict:
    cov = {"enunciados_docs": 0, "hyq_docs": 0, "docs": len(doc_ids)}
    for did in doc_ids:
        r = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2_enunciados",
                       headers={**HEADERS, "Prefer": "count=exact", "Range": "0-0"},
                       params={"select": "id", "document_id": f"eq.{did}"})
        if int((r.headers.get("content-range") or "/0").split("/")[-1]):
            cov["enunciados_docs"] += 1
    # hyq no lleva document_id: cobertura vía join por chunk_id no expuesto en REST
    # simple → se cuenta por source_file en la fase V del recibo (aproximación honesta)
    return cov


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--since", help="fecha ISO: docs con ingested_at >= fecha")
    g.add_argument("--docs-file", help="fichero con un source_file por línea")
    ap.add_argument("--tag", required=True, help="nombre del lote (p.ej. casmar314)")
    ap.add_argument("--data-root", default=None,
                    help="raíz de datos de ingest_new (para el extraction store)")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--solo", choices=["enunciados", "hyq"], default=None)
    a = ap.parse_args()

    with httpx.Client(timeout=120.0) as client:
        if a.since:
            lote = _docs_del_lote(client, a.since)
            src_files = sorted({d["source_file"] for d in lote})
            n_chunks = sum(d["chunks"] for d in lote)
        else:
            src_files = sorted({ln.strip() for ln in open(a.docs_file, encoding="utf-8")
                                if ln.strip()})
            lote, n_chunks = [], 0
            for sf in src_files:
                rc = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                                headers={**HEADERS, "Prefer": "count=exact",
                                         "Range": "0-0"},
                                params={"select": "id", "source_file": f"eq.{sf}"})
                n_chunks += int((rc.headers.get("content-range") or "/0").split("/")[-1])

        docs_txt = ROOT / "evals" / f"derive_lote_{a.tag}_docs.txt"
        docs_txt.write_text("\n".join(src_files) + "\n", encoding="utf-8")
        c_lo = len(src_files) * COSTE_ENUN_POR_DOC[0]
        c_hi = len(src_files) * COSTE_ENUN_POR_DOC[1]
        print(f"lote '{a.tag}': {len(src_files)} docs · {n_chunks} chunks → {docs_txt}")
        print(f"coste estimado: enunciados ${c_lo:.0f}-{c_hi:.0f} (banda T2, Haiku) "
              f"+ hyq ≈ ${n_chunks * COSTE_HYQ_POR_CHUNK:.1f} (sonnet-4-6) + Voyage <$1")
        if not a.aplicar:
            print("(dry-run; --aplicar para ejecutar E1→E2→H→V)")
            return 0

        py = sys.executable
        fases: list[list[str]] = []
        if a.solo in (None, "enunciados"):
            e1 = [py, "scripts/enunciados_pass.py", "--tranche", a.tag,
                  "--docs", str(docs_txt), "--to-dump", "--resume",
                  "--model", ENUN_MODEL, "--vintage", "h1"]
            if a.data_root:
                e1 += ["--store",
                       str(Path(a.data_root) / "data" / "extraction"
                           / "agent_anthropic-sonnet-45")]
            fases.append(e1)
            fases.append([py, "scripts/s104_a3_load.py",
                          "--dumps", f"evals/enunciados_dump_{a.tag}.jsonl",
                          "--rewrite-batch-tag", f"enunciados-v1:{a.tag}:h1",
                          "--ledger-check",
                          "--ids-out", f"evals/derive_lote_{a.tag}_enun_ids.json",
                          "--only-source-files", *src_files])
        if a.solo in (None, "hyq"):
            fases.append([py, "scripts/hyq_lote_pipeline.py", "--docs", str(docs_txt),
                          "--tag", a.tag, "--aplicar"])
        for cmd in fases:
            print(f"\n── {' '.join(cmd[:3])} …")
            rc = subprocess.call(cmd, cwd=str(ROOT))
            if rc:
                print(f"❌ fase falló (rc={rc}) — corrige y re-lanza (todo reanuda)")
                return rc

        # V — verificación + recibo
        doc_ids = [d["document_id"] for d in lote] if lote else []
        cov = _cobertura(client, doc_ids) if doc_ids else {}
        n_hyq = 0
        for sf in src_files:
            r = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2_hyq",
                           headers={**HEADERS, "Prefer": "count=exact", "Range": "0-0"},
                           params={"select": "id", "source_file": f"eq.{sf}"})
            n_hyq += int((r.headers.get("content-range") or "/0").split("/")[-1])
        recibo = {
            "motivo": "s315/#68: fase derivados del lote (enunciados + hyq)",
            "lote": a.tag, "docs": len(src_files), "chunks": n_chunks,
            "cobertura": cov, "hyq_filas_por_source_file": n_hyq,
            "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pendiente": "VACUUM de chunks_v2_enunciados y chunks_v2_hyq (DEC-088)",
        }
        out = ROOT / "evals" / f"derive_lote_{a.tag}_recibo.json"
        out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(f"\nrecibo → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
