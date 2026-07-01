# s88 — Dossier accionable de los 30 NO-PASS (per-caso, para decisión en lote de Alberto)

> **Qué es.** Trabajo autónomo nocturno (s88) sobre el mapa de DEC-075f. Los 5 "fidelity-errors"
> examinados **al píxel** (gold → top5 congelado s87 → literal del chunk → corpus); el resto agrupado
> por clase con la evidencia de los instrumentos (rootcause semántico + synthesis stable + famtie).
> **NADA ejecutado sin gate**: gold-edits, merges y cambios de juez son TUYOS. Fuentes: `s87_gate_report.yaml`,
> `s87_rootcause.yaml`, `s87_synthesis_stability.yaml`, `s85_b1_diagnosis.json`, corpus live.

## Hallazgo central del per-caso (cambia la lectura de DEC-075)

**En los 5 casos examinados (N=5): CERO invenciones/inversiones del generador contra el contexto
servido** — el contrato CERO-INVENCIÓN se cumple — **más 2 fallos MENORES de calibración del generador**
(cat022: presenta la diferencia que encontró [sufijo B=SIL-2, correcta según F2] como respuesta sin
declarar que no tiene la específica L-vs-L4; hp013: no explota la señal débil "EEPROM" presente en F2).
La "contradicción" con el gold nace de que el chunk con el dato del gold NO llegó al top-5 (within-doc)
o de que el gold/juez difiere del literal servido (gold-review). El bucket "contradicts ~4" de
DEC-075(d) se disuelve en **2 within-doc (hp001, cat022) + 1 frontera síntesis/retrieval (hp013) + 2
gold/juez (cat009, cat020)**.

**Validez del examen (dúo cross-model):** el corpus contra el que verifiqué ES el congelado del eval —
`corpus_fingerprint` del manifest s87 (count=25.090, max_created_at=2026-06-09T19:15:25) **IDÉNTICO** al
corpus live en el momento del examen (verificado). Los literales citados abajo son auditables (doc+página).

| caso | qué pasó (verificado al píxel) | clase real | evidencia |
|---|---|---|---|
| **hp001** '1111 vs 2222' | El top5 sirvió el Manual de USUARIO ("clave de usuario 1111"); el chunk '2222' (admin) EXISTE en 3 docs (MC-380 p18/p20 + MI_372 p29) pero es FRONTERIZO (a veces entra al top5 → por eso flipeó en estabilidad). El bot leyó fiel lo servido. | **within-doc/fronterizo** (retrieval) | corpus: 3 chunks con '2222'; frozen top5 s87 sin ninguno |
| **cat022** banda IR L vs L4 | La banda (2,5-3,0 μm vs 4,5 μm) EXISTE en MNDT722 p8/p11/p12 — el MISMO doc que el top5 sirvió (F2-F4), otras páginas. El bot respondió con la diferencia que SÍ encontró (sufijo B=SIL-2), desviada pero fiel a su contexto. | **within-doc** (retrieval) | corpus: MNDT722 p8 'longitud de onda' |
| **hp013** EEPROM | El chunk EXPLÍCITO existe: "Las configuraciones específicas del sistema se guardan en una EEPROM" (p16; también p12/p14/p30) y NO se sirvió. **[matiz del sub-agente]** PERO el F2 servido (p29) SÍ contiene el token "EEPROM" (lista de componentes) — señal débil in-context que el bot no explotó. **Frontera síntesis/retrieval**, no within-doc limpio. | **frontera síntesis/retrieval** | corpus: ADW535 p16; F2 p29 con token |
| **cat009** 6K8 "suministrada" | El literal del manual (F5 servido, HLSI-MN-025): "…con un equipo final de línea **(EFL) de condensador de 47µF (suministrado)** o resistencia **(RFL) de 6K8Ω**…" — el "(suministrado)" acompaña SOLO al condensador. El bot dijo exactamente eso. **El gold dice "EOL suministrada de 6K8"** — contra este literal. K-INESTABLE (3 PARCIAL / 2 PASS); candidato a re-juicio tras gold-review. | **GOLD-REVIEW** (gate Alberto) | literal F5 citado |
| **cat020** 0-100% universal | **[corregido por el sub-agente]** El chunk servido F2 contiene AMBOS: las pantallas de Niveles Y el literal del gold (0-100% / 80 / 100 / 108) — y el bot **acertó los 3 números core** citando [F2]. El juez penaliza la desagregación OTM/LSR-por-niveles AÑADIDA (correcta según el manual) como si contradijera la universalidad. NO es within-doc: es **over-penalización de material correcto añadido**. | **GOLD/JUEZ puro** (gate Alberto) | F2 servido contiene el 0-100%; verificado por sub-agente |

