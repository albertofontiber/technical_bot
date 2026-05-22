#!/usr/bin/env python3
"""Build calibration_v2 documents from the most recent eval log.

Reads logs/eval_*.json (last one by timestamp), groups results by category,
and emits one markdown file per category under evals/calibration_v2/.

Format mirrors evals/judge_calibration_v1.md so Alberto's reading flow is
identical: query -> expected behavior -> fragments F<n> (what the bot saw)
-> bot response -> judge verdict + rationale -> checkboxes for human juicio.

V (verification) chunks intentionally omitted to keep the doc readable;
the judge rationale flags when V was decisive ("...el dato vive en V3...")
so Alberto can ask Claude to fetch the V manually for those cases.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
OUT_DIR = ROOT / "evals" / "calibration_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_FILES = {
    "happy_path": "01_happy_path.md",
    "ambiguous_model": "02_ambiguous_model.md",
    "missing_context": "03_missing_context.md",
    "not_in_db": "04_not_in_db.md",
    "cross_manual": "05_cross_manual.md",
}

CATEGORY_DESCRIPTIONS = {
    "happy_path": (
        "Modelo y pregunta claros, info en corpus -> bot debe responder "
        "con cita y sin inventar."
    ),
    "ambiguous_model": (
        "Nombre de modelo genérico o familia -> bot debe pedir "
        "aclaración antes de responder."
    ),
    "missing_context": (
        "Técnico no menciona fabricante/modelo -> bot debe pedir "
        "aclaración."
    ),
    "not_in_db": (
        "Producto/fabricante NO en corpus -> bot debe admitir el gap sin "
        "inventar."
    ),
    "cross_manual": (
        "Pregunta menciona varios fabricantes -> política: NO inferir "
        "cross-brand."
    ),
}


def latest_eval_log() -> Path:
    candidates = sorted(LOGS.glob("eval_*.json"))
    if not candidates:
        raise SystemExit("No eval logs found")
    return candidates[-1]


def render_chunks(chunks_full: list[dict], chunks_used: list[dict]) -> str:
    """Render fragments F1..Fn for the doc.

    Prefer chunks_full (has content); fall back to chunks_used metadata if
    full not available.
    """
    src = chunks_full if chunks_full else chunks_used
    if not src:
        return "_(ningún fragmento recuperado)_"
    lines = []
    for i, c in enumerate(src[:8]):
        pm = c.get("product_model", "?")
        sec = (c.get("section_title") or "").replace("\n", " ").strip()
        sf = c.get("source_file", "?")
        page = c.get("page_number") or c.get("page")
        sim = c.get("similarity")
        content = (c.get("content") or "").strip()
        # Soft cap at 1800 chars per chunk so Alberto isn't drowned in 4500
        # like the judge sees. He's checking reasonableness, not full audit.
        if len(content) > 1800:
            content = content[:1800].rstrip() + "\n[… contenido truncado para legibilidad]"

        header_parts = [f"**[F{i+1}]** `{pm}`"]
        if sec:
            header_parts.append(f"*{sec[:120]}*")
        if sf:
            header_parts.append(f"`{sf}`" + (f" p.{page}" if page else ""))
        if sim is not None:
            header_parts.append(f"sim {sim:.2f}")
        header = " · ".join(header_parts)

        if content:
            lines.append(f"{header}\n\n```\n{content}\n```")
        else:
            lines.append(f"{header}\n\n_(sin contenido almacenado en el log; el bot sí lo vio)_")
    return "\n\n".join(lines)


def render_judge(judge: dict) -> tuple[str, str]:
    """Return (overall_label, criteria_block_md)."""
    if not judge or judge.get("judge_error"):
        return (
            "ERROR",
            f"_Judge falló: {judge.get('judge_error', 'unknown')}_" if judge else "_Sin veredicto del judge._",
        )
    overall = judge.get("overall_pass")
    overall_label = "PASS ✓" if overall else "FAIL ✗"

    def b(k: str) -> str:
        v = judge.get(k)
        if v is True:
            return "True"
        if v is False:
            return "False"
        return "n/a"

    lines = [
        f"- citation_faithful: {b('citation_faithful')}",
        f"- corpus_faithful:   {b('corpus_faithful')}",
        f"- miscitation:       {b('miscitation')}",
        f"- relevant:          {b('relevant')}",
        f"- helpful:           {b('helpful')}",
        f"- honest:            {b('honest')}",
        f"- behavior_match:    {b('behavior_match')}",
    ]
    return overall_label, "\n".join(lines)


def render_case(result: dict, idx: int, total: int) -> str:
    q = result["question"]
    res = result["result"]
    score = result.get("score", {}) or {}
    judge = score.get("judge") or {}

    qid = q["id"]
    cat = q["category"]
    qtext = q["question"]
    expected = q.get("expected_behavior", "answer")
    observed = score.get("observed_behavior", "?")
    keyword_pass = score.get("pass")
    kw_block = score.get("keywords", {}) or {}
    kw_hits = kw_block.get("hits", 0)
    kw_total = kw_block.get("total", 0)
    kw_missing = kw_block.get("missing") or []

    answer = (res.get("answer") or "").strip()
    chunks_full = res.get("chunks_full") or []
    chunks_used = res.get("chunks_used") or []
    chunks_block = render_chunks(chunks_full, chunks_used)
    overall_label, judge_criteria = render_judge(judge)
    rationale = (judge.get("rationale") or "").strip() or "_(sin rationale)_"

    # Pull a 1-line tag from the question 'notes' if it informs the case
    notes = (q.get("notes") or "").strip()
    notes_line = f"\n> _Notas YAML: {notes}_\n" if notes else ""

    # Flag patterns worth Alberto's attention
    flags = []
    if keyword_pass is False and judge.get("overall_pass") is True:
        flags.append("⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil")
    if keyword_pass is True and judge.get("overall_pass") is False:
        flags.append("⚠️ keyword=PASS ∧ judge=FAIL — sospechar judge strict")
    if observed and expected and observed == expected and judge.get("behavior_match") is False:
        flags.append(
            "🐛 BUG candidato: observed==expected pero el judge dice behavior_match=False"
        )
    if judge.get("miscitation"):
        flags.append("🔗 miscitation flag activo — dato puede estar en corpus pero el bot citó mal")
    flags_block = ("\n".join(f"> {f}" for f in flags) + "\n") if flags else ""

    return f"""## {qid} — judge dice **{overall_label}** · ({idx}/{total})

