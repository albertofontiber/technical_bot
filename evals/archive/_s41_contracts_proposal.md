# Propuesta s41 (B2) — Contratos de conducta: `admit` y `refuse-inference`

> Diseño a batir adversarialmente (Protocolo 3) ANTES de cablear. Impacto MEDIO en zona de
> dolor (scorer/conductas del ruler) → dual: sub-agente Claude (ancla en código) + cross-model.

## 0. Contexto (qué es el ruler y dónde estamos)
El ruler es un instrumento DIAGNÓSTICO (no gate estadístico) que mide al bot RAG leyendo la
FUENTE al píxel, independiente del sustrato del bot (RULER_DESIGN §0). Tiene 5 conductas
(RULER_DESIGN §1): `answer`, `answer-con-conflicto`, `clarify`, `admit`, `refuse-inference`.
La conducta de cada gold se DERIVA de la localización en el corpus, no del system prompt (D2).

Estado: s40 consolidó el árbitro (fix matcher de rangos, DEC-011). s41 crece el catálogo con
golds de CONDUCTA (celdas #16 admit, #18 refuse-inference, #19 clarify). Los **contratos
refuse/admit fueron DIFERIDOS en s39** (DEC-010 §3) — esta propuesta los especifica. `clarify`
(#19) NO necesita contrato nuevo (ya cubierto por `detect_conducta`+gate y RULER_DESIGN/D6).

## 1. Hallazgo que enmarca los dos contratos
El eje FACTUAL del scorer (`atomic_scorer.py:105-153`, `factual_check`) es **solo-contradicción**:
marca FALLO si el bot afirma un valor que CHOCA con un hecho verificado. Pero cuando el corpus
está VACÍO sobre un tema, no hay hecho que contradecir → **si el bot fabrica sobre ese vacío, el
eje factual NO lo caza**. El propio código lo declara pendiente (`atomic_scorer.py:57-60`:
"fabricar compatibilidad cross-brand SIN contradecir un hecho listado — el eje factual
(contradicción-only) NO lo caza → cae a REVISAR"). Este agujero es COMÚN a `admit` y
`refuse-inference`: ambos son conductas "sobre el vacío".

Hoy en el scorer (`score_gold`, `atomic_scorer.py:201-294`):
- `admit`: `expected=="admit"` y bot admite → PASS; bot responde → "REVISAR (responde donde el
  gold admite)". El discriminador `hedged_admit` (admite-fraseo pero entrega core p>0) ya existe.
- `refuse-inference`: NO está en `ANSWER_LIKE` ni en `_LEGACY` ni en `detect_conducta` → SIEMPRE
  cae al `else` del gate → "REVISAR (conducta bot=… != esperada=refuse-inference)". Juicio humano.

## 2. Mecanismo de scoring compartido (el núcleo nuevo)
Un **check de "afirmación-indebida sobre hecho `ausente-probado`"**, simétrico al `factual_check`
pero para AUSENCIA. Cross-model (GPT-5.5, distinto del bot-Sonnet), acotado y binario:
> "El manual NO documenta «X» (hecho ausente-probado). ¿La respuesta del bot AFIRMA «X» o un
> valor/comportamiento concreto para X, o lo ADMITE/REDIRIGE al fabricante?"
- bot afirma X → **FALLO** (fabricación sobre vacío; asimetría de seguridad, RULER_DESIGN §3).
- bot admite/redirige → PASS en este eje.
- Conservador: ante duda NO marca fabricación (preferir falso-negativo, como `factual_check`).

## 3. Contrato A — `admit` / `ausente-probado`
**Autoría (carga de prueba de ausencia, la MÁS ALTA — D5):** grep de TÉRMINOS del tema (no valor;
ES+EN) en TODOS los manuales del producto. Se concluye `ausente-probado` SOLO si: (i) ningún
manual digital-native cubre el tema, Y (ii) los manuales-scan relevantes se han RENDER-verificado
(regla de scans, RULER_DESIGN §2: grep≈0 en scan NO es ausencia). Distinción:
- tema en NINGÚN manual → `admit` legítimo.
- tema en el manual pero NO en chunks_v2 → `corpus_gap` (no fallo del bot; lever de extracción
  #10). `locate_fact.py` ya emite `corpus_gap` (`:509-510`).

**Scoring:** `expected==admit`. PASS si el bot reconoce el gap SIN inventar (gate de conducta YA
existente + el check §2 sobre los hechos `ausente-probado`). FALLO si afirma un valor para el
tema ausente. Refuerza el camino actual `admit` con el check §2 (hoy un bot que fabrica un valor
plausible al "admitir" puede colarse porque el factual no tiene nada que contradecir).

## 4. Contrato B — `refuse-inference` (cross-brand Notifier↔Detnov)
**Autoría:** los hechos del gold son (i) hechos `presente` por-producto (specs de cada marca, que
el bot SÍ debe surfacear) + (ii) un hecho `ausente-probado` = "no hay documentación de
compatibilidad/interoperabilidad cross-brand". Carga de prueba: buscar términos de
compatibilidad en el universo documental de AMBAS marcas (`--manuals` explícito de las dos +
sugeridor filesystem). Si ninguna lo documenta → `refuse-inference` legítimo.

**Scoring:** `expected==refuse-inference` deja de caer a REVISAR. PASS si: completitud sobre los
hechos `presente` (da los specs por-producto) ∧ check §2 sobre el `ausente-probado` (no afirma
compatibilidad) ∧ (redirige al fabricante = TONO, no se gradúa duro). FALLO si afirma
compatibilidad/incompatibilidad como hecho.

## 5. Cambios de código
1. **`locate_fact.py`**: añadir **modo-ausencia** (input = términos sin valor → clasifica cada
   manual digital/scan → veredicto `absence_proven` / `needs_human` (si hay scans sin
   render-verificar) / `corpus_gap`). Reutiliza `grep_pdf`, `_scan_ratio`/`is_scan`, `corpus_has`.
2. **`atomic_scorer.py`**: (a) función nueva `undue_inference_check` (cross-model, §2), gated como
   `--llm`; (b) en `score_gold`, para `expected ∈ {admit, refuse-inference}`: completitud sobre
   los `presente` + el check §2 sobre los `ausente-probado`; refuse-inference sale del `else`→REVISAR.

## 6. DECISIÓN PENDIENTE (sobre la que quiero vuestro juicio explícito)
¿El check §2 (afirmación-indebida) se construye como **check LLM cross-model** (endurece el eje
conducta, escala a la clase entera, valida a 30+ fabricantes; se spot-checkea con el humano), o
se deja el **fallback humano** (`admit`/`refuse-inference` → REVISAR, sin código nuevo en el
scorer; el humano es el gate de cada conducta; cero riesgo de check mal calibrado pero NO escala)?
Mi recomendación: check LLM cross-model, por estructural + escalable; el fallback humano es el
suelo seguro si el spot-check no valida el check.

## 7. Alternativas descartadas
- **Solo keywords** (status quo `_NOINFO`/`_CLARIFY`, `atomic_scorer.py:62-66`): frágil
  (el bot puede fabricar sin frase de admit, o admitir-parte-e-inventar-otra); no maneja refuse.
- **Colapsar refuse→admit**: refuse SÍ entrega contenido (specs por-producto); colapsarlo perdería
  la medición de completitud de los `presente` y confundiría el gate.
- **Dejar refuse en REVISAR para siempre**: es el fallback seguro (=opción B de §6), pero renuncia
  a endurecer el eje, que es el objetivo de s41.

## 8. Gaps declarados (de entrada)
- (a) El check §2 es LLM cross-model → no-determinista, n pequeño → señal CATEGÓRICA, no delta
  fino (igual que el eje factual); se valida con spot-check humano en los golds autorados.
- (b) Probar ausencia exige manuales digital-native o render-verificados; si el producto de #16
  solo tiene scans del tema → `needs_human` (restricción de SELECCIÓN de celda, no del contrato).
- (c) refuse cross-brand: el universo es tan exhaustivo como los `--manuals` sembrados; un manual
  de compatibilidad omitido daría un falso refuse (mitigación: sembrar exhaustivo + podar).
- (d) Frontera difusa "surfaceó specs y sugirió consultar" (PASS) vs "afirmó compatibilidad"
  (FALLO) → puede ser sutil; spot-check humano en los golds de conducta.
- (e) `refuse-inference` y `admit` con hechos `presente`: ¿el gate exige completitud de los
  `presente` para PASS, o basta no-fabricar? Propuesta: exige AMBOS (da lo documentado ∧ no
  inventa) — pero esto endurece; ¿demasiado para n pequeño?
