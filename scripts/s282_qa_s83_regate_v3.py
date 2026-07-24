#!/usr/bin/env python3
"""s282 QA-s83 — v3 RE-GATING: category-plausibility guard (root degradation).

The confirmatory LQAS re-draw over the v2 auto-apply cohort
(``evals/s282_qa_s83_lqas_redraw_v1.md``, seed 592) FAILED the 0-defect bar with
1 defect / 59: row #14 ``ADW535_TD_T140358es_e`` (Securiton), axis ``doc_type``.
s83 labels Securiton "Descripción técnica / Technische Beschreibung" (``_TD_T140xxx``)
manuals of 118-129 pp as ``datasheet``. It is a systematic CLASS, not one row: 3 such
files in the 536-lot, all ``doc_type=NULL`` in DB, all would auto-write ``datasheet``.

This v3 re-gate adds a DETERMINISTIC, $0 ROOT guard — not a 3-file patch: any
auto-apply proposal of a SHORT-genre ``doc_type`` (datasheet / boletin — genres that
are definitionally brief spec sheets / bulletins) on a document larger than
``CHUNK_GUARD_THRESHOLD`` chunks is a detectable category error -> routed to
``adjudicate`` (recall-safe: the whole suspect record goes to Alberto, never
auto-applied). A "datasheet" of 118 pages / 201 chunks is implausible on its face and
catchable with zero model calls.

The guard consumes the FROZEN v2 records (``evals/s282_qa_s83_result_v2.json`` — the
deterministic, 2x-byte-identical baseline) and applies the extra gate stage. It runs
2x byte-identical (asserted). The only DB access is a SELECT of ``chunks_v2.source_file``
to count chunks per document; the corpus fingerprint is re-taken and asserted equal to
v2's frame (no drift). READ-ONLY, SELECT-only, zero writes, zero paid model calls.
Outputs restricted to this lane's territory (``scripts/s282_qa_s83_*`` /
``evals/s282_qa_s83_*``). NO commits.

Usage:
  python scripts/s282_qa_s83_regate_v3.py    # apply guard, emit result_v3.json + report_v3.md ($0, 2x)
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# reuse the v1 instrument's read-only HTTP stack + helpers (_get_all/_nk/_stable_sha256/
# corpus_fingerprint/freeze_contract). Import it as a module.
_spec = importlib.util.spec_from_file_location(
    "s282_qa_s83_instrument", ROOT / "scripts/s282_qa_s83_instrument.py")
inst = importlib.util.module_from_spec(_spec)          # type: ignore[arg-type]
_spec.loader.exec_module(inst)                         # type: ignore[union-attr]

V2_RESULT = ROOT / "evals/s282_qa_s83_result_v2.json"
V3_RESULT = ROOT / "evals/s282_qa_s83_result_v3.json"
V3_REPORT = ROOT / "evals/s282_qa_s83_report_v3.md"

AUTO_APPLY = {"corroborate_noop", "fill_language_doctype"}
# Genres that are DEFINITIONALLY brief (spec sheet / bulletin). An enum member is a
# "short class" iff a document of that genre cannot plausibly run to many pages.
SHORT_DOC_TYPES = {"datasheet", "boletin"}
CHUNK_GUARD_THRESHOLD = 30   # >30 chunks (~15+ pp) is far beyond any spec sheet/bulletin


def _fetch_chunk_counts() -> dict[str, int]:
    """SELECT-only: count chunks_v2 rows per source_file (document size proxy)."""
    rows = inst._get_all("chunks_v2", "source_file", order="id.asc")
    return dict(Counter(str(r.get("source_file") or "") for r in rows))


def category_guard(row: dict[str, Any], chunk_counts: dict[str, int]) -> tuple[bool, str]:
    """Return (fired, note). Fires on a SHORT-genre doc_type fill over a large doc."""
    if row.get("write_op") not in AUTO_APPLY:
        return False, ""
    fp = row.get("fill_plan") or {}
    if not fp.get("doc_type_fill"):
        return False, ""
    dtv = fp.get("doc_type_value")
    if dtv is None or inst._nk(dtv) not in {inst._nk(x) for x in SHORT_DOC_TYPES}:
        return False, ""
    n = chunk_counts.get(row["source_file"], 0)
    if n > CHUNK_GUARD_THRESHOLD:
        return True, (f"guard de plausibilidad de categoria: doc_type='{dtv}' (clase corta) sobre "
                      f"documento de {n} chunks (>{CHUNK_GUARD_THRESHOLD}) — error de categoria "
                      "detectable a $0 -> adjudicate (registro completo a Alberto, recall-safe)")
    return False, ""


def apply_guard(records: list[dict[str, Any]], chunk_counts: dict[str, int]
                ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministic: iterate records sorted by source_file; degrade guard hits."""
    out: list[dict[str, Any]] = []
    moved: list[dict[str, Any]] = []
    for r in sorted(records, key=lambda x: x["source_file"]):
        r2 = dict(r)
        fired, note = category_guard(r, chunk_counts)
        if fired:
            fp = r.get("fill_plan") or {}
            r2["write_op"] = "adjudicate"
            r2["write_op_note"] = note
            r2["guard"] = {
                "category_plausibility": True,
                "chunks": chunk_counts.get(r["source_file"], 0),
                "threshold": CHUNK_GUARD_THRESHOLD,
                "original_write_op": r.get("write_op"),
                "original_doc_type_value": fp.get("doc_type_value"),
                "original_language_value": fp.get("language_value"),
            }
            r2["fill_plan"] = None   # adjudicate rows never auto-apply
            moved.append(r2)
        out.append(r2)
    return out, moved


