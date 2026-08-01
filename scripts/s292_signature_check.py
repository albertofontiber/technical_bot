#!/usr/bin/env python3
"""s292 — SIGNATURE-CHECK $0 del hallazgo transversal de s291c.

Hipótesis (diagnóstico cat017#2, no refutado): la vara del acreditador de SOPORTE
es más laxa en granularidad que la del juez de CONVEYED, así que un fact cuyo
carrier real NO se sirvió puede aterrizar como `synthesis-miss` (el soporte
genérico fuerza `reaches_gen=True`) cuando mecánicamente es
RECUPERADO-NO-SERVIDO. Si el patrón se repite, el «rerank 0» del FULL v3.2
(DEC-170) está infracontado.

MÉTODO (determinista, judge-free, misma vara que el instrumento):
para cada synth-miss ESTABLE del FULL v3.2 —
  1. `payload_served` = ¿algún chunk SERVIDO supera `fact_match_score` del valor?
  2. `payload_in_pool_unserved` = ¿algún chunk del POOL NO servido lo supera —
     y con score MAYOR que el mejor servido?
  3. FIRMA = (mejor servido por debajo del suelo del guard L1)
     ∧ (existe carrier no-servido por encima) ⇒ candidato a re-clasificación.
El matcher es el MISMO que el guard L1 del instrumento (`audit_locator`), así que
la firma no inventa vara nueva: mide la asimetría CON la vara existente.

Coste: 0 LLM · 0 jueces · lecturas GET-only de chunks_v2 (por id, cacheadas).
Salida: evals/s292_signature_check_result_v1.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
import httpx  # noqa: E402
import yaml  # noqa: E402

from scripts.audit_locator import fact_match_score  # noqa: E402
from src.rag.toc_detection import is_toc_page  # noqa: E402

# v2 (regla-C contra la propia sonda v1, que dio 0/10 FALSAMENTE tranquilizador):
# la v1 tenía TRES defectos que la hacían ciega a la hipótesis que debía probar —
#   (1) `fact_match_score` es un matcher de ANCHOR léxico: la forma genérica («el
#       modo CLIP requiere licencia») y el payload real («una licencia POR CADA
#       lazo CLIP») comparten tokens ⇒ MISMO score. Es exactamente la distinción
#       de GRANULARIDAD que la hipótesis afirma.  → v2 añade el predicado de
#       CARDINALIDAD (marcador distributivo presente en el hecho y ausente en lo
#       servido = gap de payload), determinista.
#   (2) no aplicaba el kill de TOC que el propio instrumento aplica (H4/s102):
#       eligió una página de ÍNDICE como «carrier» de cat017#2.
#   (3) el desempate estricto (`uscore > sscore`) descartaba los EMPATES, que son
#       justo el caso genérico-vs-payload.
# Marcadores distributivos (es/en) — cerrados, sin LLM.
_CARDINALITY = ("por cada", "para cada", "cada uno", " cada ", "una por", "uno por",
                "per ", "for each", "each ")

FULL = ROOT / "evals" / "s100_factlevel_full_v32_full_20260801.yaml"
OUT = ROOT / "evals" / "s292_signature_check_result_v1.json"
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
# Suelo del guard L1 del instrumento (audit_locator.SCORE_FLOOR - 0.15, el slack
# anti-FN que usa `support_l1_guard_allows`): por debajo, el propio instrumento
# considera que el chunk NO porta el anchor del hecho.
FLOOR = 0.40

_CACHE: dict[str, dict] = {}


def _fetch(ids: list[str]) -> dict[str, dict]:
    missing = [i for i in ids if i and i not in _CACHE]
    for start in range(0, len(missing), 40):
        batch = missing[start:start + 40]
        r = httpx.get(
            f"{URL}/rest/v1/chunks_v2",
            params={"select": "id,content,source_file,page_number,section_title",
                    "id": f"in.({','.join(batch)})"},
            headers=HEADERS, timeout=120,
        )
        for row in r.json():
            _CACHE[str(row["id"])] = row
    return {i: _CACHE[i] for i in ids if i in _CACHE}


def _best(valor: str, texto: str, rows: dict[str, dict]) -> tuple[str | None, float]:
    """Mejor score EXCLUYENDO páginas de índice (kill H4/s102 del instrumento)."""
    best_id, best = None, 0.0
    for cid, row in rows.items():
        content = row.get("content") or ""
        if is_toc_page(f"{row.get('section_title') or ''}\n\n{content}"):
            continue
        score = fact_match_score(valor, texto, content)
        if score is not None and score > best:
            best_id, best = cid, score
    return best_id, best


def _has_cardinality(text: str) -> bool:
    folded = " " + (text or "").lower().replace("\n", " ") + " "
    return any(marker in folded for marker in _CARDINALITY)


def _payload_gap(valor: str, texto: str, served_row: dict | None) -> bool:
    """Gap de GRANULARIDAD: el hecho es distributivo («una por CADA…») y el mejor
    chunk servido no lleva marcador distributivo ⇒ lo servido es la forma
    genérica, no el payload. Determinista, sin LLM."""
    if not _has_cardinality(f"{valor} {texto}"):
        return False
    return not _has_cardinality((served_row or {}).get("content") or "")


def main() -> int:
    data = yaml.safe_load(FULL.read_text(encoding="utf-8"))
    out_rows = []
    for gold in data["per_gold"]:
        served_ids = [str(x) for x in (gold.get("served_ids") or []) if x]
        pool_ids = [str(x) for x in (gold.get("pool_ids") or []) if x]
        unserved = [x for x in pool_ids if x not in set(served_ids)]
        for fact in gold["facts"]:
            if fact.get("clase") != "synthesis-miss":
                continue
            if fact.get("stability") != "stable-miss":
                continue
            valor = fact.get("valor") or ""
            texto = fact.get("texto") or ""
            srv_rows = _fetch(served_ids)
            uns_rows = _fetch(unserved)
            sid, sscore = _best(valor, texto, srv_rows)
            uid, uscore = _best(valor, texto, uns_rows)
            # v2: dos firmas independientes, ambas deterministas.
            # A (anchor-level, la de v1 con ties incluidos): lo servido no llega
            #    al suelo del guard y hay carrier no-servido por encima.
            # B (payload-level, la que prueba la hipótesis de granularidad):
            #    hecho distributivo cuyo mejor servido NO lleva marcador
            #    distributivo, con carrier no-servido que SÍ lo lleva.
            sig_a = bool(sscore < FLOOR and uscore >= FLOOR and uscore >= sscore)
            srv_row = _CACHE.get(sid or "")
            uns_row = _CACHE.get(uid or "")
            gap = _payload_gap(valor, texto, srv_row)
            # v2b (3er defecto de la sonda, cazado en el run v2): el carrier del
            # PAYLOAD no tiene por qué ser el mejor por ANCHOR — se busca en TODO
            # el pool no-servido cualquier fila sobre el suelo que SÍ lleve el
            # marcador distributivo.
            payload_carrier = None
            if gap:
                for cid, prow in uns_rows.items():
                    content = prow.get("content") or ""
                    if is_toc_page(f"{prow.get('section_title') or ''}\n\n{content}"):
                        continue
                    score = fact_match_score(valor, texto, content)
                    if (score is not None and score >= FLOOR
                            and _has_cardinality(content)):
                        payload_carrier = {"id": cid[:8], "score": round(score, 3),
                                           "page": prow.get("page_number"),
                                           "source_file": str(
                                               prow.get("source_file") or "")[:40]}
                        break
            sig_b = bool(gap and payload_carrier)
            row = {
                "key": fact["key"],
                "qid": gold["qid"],
                "n_support_served": fact.get("n_support_served"),
                "best_served": {"id": (sid or "")[:8], "score": round(sscore, 3)},
                "best_unserved_in_pool": {"id": (uid or "")[:8],
                                          "score": round(uscore, 3)},
                "unserved_rank_in_pool": (unserved.index(uid) if uid in unserved
                                          else None),
                "fact_is_distributive": _has_cardinality(f"{valor} {texto}"),
                "served_payload_gap": gap,
                "SIGNATURE_A_anchor": sig_a,
                "SIGNATURE_B_payload": sig_b,
                "SIGNATURE_reclassify": bool(sig_a or sig_b),
                "payload_carrier_unserved": payload_carrier,
            }
            signature = row["SIGNATURE_reclassify"]
            if uid:
                src = _CACHE.get(uid, {})
                row["unserved_carrier"] = {
                    "source_file": str(src.get("source_file") or "")[:40],
                    "page": src.get("page_number"),
                    "section": str(src.get("section_title") or "")[:40],
                }
            out_rows.append(row)
            print(f"  {fact['key'][:36]:36} srv={sscore:.2f} uns={uscore:.2f} "
                  f"distrib={int(row['fact_is_distributive'])} "
                  f"gap={int(gap)} A={int(sig_a)} B={int(sig_b)}")
    hits = [r for r in out_rows if r["SIGNATURE_reclassify"]]
    result = {
        "instrument": "s292_signature_check_result_v1",
        "hypothesis": ("soporte servido solo-genérico (score<L1-floor) + carrier "
                       "no-servido en pool por encima del suelo ⇒ la clase mecánica "
                       "es recuperado-no-servido, no síntesis"),
        "floor": FLOOR,
        "n_stable_synth": len(out_rows),
        "n_signature": len(hits),
        "signature_keys": [r["key"] for r in hits],
        "rows": out_rows,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nFIRMA en {len(hits)}/{len(out_rows)} synth estables: "
          f"{[r['key'][:20] for r in hits]}")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
