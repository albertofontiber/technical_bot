#!/usr/bin/env python3
"""s77 GATE-AUDIT — raíz POR-MODELO de los 9 cortes pre-RAG del gate (deploy-prep #49).

Construye sobre s76_prod_reach.py: aquel MIDIÓ que 9/29 NO-PASS se cortan antes del RAG;
este AUDITA POR QUÉ, contra la DB REAL, para que el fix se elija por DATO (no por la
hipótesis "fall-through" que el cierre de s76 pre-supuso — eso es convergencia rápida, y el
cross-model de s76 ya avisó: "sin contrato de identidad el gate-fix solo cambia falsos-rechazos
por falsos-aceptados/mis-atribución", TECH_DEBT #49:1884).

Separa limpio las 3 sub-clases de "catálogo desincronizado" (la raíz importa para el fix):
  (1) gap del parser  → product_model NUNCA es ese string (el modelo solo está en content)
  (2) casing/formato  → la DB guarda otra forma (ZXe vs ZXE) → eq case-sensitive falla
  (3) genuinamente ausente
y, para cada una, si el filtro downstream `_filter_to_query_models` (substring-norm + fail-open,
`retriever.py:1424`) RECUPERARÍA el chunk en fall-through o INANIRÍA el pool.

Anti-bias #40 (regla rectora): llama las FUNCIONES REALES (lookup_model_manufacturer /
manufacturer_in_db / normalize_model), no re-implementa lógica de datos. Re-verifica los counts
"103/157-207/486" de DEC-058 (regla-C / bias #35: no heredar una claim medida sin re-checar el
sustrato). reach != PASS sigue load-bearing: esto confirma RECUPERABILIDAD del corte, NO PASS.

Uso: python scripts/s77_gate_audit.py
Salida: evals/s77_gate_audit.yaml + resumen por consola.
"""
from __future__ import annotations

import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"  # prod, ANTES de importar config/retriever

import sys
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"  # re-asegurar tras load_dotenv
sys.path.insert(0, str(ROOT))

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, CHUNKS_TABLE  # noqa: E402
from src.rag import series_registry as _series  # noqa: E402
from src.rag.retriever import lookup_model_manufacturer, manufacturer_in_db  # noqa: E402

# Probes por modelo cortado (token extraído por el handler -> formas candidatas en DB).
# pm: variantes a sondear en product_model (ilike); content: términos para cobertura de corpus.
PROBES = {
    "CAD-150": {"pm": ["CAD-150", "CAD150", "CAD-150-8"], "content": ["CAD-150", "CAD 150"]},
    "ZXE":     {"pm": ["ZX"],                              "content": ["ZXe", "ZX5e", "ZX2e"]},
    "40-40":   {"pm": ["40-40", "40/40", "4040"],          "content": ["40/40", "40-40"]},
    "ADW535":  {"pm": ["ADW535", "ADW-535"],               "content": ["ADW535", "ADW-535"]},
    "ASD535":  {"pm": ["ASD535", "ASD-535"],               "content": ["ASD535", "ASD-535"]},
    "RP1R":    {"pm": ["RP1"],                             "content": ["RP1R", "RP1r"]},
}

_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
}


def _pm_breakdown(term: str) -> list[dict]:
    """Distinct (product_model, manufacturer) + count donde product_model ilike *term*."""
    rows: list[dict] = []
    offset = 0
    with httpx.Client(timeout=20.0) as client:
        while True:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                headers=_HEADERS,
                params={
                    "product_model": f"ilike.*{term}*",
                    "select": "product_model,manufacturer",
                    "limit": "1000",
                    "offset": str(offset),
                },
            )
            resp.raise_for_status()
            batch = resp.json()
            rows.extend(batch)
            if len(batch) < 1000 or offset >= 9000:  # cap defensivo
                break
            offset += 1000
    agg: dict[tuple, int] = {}
    for r in rows:
        key = (r.get("product_model"), r.get("manufacturer"))
        agg[key] = agg.get(key, 0) + 1
    out = [{"product_model": k[0], "manufacturer": k[1], "n": n}
           for k, n in sorted(agg.items(), key=lambda kv: -kv[1])]
    return out


def _content_count(term: str) -> dict:
    """Total chunks (count exact) cuyo content ilike *term*, + breakdown por marca (muestra)."""
    with httpx.Client(timeout=30.0) as client:
        # total exacto vía Content-Range header
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
            headers={**_HEADERS, "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"},
            params={"content": f"ilike.*{term}*", "select": "manufacturer"},
        )
        resp.raise_for_status()
        cr = resp.headers.get("content-range", "*/0")
        total = int(cr.split("/")[-1]) if "/" in cr else 0
        # breakdown por marca sobre una muestra acotada
        resp2 = client.get(
            f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
            headers=_HEADERS,
            params={"content": f"ilike.*{term}*", "select": "manufacturer", "limit": "2000"},
        )
        resp2.raise_for_status()
    by_mfr: dict[str, int] = {}
    for r in resp2.json():
        m = r.get("manufacturer") or "null"
        by_mfr[m] = by_mfr.get(m, 0) + 1
    return {"total": total, "by_manufacturer_sample": dict(sorted(by_mfr.items(), key=lambda kv: -kv[1]))}


