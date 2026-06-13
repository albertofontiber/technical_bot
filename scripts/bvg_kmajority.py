#!/usr/bin/env python3
"""bvg_kmajority.py — runner K-mayoría del ciclo baseline→A/B→held-out (gate s58, DEC-036b).

Materializa el diseño v3 gateado por el dúo (evals/_s58_gate_design_proposal.md; traza en
DECISIONS DEC-039). NO sustituye a test_bot_vs_gold.py (harness single-pass legacy con su
serie histórica): este runner es el instrumento del ciclo A/B — contexts CONGELADOS por gold
+ K generaciones + K juicios GPT-5.5 + agregación K-mayoría (DEC-015: modal + flag) +
run-manifest completo (DEC-021 §F).

Fases (reanudables; cada una persiste su artefacto y se salta lo ya hecho):
  freeze    retrieve(50)+rerank(5) UNA vez por gold dev → evals/s58_frozen_contexts.json
            (con `context` hidratado por id — las ramas keyword/content del retriever lo
            omiten en su SELECT, deuda s48; el brazo B del A/B s59 lo necesita).
  generate  K=5 × generate_answer sobre el top-5 congelado (brazo A: blurb OFF) →
            evals/s58_generations.json (answer + stop_reason + output_tokens por run).
  judge     juez gpt-5.5 (prompts importados de test_bot_vs_gold + response_format
            json_object = JUEZ NUEVO CONGELADO de la ventana) → evals/s58_judgments.json.
  report    partición v3 pre-registrada (PASS-control modal-PASS [letra PREREG] /
            residual 0-PASS / K-INESTABLE) + audit context-sufficiency determinista sobre
            el top-5 congelado (buckets: GENERACION / GENERACION-filtro / SUB-RETRIEVAL
            [multi-doc|within-doc per-hecho] / MIXTO / INDETERMINADO-solo-debiles) +
            stop_reason + run-manifest → evals/s58_gate_report.yaml + s58_run_manifest.json.

Uso:
  python scripts/bvg_kmajority.py freeze|generate|judge|report|all [--k 5] [--workers 5]

El held-out NO se toca (gold_store.dev() = la puerta con embargo, DEC-023). El A/B s59
correrá el brazo B desde s58_frozen_contexts.json y el atomic_scorer sobre las
generaciones persistidas de ambos brazos (cláusula C2 propuesta al PREREG).
"""
from __future__ import annotations

import os
# chunks_v2 + HyDE OFF (= prod) ANTES de importar config/retriever (leen env al cargar).
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
import datetime
import hashlib
import inspect
import json
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"   # re-asegurar tras load_dotenv
os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import gold_store  # noqa: E402
import test_bot_vs_gold as TBG  # noqa: E402  (prompts del juez — fuente única, no se duplican)
from src.config import (  # noqa: E402
    CHUNKS_TABLE, CHUNKS_IS_V2, RETRIEVAL_TOP_K, RERANK_TOP_K,
    LLM_MODEL, LLM_MAX_TOKENS, SUPABASE_URL, SUPABASE_SERVICE_KEY,
)
from src.config import RERANKER_BACKEND  # noqa: E402
from src.rag.retriever import retrieve_chunks  # noqa: E402
from src.rag.reranker import (  # noqa: E402
    rerank, rerank_chunks, RERANK_MODEL, VOYAGE_RERANK_MODEL,
)
from src.rag.generator import generate_answer, SYSTEM_PROMPT, RELEVANCE_THRESHOLD  # noqa: E402
import src.rag.generator as _gen_mod  # noqa: E402
import src.rag.reranker as _rr_mod  # noqa: E402
import src.rag.retriever as _ret_mod  # noqa: E402
import src.rag.series_registry as _series_mod  # noqa: E402

