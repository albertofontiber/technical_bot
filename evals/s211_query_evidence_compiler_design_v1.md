# S211 — equivalencia schema↔validator y ejecución íntegra nueva

## Por qué existe

S210 terminó `NO_GO_INCOMPLETE_FAIL_CLOSED` tras 126/202 llamadas. La primera
violación fue genérica y upstream: el schema enviado al proveedor no declaraba
`maxItems`, mientras el validador local rechazaba más de 16 claims. Haiku devolvió
17 claims válidos para el schema y el runner se detuvo correctamente. No hubo
score, crédito de facts, retry ni resume.

S211 corrige exclusivamente esa divergencia contractual. El schema v2 declara
`maxItems: 16` usando la misma constante del validador, y el entrypoint v2 vuelve
a validar el schema antes de ligar spans. No cambian el system prompt, modelos,
temperatura/esfuerzo, fallback, planner, verifier, compilador, scorer, cohorte,
réplicas, thresholds ni presupuesto.

## Integridad frente a la exposición previa

S211 no consume ninguna respuesta S210. Ejecuta las 202 llamadas desde cero y
no permite resume/retry. El target tuvo exposición operacional parcial: se vieron
conteos y el primer output inválido, pero no se abrió el gold, no se ejecutó el
scorer y no se inspeccionaron respuestas para cambiar semántica o selección. La
única corrección se demuestra con tests sintéticos de frontera 16/17 y no contiene
IDs, fabricantes, modelos, preguntas, valores ni facts target.

Esta repetición no es evidencia fresca de generalización y no se presentará como
tal. Su único propósito es obtener una matriz completa y comparable bajo el
mecanismo que Sol 5.6 xhigh y Fable 5 ya revisaron conceptualmente como acotado.
Un nuevo gate Frontier compacto debe además aceptar explícitamente que la
re-ejecución íntegra, con esta única corrección contractual, no crea un falso GO.

## Ejecución y decisión

Se heredan sin cambios la población de cuatro targets más 14 guardrails, las dos
réplicas, las 130 extracciones, 36 planes y 36 verificaciones, el techo conservador
previo a primera llamada y todos los gates S210. El GO local sigue exigiendo al
menos 11/12 relaciones residuales estables, al menos 4/5 de `hp017`, cero
regresiones y contradicciones cardinales nuevas, evidencia precisa, citas válidas,
prefijo exacto, apéndice acotado y coste bajo techo.

Un GO local mueve cero facts y abre una única revisión atómica Sol 5.6 xhigh +
Fable 5. Solo su acuerdo sobre al menos 11 facts permite la proyección diagnóstica
154/157. Runtime continúa sin cablear y default-off hasta validación externa real.
Un NO-GO o una nueva ejecución incompleta cierra S211 sin ajuste ni nueva llamada.

## Invariantes

- `chunks_v2` activo y read-only; cero escrituras de base de datos.
- `chunks_v3` permanece `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`.
- Railway no bloquea PR/merge con CI verde.
- No se generan preguntas o golds nuevos.
