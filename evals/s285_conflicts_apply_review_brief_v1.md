# s285 — Brief para revisión adversarial: conflicts-apply (75 documentos, OVERWRITE adjudicado)

## OBJETIVO + MÉTRICA
Corregir en `documents` los valores `doc_type`/`language` adjudicados como ERRÓNEOS
(packet `evals/s285_conflicts_packet_v2.md`, «OK» de Alberto 28-jul + decisión VESDA).
Métrica: integridad de metadatos de identidad (consumidores: autoridad document-local
`language='es'` en `src/rag/document_local_coverage.py:905`, ranking futuro). NO es un lever
de PASS/retrieval-miss — es corrección de datos gobernada.

## QUÉ SE REVISA
1. `scripts/s285_conflicts_apply_gen.py` — generador determinista del SQL.
2. `evals/s285_conflicts_apply_v1.sql` — el SQL que Alberto pegará (staging + guards + audit).
3. Procedencia: `evals/s285_conflicts_frame_v2.json` (80 filas; los valores s83 vienen de
   `evals/s83_document_identity_final.jsonl`, la MISMA fuente que usó el QA s282).

## ALCANCE EXACTO (esperado: 75 UPDATE · 19 doc_type · 64 language set · 1 language→NULL)
- 72 filas `recommendation='s83'` del frame v2 (solo ejes EN CONFLICTO se tocan), con 2
  adjudicaciones de Alberto en el hilo que modifican el eje doc_type (ver
  `ADJUDICACIONES_DOC_TYPE` en el generador): RS232 mixto→NO se pisa (eje retirado);
  Puedo-anular-clave→'operacion' (ni db 'usuario' [fuera de taxonomía] ni s83 'otro').
- VESDA VEP (`33976_13_..._Product_Guide...`): `doc_type='instalacion'` (decisión de Alberto).
- Addendum consistencia (Alberto): VLF-250 + VLF-500 `guia_usuario`→`instalacion` (pisa T2 con
  firma nueva — mismo género Product Guide).
- 1 multi-idioma (`UCIP-Tabla-de-compatibilidad...`, s83=['en','es'], DB='de' falso):
  `language`→NULL (política: sin convención escalar para multi → pool advisory de 209).

## CONTEXTO DE RIESGO (ataca aquí)
- **v1 tuvo un bug real**: el frame v1 tomó s83 de `fill_plan` (null en filas contradict) y 30
  recomendaciones salieron «ninguno» por artefacto; lo cazaron los escépticos del workflow y se
  reconcilió contra la fuente canónica. ¿Queda algún residuo del bug en frame v2 / en el SQL?
- **Semántica del UPDATE**: `doc_type=COALESCE(new, actual)` + `language=CASE clear→NULL |
  COALESCE(new, actual)`. ¿Algún camino escribe donde no debe o deja de escribir donde debe?
- **Guard anti-deriva**: exige valor actual == esperado para CADA eje que se toca. ¿Cubre el eje
  clear? ¿`IS DISTINCT FROM` correcto con NULLs?
- **Conteos**: 75/19/64/1 — verifica contra el frame v2 (66 contradict − 1 doc muerto = 65 eje
  idioma = 64 set + 1 clear; doc_type: s83-rows en conflicto − RS232 retirado + 3 VESDA/VLF = 19).
- **Rollback**: el fichero dice que el frame v2 en git basta para revertir. ¿Es verdad para el
  clear→NULL (el valor viejo 'de' está en el frame)? ¿Y para los 2 VLF (viejo='guia_usuario')?
- Filas `excluded_t3` (4 FAQs): T3 escribió pm/manufacturer en esos docs; aquí se tocan
  doc_type/language. ¿Colisión posible?

## LO QUE NO SE PIDE
No re-litigar la adjudicación (es de Alberto), ni la política multi-idioma (T2, firmada), ni
proponer mecanismos nuevos. Bite = defectos concretos en generador/SQL/procedencia con ancla
fichero:línea.
