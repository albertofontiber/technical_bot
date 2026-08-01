#!/usr/bin/env python3
"""s292 L3 — probe REPRODUCIBLE del gatillo «siempre» (cierra Sol-1/2/3).

Sol (r1 del dúo) cazó tres huecos del diseño v1:
  S1: «citado ⇒ el resto funciona» NO estaba medido — `bind_atoms` exige además
      una `citation_window` con solape procedimental (`atom_exigible_in`). Aquí
      se MIDE sobre el draft real.
  S2: `FAMILY_CAP` se aplica GLOBALMENTE a los `missing` de toda la respuesta y
      se ordena por fuerza de binding ⇒ el átomo nuevo puede DESPLAZAR a uno
      existente. Aquí se censa la respuesta ENTERA, no solo el chunk diana.
  S3: el recibo del censo no era reproducible (sin regex/script/hash, sin el
      brazo naive, frases truncadas). Este script ES el generador, emite AMBOS
      brazos íntegros y estampa el sha del recibo del FULL que define la
      población.

Coste: 0 LLM · 0 jueces · GETs read-only de chunks_v2.
Salida: evals/s292_l3_probe_result_v1.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
import httpx  # noqa: E402
import yaml  # noqa: E402

from src.rag.mp_lexicon import mandatory_triggers, sentence_spans  # noqa: E402
from src.rag.must_preserve import (  # noqa: E402
    FAMILY_MANDATORY,
    _content_tokens,
    _dedup,
    atom_exigible_in,
    atom_satisfied,
    cited_fragment_numbers,
    citation_window,
    detect_atoms,
    procedural_context_tokens,
)

FULL = ROOT / "evals" / "s100_factlevel_full_v32_full_20260801.yaml"
OUT = ROOT / "evals" / "s292_l3_probe_result_v1.json"
URL, KEY = os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

# ── REGLAS DEL GATILLO (S3: viven en el script, no solo en la prosa) ──────────
NAIVE = re.compile(r"\b([a-záéíóúñ]{3,}[ae])\s+siempre\b(?!\s+que\b)"
                   r"|(?<!\w)siempre\s+([a-záéíóúñ]{3,}[ae])\b", re.I)
COND = re.compile(r"siempre\s+(y\s+cuando|que)\b", re.I)
IMPER = re.compile(r"(?:^|[.;:]\s*|[*>\-]\s+)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}[ae])\s+siempre\b")
DEONT = re.compile(r"siempre[^.]{0,60}\b(debe|deben|tiene\s+que|tienen\s+que|hay\s+que)\b"
                   r"|\b(debe|deben|tiene\s+que|tienen\s+que|hay\s+que)\b[^.]{0,60}siempre\b",
                   re.I)
TARGET_QID, TARGET_CHUNK = "hp003", "eaa39792"


def _fetch(ids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(ids), 40):
        r = httpx.get(f"{URL}/rest/v1/chunks_v2",
                      params={"select": "id,content,source_file,page_number",
                              "id": f"in.({','.join(ids[i:i+40])})"},
                      headers=H, timeout=120)
        for row in r.json():
            out[str(row["id"])] = row
    return out


def _trigger_form(sent: str) -> str | None:
    if COND.search(sent) or "siempre" not in sent.lower():
        return None
    if mandatory_triggers(sent):
        return None            # ya cazada por el léxico actual
    if IMPER.search(sent):
        return "A-imperativo"
    if DEONT.search(sent):
        return "B-deontico"
    return None


def _synthetic_atom(sent: str, fragment_text: str) -> dict:
    """FIEL a `_detect_mandatory` (must_preserve.py:594-627): allí
    `proc_tokens = procedural_context_tokens(text)` se extrae del FRAGMENTO
    COMPLETO, no del span de la cláusula.

    ATENCIÓN (auto-declaración para el revisor): la v1 de esta sonda pasaba
    `procedural_context_tokens: []` y `atom_exigible_in` daba False — es decir,
    la v1 MATABA el lever. La corrección NO es tuning hacia el resultado
    deseado: el ancla es que producción computa esos tokens del fragmento
    entero (`_detect_mandatory` línea `proc_tokens = procedural_context_tokens(
    text)`), y `atom_exigible_in` documenta que F-MANDATORY exige >=2 tokens
    compartidos con `meta.procedural_context_tokens` (must_preserve.py:1619-1623).
    Con la simulación fiel el veredicto pasa a True. VERIFICAR en el dúo."""
    return {"family": FAMILY_MANDATORY, "span_text": sent.strip(),
            "anchor_tokens": _dedup(_content_tokens(sent)),
            "meta": {"triggers": ["siempre"],
                     "procedural_context_tokens": procedural_context_tokens(fragment_text)}}


def main() -> int:
    data = yaml.safe_load(FULL.read_text(encoding="utf-8"))
    full_sha = hashlib.sha256(FULL.read_bytes()).hexdigest()[:16]
    served_all = sorted({str(x) for g in data["per_gold"]
                         for x in (g.get("served_ids") or []) if x})
    rows = _fetch(served_all)

    # ── S3: censo con AMBOS brazos, frases íntegras ──────────────────────────
    naive_hits, tight_hits = [], []
    for cid, row in rows.items():
        content = row.get("content") or ""
        for s, e in sentence_spans(content):
            sent = content[s:e]
            if "siempre" not in sent.lower():
                continue
            if mandatory_triggers(sent):
                continue
            if NAIVE.search(sent):
                naive_hits.append({"id": cid[:8], "sent": sent.strip()})
            form = _trigger_form(sent)
            if form:
                tight_hits.append({"id": cid[:8], "form": form,
                                   "sent": sent.strip(),
                                   "source_file": str(row.get("source_file") or "")[:40],
                                   "page": row.get("page_number")})

    # ── S1: exigibilidad REAL del átomo diana sobre el draft real ────────────
    gold = next(g for g in data["per_gold"] if g["qid"] == TARGET_QID)
    answer = gold["answer"]
    served_ids = [str(x) for x in (gold.get("served_ids") or [])]
    target_id = next(x for x in served_ids if x.startswith(TARGET_CHUNK))
    idx = served_ids.index(target_id) + 1        # fragment_number 1-based
    cited = cited_fragment_numbers(answer)
    target_sent = next((h["sent"] for h in tight_hits
                        if h["id"] == TARGET_CHUNK), None)
    s1: dict = {"fragment_number": idx, "is_cited": idx in cited,
                "target_sentence": target_sent}
    if target_sent:
        atom = _synthetic_atom(target_sent, rows[target_id]["content"])
        window = citation_window(answer, idx)
        s1.update({
            "citation_window_chars": len(window.strip()),
            "atom_exigible_in_window": bool(window.strip()
                                            and atom_exigible_in(atom, window)),
            "atom_satisfied_by_answer": bool(atom_satisfied(atom, answer)),
        })
        s1["VERDICT_apendice_emitiria"] = bool(
            s1["is_cited"] and s1["atom_exigible_in_window"]
            and not s1["atom_satisfied_by_answer"])

    # ── S2: cap GLOBAL — censo de missing MANDATORY en TODA la respuesta ─────
    global_missing = []
    for i, cid in enumerate(served_ids, start=1):
        row = rows.get(cid)
        if not row or i not in cited:
            continue
        for a in detect_atoms(row.get("content") or ""):
            if a.get("family") != FAMILY_MANDATORY:
                continue
            window = citation_window(answer, i)
            if not window.strip() or not atom_exigible_in(a, window):
                continue
            if not atom_satisfied(a, answer):
                global_missing.append({"fragment": i, "id": cid[:8],
                                       "span": a["span_text"][:90]})
    s2 = {"missing_mandatory_en_toda_la_respuesta": len(global_missing),
          "FAMILY_CAP": 2, "detalle": global_missing,
          "riesgo_desplazamiento": len(global_missing) >= 2}

    result = {"instrument": "s292_l3_probe_result_v1",
              "full_receipt_sha256_16": full_sha,
              "poblacion_chunks_servidos": len(rows),
              "regex": {"NAIVE": NAIVE.pattern, "COND": COND.pattern,
                        "IMPER": IMPER.pattern, "DEONT": DEONT.pattern},
              "S3_censo": {"naive_n": len(naive_hits), "tight_n": len(tight_hits),
                           "naive_hits": naive_hits, "tight_hits": tight_hits},
              "S1_exigibilidad": s1, "S2_cap_global": s2}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"S3 censo: naive={len(naive_hits)} · apretado={len(tight_hits)}")
    print(f"S1 exigibilidad: {json.dumps({k: v for k, v in s1.items() if k != 'target_sentence'}, ensure_ascii=False)}")
    print(f"S2 cap global: missing={s2['missing_mandatory_en_toda_la_respuesta']} "
          f"cap=2 riesgo_desplazamiento={s2['riesgo_desplazamiento']}")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
