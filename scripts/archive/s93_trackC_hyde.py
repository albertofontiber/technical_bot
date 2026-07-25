#!/usr/bin/env python3
"""s93_trackC_hyde.py — TRACK C (extracción-tablas, micro-slice pre-registrado) +
mini-brazo HyDE (addendum pre-registrado) del bake-off s93 (plan v3.2).

TRACK C (4 hechos fijos, pre-registro en el plan): extracción LLM (claude-sonnet-4-6)
del chunk-soporte a ENUNCIADOS autónomos fila-por-fila (producto + sección + valor
literal); embed receta-fiel (context-almacenado + enunciado); evento = cos >= sim#50
del canal vectorial REAL (RPC, mismo espacio del run) ± tie 0.003.

HyDE (10 hechos): hipótesis en registro-manual -> embed_query(hipótesis) -> en ESE
espacio: frontera del canal (RPC) + cos(padre) + cos(span-B). Evento: padre-o-span
>= sim#50 de su espacio. 1 muestra por gold (probe; jitter declarado).

Coste declarado: ~6 llamadas Sonnet (extracción) + 9 Haiku/Sonnet (HyDE) + ~40 embeds
Voyage = ~$1-2. Read-only en DB.
"""
import json
import os
import sys

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
# ANTES del import de hyde (constante de módulo): sin esto, generate_hypothetical_document
# devuelve la query TAL CUAL (hyde.py:84, fallback silencioso) y el brazo mide un NO-OP —
# cazado por regla-C en la 1ª pasada (cosenos == espacio query-cruda dentro del drift).
os.environ["HYDE_ENABLED"] = "true"
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
import anthropic

from s93_trackB_probe import EXCLUDED, TIE, fetch_chunks, rpc_frontier, span_for
from src.config import LLM_MODEL
from src.ingestion.embedder import embed_query
from src.rag.hyde import generate_hypothetical_document
from src.rag.retriever import _cos, _fetch_embeddings_by_id
from src.reingest.embed import embed

C_SET = {("hp018", "1 A"), ("hp012", "2 lazos / 396"), ("hp014", "35"),
         ("hp011", "05 a 295 seg")}

EXTRACT_PROMPT = """Convierte el siguiente fragmento de un manual técnico PCI en ENUNCIADOS autónomos, uno por línea.
Reglas: cada enunciado expresa UN dato/celda como frase completa en español técnico; incluye SIEMPRE el modelo/producto y el contexto de la sección; conserva los valores LITERALES (números, unidades, códigos, referencias); nada que no esté en el fragmento; sin comentarios ni numeración."""


def extract_statements(client, ctx: str, content: str) -> list[str]:
    msg = client.messages.create(
        model=LLM_MODEL, max_tokens=1500,
        system=EXTRACT_PROMPT,
        messages=[{"role": "user", "content": f"{ctx}\n\n{content}"[:12000]}])
    return [ln.strip() for ln in msg.content[0].text.splitlines() if ln.strip()]


def main() -> int:
    tb = json.load(open("evals/s93_gate0_testbed.json", encoding="utf-8"))
    rows = [r for r in tb["rows"] if (r["qid"], r["valor"]) not in EXCLUDED]
    all_sup = sorted({s["id"] for r in rows for s in r["sup_family_ids"]})
    sup_data = fetch_chunks(all_sup)
    client = anthropic.Anthropic()
    out = {"trackC": [], "hyde": []}

    # ---------- TRACK C ----------
    solo_hyde = "--solo-hyde" in sys.argv
    if solo_hyde:                    # re-run del brazo HyDE sin re-pagar la extracción C
        prev = json.load(open("evals/s93_trackC_hyde_results.json", encoding="utf-8"))
        out["trackC"] = prev["trackC"]
    print("== TRACK C (extracción-tablas) ==" + (" [saltado --solo-hyde]" if solo_hyde else ""))
    for r in rows:
        if solo_hyde or (r["qid"], r["valor"]) not in C_SET:
            continue
        q_emb = embed_query(r["question"])
        s50 = rpc_frontier(q_emb)["sim50"]
        best = None
        for s in r["sup_family_ids"]:
            ch = sup_data.get(s["id"])
            if not ch:
                continue
            stmts = extract_statements(client, ch.get("context") or "", ch.get("content") or "")
            if not stmts:
                continue
            texts = [(f"{ch['context']}\n\n{st}" if ch.get("context") else st) for st in stmts]
            embs = embed(texts, "document")
            for st, e in zip(stmts, embs):
                c = _cos(q_emb, e)
                if best is None or c > best["cos"]:
                    best = {"sup": s["id"][:8], "cos": round(c, 4), "stmt": st[:180],
                            "n_stmts": len(stmts)}
        v = ("WIN-canal50" if best and best["cos"] >= s50 + TIE else
             "TIE-canal50" if best and best["cos"] >= s50 - TIE else "NO")
        out["trackC"].append({"qid": r["qid"], "valor": r["valor"], "verdict": v,
                              "canal_sim50": round(s50, 4), "best": best})
        print(f"{r['qid']:8} {r['valor'][:20]!r:22} {v:12} best={best and best['cos']} "
              f"canal50={round(s50,4)} stmt={best and best['stmt'][:70]!r}")

    # ---------- HyDE ----------
    print("\n== mini-brazo HyDE ==")
    hyp_cache = {}
    for r in rows:
        qid = r["qid"]
        if qid not in hyp_cache:
            hyp = generate_hypothetical_document(r["question"])
            h_emb = embed_query(hyp)
            hyp_cache[qid] = (hyp, h_emb, rpc_frontier(h_emb))
        hyp, h_emb, front = hyp_cache[qid]
        s50 = front["sim50"]
        best_p, best_s = None, None
        for s in r["sup_family_ids"]:
            pe = _fetch_embeddings_by_id([s["id"]]).get(s["id"])
            if pe:
                c = _cos(h_emb, pe)
                best_p = max(best_p or -1, c)
            ch = sup_data.get(s["id"])
            span = span_for(r["valor"], (ch or {}).get("content") or "") if ch else None
            if span:
                text = f"{ch['context']}\n\n{span}" if ch.get("context") else span
                c = _cos(h_emb, embed([text], "document")[0])
                best_s = max(best_s or -1, c)
        top = max(x for x in (best_p, best_s) if x is not None) if (best_p or best_s) else None
        v = ("WIN-canal50" if top and top >= s50 + TIE else
             "TIE-canal50" if top and top >= s50 - TIE else "NO")
        out["hyde"].append({"qid": qid, "valor": r["valor"], "verdict": v,
                            "cos_padre_hyde": best_p and round(best_p, 4),
                            "cos_span_hyde": best_s and round(best_s, 4),
                            "canal_sim50_hyde": round(s50, 4)})
        print(f"{qid:8} {r['valor'][:20]!r:22} {v:12} padre={best_p and round(best_p,4)} "
              f"span={best_s and round(best_s,4)} canal50={round(s50,4)}")

    json.dump(out, open("evals/s93_trackC_hyde_results.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n→ evals/s93_trackC_hyde_results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
