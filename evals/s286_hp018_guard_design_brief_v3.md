# s286 — Guard hp018 v3 (post-dúo r2: Sol 6 + sub-agente fresco 9; PRE-REGISTRO de medición)

Delta sobre v2 (`s286_hp018_guard_design_brief_v2.md`); v2 §1-8 siguen vigentes salvo lo aquí
enmendado. Convergencia r2: el esqueleto A'+C' se sostiene; lo que faltaba era CONTRATO de
medición reproducible + specs deterministas cerradas + las dos correcciones de autoridad.

## E1 — AUTORIDAD DE FUENTE (Sol-r2 F1 CONFIRMADO; corrige mi refutación errónea de r1)
`pdfs_used: MIE-MI-310.pdf` del gold es STALE. La provenance canónica ancla hp018 a
**`MIE-MI-530rv001` pp.12/21/44** (§3.4.4 Circuitos de Sirenas, Fig 13/14: RFL 6K8 0,5W, diodo
por sirena, 1A, polaridad; ZX2e=2 / ZX5e=4 salidas) y declara **MI-310 = ZXAE/ZXEE, PRODUCTO
DISTINTO** (s277_c1_p1_design_v1.md:482-488: chunks congelados `90d51dac` p20 + `72fc4c53` p21).
- **Adjudicación del A/B contra MI-530 pp.20-21** (no MI-310).
- **Hallazgo adicional para la lane retrieval (fuera del guard, anotar en cierre):** la traza
  10/10 sirve y cita MI-310 → contaminación cross-family activa en hp018. El guard NO la arregla;
  el binding de C' (E3) la mitiga en la superficie de seguridad.
- pdfs_used stale de hp018 → corregir vía gold_store en la lane de golds (edición menor).

## E2 — ORDEN DE ENCENDIDO (Sol-r2 F2 CONFIRMADO)
«Adelantado» aplica a BUILD + A/B dirigido, NO al ON. Flags de A'/C' permanecen **OFF en Railway
hasta**: A/B factorial GO + re-baseline v4 completa + runner end-to-end estilo runbook sobre los
QIDs afectados (hp018 incluido; C1_RELEASE_RUNBOOK.md:176-199). El ON es click de Alberto.

## E3 — C' SPEC CERRADA (sub-agente F2/F5/F6/F7 + Sol F3/F5)
1. **Binding de soporte**: el chunk que legitima una aserción de topología debe ser (a) CITADO en
   esa sección, (b) del MISMO documento que la sección cita, y (c) contener el término de
   topología en un bloque con stem sirena/salida/NAC — no cualquier hit léxico servido
   («interface en serie» de otro doc NO legitima).
2. **Scope por SECCIÓN con herencia de encabezado**: el stem del heading (p.ej. «## Sirenas»)
   se hereda a sus bloques hijos (cierra el bypass encabezado-separado + fence con S1/S2/RFL).
3. **Fences atómicos**: extraer code-fences como bloques indivisibles ANTES de segmentar por
   líneas en blanco.
4. **Regla ASCII implementable**: unsafe si fence/monoespaciado en scope-sirena contiene ≥3
   runs de {guiones Unicode ─━, ASCII `-`, `=`} + conectores {`|`,`▶`,`◀`,`->`,`<-`} o cajas
   `[...]`/`+--+`; EXCLUYE líneas-tabla markdown (`^\|.+\|$`); comparación verbatim-NORMALIZADA
   (whitespace colapsado) contra los chunks servidos.
5. **Equivalencia bilingüe** en lexicón y soporte: {en serie ↔ in series, en cadena/encadenar ↔
   daisy-chain/chained, una tras otra ↔ one after another} — sigue determinista.
6. **Notice detector-clean POR CONTRATO** + test unitario notice-pasa-el-detector (evita el
   fail_closed total por auto-flageo).
7. **Posición exacta**: C' corre tras `apply_answer_planner` (generator.py:788) y ANTES de
   must_preserve (806) → conflict_guard (825) → EC (839).
8. **A' sin invitación a fabricar**: nombrar figura SOLO si el texto servido la referencia;
   si no, remitir a «manual X, página Y» sin número de figura.

## E4 — PRE-REGISTRO DEL A/B (BLOCKER común r2; parámetros FIJADOS)
- **Batería**: pregunta hp018 + 3 paráfrasis fijas (se listan en el runner) × **K=5** por celda.
- **Celdas**: off/off · A'-only · C'-only · A'+C' — las 4 con la MISMA batería (off/off se
  RE-CORRE; la traza vieja no es celda).
- **Métrica primaria**: adjudicación contra `MIE-MI-530rv001` pp.20-21 (chunks congelados
  `90d51dac`/`72fc4c53`), CIEGA a celda (respuestas barajadas, sin flags visibles), incluyendo
  bloques de código y refs de figura (verificar contra chunk-text, no asumir). Adjudico yo;
  empates/dudas → Alberto (ground-truth de dominio).
- **Umbral GO por celda de tratamiento**: 0/20 aserciones-de-topología-no-soportadas Y 0
  supresiones de contenido legítimo en controles. Tripwire regex ampliado = secundario.
- **Regla de decisión pre-declarada**: se shipea la celda MÍNIMA que logra 0/20 (orden de
  preferencia: A'+C' > C'-only > A'-only, porque la garantía determinista es C'; si A'-only
  diera 0/20 igualmente se shipea A'+C' — defensa en profundidad barata). Si NINGUNA da 0/20 →
  NO-GO, vuelta a diseño con los fallos como evidencia.
- **Controles de sobre-supresión (en-gate y fuera-gate)**: hp009 (RFL ZXe — conexionado real,
  ejercita C') + hp003 (baterías en serie LEGÍTIMO, prosa textual) + pregunta sintética entrada
  monitorizada 2×6K8 (MIE-MP-520rv04 p27) + pregunta sintética RS-485/comunicación serie. K=3
  c/u, misma adjudicación ciega.
- **Logging del runner**: raw answer + diagrams payload + served chunk ids + flags → artefacto
  JSONL versionado (mide de paso el impacto REAL del bug DIAGRAMAS_RELEVANTES — Sol F4/sub F8:
  el ~50% era inferencia; el canal visual-assets corre independiente en generator.py:874-881).

## E5 — TALLY r1 CORREGIDO
Mi «parcialmente refutado» a Sol-r1-F1 fue un error de verificación superficial (leí pdfs_used
stale y paré). Sol r1: 7/7 confirmados. Corregido en adversarial_review_log.jsonl.
