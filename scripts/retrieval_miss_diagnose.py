#!/usr/bin/env python3
"""retrieval_miss_diagnose.py (s85·B1) — diagnóstico de cada retrieval-miss por ETAPA-DE-FALLO
(MECE, del pipeline REAL) × MOTIVO (predicados ortogonales).

Reescrito tras el dúo (sub-agente Opus): la versión anterior inferia el punto-de-fallo desde
universos PARALELOS (vector_search(q,200) SIN filtros + keyword), que NO replican el pipeline →
no distinguía "el model-filter lo expulsó" de "rankea >50" (colapsaban). FIX: instrumentar
`retrieve_chunks(_trace=...)` para que emita la membresía del chunk-valor en CADA etapa real, y
clasificar por la PRIMERA etapa donde se pierde. MECE por construcción del pipeline.

ETAPA-DE-FALLO (MECE — el chunk-valor se pierde en exactamente una):
  RECALL        : ningún canal (vector/keyword/content) lo trajo como candidato.
  MERGE         : estaba en un canal pero el merge/dedup lo perdió.
  SUPERSEDED    : el filtro de lifecycle lo quitó (doc deprecado).
  MODEL-FILTER  : `_filter_to_query_models` lo expulsó (identidad — el manual correcto filtrado). [hp018]
  DIVERSIFY     : el paso de diversidad lo dejó fuera.
  LANGUAGE      : el filtro de idioma lo quitó.
  DEPTH         : sobrevivió todos los filtros pero rankeó >top_k (competición/ranking).

MOTIVO (predicados independientes, se emite el conjunto): es-en · token-corto · within-doc.
El chunk-valor = chunks del MANUAL que el juez acreditó (votos≥THRESH ∩ manual same-family).

Uso: python scripts/retrieval_miss_diagnose.py evals/s85_retrieval_miss_DEF.yaml
(corre DESPUÉS de la pasada definitiva + famtie. Re-dúo (sub-agente + cross-model) antes de B2.)
"""
import os, sys, re, json
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2"); os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"; os.environ["HYDE_ENABLED"] = "false"
import yaml
from collections import Counter
from src.rag.retriever import retrieve_chunks
from scripts.retrieval_miss_famtie import rederive, THRESH_FIRM

# Lever ESTRUCTURAL. RECALL se DISCRIMINA por within-doc (dúo B1: 8/10 RECALL son intra-doc, y
# HyDE/embedding-global NO los toca — colapsarlos mis-dirige B2).
LEVER = {
    "RECALL-INTRADOC": "recall INTRA-doc/chunking: el manual correcto YA está en el pool pero no el "
                       "chunk-valor concreto → cobertura/chunking/within-doc (NO HyDE-global)",
    "RECALL-GLOBAL":   "recall global: findability del chunk-valor (embedding/HyDE/keyword/sinónimos)",
    "MERGE":        "merge/dedup: estrategia de fusión de canales (MERGE_STRATEGY)",
    "SUPERSEDED":   "transversal: revisar marcado de superseded (¿deprecado de verdad? DEC-058)",
    "MODEL-FILTER": "identidad: _filter_to_query_models / resolución de familia (el manual correcto filtrado)",
    "DIVERSIFY":    "diversify: cuota por source_file/fabricante deja fuera el chunk-valor",
    "LANGUAGE":     "idioma: el filtro ES/EN quita el chunk-valor (es-en)",
    "DEPTH":        "profundidad/ranking: sobrevive filtros pero cae del top-k (competición within-doc)",
    "NO_VAL_CHUNKS": "INVÁLIDO: sin val_chunks same-family (familia mal resuelta/PM ausente) — revisar, NO es RECALL",
    "RETRIEVE_ERROR": "INVÁLIDO: retrieve_chunks falló las K corridas — error instrumental, NO es RECALL",
}


def lever_for(etapa, motivos):
    if etapa == "RECALL":
        return LEVER["RECALL-INTRADOC" if "within-doc" in motivos else "RECALL-GLOBAL"]
    return LEVER.get(etapa, "revisar")
STAGE_SEQ = ["channels", "post_merge", "post_superseded", "post_model_filter",
             "post_diversify", "post_lang", "final"]
DROP_LABEL = {"post_merge": "MERGE", "post_superseded": "SUPERSEDED",
              "post_model_filter": "MODEL-FILTER", "post_diversify": "DIVERSIFY",
              "post_lang": "LANGUAGE", "final": "DEPTH"}

EN_HINT = re.compile(r"\b(the|and|with|fault|earth|ground|alarm|output|input|circuit|loop|reset|"
                     r"zone|level|default|value|range|terminal|relay|short|open|latch)\b", re.I)
