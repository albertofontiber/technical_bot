# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 19 ago 2026 (s324j — el diseño del panel a Vercel CERRADO tras seis rondas del dúo; el estado
> vigente es el bloque «Estado actual» de abajo).
>
> **El historial vive en [`docs/HISTORY.md`](HISTORY.md)** (movido en s56): log de sesiones
> s30→s55, rationale histórico de mayo 2026 (secciones originales ## 1-9, con su numeración —
> las citas antiguas tipo "PLAN §9.14" o "§660" resuelven allí), changelog y, desde s324d, el
> **archivo de los «Estado anterior» s100→s322b** (con sus anclas). Este fichero queda compacto a
> propósito: es el doc que se relee en cada arranque de sesión.
>
> **📍 Mapa canónico (un dueño por tema).** ESTE documento es el **único canónico** del
> **roadmap + estado + qué sigue**. Los demás lo referencian, NO lo duplican:
> `docs/RULER_DESIGN.md` = diseño del ruler (D1-D11 + §2 procedimiento + §8 taxonomía);
> `docs/DECISIONS.md` = el *por qué* de las decisiones med/alto; `TECH_DEBT.md` = deuda con
> triggers; `docs/ARCHITECTURE.md` = cómo funciona el sistema; `docs/HISTORY.md` = traza
> histórica (append-only). Si el rumbo aparece en dos sitios y discrepan, **manda éste**.
>
> **Principio rector.** Nada de quick fixes. Cada cambio debe ser (1) best practice con fuente
> identificable, (2) estructural — ataca la causa raíz, no el síntoma, (3) escalable a 30+
> fabricantes sin fricción por fabricante. Si una propuesta no cumple los tres, se declara como
> gap honesto.

<a id="estado-actual-s277--22-jul-2026"></a>
<a id="estado-actual-s327"></a>
## Estado actual (21 ago 2026 — DOS hilos: la línea de correcciones/asunciones s332→s335 (4 lotes shipped+verificados, el 5º con gates verdes y PR pendiente), y el packet E1 CERRADO con su aprendizaje convertido en reglas)


**s334c/d/e (DEC-273) — los dos pasos que eran míos devuelven PEOR resultado que el prometido, y por eso valen.** (1) Higiene de alias: censo de los 1.175, mi regla marcó 82 y se pasaba de frenada (56 eran numéricos que `_add` ya descarta; el nº de marcas confundía CROSS-REFERENCES con categorías) → 18; y **R20 mordió: 13 son la ÚNICA vía de su producto**, 8 porque está en cuarentena y 5 porque su canónico es digit-only. **Eso INVIERTE el orden que prescribía TECH_DEBT #99**: promover primero, retirar lo redundante después. (2) Las 43 atestaciones `secondary`: **6 verificadas, 32 sin cita, 5 sin texto** — `8100e-faast` tenía 14 documentos y ni uno lo nombra. **Corrección: el «134 → 18» que di dependía del doc_map (muerto) y de los redirects (de Alberto); el suelo real sin adjudicación es 100.** APLICADO: 65 promociones con cita + 6 atestaciones leídas → **huérfanos 134 → 100**, cuarentena 520 → 455, consumibles 1.105 → 1.170; 0 gold perdidas, 0 pérdidas de modelo en el seam 1.

**s334b — Alberto no dio por buenos los 193 y tenía razón: la cifra real era 134, y el camino a ≤10 está BLOQUEADO por dos reglas mías.** (a) Mi contador de huérfanos **no seguía los `redirect`** y el resolver sí (`catalog_resolver.py:187`): 59 de los 193 nunca estuvieron perdidos. Wiki corregida a `cat._consumable` + 2 tests con control negativo. (b) Descarté los `unresolved:` por «adjudicación» cuando **promover no exige asignar fabricante** (el detector no usa el namespace). Con eso hay un lote MEDIDO que baja **134 → 18** (dry-run PASS, 0 gold perdidas, 7 ganancias, 0 pérdidas de modelo en 156 consultas) — **NO APLICADO**: el dúo r43 lo tumbó con 10 hallazgos / 10 verificados / 0 FP, y dos son reglas de esta misma sesión: **R21** («resolver H o G es adjudicación, nunca mecánica») contra los 25 redirects, y el trigger de **TECH_DEBT #99** («higiene de alias ANTES del siguiente lote grande» con >20 activados; éste activa 85 hasta en su versión más conservadora). Además: las 43 `doc_map_altas` eran atestaciones NO leídas, y las «7 ganancias» gold son en buena parte ensanche producido por el propio lote (Fable: el instrumento lo modifica el lever que valida). **Secuencia para ≤10**: higiene de alias → leer los 43 docs → 3 fusiones Morley↔Notifier (6 manuales) + 25 redirects, ambos de Alberto. 5 son irreducibles (digit-only y `EEV(2)`: el detector los excluye a propósito).

**s334 (DEC-271) — los manuales huérfanos, atacados de forma autónoma: 245 → 193.** Encargo de
Alberto con su reencuadre («la unidad es el MANUAL, no el candidate»). Dos lotes firmados de
`products_confirmar` **aplicados** por el gate de s324: **81 productos** salen de la cuarentena
(601 → 520; consumibles 1.024 → **1.105**) y **52 manuales** dejan de ser inalcanzables por nombre
de modelo. Dry-run PASS en los dos, 0 gold perdidas, 0 disparos en 36 negativos; ganan
`fidegas:cs4` (el fallo documentado del FOCO 1) y `notifier:nfs-supra` **+9 fuentes**.
**El método es lo que hay que retener: «el token está en el texto» NO es criterio de promoción.**
601 → 245 huérfanos → 157 pares clase A → 118 ids → 110 → **89 verificados con el resolver** →
**81 tras el dúo** → 52 manuales. Guardas nuevas mecánicas y agnósticas de marca (**H** homónimo
abierto · **G** gemelo · **N** no detectable · **G4** desbloqueo verificado). Dúo r42 (Sol+Fable):
**11 hallazgos, 11 verificados, 0 FP**, y dos tumbaron lote — «clase A» no prueba producto-hood
(`notifier:eia-485` **es el bus RS-485**) y **promover puede ESTRECHAR** (`8100E FAAST` 14 fuentes
→ 1; los TG pierden sus 4 manuales genéricos) = mecanismo hp009/DEC-091b, ahora **cableado como
veredicto `DESBLOQUEA_PERO_ESTRECHA`**. Tapado además un hueco del gate: medía `allowed_sources`
(sólo añade) y no `models` (resta bajo `replace`) → `scripts/s334_huerfanos_seam1.py`, 0 pérdidas
en 156 consultas. Residuo a Alberto: 5 rebrands Morley↔Notifier↔Sensitron, 4 gemelos, 8 retirados
por el dúo (`docs/DECISIONES_PENDIENTES_ALBERTO.md`).

