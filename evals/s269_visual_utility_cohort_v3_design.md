# S269 — Cohorte v3 del clasificador de utilidad visual (diseño)

## Por qué existe una v3

S191 corrió el clasificador (gpt-5.6-luna, 60 assets, $0.04, 0 labels inválidos) y cerró
`CLOSED_NO_GO_TRIGGER_OUT_OF_RANGE` con calidad **NOT_MEASURED**
(`evals/s191_visual_utility_classifier_gate_v2.yaml`): el rango preregistrado [10, 30]
positivos estaba desalineado con una cohorte de 48/60 estratos de intención técnica y solo
12 controles de primera página. El resultado NO prueba que Luna sea sobre-inclusiva — prueba
que el trigger no midió nada.

Mandato anti-overfit de S191 (frozen en el gate, se respeta íntegro aquí):

- NO subir el umbral 10-30 tras ver los labels → v3 pre-registra un trigger NUEVO **antes**
  de etiquetar, derivado de la composición, no de los 44 positivos observados.
- NO re-tunear prompt/reasoning sobre los mismos 60 assets → v3 **excluye** los 60 de
  `evals/s191_visual_utility_cohort_v1.json` por `(document_id, page_number)`.
- `freeze_an_independent_control_balanced_cohort_before_any_new_labels` → v3 balancea
  50/50 técnicos/controles y se congela con sha antes de cualquier label.

## Composición (80 assets, balanceada en controles)

| Grupo | Regla de selección | n | Qué se espera |
|---|---|---|---|
| `expected_control` | `page_index <= 2` | 40 | portadas, índices, páginas legales → mayoría `not_useful` |
| `expected_technical` | `page_index >= 5` | 40 | páginas medias/altas de manuales → mayoría con visual técnico |

- Zona buffer `page_index 3-4` excluida de ambos grupos: es la franja ambigua
  (fin de índice / inicio de contenido) y contaminaría la expectativa de composición.
- La regla es POSICIONAL, no de contenido: no usa `content_type` ni texto del chunk, así
  que no hereda el sesgo del chunker ni permite reglas por fabricante/pregunta (contrato
  S190: escala a 30+ fabricantes).
- "Expected" es una EXPECTATIVA de composición para alinear el trigger, NO un gold: el
  label humano/spot-check decide, nunca la regla de selección.

## Fuente y muestreo

- Universo: `evals/s269_visual_assets_bridge_dump_v1.jsonl` (5.096 páginas del bridge
  exacto S190, verificado con tolerancia 0 contra
  `evals/s190_visual_asset_bridge_audit_v1.json`, digest incluido).
- Exclusión: 60 páginas de la cohorte S191 v1 (pools resultantes: 608 control /
  4.201 técnico).
- Muestreo determinista: seed `s269_visual_utility_v3`, score
  `sha256(seed|document_id|page|group)`, round-robin breadth-first por fabricante
  (mismo espíritu que `scripts/s191_freeze_visual_utility_cohort.py`) → 25 fabricantes
  distintos, máximo 5 assets por fabricante en la cohorte resultante.
- Builder: `scripts/build_visual_utility_cohort_v3.py` — solo ficheros locales:
  0 llamadas a modelo, 0 GETs a storage, 0 lecturas/escrituras a DB. Re-ejecutarlo
  reproduce byte-idéntico el `cohort_sha256`.
- Salida congelada: `evals/s269_visual_utility_cohort_v3.json`
  (`cohort_sha256 = bfa829c8d4e2b81816c449c85048be1d9a435fcf0f1ed4a0f8e65b62cb1907e7`).

## Trigger pre-registrado (alineado a la composición)

Con 40 controles esperados-negativos y 40 técnicos esperados-mayoría-positiva, la banda
razonable de positivos estrictos es **35-55% de 80 → [28, 44]** (pre-registro completo en
`evals/s269_visual_utility_cohort_v3_prereg.yaml`). La banda se deriva de la composición
50/50 ANTES de etiquetar — exactamente el control que S191 no tuvo.

## Gate v3 (qué se mide y qué NO)

1. **0 labels inválidos** (mismo contrato de validez que S191 v2).
2. **Positivos dentro de la banda [28, 44]** (política positiva estricta idéntica a S191
   v2: `technical_utility=useful` + `confidence=high` + visual legible + rol en
   `wiring/table/procedure/ui`).
3. **Spot-check manual** (Alberto u orquestador): 10 assets — 5 predichos `useful` +
   5 predichos `not_useful`, muestreo determinista con la misma seed; **cero
   portada/marketing dentro de los predichos useful**.
4. Precisión contra gold humano completo: **NO requerida aún** — es el gate siguiente
   (S190 §Gate: precisión de adjunto >=95% antes de servir). v3 solo decide si el
   clasificador merece ese gate caro.

Ejecución del clasificador: NO incluida en S269 (0 llamadas pagadas aquí). El ejecutor
hereda el contrato S191 v2 (gpt-5.6-luna, `reasoning_effort: none` — mandato
`keep_reasoning_none_unless_a_new_preregistered_disagreement_test_justifies_more`),
re-freezando antes los recibos binarios (fetch → `asset_sha256` del binario → sha del
payload semántico) como hizo S191 con su cohorte. Coste estimado: ~$0.06
(S191 midió $0.04029 por 60 assets; 80 ≈ 60 × 80/60).

## Qué pasa después del gate

- PASS → clasificar el resto del bridge (5.096) con el contrato congelado, poblar
  `visual_role`/`technical_utility`/`classifier_receipt` en `document_visual_assets`
  (migración 014) y recién entonces considerar el flag `VISUAL_ASSETS_REGISTRY` en shadow.
- FAIL por banda → NO re-tunear sobre estos 80: diagnosticar con el spot-check y, si se
  itera, cohorte v4 fresca (regla anti-overfit heredada).
