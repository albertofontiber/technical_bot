# s324b · Sondas de ALCANZABILIDAD de los 8 «servido y omitido» del FULL 16-ago — población de la etapa 3 / lever B

> **Qué es.** Ejecución del encargo `evals/s321_encargo_sondas_etapa3_v1.md` (escrito en s321), en la
> sesión hija s324b del 16-ago-2026 (rama `claude/s324b-sondas-etapa3`). Solo MEDICIÓN: un recibo
> por hecho con la sonda canónica `scripts/s293_reachability_probe.py` (juez `judge_conveyed21`
> GPT-5.5 K=5, `THRESH_FIRM=4`, generador `claude-sonnet-4-6`, `GENERATOR_PROMPT_VARIANT=fidelity`,
> `chunks_v2`, TOP_K 50 / RERANK 10 llm), 3 reps por hecho. **Ni el instrumento ni la vara se han
> tocado**; los defectos vistos van en §5. **No se diseña ningún lever aquí** (regla 5 del encargo).
> Sirve a `DEC-175` (población del lever B) — la actualización de DEC-175 / LEVER_DIGEST / PLAN la
> hace la sesión hub, no este documento.

**Regla de lectura** (`scripts/reachability_verdict.py`): `ALCANZABLE` si alguna rep del brazo
oráculo ≥4/5; `NO_ALCANZABLE` solo con prueba de entrega en TODAS las reps **y** cobertura atestada
por el operador; cualquier otra cosa `INCONCLUYENTE_*` y no cuenta como negativo. Los veredictos de
abajo están **copiados tal cual** del JSON de cada recibo (`veredicto.veredicto`).

---

## 1 · Tabla por hecho (recibos `evals/s293_reachability_<qid>_<fact>.json`)