ES_HINT = re.compile(r"\b(el|la|los|de|con|fallo|tierra|alarma|salida|entrada|circuito|lazo|"
                     r"nivel|valor|rango|terminal|relé|rearme|avería|zona|enclav)\b", re.I)


def _lang(text):
    en = len(EN_HINT.findall(text or "")); es = len(ES_HINT.findall(text or ""))
    if en == 0 and es == 0:
        return "?"
    return "EN" if en > es * 1.3 else ("ES" if es > en * 1.3 else "MIX")


def _stage_of(present):
    """ETAPA-DE-FALLO = primera etapa donde se pierde el chunk-valor (MECE).

    (s103b) `final` se comprueba PRIMERO: el pipeline ya NO es monotónico — el aside hyq
    (carve-out v3.1) y el identity-fetch re-adjuntan chunks DESPUÉS de post_lang, así que
    "ausente en una etapa intermedia" ya no implica "perdido". Para trazas monotónicas el
    resultado es IDÉNTICO al scan histórico (si estaba en final sin pérdida intermedia, el
    scan devolvía IN-POOL igualmente) — comparabilidad con artefactos previos preservada."""
    if present.get("final"):
        return "IN-POOL"   # llegó al pool final — no se perdió (aunque saliera-y-volviera)
    if not present.get("channels"):
        return "RECALL"
    for i in range(1, len(STAGE_SEQ)):
        if present[STAGE_SEQ[i - 1]] and not present[STAGE_SEQ[i]]:
            return DROP_LABEL[STAGE_SEQ[i]]
    return "IN-POOL"


def diagnose_miss(gold, miss, pin, val_chunks, k=3):
    """val_chunks = chunks del manual same-family que el juez acreditó (el dato vive ahí).
    K traces (el retrieval de identidad es NO-DETERMINISTA, p.ej. hp018 model-filter) → moda + jitter."""
    q = gold["question"]
    val_ids = {c["id"] for c in val_chunks}
    # GUARD (dúo cross-model): val_chunks vacío (familia mal resuelta) NO es RECALL — es inválido.
    if not val_ids:
        return {"qid": miss["qid"], "valor": miss["valor"], "etapa": "NO_VAL_CHUNKS",
                "motivos": [], "jitter": False, "dist": {}, "lever": LEVER["NO_VAL_CHUNKS"],
                "gold_family": miss.get("gold_family"), "trace_present": {}}
    etapas_k = []
    present_by_etapa = {}   # trace_present de la corrida MODAL (no la última — dúo)
    n_err = 0
    # el retrieval es DETERMINISTA por diseño (HyDE off + orden de submit fijo, verificado 4× idénticas
    # por el dúo) → K NO prueba estabilidad; se mantiene bajo para robustez ante fallos transitorios.
    for _ in range(k):
        trace = {}
        try:
            retrieve_chunks(q, top_k=50, _trace=trace)
        except Exception:
            n_err += 1; continue
        present = {s: bool(val_ids & trace.get(s, set())) for s in STAGE_SEQ}
        # MECE CONDICIONAL (dúo): el diversify hace fetch-fresco → un chunk puede re-entrar en
        # post_diversify sin estar en channels. Se anota si pasa (hoy no se materializa).
        e = _stage_of(present)
        etapas_k.append(e); present_by_etapa.setdefault(e, present)
    # GUARD: si las K corridas fallaron → error instrumental, NO RECALL.
    if not etapas_k:
        return {"qid": miss["qid"], "valor": miss["valor"], "etapa": "RETRIEVE_ERROR",
                "motivos": [], "jitter": False, "dist": {}, "lever": LEVER["RETRIEVE_ERROR"],
                "gold_family": miss.get("gold_family"), "trace_present": {}}
    dist = Counter(etapas_k)
    etapa = dist.most_common(1)[0][0]
    jitter = len(dist) > 1
    present = present_by_etapa[etapa]   # trace de la corrida MODAL
    diversify_reentry = present.get("post_diversify") and not present.get("channels")

    # MOTIVOS (predicados independientes — HEURÍSTICAS, no predicados certeros; dúo).
    # es-en: usar la columna `language` de la DB (fiable) — NO la heurística de keywords (daba FP).
    val_langs = {(c.get("language") or "").lower() for c in val_chunks}
    q_es = bool(ES_HINT.search(q))
    motivos = []
    if val_langs == {"en"} and q_es:
        motivos.append("es-en")
    if len(re.sub(r"\s", "", miss.get("valor", ""))) <= 4:
        motivos.append("token-corto")
    pool_srcs = {c.get("src") for c in pin}
    if {c.get("source_file") for c in val_chunks} & pool_srcs:
        motivos.append("within-doc")   # el manual tiene OTROS chunks en pool, el chunk-valor no
    return {"qid": miss["qid"], "valor": miss["valor"], "etapa": etapa, "motivos": motivos,
            "jitter": jitter, "dist": dict(dist), "lever": lever_for(etapa, motivos),
            "gold_family": miss.get("gold_family"), "n_err": n_err,
            "diversify_reentry": bool(diversify_reentry),
            "trace_present": {s: present.get(s) for s in STAGE_SEQ},
            "val_langs": sorted(val_langs)}


