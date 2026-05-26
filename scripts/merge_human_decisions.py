#!/usr/bin/env python3
"""T12 — Merge de decisiones humanas (Capa C calibración humana del judge v2)
al gate_relevant_chunks.json.

Aplica las decisiones del revisor humano (Alberto, sesión 26) sobre los 73
disagreements hp* del cross-validation Sonnet↔Opus. Las decisiones se extraen
de evals/gate_validation_disagreements.md (campo **Tu decisión:**) y se
mergean al gate_relevant_chunks.json original (gold de Sonnet) según:

  - Sonnet=SI, Alberto=NO → ELIMINAR chunk de relevant_chunks
  - Sonnet=NO, Alberto=SI → AÑADIR chunk a relevant_chunks
  - Sonnet==Alberto → no-op (no era disagreement o coincide con Sonnet)

Mantiene los 13 disagreements cm* sin tocar (alineado con "política cross-brand
DIFERIDA a post-SWAP" del plan §B.2).

Output: evals/gate_relevant_chunks.json reescrito con backup .bak.
        evals/human_review_audit.json con el log detallado de cambios.

Uso: python scripts/merge_human_decisions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8")

from src.ingestion.supabase_client import SupabaseHTTP

GOLD_PATH = Path("evals/gate_relevant_chunks.json")
MD_PATH = Path("evals/gate_validation_disagreements.md")
VALIDATION_RESULTS = Path("evals/gate_validation_results.json")
AUDIT_PATH = Path("evals/human_review_audit.json")


def parse_md_decisions(md: str) -> list[dict]:
    """Extrae (qid, short_id, decision) de cada disagreement del .md."""
    blocks = re.split(r"(?=^## hp\d+ · chunk)", md, flags=re.MULTILINE)[1:]
    decisions = []
    for b in blocks:
        m = re.match(r"## (hp\d+) · chunk `([0-9a-f]{8}-[0-9a-f]{3})`", b)
        if not m:
            continue
        qid, short_id = m.group(1), m.group(2)
        dec_match = re.search(r"\*\*Tu decisión:\*\* (SI|NO)", b)
        if not dec_match:
            print(f"  WARN: {qid} chunk {short_id} sin decisión humana — skip")
            continue
        decisions.append({
            "qid": qid,
            "short_id": short_id,
            "human": dec_match.group(1),
        })
    return decisions


def fetch_chunks_metadata(db: SupabaseHTTP, full_ids: list[str]) -> dict:
    """Fetch metadata para los chunks que vamos a añadir nuevos a relevant_chunks."""
    out = {}
    BATCH = 50
    for i in range(0, len(full_ids), BATCH):
        batch = full_ids[i:i+BATCH]
        rows = db.fetch_rows(
            "chunks_v2",
            select="id,source_file,section_path,page_number,content",
            filters={"id": f"in.({','.join(batch)})"},
            limit=BATCH * 2,
        )
        for r in rows:
            out[r["id"]] = r
    return out


def main(dry_run: bool = False):
    md = MD_PATH.read_text(encoding="utf-8")
    results = json.loads(VALIDATION_RESULTS.read_text(encoding="utf-8"))
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))

    # Map short_id → full validation entry
    short_to_v = {v["chunk_id"][:12]: v for v in results["validations"]}

    decisions = parse_md_decisions(md)
    print(f"Decisiones humanas parseadas: {len(decisions)}")

    # Enrich con sonnet/opus verdict y full chunk_id
    add_list = []   # chunks a añadir (Sonnet=NO, Alberto=SI)
    remove_list = []  # chunks a quitar (Sonnet=SI, Alberto=NO)
    no_op = []      # casos donde Alberto coincide con Sonnet
    errors = []

    for d in decisions:
        v = short_to_v.get(d["short_id"])
        if not v:
            errors.append({**d, "reason": "short_id no encontrado en validations"})
            continue
        sonnet = "SI" if v["sonnet_verdict"] else "NO"
        opus   = "SI" if v["opus_verdict"]   else "NO"
        human  = d["human"]
        entry = {
            **d,
            "chunk_id": v["chunk_id"],
            "sonnet": sonnet, "opus": opus,
            "source_file": v.get("source_file"),
            "section_path": v.get("section_path"),
            "page": v.get("page"),
        }
        if sonnet == "SI" and human == "NO":
            remove_list.append(entry)
        elif sonnet == "NO" and human == "SI":
            add_list.append(entry)
        else:
            no_op.append(entry)

    print(f"\nClasificación:")
    print(f"  add    (Sonnet=NO → Alberto=SI): {len(add_list)}")
    print(f"  remove (Sonnet=SI → Alberto=NO): {len(remove_list)}")
    print(f"  no-op (Alberto = Sonnet):         {len(no_op)}")
    print(f"  errores: {len(errors)}")

    # Fetch metadata para los chunks a añadir
    add_full_ids = [e["chunk_id"] for e in add_list]
    db = SupabaseHTTP()
    print(f"\nFetching metadata for {len(add_full_ids)} chunks to add...")
    chunks_meta = fetch_chunks_metadata(db, add_full_ids) if add_full_ids else {}
    print(f"  Got {len(chunks_meta)} chunks")

    # Aplicar cambios al gold por pregunta
    audit = {
        "version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_md_md5": __import__("hashlib").md5(md.encode("utf-8")).hexdigest(),
        "total_decisions_applied": len(remove_list) + len(add_list),
        "per_question": {},
    }

    questions = gold["questions"]
    for entry in remove_list:
        qid = entry["qid"]
        q = questions.get(qid)
        if not q:
            print(f"  WARN: qid {qid} not in gold")
            continue
        before = len(q["relevant_chunks"])
        q["relevant_chunks"] = [c for c in q["relevant_chunks"]
                                if c["id"] != entry["chunk_id"]]
        after = len(q["relevant_chunks"])
        if before == after:
            print(f"  WARN: {qid} remove {entry['short_id']} — chunk no estaba en relevant_chunks")
        audit["per_question"].setdefault(qid, {"removed": [], "added": []})
        audit["per_question"][qid]["removed"].append({
            "chunk_id": entry["chunk_id"],
            "short_id": entry["short_id"],
            "sonnet": entry["sonnet"], "opus": entry["opus"], "human": entry["human"],
        })

    for entry in add_list:
        qid = entry["qid"]
        q = questions.get(qid)
        if not q:
            print(f"  WARN: qid {qid} not in gold")
            continue
        meta = chunks_meta.get(entry["chunk_id"])
        if not meta:
            print(f"  WARN: {qid} add {entry['short_id']} — chunk no encontrado en chunks_v2")
            continue
        # Idempotencia
        if any(c["id"] == entry["chunk_id"] for c in q["relevant_chunks"]):
            continue
        # Citation snippet (primeros 200 chars del content, una frase relevante)
        content = meta.get("content") or ""
        citation_snippet = content[:200].replace("\n", " ").strip()
        if len(content) > 200:
            citation_snippet += "..."
        q["relevant_chunks"].append({
            "id": entry["chunk_id"],
            "source_file": meta.get("source_file"),
            "section_path": meta.get("section_path"),
            "page_number": meta.get("page_number"),
            "citation": citation_snippet,
            "_added_by": "human_review_session_26",
        })
        audit["per_question"].setdefault(qid, {"removed": [], "added": []})
        audit["per_question"][qid]["added"].append({
            "chunk_id": entry["chunk_id"],
            "short_id": entry["short_id"],
            "sonnet": entry["sonnet"], "opus": entry["opus"], "human": entry["human"],
        })

    # Re-evaluar verdict por pregunta si relevant_chunks queda vacío
    for qid, q in questions.items():
        n = len(q["relevant_chunks"])
        old_verdict = q.get("verdict")
        if n == 0 and old_verdict == "relevant_found":
            q["verdict"] = "no_relevant_in_candidates"
            print(f"  {qid}: verdict re-evaluado relevant_found → no_relevant_in_candidates (0 relevantes tras revisión humana)")
        elif n > 0 and old_verdict == "no_relevant_in_candidates":
            q["verdict"] = "relevant_found"
            print(f"  {qid}: verdict re-evaluado no_relevant_in_candidates → relevant_found ({n} relevantes tras revisión humana)")

    # Actualizar metadata top-level
    gold["human_review"] = {
        "applied_at": audit["generated_at"],
        "source": "evals/gate_validation_disagreements.md (sesión 26)",
        "decisions_applied": audit["total_decisions_applied"],
        "scope": "hp* only — cm* deferred to post-SWAP per plan §B.2",
        "criterion": "PROCEDURAL PURO (rigor de dominio diferido a Capa A)",
        "removals": len(remove_list),
        "additions": len(add_list),
    }

    # Recalcular stats
    relevant_per_q = {qid: len(q["relevant_chunks"]) for qid, q in questions.items()}
    answer_qs = [qid for qid, q in questions.items()
                 if q.get("expected_behavior") == "answer"]
    answer_relevant_found = sum(1 for qid in answer_qs if relevant_per_q[qid] > 0)
    gold["stats"]["relevant_chunks_per_question_after_human"] = relevant_per_q
    gold["stats"]["answer_questions_with_relevant_after_human"] = answer_relevant_found
    gold["stats"]["answer_questions_total"] = len(answer_qs)

    print(f"\nResumen tras merge:")
    print(f"  Preguntas con relevant_chunks > 0: "
          f"{sum(1 for n in relevant_per_q.values() if n>0)} / {len(relevant_per_q)}")
    print(f"  Total relevant_chunks: "
          f"{sum(relevant_per_q.values())} (antes: ver _audit)")
    print(f"  Preguntas answer con relevantes: {answer_relevant_found}/{len(answer_qs)}")

    if dry_run:
        print("\n[DRY-RUN] No se escribe nada.")
        return

    # Backup
    shutil.copy(GOLD_PATH, GOLD_PATH.with_suffix(".json.bak"))
    GOLD_PATH.write_text(json.dumps(gold, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    AUDIT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    print(f"\nWritten: {GOLD_PATH}")
    print(f"         {AUDIT_PATH}")
    print(f"Backup:  {GOLD_PATH.with_suffix('.json.bak')}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    main(dry_run=args.dry_run)
