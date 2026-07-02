#!/usr/bin/env python3
"""s93_trace_misses.py — PASO 0 del bake-off (plan v3.2, sub-agente F4): localizar DÓNDE
muere cada chunk-soporte de las miss-facts ANTES de atribuir el miss a fine-grained.

Usa el instrumento `_trace` de retrieve_chunks (s85, retriever.py:1221-25) con la config
del pin (IDENTITY_RESOLVE=on + POLICY=add, chunks_v2, top_k=50):
- soporte NUNCA aparece en 'channels' → no entra por ningún canal → clase FINE-GRAINED
  confirmada → queda en el testbed B/C;
- soporte aparece en 'channels' y desaparece en una etapa posterior → muere post-canal
  (filtro/diversify/truncado) → NO es fine-grained (fix = otro lever) → SALE de B/C.

Declarado: esto RE-RECUPERA (jitter ±1-2 documentado) — localiza el mecanismo, no mide
el evento del bake-off. Read-only sobre DB.
"""
import json
import os
import sys

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["IDENTITY_RESOLVE"] = "on"
os.environ["IDENTITY_RESOLVE_POLICY"] = "add"
sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

from src.rag.retriever import retrieve_chunks  # noqa: E402

STAGES = ["channels", "post_merge", "post_neighbor", "post_superseded",
          "post_model_filter", "post_diversify", "post_lang", "final"]


def main() -> int:
    tb = json.load(open("evals/s93_gate0_testbed.json", encoding="utf-8"))
    by_q: dict[str, dict] = {}
    for r in tb["rows"]:
        e = by_q.setdefault(r["qid"], {"question": r["question"], "facts": []})
        e["facts"].append({"valor": r["valor"], "sup": [s["id"] for s in r["sup_family_ids"]]})
    out = {}
    for qid, e in sorted(by_q.items()):
        tr: dict = {}
        try:
            retrieve_chunks(e["question"], top_k=50, _trace=tr)
        except Exception as exc:
            out[qid] = {"error": str(exc)}
            print(f"{qid}: ERROR {exc}")
            continue
        sets = {s: tr.get(s, set()) for s in STAGES}
        rows = []
        for f in e["facts"]:
            for sid in f["sup"]:
                present = [s for s in STAGES if sid in sets[s]]
                if not present:
                    clase = "NUNCA-EN-CANAL (fine-grained)"
                elif "final" in present:
                    clase = "EN-FINAL (¡ya no miss hoy — jitter!)"
                else:
                    clase = f"MUERE tras {present[-1]}"
                rows.append({"valor": f["valor"], "sup": sid[:8], "clase": clase,
                             "etapas": present})
                print(f"{qid:8} {f['valor'][:22]!r:24} {sid[:8]} → {clase}")
        out[qid] = {"n_pool_final": len(sets["final"]), "sups": rows}
    json.dump(out, open("evals/s93_paso0_trace.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n→ evals/s93_paso0_trace.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
