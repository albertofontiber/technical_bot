# -*- coding: utf-8 -*-
"""s331 — Baja de `MNDT730P` del corpus (anotación de Alberto en §1.B del packet E1).

Su nota bajo la fila `notifier:stratos-hssd`: «versión portuguesa, retirar doc».
Verificado antes de proponerlo: `MNDT730P` es un fragmento PT de **1 chunk** («# Controlos e
Indicadores») y su hermano ES `MNDT730` está activo con **6 chunks** («*STRATOS* HSSD® — DETECTOR DE
HUMO DE ALTA SENSIBILIDAD — Miniguía»). Misma clase que los 6 fragmentos PT retirados en s324.

Reversible: `status=retired`, los chunks quedan intactos (volver a `active` deshace la baja).

Uso:  python scripts/s331_retirar_mndt730p.py [--aplicar]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
SESION = "s331"
DOC = "MNDT730P"
HERMANO = "MNDT730"
MOTIVO = ("Alberto (s331, §1.B): «versión portuguesa, retirar doc» — fragmento PT de 1 chunk "
          "(«Controlos e Indicadores»); el hermano ES MNDT730 sigue activo con 6 chunks")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()
    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    with abierto(timeout=60.0) as c:
        docs, off = [], 0
        while True:
            r = c.get(f"{SB}/rest/v1/documents", headers=HS,
                      params={"select": "id,document_family,source_pdf_filename,status,notes",
                              "limit": "1000", "offset": str(off)})
            r.raise_for_status()
            page = r.json()
            docs += page
            if len(page) < 1000:
                break
            off += 1000
        obj = [d for d in docs if d["document_family"].upper().startswith(DOC) and d["status"] == "active"]
        herm = [d for d in docs if d["document_family"].upper() == HERMANO and d["status"] == "active"]
        if len(obj) != 1:
            print(f"ABORTA: se esperaba 1 documento activo {DOC}, hay {len(obj)}", file=sys.stderr)
            return 1
        if not herm:
            print(f"ABORTA: el hermano ES {HERMANO} no está activo — la baja perdería el contenido",
                  file=sys.stderr)
            return 1
        d = obj[0]
        ch = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                   params={"select": "id", "document_id": f"eq.{d['id']}"})
        ch.raise_for_status()
        n_chunks = len(ch.json())
        hc = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                   params={"select": "id", "document_id": f"eq.{herm[0]['id']}"})
        hc.raise_for_status()
        recibo = {"sesion": SESION, "utc": utc, "doc": d["document_family"], "document_id": d["id"],
                  "chunks": n_chunks, "status_prev": d["status"], "notes_prev": d.get("notes"),
                  "hermano_es": herm[0]["document_family"], "hermano_chunks": len(hc.json()),
                  "motivo": MOTIVO, "reversion": "documents.status → 'active' (los chunks no se tocan)",
                  "aplicado": False}
        print(f"{'APLICAR' if args.aplicar else 'DRY-RUN'} · RETIRAR {d['document_family']!r} "
              f"({n_chunks} chunks) · hermano ES {herm[0]['document_family']} ({len(hc.json())} chunks)")
        if args.aplicar:
            nota = f"{(d.get('notes') or '').strip()}\n{SESION} {utc}: retirado — {MOTIVO}".strip()
            u = c.patch(f"{SB}/rest/v1/documents", headers={**HS, "Content-Type": "application/json",
                                                            "Prefer": "return=representation"},
                        params={"id": f"eq.{d['id']}", "status": "eq.active"},
                        json={"status": "retired", "notes": nota})
            u.raise_for_status()
            filas = u.json()
            if len(filas) != 1:
                print(f"ABORTA: el CAS no tocó exactamente 1 fila ({len(filas)})", file=sys.stderr)
                return 1
            recibo["aplicado"] = True
            print(f"APLICADO · {d['document_family']} → retired")
    out = ROOT / "evals" / f"s331_retirar_mndt730p_{utc}.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print("recibo:", out.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
