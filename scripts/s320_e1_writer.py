# -*- coding: utf-8 -*-
"""s320 E1 — WRITER DUAL de doc_map (freeze-contract v1, tier A ejecutable).

Dos operaciones, ambas vía la puerta (`write_jsonl` valida el conjunto entero):
- **ALTA** (tier A ∩ alta del censo de reconciliación: 26): filas nuevas con la
  propuesta derivada (resolve exact/alias + prefijo de marca + vendido_bajo),
  provenance por entry.
- **RECONCILIACIÓN** (las 11 de TODOS los tiers — reparan mapeos YA adjudicados,
  no añaden juicio nuevo): la fila existente con el mismo source_file cambia su
  `document_id` stale (muerto en documents) por el vigente; entries/provenance
  INTACTOS. La colisión (id viejo VIVO) jamás se toca aquí: packet.

Dry-run por defecto; `--aplicar` escribe. Recibo con el diff completo.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.catalog_store import CATALOG_DIR, FILES, write_jsonl  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()

    detalle = json.loads(
        (ROOT / "evals" / "s320_e1_docmap_derivacion_v2_detalle.json")
        .read_text(encoding="utf-8"))
    censo = json.loads(
        (ROOT / "evals" / "s320_e1_reconciliacion_censo_v1.json")
        .read_text(encoding="utf-8"))
    doc_map = [json.loads(l) for l in
               (CATALOG_DIR / FILES["doc_map"]).read_text(encoding="utf-8")
               .splitlines() if l.strip()]

    alta_sources = {r["source_file"] for r in censo["detalle"]["alta"]
                    if r["tier"] == "tier_a"}
    altas = [c["propuesta"] for c in detalle["tier_a"]
             if c["source_file"] in alta_sources]

    recon = {r["source_file"]: r for r in censo["detalle"]["reconciliar"]}
    reconciliadas = []
    for fila in doc_map:
        sf = (fila.get("source_file") or "").strip().lower()
        r = recon.get(sf)
        if r and fila["document_id"] in r["ids_en_mapa"]:
            reconciliadas.append({"source_file": sf,
                                  "de": fila["document_id"],
                                  "a": r["document_id_actual"],
                                  "entries_preservadas":
                                      len(fila.get("entries") or [])})
            fila["document_id"] = r["document_id_actual"]

    ya = {f["document_id"] for f in doc_map}
    nuevas = [a for a in altas if a["document_id"] not in ya]
    doc_map_final = doc_map + nuevas

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recibo = {
        "que_es": ("Writer dual E1 (freeze evals/s320_e1_freeze_contract_v1.md): "
                   "altas tier-A + reconciliaciones de id stale (entries "
                   "intactas). Colisiones y tiers B/C: packet, jamás aquí."),
        "modo": "aplicar" if args.aplicar else "dry-run",
        "utc": utc,
        "altas_planificadas": len(altas),
        "altas_escritas": len(nuevas) if args.aplicar else 0,
        "reconciliaciones": reconciliadas,
        "doc_map_antes": len(doc_map), "doc_map_despues": len(doc_map_final),
        "detalle_altas": altas,
    }
    if args.aplicar:
        write_jsonl("doc_map", doc_map_final)  # valida el conjunto o revienta
        recibo["validacion"] = "write_jsonl PASS (conjunto entero)"
    destino = (ROOT / "evals" /
               f"s320_e1_writer_{recibo['modo']}_{utc}.json")
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"{recibo['modo']}: altas {len(altas)} ({len(nuevas)} nuevas) · "
          f"reconciliaciones {len(reconciliadas)} · "
          f"doc_map {len(doc_map)}→{len(doc_map_final)}")
    print(f"recibo -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
