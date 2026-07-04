#!/usr/bin/env python3
"""s93_gate0_sql.py — genera las sentencias SQL del gate-0 FTS (track A, plan v2/§gate-0).

Una sentencia por pregunta (4 celdas de la matriz pre-registrada dentro, vía CTE):
  {AND, OR} × {con/sin token-modelo}
- AND = `plainto_tsquery('spanish_unaccent', q)` — EXACTAMENTE lo que hace el RPC de
  producción `search_chunks_text_v2` (config canónica de la migración 002).
- OR  = mismo tsquery con '&'→'|' (si la pregunta entera son stopwords → tsquery vacía,
  0 matches, declarado).
- Sustrato = columna `search_vector` REAL (nunca un tsvector fresco).

Salida por pregunta-MISS: total de matches por celda + posición GLOBAL (row_number por
ts_rank desc, tie-break id) de cada chunk-soporte same-family. Evento del plan: pos<=20.
Salida por pregunta-CONTROL: por celda, top-20 solapado con el pool_pin vs top-20 nuevo
(canal redundante vs riesgo-desplazamiento).

Uso: python scripts/s93_gate0_sql.py  → escribe evals/s93_gate0_sql/<qid>.sql
Read-only (SELECT puro); se ejecutan vía MCP execute_sql y los resultados crudos se
archivan en evals/s93_gate0_results.json.
"""
import json
import os
import sys

OUTDIR = "evals/s93_gate0_sql"

MISS_SQL = """-- gate-0 track A · {qid} · {valor!r} (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', {qcon})),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', {qcon})::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', {qsin})),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', {qsin})::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell, 'total' AS what, NULL AS id, count(*)::int AS val FROM ranked GROUP BY cell
UNION ALL
SELECT cell, 'sup', id::text, pos::int FROM ranked WHERE id::text IN ({sup_ids})
ORDER BY 1, 2, 4;
"""

CTRL_SQL = """-- gate-0 track A · CONTROL {qid} (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', {qcon})),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', {qcon})::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', {qsin})),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', {qsin})::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell,
  count(*) FILTER (WHERE pos <= 20 AND id::text = ANY(ARRAY[{pool_ids}])) AS top20_en_pool,
  count(*) FILTER (WHERE pos <= 20 AND NOT (id::text = ANY(ARRAY[{pool_ids}]))) AS top20_nuevo,
  count(*)::int AS total
FROM ranked GROUP BY cell ORDER BY cell;
"""


def lit(s: str, tag: str) -> str:
    """Dollar-quote (evita escapes en preguntas con ¿'/)."""
    assert f"${tag}$" not in s
    return f"${tag}${s}${tag}$"


def main() -> int:
    tb = json.load(open("evals/s93_gate0_testbed.json", encoding="utf-8"))
    os.makedirs(OUTDIR, exist_ok=True)
    # una SQL por PREGUNTA (los hechos de un mismo qid comparten query): une sus sup-ids
    by_q: dict[str, dict] = {}
    for r in tb["rows"]:
        e = by_q.setdefault(r["qid"], {"qid": r["qid"], "question": r["question"],
                                       "qsin": r["question_sin_modelo"], "valores": [],
                                       "sup": {}})
        e["valores"].append(r["valor"])
        for s in r["sup_family_ids"]:
            e["sup"][s["id"]] = r["valor"]
    n = 0
    for qid, e in sorted(by_q.items()):
        sup_ids = ", ".join(f"'{i}'" for i in sorted(e["sup"]))
        sql = MISS_SQL.format(qid=qid, valor="|".join(e["valores"]),
                              qcon=lit(e["question"], "q"), qsin=lit(e["qsin"], "s"),
                              sup_ids=sup_ids)
        open(f"{OUTDIR}/{qid}.sql", "w", encoding="utf-8").write(sql)
        n += 1
    for c in tb["controls"]:
        pool_ids = ", ".join(f"'{i}'" for i in c["pool_ids"])
        sql = CTRL_SQL.format(qid=c["qid"], qcon=lit(c["question"], "q"),
                              qsin=lit(c["question_sin_modelo"], "s"), pool_ids=pool_ids)
        open(f"{OUTDIR}/ctrl_{c['qid']}.sql", "w", encoding="utf-8").write(sql)
        n += 1
    # mapa sup-id → hecho (para leer resultados sin ambigüedad)
    json.dump({q: e["sup"] for q, e in by_q.items()},
              open(f"{OUTDIR}/sup_map.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"{n} sentencias → {OUTDIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
