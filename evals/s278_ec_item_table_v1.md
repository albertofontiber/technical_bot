# s278 — Evidence Contract: tabla por-ítem de los 29 FAIL (diseño v2 §5, ANÁLISIS)

**Fuente de verdad:** `adjudication.json` (91 ítems, 29 `ADJUDICATED_FAIL`) + los receipts por
réplica (`replicas/*.json`, campo `served_context` y `retrieval.pool`) del run congelado
`run-p1-v3-b92ff51-20260722a` (READ-ONLY). La columna «¿evidencia servida?» está verificada
**contra el receipt de esa réplica**, no heredada del handoff §5. Notación: `F#` = posición del
chunk en `served_context` (1-based); ids abreviados a 8 hex.

Clases de remedio: **APPEND** (span exacto anexable con cita) · **DISCLOSE** (conflicto/atribución
declarable) · **ARITHMETIC** (derivación trazable con operandos citados) · **EDICIÓN** (retractación
o edición inline — residual declarado de esta fase) · **FUENTE** (la evidencia NO estaba servida —
la cubren §1-§4 del diseño).

## Tabla por-ítem

| # | qid:replica · ítem | Obligación (1 línea) | ¿Evidencia en el CONTEXTO SERVIDO? (receipt) | Clase | Clase EC | Nota |
|---|---|---|---|---|---|---|
| 1 | cat017:r1 · cat017#4:CLSS | Con CLSS: crear sitio/edificio en el portal + generar fichero de licencia `.bin` | **NO** — chunk `b7633e98` (HOP-138-8ES p5) ausente de served (12) **y del pool (52)**; «sitio/edificio» y «.bin» no aparecen en ningún chunk servido | FUENTE (§2+§4) | procedure | «licencia» genérica sí servida (F10 `e472044e` p15: hace falta licencia CLIP vía CLSS) pero sin portal/sitio/`.bin`: append no puede construir el procedimiento |
| 2 | cat017:r2 · cat017#4:CLSS | Ídem r1 | **NO** — `b7633e98` ausente de served (12) y del pool (54); mismos negativos | FUENTE (§2+§4) | procedure | Mismo patrón que r1 |
| 3 | cat019:r1 · cat019#3:salidas | Las maniobras actúan sobre sirenas **o módulos de control** | **NO** — chunk `f68f2d40` (MC-380 p10) ausente de served (12) y del pool (37); «módulos de control» en ningún chunk servido (10/12 hablan de maniobras, ninguno con ese alcance) | FUENTE (§4) | universal | Bloqueo = autoridad/serving (lineage + prosa), no corpus |
| 4 | cat019:r2 · cat019#3:salidas | Ídem r1 | **NO** — `f68f2d40` ausente de served (12) y del pool (36) | FUENTE (§4) | universal | Mismo patrón que r1 |
| 5 | hp002:r1 · hp002#banked:obl_b6f6211be439 | Advertencia obligatoria: bloquear/desconectar controles de incendio, alertas remotas **y zonas de extinción** antes del mantenimiento | **NO (completa)** — `5b6a3a19` (ASD535 p121, §9.3, la advertencia íntegra) está en el **pool #28 pero NO servido**; lo servido solo tiene la versión parcial de puesta-en-marcha (F8 `6d5a807f` p102, sin «zonas de extinción») | FUENTE (§3) | safety | EC no puede anexar la cláusula íntegra desde lo servido; r2 sí lo llevó en prefijo y pasó |
| 6 | hp005:r2 · hp005#3:CIRCUITO SIRENA | La salida al circuito de sirena debe llevar **cita local inline** válida | **SÍ** — F11 `66946fcc` (MCDT190 p50) y F12 `42baf5eb` (MCDT191 p77) respaldan la afirmación | EDICIÓN | attribution | El contrato exige `valid_local_citation_required` en la claim; un append no convierte en citada la frase inline → residual declarado (diseño v2 §5) |
| 7 | hp011:r1 · hp011#1:r.I | Tabla r.I: `--` = rearme inhibido hasta fin de extinción/t.A; `00` = rearme en cualquier momento | **SÍ** — F13 `475a8f18` (HLSI-MN-103_RP1r-Supra p63) contiene la tabla completa (`--`, `00`, `t.A`) | EDICIÓN | relation | La respuesta ASIGNÓ a `00` la semántica de `--`: hace falta retractación (solo-append contradiría el cuerpo) → residual declarado. OJO: el span servido lleva marcas de tachado OCR (`~~- -~~`, `~~t.A~~`) — la cita EC debe manejar ese markup; ambigüedad declarada |
| 8 | hp011:r2 · hp011#1:r.I | Ídem: falta por completo el valor `--` y su condición t.A (00/01-30 correctos) | **SÍ** — F13 `475a8f18` (mismo span, servido) | APPEND | relation | Anexar la fila `--` con cita al chunk exacto; misma nota OCR-tachado que r1 |
| 9 | hp012:r1 · hp012#2:2 lazos / 396 | Doc España limita AFP1010 a 2 lazos/396 dispositivos, con atribución | **SÍ** — F2 `5730afb3` (MPDT280 p3): «limitado a un máximo de dos LIB-200 (un total de 396 dispositivos)»; F11 `a29b608d` (15088SP p61) acredita LIB-200 = 1 SLC | DISCLOSE | attribution | Atribución al doc español + conflicto con el US declarables con append citado |
| 10 | hp012:r1 · hp012#3:4 lazos / 792 | 4 lazos/792 dispositivos con atribución US (PN 15088SP) + disclosure del conflicto | **PARCIAL** — «792» NO está en ningún chunk servido; los operandos SÍ: F11 `a29b608d` (15088SP p61): «cada LIB… hasta 99 detectores… hasta 99 estaciones» + «máximo de dos LIB-400s (un total de cuatro SLCs)» | ARITHMETIC | arithmetic | Derivación trazable `4 × (99+99) = 792` con operandos citados; NUNCA el literal a secas (diseño v2 §5) |
| 11 | hp012:r2 · hp012#2:2 lazos / 396 | Ídem r1 | **SÍ** — F1 `5730afb3` (MPDT280 p3) + F11 `a29b608d` (15088SP p61) | DISCLOSE | attribution | Ídem r1 |
| 12 | hp012:r2 · hp012#3:4 lazos / 792 | Ídem r1 | **PARCIAL** — «792» no servido; operandos en F11 `a29b608d` (servido) | ARITHMETIC | arithmetic | Ídem r1 |
| 13 | hp014:r1 · hp014#3:35 | Compuesto: pantalla continua en todo el lazo + máx 35 Ω + comprobación uniendo B+/B− y midiendo en A+/A− | **SÍ** — F11 `d4018c9b` (MIDT180 p17) contiene las tres cláusulas contiguas (d/e + método) | APPEND | relation | Un solo span cubre el compuesto entero; agrupar unidades adyacentes (mecánica EC) |
| 14 | hp014:r2 · hp014#0:25 | Relación: 32 equipos máx según EN54-2 vs restricción más severa ID2000 25 (20 con FET) | **SÍ** — F4 `330d7551` (MIDT180 p20): «máximo de 32 equipos de lazo» (EN54-2 12.5.2) + «En la central ID2000, no… más de 25 (20 si FET)» contiguos | APPEND | relation | El body atribuye 25/20 a EN54-2 (atribución errónea): el append correcto dispara la validación de contradicción del post-writer → disclose; si el adjudicador exige retirar la frase, cae a EDICIÓN |
| 15 | hp014:r2 · hp014#1:continuidad | Precaución: probar continuidad con baja tensión; nunca Megger/alta tensión | **SÍ** — F4 `330d7551` (MIDT180 p20): «no utilice multímetros de alta tensión (como "Meggers")… sino multímetros de baja tensión» | APPEND | safety | Cláusula de seguridad exacta anexable con cita |
| 16 | hp014:r2 · hp014#3:35 | Ídem #13 | **SÍ** — F11 `d4018c9b` (MIDT180 p17, servido también en r2) | APPEND | relation | Ídem r1 |
| 17 | hp017:r1 · hp017#2:Editar Configuracion | Ruta «Editar Configuración»→«Causa y Efecto» + identificar Regla 1 + «CUALQUIER entrada de alarma activa TODOS los equipos de salida» + eliminarla | **PARCIAL→NO** — la ruta y «dos reglas por defecto… Deben eliminarse» SÍ (F11 `a95f8659` p45), pero el span «Regla 1: CUALQUIER entrada… TODOS los equipos de salida» (chunk `94cbb0ce`, Configuration_ES p43) **NO servido y NO está en el pool (36)** | FUENTE | procedure | **Corrige el techo del diseño**: EC no puede completar honestamente el compuesto en esta réplica. No cubierta explícitamente por §1-§4; la varianza de pool entre réplicas (36/35/43; `94cbb0ce` solo entró en r2) es coherente con el diagnóstico LIMIT-sin-orden (§1b) — hipótesis, no causa probada |
| 18 | hp017:r1 · hp017#3:disclosure_DEC128 | Declarar la discrepancia: prosa dice «seis tipos» de retardo, la tabla servida lista SIETE etiquetas | **SÍ** — F1 `570d9951` (p44): «uno de seis tipos de retardo» + F2 `7e34cb72` (p44): tabla con 7 etiquetas (Fijo/Estándar/No Silenc/Est. Ext./RetExtStd/No Sil. Ext/SinRetExt) | DISCLOSE | attribution | Ambas superficies servidas → el conflicto es declarable citando ambos chunks |
| 19 | hp017:r2 · hp017#2:Editar Configuracion | Ídem #17 (aquí solo faltó el encabezado de acceso: «Causa y Efecto» desde «Editar Configuración») | **SÍ** — F9 `94cbb0ce` (p43) servido: ruta + Regla 1 + comportamiento completos; F6 `a95f8659` (p45) también con la ruta | APPEND | procedure | La única réplica de hp017 con `94cbb0ce` servido (y en pool); anexar la ruta con cita |
| 20 | hp017:r2 · hp017#3:disclosure_DEC128 | Ídem #18 | **SÍ** — F1 `570d9951` + F2 `7e34cb72` (ambos servidos) | DISCLOSE | attribution | Ídem #18 |
| 21 | hp017:r3 · hp017#2:Editar Configuracion | Ídem #17 | **PARCIAL→NO** — ruta SÍ (F11 `a95f8659` p45); span Regla-1-default (`94cbb0ce`) **NO servido y NO en pool (43)** | FUENTE | procedure | Mismo patrón que r1 (ítem #17) |
| 22 | hp017:r3 · hp017#3:disclosure_DEC128 | Ídem #18 | **SÍ** — F2 `570d9951` + F3 `7e34cb72` (ambos servidos) | DISCLOSE | attribution | Ídem #18 |
| 23 | hp018:r1 · hp018#0:4 circuitos | ZX2e = 2 / ZX5e = 4 circuitos de sirena supervisados, acreditado en MIE-MI-530 | **NO** — ningún chunk MIE-MI-530 en served ni en el pool (54); todo el contexto es ZXAE/ZXEE (MIE-MI-310/MP-310/MU-310/MP-315) | FUENTE (§1a) | relation | Política identidad `add` retuvo el paraguas ZXE → familia equivocada servida |
| 24 | hp018:r1 · hp018#1:6K8 | RFL 6K8 0,5 W en la última sirena, acreditado para ZX2e/ZX5e en MIE-MI-530 | **NO** — el valor aparece solo en chunks MIE-MI-310 (familia ZXAE/ZXEE); MIE-MI-530 ausente | FUENTE (§1a) | relation | Coincidencia numérica de otra familia no satisface el binding producto/revisión |
| 25 | hp018:r1 · hp018#2:diodo | Cada sirena con diodo integrado + diodo añadido a cada dispositivo no polarizado (MIE-MI-530) | **NO** — MIE-MI-530 ausente; «diodo» solo en F11 `692718af` (MIE-MI-310 p18) | FUENTE (§1a) | universal | Ídem binding de fuente |
| 26 | hp018:r1 · hp018#3:Sirenas A,B,C,D | Conexión en bloques de placa ZX2e/ZX5e (Figuras 13/14), terminales A/B/C/D y polaridad | **NO** — MIE-MI-530 (Figs. 13/14) ausente de served y pool | FUENTE (§1a) | relation | — |
| 27 | hp018:r1 · hp018#4:1 A | 1 A máx por circuito, acreditado para ZX2e/ZX5e en MIE-MI-530 | **NO** — «1 A» solo en chunks MIE-MI-310/MU-310 (otra familia); MIE-MI-530 ausente | FUENTE (§1a) | relation | — |
| 28 | hp018:r2 · hp018#0:4 circuitos | El compuesto incluye: cada circuito supervisado ante cortocircuito **y** circuito abierto | **SÍ** — F11 `90d51dac` (MIE-MI-530rv001 p20): «Cada circuito de sirena se supervisa ante cortocircuito y circuito abierto» | APPEND | relation | Coincide con el rationale del adjudicador («el contexto F11 sí contiene la cláusula») — verificado en receipt |
| 29 | hp018:r2 · hp018#2:diodo | Cada sirena debe llevar un diodo integrado (además del diodo en no-polarizados, que sí está) | **SÍ** — F4 `72fc4c53` (MIE-MI-530rv001 p21): «Cada sirena deberá tener un diodo integrado, para impedir el consumo en polarización inversa» | APPEND | universal | Ídem — el receipt confirma la posición F4 citada por el adjudicador |

