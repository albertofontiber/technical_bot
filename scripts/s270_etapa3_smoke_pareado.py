#!/usr/bin/env python3
"""S270 Etapa 3 — smoke de regresión JUDGE-FREE del contrato must-preserve (ruta viva).

Genera los 5 golds smoke (SMOKE_QIDS del assessment) pareados OFF/ON por la ruta
harness REAL (retrieval vivo, flags demo) y verifica:
  1. MONOTONÍA por construcción: la respuesta ON = respuesta OFF + (opcional) apéndice
     "Información adicional del manual" — el texto base NO muta (assert de prefijo).
  2. Los apéndices se persisten para lectura humana (DEC-092b).
  3. Coste y latencia por brazo.

Mismo patrón pareado que los probes: UNA generación (OFF) por gold; ON = aplicar el
contrato determinista sobre el MISMO borrador con los MISMOS chunks servidos.
Salida: evals/s270_etapa3_smoke_result_v1.json + apéndices en jsonl.
Uso: python scripts/s270_etapa3_smoke_pareado.py --execute  (sin flag: preflight $0)
"""
from __future__ import annotations
import json, os, sys, time

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ.setdefault("ENUNCIADOS_MULTIVECTOR", "on")
os.environ.setdefault("IDENTITY_RESOLVE", "on")
os.environ.setdefault("IDENTITY_RESOLVE_POLICY", "add")
os.environ.setdefault("RERANK_TOP_K", "10")
os.environ.setdefault("LLM_MAX_TOKENS", "3500")
os.environ.setdefault("GENERATOR_PROMPT_VARIANT", "fidelity")
os.environ.setdefault("HYQ_TABLE", "on")
os.environ.setdefault("GENERATOR_SELECTION_BLOCK", "on")
os.environ.setdefault("MUST_PRESERVE_CONTRACT", "off")  # el ON se aplica en post, pareado

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

SMOKE_QIDS = ["hp007", "cat007", "hp018", "hp001", "cat005"]
OUT = os.path.join("evals", "s270_etapa3_smoke_result_v1.json")
APPX = os.path.join("evals", "s270_etapa3_smoke_appendices_v1.jsonl")


def main() -> int:
    execute = "--execute" in sys.argv
    import yaml
    golds = yaml.safe_load(open(os.path.join("evals", "gold_answers_v1.yaml"), encoding="utf-8"))
    by_id = {g["qid"]: g for g in golds}
    questions = {q: by_id[q]["question"] for q in SMOKE_QIDS}
    if not execute:
        print(json.dumps({"preflight": True, "qids": SMOKE_QIDS,
                          "est_usd": round(0.11 * len(SMOKE_QIDS), 3)}, indent=1))
        return 0

    from src.rag.retriever import retrieve_chunks
    from src.rag.generator import generate_answer
    from src.rag import must_preserve as mp

    rows, results = [], []
    total = 0.0
    for qid in SMOKE_QIDS:
        q = questions[qid]
        t0 = time.time()
        chunks = retrieve_chunks(q)
        r = generate_answer(q, chunks)
        off_answer = r["answer"]
        cost = ((r.get("input_tokens") or 0) * 3 + (r.get("output_tokens") or 0) * 15) / 1e6
        total += cost
        # FIX C1 (ship-review Sol 16:05): la 1ª versión aplicaba con el flag OFF →
        # passthrough byte-idéntico (OFF-vs-OFF, trace None). El brazo ON exige el
        # flag EFECTIVO alrededor del apply (la generación base sigue con off).
        os.environ["MUST_PRESERVE_CONTRACT"] = "on"
        try:
            on_answer, trace = mp.apply_must_preserve_contract(q, chunks, off_answer)
        finally:
            os.environ["MUST_PRESERVE_CONTRACT"] = "off"
        if mp.cited_fragment_numbers(off_answer) and trace is None:
            raise RuntimeError(f"{qid}: trace None con fragmentos citados — brazo ON inerte")
        monotonic = on_answer.startswith(off_answer)
        appendix = on_answer[len(off_answer):] if monotonic else "(VIOLACIÓN DE MONOTONÍA)"
        rows.append({"qid": qid, "monotonic": monotonic,
                     "appendix_len": len(appendix.strip()), "trace": trace,
                     "latency_s": round(time.time() - t0, 1), "cost_usd": round(cost, 5)})
        with open(APPX, "a", encoding="utf-8") as f:
            f.write(json.dumps({"qid": qid, "appendix": appendix.strip(),
                                "off_answer": off_answer}, ensure_ascii=False) + "\n")
        print(f"{qid}: monotonic={monotonic} appendix={len(appendix.strip())}ch "
              f"atoms={trace.get('atoms_appended') if trace else 0} {rows[-1]['latency_s']}s")

    verdict = {"schema": "s270_etapa3_smoke_v1",
               "monotonicity_violations": [r["qid"] for r in rows if not r["monotonic"]],
               "appendix_fired": [r["qid"] for r in rows if r["appendix_len"] > 0],
               "rows": rows, "total_cost_usd": round(total, 4),
               "requires_human_read": any(r["appendix_len"] > 0 for r in rows)}
    json.dump(verdict, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: verdict[k] for k in
                      ("monotonicity_violations", "appendix_fired", "total_cost_usd")}, indent=1))
    return 0 if not verdict["monotonicity_violations"] else 2


if __name__ == "__main__":
    sys.exit(main())