EVALS = ROOT / "evals"
# Run-id del ciclo (s59+, cláusula R4 del PREREG): BVG_RUN_ID selecciona el juego de
# artefactos. Default "s58" = comportamiento EXACTO previo (mismos ficheros, resume-skip
# intacto). El brazo de un lever corre con BVG_RUN_ID=s59 → artefactos s59_* nuevos;
# la equivalencia del instrumento se VERIFICA en runtime contra el manifest s58
# (generator/judge SHAs — abort si difieren), no se declara.
RUN_ID = os.environ.get("BVG_RUN_ID", "s58")
F_CONTEXTS = EVALS / f"{RUN_ID}_frozen_contexts.json"
F_GENERATIONS = EVALS / f"{RUN_ID}_generations.json"
F_JUDGMENTS = EVALS / f"{RUN_ID}_judgments.json"
F_MANIFEST = EVALS / f"{RUN_ID}_run_manifest.json"
F_REPORT = EVALS / f"{RUN_ID}_gate_report.yaml"
F_BASELINE_MANIFEST = EVALS / "s58_run_manifest.json"   # referencia de equivalencia R4

JUDGE_MODEL = "gpt-5.5"
JUDGE_TRUNCATION = 3000  # knob del juez (vive en judge(), no en los prompts — manifest)
ORDER = {"PASS": 2, "PARCIAL": 1, "FALLO": 0}  # peor = menor (regla cosmética de empate)

_write_lock = threading.Lock()


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _git_commit() -> str | None:
    try:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save(path: Path, data: dict) -> None:
    with _write_lock:
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


_HEADERS = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


def corpus_fingerprint() -> dict:
    """count + max(created_at) de chunks_v2 + dimensión LIFECYCLE (s64, #46) —
    caza ingesta Y supersesiones/cambios de status en la ventana de freeze (el
    corpus EFECTIVO que ve el retrieval puede cambiar sin tocar chunks_v2:
    marcar un doc superseded lo saca de los pools con count/created_at
    intactos). Límite declarado restante: no detecta edits in-place de content
    (cláusula disciplinaria DEC-036e)."""
    out = {"table": CHUNKS_TABLE, "count": None, "max_created_at": None,
           "documents_status": None, "chunks_excluded_by_lifecycle": None}
    try:
        with httpx.Client(timeout=20.0) as c:
            r = c.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                      headers={**_HEADERS, "Prefer": "count=exact", "Range": "0-0"},
                      params={"select": "id"})
            cr = r.headers.get("content-range", "*/0")
            out["count"] = int(cr.split("/")[-1]) if "/" in cr else None
            r2 = c.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                       headers=_HEADERS,
                       params={"select": "created_at", "order": "created_at.desc", "limit": "1"})
            rows = r2.json()
            out["max_created_at"] = rows[0]["created_at"] if rows else None

            # lifecycle: status de documents (paginado) + chunks excluidos en runtime
            statuses: list[str] = []
            offset = 0
            while True:
                page = c.get(f"{SUPABASE_URL}/rest/v1/documents", headers=_HEADERS,
                             params={"select": "id,status", "limit": "1000",
                                     "offset": str(offset)}).json()
                statuses.extend((row.get("id"), row.get("status")) for row in page)
                if len(page) < 1000:
                    break
                offset += 1000
            from collections import Counter
            out["documents_status"] = dict(Counter(s for _, s in statuses))
            inactive_ids = [i for i, s in statuses if s != "active"]
            n_excl = 0
            for j in range(0, len(inactive_ids), 50):
                id_list = ",".join(f'"{d}"' for d in inactive_ids[j:j + 50])
                rx = c.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                           headers={**_HEADERS, "Prefer": "count=exact", "Range": "0-0"},
                           params={"select": "id", "document_id": f"in.({id_list})"})
                crx = rx.headers.get("content-range", "*/0")
                n_excl += int(crx.split("/")[-1]) if "/" in crx else 0
            out["chunks_excluded_by_lifecycle"] = n_excl
    except Exception as e:
        out["error"] = str(e)[:200]
    return out


def hydrate_context(chunks: list[dict]) -> int:
    """Rellena chunk['context'] por id para los que no lo traen (ramas keyword/content).
    Devuelve nº hidratados. El brazo A no usa el blurb; el B de s59 sí — el artefacto
    congelado debe servir a AMBOS brazos."""
    missing = [c for c in chunks if not c.get("context") and c.get("id") is not None]
    if not missing:
        return 0
    ids = ",".join(str(c["id"]) for c in missing)
    try:
        with httpx.Client(timeout=20.0) as cl:
            r = cl.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                       headers=_HEADERS,
                       params={"select": "id,context", "id": f"in.({ids})"})
        by_id = {row["id"]: row.get("context") for row in r.json()}
    except Exception:
        return 0
    n = 0
    for c in missing:
        ctx = by_id.get(c["id"])
        if ctx:
            c["context"] = ctx
            n += 1
    return n


