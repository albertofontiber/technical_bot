# s273 — Autoridad versionada del settled s105 (Fable-M1 del dúo)

Extracto VERBATIM de la sección «Estado anterior (s105 — 10 jul 2026)» de
`docs/PLAN_RAG_2026.md` en el commit de backup pre-Codex. Se versiona aquí para que la
autoridad del settled no dependa de una rama de backup (colisión de numeración DEC-103..105:
`evals/s273_quota_design_v1.md` §7).

**Pins:**
- commit: `33977c15f64705670ce377a9bfeee4cba47a9de2` (rama `codex/s107-wip-backup`)
- blob `docs/PLAN_RAG_2026.md` @ ese commit: `fe7126e41952d5b669a724289aea06e9764af5a9` (git SHA-1)
- sha256 del extracto (utf-8, tal como sigue, sin el fence): `addca176210822fc34587bb040232966238be7c8f7fbba1104377a8446e54792`

---

```
## Estado anterior (s105 — 10 jul 2026)

**s105 (DEC-103) — cuota del canal enunciados construida, revisada y MEDIDA → NO-GO a escala;
tail parado y T1 restaurado.** F1 dedup-at-fusion + F2 cuota N=10 pasaron el gate barato a T1
(109 facts +0/−0; diana 4/4; suite 481), pero tras recargar T2+G0H (49.207 filas; tabla A3 =
71.202) el gate definitivo dio **0 ganancias (<2 → STOP) y 2 anclas perdidas**
(`hp006` Fallo de Tierra + ISO-X), además de served-containment nuevo en cat021/hp005/hp006.
Se ejecutó el rollback contractual: batches T2/G0H a cero, VACUUM HNSW y tabla a **21.995 T1**;
smoke pareado 9 golds/29 facts = +0/−0, hp006 3/3 y diana 4/4. **Tail ~$95 NO gastado.**
R2 queda cerrado bajo esta mecánica; no subir N ni tunear contra hp006. Los dumps Haiku siguen
a salvo para un rediseño futuro. **Qué sigue:** análisis crítico end-to-end pedido por Alberto,
empezando en extracción y terminando en respuesta/eval; después priorizar una cartera de levers
estructurales hacia 95% OK, separando calidad real de técnicos de optimización del benchmark.
```

**Contexto adicional verificado en el mismo commit** (no forma parte del extracto): el código
de la mecánica s105 vive en `33977c1:src/rag/retriever.py:938-978` (entrada-al-sort:
`fused += quota; fused.sort(); results = fused[:top_k]`); el dump T2 completo está VERSIONADO
en ese commit (`33977c1:evals/enunciados_dump_T2.jsonl`, 45.889 filas) — de ahí se extrajo el
slice acotado `evals/s273_t2_hop138_rows_v1.jsonl` (925 filas, extraction_sha256 =
`2964cab7…` = el del ledger).