**s332 (DEC-264) — los dos GO de la mañana, ejecutados y medidos el mismo día**: tabla ASR con
modo/case/cita por fila (bqide→Kidde reescrito con AVISO; ID↔Kidde solo-aviso case-sensitive —
ID3000 es familia real de Notifier; el «id» español no dispara) + primitiva `Asuncion`
generalizable con render DETERMINISTA en bot (confirmación 🏷/ℹ️ + sufijo citando la pregunta
base) + red F1 `brand_correction_rebuild` («me refería a Kidde» reconstruye la pregunta anterior;
`state_query_override` evita que la meta-frase sea base) + sección `asunciones` tri-estado en
trace. Dúo 13/13-0FP mató el oráculo-de-plan (v2 §9 = adjudicación); gates GC0 7/7 (off=hoy) ·
GC1 7/7 (la mañana re-jugada: contenido Kidde real donde había plantilla vacía) · GC3 4/4 ·
MT 52/52 off/on. **SHIP LISTO: Railway `ASR_AVISOS=on` + `F1_MARCA_CORRECCION=on` (flip de
Alberto) → verificación DEC-099 por VOZ** (guía: `evals/s332_gc_resultado_v1.md`). Proceso:
advisor/executor en paralelo sobre worktree compartido (E1 cazó de raíz un ciclo de imports).

**s332→s335 (DEC-264/265/268/269/270) — el día entero de conversaciones reales, pagado por capas.**
CUATRO capas vivas, cada una con su población: (1) tabla ASR observada (bqide/kide/itide→Kidde;
ID↔Kidde aviso case-sensitive); (2) plantilla determinista F1 (cue gobernado, rebuild de la BASE,
polaridad, «de» preposicional); (3) fuzzy d1 acotado al slot de corrección (guard-test en CI);
(4) clasificador Sonnet 4.6 solo en el miss (frontera del owner «¿se sostiene solo?» + regla
ANAFÓRICA v3). R8: los 5 atajos escriben estado. **s332/s332b/s333/s334: SHIPPED + FLIP ON +
VERIFICADOS en producción** (KIDE→Serie NC 14:17Z; clasificador real `correccion`/1261ms +
Morley-IAS e2e). **s335 (hoy tarde): BUILD COMPLETO con gates verdes, PR #333 pendiente de
merge/flip** — pieza A `INVENTARIO_FRASEOS` (gramática v2 del atajo: tolerancia al «.» de
Whisper + desiderativas/imperativas ES+EN con frontera censada; GB1 verde, 6 negativos técnicos)
y pieza B prompt v3 + cohorte v3 **GO 15/15 con fila OBLIGATORIA p15 3/3 y 0 falsas** (la regla
fila-obligatoria queda como regla de gate generalizable) + GB2 e2e con clasificador real
(1576 ms) y RAG Morley sin cross-brand; cruce `_SWITCH_FRASE` MEDIDO; limitación lista-parcial
DECLARADA (recibos: `evals/s335_gate_resultado_v1.md`). **Qué sigue en este hilo**: (1) merge
#333 + flip `INVENTARIO_FRASEOS=on` (Alberto) → verificación por VOZ con los puntos de Whisper
(la conversación de la tarde entera); (2) re-verificación DEC-099 por voz con fraseo NO tabulado;
(3) pieza C («sí» pelado) CENSADA en 3 casos — espera su GO con dúo propio; (4) graduación de
flags DEC-210/211 (van 10 vars de s331→s335 — el siguiente movimiento estructural).


**s331d (DEC-266, DEC-267) — el packet E1 queda CERRADO y su aprendizaje, cableado.** Alberto anotó
**las 56 filas vivas** del v3. Su pasada se midió antes de interpretarse
(`scripts/s331_censo_anotaciones.py`): 57 anotaciones → **34 decisiones distintas**, 23 duplicadas
(`morley:tg` ×15), 12 puro «OK», 4 «OK + matiz», **18 correcciones**. La medida **invalidó la
propuesta de automatización que yo iba a hacer** — P4 acierta 7/7 pero **P1 60% y P3 44%** sobre esta
población; el «lo firmaste 9 veces» del packet era una tasa base heredada del v2. Al descomponer, la
mayoría de fallos eran **incompletos, no equivocados**: cada fila pregunta UNA cosa donde el
documento plantea SEIS. **Dúo r40: 12 hallazgos, 12 confirmados, 0 FP, Fable «No SÓLIDO»** — Sol
atacó la EVIDENCIA (mi lectura del K=5 era falsa: `v5/5` son votos válidos y el panel se partió 3-2;
y «mismo id = misma decisión» es falso → la clave es **id × operación**) y Fable atacó el INSTRUMENTO
(mi censo usaba dos definiciones de «acuerdo», inflando las correcciones de 18 a 22 a mi favor).
Queda: **R9–R18** en `data/catalog/reglas_clasificacion.json` (la más cara, R10: el software es
producto consultable — 18 de sus 57 anotaciones) · **Wiki de modelos** en `/catalogo` (1.024 modelos
en 36 marcas · 55 sin manual · **245 manuales huérfanos, 184 sólo por cuarentena**) · **derivación
con guardarraíl** (34 ids → 29 listas, 2 a la espera de una frase, 3 bloqueadas; falla si una nota
suya se cae) · **rumbo Q1–Q6** con umbral medido por sub-pregunta (auto-aplicación hoy: ninguna).

**Qué sigue en este hilo**: (1) las 3 frases de `docs/DECISIONES_PENDIENTES_ALBERTO.md` (paraguas
2X-A, namespace EFS/EM 8, gama WMSOU); (2) su autorización para `accessory-of` en `relations.jsonl`,
que bloquea dos filas ya adjudicadas; (3) aplicar las 29 operaciones con gate; (4) medir los tres
detectores (R9/R11/R14) sobre 69 residuo + control limpio + los nuevos, con el coste del ground
truth presupuestado.

## Estado anterior (s331 — 20 ago 2026; variantes-en-hilo: diseño cerrado en 6 dúos y build flag-off completo M1→M3c)

**s331 (DEC-257) — el 👎 real de Alberto (Kidde 2X-AF1-FB-S, 18-ago) se convirtió en el ataque
entero**: diagnóstico mecánico anclado (la variante muere al LEER —alias de familia— y al
ARRASTRAR —hint solo bindeados—, con la re-pregunta amnésica también en PLANTILLA sin LLM),
diseño CERRADO en 6 rondas de dúo (v6 = spec vinculante, §11 = checklist B1-B11; corte
anti-parálisis adjudicado por Alberto), y **build COMPLETO flag-off** bajo el esquema
advisor/executor (Fable orquesta, Opus 5 ejecuta specs cerradas): resolución gobernada en la
seam de COMPOSICIÓN de F1 + detector de mención 2-puertas con veto multi-fabricante + gramática
de confirmación con POLARIDAD + canal estructurado `turn_identity` end-to-end + conducta
anti-re-pregunta en prompt Y plantillas. 3 flags default-off = producción byte-idéntica. Suites
completas citadas por hito. Colaterales: flake del fence IPC arreglado (adjudicado), 2 erratas
de conteo en commits declaradas, deuda #96 (espejo NON_PRODUCT_CODES). PRs #322 (mergeada) y
#323 (draft con todo el ciclo).