def _clean_chunk(c: dict) -> dict:
    """Chunk serializable: fuera el embedding (pesado, innecesario); el resto se conserva
    ÍNTEGRO (todos los campos que generate_answer lee + id/page para el audit)."""
    return {k: v for k, v in c.items() if k != "embedding"}


# Provenance aceptada por backend (s61 §4): el manifest no puede mentir sobre qué corrió.
# "llm-padded" = comportamiento legítimo del LLM (devuelve <top_k y se rellena) — aceptado
# para el backend llm (statu quo del baseline s58) y REPORTADO; "short-circuit" (pool≤k,
# ningún backend corre) aceptado en ambos. Fail-opens reales ya abortan vía strict=True.
_ACCEPTED_PROVENANCE = {
    "llm": {"llm", "llm-padded", "short-circuit"},
    "voyage": {"voyage", "short-circuit"},
}


def _assert_rerank_provenance(qid: str, top5: list[dict]) -> None:
    expected = _ACCEPTED_PROVENANCE[RERANKER_BACKEND]
    used = {c.get("rerank_backend_used") for c in top5}
    assert used <= expected, (
        f"{qid}: provenance del rerank {used} fuera de lo esperado para "
        f"RERANKER_BACKEND={RERANKER_BACKEND} ({expected}) — freeze abortado"
    )
    if "llm-padded" in used:
        print(f"  {qid}: AVISO llm-padded (el LLM devolvió <top_k; relleno con orden de entrada)")


# ---------------------------------------------------------------- fase 1: freeze
def _only(args) -> set[str]:
    return {q.strip() for q in (args.qids or "").split(",") if q.strip()}


def _golds_del_run() -> list[dict]:
    """La puerta del run: dev (embargo DEC-023) salvo la corrida ÚNICA de
    confirmación held-out (cláusula R / DEC-037c: INCLUDE_HELDOUT=1 bajo
    freeze-contract completo — una vez por lever SHIPPED, sin iterar después)."""
    if os.environ.get("INCLUDE_HELDOUT") == "1":
        print("*** CORRIDA HELD-OUT (cláusula R, DEC-037c) — ÚNICA, no iterable ***")
        return gold_store.heldout()
    return gold_store.dev()


