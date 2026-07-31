#!/usr/bin/env python3
"""s288 A-core F3.2 — probe determinista de la cohorte sobre la lane endurecida.

Invoca ``collect_document_scoped_hyq`` DIRECTAMENTE (defaults de producción; la lane
sigue OFF en serving) para la cohorte de eficacia del spec
``evals/s288_acore_design_brief_v1.md`` §0/§F3:

  * cat010#0 y hp012#3 — dianas (sus docs entraron en P-A: sha real post-paste)
  * hp013#1 — BASELINE no-gating declarado (doble bloqueo: sin surrogate + sin arquetipo)

$0 y read-only: la lane no llama a ningún modelo (BM25 + configs + PostgREST GET); la
atribución es por MECANISMO (receipts: scope ids, parents_rejected, cards servidas), no
por outcome de generación. Salida: ``evals/s288_acore_f3_cohort_probe_v1.json`` + stdout.

Freeze del probe: commit HEAD + fingerprint de corpus (conteos) + fetch_receipts de la
propia lane (hyq_rows/selected/hydrated shas). El corpus CAMBIÓ con el paste P-A — este
probe estampa el estado POST (esperado: placeholders 159, sha real 1010).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

os.environ["CHUNKS_TABLE"] = "chunks_v2"
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
os.environ["CHUNKS_TABLE"] = "chunks_v2"

import httpx  # noqa: E402

import src.config as cfg  # noqa: E402
from src.rag.doc_scoped_hyq_coverage import collect_document_scoped_hyq  # noqa: E402

COHORT = {
    "cat010": ("¿Cómo se alimenta la sirena/avisador intrínsecamente seguro IS-mA1 en "
               "una zona peligrosa (ATEX) y cuáles son sus parámetros de seguridad "
               "intrínseca de entrada?"),
    "hp012": ("¿Cuántos lazos direccionables soporta la Notifier AM2020/AFP1010 y "
              "cuántos dispositivos por lazo?"),
    "hp013": ("¿Cómo se cambia la batería tampón de la Detnov ADW535 sin perder "
              "configuración?"),
}
ROLE = {"cat010": "diana", "hp012": "diana", "hp013": "baseline_no_gating"}


def corpus_counts() -> dict:
    headers = {
        "apikey": cfg.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {cfg.SUPABASE_SERVICE_KEY}",
        "Prefer": "count=exact",
    }
    base = cfg.SUPABASE_URL.rstrip("/")
    out = {}
    for name, path, params in (
        ("documents", "documents", {"select": "id", "limit": "1"}),
        ("documents_placeholder", "documents",
         {"select": "id", "source_pdf_sha256": "like.backfill:*", "limit": "1"}),
        ("chunks_v2", "chunks_v2", {"select": "id", "limit": "1"}),
    ):
        resp = httpx.get(f"{base}/rest/v1/{path}", headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        out[name] = int(resp.headers["content-range"].split("/")[1])
    return out


def main() -> int:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    result = {
        "probe": "s288_acore_f3_cohort_v1",
        "commit": head,
        "corpus_post_paste": corpus_counts(),
        "qids": {},
    }
    for qid, query in COHORT.items():
        rows, trace = collect_document_scoped_hyq(query, include_fetch_receipts=True)
        served = []
        for row in rows:
            cards = row.get("coverage_cards") or []
            served.append({
                "id": str(row.get("id")),
                "source_file": str(row.get("source_file") or ""),
                "page_number": row.get("page_number"),
                "document_id": str(row.get("document_id") or ""),
                "facets": row.get("coverage_card_facets") or [],
                # ``quote`` es la clave REAL del span de una card
                # (evidence_coverage.select_evidence_coverage_cards); leer solo
                # excerpt/content devolvía [""] y hacía ilegibles los receipts.
                "card_excerpt_heads": [
                    str(
                        card.get("quote")
                        or card.get("excerpt")
                        or card.get("content")
                        or ""
                    )[:160]
                    for card in cards
                ],
            })
        result["qids"][qid] = {
            "role": ROLE[qid],
            "status": trace.get("status"),
            "scope_document_ids": trace.get("scope_document_ids"),
            "hyq_rows": trace.get("hyq_rows"),
            "http_requests": trace.get("http_requests"),
            "parents_rejected": trace.get("parents_rejected"),
            "fetch_receipts": trace.get("fetch_receipts"),
            "served_parents": served,
        }
        print(f"[{qid}] ({ROLE[qid]}) status={trace.get('status')} "
              f"served={len(served)} rejected={len(trace.get('parents_rejected') or [])} "
              f"reqs={trace.get('http_requests')}")
        for s in served:
            print(f"    -> {s['source_file']} p.{s['page_number']} facets={s['facets']}")
    out_path = ROOT / "evals" / "s288_acore_f3_cohort_probe_v1.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\n-> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
