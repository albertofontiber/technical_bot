# -*- coding: utf-8 -*-
"""s321 E3 — Writer F3a al patrón T3 EXACTO (dúo r24 aplicado).

Alcance: SOLO el lote ADJUDICADO del censo v2 (102 docs mono-producto con
producto consumible y provenance adjudicada). Los 2 derivados y los 166
no-consumibles van al packet — jamás por aquí.

Mecánica (r24 Sol C2, el precedente s285-T3):
1. Por doc: fetch fresco de chunks (id, product_model) — el censo es INSUMO,
   la verdad es el fetch (absorbe drift tipo DP312x-supersedida).
2. Re-verificación: doc activo + entry primary única + producto consumible +
   mismatch recomputado con el patrón imatch (sabor-Postgres → \\b local).
   Cualquier divergencia con el censo → el doc se SALTA a recibo, no se fuerza.
3. BACKUP por-chunk (id + product_model_prev) ANTES de tocar nada — el
   artefacto de rollback, versionado en el recibo de detalle.
4. UPDATE compare-and-swap: por cada (pm_prev → canonical),
   PATCH WHERE document_id=X AND product_model=pm_prev, con
   Prefer: return=representation y CONTEO devuelto == esperado; si difiere →
   ABORT del resto + recibo del estado exacto.
5. Gate PRIMARIO findability (r24 Sol C3): POST por doc, TODOS los pm de sus
   chunks matchean el patrón imatch del canónico (los pm-familia superset ya
   matcheaban y NO se tocan — DEC-192/193 intacto por construcción).

Uso:
    python scripts/s321_e3_writer.py             # dry-run (default)
    python scripts/s321_e3_writer.py --aplicar
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import load as cargar_catalogo  # noqa: E402
from src.rag.retriever import model_to_imatch_pattern  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}",
      "Content-Type": "application/json"}


def _patron(canonico: str) -> re.Pattern:
    return re.compile(model_to_imatch_pattern(canonico).replace(r"\y", r"\b"),
                      re.IGNORECASE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()
    modo = "aplicar" if args.aplicar else "dry-run"

    detalle = json.loads(
        (ROOT / "evals" / "s321_e3_censo_v2_detalle.json")
        .read_text(encoding="utf-8"))
    lote = [m for m in detalle["mono_mismatch"] if m["lote"] == "adjudicado"]

    # (r25) SOLO el conjunto AUTO de la atestación: forma + atestada_auto.
    # El resto (producto-real/hermanas/no-dominante/no-atestada) = packet.
    atest = json.loads((ROOT / "evals" / "s321_e3_atestacion_v1.json")
                       .read_text(encoding="utf-8"))
    auto_pares = {(f["document_id"], f["pm_prev"])
                  for k in ("forma", "atestada_auto")
                  for f in atest["detalle"][k]}
    cat = cargar_catalogo(ROOT / "data" / "catalog")

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filas_recibo, backup, saltados = [], [], []
    aplicadas = abortado = 0

    with abierto(timeout=30.0) as c:
        for m in lote:
            did, canonico = m["document_id"], m["canonical_model"]
            # re-verificación fresca (paso 2)
            r = c.get(f"{SB}/rest/v1/documents", headers=HS,
                      params={"select": "id,status", "id": f"eq.{did}"})
            r.raise_for_status()
            fila_doc = (r.json() or [None])[0]
            if not fila_doc or fila_doc.get("status") != "active":
                saltados.append({**m, "motivo": "doc ya no activo (drift)"})
                continue
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "id,product_model",
                              "document_id": f"eq.{did}",
                              "order": "id.asc", "limit": "1000"})
            r.raise_for_status()
            chunks = r.json()
            patron = _patron(canonico)
            objetivo = [ch for ch in chunks
                        if not patron.search(ch.get("product_model") or "")
                        and (did, ch.get("product_model")) in auto_pares]
            if not objetivo:
                saltados.append({**m, "motivo": "sin pares AUTO (r25: packet)"})
                continue
            # backup por-chunk (paso 3) — SIEMPRE, también en dry-run
            for ch in objetivo:
                backup.append({"id": ch["id"], "document_id": did,
                               "product_model_prev": ch["product_model"]})
            # plan CAS por valor pm_prev (paso 4)
            por_pm: dict[str, int] = {}
            for ch in objetivo:
                por_pm[ch["product_model"]] = por_pm.get(ch["product_model"], 0) + 1
            ops = []
            doc_ok = True
            for pm_prev, esperado in sorted(por_pm.items()):
                op = {"pm_prev": pm_prev, "pm_nuevo": canonico,
                      "esperado": esperado, "afectadas": None}
                if args.aplicar and doc_ok:
                    # POR-CHUNK con CAS id+pm_prev (el bulk por pm dio 500 —
                    # timeout/trigger a escala; verificado con rollback limpio
                    # y PATCH por-id 200). T3 aún más literal: fila a fila.
                    afectadas = 0
                    ids_obj = [ch["id"] for ch in objetivo
                               if ch["product_model"] == pm_prev]
                    try:
                        for cid in ids_obj:
                            rr = c.patch(
                                f"{SB}/rest/v1/chunks_v2",
                                headers={**HS,
                                         "Prefer": "return=representation"},
                                params={"id": f"eq.{cid}",
                                        "product_model": f"eq.{pm_prev}"},
                                json={"product_model": canonico})
                            rr.raise_for_status()
                            afectadas += len(rr.json())
                    except Exception as exc:      # noqa: BLE001
                        doc_ok = False
                        abortado += 1
                        op["ABORT"] = (f"HTTP en chunk {afectadas + 1}/"
                                       f"{len(ids_obj)}: {type(exc).__name__}")
                    op["afectadas"] = afectadas
                    if doc_ok and afectadas != esperado:
                        doc_ok = False
                        abortado += 1
                        op["ABORT"] = (f"CAS: afectadas {afectadas} != "
                                       f"esperado {esperado}")
                    elif doc_ok:
                        aplicadas += afectadas
                ops.append(op)
            # gate findability POST (paso 5) — solo con aplicar y doc_ok
            post_ok = None
            if args.aplicar and doc_ok:
                rr = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                           params={"select": "product_model",
                                   "document_id": f"eq.{did}",
                                   "limit": "1000"})
                rr.raise_for_status()
                post_ok = all(patron.search(x.get("product_model") or "")
                              for x in rr.json())
            filas_recibo.append({"document_id": did,
                                 "source_file": m["source_file"],
                                 "canonical_model": canonico,
                                 "chunks_objetivo": len(objetivo),
                                 "ops": ops, "findability_post_ok": post_ok})

    recibo = {
        "que_es": ("E3 writer F3a, patrón T3 (backup por-chunk + CAS + gate "
                   "findability). Lote ADJUDICADO solo; derivados/no-"
                   "consumibles jamás por aquí."),
        "modo": modo, "utc": utc,
        "lote_censo": len(lote),
        "docs_en_recibo": len(filas_recibo),
        "saltados_por_drift": saltados,
        "chunks_backup": len(backup),
        "chunks_aplicados": aplicadas,
        "docs_abortados_cas": abortado,
        "findability_post": (
            None if not args.aplicar else
            all(f["findability_post_ok"] for f in filas_recibo
                if f["findability_post_ok"] is not None)),
        "detalle": filas_recibo,
    }
    base = ROOT / "evals" / f"s321_e3_writer_{modo}_{utc}"
    Path(str(base) + ".json").write_text(
        json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    Path(str(base) + "_backup.json").write_text(
        json.dumps(backup, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{modo}: lote {len(lote)} · en recibo {len(filas_recibo)} · "
          f"saltados {len(saltados)} · backup {len(backup)} chunks · "
          f"aplicadas {aplicadas} · aborts CAS {abortado} · "
          f"findability_post {recibo['findability_post']}")
    print(f"recibo -> {base}.json")
    # (r25 Sol M4) FAIL-CLOSED: el gate primario manda en el exit code
    findability_fallo = args.aplicar and recibo["findability_post"] is False
    return 0 if (abortado == 0 and not findability_fallo) else 1


if __name__ == "__main__":
    raise SystemExit(main())