def phase_freeze(args) -> None:
    assert CHUNKS_IS_V2, f"CHUNKS_TABLE debe ser chunks_v2, es {CHUNKS_TABLE}"
    data = _load(F_CONTEXTS)
    golds = _golds_del_run()
    if _only(args):
        golds = [g for g in golds if g["qid"] in _only(args)]
    print(f"freeze | dev={len(golds)} | retrieve={RETRIEVAL_TOP_K} rerank={RERANK_TOP_K} "
          f"| ya congelados={len(data)}")
    fingerprint_start = corpus_fingerprint()
    for g in sorted(golds, key=lambda x: x["qid"]):
        qid = g["qid"]
        if qid in data:
            continue
        q = g["question"]
        pool = retrieve_chunks(q, top_k=RETRIEVAL_TOP_K)
        # sin target_models = paridad harness; dispatcher respeta RERANKER_BACKEND (s61).
        # strict=True: en eval un fail-open del backend = dato corrupto, no disponibilidad.
        top5 = rerank(q, pool, top_k=RERANK_TOP_K, strict=True)
        _assert_rerank_provenance(qid, top5)
        n_hyd = hydrate_context(top5)
        data[qid] = {
            "question": q,
            "conducta_esperada": g.get("conducta_esperada"),
            "frozen_at": _now(),
            "n_context_hydrated": n_hyd,
            "top5": [_clean_chunk(c) for c in top5],
            "pool50_light": [{"id": c.get("id"), "source_file": c.get("source_file"),
                              "page_number": c.get("page_number"),
                              "similarity": c.get("similarity")} for c in pool],
        }
        _save(F_CONTEXTS, data)
        print(f"  {qid}: top5={[ (c.get('source_file') or '?')[:40] for c in top5 ]} (+ctx {n_hyd})")
    meta = _load(F_MANIFEST)
    meta["freeze"] = {
        "at": _now(), "git": _git_commit(), "n_golds": len(data),
        "corpus_fingerprint": fingerprint_start,
        "retrieval": {"retrieve_k": RETRIEVAL_TOP_K, "rerank_k": RERANK_TOP_K,
                      # Backend ACTIVO + SHA de la función DESPACHADA (s61 F5: el manifest
                      # estampaba "llm" hardcoded — mentiría en un freeze voyage).
                      "reranker": RERANKER_BACKEND,
                      "rerank_model": (VOYAGE_RERANK_MODEL if RERANKER_BACKEND == "voyage"
                                       else RERANK_MODEL),
                      "rerank_fn_sha": _sha(
                          inspect.getsource(_rr_mod.rerank_chunks_voyage)
                          + inspect.getsource(_rr_mod._voyage_doc)
                          if RERANKER_BACKEND == "voyage"
                          else inspect.getsource(_rr_mod.rerank_chunks)
                      ),
                      "hyde_enabled": os.environ.get("HYDE_ENABLED"),
                      "target_models": None},
        "embeddings": {"model": "voyage-4-large", "dims": 1024, "input_type": "query",
                       "embed_cache_path": os.getenv("EMBED_CACHE_PATH")},
        # La VARIABLE DE TRATAMIENTO del ciclo A s63 (r2 Z5/R2d): sin esto, un
        # registry silenciosamente vacío (fail-open) dejaría "evaluar tratamiento"
        # siendo baseline. El veredicto del par exige fingerprints distintos y
        # coherentes entre brazos (control=disabled, tratamiento=poblado).
        "series_registry": {
            "enabled": _series_mod.series_enabled(),
            "fingerprint": _series_mod.registry_fingerprint(),
            "stats": dict(zip(("n_series", "n_members", "n_shared"),
                              _series_mod.registry_stats())),
            "series_registry_sha": _sha(inspect.getsource(_series_mod)),
            "filter_fn_sha": _sha(inspect.getsource(_ret_mod._filter_to_query_models)),
            "diversify_fn_sha": _sha(inspect.getsource(_ret_mod._diversify_by_source_file)),
        },
    }
    _save(F_MANIFEST, meta)
    print(f"freeze OK → {F_CONTEXTS.name} ({len(data)} golds) | manifest estampado "
          f"| series={meta['freeze']['series_registry']['fingerprint']}")


# ------------------------------------------------------------- fase 2: generate
def _gen_one(task):
    qid, run_idx, question, top5 = task
    try:
        res = generate_answer(question, top5)
        return (qid, run_idx, {
            "answer": res.get("answer"),
            "stop_reason": res.get("stop_reason"),
            "output_tokens": res.get("output_tokens"),
            "at": _now(),
        })
    except Exception as e:
        return (qid, run_idx, {"error": f"{type(e).__name__}: {e}"[:300], "at": _now()})


def _assert_instrument_equivalence(section: str, ours: dict) -> None:
    """R4 (PREREG cláusula R): en un run que NO es el baseline, los SHAs/config del
    instrumento (generador/juez) deben ser IDÉNTICOS a los del manifest s58 — la
    equivalencia se prueba y la corrida ABORTA si difiere (un lever de retrieval no
    puede colar cambios de generación/scoring)."""
    if RUN_ID == "s58":
        return
    base = _load(F_BASELINE_MANIFEST)
    ref = (base.get(section) or {}).get(section if section != "generate" else "generator")
    if section == "judge":
        ref = (base.get("judge") or {}).get("judge")
    assert ref, f"R4: manifest baseline sin sección {section} — no puedo probar equivalencia"
    diffs = {k: (ref.get(k), ours.get(k)) for k in ours if ref.get(k) != ours.get(k)}
    assert not diffs, f"R4: instrumento '{section}' difiere del baseline s58: {diffs}"


