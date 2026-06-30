#!/usr/bin/env python3
"""retrieval_miss_judge.py (s85·B0) — instrumento REPRODUCIBLE de retrieval-miss con
JUEZ SEMÁNTICO (GPT-5.5 K=5), corregido por el dúo (brief evals/s85_b0_instrument_design_brief.md v2).

retrieval-miss = hecho CORE servible-en-corpus pero NO en el pool-50 (pre-rerank). Sustituye el
predicado LÉXICO `present_fact` del funnel (DEC-070: infla retrieval ~45%) por un juez hecho-vs-chunk.

CLAVE (fixes del dúo):
- juez NUEVO (no reuso): prompt+rúbrica versionados (sha en manifest); solo se reusa la plomería gpt-5.5.
- SIN pre-filtro con pérdida: se juzga TODO el pool50 (within-doc rompe el coseno top-k; léxico pierde es-en).
  El manual (para distinguir RETRIEVAL vs CORPUS-GAP, raro) usa pre-filtro híbrido léxico∪— recall-safe.
- métrica por-PRIMARIO (canon) Y por-TARGET (laxo, expone corroborador-tapa-primario).
- universo = 134 hechos CORE-presentes (incl. 22 no-medibles); held-out EMBARGADO.
- umbral ESTRICTO ≥4/5 (FIRME) + banda ≥3/5; rúbrica CONGELADA (sha) antes de ver el count.

Modos:
  python scripts/retrieval_miss_judge.py smoke --qids cat005,hp002      # subset, valida juez+coste
  python scripts/retrieval_miss_judge.py full [--reps 3]                # 39 dev, baseline + jitter
  python scripts/retrieval_miss_judge.py trampa                         # golds-trampa (FP del juez)
Salida: evals/s85_retrieval_miss_<mode>.yaml + manifest.
"""
from __future__ import annotations
import os
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["HYDE_ENABLED"] = "false"
import sys, json, time, hashlib, argparse, datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

from dotenv import load_dotenv
ROOT = Path(os.getcwd()).resolve()
assert (ROOT / "src").is_dir() and (ROOT / "evals").is_dir(), f"cwd no es la raíz: {ROOT}"
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"; os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

import yaml
from openai import OpenAI
from src.rag.retriever import retrieve_chunks, extract_product_models
from src.rag.reranker import rerank_chunks
from scripts.audit_retrieval_funnel import (
    target_servable, fetch_manual_chunks, source_matches_target, doc_tokens, classify,
)
from scripts.audit_locator import fact_match_score

GOLD = ROOT / "evals" / "gold_answers_v1.yaml"
JUDGE_MODEL = "gpt-5.5"
K = 5                 # votos por chunk-batch (Alberto)
THRESH_FIRM = 4       # ≥4/5 = soporte FIRME (estricto, anti sobre-acreditación)
THRESH_BAND = 3       # ≥3/5 = banda (borderline)
BATCH = 8             # chunks por prompt de juez (recall del juez > coste; Alberto)
POOL_K = 50
RERANK_K = 5
CONTENT_CHARS = 8000  # contenido COMPLETO del chunk (max ~7400) — truncar a 1100 perdía valores
                      # más allá del char 1100 = FN del juez (cat012 '24 h' en pos 6611). s85 fix.

