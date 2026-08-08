# s312 — Propuesta a atacar: el PACKET B2 de gold-review (pre-sentada de Alberto)

Objeto: `evals/s294_goldreview_b2_packet_v1.md` — 10 ítems con recomendación del autor
para la adjudicación EN LOTE de Alberto. GO explícito de Alberto para esta ronda: el dúo
afina evidencia y recomendaciones ANTES de que él gaste sus ~30 min de sentada.

## FRONTERA DEL MANDATO

Ataca EVIDENCIA y RECOMENDACIONES. NO decidas golds (DEC-025: el gold es de Alberto);
varias preguntas son de criterio de técnico PCI. Tu output por ítem: evidencia
viva/stale/mal-citada + si la recomendación se sostiene + opciones ausentes. La marca ya
puesta de Alberto en el ítem 1 es INTOCABLE.

## QUÉ VERIFICAR (los 10 ítems)

1. **Citas vs recibos**: cada medición citada (FULL v3.2, sondas s293, respuestas
   congeladas, posiciones de serving) contra su recibo REAL en `evals/` — lee el recibo
   ENTERO (lección s293: evidencia truncada induce críticos falsos).
2. **Staleness**: el packet nació en s294; desde entonces: 2 manuales EN ingestados
   (s303), backfill de `documents.product_model` aplicado en PROD (s308), y el generador
   de producción es **Opus 5 desde s308** — las «respuestas congeladas» del packet vienen
   del generador ANTERIOR. ¿Qué ítems tienen premisas desactualizadas? (El ítem 9 ya
   sufrió una corrección de esta clase.)
3. **¿La recomendación se sigue del recibo?** — en los 2 ítems donde el autor DISCREPA
   del triage s291c, ¿quién tiene razón según la evidencia?
4. **Opciones ausentes** en las decisiones planteadas.
5. **Ítem 10 (s305)**: cifras contra `evals/s305_techo_modelo_ab_v1.json`; ¿la lectura
   «los 3 modelos eligen el default» se sostiene leyendo las respuestas guardadas?

## SALIDA

Por ítem: veredicto de evidencia + hallazgos con ancla + recomendación
sostenida/no-sostenida. Final: ítems a corregir ANTES de la sentada, por gravedad.