def phase_generate(args) -> None:
    assert os.getenv("GENERATOR_INCLUDE_CONTEXT") != "1", \
        "GENERATOR_INCLUDE_CONTEXT=1 detectado — el baseline es brazo A (blurb OFF)"
    _assert_instrument_equivalence("generate", {
        "model": LLM_MODEL, "temperature": 0, "max_tokens": LLM_MAX_TOKENS,
        "include_context": 0,
        "system_prompt_sha": _sha(SYSTEM_PROMPT),   # la CONSTANTE base — prueba que no se tocó
        "relevance_threshold": RELEVANCE_THRESHOLD,
        # generate_fn_sha EXIMIDO del R4 (s69): el flag GENERATOR_PROMPT_VARIANT refactorizó
        # generate_answer (system=_assemble_system()) → su source-sha cambió legítimamente. El
        # aislamiento del refactor lo prueba el TEST DE PARIDAD (base ≡ SYSTEM_PROMPT byte-a-byte,
        # $0 determinista — tests/test_s69_prompt_variant.py), no este sha. El manifest estampa
        # el assembled_system_sha real (lo que de verdad corrió) + el generate_fn_sha nuevo.
    })
    contexts = _load(F_CONTEXTS)
    assert contexts, "no hay frozen_contexts — corre la fase freeze primero"
    data = _load(F_GENERATIONS)
    tasks = []
    for qid, ctx in sorted(contexts.items()):
        if _only(args) and qid not in _only(args):
            continue
        runs = data.get(qid, {})
        for k in range(args.k):
            rk = str(k)
            if rk in runs and runs[rk].get("answer") and not runs[rk].get("error"):
                continue
            tasks.append((qid, rk, ctx["question"], ctx["top5"]))
    print(f"generate | K={args.k} | pendientes={len(tasks)} | modelo={LLM_MODEL} temp=0 "
          f"max_tokens={LLM_MAX_TOKENS} blurb=OFF")
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_gen_one, t) for t in tasks]
        for fut in as_completed(futs):
            qid, rk, row = fut.result()
            data.setdefault(qid, {})[rk] = row
            done += 1
            if done % 10 == 0:
                _save(F_GENERATIONS, data)
                print(f"  ...{done}/{len(tasks)}")
    _save(F_GENERATIONS, data)
    errs = [(q, r) for q, runs in data.items() for r, row in runs.items() if row.get("error")]
    meta = _load(F_MANIFEST)
    meta["generate"] = {
        "at": _now(), "git": _git_commit(), "k": args.k,
        "generator": {"model": LLM_MODEL, "temperature": 0, "max_tokens": LLM_MAX_TOKENS,
                      "include_context": 0, "available_models": None,
                      # s69: variant + el sha del prompt REALMENTE ensamblado (honesto sobre
                      # qué corrió); system_prompt_sha = la constante base (sin tocar).
                      "prompt_variant": os.getenv("GENERATOR_PROMPT_VARIANT", "base"),
                      "system_prompt_sha": _sha(SYSTEM_PROMPT),
                      "assembled_system_sha": _sha(_gen_mod._assemble_system()),
                      "generate_fn_sha": _sha(inspect.getsource(_gen_mod.generate_answer)),
                      "relevance_threshold": RELEVANCE_THRESHOLD},
        "n_errors": len(errs),
    }
    _save(F_MANIFEST, meta)
    print(f"generate OK → {F_GENERATIONS.name} | errores={len(errs)} {errs[:5]}")


# ---------------------------------------------------------------- fase 3: judge
def _judge_one(task):
    qid, rk, question, expected, gold_answer, bot_answer = task
    from openai import OpenAI
    oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    try:
        resp = oai.chat.completions.create(
            model=JUDGE_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": TBG._JUDGE_SYS},
                {"role": "user", "content": TBG._JUDGE_USER.format(
                    question=question, expected=expected,
                    gold=(gold_answer or "")[:JUDGE_TRUNCATION],
                    bot=(bot_answer or "")[:JUDGE_TRUNCATION])},
            ],
        )
        out = json.loads(resp.choices[0].message.content.strip())
        out["judge_model_real"] = resp.model
        out["at"] = _now()
        return (qid, rk, out)
    except Exception as e:
        return (qid, rk, {"veredicto": "?", "error": f"{type(e).__name__}: {e}"[:300],
                          "at": _now()})