## Totales por clase

| Clase | n | Ítems |
|---|---:|---|
| APPEND-alcanzable | 8 | hp011:r2 · hp014:r1#3 · hp014:r2#0 · hp014:r2#1 · hp014:r2#3 · hp017:r2#2 · hp018:r2#0 · hp018:r2#2 |
| DISCLOSE-alcanzable | 5 | hp012:r1#2 · hp012:r2#2 · hp017:r1#3 · hp017:r2#3 · hp017:r3#3 |
| ARITHMETIC | 2 | hp012:r1#3 · hp012:r2#3 |
| EDICIÓN-NECESARIA (residual declarado) | 2 | hp005:r2#3 · hp011:r1#1 |
| FUENTE (§1-§4) | 12 | cat017:r1/r2#4 · cat019:r1/r2#3 · hp002:r1 · hp017:r1#2 · hp017:r3#2 · hp018:r1#0/#1/#2/#3/#4 |
| **Total** | **29** | |

## Techo honesto de EC — CORRECCIÓN del ~17 del diseño v2

**Techo EC = APPEND + DISCLOSE + ARITHMETIC = 8 + 5 + 2 = 15/29** (no ~17).

Evidencia de la corrección (receipts, no handoff): el diseño v2 §5 (y el split causal del handoff
§5, que puso TODO hp017 en «fuente ya servida») asumía los 3 ítems `hp017#2` como alcanzables por
postgeneración. Los receipts muestran que el span «Regla 1: CUALQUIER entrada de alarma activa
TODOS los equipos de salida» (chunk `94cbb0ce`, 997-671-005-3_Configuration_ES p43) **solo fue
servido en hp017:r2** (F9; también único pool que lo contiene, 35). En hp017:r1 (pool 36) y
hp017:r3 (pool 43) no está ni en `served_context` ni en `retrieval.pool`: EC no puede anexar esa
cláusula sin inventar fuente → `hp017:r1#2` y `hp017:r3#2` pasan a FUENTE (12 en total, no 10).

Notas de alcance:

- Los 2 ARITHMETIC son válidos SOLO como derivación trazable: «792» no existe en ningún chunk
  servido de hp012 (verificado en ambas réplicas); los operandos (99+99 por LIB, 2×LIB-400 = 4
  SLC) sí están servidos y citables (`a29b608d`).
- `hp014:r2#0` está contado en APPEND pero declarado borderline: el body contiene una atribución
  errónea (25/20 como exigencia EN54-2) — si la adjudicación exige retirarla, cae a EDICIÓN y el
  techo baja a 14.
- Los 2 ítems hp017#2 reclasificados a FUENTE no están cubiertos explícitamente por §1-§4: la
  varianza de pool entre réplicas de la misma pregunta es coherente con el diagnóstico
  LIMIT-sin-orden (§1b), pero eso es hipótesis de causa, no verificación — gap a declarar en la
  fase de fuente.
- Receipts: los 17 receipts de réplicas FAIL leídos completos y legibles; única ambigüedad
  material = el markup de tachado OCR en el span r.I de hp011 (`475a8f18`), declarada en las
  filas 7-8.