## Los 30 NO-PASS agrupados por CLASE ACCIONABLE (con settled-check y gate)

### Clase A — GOLD/JUEZ-review (candidatos; gate: Alberto) → **la palanca CANDIDATA más barata de PASS a corto (delta NO medido — son casos debatibles que TÚ adjudicas)**
Candidatos con evidencia (adjudicación tuya, es ground-truth):
- **cat009** — gold vs literal del manual ("suministrado", arriba). K-INESTABLE al borde; **candidato a
  re-juicio tras gold-review** (no expectativa — PASS es holístico y ruidoso). *Caveat: el literal citado
  es del chunk servido (HLSI-MN-025); no he barrido si OTRA página declara la 6K8 suministrada → tu adjudicación.*
- **cat020** — matiz de planos (UI-niveles vs escala analógica).
- **cat019** — falso NO-PASS del juez **triple-confirmado** (s76: audit humano should_be=PASS; sesgo
  completitud-correcta≠contradicción). K-INESTABLE (4-1).
- **cat012** — "gold-injusto debatible" ya en s71/s74. (PASS-modal en s67base, PARCIAL ahora = ruido.)
- **hp004** — conducta: gold=clarify; el bot da AMBAS versiones (24V/220V con specs correctas) + pide
  verificar la instalada. s79/s80: clarify-vs-answer DEPENDE de si la respuesta diverge → aquí diverge
  (specs distintas) pero el bot CUBRE ambas ramas + advierte. ¿Cuenta como clarify funcional? Tu llamada.
- **cat024** — el bot acertó el dato del manual objetivo (17 mA MAD-472) e introdujo la discrepancia
  CAD-250 con recomendación de verificar; el juez lo castiga (¿answer-con-conflicto era la conducta?). Revisar.
- Los **6 K-INESTABLE** (cat009/cat010/cat019/hp004/hp013/hp020) tienen votos PASS. **HIPÓTESIS (no
  resultado):** un dual-judge (s47 §D) PODRÍA estabilizarlos — es un experimento gated con métrica
  propia, no una consecuencia; sigue gated a ~sept salvo que decidas adelantarlo.

### Clase B — within-doc / fine-grained retrieval (≈8 golds) → fix = **capa-ingesta (foundational, DEC-074)**
hp001, cat022, hp013 (examinados al píxel, arriba) + hp006 (3 hechos RECALL famtie), hp014, cat013,
cat016, hp012 (por famtie/instrumentos, sin examen-píxel esta noche). El chunk-valor EXISTE en el corpus
(verificado en los 3 examinados) pero no sube al top-5 ("aguja en chunk grande", coseno sub-suelo).
**Settled-check con MÉTRICA declarada (Protocolo 4):** los NO-GO de s86 (neighbor-window / ef_search /
más-contexto) se midieron EXACTAMENTE en esta métrica — retrieval-miss del cluster **RECALL-INTRADOC**
(DEC-074(a), los 8 within-doc) — no en PASS ni en ranking genérico → el settled APLICA a esta clase.
Ranking: DEC-048/050/056 (PASS/pool). NO hay lever barato — es el workstream capa-ingesta
(multi-granularidad + extracción-tablas + BM25/ColBERT, `s86_finegrained_retrieval.md`). **Ninguna acción
nueva esta noche** (sería re-litigar). *(hp002/hp003 RETIRADOS de esta clase — corrección del dúo: hp002
'reset inicial' = judge-FN CONVEYED; hp003 = PARTIAL-completeness sin verificación within-doc → van a "sin examen-píxel".)*

