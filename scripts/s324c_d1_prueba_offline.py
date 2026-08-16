#!/usr/bin/env python3
"""s324c_d1_prueba_offline.py — prueba OFFLINE $0 del lever D1 «COVERAGE_LIST_BLOCK_CLOSURE».

Encargo (hub s324c, adenda post-dúo r33): «medir antes de construir». NO toca el seam;
solo lee la DB (REST) y corre el código REAL de la etapa de coverage importado
(`apply_profiled_post_rerank_coverage`, patrón fiel de scripts/s293_lane_replay.py)
sobre el pool y el top-k GRABADOS en el FULL 16-ago. Sin LLM: 0 llamadas de modelo.

Qué mide:
  1. la vista servida HOY de cada fila apendizada (todas las lanes, 39 golds):
     `coverage_cards` del selector, `served_coverage_cards` (= _build_served_coverage_cards,
     tabla-expandidas) y el texto que ve el generador (`coverage_context_content`);
  2. hp017#1: ¿el bullet «* Instrucción de entrada:» del carrier d27b1a1b queda fuera de las
     cards? ¿lo alcanza un «cierre de bloque de lista» simulado? Con DOS definiciones de bloque:
       A = líneas de ítem contiguas, LÍNEAS EN BLANCO PERMITIDAS entre ítems (la del diseño D1);
       B = líneas de ítem contiguas, la LÍNEA EN BLANCO ROMPE el bloque (objeción de Fable);
     ambas con ≥2 ítems, línea introductoria opcional que termina en «:», cap 1800 chars
     (MAX_EXPANDED_EXCERPT_CHARS). B1 = variante B con ≥1 ítem (la más laxa posible).
  3. censo del disparo sobre TODAS las filas apendizadas de TODAS las lanes: cuántas tienen una
     card que interseca un bloque de lista y lo corta; cuáles pertenecen a hechos NO-OK; y si el
     cierre aportaría el LITERAL del valor del hecho que hoy no está en la vista (beneficio).

Fidelidad auto-verificable: el replay debe reproducir los `appended_ids`+lanes del recibo; si
no, se declara en el JSON (la fila NO se descarta del censo, pero queda marcada).

Salida: evals/s324c_d1_prueba_offline_v1.json + .md (este script escribe SOLO esos dos).
Uso:    python scripts/s324c_d1_prueba_offline.py [--qids hp017,cat008] [--only-hp017]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)


# ── Freeze-contract: MISMO flag-set de la demo del FULL (fuente única: DEMO_FLAGS por AST) ──
def _load_demo_flags() -> dict[str, str]:
    import ast

    source = (ROOT / "scripts" / "factlevel_assessment.py").read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "DEMO_FLAGS" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise SystemExit("no se pudo leer DEMO_FLAGS del instrumento")


DEMO_FLAGS = _load_demo_flags()
for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v

sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.http_pool import abierto  # noqa: E402
from src.rag.coverage_runtime import apply_profiled_post_rerank_coverage  # noqa: E402
from src.rag.post_rerank_coverage import (  # noqa: E402
    MAX_EXPANDED_EXCERPT_CHARS,
    _build_served_coverage_cards,
    _mandatory_callout_card,
    _mandatory_callout_enabled,
    coverage_context_content,
    has_exact_mandatory_callout_receipt,
    has_exact_served_coverage_receipt,
    is_validated_coverage_chunk,
)
from src.rag.retriever import _HYDRATE_SELECT  # noqa: E402
from src.release_profiles import DOCUMENT_LOCAL_LANE  # noqa: E402

RECEIPT = ROOT / "evals" / "s100_factlevel_full_v3_20260816.yaml"
GOLDS = ROOT / "evals" / "gold_answers_v1.yaml"
OUT_JSON = ROOT / "evals" / "s324c_d1_prueba_offline_v1.json"
OUT_MD = ROOT / "evals" / "s324c_d1_prueba_offline_v1.md"
TARGET_QID = "hp017"
TARGET_FACT = "hp017#1:instruccion de entrada"
TARGET_CARRIER_PREFIX = "d27b1a1b"
TARGET_BULLET_PREFIX = "* Instrucción de entrada:"
HS = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
CHUNKS_TABLE = os.environ["CHUNKS_TABLE"]

# ───────────────────────── simulación del bloque de lista (NO está en src/) ─────────────────────────
# Regex del diseño D1 (propuesta §3): marcador de ítem + espacio.
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*•·◦]|\d{1,2}[.)])\s+")


def _line_spans(content: str) -> list[tuple[int, int, str]]:
    """(start, end, texto) por línea; `end` excluye el '\\n'. Offsets en code points."""
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    for raw in content.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        spans.append((cursor, cursor + len(line), line))
        cursor += len(raw)
    if cursor < len(content):
        spans.append((cursor, len(content), content[cursor:]))
    return spans


def list_blocks(content: str, *, blank_allowed: bool, min_items: int) -> list[dict]:
    """Bloques de lista = run de líneas-ítem (≥min_items) + intro opcional que termina en ':'.

    blank_allowed=True  → definición A: una línea en blanco NO rompe el run (si la siguiente
                          no-blanca es ítem); la intro puede estar separada por blancos.
    blank_allowed=False → definición B: la línea en blanco ROMPE el run; la intro debe ser la
                          línea inmediatamente anterior.
    Una línea no-blanca que no es ítem SIEMPRE cierra el bloque (declarado: no se modelan
    continuaciones de ítem sin marcador)."""
    lines = _line_spans(content)
    blocks: list[dict] = []
    i, n = 0, len(lines)
    while i < n:
        if not LIST_ITEM_RE.match(lines[i][2]):
            i += 1
            continue
        first, last, items = i, i, 1
        j = i + 1
        while j < n:
            text = lines[j][2]
            if LIST_ITEM_RE.match(text):
                last, items = j, items + 1
                j += 1
                continue
            if not text.strip() and blank_allowed:
                j += 1
                continue
            break
        start, end = lines[first][0], lines[last][1]
        has_intro = False
        k = first - 1
        if blank_allowed:
            while k >= 0 and not lines[k][2].strip():
                k -= 1
        if (
            k >= 0
            and lines[k][2].strip()
            and lines[k][2].rstrip().endswith(":")
            and not LIST_ITEM_RE.match(lines[k][2])
        ):
            start, has_intro = lines[k][0], True
        if items >= min_items:
            blocks.append(
                {"start": start, "end": end, "items": items, "has_intro": has_intro,
                 "items_start": lines[first][0]}
            )
        i = last + 1
    return blocks


def _merge(ranges: list[tuple[int, int]]) -> list[list[int]]:
    merged: list[list[int]] = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def _view(content: str, ranges: list[tuple[int, int]]) -> str:
    return "\n\n[... otro extracto fuente ...]\n\n".join(content[s:e] for s, e in _merge(ranges))


def simulate_closure(content: str, cards: list[tuple[int, int]], *, blank_allowed: bool,
                     min_items: int) -> dict:
    """Aplica el cierre a cada card: si interseca un bloque y NO lo cubre entero → span =
    unión(card, bloques intersecados); si supera MAX_EXPANDED_EXCERPT_CHARS → sin cambio (cap)."""
    blocks = list_blocks(content, blank_allowed=blank_allowed, min_items=min_items)
    out_cards, cuts, capped = [], [], []
    for cs, ce in cards:
        hit = [b for b in blocks if cs < b["end"] and b["start"] < ce]
        cut = [b for b in hit if b["start"] < cs or b["end"] > ce]
        if not cut:
            out_cards.append((cs, ce))
            continue
        ns = min([cs, *(b["start"] for b in cut)])
        ne = max([ce, *(b["end"] for b in cut)])
        if ne - ns > MAX_EXPANDED_EXCERPT_CHARS:
            capped.append({"card": [cs, ce], "would_be": [ns, ne], "len": ne - ns})
            out_cards.append((cs, ce))
            continue
        cuts.append({"card": [cs, ce], "closed": [ns, ne],
                     "blocks": [[b["start"], b["end"], b["items"], b["has_intro"]] for b in cut]})
        out_cards.append((ns, ne))
    return {"blocks": blocks, "cards_out": out_cards, "cuts": cuts, "capped": capped,
            "fires": bool(cuts) or bool(capped), "changes_view": bool(cuts)}


def fold(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in value if not unicodedata.combining(c)).casefold()


def literal_in(valor: str | None, text: str) -> bool | None:
    if not valor:
        return None
    return fold(valor) in fold(text)


# ───────────────────────────────── DB (solo lectura) ─────────────────────────────────
def hydrate(client, ids: list[str]) -> list[dict]:
    rows: dict[str, dict] = {}
    for start in range(0, len(ids), 40):
        batch = ",".join(f'"{cid}"' for cid in ids[start:start + 40])
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
            headers=HS,
            params={"select": _HYDRATE_SELECT, "id": f"in.({batch})"},
        )
        resp.raise_for_status()
        for row in resp.json():
            rows[row["id"]] = row
    return [rows[cid] for cid in ids if cid in rows]


def _card_ranges(cards) -> list[tuple[int, int]]:
    return [(int(c["start"]), int(c["end"])) for c in (cards or [])]


def _today_ranges(row: dict) -> tuple[list[tuple[int, int]], str]:
    """Qué cards sirve HOY coverage_context_content (misma regla que el código, flags demo)."""
    if not is_validated_coverage_chunk(row):
        return [], "content_completo(no_validated)"
    if row.get("retrieval_lane") == DOCUMENT_LOCAL_LANE and has_exact_served_coverage_receipt(row):
        return _card_ranges(row.get("served_coverage_cards")), "served_coverage_cards"
    return _card_ranges(row.get("coverage_cards")), "coverage_cards"


def _mandatory_today(row: dict) -> list[tuple[int, int]]:
    """Card de callout-MANDATORY que HOY se añade a la vista (s274 C1, flag del perfil)."""
    if _mandatory_callout_enabled() and has_exact_mandatory_callout_receipt(row):
        return _card_ranges(row.get("mandatory_callout_cards"))
    return []


def _mandatory_closed(row: dict, cards_out: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Re-deriva la card de callout con el código REAL sobre los spans CERRADOS (la callout
    excluye oraciones que ya solapan un span servido → puede cambiar si el cierre la absorbe)."""
    if not _mandatory_callout_enabled():
        return []
    callout = _mandatory_callout_card(row, [{"start": s, "end": e} for s, e in cards_out])
    return [(int(callout["start"]), int(callout["end"]))] if callout else []