# ───────────────────────── JUEZ (prompt NUEVO, CONGELADO — sha en manifest) ─────────────────────────
JUDGE_SYS = (
    "Eres un evaluador EXPERTO en manuales técnicos de protección contra incendios (PCI). "
    "Decides, con rigor literal, si un DATO concreto está soportado por fragmentos de manual. "
    "Idiomas mezclados ES/EN y OCR imperfecto son normales: juzga el SIGNIFICADO, no la forma exacta. "
    "Eres ESTRICTO: marcar un fragmento como soporte cuando NO contiene el dato es el peor error."
)
JUDGE_USER = (
    "DATO a verificar: «{valor}»\n"
    "CONTEXTO del dato (de qué trata): {texto}\n\n"
    "FRAGMENTOS (cada uno con su ID):\n{chunks}\n\n"
    "Devuelve EXCLUSIVAMENTE los IDs de los fragmentos que AFIRMAN o IMPLICAN DIRECTAMENTE el DATO «{valor}». "
    "Incluye un ID SÓLO si el VALOR CONCRETO está soportado por ese fragmento (un número/código/hecho que "
    "coincide semánticamente, admitiendo traducción ES↔EN y OCR). NO lo incluyas por: mencionar el producto "
    "sin el dato, tratar el mismo tema sin el valor, o un valor distinto. Ante la duda, EXCLUYE.\n"
    'Responde JSON: {{"supported_ids": ["id1", ...]}} (lista vacía si ninguno).'
)
_sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def _judge_call(valor: str, texto: str, batch: list[dict]) -> tuple[set[str], str]:
    """1 llamada GPT-5.5 → set de IDs soportados (de este batch) + modelo real.
    Retry con backoff: un fallo de API NO debe contar como 'sin soporte' (= falso miss en un árbitro)."""
    oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    chunk_txt = "\n\n".join(
        f"[ID: {c['id']}]\n{(c.get('content') or '')[:CONTENT_CHARS]}" for c in batch
    )
    valid = {c["id"] for c in batch}
    last = "ERR:?"
    for attempt in range(4):
        try:
            resp = oai.chat.completions.create(
                model=JUDGE_MODEL, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": JUDGE_SYS},
                          {"role": "user", "content": JUDGE_USER.format(
                              valor=valor, texto=(texto or "")[:400], chunks=chunk_txt)}],
            )
            out = json.loads(resp.choices[0].message.content.strip())
            ids = {str(i) for i in (out.get("supported_ids") or [])}
            return (ids & valid), resp.model
        except Exception as e:
            last = f"ERR:{type(e).__name__}"
            time.sleep(2 ** attempt)  # 1,2,4,8s
    return None, last  # None = fallo real tras retries → marca el voto como INVÁLIDO (no 'sin soporte')


def judge_fact(valor: str, texto: str, chunks: list[dict], workers: int = 6) -> dict:
    """Juzga el hecho contra TODOS los chunks (sin pre-filtro), K=5 por batch.
    Devuelve {id: votos(0..K)} agregando los K runs. Soporte FIRME = votos≥4, banda = votos≥3."""
    if not chunks:
        return {}
    batches = [chunks[i:i + BATCH] for i in range(0, len(chunks), BATCH)]
    tasks = [(b,) for b in batches for _ in range(K)]  # K runs por batch
    votes: Counter = Counter()
    models = set()
    n_fail = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_judge_call, valor, texto, b) for (b,) in tasks]
        for f in futs:
            ids, m = f.result()
            models.add(m)
            if ids is None:      # voto inválido (fallo de API tras retries) → NO cuenta como 'sin soporte'
                n_fail += 1
                continue
            for i in ids:
                votes[i] += 1
    return {"votes": dict(votes), "models": sorted(models), "n_fail": n_fail}


def supported_ids(vote_res: dict, thresh: int) -> set[str]:
    return {i for i, v in (vote_res.get("votes") or {}).items() if v >= thresh}


# ───────────────────────── núcleo: medir un gold ─────────────────────────
def core_facts(gold: dict) -> list[dict]:
    return [f for f in (gold.get("atomic_facts") or [])
            if f.get("tipo") == "core" and f.get("estado") == "presente"]


