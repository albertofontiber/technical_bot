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

# Lever ESTRUCTURAL por etapa-de-fallo (mapa completo, sin fallback silencioso).
LEVER = {
    "RECALL":       "recall: embedding/HyDE/expansión + keyword/sinónimos (refinar con el motivo)",
    "MERGE":        "merge/dedup: estrategia de fusión de canales (MERGE_STRATEGY)",
    "SUPERSEDED":   "transversal: revisar marcado de superseded (¿deprecado de verdad? DEC-058)",
    "MODEL-FILTER": "identidad: _filter_to_query_models / resolución de familia (el manual correcto filtrado)",
    "DIVERSIFY":    "diversify: cuota por source_file/fabricante deja fuera el chunk-valor",
    "LANGUAGE":     "idioma: el filtro ES/EN quita el chunk-valor (es-en)",
    "DEPTH":        "profundidad/ranking: sobrevive filtros pero cae del top-k (competición within-doc)",
}
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


def diagnose_miss(gold, miss, pin, val_chunks):
    """val_chunks = chunks del manual same-family que el juez acreditó (el dato vive ahí)."""
    q = gold["question"]
    val_ids = {c["id"] for c in val_chunks}
    # TRACE del pipeline REAL para esos ids
    trace = {}
    try:
        retrieve_chunks(q, top_k=50, _trace=trace)
    except Exception:
        pass
    present = {s: bool(val_ids & trace.get(s, set())) for s in STAGE_SEQ}
    # ETAPA-DE-FALLO = primera etapa donde se pierde (MECE)
    if not present.get("channels"):
        etapa = "RECALL"
    else:
        etapa = "DEPTH"   # si nunca se pierde antes de 'final', cayó por rank en el top-k
        for i in range(1, len(STAGE_SEQ)):
            if present[STAGE_SEQ[i - 1]] and not present[STAGE_SEQ[i]]:
                etapa = DROP_LABEL[STAGE_SEQ[i]]; break

    # MOTIVOS (predicados INDEPENDIENTES, se emite el conjunto)
    val_lang = _lang(" ".join((c.get("content") or "")[:800] for c in val_chunks))
    q_lang = _lang(q + " " + miss.get("valor", ""))
    motivos = []
    if val_lang == "EN" and q_lang in ("ES", "MIX"):
        motivos.append("es-en")
    if len(re.sub(r"\s", "", miss.get("valor", ""))) <= 4:
        motivos.append("token-corto")
    pool_srcs = {c.get("src") for c in pin}
    if {c.get("source_file") for c in val_chunks} & pool_srcs:
        motivos.append("within-doc")   # el manual tiene OTROS chunks en pool, el valor no
    return {"qid": miss["qid"], "valor": miss["valor"], "etapa": etapa, "motivos": motivos,
            "lever": LEVER[etapa], "gold_family": miss.get("gold_family"),
            "trace_present": {s: present[s] for s in STAGE_SEQ}, "val_lang": val_lang}


def main(run_path):
    fam = rederive(run_path)
    d = yaml.safe_load(open(run_path, encoding="utf-8"))
    res_by_qid = {r["qid"]: r for r in d["reps"][0]["results"]}
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(os.path.join(os.getcwd(), "evals", "gold_answers_v1.yaml"), encoding="utf-8"))}
    import httpx
    from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
    H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

    def fetch_content(ids):
        out = {}
        for i in range(0, len(ids), 40):
            q = ",".join(f'"{x}"' for x in ids[i:i + 40])
            try:
                r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H,
                              params={"select": "id,content", "id": f"in.({q})"}, timeout=20)
                for x in r.json():
                    out[x["id"]] = x.get("content")
            except Exception:
                pass
        return out

    out = []
    for miss in fam["misses"]:
        res = res_by_qid[miss["qid"]]
        man = {c["id"]: c for c in res.get("manual_pin", [])}
        fact = next((f for f in res["facts"] if f["valor"] == miss["valor"]), {})
        sup = [i for i, v in (fact.get("votes") or {}).items() if v >= THRESH_FIRM and i in man]
        cont = fetch_content(sup)
        val_chunks = [{"id": i, "source_file": man[i].get("src"), "content": cont.get(i, "")} for i in sup]
        out.append(diagnose_miss(golds[miss["qid"]], miss, res.get("pool_pin", []), val_chunks))
    print("retrieval-miss FAMILY-AWARE =", fam["retrieval_miss_family"],
          "| UNRESOLVED:", fam.get("unresolved"), "| meta excl:", fam.get("n_meta_excluded"))
    print("\n=== (ETAPA-FALLO × MOTIVOS) por miss ===")
    for o in out:
        print(f"  {o['qid']:8} {o['valor'][:20]!r:22} [{o['etapa']:12}] motivos={o['motivos']} → {o['lever'][:48]}")
    print("\n=== distribución ETAPA-DE-FALLO (MECE) ===", dict(Counter(o["etapa"] for o in out)))
    json.dump({"misses": out, "retrieval_miss_family": fam["retrieval_miss_family"],
               "unresolved": fam.get("unresolved")},
              open(os.path.join(os.getcwd(), "evals", "s85_b1_diagnosis.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "evals/s85_retrieval_miss_DEF.yaml")
