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

---

## s292 — EJECUCIÓN de los 2 pasos $0 (signature-check + re-cablear hp011#2)

### 1. Signature-check del hallazgo transversal → **CONTENIDO en cat017#2, NO sistémico**
Recibo: `evals/s292_signature_check_result_v1.json` (determinista, 0 LLM).
**Regla-C contra mi propia sonda:** la v1 dio 0/10 y era un null FALSAMENTE tranquilizador —
tenía TRES defectos que la hacían ciega a la hipótesis que debía probar: (a) usaba el matcher
de ANCHOR léxico, que puntúa igual la forma genérica y el payload distributivo (¡la distinción
exacta que se investigaba!); (b) no aplicaba el kill de TOC del instrumento — eligió una página
de ÍNDICE como «carrier» de cat017#2; (c) el desempate estricto descartaba los EMPATES, que son
justo el caso genérico-vs-payload. La v2b corrige las tres y **encuentra el carrier correcto por
construcción** (`4c186fb2`, p.17 del doc de licencias, score 0.50, no servido) — el mismo que el
diagnóstico había identificado, ahora por vía determinista e independiente.
**Resultado: FIRMA en 1/10 — solo cat017#2** (el ya conocido). ⇒ **El «rerank 0» del FULL v3.2
NO está infracontado por esta vía; la línea de DEC-170 se sostiene.**
Limitación declarada: la sonda mide una forma de gap de granularidad (cardinalidad
distributiva); otras formas de payload (condiciones, cualificadores) no están cubiertas — el
resultado acota la hipótesis, no la cierra universalmente.

### 2. hp011#2 re-cablado (el diagnóstico REFUTADO) → mecanismo CONFIRMADO con orientación corregida
Censo completo en DB (5 carriers, como exigió el refutador) + reconciliación con el recibo:

| carrier | idx | doc | en pool | servido |
|---|---|---|---|---|
| `2d45a70a` | 76 | HLSI-MN-103 (ES) | no | **SÍ (append)** — 5/5 votos |
| `4581dc4b` | 75 | HLSI-MN-103 (ES) | no | no |
| `7e657b4b` | 4 | Quick start guide (EN) | sí (rank 20) | no |
| `fb6f9f30` | 3 | Guía rápida (ES) | no | no |
| `2ed6b240` | 71 | HLSI-MN-103I (EN) | no | no |

**Corrección material del diagnóstico original:** la mitad servida es la del **VALOR** (idx 76,
«Valor variable de 05 a 295 seg.»), y la que falta es la del **LABEL** (idx 75, que porta el
parámetro `t.A`) — no al revés. `in_pool=true` del recibo se reconcilia: se refiere al soporte,
que es el append servido. El mecanismo «registro lógico partido por frontera de chunking» queda
**CONFIRMADO** con la orientación correcta.
**Dato nuevo, decisivo para el diseño:** el chunk servido lo trajo la lane
`same_blob_structural_neighbor_coverage_v1`, y el label perdido está a **gap 1** (idx 75 vs 76)
del mismo blob. Es decir: la lane que ya corre en producción tiene el vecino a un paso y no lo
trae. El lever no es una lane nueva — es entender por qué el vecino adyacente no entra
(¿seed-only? ¿validación de faceta?) y, si procede, la regla de **pair-completion cuando la
fila servida arranca mid-registro**. Diseño con dúo, flag-off, gate del patrón s291b.
