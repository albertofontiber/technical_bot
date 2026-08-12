# -*- coding: utf-8 -*-
"""s320 E1 — Censo de RECONCILIACIÓN source_file↔document_id sobre los 279.

Hallazgo de la sonda PRE (recibo s320_e1_sonda_allowed_sources_v1.json): parte
de los «sin entrada» SÍ están en doc_map pero bajo un document_id STALE
(re-ingestas renovaron el UUID). Este censo separa, para los 279 y por tier:
- RECONCILIAR: doc_map tiene el MISMO source_file con OTRO id → UPDATE del id
  (preservando entries/provenance adjudicados) — no es un alta.
- ALTA: source_file genuinamente ausente del mapa.
Además verifica que ningún id stale siga VIVO en documents (si el id viejo
existe activo con OTRO filename = colisión real, a packet, jamás auto-update).
"""
from __future__ import annotations

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

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}


def _norm(s: str) -> str:
    return re.sub(r"\.pdf$", "", (s or "").strip().lower())


def main() -> int:
    detalle = json.loads(
        (ROOT / "evals" / "s320_e1_docmap_derivacion_v2_detalle.json")
        .read_text(encoding="utf-8"))
    doc_map = [json.loads(l) for l in
               (ROOT / "data" / "catalog" / "doc_map.jsonl")
               .read_text(encoding="utf-8").splitlines() if l.strip()]
    por_source = {}
    for e in doc_map:
        por_source.setdefault(_norm(e.get("source_file") or ""), []).append(e)

    with abierto(timeout=30.0) as client:
        r = client.get(f"{SUPABASE_URL}/rest/v1/documents", headers=H,
                       params={"select": "id,source_pdf_filename,status",
                               "order": "id.asc", "limit": "100000"})
        r.raise_for_status()
        todos = r.json()
    doc_por_id = {d["id"]: d for d in todos}

    censo = {"reconciliar": [], "alta": [], "colision": []}
    for tier in ("tier_a", "tier_b", "tier_c", "no_producto"):
        for caso in detalle[tier]:
            sf = caso["source_file"]
            entradas = por_source.get(sf) or []
            registro = {"tier": tier, "source_file": sf,
                        "document_id_actual": caso["document_id"]}
            if not entradas:
                censo["alta"].append(registro)
                continue
            ids_stale = [e["document_id"] for e in entradas]
            vivos = [i for i in ids_stale if i in doc_por_id]
            registro.update({"ids_en_mapa": ids_stale,
                             "ids_stale_aun_vivos": vivos,
                             "n_entries_adjudicadas": sum(
                                 len(e.get("entries") or []) for e in entradas)})
            if vivos:
                # el id viejo sigue existiendo en documents con este u otro
                # filename → colisión real, adjudicación humana
                registro["filenames_de_vivos"] = [
                    doc_por_id[i].get("source_pdf_filename") for i in vivos]
                censo["colision"].append(registro)
            else:
                censo["reconciliar"].append(registro)

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recibo = {
        "que_es": ("Censo de reconciliación source_file↔id de los 279 "
                   "(hallazgo sonda PRE). RECONCILIAR = update de id stale "
                   "muerto preservando entries; ALTA = ausencia real; "
                   "COLISIÓN = id viejo aún vivo → packet."),
        "utc": utc,
        "totales": {k: len(v) for k, v in censo.items()},
        "por_tier": {t: {k: sum(1 for x in v if x["tier"] == t)
                         for k, v in censo.items()}
                     for t in ("tier_a", "tier_b", "tier_c", "no_producto")},
        "detalle": censo,
    }
    destino = ROOT / "evals" / "s320_e1_reconciliacion_censo_v1.json"
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"reconciliar {len(censo['reconciliar'])} · alta {len(censo['alta'])} "
          f"· colisión {len(censo['colision'])}")
    print(f"por tier: {json.dumps(recibo['por_tier'])}")
    print(f"recibo -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