## Estado anterior (s330 — 20 ago 2026; el panel mide CALIDAD de uso, y la retención alcanza ya a todo)

**Qué es el sistema hoy.** El bot responde en Telegram desde manuales de ~30 fabricantes, con la
puerta de acceso viva (allowlist + invitación de un solo uso) y el **panel web en
https://technical-bot-lake.vercel.app** (DEC-244). Migraciones **019→024 aplicadas**; histórico
clasificado **109/109 en taxonomía v8**. El **enlace de invitación sale completo, de copiar y
pegar** (DEC-255): el @username del bot es identidad pública y vive en código, no en una variable de
entorno que no estaba puesta en ningún sitio.

**Lo que cambió en el bloque s326→s328e**: el panel dejó de ser telemetría y pasa a medir **uso y
calidad**. La captura de feedback ya estaba completa desde s294 —el gap era de EXPOSICIÓN—, así que
se añadió `query_clasificacion` (tabla derivada 1:1, CASCADE, desechable), un clasificador
**determinista-primero** y las vistas que lo enseñan. Sobre eso, dos decisiones de Alberto marcaron
el diseño:

- **`es_pregunta` es un EJE, no una categoría** (DEC-248). Tema y «¿esto pide algo?» son
  ortogonales; mezclarlos perdía siempre una de las dos. Las 8 vistas de análisis excluyen las
  no-preguntas —votos incluidos (024)— y las no-preguntas conservan su tema. La regla dura
  («**termina** en “?” ⇒ pregunta») la decide el código, sin LLM, y manda sobre el modelo.
  **Medido**: 93/109 los resuelve la regla; **≤1/109 falsos negativos**.
- **Las gráficas son COLUMNAS en HTML, no SVG** (DEC-250). Dos intentos con SVG fallaron por lo
  mismo: *una escala uniforme mueve el texto por definición*. En HTML 12 px son 12 px a cualquier
  anchura y solo estira la barra.

**La taxonomía v8 está ACORDADA** (DEC-251): el gate de acuerdo pasó **29/29** el 20-ago, primera
vez que pasa —la v1 sacó ~80 % y disparó el ciclo del «otros»—. Las gráficas de tipología se pueden
leer como verdad, con sus residuales declarados (`catalogo_especificaciones` = 70 % por la fusión
adjudicada; `mantenimiento_pruebas` y `normativa` sin ni una fila).

**Y lo que más vale del bloque no es una feature: cuatro promesas pasaron a ser PUERTAS**, y todas
tenían un agujero que solo apareció al **ejecutar el control negativo**:

| Antes | Ahora | Lo que el control destapó |
|---|---|---|
| El CSS del panel sin red de seguridad (`#94`) | Chromium lo mide en CI: no desborda · la letra no escala · rótulo centrado · nada cortado (DEC-249/250) | El gate se saltaba en silencio sin navegador → job verde sin medir |
| El anexo del abogado, copiado a mano (llevaba el v8 con el v9 en producción) | Se **genera del código** que se sirve (DEC-252) | El comprobador miraba el texto y no la etiqueta: un bump pasaba en verde |
| La sonda del eje, con el gatillo en un docstring | **Pre-vuelo del job**: aborta si el eje regresa (DEC-253) | — |
| El hook del digest de levers, versionado en s316 «para que viaje a cloud» | Se invoca vía `bash <script>`: **el bit deja de ser condición** (DEC-254) | Viajó sin bit de ejecución → `exit 126` en todo checkout cloud **desde s316**, en silencio (es fail-open) |

**La retención cubre las 7 tablas con dato personal** (DEC-256, s330): el job mensual que ya corría
desde el 5-ago —`rgpd_retencion_pasada`, pg_cron, ventana de 24 meses como invariante RLS— se amplía
a `bot_invitaciones`, `bot_allowlist` y `panel_usuarios`, cerrando el «PENDIENTE MATERIAL (art.
5.1.e)». **Probado (54/54 contra PostgreSQL 17 real) y APLICADO en producción el 20-ago**. Y
por el camino apareció que la sentencia del runbook para el **derecho de supresión (art. 17)** la
base la RECHAZA —estaba mal en cuatro sitios, incluido el runbook del piloto—: eso sí era un fallo
de HOY, y queda arreglado.

**Frente paralelo (s325h-e, DEC-247)**: la caché del environment **PUEDE** persistir `site-packages`
—al menos a veces—, lo que **REFUTA** la conclusión de s325h-c. Sigue sin medirse el AHORRO, y la
causa de que una VM no la recibiera sigue abierta.


### QUÉ SIGUE — un solo bloqueante, y es de Alberto

> Solo lo PENDIENTE. Lo cerrado se cuenta en «Estado actual» y en su DEC — un «qué sigue» que
> arrastra tachaduras deja de leerse.