def _filter_would_recover(query_model: str, pm_values: list[str]) -> bool:
    """¿Pasaría algún product_model real el substring-norm de _filter_to_query_models?

    Réplica de la regla nivel-1 (retriever.py:1469-1473): core de la query como substring
    del product_model normalizado (sin separadores, lower).
    """
    core = _series.normalize_model(query_model or "")
    if not core:
        return False
    return any(core in _series.normalize_model(pm or "") for pm in pm_values)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    reach = yaml.safe_load((ROOT / "evals" / "s76_prod_reach.yaml").read_text(encoding="utf-8"))
    cut_rows = [r for r in reach["detalle_29"] if r["outcome"] not in ("REACHES_RAG", "MISSING_GOLD")]

    audited = []
    for row in cut_rows:
        model = row["model"]
        mentioned = row["mentioned_manufacturer"]
        probe = PROBES.get(model, {"pm": [model], "content": [model]})

        # product_model breakdown (unión de las variantes sondeadas, dedup por (pm,mfr))
        pm_seen: dict[tuple, int] = {}
        for t in probe["pm"]:
            for d in _pm_breakdown(t):
                pm_seen[(d["product_model"], d["manufacturer"])] = max(
                    pm_seen.get((d["product_model"], d["manufacturer"]), 0), d["n"])
        pm_breakdown = [{"product_model": k[0], "manufacturer": k[1], "n": n}
                        for k, n in sorted(pm_seen.items(), key=lambda kv: -kv[1])][:12]

        # cobertura de contenido (mejor término)
        content_cov = {}
        for t in probe["content"]:
            content_cov[t] = _content_count(t)

        pm_values = [d["product_model"] for d in pm_breakdown]
        recover = _filter_would_recover(model, pm_values)

        # sub-clase de la desincronización
        lookup_real = lookup_model_manufacturer(model)
        if lookup_real is not None:
            subclase = "mismatch/OEM (modelo SÍ en product_model, otra marca)"
        elif pm_breakdown:
            subclase = "casing/formato (existe product_model con el core, otra forma)"
        elif any(c["total"] > 0 for c in content_cov.values()):
            subclase = "gap-parser (modelo en content, NUNCA en product_model)"
        else:
            subclase = "genuinamente-ausente (ni product_model ni content)"

        audited.append({
            "qid": row["qid"],
            "conducta": row.get("conducta"),
            "model_extraido": model,
            "mentioned_manufacturer": mentioned,
            "gate_outcome": row["outcome"],
            "lookup_model_manufacturer": lookup_real,
            "manufacturer_in_db(mentioned)": manufacturer_in_db(mentioned) if mentioned else None,
            "subclase_raiz": subclase,
            "filtro_recuperaria": recover,
            "product_model_en_DB": pm_breakdown,
            "content_coverage": content_cov,
        })

    report = {
        "meta": {
            "proposito": "Raíz por-modelo de los 9 cortes (deploy-prep #49). reach != PASS.",
            "metodo": "funciones reales (lookup/manufacturer_in_db/normalize_model) + PostgREST "
                      "ilike sobre product_model/content; chunks_v2. Re-verifica counts DEC-058.",
            "n_cortes": len(cut_rows),
        },
        "audit": audited,
    }
    out_path = ROOT / "evals" / "s77_gate_audit.yaml"
    out_path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False, width=100),
                        encoding="utf-8")

    print("=== s77 GATE-AUDIT: raíz por-modelo de los 9 cortes ===\n")
    for a in audited:
        print(f"{a['qid']:7} {a['model_extraido']:9} (menciona {a['mentioned_manufacturer']}) "
              f"[{a['gate_outcome']}]")
        print(f"        lookup={a['lookup_model_manufacturer']}  "
              f"mfr_in_db={a['manufacturer_in_db(mentioned)']}  "
              f"filtro_recupera={a['filtro_recuperaria']}")
        print(f"        subclase: {a['subclase_raiz']}")
        pm = a["product_model_en_DB"]
        if pm:
            top = "; ".join(f"{d['product_model']}={d['manufacturer']}({d['n']})" for d in pm[:5])
            print(f"        product_model en DB: {top}")
        else:
            print(f"        product_model en DB: (ninguno con el core)")
        cov = "; ".join(f"{t}:{c['total']}" for t, c in a["content_coverage"].items())
        print(f"        content coverage: {cov}")
        print()
    print(f"Reporte -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