def phase_judge(args) -> None:
    _assert_instrument_equivalence("judge", {
        "model_alias": JUDGE_MODEL, "response_format": "json_object",
        "truncation_chars": JUDGE_TRUNCATION,
        "sys_sha": _sha(TBG._JUDGE_SYS), "user_sha": _sha(TBG._JUDGE_USER),
    })
    contexts = _load(F_CONTEXTS)
    gens = _load(F_GENERATIONS)
    assert gens, "no hay generations — corre generate primero"
    golds = {g["qid"]: g for g in _golds_del_run()}
    data = _load(F_JUDGMENTS)
    tasks = []
    for qid, runs in sorted(gens.items()):
        g = golds.get(qid)
        if not g:
            continue
        if _only(args) and qid not in _only(args):
            continue
        for rk, row in runs.items():
            if row.get("error") or not row.get("answer"):
                continue
            done_row = data.get(qid, {}).get(rk)
            if done_row and done_row.get("veredicto") not in (None, "?"):
                continue
            tasks.append((qid, rk, contexts[qid]["question"],
                          g.get("conducta_esperada", "answer"),
                          g.get("gold_answer", ""), row["answer"]))
    print(f"judge | pendientes={len(tasks)} | juez={JUDGE_MODEL}+json_object "
          f"trunc={JUDGE_TRUNCATION}")
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_judge_one, t) for t in tasks]
        for fut in as_completed(futs):
            qid, rk, row = fut.result()
            data.setdefault(qid, {})[rk] = row
            done += 1
            if done % 15 == 0:
                _save(F_JUDGMENTS, data)
                print(f"  ...{done}/{len(tasks)}")
    _save(F_JUDGMENTS, data)
    models_real = Counter(r.get("judge_model_real") for runs in data.values()
                          for r in runs.values() if r.get("judge_model_real"))
    n_err = sum(1 for runs in data.values() for r in runs.values() if r.get("veredicto") == "?")
    meta = _load(F_MANIFEST)
    meta["judge"] = {
        "at": _now(), "git": _git_commit(),
        "judge": {"model_alias": JUDGE_MODEL, "models_real": dict(models_real),
                  "response_format": "json_object", "truncation_chars": JUDGE_TRUNCATION,
                  "sys_sha": _sha(TBG._JUDGE_SYS), "user_sha": _sha(TBG._JUDGE_USER),
                  "parse_policy": "json.loads directo (response_format); error → veredicto '?' "
                                  "(re-lanzable; '?' se excluye del modal, ver report)"},
        "n_judge_errors": n_err,
    }
    _save(F_MANIFEST, meta)
    print(f"judge OK → {F_JUDGMENTS.name} | '?'={n_err} | model_real={dict(models_real)}")


# --------------------------------------------------------------- fase 4: report
def aggregate(verdicts: list[str]) -> dict:
    """Partición v3 pre-registrada (sin solape, fiel a la letra del PREREG):
    PASS-control := modal PASS · residual := 0 PASS entre los válidos · K-INESTABLE := resto.
    '?' (error de juez) se excluye del modal; <3 válidos → JUDGE-ERROR (no clasificable)."""
    valid = [v for v in verdicts if v in ORDER]
    if len(valid) < 3:
        return {"veredicto": "?", "bucket": "JUDGE-ERROR", "flag_review": True,
                "n_valid": len(valid), "votes": dict(Counter(verdicts))}
    c = Counter(valid)
    top_n = max(c.values())
    modal_cands = [v for v, n in c.items() if n == top_n]
    modal = min(modal_cands, key=lambda v: ORDER[v])  # empate → el PEOR (solo cosmético)
    n_pass = c.get("PASS", 0)
    if modal == "PASS":
        bucket = "PASS-control"
    elif n_pass == 0:
        bucket = "residual"
    else:
        bucket = "K-INESTABLE"
    return {"veredicto": modal, "bucket": bucket,
            "unanime": len(set(valid)) == 1 and len(valid) == len(verdicts),
            "flag_review": len(set(valid)) > 1 or len(valid) < len(verdicts),
            "n_valid": len(valid), "votes": dict(c)}