def main(run_path):
    fam = rederive(run_path)
    d = yaml.safe_load(open(run_path, encoding="utf-8"))
    res_by_qid = {r["qid"]: r for r in d["reps"][0]["results"]}
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(os.path.join(os.getcwd(), "evals", "gold_answers_v1.yaml"), encoding="utf-8"))}
    import httpx
    from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
    H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

    def fetch_meta(ids):   # content + language (columna fiable de la DB, para es-en)
        out = {}
        for i in range(0, len(ids), 40):
            q = ",".join(f'"{x}"' for x in ids[i:i + 40])
            try:
                r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H,
                              params={"select": "id,content,language", "id": f"in.({q})"}, timeout=20)
                for x in r.json():
                    out[x["id"]] = x
            except Exception:
                pass
        return out

    from scripts.retrieval_miss_famtie import fam_norm, _pm_by_ids
    out = []
    for miss in fam["misses"]:
        res = res_by_qid[miss["qid"]]
        man = {c["id"]: c for c in res.get("manual_pin", [])}
        fact = next((f for f in res["facts"] if f["valor"] == miss["valor"]), {})
        sup_all = [i for i, v in (fact.get("votes") or {}).items() if v >= THRESH_FIRM and i in man]
        # CLAVE: trazar SOLO los val_chunks de la MISMA FAMILIA (el miss family-aware es porque el
        # chunk SAME-FAMILY no está en pool; los wrong-family que SÍ están no son el dato correcto).
        # manual_pin trae pm=None → fetch por-ID.
        gfam = set(miss.get("gold_family") or [])
        pm = _pm_by_ids(sup_all)
        sup = [i for i in sup_all if (not gfam) or (fam_norm(pm.get(i)) in gfam)]
        meta = fetch_meta(sup)
        val_chunks = [{"id": i, "source_file": man[i].get("src"),
                       "content": (meta.get(i) or {}).get("content", ""),
                       "language": (meta.get(i) or {}).get("language")} for i in sup]
        out.append(diagnose_miss(golds[miss["qid"]], miss, res.get("pool_pin", []), val_chunks))
    print("retrieval-miss FAMILY-AWARE =", fam["retrieval_miss_family"],
          "| UNRESOLVED:", fam.get("unresolved"), "| meta excl:", fam.get("n_meta_excluded"))
    print("\n=== (ETAPA-FALLO × MOTIVOS) por miss ===")
    for o in out:
        j = f" JITTER{o['dist']}" if o.get("jitter") else ""
        print(f"  {o['qid']:8} {o['valor'][:20]!r:22} [{o['etapa']:10}]{j} motivos={o['motivos']} -> {o['lever'][:44]}")
    print("\n=== distribución ETAPA-DE-FALLO ===", dict(Counter(o["etapa"] for o in out)))
    # cluster de LEVER (RECALL discriminado por within-doc — lo que dirige B2)
    def cluster(o):
        if o["etapa"] == "RECALL":
            return "RECALL-INTRADOC" if "within-doc" in o["motivos"] else "RECALL-GLOBAL"
        return o["etapa"]
    print("=== cluster LEVER para B2 ===", dict(Counter(cluster(o) for o in out)))
    print("=== jittery ===", [o["qid"] for o in out if o.get("jitter")],
          "| retrieve-errors:", [o["qid"] for o in out if o.get("n_err")])
    print("=== NOTA: en paralelo hay RERANK-MISS =", fam["agg"].get("RERANK-MISS", 0),
          "(findability tiene 2 cubos; B2 = retrieval-miss) ===")
    json.dump({"misses": out, "retrieval_miss_family": fam["retrieval_miss_family"],
               "unresolved": fam.get("unresolved")},
              open(os.path.join(os.getcwd(), "evals", "s85_b1_diagnosis.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "evals/s85_retrieval_miss_DEF.yaml")