def measure_gold(gold: dict, workers: int = 6) -> dict:
    q = gold["question"]
    models = extract_product_models(q)
    pool = retrieve_chunks(q, top_k=POOL_K)
    top5 = rerank_chunks(q, pool, top_k=RERANK_K)
    pool_ids = {c.get("id") for c in pool}
    top5_ids = {c.get("id") for c in top5}
    by_id = {c.get("id"): c for c in pool}

    servable, srv = target_servable(gold)
    targets = srv["target_tokens"]
    primary = doc_tokens((gold.get("_provenance") or {}).get("fuente", ""))
    manual = fetch_manual_chunks(targets) if targets else []
    man_by_id = {c.get("id"): c for c in manual}

    def src(cid):  # source_file de un chunk (de pool o manual)
        c = by_id.get(cid) or man_by_id.get(cid)
        return (c or {}).get("source_file") or ""

    rest_pool = [c for c in pool if c.get("id") not in top5_ids]

    def tie_ok(cid, tie_tokens):
        return (not tie_tokens) or source_matches_target(src(cid), tie_tokens)

    facts_out = []
    for f in core_facts(gold):
        valor = f.get("valor", ""); texto = (f.get("texto") or "").strip()
        # ETAPA 1: juzgar el top5 (barato). Si un chunk PRIMARIO del top5 lo soporta → SINTESIS
        # en ambas tie (primary ⊆ target) → short-circuit del caso común.
        v_top = judge_fact(valor, texto, top5, workers=workers)
        sup_top = supported_ids(v_top, THRESH_FIRM)
        sup_top_band = supported_ids(v_top, THRESH_BAND)
        all_votes = dict(v_top.get("votes", {}))
        n_fail = v_top.get("n_fail", 0)
        sup_pool = set(sup_top)              # soporte acumulado en TODO el pool (empieza con top5)
        sup_pool_band = set(sup_top_band)
        primary_in_top5 = any(tie_ok(cid, primary) for cid in sup_top)
        # ETAPA 2 (solo si NO resuelto): juzgar el resto del pool (within-doc, sin pre-filtro)
        if not primary_in_top5 and rest_pool:
            v_rest = judge_fact(valor, texto, rest_pool, workers=workers)
            sup_pool |= supported_ids(v_rest, THRESH_FIRM)
            sup_pool_band |= supported_ids(v_rest, THRESH_BAND)
            all_votes.update(v_rest.get("votes", {}))
            n_fail += v_rest.get("n_fail", 0)
        # ETAPA 3 (TIE-AWARE): correr si falta soporte en pool para ALGUNA tie → necesito saber si
        # el manual objetivo lo tiene (RETRIEVAL) o no (CORPUS-GAP). Bug previo: gateaba con
        # in_pool_any (tie-agnóstico) → un soporte wrong-tie en pool saltaba el manual = falso CORPUS-GAP.
        sup_man = set()
        in_pool_pri = any((cid in pool_ids) and tie_ok(cid, primary) for cid in sup_pool)
        in_pool_tgt = any((cid in pool_ids) and tie_ok(cid, targets) for cid in sup_pool)
        if (not in_pool_pri or not in_pool_tgt) and manual:
            scored = sorted(((fact_match_score(valor, texto, c.get("content") or "") or 0.0, c)
                             for c in manual), key=lambda x: x[0], reverse=True)
            v_man = judge_fact(valor, texto, [c for _, c in scored[:40]], workers=workers)
            sup_man = supported_ids(v_man, THRESH_FIRM)
            n_fail += v_man.get("n_fail", 0)
            all_votes.update(v_man.get("votes", {}))

        def derive(tie_tokens):
            in_top5 = any((cid in top5_ids) and tie_ok(cid, tie_tokens) for cid in sup_top)
            in_pool = any((cid in pool_ids) and tie_ok(cid, tie_tokens) for cid in sup_pool)
            in_man = any((cid in man_by_id) and tie_ok(cid, tie_tokens) for cid in (sup_pool | sup_man))
            return classify(in_top5, in_pool, in_pool or in_man), in_top5, in_pool

        b_tgt, t5_t, pl_t = derive(targets)
        b_pri, t5_p, pl_p = derive(primary)
        facts_out.append({
            "valor": valor,
            "bucket_target": b_tgt, "bucket_primary": b_pri,
            "in_pool_target": pl_t, "in_top5_target": t5_t,
            "in_pool_primary": pl_p, "in_top5_primary": t5_p,
            "n_support_firm": len(sup_pool), "n_support_band": len(sup_pool_band),
            "borderline": bool(sup_pool_band - sup_pool), "n_fail": n_fail,
            "votes": all_votes,
        })
    return {
        "qid": gold["qid"], "n_models": len(models), "servable": servable,
        "targets": targets, "primary": primary,
        "pool_n": len(pool), "manual_n": len(manual),
        "facts": facts_out,
    }