def sufficiency_for(g: dict, top5: list[dict]) -> dict:
    """Audit determinista per-hecho sobre el top-5 CONGELADO (D3 v3)."""
    from audit_retrieval_funnel import fact_probe, present_in, doc_tokens, \
        fetch_manual_chunks, source_matches_target

    filtered = [c for c in top5 if (c.get("similarity") or 0) >= RELEVANCE_THRESHOLD]
    top5_sources = sorted({c.get("source_file") for c in top5 if c.get("source_file")})
    facts_out, fuertes = [], []
    for f in g.get("atomic_facts") or []:
        if f.get("tipo") != "core" or f.get("estado") != "presente":
            continue
        kind, probe, strength = fact_probe(f.get("valor", ""), f.get("texto", ""))
        row = {"valor": f.get("valor"),
               "probe": sorted(probe) if kind == "anchors" else f"~{probe}",
               "strength": strength,
               "in_top5": present_in(top5, kind, probe),
               "in_filtered": present_in(filtered, kind, probe)}
        facts_out.append(row)
        if strength == "fuerte":
            fuertes.append((row, kind, probe))

    if not fuertes:
        bucket = "INDETERMINADO-solo-debiles"
        sub = None
    else:
        missing = [(r, k, p) for r, k, p in fuertes if not r["in_top5"]]
        only_filtered = [r for r, _, _ in fuertes if r["in_top5"] and not r["in_filtered"]]
        if not missing:
            bucket = "GENERACION-filtro" if only_filtered else "GENERACION"
            sub = None
        elif len(missing) == len(fuertes):
            bucket = "SUB-RETRIEVAL"
            sub = _locate_missing(g, missing, top5_sources)
        else:
            bucket = "MIXTO"
            sub = _locate_missing(g, missing, top5_sources)
    return {"bucket": bucket, "sub": sub, "n_core_fuerte": len(fuertes),
            "n_core_presente": len(facts_out), "top5_sources": top5_sources,
            "facts": facts_out}


def _locate_missing(g: dict, missing: list, top5_sources: list[str]) -> dict:
    """Sub-etiqueta per-hecho (v3): ¿el hecho ausente vive en un doc que el top-5 NO trajo
    (multi-doc-miss) o en un doc presente pero otra página/sección (within-doc-miss)?
    El ESTRATO del gold se anota aparte, NO clasifica (taxonomía congelada DEC-033)."""
    from audit_retrieval_funnel import doc_tokens, fetch_manual_chunks, source_matches_target, _chunk_has
    prov = g.get("_provenance") or {}
    cits = " ".join(c.get("manual", "") for c in (g.get("citations") or []))
    tokens = doc_tokens(prov.get("fuente", ""), cits, " ".join(g.get("pdfs_used") or []))
    manual_chunks = fetch_manual_chunks(tokens) if tokens else []
    per_fact = []
    for row, kind, probe in missing:
        fact_docs = sorted({c.get("source_file") for c in manual_chunks
                            if _chunk_has(c.get("content") or "", kind, probe)})
        if not fact_docs:
            label = "fact-not-located"   # ni en los docs objetivo → sospecha corpus-gap
        elif any(s in top5_sources for s in fact_docs):
            label = "within-doc-miss"
        else:
            label = "multi-doc-miss"
        per_fact.append({"valor": row["valor"], "fact_docs": fact_docs, "label": label})
    labels = Counter(p["label"] for p in per_fact)
    return {"per_fact": per_fact, "labels": dict(labels),
            "estrato_anotado": g.get("estrato") or []}


