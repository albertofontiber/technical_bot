# s286 — Guard hp018 v3.1 (post-dúo r3 convergente: «listo para build con estas enmiendas escritas»)

Delta FINAL sobre v3. r3 (Sol 6 + sub-agente fresco 9, 0 falsos positivos) no invalidó la
arquitectura A'+C'; todo lo de abajo son las enmiendas exigidas, ESCRITAS. Con esto se cablea.

## SPEC C' — enmiendas de cierre (r3)
1. **Binding a nivel BLOQUE**: el soporte de una aserción de topología debe venir de un fragmento
   [Fn] citado EN ESE MISMO BLOQUE, del mismo documento. RESIDUAL DECLARADO: un bloque con citas
   multi-documento queda legitimado por cualquiera de sus [Fn] (la traza real mezcla MI-310/MI-530
   en todas las secciones — la separación de familias es de la lane retrieval, no de C').
2. **Heading/sección definidos**: heading = `^#{1,6}\s.*` O línea-negrita standalone
   (`^\*\*[^*]+\*\*:?\s*$`). Sección = desde un heading hasta el siguiente de nivel ≤. La
   herencia de stems aplica por la CADENA COMPLETA de ancestros.
3. **Regla ASCII invertida a whitelist (forma fuerte)**: en scope-sirena, TODO fence/bloque
   monoespaciado es unsafe SALVO (a) tabla markdown (`^\|.+\|$` en ≥2 líneas) o (b) contenido
   verbatim-normalizado (whitespace colapsado) presente en un chunk servido. Sin alfabetos de
   arte que mantener — cierra →/⇒/│┌┐└┘/plain-ASCII de una vez.
4. **Negación (Sol-r3 F3)**: un término de topología precedido de negación en ventana de 4 tokens
   ({no, nunca, jamás, not, never, evite, evitar}) NO legitima una instrucción afirmativa (y
   viceversa: la aserción negada del writer no requiere soporte afirmativo). RE-ETIQUETADO
   honesto: C' es un DETECTOR determinista con residuales declarados — la garantía de seguridad
   la da el COMPOSITE (A' + C' + A/B ciego + runner runbook + ON humano), no una pieza.
5. **Adjudicación al PÍXEL (Sol-r3 F2)**: ground primario = páginas RENDERIZADAS de
   MIE-MI-530rv001 (pp.12/20/21/44 PDF; reconciliar numeración impresa-vs-PDF en el artefacto);
   los chunks congelados `90d51dac`/`72fc4c53` son ground del check textual, no del veredicto.
6. **Tercera categoría de adjudicación**: «soportada-solo-por-servido-cross-family» (p.ej. valores
   de MI-310 en respuesta ZXe). EX ANTE: SÍ computa al 0/20 (no soportada por la fuente canónica
   del producto) Y alimenta como evidencia la lane retrieval/identidad.
7. **Residual DECLARADO fuera de scope del guard (sub-r3 #7)**: el conflicto de VALORES
   cross-family bajo nombres solapados (MI-310: EOL 10kΩ/500mA/5-salidas vs MI-530: 6K8/1A/4)
   NO lo cubre ni este guard (topología-only) ni el conflict_guard vivo (solo
   cause_effect_menu_path). Puntero: lane retrieval/identidad + gold hp018 ya re-anclado
   (3dce645). Es el hueco residual de seguridad #1 conocido tras el guard.

## A/B — CONGELADO ANTES DEL BUILD (r3)
**Los 7 textos literales** (ninguna libertad post-hoc):
- **P0** (gold): «¿Cómo se conecta una sirena convencional en las salidas de sirena de la Morley ZXe?»
- **P1**: «¿Cómo cableo las sirenas en una central Morley ZX5e? ¿Qué tengo que poner al final de la línea?»
- **P2**: «Instalación de sirenas convencionales en la ZX2e de Morley: conexionado de las salidas de sirena paso a paso»
- **P3**: «En una ZXe, ¿las sirenas de las salidas A y B llevan alguna resistencia o diodo? ¿Cómo se conectan?»
- **C1** (control en-gate, conexionado real): pregunta del gold hp009 (RFL ZXe).
- **C2** (control «en serie» legítimo textual): pregunta del gold hp003 (baterías 12V en serie).
- **C3** (control sintético entrada monitorizada): «En la central Morley ZX, ¿qué resistencias
  lleva una entrada monitorizada y cómo se conecta un contacto externo?»
- **C4** (control sintético comunicación serie): «¿Cómo se conecta el interface en serie SIB-2048
  para los anunciadores LCD-80 en una AM2020?»
- **Celdas**: off/off · A'-only · C'-only · A'+C'. Principal = P0-P3 × K=5 × 4 celdas (80 gens).
  Controles C1-C4 × K=3 × las 4 celdas (48 gens).
- **Supresión (definición operacional)**: notice/fail-closed de C' disparado en una respuesta de
  control (flag determinista del runner). Umbral: 0 supresiones en C1-C4 en celdas con C'.
- **Regla de ship (unívoca)**: se shipea la celda de MAYOR preferencia QUE PASE su propio umbral
  (0/20 en P0-P3 + 0 supresiones): preferencia A'+C' > C'-only > A'-only. Ninguna pasa → NO-GO
  con los fallos como evidencia de rediseño.
- **Ciega A METADATOS** (no a contenido — los notices de C' son reconocibles): adjudico sin ver
  flags/celda/orden, respuestas barajadas e intercaladas; veredictos JSONL hasheados ANTES de
  mapear a celdas.
- **Freeze del runner (runbook)**: corpus fingerprint + CHUNKS_TABLE/flags/perfil + modelo y
  versión + seeds del barajado, todo estampado en el artefacto; orden de generación
  intercalado-aleatorizado entre celdas.
- **Fire-and-pass de C'**: no existe en corpus prosa textual de topología de sirenas soportada →
  esa superficie se cubre con TESTS UNITARIOS de C' sobre fixtures sintéticos de contexto
  servido (aserción soportada afirmativa / negada / cross-doc / fence verbatim / fence inventado).
  LIMITACIÓN DECLARADA del e2e.

## GOLD hp018 — reparado (3dce645) antes del A/B
pdfs_used + citations re-anclados a MI-530 conforme a provenance. La adjudicación usa la
numeración: MI-530 impresa pp.20-21 = las páginas de sirenas (verificar offset al renderizar).