| # | hecho (`valor`) | modo FINAL (y qué pasó antes) | reps base→oráculo | veredicto (literal) | máx oráculo | entrega | coste |
|---|---|---|---|---|---|---|---|
| 1 | `cat001#3` (`32 / 25 / 20`) | `appendix --span-grep "25 equipos\|20 equipos\|32 equipos"` (regex del encargo, 1.ª y única corrida) · span F1 «Para cumplir los requisitos de EN54-2, los aisladores deben instalarse entre 32 equipos como máximo.» | 5→5 · 5→5 · 5→5 | **`ALCANZABLE`** | 5/5 (3/3 firmes; **base ya firme 3/3**) | tautológica (appendix) 3/3 | no impreso |
| 2 | `cat008#3` (`1/2/3/4 lazo; 6-7 entrada A`) | `appendix --span-grep "Entrada del lazo\|Salida del lazo"` (regex del encargo, 1.ª y única) · span F4 «Salida del lazo - 1» / «**a:** T1 Salida del lazo -.» | 5→5 · 5→5 · 5→5 | **`ALCANZABLE`** | 5/5 (3/3; **base ya firme 3/3**) | tautológica 3/3 | no impreso |
| 3 | `cat016#1` (`menu ZONA + ELEMENTO`) | run1 `appendix --span-grep "ELEMENTO\|men[úu] ZONA"` (encargo) → **`INCONCLUYENTE_SIN_COBERTURA_ATESTADA`** (0→0 ×3): el span elegido fue la línea de la autobúsqueda («…nos mostrará todos los **elementos** que encuentra») que **NO cubre** el hecho, así que NO se atestó cobertura. run2 (FINAL) `appendix --span-grep "acceda al men[úu] ZONA"` → span F1 verificado «Para crear y asignarlas zonas a los elementos acceda al menú ZONA.» (chunk `294a778c`, CAD-150-8 Instalación p11 idx8 §3.3) | 0→0 · **5→5** · 0→1 | **`ALCANZABLE`** | 5/5 (1/3 firme, y esa rep tenía **base 5/5**: el apéndice NO levantó las dos reps con base 0) | tautológica 3/3 | no impreso |
| 4 | `hp005#3` (`CIRCUITO SIRENA`) | `appendix --span-grep "CIRCUITO SIRENA"` (encargo) → **no construible** («span no encontrado en los 13 servidos» — sin recibo). FINAL `serve --inject 29270029,b92ecc4a,33603a2d` (MPDT190 = ID3000 Manual de programación, p76 idx94 §7.6.1.3 pantallas «1: Salidas activadas» / «2:TODAS SALIDAS: Subzona/Zona/Central | 3:CIRCUITO SIRENA/RELÉ»; p78 idx96 §7.6.2.2 «¿Limitado por TIPO? … 2:TODOS LOS MÓDULOS DE SIRENA»; p80 idx99 §7.6.2.3 «se selecciona un circuito de sirena o relé en lugar de una zona y equipo»), cobertura atestada (§6) | 5→5 · **0→5** · 5→5 | **`ALCANZABLE`** | 5/5 (3/3 firmes; base firme 2/3) | medida 3/3 (`requeridos 3, admitidos_unicos 3, faltan []`) | no impreso |
| 5 | `hp009#0` (`Retorno`) | `appendix --span-grep "Retorno\|bucle cerrado\|Inicio Lazo"` (encargo) → rep0 0→0 [span F6 «- Datos/Alimentación (+) Retorno (red line)», leyenda de figura], rep1 0→0 [F6], **rep2 «no construible»** (el set servido cambió y ya no había span) ⇒ la sonda abortó **sin escribir recibo** (solo queda el log). FINAL `serve --inject a8d7b1a4,dadab3e0` (MIE-MI-530rv001 = Manual de Instalación ZX2e/ZX5e: p19 idx24 §3.4.3.1 «Retorne el final del lazo al otro extremo del conector de lazo (+/-) del panel» + Fig. 9 «Inicio Lazo (+) OUT / … (+) Retorno / (-) Retorno»; p17 idx21 «debe instalarse en bucle cerrado»). `a8d7b1a4` **no está ni en `served_ids` ni en `pool_ids` del FULL 16-ago** (carrier nunca recuperado). Cobertura atestada **con caveat** (§6) | 0→0 · 0→0 · 0→**3** | **`NO_ALCANZABLE`** | 3/5 (0/3 firmes) | medida 3/3 (`requeridos 2, admitidos_unicos 2, faltan []`) | no impreso |
| 6 | `hp015#0` (`convencional`) | run1 `appendix --span-grep "convencional"` (encargo) → **`INCONCLUYENTE_SIN_COBERTURA_ATESTADA`** (0→0 ×3): span «La central de extinción de incendios es compatible con los detectores de la gama convencional…» (`fdb14497` p15) **NO cubre** el hecho (no dice que la central sea convencional/no direccionable), no se atestó. FINAL `serve --inject 717223e7,da5d4101` (CCD-103 portada p1 idx0 «Central Convencional de 3 Zonas de detección y 1 Extinción» + §1 Introducción p5 idx1 «único modelo de central de 3 zonas convencionales y 1 riesgo»); ninguno en `served_ids`/`pool_ids` del FULL. Cobertura atestada con caveat (§6) | 0→0 · **0→5** · **0→5** | **`ALCANZABLE`** | 5/5 (2/3 firmes; base 0/3) | medida 3/3 (`requeridos 2, admitidos_unicos 2, faltan []`) | no impreso |
| 7 | `hp015#2` (`32`) | `appendix --span-grep "32 detectores\|32 equipos"` (encargo) → **no construible** («span no encontrado en los 11 servidos» — el carrier SÍ está servido pero dice «detectores o pulsadores por zona son 32», patrón ciego al orden de palabras). FINAL `appendix --span-grep "por zona son 32"` → span F3 «Recuerde que el número máximo de detectores o pulsadores por zona son 32.» (`fdb14497`, CCD-103 p15 idx10, servido) | **0→5** · **0→5** · 5→5 | **`ALCANZABLE`** | 5/5 (3/3 firmes; base 1/3) | tautológica 3/3 | no impreso |
| 8 | `hp017#1` (`instruccion de entrada`) | `appendix --span-grep "[Ii]nstrucci[óo]n de [Ee]ntrada"` (encargo) → **no construible** («span no encontrado en los 13 servidos»): el carrier `d27b1a1b` SÍ se sirve (fila apendizada por `same_blob_structural_neighbor_coverage_v1`) pero la sonda parte «* Instrucción de entrada:» en el «:» y la etiqueta mide **exactamente 25 chars** (guard `len>25`) → sin span. FINAL `serve --inject d27b1a1b` (997-671-005-3_Configuration_ES = PEARL Manual de configuración, p41 idx73, Apéndice 5 §A5.1: «Una regla consta de dos instrucciones de acción… * Instrucción de entrada: … condición de entrada… * Instrucción de salida: … accionamiento de… sirenas o relés»), cobertura atestada (§6). `oracle_ids_admitidos` lista `d27b1a1b` **dos veces** (la lane también lo apendizó) ⇒ el oráculo aquí = el MISMO chunk duplicado y colocado con `similarity` máxima, no evidencia ausente | **0→5** · **0→5** · **0→5** | **`ALCANZABLE`** | 5/5 (3/3 firmes; base 0/3) | medida 3/3 (`requeridos 1, admitidos_unicos 1, faltan []`) | no impreso |

