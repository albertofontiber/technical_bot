#!/usr/bin/env python3
"""s287_p1_sweep39_pool.py — SWEEP-39 de COMPOSICIÓN DE POOL ($0 LLM, solo DB/embeddings).

Capa de protección DETERMINISTA del gate de la PIEZA 1 (regla monótona-segura corpus-aware,
`catalog_resolver._drop_gates_pass` puerta 4) extendida de los 7 golds del probe de P1
(`s287_p1_probe_pool.py`: hp018 + 6 centinelas) a los **39 golds dev**. Reúsa esa maquinaria
tal cual (flags de la ruta HARNESS de `s287_p05_probe_pool.RETRIEVAL_FLAGS`, `describe`,
`CENTINELAS`) — nada duplicado, nada de código de pipeline tocado.

DOS BRAZOS (el mismo patrón del probe existente: se varía SOLO la presencia de corpus):
  p1      = estado REAL de este build: quarantine real (VACÍA tras el sunset P0.5) + presencia
            real consultada a la DB ⇒ la regla es lo único que puede conservar un token.
  pre_p1  = contrafactual: presencia VACÍA ⇒ `_token_core_absent_in_corpus` siempre True ⇒ el
            drop de paraguas/alias procede SIEMPRE = conducta pre-P1. Quarantine idéntica al
            brazo p1 (real/vacía) — así el ÚNICO factor variado es la regla, no el hotfix.
  p1_rep  = RÉPLICA del brazo p1 = CONTROL DE RUIDO (DEC-096b): el artefacto de P1 ya
            documentó que la composición se mueve entre réplicas del MISMO brazo (44 vs 45
            filas) ⇒ sin este control no se distingue efecto-de-regla de churn del instrumento.
            Se corre SOLO en los golds que la capa determinista marca como tocados por la
            regla: en los demás el par (p1, pre_p1) YA ES un control OFF-vs-OFF por
            construcción (misma salida de resolver ⇒ misma ruta de retrieval ⇒ cualquier
            diferencia es churn), y son 29 golds de suelo de ruido en vez de 2 réplicas de uno.
  Los brazos corren INTERLEAVED por gold (back-to-back) para que el churn se mida en la misma
  escala temporal que el contraste entre brazos.

CAPA DETERMINISTA (el instrumento fuerte, $0 y SIN churn): además del pool, se compara la
salida del resolver por gold (`resolve_query` + `apply_to_models`) entre brazos. Si
`drop_tokens`/`models_after` son IDÉNTICOS, la regla PROVABLEMENTE no puede tocar ese gold y
cualquier diferencia de pool es ruido del retriever. La atribución NO se apoya en el pool.

DOS PARCHES IN-PROCESS (declarados; ninguno toca lógica de retrieval):
  1. `corpus_pm_elements` se PINEA a un valor constante por brazo. No basta la inyección de
     `_presence` del probe de P1 en un sweep largo: el re-chequeo de fingerprint
     (`_PRESENCE_FP_RECHECK_S = 60s`) compara `fp=("arm","pre_p1")` contra el fingerprint real,
     no coincide, y RECARGA la presencia de la DB ⇒ el brazo pre_p1 se convertiría en p1 en
     silencio a los 60s. El pin también congela el set del brazo p1 en TODO el sweep
     (freeze-contract: misma presencia en las 3 pasadas).
  2. `_shadow_log` → no-op: `resolve_for_retrieval` hace un POST fire-and-forget a
     `identity_resolve_shadow` en cada query con token detectado. Es telemetría (no alimenta
     el pool), y el mandato del sweep es CERO escrituras en DB.

Salida: evals/s287_p1_sweep39_composicion_v1.json
Uso:  python scripts/s287_p1_sweep39_pool.py [--qids hp018,hp009]
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
assert (ROOT / "src").is_dir() and (ROOT / "evals").is_dir(), f"cwd no es la raíz: {ROOT}"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# los probes de P0.5/P1 fijan las flags de la ruta HARNESS en import-time y las re-afirman
# tras los imports (la cadena hace load_dotenv(override=True)) — se REUSAN tal cual para que
# este sweep mida la MISMA ruta que los dos gates anteriores
import s287_p05_probe_pool as P05  # noqa: E402
import s287_p1_probe_pool as P1  # noqa: E402

import yaml  # noqa: E402

from src.config import RETRIEVAL_TOP_K  # noqa: E402
from src.rag import catalog_resolver  # noqa: E402
from src.rag.retriever import extract_product_models, retrieve_chunks  # noqa: E402

P05._assert_flags()

GOLDS_PATH = ROOT / "evals" / "gold_answers_v1.yaml"
OUT_PATH = ROOT / "evals" / "s287_p1_sweep39_composicion_v1.json"
CENTINELAS = P1.CENTINELAS          # hp009 hp011 hp012 cat022 cat012 hp001 (ya verificados)
ARMS = ("p1", "pre_p1", "p1_rep")
# la composición que define el veredicto (el ORDEN dentro del pool NO entra: el gate es de
# COMPOSICIÓN — lo que el reranker puede ver), igual que en P0.5/P1
COMP_KEYS = ("pool_n", "pool_by_source_file", "pool_by_family")


# ────────────────────────────── golds ──────────────────────────────
def dev_golds(only: set[str] | None) -> list[dict]:
    raw = yaml.safe_load(GOLDS_PATH.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("golds") or []
    out = [g for g in rows if (g.get("split") or "").strip() == "dev"]
    if only:
        out = [g for g in out if g["qid"] in only]
    return out


def _stem(name: str) -> str:
    n = str(name or "").strip()
    return n[:-4] if n.lower().endswith(".pdf") else n


def known_support(gold: dict) -> list[str]:
    """source_files de SOPORTE CONOCIDO del gold: `pdfs_used` + los manuales de `citations`
    (píxel-verificados por Alberto). Un soporte conocido que SALE del pool con la regla
    ACTIVA es el FLAG ROJO que este sweep busca."""
    names = {_stem(p) for p in (gold.get("pdfs_used") or [])}
    for c in gold.get("citations") or []:
        if isinstance(c, dict) and c.get("manual"):
            names.add(_stem(c["manual"]))
    return sorted(n for n in names if n)


# ────────────────────────────── brazos ──────────────────────────────
_REAL_PRESENCE_FN = catalog_resolver.corpus_pm_elements


def pin_presence(elements: frozenset[str]) -> None:
    """Parche 1 (ver docstring): presencia CONSTANTE por brazo, inmune al TTL/fp-recheck."""
    catalog_resolver.corpus_pm_elements = lambda: elements


def suppress_shadow_log() -> None:
    """Parche 2 (ver docstring): CERO escrituras en DB."""
    catalog_resolver._shadow_log = lambda *a, **k: None  # noqa: SLF001


# ─────────────────────── capa determinista (sin churn) ───────────────────────
def det_state(question: str) -> dict:
    """Salida del resolver bajo el brazo pineado AHORA. Es la capa que ATRIBUYE: si esto no
    cambia entre brazos, la regla no puede tocar el gold (y el pool solo puede diferir por
    churn del retriever)."""
    models_pre = extract_product_models(question)
    res = catalog_resolver.resolve_query(question)
    return {
        "models_pre_resolve": list(models_pre),
        "detected": list(res["detected"]),
        "records_via": {r["token"]: r.get("via") for r in res["records"]},
        "drop_tokens": sorted(res["drop_tokens"]),
        "add_models": sorted(res["add_models"]),
        "models_after": catalog_resolver.apply_to_models(list(models_pre), res),
        "allowed_sources_n": len(res["allowed_sources"]),
        "allowed_sources": sorted(str(s) for s in res["allowed_sources"]),
    }


DET_KEYS = ("drop_tokens", "models_after", "add_models", "allowed_sources")


# ────────────────────────────── comparación ──────────────────────────────
def comp(d: dict) -> dict:
    return {k: d[k] for k in COMP_KEYS}


def sf_delta(base: dict, other: dict) -> dict:
    """Movimiento de source_files base→other (entran / salen / cambian de cuenta)."""
    b, o = base["pool_by_source_file"], other["pool_by_source_file"]
    keys = sorted(set(b) | set(o))
    return {
        "entran": {k: o[k] for k in keys if k not in b},
        "salen": {k: b[k] for k in keys if k not in o},
        "cambio_de_cuenta": {k: [b[k], o[k]] for k in keys
                             if k in b and k in o and b[k] != o[k]},
    }


def fam_delta(base: dict, other: dict) -> dict:
    b, o = base["pool_by_family"], other["pool_by_family"]
    keys = sorted(set(b) | set(o))
    return {
        "entran": {k: o[k] for k in keys if k not in b},
        "salen": {k: b[k] for k in keys if k not in o},
        "cambio_de_cuenta": {k: [b[k], o[k]] for k in keys
                             if k in b and k in o and b[k] != o[k]},
    }


def main() -> None:
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--qids"):
            raw = a.split("=", 1)[1] if "=" in a else sys.argv[sys.argv.index(a) + 1]
            only = {q.strip() for q in raw.split(",") if q.strip()}
    golds = dev_golds(only)
    print(f"sweep-39 · golds dev: {len(golds)} · top_k={RETRIEVAL_TOP_K}")

    suppress_shadow_log()

    # estado REAL de partida: quarantine del YAML (debe estar VACÍA tras el sunset P0.5) +
    # presencia real de la DB, cargada UNA vez y pineada para todo el sweep
    catalog_resolver._quarantine = None
    quarantine_real = sorted(catalog_resolver._quarantine_tokens())
    catalog_resolver._presence = None
    fp_before = catalog_resolver._try_corpus_fingerprint()
    t0 = time.time()
    real_elements = _REAL_PRESENCE_FN()
    assert real_elements, "presencia de corpus VACÍA/None — el brazo p1 sería vacuo (STOP)"
    print(f"presencia real: {len(real_elements)} elementos en {time.time() - t0:.1f}s "
          f"· quarantine={quarantine_real} · fp={fp_before}")
    if quarantine_real:
        print(f"  AVISO: quarantine NO vacía ({quarantine_real}) — el sunset P0.5 no está "
              f"cumplido; el sweep sigue midiendo SOLO la regla (misma quarantine en ambos "
              f"brazos), pero la interpretación del brazo pre_p1 lo debe declarar")
    arm_presence = {"p1": real_elements, "pre_p1": frozenset(), "p1_rep": real_elements}

    # resumible (~40s por retrieve · el sweep entero es ~1h): una línea JSON por gold
    partial = OUT_PATH.with_suffix(".partial.jsonl")
    done: dict[str, dict] = {}
    if partial.exists():
        for line in partial.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["qid"]] = rec
        print(f"resumiendo: {len(done)} golds ya medidos en {partial.name}")

    det: dict[str, dict[str, dict]] = {}
    pools: dict[str, dict[str, dict]] = {}
    fh = partial.open("a", encoding="utf-8")
    for i, g in enumerate(golds, 1):
        qid, q = g["qid"], g["question"]
        if qid in done and done[qid].get("presence_n") == len(real_elements):
            det[qid], pools[qid] = done[qid]["det"], done[qid]["pools"]
            print(f"  [{i:2d}/{len(golds)}] {qid}: (cache)", flush=True)
            continue
        det[qid], pools[qid] = {}, {}
        # capa determinista PRIMERO ($0): decide si hace falta la réplica de churn
        for arm in ("p1", "pre_p1"):
            pin_presence(arm_presence[arm])
            det[qid][arm] = det_state(q)
        rule_touches = not all(det[qid]["p1"][k] == det[qid]["pre_p1"][k] for k in DET_KEYS)
        arms = ARMS if rule_touches else ("p1", "pre_p1")
        for arm in arms:
            pin_presence(arm_presence[arm])
            if arm == "p1_rep":
                det[qid][arm] = det_state(q)
            t = time.time()
            pools[qid][arm] = P1.describe(retrieve_chunks(q, top_k=RETRIEVAL_TOP_K))
            pools[qid][arm]["arm"] = arm
            pools[qid][arm]["secs"] = round(time.time() - t, 1)
        c_same = comp(pools[qid]["p1"]) == comp(pools[qid]["pre_p1"])
        r_same = (comp(pools[qid]["p1"]) == comp(pools[qid]["p1_rep"])
                  if "p1_rep" in pools[qid] else None)
        fh.write(json.dumps({"qid": qid, "presence_n": len(real_elements),
                             "det": det[qid], "pools": pools[qid]},
                            ensure_ascii=False) + "\n")
        fh.flush()
        print(f"  [{i:2d}/{len(golds)}] {qid}: regla-toca={rule_touches} "
              f"comp_igual(p1 vs pre_p1)={c_same} comp_igual(réplica)={r_same} "
              f"pool_n={ {a: pools[qid][a]['pool_n'] for a in pools[qid]} }", flush=True)
    fh.close()
    fp_after = catalog_resolver._try_corpus_fingerprint()

    # ───────── veredicto por gold ─────────
    per_gold, rojos = [], []
    for g in golds:
        qid = g["qid"]
        p1, pre = pools[qid]["p1"], pools[qid]["pre_p1"]
        rep = pools[qid].get("p1_rep")
        rule_touches = not all(det[qid]["p1"][k] == det[qid]["pre_p1"][k] for k in DET_KEYS)
        comp_same = comp(p1) == comp(pre)
        replica_same = (comp(p1) == comp(rep)) if rep else None
        sup = known_support(g)
        # soporte conocido que estaba en el pool SIN la regla y desaparece CON la regla
        lost = [{"source_file": s, "n_pre_p1": pre["pool_by_source_file"].get(s, 0),
                 "n_p1": p1["pool_by_source_file"].get(s, 0),
                 "n_p1_replica": (rep["pool_by_source_file"].get(s, 0) if rep else None)}
                for s in sup
                if pre["pool_by_source_file"].get(s, 0) > 0
                and p1["pool_by_source_file"].get(s, 0) == 0]
        # atribuible a la REGLA solo si la regla puede tocar el gold Y la pérdida no se
        # reproduce como churn en la réplica del mismo brazo
        rojo = [x for x in lost if rule_touches and x["n_p1_replica"] == 0]
        row = {
            "qid": qid, "question": g["question"], "centinela": qid in CENTINELAS,
            "regla_toca_el_gold": rule_touches,
            "det_diff": {k: {"p1": det[qid]["p1"][k], "pre_p1": det[qid]["pre_p1"][k]}
                         for k in DET_KEYS if det[qid]["p1"][k] != det[qid]["pre_p1"][k]},
            "composicion_identica": comp_same,
            "replica_identica_mismo_brazo": replica_same,
            "pool_n": {a: pools[qid][a]["pool_n"] for a in pools[qid]},
            "delta_source_file_pre_p1_a_p1": sf_delta(pre, p1) if not comp_same else {},
            "delta_family_pre_p1_a_p1": fam_delta(pre, p1) if not comp_same else {},
            "delta_source_file_churn_p1_a_replica": (
                sf_delta(p1, rep) if (rep and not replica_same) else {}),
            "soporte_conocido": sup,
            "soporte_conocido_perdido": lost,
            "flag_rojo": bool(rojo),
        }
        if rojo:
            rojos.append({"qid": qid, "perdido": rojo})
        per_gold.append(row)

    n_ident = sum(1 for r in per_gold if r["composicion_identica"])
    n_diff = len(per_gold) - n_ident
    n_rule = sum(1 for r in per_gold if r["regla_toca_el_gold"])
    n_churn = sum(1 for r in per_gold if r["replica_identica_mismo_brazo"] is False)
    # SUELO DE RUIDO por construcción: golds cuya salida de resolver es IDÉNTICA entre brazos
    # ⇒ los dos retrieves son el MISMO estado (control OFF-vs-OFF, 29 pares en vez de 2)
    equiv = [r for r in per_gold if not r["regla_toca_el_gold"]]
    n_equiv_diff = sum(1 for r in equiv if not r["composicion_identica"])
    cent_rows = {r["qid"]: {"composicion_identica": r["composicion_identica"],
                            "regla_toca_el_gold": r["regla_toca_el_gold"],
                            "replica_identica_mismo_brazo": r["replica_identica_mismo_brazo"]}
                 for r in per_gold if r["centinela"]}
    # diffs NO explicables por la regla (la regla no toca el gold) = churn del instrumento
    churn_only = [r["qid"] for r in per_gold
                  if not r["composicion_identica"] and not r["regla_toca_el_gold"]]
    rule_diff = [r["qid"] for r in per_gold
                 if not r["composicion_identica"] and r["regla_toca_el_gold"]]

    # ── movimiento del SOPORTE CONOCIDO en los golds que la regla toca ──────────────
    # Es el eje que decide el veredicto: la composición puede moverse en cualquier
    # dirección, lo que importa es si el doc que SUSTENTA el gold gana o pierde presencia.
    soporte_mov = []
    for r in per_gold:
        if not r["regla_toca_el_gold"]:
            continue
        pl = pools[r["qid"]]
        for sf in r["soporte_conocido"]:
            cnt = {a: pl[a]["pool_by_source_file"].get(sf, 0) for a in pl}
            if not any(cnt.values()):
                continue          # nombre de cita sin match de source_file: inerte
            soporte_mov.append({
                "qid": r["qid"], "source_file": sf,
                "n_pre_p1": cnt["pre_p1"], "n_p1": cnt["p1"],
                "n_p1_replica": cnt.get("p1_rep"),
                "delta": cnt["p1"] - cnt["pre_p1"],
            })
    # magnitud comparada: efecto de la regla vs suelo de ruido (|Δ pool_n|)
    churn_abs = sorted((abs(pools[r["qid"]]["p1"]["pool_n"]
                            - pools[r["qid"]]["pre_p1"]["pool_n"])
                        for r in equiv), reverse=True)

    result = {
        "gate": "s287 P1 SWEEP-39 — composición de pool con la regla corpus-aware ACTIVA vs "
                "contrafactual pre-P1 (presencia VACÍA), 39 golds dev, $0 LLM",
        "flags": dict(P05.RETRIEVAL_FLAGS),
        "retrieval_top_k": RETRIEVAL_TOP_K,
        "arms": {
            "p1": "presencia REAL (regla activa) — estado de este build",
            "pre_p1": "presencia VACÍA (regla inerte) = conducta pre-P1",
            "p1_rep": "réplica del brazo p1 = control de ruido OFF-vs-OFF (DEC-096b)",
        },
        "estado": {
            "quarantine_yaml": quarantine_real,
            "presence_elements_n": len(real_elements),
            "corpus_fingerprint_antes": list(fp_before) if fp_before else None,
            "corpus_fingerprint_despues": list(fp_after) if fp_after else None,
            "corpus_estable_durante_el_sweep": fp_before == fp_after,
        },
        "parches_declarados": [
            "corpus_pm_elements pineada por brazo (inmune al fp-recheck de 60s que revertiría "
            "la inyección de _presence a mitad de sweep)",
            "_shadow_log no-op (cero escrituras en DB; telemetría, no alimenta el pool)",
        ],
        "resumen": {
            "n_golds": len(per_gold),
            "n_composicion_identica": n_ident,
            "n_composicion_con_diff": n_diff,
            "n_golds_que_la_regla_toca": n_rule,
            "qids_que_la_regla_toca": [r["qid"] for r in per_gold if r["regla_toca_el_gold"]],
            "n_golds_con_churn_en_la_replica": n_churn,
            "suelo_de_ruido_por_construccion": {
                "n_pares_equivalentes": len(equiv),
                "n_con_diff_de_composicion": n_equiv_diff,
                "qids": [r["qid"] for r in equiv if not r["composicion_identica"]],
                "nota": "pares con salida de resolver IDÉNTICA entre brazos = mismo estado "
                        "de retrieval ⇒ toda diferencia de composición es churn del "
                        "instrumento (control OFF-vs-OFF de N pares, no de 2 réplicas)",
            },
            "qids_diff_atribuible_a_la_regla": rule_diff,
            "qids_diff_solo_churn": churn_only,
            "movimiento_del_soporte_conocido": soporte_mov,
            "magnitud": {
                "churn_delta_pool_n_pares_equivalentes": churn_abs,
                "churn_max": (churn_abs[0] if churn_abs else 0),
                "churn_medio": (round(sum(churn_abs) / len(churn_abs), 2) if churn_abs else 0),
                "efecto_regla_delta_pool_n": {
                    r["qid"]: [pools[r["qid"]]["pre_p1"]["pool_n"],
                               pools[r["qid"]]["p1"]["pool_n"]]
                    for r in per_gold if r["regla_toca_el_gold"]},
                "nota": "|Δ pool_n| NO es la métrica del veredicto (hp019 mueve solo 2 filas "
                        "de tamaño y 41 de soporte): sirve para situar el efecto frente al "
                        "suelo de ruido. El veredicto lo da `movimiento_del_soporte_conocido`.",
            },
            "n_flags_rojos": len(rojos),
            "flags_rojos": rojos,
            "centinelas": cent_rows,
            "centinelas_sin_efecto_de_regla": all(
                not v["regla_toca_el_gold"] for v in cent_rows.values()),
        },
        "por_gold": per_gold,
        "capa_determinista": det,
        "pools": pools,
        "nota": "pool FILTRADO pre-rerank (el rerank es LLM y NO se llama); el gate es de "
                "COMPOSICIÓN, no de orden. La igualdad estricta de composición NO es "
                "utilizable sola como criterio (el artefacto de P1 ya documentó churn entre "
                "réplicas del mismo brazo): la ATRIBUCIÓN la da la capa determinista "
                "(drop_tokens/models_after del resolver), que no tiene churn.",
    }
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    print(f"\nescrito {OUT_PATH}")
    print(f"  idénticos={n_ident}/{len(per_gold)} · con diff={n_diff} "
          f"(regla={len(rule_diff)} · churn={len(churn_only)}) "
          f"· la regla toca {n_rule} golds · churn en réplica={n_churn} "
          f"· suelo de ruido={n_equiv_diff}/{len(equiv)} pares equivalentes con diff "
          f"· FLAGS ROJOS={len(rojos)}")
    for r in per_gold:
        if not r["composicion_identica"]:
            print(f"    DIFF {r['qid']}: regla-toca={r['regla_toca_el_gold']} "
                  f"pool_n={r['pool_n']} "
                  f"entran={r['delta_source_file_pre_p1_a_p1']['entran']} "
                  f"salen={r['delta_source_file_pre_p1_a_p1']['salen']} "
                  f"cambio={r['delta_source_file_pre_p1_a_p1']['cambio_de_cuenta']}")
    for r in rojos:
        print(f"    FLAG ROJO {r['qid']}: {r['perdido']}")


if __name__ == "__main__":
    main()