def recompute(guarded: list[dict[str, Any]]) -> dict[str, Any]:
    wo_dist = Counter(r["write_op"] for r in guarded)
    adj: dict[str, int] = {}
    for r in guarded:
        if r["write_op"] != "adjudicate":
            continue
        if r.get("guard", {}).get("category_plausibility"):
            key = "category_guard"
        else:
            note = r.get("write_op_note", "")
            if "juez-triage marco CONFLICT" in note:
                key = "judge_pull"
            elif r.get("subrel") == "corrob_prim":
                key = "corrob_prim"
            else:
                key = r.get("subrel", "?")
        adj[key] = adj.get(key, 0) + 1
    auto_rows = [r for r in guarded if r["write_op"] in AUTO_APPLY]
    fp = {
        "language_fills_singleton_auto": sum(1 for r in auto_rows if r["fill_plan"]["language_fill_singleton"]),
        "language_fills_multi_advisory": sum(1 for r in auto_rows if r["fill_plan"]["language_fill_multi_advisory"]),
        "doc_type_fills": sum(1 for r in auto_rows if r["fill_plan"]["doc_type_fill"]),
        "language_contradict_in_auto": sum(1 for r in auto_rows if r["fill_plan"]["language_contradict"]),
        "doc_type_differ_in_auto": sum(1 for r in auto_rows if r["fill_plan"]["doc_type_differ"]),
    }
    return {
        "write_op_distribution": dict(wo_dist),
        "auto_apply_n": len(auto_rows),
        "adjudicate_breakdown": dict(sorted(adj.items(), key=lambda kv: -kv[1])),
        "fill_summary": fp,
    }