def phase_report(args) -> None:
    contexts = _load(F_CONTEXTS)
    judgments = _load(F_JUDGMENTS)
    gens = _load(F_GENERATIONS)
    assert contexts and judgments, "faltan artefactos (freeze/judge)"
    golds = {g["qid"]: g for g in gold_store.dev()}

    rows, buckets = [], Counter()
    stop_counter = Counter()
    for qid in sorted(contexts):
        g = golds[qid]
        runs_j = judgments.get(qid, {})
        runs_g = gens.get(qid, {})
        verdicts = [runs_j[k].get("veredicto", "?") for k in sorted(runs_j)]
        agg = aggregate(verdicts)
        stops = [runs_g[k].get("stop_reason") for k in sorted(runs_g) if not runs_g[k].get("error")]
        stop_counter.update(stops)
        conducta_modal = Counter(
            runs_j[k].get("conducta_bot") for k in sorted(runs_j)
            if runs_j[k].get("conducta_bot")).most_common(1)
        row = {
            "qid": qid,
            "conducta_esperada": g.get("conducta_esperada"),
            "conducta_bot_modal": conducta_modal[0][0] if conducta_modal else None,
            "estrato": g.get("estrato") or [],
            **agg,
            "stop_reasons": dict(Counter(stops)),
            "diagnosticos": [runs_j[k].get("diagnostico") for k in sorted(runs_j)][:5],
        }
        # Audit de sufficiency: SOLO residual accionable de conducta answer (D3 v3).
        if agg["bucket"] == "residual":
            if g.get("conducta_esperada") in ("answer", "answer-con-conflicto"):
                suff = sufficiency_for(g, contexts[qid]["top5"])
                row["sufficiency"] = suff
                row["atribucion"] = suff["bucket"]
            else:
                row["atribucion"] = "CUALITATIVA (conducta no-answer)"
        buckets[row.get("atribucion") or agg["bucket"]] += 1
        rows.append(row)

    # PASS-control fijado (membresía contrato PREREG + sub-split estabilidad declarado).
    control = [r["qid"] for r in rows if r["bucket"] == "PASS-control"]
    control_unanime = [r["qid"] for r in rows if r["bucket"] == "PASS-control" and r["unanime"]]
    solo_debiles = [r["qid"] for r in rows
                    if (r.get("sufficiency") or {}).get("bucket") == "INDETERMINADO-solo-debiles"]

    meta = _load(F_MANIFEST)
    meta["report"] = {
        "at": _now(), "git": _git_commit(), "k": args.k,
        "corpus_fingerprint_at_report": corpus_fingerprint(),
        "reglas_preregistradas": {
            "particion": "PASS-control := modal PASS (letra PREREG; sub-split unanime/no "
                         "declarado — la exclusión de no-unánimes del Δ primario en s59 es "
                         "estadística, no de membresía) · residual := 0 PASS entre válidos · "
                         "K-INESTABLE := resto (modal no-PASS con algún PASS)",
            "empate_modal": "peor de los empatados — SOLO presentación, no buckets",
            "judge_error": "'?' fuera del modal; <3 válidos → JUDGE-ERROR",
            "sufficiency": "determinista sobre top-5 CONGELADO; INDETERMINADO-solo-debiles "
                           "pre-registrado (verdad-vacua cazada por el dúo); sub-etiqueta "
                           "multi-doc per-hecho, estrato solo anota (DEC-033)",
            "seeds": "KNOB-MUERTO declarado (DEC-015: gpt-5.5 rechaza temp/seed inerte; "
                     "Sonnet temp=0 no-determinista) — reproducibilidad = contexts congelados "
                     "+ K-mayoría + este manifest",
        },
    }
    _save(F_MANIFEST, meta)

    report = {
        "meta": {"generated_at": _now(), "git": _git_commit(), "k": args.k,
                 "n_golds": len(rows), "manifest": F_MANIFEST.name},
        "resumen": {
            "particion": dict(Counter(r["bucket"] for r in rows)),
            "pass_control_FIJADO": control,
            "pass_control_unanime": control_unanime,
            "atribucion_residual": {k: v for k, v in buckets.items()
                                    if k not in ("PASS-control", "K-INESTABLE")},
            "k_inestables": [r["qid"] for r in rows if r["bucket"] == "K-INESTABLE"],
            "indeterminados_solo_debiles": solo_debiles,
            "stop_reasons_global": dict(stop_counter),
            "max_tokens_hits": stop_counter.get("max_tokens", 0),
        },
        "golds": rows,
    }
    F_REPORT.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False,
                                       width=110), encoding="utf-8")

    print("=" * 72)
    print(f"PARTICIÓN: {report['resumen']['particion']}")
    print(f"PASS-control FIJADO ({len(control)}): {control}")
    print(f"  (unánimes 5/5: {len(control_unanime)}: {control_unanime})")
    print(f"K-INESTABLES: {report['resumen']['k_inestables']}")
    print(f"ATRIBUCIÓN del residual: {report['resumen']['atribucion_residual']}")
    print(f"stop_reasons: {dict(stop_counter)}  (max_tokens={stop_counter.get('max_tokens', 0)})")
    print(f"\n→ {F_REPORT.name} + {F_MANIFEST.name}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["freeze", "generate", "judge", "report", "all"])
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--qids", default="", help="csv de qids (smoke dirigido; report ignora)")
    args = ap.parse_args()
    phases = {"freeze": phase_freeze, "generate": phase_generate,
              "judge": phase_judge, "report": phase_report}
    if args.phase == "all":
        for name in ("freeze", "generate", "judge", "report"):
            print(f"\n===== FASE {name} =====")
            phases[name](args)
    else:
        phases[args.phase](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
