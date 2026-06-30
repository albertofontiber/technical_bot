#!/usr/bin/env python3
"""retrieval_miss_diagnose.py (s85·B1) — diagnóstico de cada retrieval-miss por (CANAL × MOTIVO).

CANAL = el paso del retrieval que debió cazar el chunk-valor y falló:
  - IDENTIDAD/model-filter : el manual de la familia CORRECTA no entra al pool (solo familia
                             equivocada). Señal: ningún chunk de gold_family en el pool. [hp018]
  - VECTOR/semántico       : el chunk-valor existe pero el embedding no lo rankea al top-50.
  - LÉXICO/keyword         : el token del valor/modelo existe pero keyword/content no lo surfacea.
  - PROFUNDIDAD/ranking    : el manual correcto SÍ está en el pool pero el chunk-valor rankea >50
                             (competición within-doc).
MOTIVO = el por qué (el fix concreto):
  - es-en (valor en columna EN) · vocab informal↔formal · familia-mal-tagueada · within-doc ·
    chunking/extracción · token-corto/formato.

Input: la salida family-aware (famtie) con los misses + el pin del pool. Para cada miss, el
chunk-valor = los chunks del MANUAL que el juez acreditó (votos≥THRESH ∩ manual_pin, same-family).
Se analiza por qué ese chunk no entró al pool.

Uso: python scripts/retrieval_miss_diagnose.py evals/s85_retrieval_miss_DEF.yaml
(corre DESPUÉS de la pasada definitiva + dúo del famtie aprobado).
"""
import os, sys, re, json
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2"); os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"; os.environ["HYDE_ENABLED"] = "false"
import yaml
from src.rag.retriever import vector_search, keyword_search, content_search, extract_product_models
from scripts.retrieval_miss_famtie import rederive, fam_norm, gold_family, THRESH_FIRM
from scripts.audit_locator import fact_match_score

EN_HINT = re.compile(r"\b(the|and|with|fault|earth|ground|alarm|output|input|circuit|loop|reset|"
                     r"detector|zone|level|default|value|range|terminal|relay|short|open)\b", re.I)
ES_HINT = re.compile(r"\b(el|la|los|de|con|fallo|tierra|alarma|salida|entrada|circuito|lazo|"
                     r"nivel|valor|rango|terminal|relé|rearme|avería|zona)\b", re.I)


def _lang(text: str) -> str:
    en = len(EN_HINT.findall(text or "")); es = len(ES_HINT.findall(text or ""))
    return "EN" if en > es * 1.5 else ("ES" if es > en * 1.5 else "?")


# Levers accionables por (punto-de-fallo × motivo) — para B2.
LEVER = {
    ("PRE-RETRIEVAL", "identidad"): "model-filter / resolución de identidad (familia correcta al pool)",
    ("PRE-RETRIEVAL", "superseding"): "detección+marcado de superseded (pre-exclude deprecados)",
    ("RECALL", "es-en"): "es-en: alinear/traducir columna EN en vector+keyword",
    ("RECALL", "vocab"): "HyDE / expansión de query / sinónimos",
    ("RECALL", "token-corto"): "keyword/format-aware para tokens cortos/códigos",
    ("RECALL", "chunking"): "re-chunk / extracción (el valor se parte/pierde)",
    ("DEPTH", "within-doc"): "within-doc surfacing / merge / diversify-depth",
    ("DEPTH", "competicion"): "merge/ranking depth (el candidato cae del top-50)",
}


