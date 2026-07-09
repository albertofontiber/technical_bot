# s99 · Pre-registro — Piloto de HYPOTHETICAL QUESTIONS (lado-pregunta) — PARA EL DÚO

> Autónomo, GO de Alberto. **Objetivo del PILOTO**: caracterizar si generar preguntas-hipotéticas
> por chunk (question-side, HyPE/HyQE) y añadirlas como surrogates cierra el gap de vocabulario
> query↔celda en NUESTRO corpus — MEDIDO en un slice, sin shipear. NO es caza de PASS (el residual
> retrieval ya es bajo); es prueba de MECANISMO + de que el activo es sano para findability futura.

## Encuadre honesto (declarado de entrada)
- **Valor con 0 técnicos**: el PILOTO sí (barato, caracteriza el mecanismo); el relleno corpus-wide
  NO hasta gatillo (técnicos o ganancia medida) — mismo criterio que catálogo-identidad y A3.
- **Distinto de A3 (SHIPPED)**: A3/enunciados = lado-RESPUESTA (afirmaciones declarativas, no cierra
  el gap de vocabulario). hyq = lado-PREGUNTA (question↔question). Complementario, señal NUEVA.
- **NO re-litiga consumo-aditivo (DEC-069/L22)**: no une chunks al pool por identidad ni desplaza;
  añade surrogates-pregunta que apuntan al MISMO chunk (patrón A3, tabla separada, colapso a padre).
- **Límite de alcance declarado**: es fix de RETRIEVAL/matching. NO toca el synthesis-drop (el
  generador que no escribe un dato que ya tiene). No se le pide PASS; se le pide famtie.

