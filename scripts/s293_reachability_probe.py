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
      [--cobertura-verificada '<cómo verificaste que el carrier cubre el hecho>']  ← exigido para un NO
  python scripts/s293_reachability_probe.py <qid> <fact_prefix> appendix --span-grep <regex>   [reps]
  … [--receipt evals/s100_factlevel_full_v3_<fecha>.yaml]   (por defecto: el FULL v3* MÁS RECIENTE)
Salida: evals/s293_reachability_<qid>_<fact>.json

Endurecimiento s324d (TECH_DEBT #89, cinco defectos vistos en las 8 sondas de etapa 3):
  1. el recibo FULL ya no está pineado al 1-ago: `--receipt` o el más reciente; se estampa `receipt_usado`;
  2. `appendix` elige el span CON guard de cobertura (`reachability_verdict.elegir_span`: no parte por «:»,
     extiende hasta 2 líneas, exige los tokens del valor); si nada cubre → la rep queda NO construible y el
     veredicto INCONCLUYENTE explícito (nunca se juzga un span que no cubre el hecho);
  3. un fallo en una rep tardía escribe un recibo PARCIAL (`estado: PARCIAL`) con las reps ya juzgadas;
  4. el recibo lleva `coste` (usage real por llamada, `scripts/usage_meter.py`);
  5. `serve` declara los carriers YA servidos en la base (`carriers_ya_servidos_en_base`): ahí el oráculo mide
     PROMINENCIA, no evidencia ausente; no duplica la fila (eleva su similarity in-place) y guarda la
     composición de la base (`base_served_ids`).
  Dúo r34 (Sol): el oráculo de `serve` es ahora PAREADO por defecto — se genera sobre la MISMA vista que
  recibió el generador en la base + la inyección (sin churn de retrieval/rerank), como `appendix`;
  `--oracle-fresco` restaura los turnos independientes. Los votos caídos del juez (`n_fail`) se registran y
  una rep no firme con votos caídos NO sostiene un negativo (INCONCLUYENTE_JUEZ_INCOMPLETO). Un recibo
  PARCIAL nunca lleva `ALCANZABLE`/`NO_ALCANZABLE` a secas (`PARCIAL_…`).
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

import glob as _glob  # noqa: E402

from scripts.reachability_verdict import elegir_receipt  # noqa: E402

RECEIPT_LEGADO = "evals/s100_factlevel_full_v32_full_20260801.yaml"   # el pin histórico (defecto 1 de #89)


def receipt_por_defecto(explicito: str | None = None) -> str:
    return elegir_receipt(sorted(_glob.glob("evals/s100_factlevel_full_v3*.yaml")), explicito)


def _args() -> dict:
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    out = {
        "qid": sys.argv[1],
        "fact": sys.argv[2],
        "mode": sys.argv[3],
        "inject": [],
        "span_grep": None,
        "cobertura_verificada": "",
        "reps": 3,
        "receipt": None,
        "oracle_pareado": True,
    }
    rest = sys.argv[4:]
    while rest:
        token = rest.pop(0)
        if token == "--oracle-fresco":
            # (Sol r34) comportamiento anterior: base y oráculo como turnos INDEPENDIENTES (churn de
            # retrieval/rerank mezclado con el efecto de la inyección). Por defecto el oráculo se genera
            # sobre la MISMA vista de la base (pareado), como ya hacía `appendix`.
            out["oracle_pareado"] = False
        elif token == "--receipt":
            out["receipt"] = rest.pop(0)
        elif token == "--cobertura-verificada":
            # Atestación EXPLÍCITA del operador de que el carrier inyectado CUBRE el hecho.
            # Sin ella no se puede emitir NO_ALCANZABLE (s321): el Protocolo 4 ya exigía
            # «verifica el carrier ANTES de inyectar» y nada lo hacía cumplir.
            out["cobertura_verificada"] = rest.pop(0)
        elif token == "--inject":
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


def _inyectar(rows: list[dict], inject_rows: list[dict], captured: dict) -> list[dict]:
    """Mete los carriers en la vista: si uno YA está, no se duplica (se eleva su similarity in-place y se
    declara — #89 defecto 5); si no, se añade con la similarity techo."""
    if not inject_rows:
        return rows
    ceiling = max([float(c.get("similarity") or 0.0) for c in rows] + [0.9])
    presentes = {str(c.get("id") or ""): c for c in rows}
    for row in inject_rows:
        rid = str(row.get("id") or "")
        if rid in presentes:
            presentes[rid]["similarity"] = ceiling
            captured.setdefault("ya_servidos", []).append(rid)
            continue
        extra = dict(row)
        extra["similarity"] = ceiling
        rows.append(extra)
    return rows


def generar_sobre_vista(question: str, vista_base: list[dict], inject_rows: list[dict]) -> dict:
    """Oráculo PAREADO (Sol r34): la MISMA vista que recibió el generador en la base + la inyección, sin
    volver a pasar por retrieval/rerank (mecanismo `gen_answer_only` de s289/DEC-168). Aísla el efecto de
    la evidencia del churn de composición."""
    captured: dict = {}
    rows = _inyectar([dict(c) for c in vista_base], inject_rows, captured)
    served = admitted_evidence_rows(rows)
    generation = FA.generate_answer(question, rows, available_models=None)   # dict (como en el seam)
    return {
        "answer": (generation or {}).get("answer", "") if isinstance(generation, dict) else str(generation or ""),
        "served_ids": [str(c.get("id") or "") for c in served],
        "served_ids_sin_inyeccion": [str(c.get("id") or "") for c in vista_base],
        "carriers_ya_servidos": captured.get("ya_servidos") or [],
        "chunks": [],
        "pareado": True,
    }


def run_turn(question: str, inject_rows: list[dict]) -> dict:
    """Turno completo por el seam (espejo de FA.run_pipeline) con inyección opcional
    en la VISTA del generador. Devuelve también `vista` (las filas EXACTAS que recibió el
    generador antes de inyectar) para poder generar el oráculo pareado sobre ella."""
    captured: dict = {}

    def generate(query, chunks, available_models=None):
        rows = [dict(c) for c in chunks]
        captured["served_sin_inyeccion"] = [str(c.get("id") or "") for c in rows]
        captured["vista"] = copy.deepcopy(rows)
        rows = _inyectar(rows, inject_rows, captured)
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
        "served_ids_sin_inyeccion": captured.get("served_sin_inyeccion") or [],
        "carriers_ya_servidos": captured.get("ya_servidos") or [],
        "chunks": pipeline.get("chunks") or [],
        "vista": captured.get("vista") or [],
        "pareado": False,
    }


