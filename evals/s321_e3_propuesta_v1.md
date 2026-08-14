# s321 E3 — Re-tag F3a: propagar la identidad ADJUDICADA a los chunks — v2 (tras dúo r24)

> **v1→v2 (dúo r24: Sol 5 — 3 críticos — · Fable 4; 1 FP de Fable, el PRIMERO en 13
> rondas, documentado abajo):**
> 1. **Censo v2 con la puerta `_consumable`** (Sol C1 + Fable C1): candidates
>    (APIC), ids `unresolved:*` y redirects fuera del lote; y la partición
>    ADJUDICADO/DERIVADO se LEE de la provenance de cada entry (evidenciada,
>    no afirmada).
> 2. **Writer al patrón T3 EXACTO** (Sol C2): backup por-chunk (id +
>    `product_model_prev`) + update condicional compare-and-swap (WHERE pm =
>    prev) + conteos esperados verificados; el rollback restaura por id.
> 3. **Gate PRIMARIO = FINDABILITY** (Sol C3, contrato §F3): sonda positiva
>    pre/post — los 161 recuperables por su término canónico Y los términos de
>    familia útiles (DEC-192/193) conservando alcance A NIVEL CHUNK; el
>    sweep-39 queda como no-regresión, no como evidencia.
> 4. **Coherencia por la semántica del FILTRO** (Sol M4): `model_to_imatch_pattern`
>    (no normkey, que tira la «/»: ID/3000 vs ID-3000 censados coherentes pero
>    irrecuperables) — el censo v2 re-clasifica con el regex real.
> 5. **Contabilidad TOTAL** (Fable M3): 887 = suma exacta de buckets (los 72
>    descartes silenciosos del v1 salen a recibo con su clase).
> 6. **Freeze con hashes** (Sol M5) + diff E2-POST pre-registrado POR DOC
>    (Fable m4: sin pre-registro, el gate es ritual).
> 7. **FP documentado (regla C con el texto delante)**: la cláusula «pm JAMÁS
>    auto» SÍ existe — DEC-156(b), DECISIONS.md:3651 («v2 re-gating por
>    write_op (548; pm JAMÁS auto)») — el grep de Fable la perdió por
>    línea-kilométrica omitida del output. Mecanismo anotado para el tally.

**Marco**: fase E3 del elefante (plan v2, dúo r20). Contrato §F3: SOLO
mono-producto (multi = multi-valor/paraguas, JAMÁS colapso — 272 censados y
fuera); F3b por-página sigue gated out-of-scope. Precedente: T3 s285 (DEC-161,
221 chunks re-tagueados CON adjudicaciones).

## Censo (recibo `evals/s321_e3_censo_v1.json`, solo-lectura)

**161 docs mono-producto** (3.928 chunks) cuyo pm de chunks ≠ `canonical_model`
del producto adjudicado en doc_map · 382 ya coherentes · 0 sin chunks.

## Diseño del writer (dry-run → recibo → aplicar)

1. **Lote ADJUDICADO** (provenance de la entry = s83/adjudicación/DEC-150…):
   `UPDATE chunks_v2 SET product_model = canonical_model WHERE document_id = X`
   — propaga identidad YA adjudicada (el precedente T3 exacto). Reversible:
   el recibo guarda pm-viejo por chunk_count y el rollback es re-aplicar.
2. **Lote DERIVADO** (provenance = s320-e1 derivación tier-A, mis 26): NO se
   auto-aplica encima de mi propia derivación (sería auto-consumo sin
   adjudicación, la clase que DEC-156b «pm JAMÁS auto» veta) → packet.
3. `documents.product_model` NO se toca aquí si difiere con función (la
   convención lista-con-barras de familia es findability, DEC-192/193): el
   re-tag es de CHUNKS; cualquier doc-level va a packet con diff.
4. **Gates**: dry-run con recibo por-doc · sonda de equivalencia del detector
   E2 re-corrida POST (el snapshot derivado atesta por pm: el re-tag lo mueve
   — diff esperado y explicado, no silencioso) · sweep-39 composición ·
   suite completa. Freeze-contract con catálogo-commit.

## Gaps declarados

- El re-tag cambia la señal pm que consumen model-filter/hyq family-parity:
  el gate de composición es el árbitro (si un gold cambia, STOP e investigar).
- La normalización de comparación es normkey (la del filtro): un pm distinto
  en forma pero igual en normkey NO está en la lista (ya-coherente).
- Los 272 multi quedan censados para F3b/paraguas (fase posterior, gated).