DEFS = {
    "A_blancos_permitidos_ge2": {"blank_allowed": True, "min_items": 2},
    "B_blanco_rompe_ge2": {"blank_allowed": False, "min_items": 2},
    "B1_blanco_rompe_ge1": {"blank_allowed": False, "min_items": 1},
}


def analyse_row(row: dict, facts: list[dict]) -> dict:
    content = str(row.get("content") or "")
    today_ranges, today_field = _today_ranges(row)
    mandatory_today = _mandatory_today(row)
    today_view = coverage_context_content(row)
    served_cards = row.get("served_coverage_cards")
    if served_cards is None:
        served_cards = _build_served_coverage_cards(row)
    base_ranges = _card_ranges(served_cards) or today_ranges  # D1 actúa tras la expansión de tabla
    out = {
        "id": row.get("id"),
        "lane": row.get("retrieval_lane"),
        "source_file": row.get("source_file"),
        "chunk_index": row.get("chunk_index"),
        "page_number": row.get("page_number"),
        "content_chars": len(content),
        "coverage_cards": _card_ranges(row.get("coverage_cards")),
        "served_coverage_cards": _card_ranges(served_cards),
        "table_expanded": _card_ranges(served_cards) != _card_ranges(row.get("coverage_cards")),
        "mandatory_callout_cards": mandatory_today,
        "today_view_field": today_field,
        "today_view_chars": len(today_view),
        # auto-check: mi reconstrucción de la vista de hoy == la del código real
        "today_view_reconstructed_equal": _view(content, today_ranges + mandatory_today) == today_view,
        "defs": {},
    }
    for name, kw in DEFS.items():
        sim = simulate_closure(content, base_ranges, **kw)
        closed_view = _view(content, sim["cards_out"] + _mandatory_closed(row, sim["cards_out"]))
        entry = {
            "n_blocks": len(sim["blocks"]),
            "fires": sim["fires"],
            "changes_view": sim["changes_view"],
            "capped": sim["capped"],
            "cuts": sim["cuts"],
            "closed_view_chars": len(closed_view),
            "added_chars": len(closed_view) - len(today_view),
            "facts": [],
        }
        for fact in facts:
            valor = fact.get("valor")
            in_content = literal_in(valor, content)
            in_today = literal_in(valor, today_view)
            in_closed = literal_in(valor, closed_view)
            entry["facts"].append({
                "key": fact["key"], "clase": fact.get("clase"),
                "row_in_support": str(row.get("id")) in (fact.get("served_support_votes") or {}),
                "valor_in_content": in_content, "valor_in_view_today": in_today,
                "valor_in_view_closed": in_closed,
                "beneficio_literal": bool(in_closed) and not bool(in_today),
            })
        out["defs"][name] = entry
    return out