**Coste**: la sonda **no imprime ni registra coste** (el recibo no tiene campo de coste); el
encargo estimaba ~$1/hecho. Corridas totales: **14 invocaciones** = 10 completas (3 reps × 2
juicios K=5, recibo escrito) + 1 parcial (hp009 appendix: 2 reps juzgadas, abortó en la 3.ª sin
recibo) + 3 abortadas en la primera rep sin juez (hp005 / hp015#2 / hp017#1 appendix). Estimación
honesta: **~$11-13**, por encima de los ~$8 previstos por las re-corridas de fallback.

**Sello parcial de cada recibo** (`sello_freeze_PARCIAL.git_sha`): cat001/cat008/cat016/hp005 →
`246cb59b`; hp009 → `2ab9a5a8`; hp015#0/#2 → `630caabd`; hp017#1 → `8e321522`. El sha cambió
porque la sesión hub **commiteó en la misma rama durante la medición** (ver §7: ninguno de esos
commits toca `scripts/s293_reachability_probe.py`, `reachability_verdict.py`,
`factlevel_assessment.py` ni `src/`; sí mutan catálogo/doc_map y retiran 2 docs del corpus).

---

## 2 · Recuento y ajuste `hp015`

- **`ALCANZABLE` (7 hechos)**: `cat001#3`, `cat008#3`, `cat016#1`, `hp005#3`, `hp015#0`, `hp015#2`,
  `hp017#1`.
- **`NO_ALCANZABLE` (1 hecho)**: `hp009#0` (con prueba de entrega 3/3 y cobertura atestada; caveat
  declarado sobre la negación «sin RFL», que el manual no escribe literal).
- **`INCONCLUYENTE_*` finales: 0.** (Los dos INCONCLUYENTE intermedios —`cat016#1` run1 y `hp015#0`
  run1— eran oráculos con span que NO cubría el hecho; se corrigió el oráculo (regla-C de DEC-173:
  oráculo incompleto ⇒ corregir y verificar) y el recibo final los sustituye. Copias de los run1 en
  el scratchpad de la sesión, ver §8.)

**Ajuste `hp015` (regla 3 del encargo)**: `hp015#0` y `hp015#2` son del MISMO gold y salen igual
(ambos `ALCANZABLE`) ⇒ cuentan como **UNA** observación de la clase. Recuento ajustado:
**6 observaciones ALCANZABLE / 1 NO_ALCANZABLE / 0 INCONCLUYENTE** sobre 7 observaciones
(8 hechos, 7 golds).

**Desglose que el hub necesita para adjudicar (no es decisión, es dato)** — la vara canónica no
distingue *cómo* se alcanza el ≥4/5, y aquí importa:

| clase | hechos | golds |
|---|---|---|
| ALCANZABLE porque **la base ya transmite hoy** (flip): el oráculo no aporta sobre la base | `cat001#3` (base 5/5 ×3), `cat008#3` (base 5/5 ×3), `cat016#1` (única rep firme tenía base 5/5; con base 0 el apéndice dio 0 y 1) | cat001, cat008, cat016 |
| ALCANZABLE porque **el oráculo levanta** una base no firme (0→5) | `hp005#3` (rep1 0→5; base ya 5/5 en las otras dos), `hp015#0` (0→5 ×2, carriers NO servidos ni en pool), `hp015#2` (0→5 ×2, carrier servido + apéndice), `hp017#1` (0→5 ×3, chunk ya servido por lane, duplicado en cabeza) | hp005, hp015, hp017 |
| NO_ALCANZABLE | `hp009#0` (0→0, 0→0, 0→3; carrier `a8d7b1a4` nunca recuperado) | hp009 |

Los tres «flip» **contradicen su etiqueta del FULL 16-ago** (`conveyed_yes 0`, `stability: flip`
en cat001/cat008/cat016): hoy la base los transmite en 3/3, 3/3 y 1/3 reps. También `hp005#3`
(`stable-miss` en el FULL) sale con base firme 2/3 hoy, y `hp015#2` (`flip`) 1/3. Solo `hp009#0`,
`hp015#0` y `hp017#1` repiten base 0/5 ×3 (los otros tres `stable-miss` del FULL; `hp017#1` es
además el atípico `raw=0 / in_pool=False`).

---

## 3 · Cota inferior de población resultante

Punto de partida (brief del hub / DEC-175 banner s321): **≥2** (`hp001#2`, `hp012#3` + `hp017#2`
probado; `hp003#4` ✅ y `cat017#2` OK ya medidos; `hp011#2` ❌ caducado; `hp013#1` `NO_ALCANZABLE`).

- **Por la vara canónica (veredicto del instrumento, hp015 como una)**: +6 observaciones ⇒
  **cota inferior ≥ 2 + 6 = 8** observaciones. Si la población se cuenta por GOLD (como DEC-175:
  «1 gold de 39»), `hp017` ya estaba dentro vía `hp017#2` ⇒ golds nuevos = {cat001, cat008,
  cat016, hp005, hp015} = **+5 ⇒ ≥7 golds**.
- **Contando solo donde el oráculo aporta sobre la base** (columna 2 de la tabla de §2): +3
  hechos (`hp005#3`, `hp015`, `hp017#1`) ⇒ **≥5**; por gold nuevo (hp017 ya contado) {hp005, hp015}
  ⇒ **≥4 golds**.
- **En todas las lecturas el número de alcanzables nuevos es ≥3** (mínimo 3 hechos / 2 golds
  «oráculo-levanta»; 6 hechos / 5 golds por la vara literal) ⇒ cae en el desenlace «≥3-4
  alcanzables» del encargo §1. Y `hp009#0` es el único NO, ganado con entrega + cobertura + texto
  del oráculo (§4).

Qué NO dice esto: no dice que haya lever (alcanzable ≠ GO; DEC-173 «un alcanzable NO es un GO»),
no localiza el fallo en retrieval vs síntesis (base y oráculo son generaciones independientes en
`serve`; DEC-173 banner), y **no reabre DEC-173** ni diseña nada. Adjudicar cuál de las dos cotas
es la de lever B (¿cuenta un flip como población?) es del hub/Alberto.

---

## 4 · Lo que dijo el oráculo en el NO (`hp009#0`) — informativo, como en `hp013#1`

Con `a8d7b1a4` (Inicio Lazo OUT / Retorno) y `dadab3e0` (bucle cerrado) admitidos las 3 veces:
- rep0 (0/5): «**Lazo analógico:** Los fragmentos disponibles no especifican una RFL para el lazo
  analógico. El lazo analógico se realiza en **bucle cerrado** [F12], sin mención de resistencia de
  fin de línea» — no nombra los terminales **Retorno** (el `valor`).
- rep1 (0/5): mismo patrón (RFL de sirenas 6,8 kΩ y RS-485 150 Ω en primer plano).
- rep2 (**3/5**): «El lazo analógico **no utiliza resistencia de fin de línea**. Se instala en
  **bucle cerrado** (retorno al panel) [F11][F12]» — lo más cerca que llegó; el juez no lo dio
  por firme (3<4), plausiblemente por no nombrar los terminales `Retorno`.
⇒ El modelo, con el carrier delante, contesta la pregunta («¿qué RFL?») con las RFL que SÍ existen
(sirenas, RS-485) y relega el lazo a una nota; el hecho exige NEGAR la premisa y nombrar `Retorno`.
Igual que `hp013#1`: caso de conducta/gold-review más que de serving. **N=3 y máx 3/5**: no es
un 0/5 rotundo; si el hub quiere separar «inestable» de «no», hace falta más N (fuera del encargo).

---

## 5 · Hallazgos sobre el instrumento (NO tocado; para deuda o dúo)

1. **`RECEIPT` apunta al FULL del 1-ago** (`scripts/s293_reachability_probe.py:55` →
   `evals/s100_factlevel_full_v32_full_20260801.yaml`): pregunta, `valor`, `texto` y `pool_ids`
   salen de ese recibo, no del FULL 16-ago que motiva el encargo. **Verificado sin efecto aquí**
   (key/valor/texto/question idénticos en ambos YAML para los 8 hechos), pero un gold editado tras
   el 1-ago se mediría con el texto viejo, y la resolución de prefijos cortos usa el pool viejo.
2. **Selección de span en `appendix` sin guard de cobertura**: toma la PRIMERA línea (split en
   `.;:` y saltos) que casa el regex con `len>25`. Consecuencias vistas: (a) elige líneas que no
   cubren el hecho (`cat016#1` run1: «elementos» casó la frase de la autobúsqueda; `hp015#0` run1:
   «gama convencional») y **nada lo detecta salvo la atestación del operador**; (b) las listas
   «etiqueta: definición» se parten en el «:» y la etiqueta cae por el guard (`hp017#1`: «*
   Instrucción de entrada:» = 25 chars) ⇒ «no construible» con el carrier servido; (c) un span de
   una sola frase **no puede cubrir hechos de dos frases** (`cat016#1`: menú ZONA y menú ELEMENTOS
   están en bullets distintos; `hp009#0`) ⇒ en `appendix` un NO no es atestable para esos hechos.
3. **Un `SystemExit` en una rep tardía tira las reps anteriores**: `hp009#0` appendix juzgó rep0 y
   rep1 (0→0 ×2, ~20 llamadas al juez) y abortó en rep2 («no construible» porque el set servido
   cambió) **sin escribir recibo**; la evidencia solo queda en el log. Y muestra que «construible»
   es por-rep (retrieval no determinista).
4. **Sin coste**: la sonda no imprime ni guarda coste (el encargo pedía «coste si lo imprime»).
5. **`serve` sobre un chunk ya servido por lane** (`hp017#1`): el oráculo lo duplica y lo pone con
   `similarity` máxima; `oracle_ids_admitidos` lo lista dos veces. El `ALCANZABLE` mide
   prominencia/duplicación, no evidencia ausente — el recibo no guarda la composición base para
   separarlo (limitación ya declarada en DEC-173).
6. **Sello parcial + DB en movimiento**: `git_sha` cambió 4 veces entre recibos por commits del hub
   en la misma rama, y el hub mutó doc_map/catálogo/corpus durante la medición (§7); el sello no lo
   ve (`sello_no_cubre` ya lo declara).

---

## 6 · Atestaciones de cobertura (literal, tal cual en cada JSON `cobertura_verificada`)

**`hp009#0` (el NO)**: «leido chunk a8d7b1a4 (MIE-MI-530rv001 = Manual de Instalacion Paneles de
Incendio ZX2e/ZX5e MORLEY-IAS, p19 idx24, §3.4.3.1 Conexionado de lazo analogico): «Inicie el
cableado de cada lazo (+/-) desde un extremo del conector de lazo del panel. [...] Retorne el final
del lazo al otro extremo del conector de lazo (+/-) del panel.» + Figura 9 «Inicio Lazo (+) OUT /
Inicio Lazo (-) OUT [...] (+) Retorno / (-) Retorno» + Figura 10 «All lines form a complete loop
circuit» — cubre el valor Retorno y el predicado (bucle cerrado: sale por Inicio Lazo OUT y vuelve
por los terminales Retorno del mismo conector); leido chunk dadab3e0 (MIE-MI-530rv001 p17 idx21,
§3.4.3 Lazos Analogicos): «El cableado de lazo analogico debe instalarse en bucle cerrado con los
aisladores de cortocircuito necesarios [...]» — cubre «bucle cerrado». CAVEAT declarado: la negacion
«NO se cierra con una resistencia de fin de linea» NO aparece literal en el manual (grep del doc:
RFL solo se prescribe para sirenas 6.8k, idx25/27, y RS485 150 ohm, idx35); se infiere del bucle
cerrado con retorno al panel. a8d7b1a4 NO esta en served_ids ni en pool_ids del FULL 16-ago
(carrier nunca recuperado); sin chunk_index duplicados para idx24/idx21 (1 fila por idx, verificado
s324b via REST source_file+chunk_index).»

**`hp005#3`**: «leido chunk 29270029 (MPDT190 = Panel ID3000 Manual de programacion MP-DT-190_D,
p76 idx94, §7.6.1.3): pantallas «Selecc. definicion de SALIDA:- 1: Salidas activadas | 2:
TRANSFERIR FLAG | 3: Sistema de EXTINCION» y «1:Un modulo especificado | 2:TODAS SALIDAS:
Subzona/Zona/Central | 3:CIRCUITO SIRENA/RELE» — cubre el valor CIRCUITO SIRENA y el predicado
(Salidas activadas -> CIRCUITO SIRENA/RELE o TODAS SALIDAS: Subzona/Zona/Central); leido chunk
b92ecc4a (MPDT190 p78 idx96, §7.6.2.2 Todas salidas: Subzona, zona o central): «¿Limitado por TIPO?
1:TODOS LOS MODULOS DE SALIDA 2:TODOS LOS MODULOS DE SIRENA 3:TODOS LOS MODULOS DE CONTROL» +
«Limitado por tipo: Seleccione TODOS LOS MODULOS DE SALIDA o limite a un tipo de modulo» — cubre
«limitando por tipo a los modulos de sirena»; leido chunk 33603a2d (MPDT190 p80 idx99, §7.6.2.3
Circuito de sirena/rele): «Este procedimiento es el mismo que el descrito para TODAS LAS SALIDAS
excepto en que se selecciona un circuito de sirena o rele en lugar de una zona y equipo» — cubre
«un circuito de sirena concreto». Sin chunk_index duplicados en MPDT190 para 94/96/99 (3 filas para
3 idx, verificado s324b via REST source_file+chunk_index).»

**`hp015#0`**: «leido chunk 717223e7 (CCD-103_Manual_ES_FR_GB_IT p1 idx0, portada): «3 Zones
Conventional fire extinguishant control panel» / «Central Convencional de 3 Zonas de deteccion y 1
Extincion» — cubre el valor «convencional» y «3 zonas de deteccion + 1 de extincion»; leido chunk
da5d4101 (mismo doc p5 idx1, §1 Introduccion): «[...] mantenimiento de la central convencional de
extincion [...]» y «La gama de centrales de extincion de incendios esta compuesta por un unico
modelo de central de 3 zonas convencionales y 1 riesgo.» — cubre «central convencional (3 zonas + 1
extincion)». CAVEAT declarado: la consecuencia «no direcciona equipos individualmente, por lo que NO
existe desactivar un detector concreto» no aparece literal (se infiere de «convencional»; el manual
solo describe desconexion por ZONA, servida hoy en F1/F2). Ninguno de los dos esta en served_ids ni
pool_ids del FULL 16-ago; el appendix con el regex del encargo (run1, conservado en scratchpad)
selecciono «compatible con los detectores de la gama convencional» (fdb14497 idx10 p15), que NO
cubre el hecho. Sin chunk_index duplicados para idx0/idx1 (2 filas para 2 idx, verificado s324b via
REST source_file+chunk_index).»

**`hp017#1`**: «leido chunk d27b1a1b (997-671-005-3_Configuration_ES = Manual de configuracion de la
central PEARL, p41 idx73, Apendice 5 Programacion de causa-efecto §A5.1): «Una regla consta de dos
instrucciones de accion, como se explica a continuacion: * Instruccion de entrada: esta parte de la
regla es una condicion de entrada, como una alarma, una averia o la deteccion de un cambio de estado
en una determinada categoria de entrada [...] * Instruccion de salida: esta parte de la regla solo
puede procesarse cuando se cumplen todas las condiciones de entrada programadas. La salida se
refiere al accionamiento de uno o mas equipos asignados, como sirenas o reles [...]» — cubre el
valor «instruccion de entrada» y el predicado completo (regla = INSTRUCCION DE ENTRADA condicion +
INSTRUCCION DE SALIDA equipo a accionar: sirenas o reles). Es el chunk apendizado por
same_blob_structural_neighbor_coverage_v1 en el FULL 16-ago (served_support_votes 5/5; raw=0,
in_pool=False). El appendix con el regex del encargo NO es construible por el instrumento: la linea
«* Instruccion de entrada:» mide exactamente 25 chars y el split en «:» la separa de su definicion
(guard len>25). Sin chunk_index duplicados para idx73 (1 fila, verificado s324b via REST
source_file+chunk_index).»

Los `appendix` finales (`cat001#3`, `cat008#3`, `cat016#1`, `hp015#2`) no llevan atestación: son
`ALCANZABLE` (positivo, no la necesita) y en `cat001#3`/`cat008#3` la base ya era firme, así que el
span no decide nada.

---

## 7 · Caveat de contexto: la DB se movió durante la medición (sesión hub en paralelo, misma rama)

Recibos del hub con hora local: 20:50:31 `s324b_r1prima_aplicar` (3 filas doc_map / 62 entries,
Kidde 2X-A/2X-AT); **21:25:11 `s324b_retirar_docs_aplicar`** (2 bajas de corpus: Vision Supra
tarjetas idiomas + MADT190P PT); **21:35:09 `s324b_lote_0c_aplicar`** (21 altas, 7 alias, 26 filas
doc_map — Kidde Excellence, Spectrex S40, ID2NET/CLSS, NFXI-BSF-WCH…). Mis recibos (mtime):
cat001 20:53 · cat008 20:56 · cat016 21:05 · hp005 21:15 · hp009 21:24 · hp015#0 21:31 ·
hp015#2 21:35 · hp017#1 21:41. ⇒ hp015#0-serve, hp015#2 y hp017#1 corrieron tras las 2 bajas;
hp017#1 tras el lote §0.C. Ninguna de las familias tocadas es la de los golds medidos (PEARL,
M710/MI-DMMI, CAD-150, ID3000, ZXe, CCD-103); la única duda es `MADT190P PT` (¿doc ID3000 en
portugués?) y `hp005` terminó ANTES de esa baja. **No verificado más allá de esto**; el sello no lo
cubre.

