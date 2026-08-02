#!/usr/bin/env python3
"""s293_reachability_probe.py — ¿es ALCANZABLE el hecho-diana con evidencia perfecta?

Generaliza lo que en s293 mató el lever A en veinte minutos: antes de diseñar un lever
de serving/síntesis, medir si el hecho transmitiría **con la evidencia ideal ya delante
del modelo**. Si no transmite ni así, ningún lever de serving puede pagarlo y el diseño
sobra (DEC-172, lección #58).

Dos oráculos, según por qué falla el hecho:

  `serve`     el carrier del dato NO se sirve → se INYECTA en la vista del generador
              (fila real de DB, `similarity` elevada al máximo de las servidas: el oráculo
              pregunta «¿y si el modelo lo hubiera visto?», no «¿por qué lane entraría?»).
              Brazos: base (sin inyección) y oracle (con), generaciones independientes.

  `appendix`  el carrier YA se sirve y el modelo lo omite → se simula el apéndice
              determinista añadiendo el span VERBATIM con su cita al final de la respuesta
              (formato de `must_preserve.render_appendix`). Brazos PAREADOS: la MISMA
              generación se juzga con y sin apéndice.

Vara: el juez canónico `judge_conveyed21` (K=5, `THRESH_FIRM=4`) — la métrica del objetivo,
no un regex propio (lección #58(c)).

Uso:
  python scripts/s293_reachability_probe.py <qid> <fact_prefix> serve    --inject <id8>[,<id8>] [reps]
  python scripts/s293_reachability_probe.py <qid> <fact_prefix> appendix --span-grep <regex>   [reps]
Salida: evals/s293_reachability_<qid>_<fact>.json
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

import httpx  # noqa: E402
import yaml  # noqa: E402

# Importar el instrumento fija DEMO_FLAGS en import-time (freeze-contract) antes del pipeline.
import scripts.factlevel_assessment as FA  # noqa: E402
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.rag.retriever import _HYDRATE_SELECT  # noqa: E402
from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn  # noqa: E402
from src.rag.structural_neighbor_shadow import observe_structural_neighbor_shadow  # noqa: E402
from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K  # noqa: E402
from src.rag.generator import admitted_evidence_rows  # noqa: E402
from src.rag.must_preserve import APPENDIX_HEADER  # noqa: E402

RECEIPT = "evals/s100_factlevel_full_v32_full_20260801.yaml"


def _args() -> dict:
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    out = {
        "qid": sys.argv[1],
        "fact": sys.argv[2],
        "mode": sys.argv[3],
        "inject": [],
        "span_grep": None,
        "reps": 3,
    }
    rest = sys.argv[4:]
    while rest:
        token = rest.pop(0)
        if token == "--inject":
            out["inject"] = rest.pop(0).split(",")
        elif token == "--span-grep":
            out["span_grep"] = rest.pop(0)
        else:
            out["reps"] = int(token)
    if out["mode"] not in {"serve", "appendix"}:
        raise SystemExit("modo: serve | appendix")
    return out


def fetch_by_prefix(prefixes: list[str], pool_ids: list[str]) -> list[dict]:
    # El oráculo también sirve para carriers que NUNCA llegaron al pool (el caso de
    # hp011#2): un uuid completo se acepta tal cual; un prefijo se resuelve contra el
    # pool del recibo.
    full = [p for p in prefixes if len(p) == 36]
    short = [p for p in prefixes if len(p) != 36]
    full += [cid for cid in pool_ids if any(cid.startswith(p) for p in short)]
    missing = [p for p in short if not any(cid.startswith(p) for cid in full)]
    if missing:
        raise SystemExit(
            f"ids no resolubles desde el pool del recibo: {missing} "
            "(pásalos completos: el pool solo cubre lo recuperado)"
        )
    with httpx.Client(timeout=90.0) as client:
        batch = ",".join(f'"{cid}"' for cid in full)
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{os.environ['CHUNKS_TABLE']}",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            },
            params={"select": _HYDRATE_SELECT, "id": f"in.({batch})"},
        )
        resp.raise_for_status()
        return resp.json()


def run_turn(question: str, inject_rows: list[dict]) -> dict:
    """Turno completo por el seam (espejo de FA.run_pipeline) con inyección opcional
    en la VISTA del generador."""
    captured: dict = {}

    def generate(query, chunks, available_models=None):
        rows = [dict(c) for c in chunks]
        if inject_rows:
            ceiling = max(
                [float(c.get("similarity") or 0.0) for c in rows] + [0.9]
            )
            for row in inject_rows:
                extra = dict(row)
                extra["similarity"] = ceiling
                rows.append(extra)
        captured["served"] = admitted_evidence_rows(rows)
        return FA.generate_answer(query, rows, available_models=available_models)

    pipeline = execute_rag_turn(
        query=question,
        query_for_retrieval=question,
        target_models=None,
        available_models=None,
        retrieval_top_k=RETRIEVAL_TOP_K,
        rerank_top_k=RERANK_TOP_K,
        adapters=RagServingAdapters(
            retrieve=FA._capture_retrieve,
            rerank=FA._eval_strict_rerank,
            observe_structural_shadow=observe_structural_neighbor_shadow,
            generate=generate,
        ),
    )
    served = captured.get("served") or []
    return {
        "answer": (pipeline.get("generation") or {}).get("answer", ""),
        "served_ids": [str(c.get("id") or "") for c in served],
        "chunks": pipeline.get("chunks") or [],
    }


def appendix_block(span: str, fragment_number: int | None) -> str:
    cite = f" [F{fragment_number}]" if fragment_number else ""
    return f"\n\n---\n⚠️ **{APPENDIX_HEADER}**\n- \"**{span.strip()}**\"{cite}"


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    cfg = _args()

    receipt = yaml.safe_load(open(RECEIPT, encoding="utf-8"))
    gold = [r for r in receipt["per_gold"] if r["qid"] == cfg["qid"]][0]
    fact = [f for f in gold["facts"] if f["key"].startswith(cfg["fact"])][0]
    valor, texto = fact["valor"], fact["texto"]
    question = gold["question"]

    inject_rows = (
        fetch_by_prefix(cfg["inject"], list(gold["pool_ids"]))
        if cfg["mode"] == "serve"
        else []
    )

    reps = []
    for index in range(cfg["reps"]):
        if cfg["mode"] == "serve":
            base = run_turn(question, [])
            oracle = run_turn(question, inject_rows)
            base_votes = FA.judge_conveyed21(valor, texto, base["answer"])
            oracle_votes = FA.judge_conveyed21(valor, texto, oracle["answer"])
            reps.append(
                {
                    "rep": index,
                    "base_yes": base_votes["yes"],
                    "oracle_yes": oracle_votes["yes"],
                    "oracle_ids_admitidos": [
                        cid for cid in oracle["served_ids"]
                        if any(cid.startswith(p) for p in cfg["inject"])
                    ],
                    "base_answer": base["answer"],
                    "oracle_answer": oracle["answer"],
                }
            )
        else:
            base = run_turn(question, [])
            served = base["chunks"]
            span = None
            fragment_number = None
            pattern = re.compile(cfg["span_grep"], re.IGNORECASE)
            for position, chunk in enumerate(served, start=1):
                content = str(chunk.get("content") or "")
                for line in re.split(r"(?<=[.;:])\s+|\n", content):
                    if pattern.search(line) and len(line.strip()) > 25:
                        span, fragment_number = line.strip(), position
                        break
                if span:
                    break
            if not span:
                raise SystemExit(
                    f"span no encontrado en los {len(served)} servidos con "
                    f"/{cfg['span_grep']}/ — el oráculo no es construible"
                )
            augmented = base["answer"] + appendix_block(span, fragment_number)
            base_votes = FA.judge_conveyed21(valor, texto, base["answer"])
            oracle_votes = FA.judge_conveyed21(valor, texto, augmented)
            reps.append(
                {
                    "rep": index,
                    "base_yes": base_votes["yes"],
                    "oracle_yes": oracle_votes["yes"],
                    "span": span,
                    "fragment_number": fragment_number,
                    "base_answer": base["answer"],
                    "oracle_answer": augmented,
                }
            )
        row = reps[-1]
        print(
            f"  rep{index}: base {row['base_yes']}/5 → oracle {row['oracle_yes']}/5"
            + (f"  [span F{row.get('fragment_number')}]" if cfg["mode"] == "appendix" else "")
        )

    firm = FA.THRESH_FIRM
    out = {
        "probe": "s293_reachability_v1",
        "git_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True
        ).stdout.decode().strip(),
        "qid": cfg["qid"],
        "fact": fact["key"],
        "valor": valor,
        "texto": texto,
        "mode": cfg["mode"],
        "inject": cfg["inject"],
        "span_grep": cfg["span_grep"],
        "THRESH_FIRM": firm,
        "reps": reps,
        "veredicto": {
            "n_reps": len(reps),
            "base_firme": sum(1 for r in reps if r["base_yes"] >= firm),
            "oracle_firme": sum(1 for r in reps if r["oracle_yes"] >= firm),
            "alcanzable": any(r["oracle_yes"] >= firm for r in reps),
            "max_oracle": max((r["oracle_yes"] for r in reps), default=0),
        },
    }
    path = os.path.join(
        os.getcwd(), "evals",
        f"s293_reachability_{cfg['qid']}_{cfg['fact'].replace('#','_')}.json",
    )
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"escrito: {path}")
    print(json.dumps(out["veredicto"], ensure_ascii=False))


if __name__ == "__main__":
    main()
