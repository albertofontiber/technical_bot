#!/usr/bin/env python3
"""Paso 0 (s78) — diagnóstico de RAÍZ de los 16 retrieval-miss por EJE DE IDENTIDAD (judge-free, $0).

NO repite s71 (que clasifica DÓNDE muere en el pipeline). Añade el eje ortogonal: ¿el gold falla
porque la IDENTIDAD del dato está rota (product_model mal/ausente/colapsado) o porque el chunk
bien-etiquetado está enterrado? Separar eso decide el FIX (backfill de identidad vs palanca de
retrieval) y evita la trampa de arreglar 1 gold sin ver la clase.

Clases (eje identidad):
  CLEAN          — lookup_model_manufacturer(M) != None: el modelo tiene su etiqueta propia →
                   el fallo es de RETRIEVAL puro (clase B), no de identidad.
  FAMILY-COLLAPSE— M no existe como product_model, pero SÍ sus variantes/familia (mismo prefijo,
                   misma marca): CAD-150→CAD-150-8/R, ZXe→ZX2e/ZX5e. (clase A)
  MIS-ATTRIB     — el contenido menciona M pero sus chunks están etiquetados bajo product_models
                   AJENOS (SDX-751→LOCAL-360). M no tiene identidad. (clase A)
  SPLIT          — M aparece bajo >1 fabricante (RP1r: Morley + Notifier). (clase A)
  CORPUS-GAP     — ni product_model ni contenido → el dato quizá no está. (clase C)
  NO-MODEL       — la query no extrae modelo (query temática) → no es identidad-de-modelo.

Señales = corpus real (funciones reales + PostgREST, anti-bias #40). La clase es HEURÍSTICA;
el alias-paraguas (ZXe) necesita criterio humano → se marca y se afina leyendo. Read-only.
"""
from __future__ import annotations
import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
import re
import sys
from pathlib import Path
import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
sys.path.insert(0, str(ROOT))

import scripts.gold_store as gold_store  # noqa: E402
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, CHUNKS_TABLE  # noqa: E402
from src.rag import series_registry as _series  # noqa: E402
from src.rag.retriever import extract_product_models, lookup_model_manufacturer  # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

# Los 16 RETRIEVAL-miss (s71_classification_v2.yaml, categoria=RETRIEVAL-miss) + su detalle s71.
S71 = yaml.safe_load((ROOT / "evals" / "s71_classification_v2.yaml").read_text(encoding="utf-8"))
RET16 = [q for q, v in S71.items() if v.get("categoria") == "RETRIEVAL-miss"]


def fetch(params, cap=3000):
    rows, off = [], 0
    with httpx.Client(timeout=30.0) as c:
        while True:
            r = c.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}", headers=H,
                      params={**params, "limit": "1000", "offset": str(off)})
            r.raise_for_status(); b = r.json(); rows += b
            if len(b) < 1000 or off >= cap:
                break
            off += 1000
    return rows


def agg_pm_mfr(rows):
    d = {}
    for r in rows:
        k = (r.get("product_model"), r.get("manufacturer"))
        d[k] = d.get(k, 0) + 1
    return sorted([{"pm": k[0], "mfr": k[1], "n": n} for k, n in d.items()], key=lambda x: -x["n"])


def diagnose(model: str):
    core = _series.normalize_model(model or "")
    prefix = (re.match(r"^[A-Za-z]+", model or "") or [""])[0]  # "ZX" de "ZXe", "CAD" de "CAD-150"
    lookup = lookup_model_manufacturer(model) if model else None

    # familia/variantes: product_model que comparten prefijo alfabético (o substring-core)
    fam = agg_pm_mfr(fetch({"product_model": f"ilike.{prefix}*", "select": "product_model,manufacturer"})) if prefix else []
    fam = [f for f in fam if f["pm"]]
    core_match = [f for f in fam if core and (core in _series.normalize_model(f["pm"]) or _series.normalize_model(f["pm"]) in core)]
    # dónde vive el contenido que menciona M (revela mis-atribución)
    hosts = agg_pm_mfr(fetch({"content": f"ilike.*{model}*", "select": "product_model,manufacturer"}, cap=1000))[:8] if model else []
    mfrs_fam = sorted({f["mfr"] for f in core_match}) if core_match else sorted({f["mfr"] for f in fam[:6]})

    exact = lookup is not None
    if not model:
        cls = "NO-MODEL"
    elif exact:
        cls = "CLEAN→B(retrieval)"
    elif not fam and not hosts:
        cls = "CORPUS-GAP→C"
    elif core_match and len({f["mfr"] for f in core_match}) > 1:
        cls = "SPLIT→A"
    elif core_match:
        cls = "FAMILY-COLLAPSE→A"
    elif hosts and not any(core in _series.normalize_model(h["pm"] or "") for h in hosts):
        cls = "MIS-ATTRIB→A"
    elif fam:  # mismo prefijo, no substring-core (alias-paraguas tipo ZXe→ZX2e)
        cls = "FAMILY/ALIAS?→A (revisar)"
    else:
        cls = "AMBIGUO (revisar)"
    return {"model": model, "core": core, "prefix": prefix, "lookup": lookup,
            "exact_pm": exact, "core_match": core_match[:6], "fam_top": fam[:6],
            "content_hosts": hosts, "mfrs": mfrs_fam, "clase": cls}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    by_qid = {g.get("qid"): g for g in gold_store.load()}
    out = []
    print(f"=== Paso 0: diagnóstico de identidad de los {len(RET16)} retrieval-miss ===\n")
    for qid in RET16:
        g = by_qid.get(qid, {})
        q = (g.get("question") or "").strip()
        models = extract_product_models(q)
        m0 = models[0] if models else None
        d = diagnose(m0)
        s71 = S71.get(qid, {})
        row = {"qid": qid, "conducta": g.get("conducta_esperada"), "models": models,
               "s71_detalle": s71.get("detalle"), **d}
        out.append(row)
        print(f"{qid:7} [{d['clase']}]  conducta={g.get('conducta_esperada')}")
        print(f"        modelos={models}  lookup({m0})={d['lookup']}")
        if d["core_match"]:
            print(f"        familia(core): " + "; ".join(f"{f['pm']}={f['mfr']}({f['n']})" for f in d["core_match"]))
        elif d["fam_top"]:
            print(f"        prefijo '{d['prefix']}': " + "; ".join(f"{f['pm']}={f['mfr']}({f['n']})" for f in d["fam_top"][:5]))
        if d["content_hosts"]:
            print(f"        content '{m0}' vive en: " + "; ".join(f"{h['pm']}={h['mfr']}({h['n']})" for h in d["content_hosts"][:5]))
        print(f"        s71: {s71.get('detalle')}")
        print()

    # Resumen por clase
    from collections import Counter
    cnt = Counter(r["clase"].split("→")[0].split(" ")[0] for r in out)
    print("=== Resumen por clase de identidad ===")
    for cls, n in cnt.most_common():
        qids = [r["qid"] for r in out if r["clase"].startswith(cls)]
        print(f"  {cls:18} {n:2}  {qids}")

    rep = {"meta": {"proposito": "Paso 0 s78 — eje de identidad de los 16 retrieval-miss. judge-free, reach!=PASS.",
                    "n": len(RET16)}, "diagnostico": out}
    p = ROOT / "evals" / "s78_retrieval16_identity.yaml"
    p.write_text(yaml.safe_dump(rep, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")
    print(f"\nReporte -> {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