---

## 8 · Ficheros y comandos

Recibos escritos por la sonda (`evals/`): `s293_reachability_cat001_cat001_3.json`,
`s293_reachability_cat008_cat008_3.json`, `s293_reachability_cat016_cat016_1.json` (run2),
`s293_reachability_hp005_hp005_3.json`, `s293_reachability_hp009_hp009_0.json`,
`s293_reachability_hp015_hp015_0.json` (serve), `s293_reachability_hp015_hp015_2.json` (run2),
`s293_reachability_hp017_hp017_1.json`. Este agregado: `evals/s321_poblacion_etapa3_v1.md`.

Copias de los run1 sustituidos (fuera del repo, scratchpad de la sesión
`C:\Users\Admin\AppData\Local\Temp\claude\C--dev-technical-bot\33fcbf8d-1ebe-416c-9480-14a7ea1675e2\scratchpad\`):
`s293_reachability_cat016_cat016_1__run1_spangrep_encargo_span_no_cubre.json`,
`s293_reachability_hp015_hp015_0__run1_appendix_convencional_span_no_cubre.json`, y los logs
`probe_*.log` de las 14 invocaciones (incluido `probe_hp009_0_appendix.log` con las 2 reps que la
sonda no llegó a escribir).

Comandos (todos desde `C:\dev\technical_bot`, `PYTHONIOENCODING=utf-8`; los `serve` con la
atestación completa de §6 en `--cobertura-verificada`):
```
python scripts/s293_reachability_probe.py cat001 cat001#3 appendix --span-grep "25 equipos|20 equipos|32 equipos" 3
python scripts/s293_reachability_probe.py cat008 cat008#3 appendix --span-grep "Entrada del lazo|Salida del lazo" 3
python scripts/s293_reachability_probe.py cat016 cat016#1 appendix --span-grep "ELEMENTO|men[úu] ZONA" 3            # run1 → INCONCLUYENTE_SIN_COBERTURA_ATESTADA (span no cubre)
python scripts/s293_reachability_probe.py cat016 cat016#1 appendix --span-grep "acceda al men[úu] ZONA" 3           # run2 (recibo final)
python scripts/s293_reachability_probe.py hp005 hp005#3 appendix --span-grep "CIRCUITO SIRENA" 3                     # no construible (sin recibo)
python scripts/s293_reachability_probe.py hp005 hp005#3 serve --inject 29270029-d8bb-481e-b700-46ca50377269,b92ecc4a-23ad-4f1f-bbf6-3778bebbbcc8,33603a2d-d152-4b76-b686-0e62b80dbee6 3 --cobertura-verificada '…'
python scripts/s293_reachability_probe.py hp009 hp009#0 appendix --span-grep "Retorno|bucle cerrado|Inicio Lazo" 3   # rep0/rep1 0→0, rep2 no construible (sin recibo)
python scripts/s293_reachability_probe.py hp009 hp009#0 serve --inject a8d7b1a4-41a2-4ee7-9733-fa541bf6552a,dadab3e0-58d8-4346-b4fa-adf6b22f2c31 3 --cobertura-verificada '…'
python scripts/s293_reachability_probe.py hp015 hp015#0 appendix --span-grep "convencional" 3                        # run1 → INCONCLUYENTE_SIN_COBERTURA_ATESTADA (span no cubre)
python scripts/s293_reachability_probe.py hp015 hp015#0 serve --inject 717223e7-46dd-41a8-90f9-5cf7596b621e,da5d4101-1f51-4b29-9edc-6404aa3b8628 3 --cobertura-verificada '…'
python scripts/s293_reachability_probe.py hp015 hp015#2 appendix --span-grep "32 detectores|32 equipos" 3            # no construible (sin recibo)
python scripts/s293_reachability_probe.py hp015 hp015#2 appendix --span-grep "por zona son 32" 3                    # recibo final
python scripts/s293_reachability_probe.py hp017 hp017#1 appendix --span-grep "[Ii]nstrucci[óo]n de [Ee]ntrada" 3     # no construible (sin recibo)
python scripts/s293_reachability_probe.py hp017 hp017#1 serve --inject d27b1a1b-69cd-4318-a459-f3c86eb757ba 3 --cobertura-verificada '…'
```
Verificación de carriers antes de inyectar: lectura del `content` por REST (`chunks_v2`, filtro
`id=in.(…)` y `source_file=eq.…&chunk_index=in.(…)` para detectar `chunk_index` duplicados; `like`
sobre uuid no se usó), con las credenciales del `.env` (`SUPABASE_URL` / `SUPABASE_SERVICE_KEY`,
`src.http_pool.abierto`).