def hp017_detail(row: dict, gold_question: str) -> dict:
    content = str(row.get("content") or "")
    lines = _line_spans(content)
    bullet = next((ln for ln in lines if ln[2].startswith(TARGET_BULLET_PREFIX)), None)
    today_ranges, today_field = _today_ranges(row)
    mandatory_today = _mandatory_today(row)
    today_view = coverage_context_content(row)
    detail = {
        "carrier": row.get("id"), "source_file": row.get("source_file"),
        "chunk_index": row.get("chunk_index"), "page_number": row.get("page_number"),
        "gold_question": gold_question, "content_chars": len(content),
        "coverage_cards": [
            {"start": c["start"], "end": c["end"], "facet": c.get("facet"),
             "quote_head": str(c.get("quote") or "")[:70]}
            for c in row.get("coverage_cards") or []
        ],
        "served_coverage_cards": _card_ranges(row.get("served_coverage_cards")),
        "mandatory_callout_cards": mandatory_today,
        "today_view_field": today_field, "today_view_chars": len(today_view),
        "today_view_reconstructed_equal": _view(content, today_ranges + mandatory_today) == today_view,
        "target_bullet": None, "line_map": [
            {"start": s, "end": e, "is_item": bool(LIST_ITEM_RE.match(t)), "head": t[:60]}
            for s, e, t in lines
        ],
        "defs": {},
    }
    if bullet is None:
        detail["target_bullet"] = "NO ENCONTRADO"
        return detail
    bs, be, bt = bullet
    detail["target_bullet"] = {"start": bs, "end": be, "chars": be - bs, "text": bt}
    detail["target_outside_all_cards_today"] = all(
        not (cs < be and bs < ce) for cs, ce in today_ranges
    )
    detail["target_literal_in_today_view"] = "instrucción de entrada" in today_view.casefold()
    base_ranges = _card_ranges(row.get("served_coverage_cards")) or today_ranges
    for name, kw in DEFS.items():
        sim = simulate_closure(content, base_ranges, **kw)
        closed_view = _view(content, sim["cards_out"] + _mandatory_closed(row, sim["cards_out"]))
        reached = any(cs <= bs and be <= ce for cs, ce in sim["cards_out"])
        # chars añadidos y cuántos NO son el bullet diana
        added = len(closed_view) - len(today_view)
        target_added = (be - bs) if (reached and detail["target_outside_all_cards_today"]) else 0
        detail["defs"][name] = {
            "blocks": sim["blocks"], "cuts": sim["cuts"], "capped": sim["capped"],
            "cards_out": sim["cards_out"], "target_reached": reached,
            "target_literal_in_closed_view": "instrucción de entrada" in closed_view.casefold(),
            "added_chars_total": added,
            "added_chars_target_bullet": target_added,
            "added_chars_ajenos": added - target_added,
            "closed_view_chars": len(closed_view),
        }
    return detail


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--qids", default="", help="lista separada por comas (default: todos)")
    ap.add_argument("--only-hp017", action="store_true")
    args = ap.parse_args()

    receipt = yaml.safe_load(RECEIPT.read_text(encoding="utf-8"))
    per_gold = receipt["per_gold"]
    golds = {g["qid"]: g for g in yaml.safe_load(GOLDS.read_text(encoding="utf-8"))}
    wanted = set(args.qids.split(",")) if args.qids else None
    if args.only_hp017:
        wanted = {TARGET_QID}

    t0 = time.time()
    results: list[dict] = []
    hp017: dict | None = None
    with abierto(90.0) as client:
        for g in per_gold:
            qid = g["qid"]
            if wanted and qid not in wanted:
                continue
            query = g["question"]
            gold_q = (golds.get(qid) or {}).get("question")
            pool_ids, topk_ids = list(g["pool_ids"]), list(g["topk_ids"])
            pool, topk = hydrate(client, pool_ids), hydrate(client, topk_ids)
            served, trace = apply_profiled_post_rerank_coverage(
                query, [dict(c) for c in topk], retrieval_pool=[dict(c) for c in pool]
            )
            appended = served[len(topk):]
            replay_ids = [str(r.get("id") or "") for r in appended]
            replay_lane = {str(r.get("id") or ""): r.get("retrieval_lane") for r in appended}
            rec_ids = list(g.get("appended_ids") or [])
            rec_lane = dict(g.get("appended_lane") or {})
            facts = g.get("facts") or []
            fidelity = {
                "recorded_appended": rec_ids, "replay_appended": replay_ids,
                "equal_order": rec_ids == replay_ids,
                "equal_set": sorted(rec_ids) == sorted(replay_ids),
                "lanes_equal": all(rec_lane.get(i) == replay_lane.get(i) for i in rec_ids if i in replay_lane),
                "missing_pool": [i for i in pool_ids if i not in {c["id"] for c in pool}],
                "missing_topk": [i for i in topk_ids if i not in {c["id"] for c in topk}],
                "model_calls": trace.get("model_calls"),
            }
            rows = [analyse_row(r, facts) for r in appended]
            results.append({
                "qid": qid, "question": query, "gold_question_equal": (gold_q == query),
                "fidelity": fidelity, "n_facts": len(facts),
                "facts_no_ok": [f["key"] for f in facts if f.get("clase") != "OK"],
                "rows": rows,
                "lanes_trace": [
                    {"lane": ln.get("lane"), "status": ln.get("status")}
                    for ln in (trace.get("lanes") or []) if isinstance(ln, dict)
                ],
            })
            if qid == TARGET_QID:
                carrier = next((r for r in appended if str(r.get("id")).startswith(TARGET_CARRIER_PREFIX)), None)
                if carrier is None:
                    # el carrier no salió en el replay: hidratar y atestar aparte, declarado
                    hp017 = {"carrier_in_replay": False}
                else:
                    hp017 = hp017_detail(carrier, gold_q)
                    hp017["carrier_in_replay"] = True
            print(f"{qid}: fidelidad orden={fidelity['equal_order']} set={fidelity['equal_set']} "
                  f"filas={len(rows)} lanes={[r['lane'].split('_')[0] for r in rows]}", flush=True)

    # ── censo agregado ──
    lanes_count: dict[str, int] = {}
    census = {name: {"rows_fire": 0, "rows_change": 0, "rows_capped_only": 0, "golds": set(),
                     "rows": [], "facts_no_ok_strict": set(), "facts_no_ok_loose": set(),
                     "facts_no_ok_beneficio_literal": set(), "facts_ok_touched": set()}
              for name in DEFS}
    n_rows = 0
    fidelity_ok = sum(1 for g in results if g["fidelity"]["equal_order"])
    for g in results:
        for r in g["rows"]:
            n_rows += 1
            lanes_count[r["lane"]] = lanes_count.get(r["lane"], 0) + 1
            for name in DEFS:
                d = r["defs"][name]
                if not d["fires"]:
                    continue
                c = census[name]
                c["rows_fire"] += 1
                if d["changes_view"]:
                    c["rows_change"] += 1
                else:
                    c["rows_capped_only"] += 1
                c["golds"].add(g["qid"])
                c["rows"].append({"qid": g["qid"], "id": r["id"], "lane": r["lane"],
                                  "source_file": r["source_file"], "chunk_index": r["chunk_index"],
                                  "added_chars": d["added_chars"], "capped": bool(d["capped"]),
                                  "cuts": [x["closed"] for x in d["cuts"]]})
                for f in d["facts"]:
                    if f["clase"] != "OK":
                        c["facts_no_ok_loose"].add(f["key"])
                        if f["row_in_support"]:
                            c["facts_no_ok_strict"].add(f["key"])
                        if f["beneficio_literal"]:
                            c["facts_no_ok_beneficio_literal"].add(f["key"])
                    elif f["row_in_support"] and d["changes_view"]:
                        c["facts_ok_touched"].add(f["key"])
    for name, c in census.items():
        for k in ("golds", "facts_no_ok_strict", "facts_no_ok_loose",
                  "facts_no_ok_beneficio_literal", "facts_ok_touched"):
            c[k] = sorted(c[k])

    out = {
        "probe": "s324c_d1_prueba_offline_v1",
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True).stdout.decode().strip(),
        "recibo": str(RECEIPT.relative_to(ROOT)),
        "flags_demo": DEMO_FLAGS,
        "coste": {"llamadas_modelo": 0, "escrituras_db": 0, "segundos": round(time.time() - t0, 1)},
        "definiciones": {
            "A_blancos_permitidos_ge2": "run de líneas-ítem (regex D1) con líneas en blanco permitidas entre ítems, ≥2 ítems, intro opcional que termina en ':' (blancos permitidos), cap 1800",
            "B_blanco_rompe_ge2": "run de líneas-ítem CONSECUTIVAS (la línea en blanco rompe), ≥2 ítems, intro = línea inmediatamente anterior que termina en ':', cap 1800",
            "B1_blanco_rompe_ge1": "como B pero ≥1 ítem (la más laxa)",
            "disparo": "una card (served_coverage_cards, tras expansión de tabla) interseca un bloque y NO lo cubre entero → span = unión(card, bloque); si > 1800 chars → sin cambio (capped)",
            "beneficio_literal": "fold(valor del hecho) ∉ vista de hoy ∧ ∈ vista cerrada",
            "strict": "hecho NO-OK cuyo served_support_votes incluye la fila disparada",
            "loose": "hecho NO-OK de un gold con ≥1 fila disparada",
        },
        "resumen": {
            "golds": len(results), "golds_fidelidad_orden": fidelity_ok,
            "filas_apendizadas": n_rows, "filas_por_lane": lanes_count,
            "censo": census,
        },
        "hp017": hp017,
        "per_gold": results,
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"escrito: {OUT_JSON}")
    print(json.dumps({"golds": len(results), "fidelidad": fidelity_ok, "filas": n_rows,
                      "censo": {k: {"fire": v["rows_fire"], "change": v["rows_change"],
                                    "golds": len(v["golds"]), "no_ok_strict": v["facts_no_ok_strict"],
                                    "beneficio": v["facts_no_ok_beneficio_literal"]}
                                for k, v in census.items()}}, ensure_ascii=False, indent=1))
    if hp017:
        print(json.dumps({k: v for k, v in hp017.items() if k not in ("line_map",)},
                         ensure_ascii=False, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