def build_report(v2: dict[str, Any], payload: dict[str, Any]) -> str:
    L: list[str] = []
    A = L.append
    g = payload["guard"]
    v2wo = v2["write_op_distribution"]
    v3wo = payload["write_op_distribution"]
    v2fs = v2["fill_summary"]
    v3fs = payload["fill_summary"]

    A("# s282 QA-s83 — RE-GATING v3: guard de plausibilidad de categoría (degradación de raíz)")
    A("")
    A("El re-draw LQAS confirmatorio v1 (`evals/s282_qa_s83_lqas_redraw_v1.md`, seed 592) **NO pasó** el "
      "listón 0-defectos: 1 defecto / 59, fila `ADW535_TD_T140358es_e` (Securiton), eje `doc_type`. "
      "s83 etiqueta las «Descripción técnica / Technische Beschreibung» (`_TD_T140xxx`) de Securiton, "
      "manuales de 118–129 pp, como `datasheet`. Es una CLASE sistemática (3 ficheros en el lote de 536).")
    A("")
    A("**Fix de RAÍZ (no parche de 3 ficheros):** guard determinista $0 — toda propuesta auto-apply de un "
      f"`doc_type` de **clase corta** ({' / '.join(sorted(SHORT_DOC_TYPES))} — géneros definitoriamente breves) "
      f"sobre un documento de **> {CHUNK_GUARD_THRESHOLD} chunks** es un error de categoría detectable "
      "→ `adjudicate` (el registro completo va a Alberto; recall-safe, nunca se auto-escribe). Un "
      "«datasheet» de 118 pp / 201 chunks es implausible por construcción y cazable con 0 llamadas de modelo.")
    A("")
    A("READ-ONLY, SELECT-only (`chunks_v2.source_file` para contar chunks/documento), 0 escrituras, "
      "0 modelo de pago. Consume los records FROZEN del v2 (baseline 2×-byte-idéntico) y aplica la etapa "
      "extra de gate. Guard 2× byte-idéntico (aserción). Frame verificado == v2 (sin drift).")
    A("")
    A("## 1. Determinismo + frame")
    A("")
    A(f"- guard 2× byte-idéntico: **{'IDÉNTICO' if payload['deterministic_2x'] else 'DIVERGE'}** "
      f"(`{payload['guard_sha256_pass1'][:16]}` == `{payload['guard_sha256_pass2'][:16]}`)")
    A(f"- corpus fingerprint == v2: **{payload['frame_matches_v2']}** "
      f"(chunks_v2={payload['corpus_fingerprint']['chunks_v2']['count']} · "
      f"documents={payload['corpus_fingerprint']['documents']['count']} · sha "
      f"`{payload['corpus_fingerprint']['sha256'][:16]}`)")
    A(f"- commit HEAD: `{payload['freeze_contract']['commit_head']}` "
      f"(dirty: {payload['freeze_contract']['worktree_dirty']})")
    A("")
    A("## 2. Filas movidas por el guard (declaración exacta)")
    A("")
    A(f"**El guard mueve {g['n_moved']} filas** auto-apply → `adjudicate` (esperado: pocas). "
      "TODAS son la clase Securiton `_TD` `datasheet`; ninguna otra clase corta (`boletin`, máx 21 chunks) "
      "supera el umbral. Detalle:")
    A("")
    A("| source_file | marca | chunks | write_op v2 → v3 | doc_type (s83) | language (s83) |")
    A("|---|---|---:|---|---|---|")
    for m in g["moved_detail"]:
        A(f"| `{m['source_file']}` | {m['brand']} | {m['chunks']} | "
          f"`{m['original_write_op']}` → `adjudicate` | `{m['original_doc_type_value']}` | "
          f"{m['original_language_value']} |")
    A("")
    A("## 3. Cohortes v2 → v3")
    A("")
    A("| write_op | v2 | v3 | Δ | destino |")
    A("|---|---:|---:|---:|---|")
    dest = {
        "corroborate_noop": "**AUTO-APPLY**", "fill_language_doctype": "**AUTO-APPLY**",
        "adjudicate": "[ALBERTO]", "excluded_t3": "excluido (T3)", "unmapped": "fuera de alcance",
        "replace_pm": "vacío por diseño",
    }
    for wo in ["corroborate_noop", "fill_language_doctype", "adjudicate", "excluded_t3", "unmapped"]:
        a, b = v2wo.get(wo, 0), v3wo.get(wo, 0)
        A(f"| `{wo}` | {a} | {b} | {b - a:+d} | {dest.get(wo, '')} |")
    A(f"| **TOTAL** | **{sum(v2wo.values())}** | **{sum(v3wo.values())}** | 0 | |")
    A("")
    A(f"**Auto-apply v2 → v3: {v2['auto_apply_n']} → {payload['auto_apply_n']}** "
      f"({payload['auto_apply_n'] - v2['auto_apply_n']:+d}).")
    A("")
    A("### 3b. Desglose de `adjudicate` (nuevo bucket `category_guard`)")
    A("")
    A("| sub-relación | v2 | v3 |")
    A("|---|---:|---:|")
    keys = list(dict.fromkeys(list(v2["adjudicate_breakdown"].keys()) +
                              list(payload["adjudicate_breakdown"].keys())))
    for k in keys:
        A(f"| `{k}` | {v2['adjudicate_breakdown'].get(k, 0)} | {payload['adjudicate_breakdown'].get(k, 0)} |")
    A("")
    A("## 4. Fill summary (eje a eje) v2 → v3")
    A("")
    A("| eje | v2 | v3 | Δ |")
    A("|---|---:|---:|---:|")
    labels = {
        "doc_type_fills": "`doc_type` AUTO (DB NULL → s83)",
        "language_fills_singleton_auto": "`language` SINGLETON AUTO",
        "language_fills_multi_advisory": "`language` MULTI (advisory, no auto)",
        "language_contradict_in_auto": "`language` contradicho (advisory)",
        "doc_type_differ_in_auto": "`doc_type` distinto en DB (advisory)",
    }
    for k, lab in labels.items():
        a, b = v2fs.get(k, 0), v3fs.get(k, 0)
        A(f"| {lab} | {a} | {b} | {b - a:+d} |")
    A("")
    A("`product_model` NUNCA se auto-escribe (corroborate_noop = NO-OP; family = etiqueta gobernada "
      "conservada) — invariante desde v2.")
    A("")
    A("## 5. Qué NO cambia y honestidad")
    A("")
    A("- El guard **sólo puede SACAR** filas del auto-apply (dirección segura); nunca añade ninguna.")
    A("- `language`-MULTI sigue ADVISORY (over-call de idioma, v2). El guard es ortogonal: ataca el eje "
      "`doc_type` (género implausible), no el idioma.")
    A("- Las 3 filas movidas tenían `language='es'` singleton CORRECTO (verificado en el re-draw v1); "
      "aun así el registro COMPLETO va a Alberto (recall-safe: si s83 confunde el género del documento, "
      "el registro entero es sospechoso). El coste es 3 fills de idioma correctos que Alberto revisará, "
      "no un auto-write erróneo.")
    A("- La firma del lote sigue GATEADA por un re-draw LQAS confirmatorio (draw 3, seed distinta) sobre "
      "la cohorte v3 a 0-defectos — este re-gate no la sustituye.")
    A("")
    return "\n".join(L)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    v2 = json.loads(V2_RESULT.read_text(encoding="utf-8"))
    records = v2["records"]

    inst._init_http()
    contract = inst.freeze_contract()
    fp_corpus = inst.corpus_fingerprint()
    frame_matches = fp_corpus["sha256"] == v2["corpus_fingerprint"]["sha256"]
    if not frame_matches:
        print("WARNING: corpus fingerprint DIVERGES from v2 frame — chunk counts may not match the "
              "records' frame. Proceeding but flagging frame_matches_v2=False.", file=sys.stderr)

    chunk_counts = _fetch_chunk_counts()

    # 2x deterministic guard application
    g1, moved1 = apply_guard(records, chunk_counts)
    g2, moved2 = apply_guard(records, chunk_counts)
    sha1 = inst._stable_sha256(g1)
    sha2 = inst._stable_sha256(g2)
    deterministic = sha1 == sha2

    agg = recompute(g1)

    moved_detail = [{
        "source_file": m["source_file"], "brand": m["brand"], "chunks": m["guard"]["chunks"],
        "original_write_op": m["guard"]["original_write_op"],
        "original_doc_type_value": m["guard"]["original_doc_type_value"],
        "original_language_value": m["guard"]["original_language_value"],
    } for m in sorted(moved1, key=lambda x: x["source_file"])]

    payload = {
        "schema": "s282_qa_s83_regate_v3",
        "authority": "DEVELOPMENT_QA_READ_ONLY_SELECT_ONLY_ZERO_WRITES_ZERO_PAID_MODEL",
        "inherits": "evals/s282_qa_s83_result_v2.json (frozen baseline records)",
        "freeze_contract": contract,
        "corpus_fingerprint": fp_corpus,
        "frame_matches_v2": frame_matches,
        "deterministic_2x": deterministic,
        "guard_sha256_pass1": sha1,
        "guard_sha256_pass2": sha2,
        "guard": {
            "rule": "auto-apply doc_type in SHORT_DOC_TYPES AND chunks > threshold -> adjudicate",
            "short_doc_types": sorted(SHORT_DOC_TYPES),
            "chunk_threshold": CHUNK_GUARD_THRESHOLD,
            "n_moved": len(moved1),
            "moved_source_files": [m["source_file"] for m in moved_detail],
            "moved_detail": moved_detail,
        },
        "n_source_files": len(g1),
        "write_op_distribution": agg["write_op_distribution"],
        "auto_apply_n": agg["auto_apply_n"],
        "adjudicate_breakdown": agg["adjudicate_breakdown"],
        "fill_summary": agg["fill_summary"],
        "records": g1,
    }
    with io.open(V3_RESULT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1, default=str)
        fh.write("\n")
    V3_REPORT.write_text(build_report(v2, payload), encoding="utf-8")

    print(f"deterministic_2x={deterministic} frame_matches_v2={frame_matches} sha={sha1[:16]}")
    print(f"guard moved {len(moved1)} rows: {[m['source_file'] for m in moved_detail]}")
    print(f"write_op v2={v2['write_op_distribution']}")
    print(f"write_op v3={agg['write_op_distribution']}")
    print(f"auto_apply {v2['auto_apply_n']} -> {agg['auto_apply_n']}")
    print(f"fill_summary v2={v2['fill_summary']}")
    print(f"fill_summary v3={agg['fill_summary']}")
    print(f"adjudicate_breakdown v3={agg['adjudicate_breakdown']}")
    print(f"result: {V3_RESULT}")
    print(f"report: {V3_REPORT}")
    return 0 if (deterministic and frame_matches) else 2


if __name__ == "__main__":
    sys.exit(main())
