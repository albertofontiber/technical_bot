# s41 — DIFF a atacar (Protocolo 3 ronda 2: implementación, no diseño)

El diseño (`_s41_contracts_proposal.md`) ya pasó la ronda 1 del dúo (SÓLIDO-CON-CAMBIOS). Se cableó
el **corte acordado** en `scripts/atomic_scorer.py` (ver `git diff` adjunto) + `tests/test_atomic_scorer.py`
(nuevo, contexto explícito). Atacad la IMPLEMENTACIÓN, no el diseño otra vez.

## Qué se implementó (el corte del dúo)
1. **C1 — ramificar por estado-del-hecho**: `score_gold` separa `present_rows` (estado != ausente-probado)
   de los `ausente-probado`. La completitud se calcula SOLO sobre present_rows core. Los `ausente-probado`
   NO cuentan en el denominador (antes caían a `core_manual` por valor=null; ahora se excluyen explícitamente
   por estado). Esto cubre el patrón D5 (ausente-probado dentro de un `answer` mixto: hp006/09/13).
2. **Eje NO-FABRICACIÓN** (`undue_inference_check`, gated en `--llm`, cross-model GPT-5.5, binario,
   conservador): caza que el bot AFIRME un hecho `ausente-probado` (compatibilidad/valor/recomendación/
   inferencia). Asimetría de seguridad: afirmar un ausente = FALLO. Aplica a TODO hecho ausente-probado,
   no solo admit/refuse (por eso va por-hecho, no por conducta_esperada).
3. **refuse-inference entra en `ANSWER_LIKE`**: deja de caer a REVISAR; su fallo típico lo caza ahora el
   eje no-fabricación. Comentario actualizado.
4. Sin `--llm`, el camino es byte-idéntico al anterior (eje gated) salvo notas auxiliares.

## Atacad en particular (regla C: verificad contra el código real)
- ¿El orden del veredicto respeta la asimetría de seguridad? (factual_error → inference_error →
  contradictions → undue_inferences → gate). ¿Algún caso enmascara un FALLO?
- ¿La ramificación por `estado` rompe la no-regresión de los 16 golds SIN ausente-probado? ¿Y de los 3 CON?
- ¿`undue_inference_check` tiene el mismo contrato que `factual_check` (éxito→([...],None); fallo→([],err))?
  ¿El gating en `--llm` (no en `client`) es correcto, como el bug ya cazado en el factual?
- El prompt `_UNDUE_SYS`: ¿es lo bastante específico para cazar inferencia indebida sin falsos positivos
  sobre un bot que surfacea hechos por-producto SIN inferir? ¿Conservador de verdad?
- ¿Los tests cubren los casos límite, o hay un agujero (p.ej. ausente-probado con valor no-null)?
- ¿Hay algún claim de los comentarios nuevos que sea falso contra el código?