# ───────────────────────── agregación + manifest ─────────────────────────
def aggregate(results: list[dict]) -> dict:
    agg = {"by_primary": Counter(), "by_target": Counter()}
    n_fail_total = facts_with_fail = 0
    for r in results:
        for f in r["facts"]:
            agg["by_primary"][f["bucket_primary"]] += 1
            agg["by_target"][f["bucket_target"]] += 1
            nf = f.get("n_fail", 0)
            n_fail_total += nf
            facts_with_fail += int(nf > 0)
    return {"by_primary": dict(agg["by_primary"]), "by_target": dict(agg["by_target"]),
            "retrieval_miss_primary": agg["by_primary"].get("RETRIEVAL", 0),
            "retrieval_miss_target": agg["by_target"].get("RETRIEVAL", 0),
            "n_fail_total": n_fail_total, "facts_with_fail": facts_with_fail}


def manifest(extra: dict) -> dict:
    import subprocess
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    return {"instrument": "retrieval_miss_judge", "judge_model": JUDGE_MODEL,
            "K": K, "thresh_firm": THRESH_FIRM, "thresh_band": THRESH_BAND,
            "batch": BATCH, "pool_k": POOL_K, "content_chars": CONTENT_CHARS,
            "judge_sys_sha": _sha(JUDGE_SYS), "judge_user_sha": _sha(JUDGE_USER),
            "git_commit": commit, "chunks_table": os.environ["CHUNKS_TABLE"],
            "hyde": os.environ["HYDE_ENABLED"], **extra}


def load_dev() -> list[dict]:
    from scripts.gold_store import exclude_heldout
    return exclude_heldout(yaml.safe_load(GOLD.read_text(encoding="utf-8")))


# ───────────────────────── golds-trampa (certificación del árbitro: FP del juez) ─────────────────────────
def _perturb(valor: str) -> str:
    """Desplaza cada dígito +3 mod 10 → valor de MISMO FORMATO pero FALSO (no en el manual).
    Mide si el juez sobre-acredita un valor inexistente (el sesgo que DESINFLA retrieval-miss)."""
    return "".join(str((int(ch) + 3) % 10) if ch.isdigit() else ch for ch in valor)


