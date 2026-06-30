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


def diagnose_miss(gold: dict, miss: dict, pin: list[dict], val_chunks: list[dict]) -> dict:
    """val_chunks = chunks del manual (same-family) que el juez acreditó (el dato vive ahí)."""
    q = gold["question"]
    gfam = set(miss.get("gold_family") or [])
    pool_fams = {fam_norm(c.get("pm")) for c in pin}
    pool_srcs = {c.get("src") for c in pin}
    # CANAL 1 — IDENTIDAD: ¿hay algún chunk de la familia correcta en el pool?
    family_in_pool = bool(gfam & pool_fams) if gfam else None
    # CANAL 4 — PROFUNDIDAD/within-doc: ¿el manual del chunk-valor está en el pool (otros chunks) pero no el valor?
    val_srcs = {c.get("source_file") for c in val_chunks}
    manual_in_pool = bool(val_srcs & pool_srcs)
    # CANAL 2 — VECTOR: rank del chunk-valor en el canal vectorial (top 200)
    vrank = None
    try:
        vres = vector_search(q, 200, 0.0, None, None, None)
        vids = [c.get("id") for c in vres]
        for c in val_chunks:
            if c.get("id") in vids:
                vrank = min(vrank or 1e9, vids.index(c.get("id")) + 1)
    except Exception:
        pass
    # MOTIVO — es-en: ¿el chunk-valor es EN y la query/valor ES?
    val_lang = _lang(" ".join((c.get("content") or "")[:600] for c in val_chunks))
    q_lang = _lang(q + " " + miss.get("valor", ""))
    es_en = (val_lang == "EN" and q_lang == "ES")
    # síntesis de canal × motivo
    if gfam and family_in_pool is False:
        canal = "IDENTIDAD"; motivo = "familia-correcta-no-recuperada (solo familia equivocada en pool)"
    elif manual_in_pool:
        canal = "PROFUNDIDAD/within-doc"; motivo = "manual en pool, chunk-valor compite y rankea >50"
    elif es_en:
        canal = "VECTOR/LÉXICO"; motivo = "es-en (valor en EN, query ES)"
    elif vrank and vrank <= 200:
        canal = "PROFUNDIDAD/VECTOR"; motivo = f"chunk-valor rankea {vrank} en vector (fuera del top-50)"
    else:
        canal = "VECTOR/LÉXICO"; motivo = "ni vector(top200) ni léxico surfacean el chunk-valor (vocab/chunking)"
    return {"qid": miss["qid"], "valor": miss["valor"], "canal": canal, "motivo": motivo,
            "family_in_pool": family_in_pool, "manual_in_pool": manual_in_pool,
            "vector_rank": vrank, "val_lang": val_lang, "es_en": es_en}


def main(run_path: str):
    fam = rederive(run_path)
    d = yaml.safe_load(open(run_path, encoding="utf-8"))
    res_by_qid = {r["qid"]: r for r in d["reps"][0]["results"]}
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(os.path.join(os.getcwd(), "evals", "gold_answers_v1.yaml"), encoding="utf-8"))}
    out = []
    for miss in fam["misses"]:
        res = res_by_qid[miss["qid"]]
        man = {c["id"]: c for c in res.get("manual_pin", [])}
        # chunk-valor = votos del fact en el manual (recupera el fact por valor)
        fact = next((f for f in res["facts"] if f["valor"] == miss["valor"]), {})
        sup = [i for i, v in (fact.get("votes") or {}).items() if v >= THRESH_FIRM]
        val_chunks = [{"id": i, "source_file": man[i].get("src"), "pm": man[i].get("pm"),
                       "content": ""} for i in sup if i in man]
        out.append(diagnose_miss(golds[miss["qid"]], miss, res.get("pool_pin", []), val_chunks))
    from collections import Counter
    print("retrieval-miss FAMILY-AWARE =", fam["retrieval_miss_family"])
    print("\n=== (CANAL × MOTIVO) por miss ===")
    for o in out:
        print(f"  {o['qid']:8} {o['valor'][:24]!r:26} [{o['canal']}] {o['motivo']}")
    print("\n=== distribución por CANAL ===", dict(Counter(o["canal"] for o in out)))
    json.dump({"misses": out, "retrieval_miss_family": fam["retrieval_miss_family"]},
              open(os.path.join(os.getcwd(), "evals", "s85_b1_diagnosis.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "evals/s85_retrieval_miss_DEF.yaml")