### Clase C — SÍNTESIS completeness (≈6-8 golds) → **settled NO-GO (DEC-051), sin acción**
cat001, cat011, cat017, cat018, hp007, hp010 (+solape con B). Omisiones de granularidad/secundarios
estables; el lever barato (prompt completitud) está medido Δ_net=0 + colateral. Techo del ruler ±2.

### Clase D — RERANK (6) → **settled (DEC-048/050), sin acción**
cat010, cat021, hp005, hp009, hp011, hp017 (hecho en pool-50, no en top-5).

### Clase E — IDENTIDAD (1) → workstream (A) ya planificado
hp018 (ZXe→MIE-530; DEC-074, catálogo canónico 2-etapas).

### Casos restantes sin examen-píxel esta noche
cat007 (imprecisión "relé de..."), cat008 (asignación terminales), hp008 (omite LPB…), hp020 (omite
supp), **hp002** (su 'reset inicial' = judge-FN CONVEYED; su otro hecho = RERANK), **hp003** (PARTIAL
completeness, within-doc NO verificado) — PARCIALes de completitud/matiz, baja palanca individual;
candidatos a la misma revisión A/C si abres el lote de gold-review.

## Recomendación operativa (decisión en lote para ti, ~30-45 min de lectura)
1. **Abrir el lote de GOLD-REVIEW de la Clase A** (7-9 golds): es la única palanca de PASS a corto
   plazo, es barata, y ahora tiene evidencia per-caso al píxel (no vibes). Yo preparo cada edición
   propuesta con cita literal del manual; tú adjudicas (ground-truth, tu gate DEC-025/RULER §2).
2. **Nada nuevo en B/C/D** (todo settled/foundational — la disciplina del digest evitó 4 re-litigaciones esta noche).
3. **(A) catálogo Fase 0** sigue disponible para cuando tengas la ~1h.

**Corrección honesta a DEC-075:** "fidelity-errors reales del bot (cat022/hp001/cat009)" era una
sobre-lectura mía del adjudicador — en los 5 examinados (N=5), ninguno es inversión del generador
contra el contexto servido. El "highest-leverage candidato = gold-review del bucket OTRO" SE REFUERZA
(ahora con 2 candidatos más y evidencia literal), con delta PASS NO medido (tu adjudicación decide).

**Dúo COMPLETO (Protocolo 3):** (1) cross-model GPT-5.5 — 8 findings (6 confirmados + 1 FP-en-sustancia
[el settled de clase B SÍ se midió en la métrica de la clase] + 1 cerrado-con-dato [fingerprint corpus
idéntico]); (2) sub-agente (ronda fresca) — veredicto **SÓLIDA**: verificó independientemente TODOS los
claims de corpus (ciertos) y cazó mi **sobre-benevolencia hacia el bot**: cat020 reclasificado a
gold/juez-puro (el chunk 0-100% SÍ se sirvió; mi "+within-doc" era racionalización), hp013 →
frontera síntesis/retrieval (token EEPROM servido, señal débil ignorada), "cero bugs" → "cero
invenciones + 2 fallos menores de calibración". También: **el dossier corrige un FN del instrumento**
(`s87_rootcause` marcaba hp001=OTRO/n_retr=0; el examen píxel demuestra retrieval within-doc). Todas
las correcciones aplicadas in-place. **Traza de probes de corpus: `evals/s88_corpus_probes.yaml`**
(fingerprint idéntico al manifest s87 + hits por probe con doc/página/id).