**Pregunta del técnico:** {qtext}

**Conducta esperada:** `{expected}` · **observada:** `{observed}`

**Keyword score:** {kw_hits}/{kw_total} hits · missing: `{kw_missing}` · **keyword_pass:** `{keyword_pass}`
{notes_line}{flags_block}
### Fragmentos que el bot usó (top {min(len(chunks_full or chunks_used), 8)})

{chunks_block}

### Respuesta del bot

```
{answer}
```

### Veredicto del judge: **{overall_label}**

```
{judge_criteria}
```

**Razón del judge:** {rationale}

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

---

"""


def render_header(category: str, count: int, log_name: str) -> str:
    desc = CATEGORY_DESCRIPTIONS.get(category, "")
    return f"""# Calibración del judge v2 — categoría `{category}` ({count} preguntas)

**Origen:** `logs/{log_name}` (eval del 2 mayo 2026).

**Categoría:** {desc}

## Cómo evaluar cada caso

Para cada pregunta lees: **query → fragmentos que el bot vio → respuesta del bot → veredicto del judge**.

1. Verifica mentalmente si cada afirmación del bot está respaldada por al menos un fragmento. Si dice "40 Ω" y un fragmento lo menciona, ok. Si dice "1.5 km con cable 2×1.5" y no aparece en ningún fragmento, mal.
2. Verifica si la conducta observada (responder / clarificar / admitir) coincide con la esperada del YAML.
3. Marca **De acuerdo** o **En desacuerdo** y, si estás en desacuerdo, indica qué dimensión del judge falló (faithful / relevant / helpful / honest / behavior_match) y por qué.

**No necesitas saber PCI**: es lectura comparativa entre lo que dicen los fragmentos y lo que dice el bot.

Los flags **⚠️** y **🐛** que verás arriba de algunos casos marcan patrones sospechosos que Claude detectó automáticamente — úsalos como pista pero no como conclusión.

---

"""


def main() -> None:
    log_path = latest_eval_log()
    log_name = log_path.name
    data = json.loads(log_path.read_text(encoding="utf-8"))
    results = data.get("results", [])

    # Group by category, preserving YAML order (which the runner respects)
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        cat = r["question"]["category"]
        by_cat[cat].append(r)

    written = []
    for cat, items in by_cat.items():
        fname = CATEGORY_FILES.get(cat, f"99_{cat}.md")
        out_path = OUT_DIR / fname
        body = render_header(cat, len(items), log_name)
        for i, r in enumerate(items, 1):
            body += render_case(r, i, len(items))
        out_path.write_text(body, encoding="utf-8")
        written.append((cat, len(items), out_path.relative_to(ROOT)))

    print(f"Built {sum(n for _, n, _ in written)} cases across {len(written)} files from {log_name}:")
    for cat, n, p in written:
        print(f"  - {p}  ({n} casos)")


if __name__ == "__main__":
    main()
