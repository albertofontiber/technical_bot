#!/usr/bin/env python3
"""enunciados_panel.py — panel de DESPLAZAMIENTO por tramo (T0-4, dúo s94b F6).

El guard famtie ±2 solo ve los pools de los 39 golds; a 25-50k surrogates el
desplazamiento en OTRAS queries es invisible. Este panel pinea los pools top-50 de un
set FIJO de queries (39 dev + ~20 reales de query_gaps; held-out FUERA por embargo) y
compara pre/post-tramo: overlap@50 + profundidad del shift.

Uso:
  python scripts/enunciados_panel.py pin            → evals/enunciados_panel_pin.json
  python scripts/enunciados_panel.py compare        → reporte vs el pin
Config: flag/tabla estampados. Umbral pre-registrado (plan s94b): investigar si
overlap<0.8 en >20% del panel (los tramos NO deberían mover queries sanas — los
surrogates solo entran al pool en modo multi-vector y swapeados a padres).
"""
import json
import os
import sys

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ.setdefault("HYDE_ENABLED", "false")
sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
import httpx
import yaml

from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

PIN_PATH = "evals/enunciados_panel_pin.json"
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


def panel_queries() -> list[dict]:
    golds = yaml.safe_load(open("evals/gold_answers_v1.yaml", encoding="utf-8"))
    # EMBARGO (dúo T0 H1 — el filtro v1 comparaba "heldout" y el YAML dice "held-out":
    # código muerto que metía los 12 embargados al pin): solo dev, doble variante.
    qs = [{"src": "gold", "id": g["qid"], "q": g["question"]}
          for g in golds if g.get("split") not in ("held-out", "heldout")]
    assert len(qs) < len(golds), "el filtro de embargo no filtró nada — revisar splits"
    # queries REALES: query_logs (la tabla que existe — query_gaps era 404, dúo H1);
    # limitación declarada: muchas son copias-de-eval de Alberto (feedback s92), pero
    # incluyen las no-gold reales (p.ej. el caso calc-assist del empresario).
    try:
        r = httpx.get(f"{SUPABASE_URL}/rest/v1/query_logs", headers=_H,
                      params={"select": "id,query", "order": "id.desc", "limit": "40"},
                      timeout=15)
        r.raise_for_status()
        vistos = {q["q"] for q in qs}
        for row in r.json():
            texto = (row.get("query") or "").strip()
            if texto and texto not in vistos and len(texto) > 12:
                vistos.add(texto)
                qs.append({"src": "query_logs", "id": f"ql{row['id']}", "q": texto})
            if sum(1 for x in qs if x["src"] == "query_logs") >= 20:
                break
    except Exception as exc:
        print(f"[warn] query_logs no disponible ({exc}) — panel solo-golds-dev")
    return qs


def run_pools() -> dict:
    from src.rag import catalog_resolver
    from src.rag.retriever import retrieve_chunks
    out = {"_config": {"identity_resolve": os.getenv("IDENTITY_RESOLVE", ""),
                       "multivector": os.getenv("ENUNCIADOS_MULTIVECTOR", "off"),
                       "catalog_commit": catalog_resolver.catalog_commit()},
           "pools": {}}
    qs = panel_queries()
    for i, item in enumerate(qs):
        try:
            pool = retrieve_chunks(item["q"], top_k=50)
            out["pools"][item["id"]] = [c.get("id") for c in pool]
        except Exception as exc:
            out["pools"][item["id"]] = {"error": str(exc)}
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(qs)}]")
    return out


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "pin":
        out = run_pools()
        json.dump(out, open(PIN_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"panel pineado: {len(out['pools'])} queries → {PIN_PATH}")
        return 0
    if cmd == "compare":
        pin = json.load(open(PIN_PATH, encoding="utf-8"))
        now = run_pools()
        # freeze-guard (MEDIO del cross-model T0): un shift por catálogo/flags NO es del
        # tramo — configs distintas invalidan la comparación.
        difs = {k: (pin["_config"].get(k), now["_config"].get(k))
                for k in set(pin["_config"]) | set(now["_config"])
                if pin["_config"].get(k) != now["_config"].get(k)}
        if difs:
            print(f"⚠ CONFIG DISTINTA pin-vs-ahora — comparación INVÁLIDA: {difs}")
            return 2
        rows, alerta = [], 0
        for qid, ids0 in pin["pools"].items():
            ids1 = now["pools"].get(qid)
            if not isinstance(ids0, list) or not isinstance(ids1, list) or not ids0:
                continue
            s0, s1 = set(ids0), set(ids1)
            ov = len(s0 & s1) / max(len(s0), 1)
            top10_ov = len(set(ids0[:10]) & set(ids1[:10])) / 10
            # rank-shift REAL (mediana de |Δpos| de los ids comunes)
            pos1 = {cid: i for i, cid in enumerate(ids1)}
            deltas = sorted(abs(i - pos1[cid]) for i, cid in enumerate(ids0) if cid in pos1)
            med_shift = deltas[len(deltas) // 2] if deltas else None
            rows.append((qid, round(ov, 3), round(top10_ov, 2), med_shift))
            if ov < 0.8:
                alerta += 1
        rows.sort(key=lambda r: r[1])
        print("qid        overlap@50  overlap@10  medΔrank  (peores 12)")
        for r in rows[:12]:
            print(f"  {r[0]:10} {r[1]:8} {r[2]:8} {r[3]}")
        frac = alerta / max(len(rows), 1)
        print(f"\nqueries con overlap<0.8: {alerta}/{len(rows)} ({100*frac:.0f}%) — "
              f"umbral pre-registrado: investigar si >20%  → {'⚠ INVESTIGAR' if frac > 0.2 else 'OK'}")
        json.dump({"pin_config": pin["_config"], "now_config": now["_config"],
                   "rows": rows}, open("evals/enunciados_panel_compare.json", "w",
                                       encoding="utf-8"), ensure_ascii=False, indent=1)
        return 1 if frac > 0.2 else 0
    print("uso: pin | compare")
    return 1


if __name__ == "__main__":
    sys.exit(main())