## Mecanismo — TABLA-PILOTO SEPARADA (fix dúo crítico: aislamiento estructural, no procedimental)
- **NO reusar `chunks_v2_enunciados`** (el RPC `match_chunks_v2_enunciados` NO filtra por batch/origin
  → una fila hyq ahí se serviría a la demo si alguien activa el flag; verificado mig. 012). En su
  lugar: **tabla-piloto NUEVA `chunks_v2_hyq_pilot`** con su propio HNSW + su propio RPC (o medición
  solo-offline en el harness, sin RPC vivo) → el canal A3 SHIPPED **físicamente no puede alcanzarla**.
  Aislamiento por CONSTRUCCIÓN, no por disciplina de borrado. **Es DDL NUEVO** (no "reuso mínimo de
  A3" — corrijo el framing): tabla + índice + columnas `origin` (synthetic|real) y `surrogate_type`.
- Patrón de A3 conservado: `parent_id`→chunk real, colapso Dense-X keep-max, invariante de no-servicio.
  **Traceability (fix dúo)**: el colapso debe registrar QUÉ pregunta-surrogate ganó cada padre + su
  `origin` → poder diagnosticar realista-vs-genérica y podar sintéticas después (el colapso A3 actual
  solo guarda `_swapped_from_surrogate` del primero — hay que extenderlo o loggear aparte en el piloto).
- **Generación** (pipeline enunciados adaptado, `LLM_MODEL` Sonnet-class, offline):
  prompt = "genera 2-4 preguntas que un técnico de PCI en campo haría y que ESTE fragmento responde;
  registro llano/coloquial, incluye el modelo/producto exacto; sin markdown". Dedup + cap por chunk.
- **Few-shot NO-CIRCULAR (fix dúo, = Q3 de Alberto)**: calibrar el registro con `query_logs` reales
  (si hay) **o con preguntas gold de golds FUERA del slice de medición** — NUNCA con las preguntas de
  los golds que luego mido (sería fuga: sesga los surrogates hacia la forma sintáctica del instrumento).
  Es un TRADE-OFF declarado, no una mitigación resuelta: si no hay registro real limpio, el piloto mide
  "¿el mecanismo genera preguntas útiles?" con menos garantía de generalización a queries reales.

## Slice del piloto (los golds donde vive el residual de retrieval)
Docs de los golds RERANK (8) + document-side (3), funnel s98: cat001·cat010·hp002·hp003·hp005·hp006·
hp009·hp017 (rerank) + cat016·hp011·hp012 (doc-side). ~11 golds → sus source_files. Genera hyq solo
para los chunks de esos docs (barato, revertible por batch-tag).

## Métrica + predicciones pre-registradas
- **Primaria = famtie (retrieval-miss)** con hyq ON vs OFF en el slice (juez family-aware K=5, pin del
  pool). NO PASS (fix de retrieval).
- **Predicciones (falsables)**: (a) cat016·autobúsqueda (único document-side puro, gap "dar de alta
  detector"↔"autobúsqueda/bucle") DEBE recuperarse si el mecanismo funciona; (b) ≥2 del bucket rerank
  deberían subir (mejor matching → la aguja sube en el pool); (c) 0 regresiones en golds sanos.
- **CONTROL NEGATIVO (fix dúo, obligatorio)**: medir famtie en el **dev COMPLETO (39)**, no solo el
  slice — para cazar daño colateral (una pregunta hyq genérica que roba slots a golds NO-diana; el
  HNSW es corpus-wide). Si golds fuera del slice regresan → las preguntas son demasiado genéricas
  (NO-GO / re-prompt), aunque el slice mejore.
- **Sanidad del mecanismo (anti garbage-in)**: muestreo-verificación de N=20 preguntas generadas
  (¿son realistas y responde el chunk?) — dúo/yo; si <70% sanas → el prompt está mal, no el mecanismo.

## Gates de decisión
- **GO del mecanismo** si: recupera cat016 (el document-side puro) + ≥1 del rerank SIN regresión + las
  preguntas muestreadas son sanas (≥70%). → activo caracterizado; corpus-wide = decisión de Alberto
  (coste + gatillo de técnicos), NUNCA auto-ship.
- **NO-GO** si: no recupera el document-side puro, o las preguntas son basura (prompt/mecanismo malo),
  o regresa golds sanos (los surrogates-pregunta meten ruido en el pool). Reportar honesto (patrón s94/D).
- Flag OFF, tabla de piloto revertible (batch-tag → DELETE + VACUUM, lección s95). NADA a demo.

## Coste estimado
Slice ~11 docs × chunks/doc × 2-4 preguntas ≈ pocos miles de generaciones cortas Sonnet + embeddings
Voyage → ~$5-15. Se corre UNA vez. Muy por debajo del corpus-wide (~$150-300, gateado).

## Preguntas para el dúo
1. ¿El mecanismo (surrogate-pregunta en tabla A3 + colapso + procedencia) es sano, o hay un modo de
   fallo (p.ej. una pregunta genérica que casa con MUCHOS chunks → ruido en el pool de golds sanos)?
2. ¿La métrica famtie + predicciones aíslan el efecto? ¿Falta un control (p.ej. hyq de docs NO-diana
   no debe cambiar golds de otros docs)?
3. ¿El diseño de procedencia (synthetic/real) es suficiente para el bucle futuro, o falta algo para
   que añadir preguntas reales + podar sintéticas sea limpio?
4. ¿Es esto pregunta-cero-positivo (piloto barato, activo foundational) o rigor mal dirigido (el
   residual retrieval es ~1-2 facts puros; el muro es síntesis)? Sé duro con la justificación.
5. ¿Riesgo de que el piloto contamine el canal A3 SHIPPED (misma arquitectura)? ¿Aislamiento correcto?

---

## ADDENDUM s101 (7 jul 2026) — cambios vs el prereg original, DECLARADOS (fix dúo cross-model)
1. **Slice ACTUALIZADO por evidencia nueva**: el deathpoint s101 (`evals/s101_deathpoint.yaml`) re-derivó
   los RECALL reales post-dual-soporte → se AÑADEN hp013 y hp020 al slice (sus docs faltaban:
   ADW535_TD_T140358es, HOP-138-8ES). hp013 SALE del few-shot al entrar al slice (regla anti-fuga
   intacta; entra hp008). Las preguntas pre-existentes de otros docs fueron calibradas con el few-shot
   viejo (incluía la pregunta de hp013) — contaminación de ESTILO sobre docs ≠ ADW535: declarada, riesgo
   bajo (las preguntas que miden hp013 son las nuevas, generadas con few-shot limpio).
2. **Métrica primaria PINEADA a la del instrumento canónico**: "chunk-valor en el POOL-50 (same-family)"
   = el bucket RETRIEVAL del assessment (criterio de Alberto: GO por reducción del bucket). NO top-k
   (eso mediría rerank, no vocabulario). El paso RECALL→IN-POOL del deathpoint es el flip que cuenta.
3. **Tratamiento estampado**: la medición estampa `HYQ_PILOT_FILE` + sha del `.npz` + n_preguntas en su
   manifest (un ON/OFF sin fingerprint del artefacto no es A/B válido).
4. **Framing corregido**: el canal hyq SÍ compite por slots del pool (unión+sort+cap) — es competencia
   de ranking, no "no-desplazamiento". El control negativo full-dev(39) mide exactamente ese daño:
   ningún chunk-soporte actual (baseline = full v2) puede salir del pool con el flag ON.
5. **Dedup+cap**: el parser del generador no capaba — el embed (`s101_hyq_embed.py`) aplica dedup global
   normalizado + cap 4/chunk (el prereg prometía 2-4).
6. **Fusión por CUOTA (iteración s101, post-primera-medición)**: la 1ª medición (sort-mixto A3-fiel) dio
   0 flips CON diagnóstico de mecanismo: cos pregunta↔query (~0.48-0.52, espacio asimétrico Voyage
   deflactado) vs cos chunk↔query (suelo del top-50 vectorial ≈0.577) = **escalas incomensurables** →
   todos los padres cortados en el cap-50 del canal (verificado con trace: la pregunta correcta de
   cat016 rankea #5 global y su padre 294a778c NUNCA entra a channels). El patrón A3 sort-mixto vale
   para enunciados (content-side, escala comensurable), NO para preguntas. Fix BP-HyPE: el índice de
   preguntas tiene su PROPIO top-k → **cuota `HYQ_PILOT_QUOTA=10`** (hiperparámetro de PILOTO, dev-
   elegido, lección DEC-092: se declara, no se vende como estructural). Los padres desplazan la cola
   del canal real = competencia de slots EXPLÍCITA; el control negativo full-dev mide el daño.
   El gate del piloto NO cambia: cat016 debe flipear (métrica pineada pool-50) + 0 regresiones.
