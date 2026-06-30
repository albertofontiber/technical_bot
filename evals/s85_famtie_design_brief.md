# s85·B0 Fase 0.5 — DISEÑO del family-tie + pin del pool (dúo ANTES de aplicar)

**Qué reviso (Protocolo 3, zona de dolor retrieval):** el upgrade del árbitro = (a) pin del pool en el
instrumento + (b) re-derivación FAMILY-AWARE del retrieval-miss. La DECISIÓN está tomada (Alberto: el tie
por filename-token acredita mal — by-target acreditó hp018 vía un manual de FAMILIA equivocada que coincide
por casualidad). El dúo audita que la IMPLEMENTACIÓN sea correcta, robusta y no introduzca FN/FP.

## Contexto (no re-litigar)
- by-target acreditó los 5 hechos de hp018 vía `MIE-MI-310` (familia `ZXAE/ZXEE`) para una pregunta de
  ZXe (`MIE-MI-530` = `ZX2e/ZX5e`) — producto DISTINTO, coincide por azar = ERROR (ground-truth de Alberto,
  confirmado en corpus: MI-310→ZXAE/ZXEE, MI-530→ZX2e/ZX5e).
- El tie correcto = "¿el chunk-soporte es de la MISMA FAMILIA de `product_model` que el gold?".
- retrieval-miss FAMILY = hecho CORE con soporte del juez (≥4/5) pero SIN chunk same-family en el pool.

## El cambio (2 piezas)
1. **Pin del pool** (`retrieval_miss_judge.py`, return de `measure_gold`): guarda `pool_pin`/`top5_ids`/
   `manual_pin` (id+product_model+source_file por chunk). → la re-derivación es EXACTA (no re-retrieve →
   mata el ruido del pool-jitter que dio el falso flip de hp001 '2222'). El juez NO cambia (solo se añade
   metadata al output). PIN = barato y seguro.
2. **`retrieval_miss_famtie.py`** (re-derivación, SIN GPT): por hecho, `bucket_family` vía `classify` sobre
   in_top5_fam/in_pool_fam, donde "same-family" = `fam_norm(chunk.pm) ∈ gold_family`. `gold_family` resuelve
   la familia del gold desde sus tokens primario/target con FALLBACK de source-naming (clase DEC-065):
   - guion-normalizado (`MN-DT-722`→`MNDT722`),
   - strip de sufijo de revisión (`MNDT722_B`→`MNDT722`) + core alfa+dígito,
   - token descriptivo distintivo del fuente para nombres sin dígito (`DXc`), con stop-list anti-genéricos.
   `fam_norm` colapsa variantes `40-40L/U/R/M/I`→`40-40`.

## Verificado (regla C — verifícalo, no lo asumas)
- `gold_family` resuelve bien los 6 golds clave: hp018→ZX2E/ZX5E, hp001→CAD-250, cat020→DXC, cat021→40-40,
  cat022→40-40 (suffix-fix), hp010→DXC (stop-list-fix). Los 2 bugs iniciales (cat022 vacío, hp010 over-match)
  ya corregidos.
- El pin se puebla (smoke cat005: pool_pin=50, top5=5, manual=11, n_fail=0).

## Lo que el dúo DEBE atacar
1. **¿`gold_family` mete FP/FN en un gold CON MISS?** Los 4 source-naming (cat020/21/22, hp010) son all-found
   (sin miss) → su resolución imperfecta es benigna para el conteo. Pero ¿algún gold con RETRIEVAL-miss
   (hp018, cat013/016/018, hp002/006/009/011/012/014/017…) tiene su familia mal resuelta → flip espurio?
   Revisa la resolución de los miss-golds, no solo los 6 de muestra.
2. **¿`fam_norm` colapsa de más/menos?** El colapso `40-40*`→`40-40` agrupa variantes legítimas (40-40L/U/R/M),
   pero ¿hay familias donde colapsar variantes sea INCORRECTO (variantes que SÍ son productos distintos con
   specs distintas, p.ej. ZX2e vs ZX5e dentro de ZX2e/ZX5e)? ¿El tag `ZX2e/ZX5e` ya viene combinado del corpus?
3. **¿La re-derivación es realmente exacta?** Usa `pool_pin` (no re-retrieve). ¿Algún caso donde un chunk
   votado no esté en pool_pin ni manual_pin (p.ej. votado en una etapa pero no pinneado)? ¿`same_fam` lo
   maneja (devuelve False si no encuentra el chunk)?
4. **Meta-fact exclusion**: se excluye 'manual de variaciones Espana' (cat020) por ser meta-referencia, no
   dato. ¿Es legítimo o ad-hoc? ¿Hay OTROS hechos meta-referencia que deberían excluirse igual?
5. **¿El tie family-aware es la métrica correcta, o sobre/infra-corrige?** by-target=15, by-primary=22,
   family≈15-16. ¿El family-aware puede ENMASCARAR un miss real (familia resuelta de más → acredita un
   chunk que no debería)? El sesgo peligroso es DESINFLAR el miss.
6. **Source-naming como workstream**: el fallback es un parche para B0; la resolución limpia gold↔corpus es
   DEC-065 (aparte). ¿El parche es suficiente para no contaminar el número, o hay riesgo de que falle
   silenciosamente en un gold con miss?

## Gaps declarados
- Resolución source-naming imperfecta en los 4 golds descriptivos/sufijo (benigna: all-found).
- `fam_norm` colapsa 40-40* (asumido correcto: son la serie 40/40); revisar si hay colapsos incorrectos.
- Superseding/revisión NO se filtra en el manual-fetch (workstream aparte, DEC-058); el pool sí lifecycle-filtra.