def run_trampa(dev: dict, qids: list[str], workers: int) -> dict:
    """Por cada hecho CORE medible con dígitos: juzgar el VALOR PERTURBADO (falso) contra el pool
    del propio gold. El juez DEBE devolver 0 soporte. FP = soporte≥THRESH_FIRM a un valor inexistente."""
    cases, fp = [], 0
    for qid in qids:
        g = dev[qid]
        pool = retrieve_chunks(g["question"], top_k=POOL_K)
        for f in core_facts(g):
            valor = f.get("valor", ""); texto = (f.get("texto") or "").strip()
            if not any(ch.isdigit() for ch in valor):
                continue  # perturbación solo sobre valores con dígitos
            fake = _perturb(valor)
            if fake == valor:
                continue
            v = judge_fact(fake, texto, pool, workers=workers)
            sup = supported_ids(v, THRESH_FIRM)
            is_fp = len(sup) > 0
            fp += int(is_fp)
            cases.append({"qid": qid, "valor_real": valor, "valor_fake": fake,
                          "n_support_fake": len(sup), "FP": is_fp})
            print(f"  trampa {qid}: real={valor!r} fake={fake!r} → support={len(sup)} {'FP!' if is_fp else 'ok'}",
                  flush=True)
    rate = fp / len(cases) if cases else 0.0
    print(f"\nTRAMPA: {fp}/{len(cases)} FP = {rate:.1%} (umbral de aceptación: ≤10%)", flush=True)
    return {"n_cases": len(cases), "n_fp": fp, "fp_rate": round(rate, 3), "cases": cases}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["smoke", "full", "trampa"])
    ap.add_argument("--qids", default="")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    dev = {g["qid"]: g for g in load_dev()}
    if args.qids:
        qids = [q.strip() for q in args.qids.split(",") if q.strip()]
    elif args.mode == "smoke":
        qids = list(dev)[:3]
    else:
        qids = sorted(dev)
    print(f"[{args.mode}] {len(qids)} golds | K={K} thresh_firm={THRESH_FIRM} batch={BATCH} reps={args.reps}",
          flush=True)

    if args.mode == "trampa":
        tr = run_trampa(dev, qids, args.workers)
        out = ROOT / "evals" / (args.out or "s85_retrieval_miss_trampa.yaml")
        out.write_text(yaml.safe_dump({"manifest": manifest({"mode": "trampa", "qids": qids}),
                                       "trampa": tr}, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"[written] {out}")
        return

    # Resumibilidad (los runs largos mueren al cerrarse la sesión): cada gold completado se
    # persiste a <out>.partial.jsonl; al arrancar se cargan y se SALTAN los ya hechos.
    out_name = args.out or f"s85_retrieval_miss_{args.mode}.yaml"
    partial = ROOT / "evals" / (out_name + ".partial.jsonl")
    done = {}
    if partial.exists():
        skipped_bad = 0
        for line in partial.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            nf = sum(f.get("n_fail", 0) for f in rec["result"].get("facts", []))
            if nf > 0:           # gold corrupto (cuota/rate-limit) → re-correr limpio
                skipped_bad += 1
                continue
            done[(rec["rep"], rec["qid"])] = rec["result"]
        print(f"[resume] {len(done)} (rep,gold) limpios cargados, {skipped_bad} corruptos (n_fail>0) se re-corren",
              flush=True)

    reps_out = []
    for rep in range(args.reps):
        t0 = time.time()
        results = []
        for qid in qids:
            if (rep, qid) in done:
                r = done[(rep, qid)]
            else:
                r = measure_gold(dev[qid], workers=args.workers)
                with partial.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"rep": rep, "qid": qid, "result": r}, ensure_ascii=False) + "\n")
            results.append(r)
            agg_q = Counter(f["bucket_primary"] for f in r["facts"])
            nf = sum(f.get("n_fail", 0) for f in r["facts"])
            print(f"  rep{rep} {qid}: {dict(agg_q)}  (pool={r['pool_n']} manual={r['manual_n']}"
                  f"{' n_fail='+str(nf) if nf else ''})", flush=True)
        agg = aggregate(results)
        reps_out.append({"rep": rep, "agg": agg, "results": results,
                         "elapsed_s": round(time.time() - t0, 1)})
        print(f"  rep{rep} AGG primary={agg['by_primary']} | retrieval_miss(primary)={agg['retrieval_miss_primary']}"
              f" | n_fail={agg['n_fail_total']} (facts_afectados={agg['facts_with_fail']}) "
              f"{'<<< CORRUPTO si >0' if agg['n_fail_total'] else 'LIMPIO'}", flush=True)

    out = ROOT / "evals" / (args.out or f"s85_retrieval_miss_{args.mode}.yaml")
    out.write_text(yaml.safe_dump(
        {"manifest": manifest({"mode": args.mode, "qids": qids, "reps": args.reps}),
         "reps": reps_out}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"[written] {out}")


if __name__ == "__main__":
    main()
