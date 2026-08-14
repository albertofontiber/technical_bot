# -*- coding: utf-8 -*-
"""s321 E3 — Sonda de ATESTACIÓN (solo lectura; reglas del dúo r25).

Para cada pareja pm_prev→canónico del dry-run (99), decide su DESTINO con
contabilidad cerrada (cada pareja cae en EXACTAMENTE un cubo):

1. FORMA: pm_prev y canónico se matchean MUTUAMENTE con el patrón imatch
   (la semántica del filtro, bidireccional — r25/Fable: la raíz, no blacklists).
2. PM_PREV_PRODUCTO_REAL → PACKET (r25/Sol M3): si pm_prev resuelve en el
   catálogo o vive en el snapshot del detector, re-tagearlo pierde findability
   de un término válido — decisión multi-valor de Alberto.
3. ATESTADA_AUTO: el canónico es el token-producto DOMINANTE del contenido
   del doc (frecuencia vs los demás términos del catálogo presentes) Y sin
   variantes HERMANAS en content (sonda sobre TODAS las aplicables) →
   auto-aplicable.
4. AMBIGUA_HERMANAS → PACKET: hermanas de la base del canónico en content.
5. NO_DOMINANTE → PACKET: el canónico no domina (mención ≠ sujeto — Sol M1).
6. NO_ATESTADA → PACKET: el canónico no aparece en el content (jamás descarte).

Extractos muestreados al recibo para la adjudicación (evidencia correlacionada
DECLARADA: doc_map s83 y content nacen del mismo manual — Sol M2).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
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
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}


def _pat(t: str) -> re.Pattern:
    return re.compile(model_to_imatch_pattern(t).replace(r"\y", r"\b"),
                      re.IGNORECASE)


def main() -> int:
    dry = json.loads(
        (ROOT / "evals" / "s321_e3_writer_dry-run_20260813T220152Z.json")
        .read_text(encoding="utf-8"))
    cat = cargar_catalogo(ROOT / "data" / "catalog")
    snapshot = json.loads((ROOT / "data" / "model_catalog.json")
                          .read_text(encoding="utf-8"))
    modelos_detector = {str(m.get("model") if isinstance(m, dict) else m).lower()
                        for m in snapshot.get("models", [])}
    # términos del catálogo para dominancia (canonical de consumibles)
    terminos_cat = {p.get("canonical_model") for p in cat.products.values()
                    if p.get("canonical_model") and not p.get("candidate")}

    destinos: dict[str, list] = {k: [] for k in (
        "forma", "pm_prev_producto_real", "atestada_auto",
        "ambigua_hermanas", "no_dominante", "no_atestada")}

    with abierto(timeout=30.0) as c:
        for d in dry["detalle"]:
            did, canonico = d["document_id"], d["canonical_model"]
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "content",
                              "document_id": f"eq.{did}", "limit": "1000"})
            r.raise_for_status()
            contenido = "\n".join((x.get("content") or "") for x in r.json())
            pat_canon = _pat(canonico)
            hits_canon = len(pat_canon.findall(contenido))
            # dominancia: vs los demás términos de catálogo presentes
            otros = Counter()
            for t in terminos_cat:
                if t == canonico:
                    continue
                n = len(_pat(t).findall(contenido))
                if n:
                    otros[t] = n
            # hermanas: misma base alfabética que el canónico
            base = re.match(r"[A-Za-z]+[- ]?\d*", canonico)
            base_pref = (base.group(0).strip("- ").lower() if base else
                         canonico.lower())
            hermanas = {t: n for t, n in otros.items()
                        if t.lower().startswith(base_pref) and t != canonico}
            extracto = ""
            m0 = pat_canon.search(contenido)
            if m0:
                a = max(0, m0.start() - 80)
                extracto = contenido[a:m0.end() + 80].replace("\n", " ")

            for op in d["ops"]:
                pm_prev = op["pm_prev"]
                fila = {"document_id": did, "source_file": d["source_file"],
                        "pm_prev": pm_prev, "canonico": canonico,
                        "chunks": op["esperado"], "hits_canon": hits_canon,
                        "otros_top": dict(otros.most_common(4)),
                        "hermanas": hermanas, "extracto": extracto}
                # 1. forma: mismo contenido alfanumérico (acentos plegados) Y
                # mismo multiconjunto de signos con carga semántica {+,*,/}.
                # (El test bidireccional imatch falló por diseño del patrón:
                # solo opcionaliza separadores PRESENTES — asimétrico. Y
                # mal-clasificar forma→packet es fail-safe: cuesta un vistazo.)
                import unicodedata as _ud

                def _nk(s):
                    plano = _ud.normalize("NFKD", s or "")
                    plano = "".join(ch for ch in plano
                                    if not _ud.combining(ch)).lower()
                    return re.sub(r"[^a-z0-9]", "", plano)

                def _signos(s):
                    return sorted(ch for ch in (s or "") if ch in "+*/")

                if (_nk(pm_prev) == _nk(canonico)
                        and _signos(pm_prev) == _signos(canonico)):
                    destinos["forma"].append(fila)
                    continue
                # 2. pm_prev producto real → packet. SOLO el catálogo GOBERNADO
                # (r25-bis: la membresía en el snapshot del detector era
                # CIRCULAR — el snapshot nació de estos mismos pm y contiene
                # la basura que limpiamos).
                partes = ([p.strip() for p in pm_prev.split("/")]
                          if "/" in pm_prev else [pm_prev])
                if any(cat.resolve(p) is not None for p in partes):
                    destinos["pm_prev_producto_real"].append(fila)
                    continue
                # 3-6. atestación
                if hits_canon == 0:
                    destinos["no_atestada"].append(fila)
                elif hermanas:
                    destinos["ambigua_hermanas"].append(fila)
                elif otros and hits_canon < max(otros.values()):
                    destinos["no_dominante"].append(fila)
                else:
                    destinos["atestada_auto"].append(fila)

    total = sum(len(v) for v in destinos.values())
    n_pares_dry = sum(len(d["ops"]) for d in dry["detalle"])
    assert total == n_pares_dry, f"contabilidad rota: {total} != {n_pares_dry}"

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recibo = {
        "que_es": ("E3 atestación r25: destino por pareja con contabilidad "
                   "cerrada. AUTO = forma + atestada_auto; el resto = packet."),
        "utc": utc,
        "total_parejas": total,
        "por_destino": {k: len(v) for k, v in destinos.items()},
        "chunks_por_destino": {k: sum(f["chunks"] for f in v)
                               for k, v in destinos.items()},
        "detalle": destinos,
    }
    destino_f = ROOT / "evals" / f"s321_e3_atestacion_v1.json"
    destino_f.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print(f"parejas {total} · " + " · ".join(
        f"{k} {len(v)}({sum(f['chunks'] for f in v)}ch)"
        for k, v in destinos.items()))
    print(f"recibo -> {destino_f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