def appendix_block(span: str, fragment_number: int | None) -> str:
    cite = f" [F{fragment_number}]" if fragment_number else ""
    return f"\n\n---\n⚠️ **{APPENDIX_HEADER}**\n- \"**{span.strip()}**\"{cite}"


# La lógica de veredicto vive en `reachability_verdict` SIN dependencias pesadas: un guard
# solo protege si se ejecuta, y un test sobre este módulo se cae en CI por falta de entorno
# (PR #263: KeyError SUPABASE_URL en CI mientras en local pasaba con el .env copiado).
from scripts.reachability_verdict import (  # noqa: E402
    carriers_ya_servidos,
    elegir_span,
    prueba_de_entrega,
    veredicto_recibo,
)
from scripts.usage_meter import METER, cost_of  # noqa: E402


def sello_freeze() -> dict:
    """Sello PARCIAL del freeze-contract. Mejora sobre `git_sha` a secas —que dejaba envejecer un
    veredicto en silencio mientras el corpus se movía tres veces en un día— pero **NO es completo**,
    y llamarlo así era framing por encima de la realidad (dúo s321, ambos revisores).

    **Lo que NO cubre, declarado**: huella/conteo del corpus (una mutación in-place es invisible),
    configuración física del índice, versión del modelo de embeddings, semillas, y el closure del
    código. Un patrón más cercano al contrato vive en `factlevel_assessment.py` (manifest del run).
    """
    return {
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                  capture_output=True).stdout.decode().strip(),
        "CHUNKS_TABLE": FA.CHUNKS_TABLE,
        "RETRIEVAL_TOP_K": FA.RETRIEVAL_TOP_K,
        "RERANK_TOP_K": FA.RERANK_TOP_K,
        "RERANKER_BACKEND": FA.RERANKER_BACKEND,
        "MERGE_STRATEGY": FA.MERGE_STRATEGY,
        "LLM_MAX_TOKENS": FA.LLM_MAX_TOKENS,
        "LLM_MODEL": FA.LLM_MODEL,
        "GENERATOR_PROMPT_VARIANT": os.getenv("GENERATOR_PROMPT_VARIANT"),
        "juez": {"model": FA.JUDGE_MODEL, "K": FA.K, "THRESH_FIRM": FA.THRESH_FIRM},
        "INSTRUMENT_VERSION": FA.INSTRUMENT_VERSION,
    }


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    cfg = _args()
    receipt_path = receipt_por_defecto(cfg.get("receipt"))
    receipt = yaml.safe_load(open(receipt_path, encoding="utf-8"))
    print(f"recibo FULL: {receipt_path}" + ("" if receipt_path != RECEIPT_LEGADO else "  (legado 1-ago)"))
    gold = [r for r in receipt["per_gold"] if r["qid"] == cfg["qid"]][0]
    fact = [f for f in gold["facts"] if f["key"].startswith(cfg["fact"])][0]
    valor, texto = fact["valor"], fact["texto"]
    question = gold["question"]

    METER.install()          # (#89 defecto 4) coste real por llamada, observación pura
    inject_rows = (
        fetch_by_prefix(cfg["inject"], list(gold["pool_ids"]))
        if cfg["mode"] == "serve"
        else []
    )

    reps: list[dict] = []
    path = os.path.join(
        os.getcwd(), "evals",
        f"s293_reachability_{cfg['qid']}_{cfg['fact'].replace('#','_')}.json",
    )

    def escribir(out: dict) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)

    def recibo(estado: str, error: str | None = None) -> dict:
        firm = FA.THRESH_FIRM
        vered = veredicto_recibo(reps, firm, bool(cfg.get("cobertura_verificada")), estado, cfg["reps"])
        ya = sorted({p for r in reps for p in (r.get("carriers_ya_servidos_en_base") or [])})
        no_constr = [r["rep"] for r in reps if r.get("no_construible")]
        return {
            "probe": "s293_reachability_v1",
            "instrumento_endurecido": ("s321 (prueba de entrega por modo + sello de freeze PARCIAL) · "
                                       "s324d (#89: recibo FULL vigente, guard de cobertura del span, recibo "
                                       "parcial, coste, carrier ya servido declarado)"),
            "estado": estado,
            "error": error,
            "⚠️_sesion_de_la_medicion": ("el prefijo `s293` del nombre y de `probe` lo deriva el script "
                                         "de SÍ MISMO, no de la sesión que midió — comprobar `sello_freeze"
                                         ".git_sha` y la fecha del fichero antes de atribuirlo (dúo s321)"),
            "sello_freeze_PARCIAL": sello_freeze(),
            "sello_no_cubre": ["huella/conteo del corpus", "config del índice", "versión de embeddings", "seeds", "closure del código"],
            "receipt_usado": receipt_path,
            "qid": cfg["qid"],
            "fact": fact["key"],
            "valor": valor,
            "texto": texto,
            "mode": cfg["mode"],
            "inject": cfg["inject"],
            "span_grep": cfg["span_grep"],
            "THRESH_FIRM": firm,
            "cobertura_verificada": cfg.get("cobertura_verificada") or None,
            "reps": reps,
            "veredicto": {
                "n_reps": len(reps),
                "n_reps_pedidas": cfg["reps"],
                "base_firme": sum(1 for r in reps if r["base_yes"] >= firm),
                "oracle_firme": vered["oracle_firme"],
                "alcanzable": vered["alcanzable"],
                "max_oracle": max((r["oracle_yes"] for r in reps), default=0),
                "veredicto": vered["veredicto"],
                "veredicto_reps_juzgadas": vered["veredicto_reps_juzgadas"],
                "reps_sin_prueba_de_entrega": vered["reps_sin_prueba_de_entrega"],
                "reps_juez_incompleto": vered["reps_juez_incompleto"],
                "oracle_pareado": cfg["oracle_pareado"] if cfg["mode"] == "serve" else True,
                "reps_no_construibles": no_constr,
                "carriers_ya_servidos_en_base": ya,
                "aviso_prominencia": (f"los carriers {ya} YA estaban en la vista base: en esas reps el oráculo "
                                      "mide PROMINENCIA (similarity elevada), no evidencia ausente") if ya else None,
            },
            "coste": {**cost_of(METER.summary()), "medicion_disponible": METER.disponible(),
                      "proveedores_instalados": METER.proveedores_instalados,
                      "n_llamadas_medidas": METER.summary()["n_calls"]},
        }

    try:
        for index in range(cfg["reps"]):
            if cfg["mode"] == "serve":
                METER.phase = "turn_base"
                base = run_turn(question, [])
                METER.phase = "turn_oracle"
                if cfg["oracle_pareado"]:
                    oracle = generar_sobre_vista(question, base["vista"], inject_rows)
                else:
                    oracle = run_turn(question, inject_rows)
                METER.phase = "judge"
                base_votes = FA.judge_conveyed21(valor, texto, base["answer"])
                oracle_votes = FA.judge_conveyed21(valor, texto, oracle["answer"])
                reps.append(
                    {
                        "rep": index,
                        "base_yes": base_votes["yes"],
                        "base_n_fail": base_votes["n_fail"],
                        "oracle_yes": oracle_votes["yes"],
                        "oracle_n_fail": oracle_votes["n_fail"],
                        "oracle_pareado": bool(oracle.get("pareado")),
                        "oracle_ids_admitidos": [
                            cid for cid in oracle["served_ids"]
                            if any(cid.startswith(p) for p in cfg["inject"])
                        ],
                        "base_served_ids": base["served_ids"],
                        "oracle_served_ids": oracle["served_ids"],
                        "carriers_ya_servidos_en_base": carriers_ya_servidos(base["served_ids"], cfg["inject"]),
                        "carriers_ya_servidos_en_oracle_sin_inyeccion": carriers_ya_servidos(
                            oracle["served_ids_sin_inyeccion"], cfg["inject"]),
                        "base_answer": base["answer"],
                        "oracle_answer": oracle["answer"],
                    }
                )
            else:
                METER.phase = "turn_base"
                base = run_turn(question, [])
                served = base["chunks"]
                eleccion = elegir_span(served, cfg["span_grep"], valor, texto)
                span, fragment_number = eleccion["span"], eleccion["fragment_number"]
                if not span or not eleccion["cubre"]["ok"]:
                    # (#89 defecto 2) no se juzga un span que no cubre el hecho: la rep queda NO construible
                    motivo = ("span no encontrado" if not span else
                              f"el mejor span no cubre el valor (ausentes: {eleccion['cubre']['ausentes']})")
                    METER.phase = "judge"
                    base_votes = FA.judge_conveyed21(valor, texto, base["answer"])
                    reps.append({"rep": index, "base_yes": base_votes["yes"], "base_n_fail": base_votes["n_fail"],
                                 "oracle_yes": 0, "oracle_n_fail": 0,
                                 "span": None, "fragment_number": None, "no_construible": motivo,
                                 "eleccion_span": eleccion, "base_answer": base["answer"], "oracle_answer": None})
                else:
                    augmented = base["answer"] + appendix_block(span, fragment_number)
                    METER.phase = "judge"
                    base_votes = FA.judge_conveyed21(valor, texto, base["answer"])
                    oracle_votes = FA.judge_conveyed21(valor, texto, augmented)
                    reps.append(
                        {
                            "rep": index,
                            "base_yes": base_votes["yes"],
                            "base_n_fail": base_votes["n_fail"],
                            "oracle_yes": oracle_votes["yes"],
                            "oracle_n_fail": oracle_votes["n_fail"],
                            "span": span,
                            "fragment_number": fragment_number,
                            "span_extendido": eleccion["extendido"],
                            "span_cobertura": eleccion["cubre"],
                            "base_answer": base["answer"],
                            "oracle_answer": augmented,
                        }
                    )
            row = reps[-1]
            row["prueba_entrega"] = prueba_de_entrega(cfg, row)
            print(
                f"  rep{index}: base {row['base_yes']}/5 → oracle {row['oracle_yes']}/5"
                + (f"  [span F{row.get('fragment_number')}]" if cfg["mode"] == "appendix" and row.get("span") else "")
                + (f"  ⚠️ NO CONSTRUIBLE: {row['no_construible']}" if row.get("no_construible") else "")
                + ("" if row["prueba_entrega"]["ok"]
                   else f"  ⚠️ SIN PRUEBA DE ENTREGA: {row['prueba_entrega']['motivo']}")
                + (f"  ⚠️ carrier YA servido en base: {row['carriers_ya_servidos_en_base']}"
                   if row.get("carriers_ya_servidos_en_base") else "")
            )
    except BaseException as exc:      # (#89 defecto 3) recibo PARCIAL con las reps ya juzgadas
        out = recibo("PARCIAL", error=f"{type(exc).__name__}: {exc}")
        escribir(out)
        print(f"\n⚠️  fallo en la rep {len(reps)}: {type(exc).__name__}: {exc} — recibo PARCIAL escrito: {path}")
        print(json.dumps(out["veredicto"], ensure_ascii=False))
        raise

    firm = FA.THRESH_FIRM
    out = recibo("COMPLETO")
    veredicto_txt, sin_entrega = out["veredicto"]["veredicto"], out["veredicto"]["reps_sin_prueba_de_entrega"]
    if out["veredicto"]["reps_no_construibles"]:
        print(f"\n⚠️  reps NO construibles {out['veredicto']['reps_no_construibles']}: el span elegido no cubría el "
              "valor del hecho (guard #89) — se declaran INCONCLUYENTES, no se juzgó un apéndice incompleto.")
    if out["veredicto"]["aviso_prominencia"]:
        print(f"\n⚠️  {out['veredicto']['aviso_prominencia']}")
    if veredicto_txt == "INCONCLUYENTE_SIN_COBERTURA_ATESTADA":
        print("\n⚠️  NO se puede emitir «NO alcanzable»: la entrega está probada, pero NADIE ha "
              "atestado\n   que el carrier inyectado CUBRA el hecho. Verifícalo y re-lanza con "
              "--cobertura-verificada\n   '<cómo lo comprobaste>'. ENTREGA ≠ COBERTURA: un oráculo "
              "incompleto entrega perfecto\n   y produce un NO falso (regla-C de DEC-173, hp011#2 "
              "con media etiqueta).")
    if veredicto_txt == "INCONCLUYENTE_SIN_PRUEBA_DE_ENTREGA":
        print(f"\n⚠️  NO se puede emitir «NO alcanzable»: las reps {sin_entrega} no prueban que la "
              f"evidencia llegara al generador. Veredicto = INCONCLUYENTE. Arregla la entrega y "
              f"re-mide; un «no transmite» sin entrega probada no distingue incapacidad de ausencia.")
    escribir(out)
    print(f"escrito: {path}")
    print(json.dumps(out["veredicto"], ensure_ascii=False))
    if out["coste"]["medicion_disponible"] and out["coste"]["n_llamadas_medidas"]:
        print(f"coste: ${out['coste']['usd_total']} ({out['coste']['n_llamadas_medidas']} llamadas medidas)")
    else:
        print("coste: NO MEDIDO (medidor no disponible o 0 llamadas capturadas)")


if __name__ == "__main__":
    main()
