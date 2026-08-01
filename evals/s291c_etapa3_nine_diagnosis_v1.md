# s291c — DIAGNÓSTICO de los 9 synth-miss estables de etapa 3 (fan-out + refutador por miss)

Estado: **DIAGNÓSTICO CERRADO, nada cableado.** Método: 9 misiones judge-free en paralelo
sobre el recibo del FULL v3.2 (`s100_factlevel_full_v32_full_20260801.yaml`) + código + DB
read-only, cada una con **grep obligatorio de settled** (DEC + métrica) en el prompt, y **1
refutador adversarial por diagnóstico** (18 agentes; 17 completos, 1 refutador caído por
crédito). Journal: `wf_0d2fc27f-832`.

## Resultado: los 9 NO son 9 problemas — son 4 clases

| # | fact | clase | lever | refutador |
|---|---|---|---|---|
| 1 | **hp003#4** magnetotérmico | **mecanismo-pipeline** | Extensión ACOTADA del léxico MANDATORY con gatillo COMPUESTO «siempre + imperativo procedimental» (espejo del compuesto `debe(n)+antes de` ya existente) → **alimenta la maquinaria del apéndice L2 recién shippeada** | NO refutado |
| 2 | **hp017#2** Editar Configuración | **mecanismo-pipeline** | Precisión del **conflict-guard post-generación** (`KNOWN_ANSWER_CONFLICTS`): el fact viaja servido y verbatim, y lo SUPRIME un guard de disclosure numérica (rama one-sided) | NO refutado |
| 3 | **cat017#2** licencia CLIP/lazo | **mecanismo-pipeline** (+ hallazgo de instrumento) | Probe $0 de lanes existentes sobre el carrier en pool-rank-19 + candidato lane reference-scoped (el servido b7633e98 lleva el hook gobernado «Consulte… 4188-1125-ES» y doc_map ya acredita ese doc) | NO refutado |
| 4 | **cat018#2** Tipo SW / CBE | **mecanismo-pipeline** | **GOLD-SPLIT primero** (fact compuesto: la mitad CBE ya convierte; la mitad «Tipo SW» nunca llega a la vista) → luego re-medir | ⚠ refutador caído (crédito) |
| 5 | **hp011#2** 05 a 295 seg | mecanismo-pipeline **PERO** | **Pair-completion de registro lógico inter-chunk** (la celda t.A quedó partida por frontera de chunking) | **REFUTADO** — censo mal (5 carriers, no 3) + `in_pool` sin reconciliar ⇒ **re-cablear el diagnóstico antes de cualquier lever** |
| 6 | **hp006#2** ISO-X | **scope-gold** (Alberto) | ninguno: servido+acreditado, la pregunta no contrata ese ítem | NO refutado |
| 7 | **hp008#4** LPB500 | **scope-gold** (Alberto) | ninguno: servido en pos 2/10 y citado; la miss es de alcance del gold | NO refutado |
| 8 | **hp013#1** PWR-R | **techo declarado** | ninguno fuera de settled (DEC-089/164c) | NO refutado |
| 9 | **hp017#1** instrucción de entrada | **techo declarado** | ninguno: familia de conversión-en-síntesis del span murió en S274 (obl_b2043) | NO refutado |

**Reparto: 3 levers vivos + 1 gold-split + 1 re-cablear + 2 gold-review + 2 techo.**

## HALLAZGO TRANSVERSAL (el más importante) — el «rerank 0» del full está INFRACONTADO

El diagnóstico de cat017#2 (no refutado, anclas verificadas) destapa una **asimetría de vara
dentro del instrumento**: el acreditador de SOPORTE es laxo en granularidad (acredita un chunk
que dice «el modo CLIP requiere licencia») mientras el juez de CONVEYED es estricto (exige el
payload «una licencia POR CADA lazo»). Consecuencia: un fact cuyo carrier real nunca se sirvió
—y que mecánicamente es **recuperado-no-servido**— aterriza etiquetado **synthesis-miss**,
porque el soporte genérico fuerza `reaches_gen=True`. Sin ese sobre-crédito habría caído
rerank-miss con `best_pool_rank≈19`.

Implicación directa: la línea **«rerank 0»** de la fila del scoreboard (DEC-170) **no significa
que la clase esté vacía** — significa que parte de ella está escondida dentro del bucket synth.
Antes de diseñar levers de SÍNTESIS para los 9, hay que correr el **signature-check** (soporte
servido solo-genérico + payload-carrier en pool fuera de ventana) sobre los 8 restantes. Es $0
(lectura de recibo + DB) y puede re-clasificar más de uno.

## Correcciones de los refutadores a incorporar (no cambian clase)
- hp011#2: censo de carriers 3→5; reconciliar `in_pool=true`; **el lever de pair-completion NO
  se diseña hasta re-cablear**.
- hp003#4: el recibo NO acredita `eaa39792` como el soporte contado (semántica de
  `support_l1_override`) — el lever sigue en pie, la traza del soporte se corrige.
- hp017#2: el brazo serving-side alternativo roza una fila settled ⇒ solo el brazo de
  precisión del guard.
- hp008#4: «el residual cae en espacio settled NO-GO» era demasiado fuerte — la exhaustividad
  se declara, no se afirma.

## Secuencia propuesta (barata primero, sin re-litigar nada)
1. **Signature-check $0 sobre los 8** (hallazgo transversal) → cola real de síntesis vs
   recuperado-no-servido.
2. **Lever hp003#4** (gatillo compuesto del léxico MANDATORY): el más barato con retorno —
   reusa el apéndice L2 ya vivo en prod; dúo + gate FP del mismo patrón s291b.
3. **Lever hp017#2** (precisión del conflict-guard): zona sensible (guard de seguridad
   numérica) ⇒ dúo obligatorio, invariante «nunca asertar número en conflicto sin disclosure»
   intacto.
4. **cat017#2**: probe $0 de lanes + diseño de la lane reference-scoped si ninguna cubre.
5. **A bandeja de Alberto (sentada B2)**: hp006#2, hp008#4, cat018#2 (gold-split), + las
   fichas previas (meta-ref cat020#2, hp001#2, gold hp002 «de Detnov»).
6. hp011#2: re-cablear diagnóstico ($0) antes de nada.
7. hp013#1 / hp017#1: techo — no se tocan.