def diagnose_miss(gold: dict, miss: dict, pin: list[dict], val_chunks: list[dict],
                  wide_vids: list[str], kw_ids: set[str]) -> dict:
    """Clasifica el miss en DOS ejes ORTOGONALES:
      punto_fallo (MECE): PRE-RETRIEVAL | RECALL | DEPTH
      motivo (raíz): identidad | superseding | es-en | vocab | within-doc | chunking | token-corto
    val_chunks = chunks del manual (same-family) que el juez acreditó (el dato vive ahí)."""
    q = gold["question"]
    gfam = set(miss.get("gold_family") or [])
    pool_fams = {fam_norm(c.get("pm")) for c in pin}
    pool_srcs = {c.get("src") for c in pin}
    val_ids = {c.get("id") for c in val_chunks}
    val_srcs = {c.get("source_file") for c in val_chunks}

    # SEÑALES (ortogonales, computadas todas)
    family_in_pool = bool(gfam & pool_fams) if gfam else None      # ¿familia correcta en pool?
    manual_in_pool = bool(val_srcs & pool_srcs)                    # ¿el manual del valor en pool (otros chunks)?
    in_wide_vector = bool(val_ids & set(wide_vids))               # ¿candidato en vector-top-200?
    vrank = min([wide_vids.index(i) + 1 for i in val_ids if i in wide_vids], default=None)
    in_keyword = bool(val_ids & kw_ids)                           # ¿candidato vía keyword?
    is_candidate = in_wide_vector or in_keyword
    val_lang = _lang(" ".join((c.get("content") or "")[:800] for c in val_chunks))
    q_lang = _lang(q + " " + miss.get("valor", ""))
    es_en = (val_lang == "EN" and q_lang == "ES")
    short_tok = len(re.sub(r"\s", "", miss.get("valor", ""))) <= 4

    # EJE 1 — PUNTO DE FALLO (MECE, secuencial):
    if gfam and (family_in_pool is False) and not is_candidate and not manual_in_pool:
        punto = "PRE-RETRIEVAL"        # el manual de la familia correcta ni aparece → filtrado/no-surfaceado
    elif is_candidate:
        punto = "DEPTH"               # era candidato (vector-200/keyword) pero no llegó al top-50
    else:
        punto = "RECALL"             # ni vector-200 ni keyword lo trajeron como candidato

    # EJE 2 — MOTIVO (raíz, ortogonal — el dominante):
    if punto == "PRE-RETRIEVAL":
        motivo = "identidad"          # (superseding se marca aparte si el doc es deprecado — TODO transversal)
    elif manual_in_pool:
        motivo = "within-doc"         # el manual está en pool, el chunk-valor compite
    elif es_en:
        motivo = "es-en"
    elif short_tok:
        motivo = "token-corto"
    elif punto == "DEPTH":
        motivo = "competicion"
    else:
        motivo = "vocab"             # recall sin es-en/token-corto → vocab/chunking (refinar con contenido)

    lever = LEVER.get((punto, motivo)) or LEVER.get((punto, "competicion")) or "revisar manual"
    return {"qid": miss["qid"], "valor": miss["valor"], "punto_fallo": punto, "motivo": motivo,
            "lever": lever,
            "señales": {"family_in_pool": family_in_pool, "manual_in_pool": manual_in_pool,
                        "in_wide_vector": in_wide_vector, "vector_rank": vrank,
                        "in_keyword": in_keyword, "val_lang": val_lang, "es_en": es_en,
                        "short_tok": short_tok}}


def _fetch_content(ids: list[str]) -> dict:
    import httpx
    from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
    H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
    out = {}
    for i in range(0, len(ids), 40):
        ch = ids[i:i + 40]; q = ",".join(f'"{x}"' for x in ch)
        try:
            r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H,
                          params={"select": "id,content", "id": f"in.({q})"}, timeout=20)
            for x in r.json():
                out[x["id"]] = x.get("content")
        except Exception:
            pass
    return out


def main(run_path: str):
    fam = rederive(run_path)
    d = yaml.safe_load(open(run_path, encoding="utf-8"))
    res_by_qid = {r["qid"]: r for r in d["reps"][0]["results"]}
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(os.path.join(os.getcwd(), "evals", "gold_answers_v1.yaml"), encoding="utf-8"))}
    # cache por gold de vector-wide + keyword (varios misses comparten gold)
    wide_cache, kw_cache = {}, {}
    out = []
    for miss in fam["misses"]:
        qid = miss["qid"]; res = res_by_qid[qid]; g = golds[qid]; q = g["question"]
        man = {c["id"]: c for c in res.get("manual_pin", [])}
        fact = next((f for f in res["facts"] if f["valor"] == miss["valor"]), {})
        sup = [i for i, v in (fact.get("votes") or {}).items() if v >= THRESH_FIRM and i in man]
        cont = _fetch_content(sup)
        val_chunks = [{"id": i, "source_file": man[i].get("src"), "pm": man[i].get("pm"),
                       "content": cont.get(i, "")} for i in sup]
        if qid not in wide_cache:
            try:
                wide_cache[qid] = [c.get("id") for c in vector_search(q, 200, 0.0, None, None, None)]
            except Exception:
                wide_cache[qid] = []
            kw = set()
            for m in extract_product_models(q):
                try:
                    kw |= {c.get("id") for c in keyword_search(m, limit=30)}
                except Exception:
                    pass
            kw_cache[qid] = kw
        out.append(diagnose_miss(g, miss, res.get("pool_pin", []), val_chunks,
                                 wide_cache[qid], kw_cache[qid]))
    from collections import Counter
    print("retrieval-miss FAMILY-AWARE =", fam["retrieval_miss_family"])
    print("\n=== (PUNTO-FALLO × MOTIVO) por miss ===")
    for o in out:
        print(f"  {o['qid']:8} {o['valor'][:22]!r:24} [{o['punto_fallo']:13}|{o['motivo']:12}] → {o['lever']}")
    print("\n=== distribución PUNTO-FALLO ===", dict(Counter(o["punto_fallo"] for o in out)))
    print("=== distribución MOTIVO ===", dict(Counter(o["motivo"] for o in out)))
    json.dump({"misses": out, "retrieval_miss_family": fam["retrieval_miss_family"]},
              open(os.path.join(os.getcwd(), "evals", "s85_b1_diagnosis.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "evals/s85_retrieval_miss_DEF.yaml")
