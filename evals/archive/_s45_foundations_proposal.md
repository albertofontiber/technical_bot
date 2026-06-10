# Propuesta s45 — Cimientos F1 (BP/determinismo/legibilidad) + F2 + audit. Autor = Claude. (dúo, Protocolo 3)

> Atácala: ¿son cambios "sí o sí por BP" o lever-hunting disfrazado? ¿determinismo = BP o instrument-obsession?
> ¿regresión al cambiar el reranker? ¿F2 bien dimensionado? Verifica contra código (regla C). Bite, no ritual.

## Contexto
El gate de s45 (source-anchored, verificado) concluyó: **F1 no tiene lever de CALIDAD limpio** (síntesis genuina ~2-4 casos
dispersos; recall no convierte, TECH_DEBT:1246; los FALLO peligrosos cerrados por retrieve-wide). Alberto reencuadra: ¿qué
CIMIENTOS BP valen la pena AUNQUE el delta de calidad sea pequeño (robustez/escala/legibilidad/determinismo)?

## Q1 — Mejoras F1 "sí o sí" (cimiento, no delta de calidad)
**Principal = el RERANKER es un anti-patrón RAG:** un LLM (Sonnet) que se pide a sí mismo, lee SÓLO 800 chars/chunk
(`reranker.py:56`), NO-determinista (DEC-005 — **la fuente del ruido de medición que costó media sesión**), caro (~3-7× latencia).
BP = **cross-encoder dedicado** (Voyage rerank, YA cableado `rerank_chunks_voyage:178`, lee el doc completo `[:4000]`).
- Beneficio = **CIMIENTO**: determinismo (↓ruido de eval), lee chunk completo, +barato/rápido, escala 30+. **NO calidad**
  (TECH_DEBT:1246 dijo que como lever-de-calidad no convierte — pero como cimiento determinista/BP/coste, sí).
- **GAP:** el reranker-LLM tiene domain-awareness (tags `[DIAGRAMA DISPONIBLE]` `reranker.py:53` + prioridad-modelo). La
  prioridad-modelo es guarda AGUAS ARRIBA (se conserva); la surfacing de diagramas vive en el prompt del reranker → al pasar a
  Voyage hay que reubicar ese boost upstream o se pierde. No es win puro. Vara = **no-regresión** (2 ejes), no mejora.
- Secundarias: **HyDE-OFF** (ya decidido, determinismo) + **endurecer el harness** (estampar config + frontera-de-dígito en el
  matcher del funnel, `_chunk_has`).

## Q2 — Legacy a eliminar para ver mejor qué falla
Tema = **quitar estocasticidad + cruft → señal limpia:**
1. **Cruft de scores planos (#32):** constantes mágicas 0.65/0.80/0.85 (`retriever.py`) entierran matches vectoriales reales
   (hp019). retrieve-wide lo SORTEÓ, no lo borró → sigue oscureciendo el retrieval. Limpiar → rankear por coseno real.
   **CONSERVAR las guardas** (filtros modelo/categoría — anti-alucinación cross-product, TECH_DEBT:1250).
2. **Componentes estocásticos no-BP:** HyDE(→off) + reranker-LLM(→Voyage) = −2 fuentes de no-determinismo → más claro qué falla.
3. **Sprawl de eval:** ~8 harnesses solapados (run_eval/eval_rag/run_ragas/test_bot_vs_gold/atomic_scorer/factual_gate/gate…).
   Consolidar a UNO canónico (per-hecho, determinista, config-estampada).
- **GAP:** la tabla `chunks` vieja (OpenAI-1536) = rollback del SWAP → NO tocar hasta que F2 estabilice.

## Q3 — F2 (escala)
Bot **manufacturer-agnóstico por DATOS, no por código:**
- **MODEL_PATTERN regex hardcoded** (`retriever.py`, ~50 líneas/3 fab) → **catálogo data-driven** (`catalog.json`/`build_model_catalog.py`).
- **CATEGORY_TERMS / filtros hardcoded** → data-driven.
- **Pipeline de onboarding** repetible (download→ingest LlamaParse→registrar catálogo→verificar) SIN tocar código.
- **Test medible user-independent:** "¿un fabricante held-out funciona sin cambiar código?" = la vara de F2.
- **GAP:** esfuerzo de F2 sin dimensionar; el audit + el dúo lo afinan.

## Q4 — ¿Auditar los 14? SÍ, REFRAMEADO
No para "encontrar un lever" (perfeccionismo) sino para **MAPEAR modos de fallo** (retrieval-contexto / síntesis-genuina /
chunking / scoring-plano / suelo) → **qué cimiento (Q1/Q2) lo justifica un patrón REAL.** Ej: si N/14 fallan por "el dato se
enterró bajo scores planos" → justifica limpiar el cruft; si M/14 por "tabla partida en el chunking" → justifica fix de ingesta.
Es el PUENTE entre "no hay lever" y "qué cimientos construir". Acotado (el audit, no sin fin).

## TESIS de convergencia (atácala)
Q1+Q2+Q4 convergen en UN rumbo coherente: **determinizar + limpiar + hacer LEGIBLE el pipeline de retrieval** (Voyage reranker,
HyDE-off, scores limpios, un eval canónico), **informado por el audit de modos-de-fallo de los 14**, y LUEGO **F2-escala**.
Construye cimientos + arregla la raíz del ruido de medición (que costó media sesión) + prepara escala — justificado por
BP/robustez, NO por delta de eval ruidoso. ¿Es esto BP sólido o es otra pila de cambios / instrument-obsession?

## Preguntas para el dúo
1. ¿El Voyage-reranker es BP-vale-la-pena o cambio un componente domain-aware por uno genérico (regresión)? ¿El gap de diagramas es dealbreaker?
2. ¿"Quitar estocasticidad" es RAG BP legítimo o instrument-obsession (la queja de Alberto)? ¿Dónde está la línea?
3. ¿Cuáles de Q1/Q2 son VERDADERAMENTE "sí o sí" (independientes del delta) vs cuáles necesitan medir mejora antes?
4. ¿El audit de los 14 es foundation-informing legítimo o perfeccionismo disfrazado? ¿Cómo acotarlo?
5. ¿F2 está bien planteado? ¿Orden correcto (cimientos F1 → F2) o F2 ya, dado sin-usuarios?
6. ¿Falta un cimiento BP obvio? (contextual-retrieval, semantic chunking, retrieval-eval recall@k separado, etc.)

## Contrato
BP + estructural (raíz) + escalable (30+ fab, ES/EN) + cada cambio justificado como cimiento-vs-delta + gaps declarados.
