# -*- coding: utf-8 -*-
"""s324d — TECH_DEBT #88: `documents.product_model` conserva los artefactos que E3 (F3a, 13-ago) corrigió SOLO en
`chunks_v2` (55 documentos: «System 5000»→CPU-5000, «LOCAL-360»→FDX-551EM, «TO-3200M»…). Serving no lee ese
campo (el retriever usa el pm del CHUNK; de `documents` lee status/manufacturer/revision/source_url), pero sí lo
leen los censos y derivaciones (el draft de candidates E1 nació de ahí). Este script lo alinea con el canónico
ADJUDICADO en E3, con las guardas del patrón T3:

  · universo = EXACTAMENTE los 55 docs del recibo `evals/s321_e3_writer_aplicar_20260813T222611Z.json`
    (lote adjudicado por Alberto; nada fuera de él);
  · guardas por fila (si una falla, la fila NO se toca y se declara): doc existe y está `active`; el 100 % de sus
    chunks lleva YA el canónico E3 (la verdad curada); `documents.product_model` es el valor censado (CAS);
  · escritura: PATCH por fila con `product_model=eq.<actual>` (CAS) + backup del valor previo en el recibo;
    verificación en el mismo turno; reversión = PATCH con el valor previo del recibo.

Uso:  python scripts/s324d_retag_documents_pm.py [--aplicar]
Salida: evals/s324d_retag_documents_pm_<modo>_<utc>.json
"""
from __future__ import annotations
import argparse, json, os, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"], "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
E3 = ROOT / "evals" / "s321_e3_writer_aplicar_20260813T222611Z.json"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args(); modo = "aplicar" if args.aplicar else "dry-run"
    e3 = json.loads(E3.read_text(encoding="utf-8"))
    canon = {d["document_id"]: (d["canonical_model"], d["source_file"]) for d in e3["detalle"]}
    plan, rechazadas, sin_cambio = [], [], []
    with abierto(timeout=60.0) as c:
        ids = list(canon)
        docs = {}
        for i in range(0, len(ids), 40):
            batch = ",".join(f'"{x}"' for x in ids[i:i + 40])
            r = c.get(f"{SB}/rest/v1/documents", headers=HS,
                      params={"select": "id,source_pdf_filename,product_model,status,notes", "id": f"in.({batch})"})
            r.raise_for_status()
            docs.update({d["id"]: d for d in r.json()})
        for did, (cm, sf) in canon.items():
            d = docs.get(did)
            if not d:
                rechazadas.append({"document_id": did, "source_file": sf, "fallo": "no existe en documents"}); continue
            fallos = []
            if d["status"] != "active":
                fallos.append(f"status={d['status']}")
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS, params={"select": "product_model", "document_id": f"eq.{did}", "limit": "2000"})
            r.raise_for_status()
            cnt = Counter(x["product_model"] for x in r.json())
            if not cnt or set(cnt) != {cm}:
                fallos.append(f"chunks no llevan el canónico al 100 %: {dict(cnt)}")
            if (d["product_model"] or "") == cm:
                sin_cambio.append({"document_id": did, "source_file": d["source_pdf_filename"], "pm": cm}); continue
            if fallos:
                rechazadas.append({"document_id": did, "source_file": d["source_pdf_filename"], "fallo": "; ".join(fallos)}); continue
            plan.append({"document_id": did, "source_file": d["source_pdf_filename"], "pm_prev": d["product_model"],
                         "pm_nuevo": cm, "n_chunks": sum(cnt.values()), "notes_prev": d.get("notes")})
        print(f"{modo}: {len(plan)} retags planificados · {len(sin_cambio)} ya alineados · {len(rechazadas)} rechazados por guarda")
        for p in plan:
            print(f"  {p['source_file'][:45]!r}: {p['pm_prev']!r} → {p['pm_nuevo']!r} ({p['n_chunks']} chunks)")
        for r_ in rechazadas:
            print(f"  NO TOCAR {r_['source_file']!r}: {r_['fallo']}")
        aplicado, abortados = [], []
        if args.aplicar and plan:
            utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for p in plan:
                nota = (p["notes_prev"] + " | " if p["notes_prev"] else "") + \
                       f"s324d {utc}: documents.product_model {p['pm_prev']!r} → {p['pm_nuevo']!r} (alineado con chunks_v2 tras E3 F3a; TECH_DEBT #88)"
                r = c.patch(f"{SB}/rest/v1/documents", headers={**HS, "Prefer": "return=representation"},
                            params={"id": f"eq.{p['document_id']}", "product_model": f"eq.{p['pm_prev']}"},   # CAS
                            json={"product_model": p["pm_nuevo"], "notes": nota})
                r.raise_for_status()
                rows = r.json()
                if len(rows) != 1:
                    abortados.append({"document_id": p["document_id"], "motivo": f"CAS no casó ({len(rows)} filas): el pm cambió entre censo y escritura"})
                    continue
                aplicado.append({"document_id": p["document_id"], "product_model": rows[0]["product_model"]})
            # verificación en el mismo turno
            for a in aplicado:
                r = c.get(f"{SB}/rest/v1/documents", headers=HS, params={"select": "id,product_model", "id": f"eq.{a['document_id']}"})
                r.raise_for_status()
                assert r.json()[0]["product_model"] == canon[a["document_id"]][0], a
    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recibo = {"que_es": __doc__.strip().splitlines()[0], "modo": modo, "utc": utc, "fuente_lote": str(E3.relative_to(ROOT)),
              "plan": plan, "sin_cambio": sin_cambio, "rechazadas": rechazadas, "aplicado": aplicado, "abortados_cas": abortados,
              "reversion": "PATCH documents set product_model=<pm_prev> (y notes_prev) por document_id, desde este recibo"}
    out = ROOT / "evals" / f"s324d_retag_documents_pm_{modo}_{utc}.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print("recibo:", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