0b. **s331 variantes-en-hilo — ✅ SHIPPED Y VERIFICADO EN PRODUCCIÓN** (DEC-257/258/**263**):
   flip de Alberto 21-ago 07:37Z (4 vars, deploy SUCCESS, interlock pasado) y **verificación
   DEC-099 CERRADA a las 07:50Z**: la conversación real re-lanzada por VOZ — T2 «¿cómo la
   programo?» responde con clarify de ASPECTO (cero re-pregunta de identidad) y T3 entrega el
   manual de FAMILIA; `turn_identity` estampado en producción
   (`evals/s331_dec099_verificacion_prod_v1.md`). Rollback = quitar las 4 vars. Residuales
   post-flip se observan con tráfico; graduación de las 4 flags cuando asienten (DEC-210/211);
   **packet Alberto**: paraguas «2X-A» diferido.
0c. **s332+s333 correcciones/asunciones visibles + clasificador de corrección — s332 FLIP ON; s333 GO en gate, flip `F1_CORRECCION_LLM=on` tras merge #329; re-verificación por voz pendiente (fraseo NO tabulado)** (DEC-264/265/268/269 — s334: fuzzy+R8 VERIFICADOS en prod 14:17Z; quedan 2 GO nuevos — «sí»-pelado (1ª observación) y fraseos de inventario del atajo; los
   dos GO de la mañana ya EJECUTADOS y con gates PASS): **Railway worker = 2 vars**:
   `ASR_AVISOS=on` + `F1_MARCA_CORRECCION=on`. **Tras el flip: verificación DEC-099 por VOZ**
   — dictar «¿Qué centrales Kidde tienes?» (si el ASR rompe la marca, la confirmación lleva el
   aviso), luego «me refería a Kidde» si hiciera falta → contenido Kidde + sufijo ℹ️; filas con
   `asunciones.status=on`. Rollback = quitar las 2 (GC0 = byte-idéntico probado). Después:
   R4 (aviso-ID) se re-adjudica con tráfico; graduación DEC-210/211 cuando asienten.
1. ⛔ **ENVIAR el paquete del abogado.** Es lo ÚNICO que bloquea invitar al primer DG. El documento
   está listo (DEC-252): anexo A con el **v9 generado del código**, anexo B con el delta v8→v9 —y el
   cambio de fondo subido a P1: la mención a las transferencias fuera de la UE **bajó** de la
   pantalla de aceptación a `/privacidad`—, **P7** (leer conversaciones desde el Explorador) y **P8**
   (clasificación con un LLM) añadidas, y **P4 con el plazo de `panel_usuarios` en 24 meses**.
   **Lo que falta: rellenar los dos `<…>` del apartado 1 (a quién y cuándo), borrar la nota de
   cabecera y mandarlo.** Todo lo demás del piloto está en verde y verificado
   (`docs/PILOTO_DG_ESTADO.md`).
2. **Re-medir el eje con datos del piloto** (~200 mensajes). El censo de hoy es PRE-piloto: 109
   mensajes de 2 personas y casi sin multi-turno. Con tráfico real sube la proporción de
   continuaciones y con ella el peso de `TECH_DEBT #92` (el clasificador no ve el hilo).
3. **Opcional, cuando el tráfico lo pida**: `CLASIFICADOR_PREGUNTAS=on` en Railway (corrida cada
   6 h). Hoy es manual y con recibo, que para 109 filas es lo correcto. Esa corrida ya lleva
   **pre-vuelo del eje**: si el prompt cambió, mide y **aborta sin escribir** si el eje regresó
   (DEC-253).
4. **Gate de EXPONER que sigue abierto**: la **medición XFF** antes de encender la mitad `ip:` del
   cerrojo (`INCLUIR_CLAVE_IP` sigue en False). **No bloquea nada** — el cerrojo por usuario
   funciona desde el día 1.
5. ~~Aplicar la purga del control de acceso~~ **APLICADA EN PRODUCCIÓN (20-ago, s330/DEC-256)**:
   postcondiciones PASS y dry-run con **0 filas tocadas** en las 7 tablas
   (`evals/s330_aplicacion_produccion_v1.json`). La primera pasada del cron (1-sep, 04:30 UTC)
   destruirá 3 vínculos de `persona_seudonimo` **sin ninguna fila identificada** —caso benigno ya
   declarado en s299— y nada más; el primer borrado con datos sería en agosto de 2028.
   · **Gap nuevo para el asesor**: `creada_por`/`revocada_por` guardan `panel:<usuario>` —posible
   correo del administrador— **sin plazo**; es dato personal de otro interesado. Merece una línea en
   el paquete.
6. **Del frente paralelo (s325h-e)**: sigue **sin medirse el AHORRO** de la caché del environment
   —la huella se movió tres veces ese día, así que la medida limpia solo sale tras un día sin tocar
   el instalador— y la causa de que una VM NO la recibiera sigue abierta.
7. **Del packet E1 — trabajar sobre el `v3`, NO sobre el v2** (s331/DEC-259→260). El packet va por
   **125 de 192 filas resueltas**; las **67 vivas** están en `evals/s320_e1_packet_adjudicacion_v3.md`,
   pre-clasificadas por los patrones que Alberto ya firmó (**15 P1** «seguir al juez», **9 P3**
   «retirar artefactos», **8 P4** suyas una a una). Lo que espera su decisión está reunido en
   **`docs/DECISIONES_PENDIENTES_ALBERTO.md`**. Lo que sigue siendo de Alberto del residuo del
   `s320_e1_packet_adjudicacion_v2.md` quedó cerrado salvo (a) **una frase sobre el paraguas «2X-A»**
   —con táctiles (38) o sin ellos (27)—, ya con la medida hecha (0 gold perdidas, +2 golds ganan 12
   fuentes cada una, 0 disparos en 111 consultas reales; solo salta la sonda sintética «2 x a»:
   `evals/s331_2xa_sonda_plan_v1.json`); (b) los **10 nombres reales con barra** (un «sí» = alta; con
   20/20MI y 20/20R **ya no** dependen de esto: la serie 20/20 entró entera en DEC-260); (c)
   **VSN2-PLUS**, censado y diferido a propósito a la sentada E1b por ser rebrand multi-marca
   (`evals/s331_vsn2plus_censo_v1.md`). **§1.A queda COMPLETA** y las 3 preguntas delegadas están
   adjudicadas y aplicadas con recibo. Los bloques **E1b (474)** y **E2 (1.361 altas)** siguen
   abiertos y son el grueso pendiente.
8. **La cola REAL de «asignar modelo a un documento» son 85 → 77 documentos activos SIN doc_map**
   (censo s331, tras enganchar los 7 de la serie 20/20): Notifier 31 · Morley 23 · Kidde 13 ·
   Spectrex 8 → 1 · Aritech 4 · Xtralis 3 · resto 3. **No vive en ningún packet** — es la lista que
   sale de cruzar `documents` activos contra `doc_map.jsonl`, y es el sitio natural para seguir
   adjudicando identidad documento a documento cuando E1b/E2 no sean la prioridad.


## Estado anterior (s324b/c — 16-17 ago 2026, misma sesión que s324; noche autónoma)

**s325b — el extraction store, a la nube (DEC-221)**: lo ÚNICO del corpus fuente que
no estaba ya en cloud (1.143 JSON / 354 MB, solo en OneDrive) vive ahora también en el
bucket privado `extraction`. `src/extraction_store.py` resuelve **disco primero,
bucket después**, así que en local nada cambia; cableados `enunciados_pass`,
`s94_f1_generate` y `src/reingest/pipeline`. Verificado contra el bucket REAL sin
disco: `_build_sha_map` da **1.136 claves, las mismas que desde disco**, en 0,5 s.
Consistencia por **puerta única**: `ingest_new` publica al bucket en el mismo acto en
que escribe (fail-open declarado), con `--verificar` por SHA como red y la `config`
como versión del mecanismo de extracción. **LÍMITE declarado**: ingestar manuales
NUEVOS sigue siendo local — `ingest_new` escribe al store y exige PDFs y sidecar en
disco. Dúo completo NO SÓLIDO → 3 críticos convergentes aplicados (faltaba un
consumidor; ingest_new es productor; la «descarga perezosa» era falsa), más un bug de
plataforma: `os.path.basename` sobre rutas Windows habría vaciado el mapa EN SILENCIO
al correr en Linux.

**Dos frentes en una sola sesión, en paralelo (Alberto: «prefiero la simplicidad de una sesión»): él
adjudica la asignación documento→modelo en los packets; yo mido la etapa 3 y aplico lo firmado (DEC-227).**
**Etapa 3, MEDIDA antes de construir**: sondas de los 8 «servido y omitido» del FULL 16-ago → 7 ALCANZABLE / 1 NO
(`hp009#0`); pero la población por gold de hoy = {hp017, hp005, hp015, hp001} = 4 y **no es una clase** (`hp015`
era DATOS —CCD-103 candidate, resuelto—, `hp001#2` within-doc NO-GO 3×, `hp005#3` omisión inestable) ⇒ **un solo
hecho pagable por serving: `hp017#1`** (cards de 360 chars cortan el bullet). Propuesta D1 «cierre de bloque de
lista» → **dúo r33 (Sol 6, Fable 5 con 14 tool_use reales): NO construir, medir antes** → medido esa noche:
**prueba offline D1** ($0, código real de coverage, fidelidad 40/40): alcanza `hp017#1` SOLO con la definición A
(blanco entre ítems no rompe), 0 hechos NO-OK adicionales, toca 6/27 filas estructurales y 9 hechos OK;
**replay congelado** de los 4 flips ($5,44, N=5 misma vista + N=3 fresco, juez K=5 intacto): **4/4 SÍNTESIS
INESTABLE**, 0 serving (con N=3 el FULL etiqueta «flip»/«stable-miss» por azar). Cifra de cabecera de DEC-175:
**1 hecho**; D1 solo con GO explícito de Alberto sobre «1». Los 3 de conducta («negar la premisa») → packet de
gold-review `evals/s324c_goldreview_conducta_packet_v1.md`.
**Catálogo (todo con las puertas de DEC-225, verificación posterior 0 fallos)**: R1' (62 entries) · §0.C (21 altas
+ 7 alias + 26 doc_map + 2 bajas; Fable standalone 6 hallazgos aplicados) · STRATOS = paraguas de familia · §0.D/§0.E
(5 docs retirados, altas Fidegas S/3-2·S/3-IR·S/2-IR y EMA1224B4R/W, TG = software, MADT731_06 → HSSD-2, 5 retags)
· **Detnov E1b** (8 confirmaciones + `detnov:ccd-103`; el gate cazó 14 alias descriptivos «2 zonas»… que la
confirmación activaba → retirados antes). **E1b PREPARADO, NO aplicado**: 13 planes + dry-run **13/13 PASS** (453
confirmables verificadas, 44 `no_aplicar` con propuesta, 132 alias descriptivos a retirar antes) —
`evals/s324c_e1b_bloques_censo_v1.md`. **Re-juicio K=5 cross-model** de las 61 «confianza media» (E1 14 + E1b 47; 3× sonnet-5 + 2× gpt-5.5, rúbrica original,
texto completo, cita verificada; ≈$6,6): 39 convergentes ≥4/5 (E1b 34 CONFIRMAR + 1 RETIRAR; E1 2 PRODUCTO_REAL + 2
ARTEFACTO), 22 no (10 con desacuerdo cross-model Sonnet↔GPT) → bloque `k5_confirmar` PREPARADO con el gate (31 PASS)
— `evals/s324c_rejuicio_k5_v1.md`. Suite verde (3.891; `test_s307` desacoplado de los datos del catálogo). Deuda nueva #89
(5 defectos del instrumento de sonda). Coste de la noche ≈ $25 (sondas ~$12, replay $5,44, K=5 ≈$6,6, resto $0). **PR #276 abierta** (rama `claude/s324b-sondas-etapa3`; la mergea Alberto).

**s324d (17-ago, mañana autónoma mientras Alberto revisa packets; DEC-228)**: E2 **re-derivado** tras los lotes
(conservador PASS · pleno STOP con las 5 pérdidas conocidas, CCD-103 ya no pierde · split 618+743); **PLAN podado**
162 KB → 17 KB (archivo íntegro en HISTORY); **#86** runner Fable audita `tool_use` reales; **#89 RESUELTO** con dúo
r34 (Sol 7/7 + Fable 1/1 aplicados): sonda con oráculo `serve` PAREADO, guard de cobertura valor+predicado,
`JUEZ_INCOMPLETO`, recibo parcial honesto, coste real, `--receipt`; **#88 PREPARADO** (55 retags `documents.pm` →
canónico E3, dry-run 55/55, nada aplicado); **#87**: sin pipeline OCR en el repo. Suite verde.

**s324d tarde (17-ago, autónoma con Alberto en paralelo; DEC-229)**: **el hallazgo que cambia el rumbo — de los 15
hechos no-OK del FULL, 9 son INESTABLES y sólo 6 son defecto real** (N=5 sobre vista congelada, $9,12): el ruler con
N=1 clasifica ~60 % de sus no-OK **por azar**. **#87 RESUELTO con su raíz real** (no era OCR: `md or text` dejaba pasar
un markdown degenerado; guarda en `src/ingestion/page_content.py`, dúo r35, TI-007 re-ingestado 47 → 3.601 chars).
**#84 corregido**: su «medido» era un NO-DATO (el flag no existe en Railway; el sub-defecto real es el join doc_map
exacto, 98/977 filas, 1 % de los chunks de golds). **#90 cerrada documentada** tras dúo r36 (Opus 5 dictaminó NO
SÓLIDO mi propuesta: mismatch de métrica del settled + una afirmación falsa; recomendación E = declarar el drop, en la
próxima ingesta). **#88 aplicado** (55 retags con CAS). Censo de corpus **completo 1.054/1.054**: 13 accionables,
**ninguno sustenta un gold**.

**s324e (17-ago) — PRIORIDAD #1 DE ALBERTO: preparar el piloto con Directores Generales (DEC-230).**
El bot tenía 96 consultas de UN usuario y 6 👎 / 0 👍, todos por el mismo fallo (hablar de otra marca).
Cableado con dúo: **puerta de acceso** por invitación de un solo uso (48 h, revocable, fail-closed con
gracia, tope diario, **chat privado obligatorio**), **errores con insights** (taxonomía por causa, red
global, `bot_errors` sin PII directa), **aislamiento por usuario PROBADO** (13 tests; cerrado el agujero de
la doble instancia que partía la sesión de un DG), y la **conducta (a)** ante marca cruzada con flag
apagado. Migraciones 015 y 016 **APLICADAS** (la 016 costó dos intentos: su validación con
`BEGIN/ROLLBACK` revertía el fichero entero — lección cableada como test). Suite 4192.

**s324f (17-ago) — LA PUERTA SE ENCENDIÓ Y EL PRIMER SMOKE REAL DESTAPÓ EL CATÁLOGO (DEC-232).**
Alberto puso `BOT_ALLOWLIST_BOOTSTRAP` + `BOT_ALLOWLIST=on` en Railway: la puerta está **ACTIVA en
producción** (log: «puerta de acceso ACTIVA … bootstrap=1 ids, tope diario=30») y su consulta la
atravesó (O2 ✅). Con eso preguntó «¿qué fabricantes tienes?» y el bot respondió **22 modelos de
756** bajo etiquetas de ingesta (`DESCARTADO`, `EN_unico`, `ES`, `PT`) y sin botones para
puntuarlo. Ninguna suite lo cazaba —los tests congelaban esa conducta como correcta—; lo cazó un
usuario en 30 segundos. Corregido con dúo r39 (13 hallazgos, ninguno SÓLIDO): la fuente pasa a
`get_manufacturers_by_docs()` (regla r27, que este atajo era el último en incumplir), se separa la
intención en el PLAN, y toda respuesta que no quepa **lo dice y ofrece el follow-up**
(`src/bot/acotar.py`, adjudicado por Alberto). **Panel web v1 construido y verificado**
(`dashboard/`, DEC-231): nada responde sin sesión, la service key no sale del servidor.

**s324f-noche (17/18-ago) — EL PILOTO ESTÁ VIVO Y YA HA ENSEÑADO CUATRO DEFECTOS (DEC-233).**
Alberto invitó a la primera usuaria (Sara, alta por invitación: **O3 verificado con tráfico
real**). En la primera hora: el bot le dijo «saturado» cuando lo que faltaba era **saldo** en la
cuenta de OpenAI de Railway (clave distinta de la local, ya corregida), y transcribió **«Detnov»
como «Death Knob»**, dejando el turno sin fabricante. Los dos arreglados y **desplegados**
(commit `5eda845`, verificado). Además, abrir el panel en un navegador destapó que **su propio
login daba 403** y que **la portada decía «0 errores» habiendo dos**. Dúo r40: Sol 8/8
confirmados — el mejor me hizo mover la corrección de voz porque rompía un contrato ya escrito.
Aviso **v9** desplegado. Suite **4373**.

**Qué sigue (s324f — VIGENTE; LO PRIMERO al abrir sesión):**
(0-0) **DE ALBERTO, cuando se levante**: (a) **volver a aceptar los términos** (`/start` +
`/accept`) — el v9 invalidó el v8, y Sara también tendrá que hacerlo; (b) **smoke de audio**
—preguntar por Detnov por voz— que es lo único que los arreglos de esta noche NO ejercitan;
(c) aplicar `migrations/017_bot_errores_clase_cuota.sql` y **sólo entonces** avisarme para
cambiar la clase en el código (al revés se pierde el registro).

(0-a) **DESPLEGAR lo de esta sesión**: PR → merge → Railway. Incluye el catálogo arreglado (que
hoy sigue roto en producción) y el panel, que además necesita **servicio Railway aparte** +
`DASHBOARD_SECRET` y `DASHBOARD_USUARIOS` (el hash lo genera
`scripts/s324f_dashboard_password.py`, que pide la contraseña por `getpass` y no guarda nada).
(0) **PILOTO DG — lo que falta es de Alberto**: (a) **abogado** = aviso v8 (redactado, 6 decisiones
resueltas) + texto de `bot_errors` + plazo de 24 meses de las tablas nuevas + el aviso de canje comunica
nombre/alias de quien canjea; **paquete listo para reenviar en `docs/PAQUETE_ABOGADO_PILOTO_DG.md`**;
(b) ✅ **HECHO** — PR #278 mergeada y Railway desplegó (SUCCESS 17-ago 16:18; log de arranque: «Bot
started» + el WARNING que declara la puerta apagada: el código está en producción e INERTE);
(c) **encender** `BOT_ALLOWLIST_BOOTSTRAP=<id>` y luego `BOT_ALLOWLIST=on`. ⚠️ **Matiz verificado
17-ago**: el motivo original del orden («al revés te quedas fuera de tu bot») **ya no aplica** — la
migración 016 hizo el bootstrap EN LA BASE y la fila de Alberto está activa (`origen=bootstrap`,
`alta_por=migracion_016`), y la puerta autoriza desde la base. Pero la variable **sigue haciendo falta
por otras dos razones**: el **aviso de canje** se manda a `ids_bootstrap()` —sin ella la contramedida
anti-reenvío se queda muda— y es el único camino que funciona con Supabase caído;
(d) invitar al PRIMER DG y hacer el **smoke real** (el harness no atraviesa `mismatch`: su testigo es
Telegram, no el eval); (e) medir la cobertura de la corrección en `rag_trace ? 'mismatch_corrected'`.
Criterio de GO: O1-O4 en `evals/s324e_allowlist_duo_r1_v1.md`; **NO-GO si fallan O1 u O4**.
(0-bis) **Pendiente técnico del piloto**: escribir la política de retención de las dos tablas nuevas en
`rgpd_retencion_pasada` (una función y dos UPDATE) cuando el abogado se pronuncie.
(0) **CABEZA DE COLA — el ruler y N=1**: decidir si los hechos no-OK se miden con N≥3 antes de etiquetarlos (9/15 son
ruido hoy). Afecta a cómo se lee CUALQUIER delta y a qué cola de defectos se ataca (6, no 15). Diseño + dúo pendientes.
(a) **Alberto, con lo preparado delante** (todo ⏳ en los packets canónicos): **bloques E1b** — un «sí» por bloque =
re-dry-run del mismo sha + `--aplicar` (cross-bloque morley↔unresolved/notifier exige adjudicar homónimos); las
3 preguntas de §0.D (MADT015_01 ¿NFS2-8?, MNDT600 ¿familia SMART 3?, MNDT701 sin id) · paraguas «2X-A» (¿con
2X-AT dentro?) · nombres con barra (10) · baja del FR `996-130` · packet **gold-review de conducta** (3 hechos ×
3 opciones) · ¿GO sobre «1 hecho» para D1? (recomendación: NO; si GO, definición A pineada + G2 antes de G3).
(b) **E2**: re-derivar snapshot + G1/G2 tras cada lote (conservador PASS hoy) antes de cualquier swap.
(c) Etapa 3 sin lever de serving: la varianza de síntesis (4/4 flips) es OTRA clase — si se quiere atacar, es
diseño nuevo con pregunta cero (¿medir con N≥5 por hecho antes de etiquetar el FULL?), no D1.
(d) ~~#89~~ ~~#86~~ hechos (s324d) · **#88: un «sí» de Alberto aplica los 55 retags** (`scripts/s324d_retag_documents_pm.py --aplicar`) ·
#87 OCR TI-007: sin pipeline OCR (Alberto aporta PDF OCR-izado o se diseña el paso con dúo) · #84 doc_map como
fuente de aplicabilidad (dúo).
(e) DEC-226 (conducta `mismatch`, decisión de producto multi-modelo) y DEC-186b siguen donde estaban.
(f) podar el PLAN (>160 KB).

## Estado anterior (s324 — 16 ago 2026)

**s324 — el residuo de los packets se adjudica por REGLAS, no por filas; y las puertas
prueban antes de escribir (DEC-225).** Alberto no firmó 911 filas: firmó **7 reglas** (R1
serie×categoría en el residuo · R2 confirmar solo modelos concretos nombrados como sujeto —
las etiquetas de familia son paraguas, nunca producto · R3 OEM no amplía `vendido_bajo` ·
R4 alta+doc_map solo con cita, jamás por ficha · R6 fuente retirada → no alta · R7 concatenados
→ componentes con cita propia · R5 → BAJA de 6 fragmentos PT con hermano ES + OCR de TI-007).
Con eso: **lote aplicado con recibo** (`evals/s324_lote_firmado_aplicar_20260816T113215Z.json`):
doc_map **+57 filas / 225 entries** (§0.B completo + §1.A por reglas + docs sustentantes), **13
altas** (KE-DP312x mini-familia + componentes R7), **7 confirmaciones** (DX1e/2e/4e + cajas —
cierra el ÚNICO agujero de paraguas del catálogo, «Dimension» 0/3 → 3/3 — y VSN 12 PLUS), 2
etiquetas retiradas (`2x-at`, `vsn-plus` → paraguas `2X-AT`/`2X-A Táctil`/`VSN PLUS`), 2 retags
DB con CAS (Qref INSPIRE mal etiquetada `CLSS-10`; KE-IO3144/IU3110 → IO3122/IO3144), 7 docs
retirados del corpus. **Todo por puertas que prueban**: cita verificada full-text en cada fila,
freeze (sha×4 + fingerprint + snapshot), build-validar-backup-swap, CAS con rollback, **censo del
radio de explosión** (detector del resolver 1.667→1.695, +28/−0; 0 gold perdidas; 0 disparos en
36 negativos; `resolve_query` sobre las 51 gold: 0 pérdidas / 9 ganancias), verificación
posterior en censo 0 fallos, suite 3.890 verde. **Dúo r32** (Sol 6/6 confirmados: freeze,
atomicidad, CAS documents, censo solo-detector, **R1' no firmada**, sobre-afirmación; Fable 5/6 +
1 premisa falsa) aplicado ENTERO antes de escribir. **Puerta A rehecha y VALIDADA** (predicado de
reconstruibilidad: 5/5 positivos, 3/3 negativos) — 0/18 filas RETIRAR de E1b son de esa clase
(palabras genéricas/part-numbers → siguen en cuarentena). Los packets que Alberto abre llevan el
ESTADO fila a fila (✅ resuelto / ⏳ suyo). **Deuda nueva #86** (Fable fabricó una transcripción
de tools: 0 `tool_use` reales; el emparejamiento se rompió al mover HEAD durante su run), **#87**
(ingestas vacías <300 chars: TI-007 47 chars, QR Morley-IAS Max 142 → OCR/baja), **#88**
(`documents.product_model` con artefactos residuales tras E3: TO-3200M, LOCAL-360…).

**Qué sigue (s324 — VIGENTE, consolidado; LO PRIMERO al abrir sesión):**
(a) **lo que solo puede firmar Alberto** (todo listado en el bloque 🟢 al inicio de
`s320_e1_packet_adjudicacion_v2.md`): **R1'** («si el doc NOMBRA modelos, atestar solo los
nombrados» — 3 docs 2X-A/2X-AT en espera), §0.C/§0.D/§0.E de E1 (sus «sí» pasan por el gate del
detector), nombres reales con barra (10), paraguas «2X-A» (frenado por el gate léxico), baja del
fragmento FR `996-130`, VSN2-PLUS/«Plus2»; los bloques E1b (474) y E2 (562) siguen abiertos y su
«sí» se aplica por lotes MEDIDOS (censo + gate), no en seco. (b) **Re-juicio K=5 cross-model** de
la clase «confianza media con sujeto nombrado» (E1 14 + E1b 42) → lo convergente sube a bloque
(NO se aplica). (c) **Re-derivar el snapshot E2** (`s320_e2_snapshot_derivado.py`) y pasar G1/G2
tras el cambio de catálogo, antes de cualquier swap. (d) **#80/#81**: las fases A (repunte 49), B (resolución TIPADA en la ingesta) y C
(gate de invariantes corpus↔catálogo) quedaron APLICADAS en s323 (PRs #266–#268); resta solo el
backfill #81 por igualdad exacta de sha → packet (pocos o ningún caso, y es lo correcto). (e) ~~**FULL fresco v3.2** — sigue sin medirse el bot e2e desde el elefante~~ **HECHO (16-ago tarde, PR #273): 116/135 OK (86%), paridad con s291; los 6 golds de la sentada por hecho = lo pretendido, 0 regresiones; fila 2026-08-16b en el scoreboard.** El censo; el censo
de s324 NO mide retrieval/generación. (f) smoke de recepción en cloud (DEC-220). (g) OCR de TI-007
+ censo de ingestas vacías (#87). (h) #86: endurecer el runner Fable (exigir `tool_use` reales o
marcar `sin_tools`) y no commitear durante un run emparejado. (i) **s321-ruler: su «Qué sigue» de la MAÑANA está SUPERADO por la tarde autónoma (PRs #273/#274).**
Estado real de los 5: **re-medir factlevel HECHO** (smoke #271 + FULL #273) · **#84 «medido»** — ⚠️ **s324d: era un NO-DATO** (el flag `ANSWER_OBLIGATION_PLANNER` no existe en Railway ⇒ `_product_aligned_chunks` no corre en producción; ver `TECH_DEBT #84`) · **sonda `hp013#1` hecha** (NO_ALCANZABLE; sale
de la población de lever B, que queda en ≥2) · **conducta (a) del `mismatch` NO cableada A PROPÓSITO**
(DEC-226: 4 subsistemas + una decisión de producto de Alberto) · **DEC-186b NO escrita A PROPÓSITO**
(reconciliación de 4 docs + prereg + pregunta cero de Alberto).
(j) **NUEVO, del FULL — la cola de síntesis DIMENSIONADA**: de los 19 hechos no-OK, **12 son de síntesis
y 10 de ellos son «servido y OMITIDO»** (el carrier llega al generador y el LLM no lo dice), repartidos
**1 por gold en 10 preguntas distintas** — no hay preguntas rotas, hay UN mecanismo. Solo **4 de los 12
tienen sonda de alcanzabilidad** (Protocolo 4): `hp017#2` y `hp003#4` **atacables PROBADOS** (0/5→5/5),
`hp011#2` **no** (0/5→0/5), `cat017#2` ya flipeó a OK. **Los 8 restantes están SIN SONDAR, ~$1 cada uno**
⇒ el movimiento barato y correcto antes de diseñar ningún lever es **sondarlos** y saber si hay población
(la pregunta abierta de DEC-175). Análisis: `evals/s321_full_analisis_fallos_v1.md`; **encargo listo para ejecutar** (los 8 con su modo, su `--span-grep` propuesto y las 3 trampas conocidas): `evals/s321_encargo_sondas_etapa3_v1.md`.

## Estado anterior (s321-ruler — 16 ago 2026, sesión paralela)

**s321 — la sentada B2 APLICADA al ruler (DEC-224), y por el camino el instrumento se
arregló dos veces.** Arrancó como una pregunta de Alberto sobre el ítem 2 del packet y
acabó así: (1) **DEC-186 en revisión** — el «techo del modelo» de s305 nunca leyó al juez
(`sum()` sobre un dict → constante 2; TECH_DEBT #75) y su «NO alcanzable» de `hp017#2` no
era una medición: la sonda de alcanzabilidad se **endureció** (prueba de entrega +
cobertura atestada, `scripts/reachability_verdict.py`, 10 tests) y **DEC-173/175 reabiertas**
(la población de lever B es ≥3, no 1). (2) **DEC-221**: el gold se ancla en el pasaje que da
el **mecanismo** — nació de un caso (PEARL A5.2/A5.4) y se pagó solo en el siguiente (ISO-X
p17/p77). (3) **DEC-223**: el ISO-X **no** acota un fallo de tierra — cerrado dentro del manual
aplicable, y con el razonamiento de Alberto («si lo acotara no verías 'Tierra'»). (4) **DEC-224**:
los 6 golds de la sentada escritos vía `gold_store` con verificación COMPLETA (render ±1 →
cazó un off-by-one en MI-716; GPT-5.5 en frío coincidente 7/7; localización ES+EN por
`doc_map`), cascada s277 + canarios en el mismo commit, **sin migración de índices** (no partir
`hp017#2`, que es release_guard). Y la **conducta ante marca↔producto errónea pasa a (a)
«corregir Y responder»** — decisión de producto, **pendiente de cablear** (serving, dúo, PR
propio); `hp002` NO es su testigo (el harness no atraviesa `mismatch`). Deuda nueva: **#83**
(capa visual de criticidad perdida), **#84** (`product_model` ≠ aplicabilidad: 35% de discrepancia
con `doc_map`, censo ejecutado), **#85** (guard de paridad lee `GENERATOR_INCLUDE_CONTEXT` con
distinta semántica que su consumidor). Y un guard que se apagaba en silencio en la suite
(`test_s321_reachability_delivery_proof`) — arreglado junto con la fuga de entorno de `s156` que
lo destapaba. Dúo: 4 rondas Sol (v1→v4) + Fable emparejado, **0 falsos positivos**; lo que el dúo
no cazó lo cazó Alberto dos veces (2222 como suppl; A5.4 es un EJEMPLO).

**Tarde autónoma (16-ago, Alberto fuera; DEC-226)** — hecho: smoke (#271) y **FULL** (#273) de
factlevel sobre el ruler nuevo: 116/135 OK, paridad con s291, los 6 golds de la sentada por hecho =
exactamente lo pretendido, 0 regresiones; `hp013#1` bajó a retrieval-miss (raw=0). **#84 «medido» en
serving (⚠️ s324d: NO-DATO — el flag no existe en Railway)**: 12,7% de chunks primary fuera del alineado, concentrado en 8/23 golds (hp006 48% · hp021 62% ·
cat008 100%; S141 no rescata ninguno). Dos cosas se llevaron **a propósito sin cablear/escribir**
tras dúo: la conducta (a) del `mismatch` (2 rondas Sol: 4 subsistemas + decisión de producto
multi-modelo — `s321_mismatch_conducta_a_propuesta_v3.md`) y DEC-186b (2 rondas Sol NO SÓLIDO:
reconciliación de 4 docs + prereg — `s321_dec186b_propuesta_v3.md`). 0 falsos positivos en 6 rondas.

**Qué sigue**: (1) **decisión de producto** multi-modelo en `mismatch` (DEC-226 recomienda «fuera de
alcance en v1») → sesión dedicada de cableado con dúo; (2) DEC-186b como reconciliación de
DEC/PLAN×2/LEVER_DIGEST/#75 con vocabulario único + pregunta cero (¿medir el eje modelo?); (3) #84:
proponer fix con dúo (el daño ya está medido) — el `doc_map` como fuente de aplicabilidad; (4)
`hp013#1`: el carrier ya no entra al pool — ver sonda `serve`; (5) podar el PLAN (154 KB).

**Qué sigue**: (antes de la tarde: (1) cablear la conducta (a);
(2) reescribir DEC-186 con su número real (dúo propio) y la raíz de #75; (3) #84 medir el daño
en serving antes de tocar `_product_aligned_chunks`; (4) sonda `hp013#1` para afinar la población
de lever B; (5) re-medir factlevel (los golds cambiaron: 4 cores nuevos, 1 demote, 1 entra al
denominador) — smoke antes del full.

## Estado anterior (s323 — 15 ago 2026)

> **ACOTADO en s325 (18 ago 2026, addendum DEC-220)**: el alcance ADOPTADO es
> **Cloud + Dispatch**; Remote Control queda documentado pero **NO activado**. No deja
> hueco: Dispatch abre sus sesiones EN EL PC, así que cubre igual lo que necesita
> OneDrive. Y la DB no exige tocar nada en Supabase (`service_role` por REST para datos;
> para DDL, `DATABASE_URL` por el pooler IPv4 o el conector MCP).


**s323 — «dónde corre Claude» montado (DEC-220)**: las TRES superficies quedan
cubiertas — **Cloud** (VM de Anthropic, sigue con el PC apagado), **Remote Control**
(la sesión corre en el PC y se dirige desde el móvil) y **Dispatch**. El hallazgo de
rumbo: **Remote Control cierra el gap que `ENTORNO_CLOUD.md §3` daba por perpetuo**
(OneDrive) — la ingesta ya es gobernable desde el móvil, ejecutándose en local.
Alberto adjudicó **un environment con todas las keys y red Full**, con el riesgo
declarado (no hay secret store). Nacen `scripts/cloud_smoke.py` + tests (verificador
con recibo, contrato de no-fuga de secretos), el hook de arranque pasa a ser
**idempotente**, y `ENTORNO_CLOUD.md` se reescribe contra la doc vigente. Dúo Fable:
NO SÓLIDO → 3 hallazgos aplicados (el mejor: el centinela del hook no sondeaba
`cryptography`, justo el módulo que motivó el hook en s315). **Queda pendiente el
smoke de recepción EN cloud** — sin ese recibo esto es aparato preparado, no entorno
verificado. Deuda nueva #79 (el revisor adversarial es ciego a `.claude/`).

## Estados anteriores a s323 — ARCHIVADOS en HISTORY (s324d, 17 ago 2026)

Los bloques «Estado anterior» de **s322b, s314, s293, s292, s291, s290, s289, s288c, s286, s285, S277
(con el cierre operativo de la P1 fresca y su contexto histórico), S205, s129, s104, s103b, s103, s102,
s101, s100** y el «Qué sigue (s77)» con sus **Antecedentes s69–s83** viven ahora en
[`docs/HISTORY.md`](HISTORY.md) → sección **«Archivo del PLAN — estados anteriores s100→s322b (movidos en
s324d)»**, con su texto íntegro y sus anclas (`estado-anterior-s205--18-jul-2026`). Motivo: el PLAN se relee
en cada arranque y había vuelto a superar los 160 KB (DEC-036/s56: el PLAN se mantiene COMPACTO; el estado
vigente son los 4 últimos bloques + «Qué sigue»). Nada se ha reescrito: es un movimiento, no una edición.

**Roadmap macro (vigente desde s77; rationale en HISTORY):** F1 calidad (levers de retrieval = rendimiento
decreciente; el ±2 del ruler es el techo) → **F2 escala (identidad de producto en ingesta = EL siguiente
bloque; el elefante DEC-074 se completó en s320-s321 y hoy se gobierna por catálogo + packets)** → F3
routing/tool-use + multi-dominio del scope M&A → F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).
