# s284 — Packet de adjudicación GOLD-REVIEW **ronda 2** · los 20 PARCIAL del baseline v2

> **Cómo usarlo (~25-30 min):** una ficha por qid con (1) qué pide el gold, (2) qué dio el bot,
> (3) qué criticó el juez, (4) mi análisis con evidencia verificable, (5) la decisión concreta que
> se te pide. Marca por fila: `[ ] ✅ acepto · [ ] ✏️ editar (anota el matiz) · [ ] ❌ rechazo`.
> **NADA se edita sin tu marca** (DEC-025: el gold es tuyo). Las ediciones aceptadas se aplican
> vía `gold_store` (la puerta valida).
>
> **Fuentes:** `evals/bot_vs_gold_39_baseline_c1v4_parity_s283.yaml` (baseline v2 OFICIAL,
> 16 PASS / 20 PARCIAL / 3 FALLO, DEC-157b) · `evals/gold_answers_v1.yaml` ·
> verificaciones DB (SELECT, `chunks_v2`) citadas por fila. **Coste LLM de este packet: $0**
> (análisis por lectura, no juez pagado). Sin commits, sin escrituras en DB.

---

## 1 · RESUMEN EJECUTIVO

### 1.1 Distribución de los 20 PARCIAL

| clase | qué significa | n | qids |
|---|---|---|---|
| **A** | gap real del bot (incompletitud/error genuino y servible) | **10** | cat009, cat010, hp002, hp004, hp005, hp006, hp009, hp010, hp014, hp017 |
| **B** | artefacto de scope/vara del gold (todos los cores presentes; el PARCIAL lo produce contenido `supplementary` o que solo vive en la prosa del gold) | **4** | cat008, hp003, hp008, hp020 |
| **C** | artefacto de juez (la crítica NO se sostiene al leer la respuesta — patrón DEC-092b) | **4** | cat001, cat011, cat017, cat019 |
| **D** | techo ya declarado (DEC-158/159), solo referencia | **2** | cat022, hp012 |
| **E** | conducta-por-diseño castigada | **0 como clase primaria** (aparece como componente secundario en cat011) |  |

**Golds con propuesta de ajuste: 5** (hp017, hp020, hp003, hp008, cat011) + **2 decisiones
transversales** (§1.2 y §1.3) que no editan ningún gold pero sí la vara con la que se mide.

**Lectura honesta del número:** 10 de 20 son fallos reales del bot. No he inflado B/C — el sesgo
documentado del autor (`feedback_my_bias`) es sobre-atribuir fuera del bot, así que cada B/C de
este packet lleva evidencia mecánica (offset de carácter, consulta DB o cita del propio gold), no
opinión. Y cada A lleva el mecanismo, no solo la etiqueta.

### 1.2 HALLAZGO TRANSVERSAL 1 (instrumento) — **el juez solo ve los primeros 3000 caracteres de la respuesta**

`scripts/test_bot_vs_gold.py:163`:

```python
gold=(gold or "")[:3000], bot=(bot or "")[:3000])},
```

La línea entró con `de45a9b` (28-may-2026) y **ha estado activa en toda la serie bvg**, incluido el
baseline v2. Consecuencia medida sobre el propio artefacto:

- **12 de los 20 PARCIAL** tienen respuesta > 3000 chars → el juez vio una respuesta truncada
  (cat001, cat008, cat010, cat017, cat019, hp002, hp005, hp006, hp012, hp014, hp017, hp020).
- Los 4 casos de clase **C** son truncación pura y **está probado por offset de carácter**:

| qid | len | % visto | lo que el juez declaró "falta" | offset real en la respuesta |
|---|---|---|---|---|
| cat001 | 6664 | 45 % | "no incluye la edición individual —zona, tipo de equipo, niveles de alarma/prealarma— y la respuesta **aparece truncada**" | §4 «Edición individual» @3552 · «Tipo de equipo» @3769 · «255 zonas locales» @3928 · «nivel de alarma» @4220 · «nivel de prealarma» @4286 |
| cat017 | 7286 | 41 % | "falta la parte clave de alta/configuración: autoconfiguración, CLSS, POL-200-TS" | «POL-200-TS» @3327 · PARTE 5 CLSS @~5000 · «Auto Configuración» @4994 |
| cat019 | 6358 | 47 % | "queda **truncada** y no explica la asignación de salidas/acciones" | PASO 4 «Añadir Salidas» @3170 · «ACCIÓN» @3301 · «RETRASO» @3354 · «Sirenas:» @4353 |
| hp005 | 4378 | 69 % | "el procedimiento PK-ID3000 **queda truncado**" | el corte cae literalmente en el paso 4 del bloque PK-ID3000 |

El juez no se equivocó: **describió con precisión el texto que recibió**. El defecto es del harness.

**No afirmo que arreglarlo suba el PASS.** El truncado afecta también a **6 de los 16 PASS**
(cat012, cat016, cat018, cat023, hp007, hp013) y a **2 de los 3 FALLO** (cat007, hp011): un PASS
concedido sobre 3000 chars puede caerse cuando el juez vea el resto (más superficie = más agarre
para el completista). El signo del delta es **desconocido hasta re-medir**. Lo que sí es seguro es
que hoy la vara **no es la que creemos que es**.

> **Nota colateral (fuera del alcance de esta lane):** el mismo `[:3000]` está en
> `scripts/test_multiturn_vs_gold.py:611` → el e2e multi-turn de s281b (18 PASS/2 PARCIAL/1
> residual) comparte el defecto de contrato. No medido aquí si muerde (depende de la longitud de
> las respuestas multi-turn).

> **Relectura de DEC-092b:** el patrón "el juez penaliza al bot por servir MÁS info correcta" sigue
> siendo real (cat011/hp008 de este packet lo reproducen), pero **el mecanismo dominante en
> respuestas largas es otro**: al servir más, el contenido que el gold exige **se desplaza más allá
> del carácter 3000 y desaparece de la vista del juez**. Con top-10 + `LLM_MAX_TOKENS=3500` las
> respuestas crecieron; el efecto "regresión aparente" tiene aquí una explicación mecánica que la
> lectura manual de s99 no podía ver. El veredicto de DEC-092b (ship de top-10) NO cambia; su
> explicación causal se completa.

### 1.3 HALLAZGO TRANSVERSAL 2 (contrato de la vara) — **el juez no ve `tipo: core / supplementary`**

`test_bot_vs_gold.py:244` pasa al juez **solo `gold_answer`** (la prosa). Los `atomic_facts` con su
`tipo` — el trabajo de adjudicación que tú hiciste en s88/s89 y s269 — **no llegan al juez**. En la
práctica: **todo lo que esté escrito en la prosa del gold es exigible para el PASS**, incluidos los
hechos que tú mismo clasificaste como `supplementary`, e incluso contenido que está en la prosa
pero **no** en los `atomic_facts` (caso hp003: las capacidades 18Ah/24Ah).

Los 4 casos de clase **B** son exactamente esto: **cores 4/4 presentes** y PARCIAL por
supplementary. Es una decisión tuya, no un bug:

- **(a) statu quo** — la prosa del gold ES el contrato; `supplementary` solo sirve para el
  instrumento fact-level. Coste: el PASS holístico es sistemáticamente más duro que la vara que
  creíamos aplicar; 4 PARCIAL de 20 son de esta clase.
- **(b) pasar los `atomic_facts` con su `tipo` al juez** y pedirle que pondere core > supplementary.
  Coste: cambia el juez → toca el freeze DEC-021/023 y obliga a re-baseline; riesgo de que el juez
  se vuelva laxo con omisiones que sí importan en campo.
- **(c) reescribir la prosa del gold** de los 4 afectados separando «núcleo exigible» de
  «complementario». Coste: 4 ediciones de gold; no toca el juez; el efecto es real pero por-gold.

Mi recomendación: **(a) para esta ronda + (c) selectivo** solo donde el `supplementary` sea de
seguridad o donde la pregunta sea de enumeración (hp003, hp008 — ver fichas). (b) no ahora: cambiar
el juez con el truncado sin arreglar mezcla dos variables.

### 1.4 Lo que este packet NO zanja

- No re-juzga nada: no hay llamadas a modelo. Los veredictos siguen siendo los del baseline v2.
- No promete movimiento de PASS por ninguna vía (§1.2). DEC-075/DEC-095: plateau noise-limited,
  single-pass K=1 → ±1-2 de swing por réplica es esperable.
- Los dos **D** (cat022, hp012) NO se re-litigan: están declarados techo en DEC-158/159 y siguen
  esperando decisiones de datos que ya están en tu lote (H0 lineage, semántica `~~`).

---

## 2 · LAS 20 FICHAS

---

### cat001 — «Notifier PEARL: equipos por lazo SLC, límites de aisladores, y alta/edición de equipos» ‖ **C** (artefacto de juez)

**1 · Qué pide el gold.** 6 cores: 159+159 / 99+99 por lazo · 0,75 A · 40 CLIP en lazo mixto ·
aisladores 32/25/20 + base B501 AP · alta por AUTOCONFIGURACIÓN · **edición individual (zona
255/8192, tipo de equipo, niveles alarma/prealarma)**. 3 supplementary: 1-o-2 lazos · 512 de
sistema · «4: Inicializar equipo prot.OPAL».

**2 · Qué dio el bot** (6664 chars). Los 6 cores. Su §4 «Edición individual de equipos» lista
literalmente «Tipo de equipo», «Número de zonas (hasta **255 zonas locales** o **8192 zonas de
red**)», «Ajuste del nivel de alarma», «Ajuste del nivel de prealarma». Cierre completo (fuentes +
follow-ups + bloques de evidencia).

**3 · Qué criticó el juez.** «Queda incompleta porque no incluye la edición individual desde la
central —zona, tipo de equipo, niveles de alarma/prealarma e inicialización OPAL— y la respuesta
aparece truncada.»

**4 · Análisis.** 4 de las 5 cosas que el juez dice ausentes están presentes, en offsets
**3552 / 3769 / 3928 / 4220 / 4286** — es decir, **después del corte de 3000 chars** del harness
(§1.2). «La respuesta aparece truncada» es literalmente cierto **del input del juez**, no de la
respuesta. Único miss real: `4: Inicializar equipo prot.OPAL` (**supplementary**). La respuesta no
está truncada: termina con fuentes, follow-ups y bloques de evidencia.

**5 · Recomendación [ADJUDICAR-ALBERTO].** **No tocar el gold.** Registrar cat001 como instancia
mecánicamente probada del defecto §1.2 (6ª de la serie DEC-092b, pero esta con causa raíz
identificada). Decisión que se te pide: **¿autorizas quitar el `[:3000]` y re-medir el baseline
(~$3)?** — sabiendo que el delta puede ser negativo.

---

### cat008 — «M710 / MI-DMMI: cableado en lazo y resistencias (RFL y modo 3 estados)» ‖ **B** (scope del gold) + componente A menor

**1 · Gold.** 4 cores: 2-estados vs 3-estados · RFL 47 kΩ · 18 kΩ en serie (M200E-EOL-R18) ·
terminales 1/2/3/4 del lazo + entrada A en 6-7. 3 supplementary: terminales 4 y 5 para anular el
aislador · part `M200E-EOL-R` · **`M200E-EOL-RD` polarizada para VdS 2489**.

**2 · Bot** (3454 chars; el corte solo se come los bloques de evidencia anexos). Los **4 cores
completos**. Añade el terminal 5, el NAS-2 (no hace falta la 47 kΩ si va a J14) y los terminales
8-9 del MI-DMM2I.

**3 · Juez.** «Impreciso/confuso con el uso del terminal 5 para anular el aislador interno y omite
la opción de fin de línea polarizada M200E-EOL-RD para VdS 2489.»

**4 · Análisis.** La segunda crítica es un **supplementary** (fact 7). La primera **sí tiene base**:
el bot escribe «El terminal 5 está conectado internamente con el **terminal 4**» mientras el propio
fragmento que anexa dice «El terminal 5 está conectado internamente con el **terminal 2**» — se
contradice con su propia fuente servida en la misma respuesta. (Nota: el fragmento fuente es de
calidad pobre — traducción con frase duplicada y «En no se necesita…» — pero la regla es fidelidad a
lo servido.) Impacto práctico: bajo (el bot sí da el "positivos in/out a 4 y 5" del gold), pero es
un error de fidelidad real, no de scope.

**5 · Recomendación [ADJUDICAR-ALBERTO].** **Mantener la barra** (no editar el gold). Anotar el
desliz terminal-5 como fidelity-slip menor sin lever propio (fuente corrupta ≈ clase P2/`~~` de tu
lote). Decisión: **¿confirmas que `M200E-EOL-RD`/VdS 2489 NO es exigible para un PASS de esta
pregunta?** (si dices que sí lo es, cat008 pasa a A y hay que tirar de retrieval).

---

### cat009 — «Resistencia EOL en las líneas de zona de la NFS Supra» ‖ **A** (raíz = datos de linaje)

**1 · Gold.** Core: **6K8 Ω** (o el condensador 47 µF suministrado por defecto) — valor de la
edición vigente v.05. Notas del gold: CONFLICTO-REVISIÓN **latest-wins** (v.04 = 4K7 → v.05 = 6K8);
«NO es answer-con-conflicto (eso es para variantes de mercado ES-vs-US)».

**2 · Bot** (2377 chars, **sin truncar**). Da 47 µF por defecto y 6K8 en modo resistivo, la regla de
todas las zonas y hasta el procedimiento de cambio capacitivo↔resistivo. Pero: «El Fragmento 3
(versión v.04 del manual en inglés) menciona **4K7 Ω**… **Verifica qué versión de firmware/hardware
tienes instalada y usa el valor correspondiente**.»

**3 · Juez.** «Trata el valor 4K7 de la versión antigua como una posible opción según
firmware/hardware, cuando la referencia correcta exige usar la revisión vigente con 6K8.»

**4 · Análisis. La crítica se sostiene y es la conducta la que falla**, no el gold (que ya fue
editado y adjudicado por ti en s88/s89 A1). Dos capas:
- **Generación:** la regla del proyecto es *latest-wins*; el bot delega en el técnico un criterio
  («mira tu firmware») que **no existe**: 4K7 vs 6K8 es una revisión de manual, no una variante de
  hardware. En campo esto es instalable-mal.
- **Raíz de datos (verificada en DB, SELECT):** `HLSI-MN-025-I_NFS Supra Series` (v.04) tiene **5
  chunks con 4K7 y 0 con 6K8**; `…v05` tiene 5 con 6K8 (+1 con 4K7 = la inconsistencia interna
  §4.4.2 que el propio gold documenta). **Las dos ediciones conviven en el corpus sin marca de
  supersedes** → el generador no tiene forma de saber cuál manda. Esto es exactamente la campaña
  **H0 lineage/supersedes** que ya está en tu lote (T1/T2/T3).

**5 · Recomendación [ADJUDICAR-ALBERTO].** **Mantener la barra; no editar el gold.** Registrar
cat009 como **caso-testigo servible del valor de H0**: es el ejemplo concreto de "sin linaje, el bot
hedgea entre una revisión viva y una muerta en un dato instalable". Decisión: **¿lo añades como
criterio de aceptación de la campaña H0** (cuando T2/T3 estén aplicados, cat009 debería resolver a
6K8 sin hedge)?

---

### cat010 — «IS-mA1 (ATEX): cómo se alimenta y parámetros de seguridad intrínseca de entrada» ‖ **A** — *el gap más servible de los 20*

**1 · Gold.** Core 1: **se alimenta a 24 V dc** en zona peligrosa a través de barrera Zener /
aislador galvánico 28V/93mA (y en zona segura sin barrera, **no operar en continuo por encima de
16 V** por el límite de corriente interno). Core 2: Ui=28V, Ii=93mA, Pi=660mW, Ci=0, Li=0.
Supplementary: marcado II 1G Ex ia IIC T4 Ga, −40…+60 °C.

**2 · Bot** (4615 chars). Core 2 completo y muy bien; marcado ATEX completo; barreras Zener,
aisladores galvánicos, S2/S3, capacitancia máxima 83 nF. **La pregunta literal — «¿cómo se
alimenta?» — no tiene respuesta numérica**: `24 V`, `24V`, `16V`, `16 V` = **0 ocurrencias en toda
la respuesta**.

**3 · Juez.** «No indica claramente la alimentación nominal a 24V dc ni la advertencia del uso en
zona segura sin barrera y el límite interno por encima de 16V.» — **correcto**.

**4 · Análisis + mecanismo (verificado en DB).** El párrafo que falta es literal y está en
`chunks_v2`, **`IS5001-F_IS-mA1_EN` página 1, `chunk_index = 0`**: «*…designed to operate in a
hazardous area from a 24V dc supply via 28V 93mA resistive… at supply voltages above 16V the
internal current limit will function…*». **Y ese mismo chunk contiene el marcado ATEX y los números
de certificado que el bot SÍ cita como [F1]** (SIRA 05ATEX2084X / IECEx SIR 06.0045X / T4 Ga están
justo debajo, en el mismo chunk). ⇒ **el chunk fue servido y el generador saltó el párrafo que
responde la pregunta**. No es corpus-gap (`feedback_corpus_gap`), no es retrieval: es **omisión de
síntesis** sobre contenido servido, en el eje exacto de la pregunta.

**5 · Recomendación [ADJUDICAR-ALBERTO].** **Mantener la barra.** Es el caso más limpio de la
cola de síntesis (DEC-075/094) con ancla fichero:chunk. Decisión: **¿lo adoptamos como caso-testigo
del próximo lever de generación** (el patrón "responder el marco y saltarse el valor pedido")?

---

### cat011 — «Necesito un detector "751" para Notifier; ¿cuál es el correcto?» ‖ **C** (+ componente E y B)

**1 · Gold.** Conducta **clarify**. Cores: «751» es ambiguo → pedir aclaración con candidatos
**acotados del catálogo gobernado**: CPX-751E (iónico), IDX-751 (óptico **seguridad intrínseca**,
ATEX). Supplementary: FSL-751E (aspiración/láser). Nota del gold: «candidatos restringidos a los que
SÍ están en el catálogo; SDX-751/SDX-751EM excluidos porque NO están en el catálogo».

**2 · Bot** (1421 chars, sin truncar). **Clarify correcto**: dice que 751 no identifica un único
modelo, lista 8 variantes con cita, y pregunta central / principio de detección / **«¿es una zona
con atmósfera potencialmente explosiva?»** (la distinción safety-critical del gold, cubierta).

**3 · Juez.** «Omite el FSL-751E indicado en la referencia y **añade múltiples variantes no
presentes en el gold/corpus**, lo que puede confundir o **alucinar el catálogo** relevante.»

**4 · Análisis. La acusación de alucinación es FALSA — verificado en DB** (`chunks_v2`, conteo de
chunks/documentos distintos):

| modelo | chunks | docs |  | modelo | chunks | docs |
|---|---|---|---|---|---|---|
| SDX-751 | 52 | 26 | | IPX-751 | 29 | 16 |
| CPX-751 | 35 | 20 | | LPX-751 | 22 | 15 |
| SDX-751TEM | 19 | 9 | | IRX-751CTEM | 12 | 10 |
| IDX-751 | 12 | 7 | | IRX-751TEM | 3 | 3 |

Las 8 variantes que el bot lista **existen en el corpus con cita**. Lo que el gold exige es otra
cosa: que la lista salga **del catálogo gobernado**, no de los chunks — y ese catálogo se sabe
incompleto (DEC-093: 630 candidatos sin confirmar). Miss real: **FSL-751E**, que es
**supplementary** (y el bot sí ofrece su hermano VIEW/láser `LPX-751`).

**5 · Recomendación [ADJUDICAR-ALBERTO] — decisión de diseño, no de gold.** Para un técnico que
pregunta «¿cuál es el 751 correcto?», ¿el clarify debe:
- **(a)** listar solo el catálogo gobernado (statu quo del gold: 3 candidatos), o
- **(b)** listar las variantes documentadas en corpus con cita (lo que hace el bot: 8, todas reales)?
Si eliges **(b)**, propongo editar el gold: *«…ofreciendo los candidatos documentados en el corpus
con cita (al menos CPX-751E iónico, IDX-751 seguridad intrínseca/ATEX, FSL-751E y LPX-751
aspiración/láser); el requisito irrenunciable es distinguir estándar vs seguridad intrínseca antes
de elegir»*. Si eliges **(a)**, cat011 se queda PARCIAL y el lever es el catálogo (workstream
DEC-074), no el bot.

---

### cat017 — «INSPIRE E10/E15: cómo se cablea y se da de alta un lazo» ‖ **C** (artefacto de juez)

**1 · Gold.** 5 cores: pinout del módulo OPAL HOP-433-100 (1/2, 4/5, 6/7, 9/10; 3 y 8 no se usan;
apantallado a tierra en central) · capacidad 159+159 / 99+99, no mezclar, 750 mA, 3,5 km ·
**licencia CLIP una por cada circuito de lazo** · alta por **AUTO CONFIGURACIÓN** · configuración
por **Programa CLSS** (+ `.bin` de licencia). Supplementary: **POL-200-TS**.

**2 · Bot** (7286 chars). Pinout completo, capacidades, no-mezclar, 750 mA, 3,5 km, comprobaciones
con multímetro, primer encendido, **PARTE 5 «CONFIGURACIÓN DEL LAZO EN CLSS»**, **PARTE 6 «AUTO
CONFIGURACIÓN»** paso a paso, y **POL-200-TS**.

**3 · Juez.** «Falta la parte clave de alta/configuración del lazo: autoconfiguración, uso del
Programa de Configuración CLSS, generación/carga de licencia .bin y mención de POL-200-TS.»

**4 · Análisis.** Offsets: `POL-200-TS` @**3327**, `Auto Configuración` @**4994**, la PARTE 5 de
CLSS @~**5000** → **los tres están detrás del corte de 3000** (§1.2; el juez solo vio el 41 % de la
respuesta). Genuinamente ausentes: **el `.bin` de licencia** y el **cuantificador «una licencia por
cada circuito de lazo CLIP»** (el bot dice «requiere licencia» sin el por-lazo). Y este segundo es
justo el residual `cat017#2` del Apéndice de s269 — **retrieval-miss documentado** (chunk
`5bb83899`, HOP-138-9ES p5, `pool_position=null`, nunca entra al pool).

**5 · Recomendación [ADJUDICAR-ALBERTO].** **No tocar el gold.** cat017 = artefacto de truncado con
un residual real ya catalogado. Decisión: ninguna nueva — solo confirmar que el residual
`licencia-por-lazo` sigue en la cola de retrieval (s269 Apéndice) y no se re-litiga aquí.

---

### cat019 — «CAD-250: cómo se configura una maniobra causa-efecto completa» ‖ **C** (artefacto de juez)

**1 · Gold.** 4 cores: crear maniobra (menú Maniobras → AÑADIR) + campo **COINCIDENCIAS** ·
componentes **EVENTO / ACCIÓN** (máx 100.000) · el EVENTO se define sobre **ENTIDAD** o **CONDICIÓN
TEMPORAL** · **las ACCIONES/salidas actúan sobre sirenas o módulos de control**. Supplementary:
sectorización previa (§7).

**2 · Bot** (6358 chars). Los 4 cores. **PASO 4 «Añadir Salidas (Acciones)»** con RETRASO 0-600 s,
entidad destino, y el desglose Activar/Desactivar/Habilitar/Deshabilitar/Test/Reiniciar/Pulso +
tipos Todos/Sirenas/Relés/Sirena discontinua/PCB1/PCB2. Cierre completo con fuentes y follow-ups.

**3 · Juez.** «La respuesta **queda truncada** y **no explica la asignación de salidas/acciones**,
que es parte esencial… además introduce detalles no contrastados frente al gold y una formulación
confusa de la lógica N de M.»

**4 · Análisis.** «Añadir Salidas» @**3170**, «ACCIÓN» @3301, «RETRASO» @3354, «Sirenas:» @4353 →
**todo el PASO 4 está detrás del corte** (§1.2, el juez vio el 47 %). La crítica central es un
artefacto puro. «Detalles no contrastados» = información extra correcta con cita (patrón DEC-092b).
**Sí es real** el desliz de la lógica: el bot escribe *«Coincidencias = N de M → Se deben cumplir N
eventos de los M configurados (lógica "N de N")»* — el paréntesis final es erróneo/confuso (micro-A,
una línea).

**5 · Recomendación [ADJUDICAR-ALBERTO].** **No tocar el gold.** Registrar como artefacto §1.2.
Decisión: ninguna específica (va con la decisión transversal del truncado).

---

### cat022 — «SharpEye 40/40: diferencia 40/40L vs 40/40L4 y sufijo B» ‖ **D** (techo declarado, DEC-158)

**1 · Gold.** 3 cores: banda IR **2,5-3,0 µm** (L/LB) · **4,5 µm** (L4/L4B, hidrocarburos) · sufijo
**B = BIT**.

**2 · Bot** (2233 chars, sin truncar). Sustituye la diferencia de banda por una de **sensibilidad**
(15 m vs 28 m leídos de las Tablas 6 y 7) y declara explícitamente: «Los fragmentos no describen
otras diferencias técnicas entre el L y el L4 (óptica, espectro, tecnología de sensor)… consulta el
Apéndice A». Deriva el sufijo B correctamente desde el manual hermano del 40/40U, marcando que es
inferencia.

**3 · Juez.** «Falló en la diferencia principal…: no menciona la banda 2,5-3,0 µm vs 4,5 µm, y la
sustituye por una diferencia de sensibilidad/rango, dejando la respuesta incompleta y
potencialmente engañosa.»

**4 · Análisis.** El veredicto es justo y **ya está adjudicado**: DEC-158 declaró cat022
**techo-bloqueado** (el padre que porta la banda muere en `_diversify_by_source_file`; el fichero
diana está saturado; medido con el flip-check de $0,15). Dos matices honestos: (i) la conducta de
declarar límites y no inventar es **buena** (componente E), pero la respuesta sigue sin contestar la
pregunta → PARCIAL correcto; (ii) el paso *«Es decir, el 40/40L4 tiene un rango de detección
mayor»* **sí es una inferencia del bot** comparando dos tablas de ajustes distintos — el juez la
llama «potencialmente engañosa» con razón.

**5 · Recomendación [ADJUDICAR-ALBERTO].** **No-action / aceptar como techo** (DEC-158). Único
apunte: si algún día se toca el prompt, la comparación cruzada de tablas sin base explícita es el
tipo de inferencia que conviene marcar como tal.

---

### hp002 — «ASD535: alarma intermitente de flujo bajo, causa y diagnóstico» ‖ **A**

**1 · Gold.** 4 cores: no es "alarma de flujo bajo" sino **fallo de flujo de aire** respecto al
**nominal registrado en el reset inicial (=100 %)** · causa probable <80 % = obstrucción (>120 % =
rotura) · retardo **300 s** · lectura del valor en **posición V (cap. 7.6.1)**, V01/V02.
Supplementary: reset inicial posterior con sus condiciones · **turbulencias** como causa de
intermitencia.

**2 · Bot** (6743 chars). Causa (obstrucción, código 001), ±20 %/80 %, 300 s, posición V, tensión
en bornes, códigos 001/002/004/008, limpieza, y **el gate de seguridad de aislar controles/alertas
antes de intervenir** (el que tú marcaste ✅ CORE en s269).

**3 · Juez.** «No explica bien que es un fallo de flujo respecto al reset inicial, omite
turbulencias/fluctuaciones como causa probable de intermitencia y el reset inicial posterior con sus
condiciones, y añade pasos/códigos no suficientemente centrados.»

**4 · Análisis.** Verificado: `turbulencia` = **0 ocurrencias**; `reset inicial` solo aparece
@2979, en la línea de follow-ups («también puedo ayudarte con…»), no en el cuerpo; el marco
«100 % = valores nominales del reset inicial» no está (los «nominal» de la respuesta son de
**tensión**). Ese marco es precisamente la obligación `obl_a5d9fa1f` que **tú marcaste ✅
CORE-REQUIRED en s269**. Y la pregunta dice **intermitente** → las turbulencias son la causa
diferencial de la intermitencia. ⇒ crítica válida, clase A. Componente C declarado: «añade
códigos no centrados» penaliza información correcta con cita (DEC-092b). Nota de instrumento: hp002
es el único gold cuyo **texto de referencia también se truncó** (3270 → 3000 chars: el juez perdió
la ADVERTENCIA Detnov/Securiton del final).

**5 · Recomendación [ADJUDICAR-ALBERTO].** **Mantener la barra.** hp002 es coherente con tu
adjudicación s269 (el 100 %-nominal es core). Decisión: ninguna edición; hp002 se queda como caso de
la cola de síntesis con obligación ya adjudicada.

---

### hp003 — «Detnov CAD-150: cómo se conectan las baterías de 24V» ‖ **B** (scope) + componente A de seguridad

**1 · Gold.** 4 cores: dos baterías de **12 V en serie** · **cable puente** (+ de una al − de la
otra) · cables **rojo/negro** del circuito · **orden: primero red 230VAC, después baterías**.
3 supplementary: comprobar **>24 V con voltímetro** · ubicación en la parte inferior en vertical ·
**desconectar el magnetotérmico bipolar** antes de manipular. En la **prosa** (no en los
`atomic_facts`): «también existen modelos con capacidad para 18A/h o 24A/h».

**2 · Bot** (2209 chars, sin truncar). Los **4 cores completos** + ubicación + fusible + pulsador
BAT. Escopa la respuesta a **CAD-150-8** y a baterías 7 Ah.

**3 · Juez.** «Limita la respuesta a CAD-150-8 y a baterías 7Ah, omitiendo variantes de capacidad…,
además de no mencionar la comprobación de tensión >24V ni la desconexión del magnetotérmico antes de
manipular.»

**4 · Análisis.** Las tres críticas son: (i) contenido que vive **solo en la prosa del gold**, no en
los facts (18/24 Ah); (ii) y (iii) dos **supplementary**. Los 4 cores están. El escopado a
CAD-150-8 es defendible: los dos manuales servidos SON los de la CAD-150-8 (y tu ground-truth de
`reference_detnov_cad150` dice que todo el corpus está tagueado `CAD-150-8`) → el bot es fiel a lo
que tiene. **PERO** hay un matiz que no quiero suavizar: *«desconectar el magnetotérmico bipolar
antes de manipular»* es un **paso de seguridad previo**, y en s269 tú marcaste ✅ CORE-REQUIRED
exactamente esa clase (hp002, `obl_b6f6211b`: aislar antes de intervenir). Hay una **inconsistencia
de criterio entre golds**: aquí está como supplementary.

**5 · Recomendación [ADJUDICAR-ALBERTO] — 2 marcas.**
- **(a) Propuesta de edición del gold:** promover el magnetotérmico a **core** (consistencia con tu
  criterio s269 de gates de seguridad). Texto propuesto para el fact: *«Antes de manipular la
  central, desconectar el magnetotérmico bipolar exterior (gate de seguridad previo al conexionado)
  — tipo: core»*. Si aceptas, hp003 pasa de B a **A** y el PARCIAL queda plenamente justificado.
- **(b)** ¿Las capacidades 18/24 Ah deben ser exigibles? Si sí → añadirlas como fact supplementary
  o core (hoy no son fact ninguno, solo prosa); si no → **quitarlas de la prosa del gold** para que
  la vara y el contrato coincidan.

---

### hp004 — «DGD-600: tensión de funcionamiento y consumo en reposo» ‖ **A** (conducta)

**1 · Gold.** Conducta **clarify**. Cores: existen dos versiones (24V y 220V) → **ofrecer ambas y
pedir aclaración**; 22-38 V / 45 mA; 180-240 V / 70 mA. Nota del gold (**tu adjudicación s89, A4a**):
«también se considera CORRECTA una respuesta que dé ambas versiones claramente separadas **e indique
la necesidad de confirmar la versión instalada**».

**2 · Bot** (625 chars, sin truncar). Las dos versiones perfectamente separadas y con cita. **No hay
ninguna frase de confirmación** ni pregunta al técnico.

**3 · Juez.** «No pide ni indica explícitamente que debe confirmarse qué versión está instalada, que
era la conducta esperada ante variantes distintas.»

**4 · Análisis. La crítica es exacta contra tu propia adjudicación**: la rama alternativa que tú
aceptaste en s89 exige **ambas ramas + confirmación**; el bot cumple la primera mitad y no la
segunda. Contexto relevante: en s89, con ese mismo gold, hp004 flipeó a **PASS 5/5 unánime** — la
respuesta de entonces sí llevaba la línea de confirmación. Hoy la respuesta es más corta y la
perdió. ⇒ gap de conducta real y muy barato de arreglar (una frase), y `conducta_bot` registrada =
`answer-con-conflicto` ≠ `clarify` esperada.

**5 · Recomendación [ADJUDICAR-ALBERTO].** **Mantener la barra.** hp004 es el mejor
caso-testigo de la conducta `clarify` en el eje single-turn (y enlaza con el residual `mt11b`
gold-vs-diseño que espera dogfooding). Decisión: ¿lo marcas como criterio de aceptación del bloque
de conducta (respuesta multi-rama **debe** cerrar con la petición de confirmación)?

---

### hp005 — «ID3000: zona que active sirena solo con coincidencia de dos detectores» ‖ **A** (mixto declarado: A + C + B)

**1 · Gold.** 4 cores: instrucción en la **Matriz de Control** con entrada ALARMA · **COINCIDENCIA
2 EQUIPOS** · misma zona o subzona · **salida = «CIRCUITO SIRENA/RELÉ»** (o TODAS SALIDAS limitando
a módulos de sirena). 3 supplementary: EN54-2 7.1.4 (no pulsadores) · niveles 1 y 2 fijos ·
PK-ID3000.

**2 · Bot** (4378 chars). Matriz de Control, entrada ALARMA, tipo ANALÓGICO, **COINCIDENCIA 2
EQUIPOS**, misma zona/subzona, la advertencia EN54-2 7.1.4 con las dos instrucciones separadas, y el
procedimiento PK-ID3000. **La salida se despacha en una línea**: «define la salida como el circuito
de sirena correspondiente [F12]».

**3 · Juez.** «Queda incompleta/imprecisa en la programación de la salida de sirena, omite pasos del
flujo oficial como 'UNA ÚNICA zona', selección SMART 'Normal (Combinada) Alarma', confirmación y
detalles de niveles de coincidencia, y **el procedimiento PK-ID3000 queda truncado**.»

**4 · Análisis — las tres partes tienen distinto veredicto:**
- **A (real):** la salida (core 4) se sirve a una línea sin «CIRCUITO SIRENA/RELÉ» ni la alternativa
  TODAS SALIDAS ni el modo FIJO/PULSANTE. Coincide con un residual **ya documentado**: DEC-092/s102
  listaron *«hp005·CIRCUITO SIRENA… enterrado >rank-15 = document-side (hypothetical-questions), no
  rerank»*. ⇒ retrieval-miss conocido, no gold.
- **C (artefacto):** «PK-ID3000 queda truncado» — el corte de 3000 chars cae **literalmente** en el
  paso 4 de ese bloque (§1.2).
- **B (scope):** «UNA ÚNICA zona» y «Normal (Combinada) Alarma» son **pasos que solo existen en la
  prosa del gold**, no en los `atomic_facts` (0 ocurrencias verificadas en la respuesta).

**5 · Recomendación [ADJUDICAR-ALBERTO].** **Mantener la barra** (el core 4 falta de verdad).
Decisión: ¿confirmas que los pasos prosa-only («UNA ÚNICA zona», SMART combinada) **no** son
exigibles para el PASS? Si lo son, hay que subirlos a `atomic_facts`; si no, conviene aligerarlos de
la prosa (§1.3c).

---

### hp006 — «AFP-400: aviso 'Tierra' (Earth Fault), qué significa y cómo se localiza» ‖ **A**

**1 · Gold.** 3 cores presentes: LED «Fallo de Tierra» de la MPS-400 + JP2 · «Tierra» como avería
reconocida en el SLC (Estilos 4/6/7) · **módulos aisladores ISO-X para acotar el fallo en el lazo**.
1 core **ausente-probado**: los manuales **NO** incluyen procedimiento paso a paso de localización.
Supplementary: TB1-3 a tierra sólida · SW2/SW3 del NAM-232W.

**2 · Bot** (3253 chars; el corte solo alcanza el bloque anexo de descripción de imagen). Significado
correcto, LED MPS-400, JP2, SLC Estilos 4/6/7, y dice explícitamente «Los fragmentos disponibles no
describen un procedimiento paso a paso de localización» (@887, **visible al juez**). Redirige al
manual 50253.

**3 · Juez.** «Añade pasos no documentados o poco fiables para localizar por LCD/estado y para
atribuir origen a la fuente, omite TB1-3, NAM-232W e **ISO-X**, y no deja tan claro que no existe
procedimiento paso a paso.»

**4 · Análisis.** Verificado: `ISO-X` = **0 ocurrencias** → **falta un core**, y es el único
mecanismo real de acotación del fallo en el lazo (lo que el técnico necesita para *localizar*).
TB1-3 y NAM-232W son supplementary. La última crítica es **injusta**: el bot sí lo declara, y
temprano. Pero la primera **sí muerde**: tras declarar que no hay procedimiento, el bot **construye
uno** (menú Leer Estados, «confirma si el fallo está en el circuito de alimentación») que el gold
marca explícitamente como no documentado → es la clase de inferencia que el core `ausente-probado`
pretende impedir.

**5 · Recomendación [ADJUDICAR-ALBERTO].** **Mantener la barra.** Decisión: ninguna edición.
Apunte de conducta: cuando un gold tiene un core `ausente-probado`, la conducta correcta es
declarar la ausencia **y no rellenarla** con un procedimiento ensamblado; hoy el bot hace ambas
cosas a la vez.

---

### hp008 — «¿Qué detectores de humo analógicos son compatibles con la ID3000?» ‖ **B** (scope) + componente C

**1 · Gold.** 4 cores (iónicos CPX-551E/CPX-751E · ópticos SDX551E/SDX-751/SDX-751EM ·
multicriterio IRX-751CTEM/IRX-751TEM · SDX-751-TEM OptiPlex). 6 supplementary: HPX-751E · IDX-751 ·
LPX-751/FSL-751E · **LPB500 (máx 4/lazo) y LPB-700/-700T** · protocolo **CLIP** · 99+99 por lazo.

**2 · Bot** (1932 chars, sin truncar). **Los 4 cores completos** + HPX/IDX/LPX/FSL (4 de 6
supplementary) + notas de programación (tipos MULTI/VIEW/SMT4, niveles de sensibilidad).

**3 · Juez.** «Omite los detectores por rayo LPB500 y LPB-700/LPB-700T… Además introduce una nota
sobre **IPX-751** que no aparece en el listado GOLD y puede confundir.»

**4 · Análisis.** (i) La segunda crítica **no se sostiene**: `IPX-751` está en el corpus con **29
chunks en 16 documentos** (SELECT verificado) y el bot lo cita como tipo MULTI con fuente → penalizar
información correcta con cita = DEC-092b. (ii) La primera **es un miss real** pero de facts
**supplementary** (LPB500/LPB-700, CLIP, 99+99). **Contra-argumento que declaro de entrada**: esta es
una pregunta de **ENUMERACIÓN**, donde la completitud *es* el payload — omitir 3 modelos de una lista
de ~15 es una incompletitud sustantiva aunque el gold los etiquete supplementary. Es decir: la
etiqueta `supplementary` puede estar mal **para este tipo de pregunta**.

**5 · Recomendación [ADJUDICAR-ALBERTO] — propuesta de edición.** Promover a **core** los detectores
por rayo (**LPB500, LPB-700/-700T**) en hp008, porque en preguntas de enumeración la lista completa
es el hecho. Texto propuesto: *«Detectores de humo por rayo/haz proyectado compatibles: LPB500 (máx.
4 por lazo) y LPB-700/LPB-700T — tipo: core»*. Si aceptas, hp008 pasa de B a **A** con PARCIAL
justificado; si rechazas, hp008 debería ser PASS bajo una vara cores-only (§1.3).

---

### hp009 — «¿Resistencia de fin de línea recomendada para los lazos de la Morley ZXe?» ‖ **A**

**1 · Gold.** Core: el lazo direccionable de la ZXe **NO lleva RFL** — se cablea como **bucle
cerrado** con retorno al panel; la RFL es concepto de circuitos convencionales (las sirenas usan
6K8). Core `ausente-probado`: ningún manual ZXe da RFL para el lazo. Supplementary: aisladores
internos, máx 32 entre aisladores.

**2 · Bot** (1554 chars, sin truncar). Titula **«Resistencia de Fin de Línea (RFL) — Circuitos de
Sirenas ZX2e/ZX5e»**, abre con **6,8 KΩ (sirenas)**, sigue con **150 Ω (RS-485)** y deja la
respuesta real —«los lazos analógicos no utilizan resistencia de fin de línea»— en una **«Nota
importante» al final**. Nunca menciona el bucle cerrado con retorno al panel.

**3 · Juez.** «Acertó al indicar que los lazos direccionables no usan RFL, **pero lo dejó como nota
secundaria** y mezcló valores de sirenas y RS-485 que no responden a la pregunta y pueden confundir.
Falta explicar que el lazo se cablea como bucle cerrado con retorno al panel, sin RFL.»

**4 · Análisis. La crítica es correcta y el riesgo es de campo**: un técnico que pregunta por la RFL
del lazo y lee un titular «RFL — 6,8 KΩ» tiene todas las papeletas de colocar una 6K8 donde no va.
Además falta el **mecanismo** (core 1: bucle cerrado + aisladores) que es lo que hace la respuesta
accionable. El contenido servido es correcto; el **orden y el encuadre** son el fallo (clase
framing/lede-burial, distinta de omisión).

**5 · Recomendación [ADJUDICAR-ALBERTO].** **Mantener la barra.** Es el caso-testigo más claro de
**lede-burial** del set (responder primero lo que no se preguntó). Decisión: ¿lo adoptas como
criterio explícito de conducta («la respuesta directa a la pregunta va primero; las variantes
adyacentes después»)?

---

### hp010 — «Morley DXc: cómo se añade un nuevo detector al lazo tras la puesta en marcha» ‖ **A** (raíz = retrieval documentado)

**1 · Gold.** 3 cores: **AUTOBÚSQUEDA** · **acceder a Nivel 3 (clave) y desbloquear la memoria**,
tecla '2' en el menú de Lazos, elegir lazo, confirmar · resumen final con nuevos/eliminados/
modificados. Supplementary: esperar 2 min tras cambio de protocolo · evento «EQUIPO NUEVO» ·
«Editar Equipos».

**2 · Bot** (2799 chars, sin truncar). Autobúsqueda impecable con las pantallas literales del panel,
resumen, 2 minutos, y notas DXc1/DXc2/DXc4. El paso 2 dice: *«Accede al menú de Lazos **desde el
nivel de programación correspondiente**»*.

**3 · Juez.** «No detalla el acceso a Nivel 3 ni el desbloqueo de memoria, no menciona que la
autobúsqueda acepta el evento 'EQUIPO NUEVO' y apenas cubre la edición posterior de propiedades.»

**4 · Análisis.** Verificado: `Nivel 3`, `memoria`, `EQUIPO NUEVO`, `Editar` = **0 ocurrencias**. El
prerequisito de acceso es **core** y su ausencia es de campo pura: el técnico llega a la central y no
puede entrar. **Raíz ya diagnosticada** (s269, Apéndice, `hp010#1`): el span de la autobúsqueda se
sirve (p48) pero el prerequisito de acceso vive en el chunk `155a90fe` (p37) con
`pool_position=null` → **retrieval-miss multi-span dentro del mismo manual**, con camino propuesto
(re-scope por facet del gate s174, facet `access_prerequisite` que pasó sus umbrales: 8 TPs / 7
fabricantes). Mejora respecto a s269: la respuesta congelada de entonces decía «Nivel 2, clave
1234» (incorrecto); hoy es vaga en vez de errónea.

**5 · Recomendación [ADJUDICAR-ALBERTO].** **Mantener la barra.** Decisión: ¿autorizas el
re-scope por facet del gate s174 (riesgo declarado: gate-shopping) para atacar
`access_prerequisite`? Es el residual «más convertible» según s269 y hp010 es su caso-testigo.

---

### hp012 — «AM2020/AFP1010: lazos direccionables y dispositivos por lazo» ‖ **D** (techo declarado, DEC-158 + DEC-159)

**1 · Gold.** Conducta **answer-con-conflicto**. Cores: AM2020 = 10 lazos · 99+99 por lazo ·
AFP1010 **España** = 2 LIB-200 / 396 dispositivos · AFP1010 **US** = 4 lazos / 792 → **en
conflicto**, con la discrepancia **declarada como tal**.

**2 · Bot** (3193 chars, 94 % visible). AM2020 10 lazos ✔, 99+99 ✔. Para el AFP1010 pone «máximo de
lazos: **4** (gabinete CAB-A3 con LIB-400 exclusivamente)» y «límite total: máximo 2 tarjetas
LIB-200, 396 dispositivos» — los dos números, **sin etiquetarlos ES vs US y sin declarar el
conflicto**. Falta el 792.

**3 · Juez.** «No explica claramente la discrepancia España vs US ni presenta bien las dos variantes
completas… además afirma el máximo de 4 lazos como si fuera general y lo restringe a LIB-400.»

**4 · Análisis.** Crítica correcta y **ya adjudicada**: DEC-158 declara hp012-retrieval
**techo-bloqueado** (el padre muere en `_diversify_by_source_file`) y DEC-159 deja
**hp012-framing** aparcado-en-datos: la EC `attribution_conflict` fue **rechazada pre-build por el
dúo** porque la raíz real es poblar **lineage/supersedes** (= campaña H0 T1/T2 de tu lote), no más
ingeniería. Nada nuevo que decidir aquí.

**5 · Recomendación [ADJUDICAR-ALBERTO].** **No-action / referencia.** hp012 se resuelve (o no)
cuando H0 aporte la atribución de mercado. Sirve como segundo caso-testigo de H0 junto a cat009.

---

### hp014 — «ID2000: cómo se conecta un módulo de aislamiento de línea en el lazo» ‖ **A**

**1 · Gold.** 4 cores: máx 32 (EN54-2) / 25 en ID2000 / 20 con FET · continuidad **antes** de
conectar los aisladores · **puentear terminales 2 y 4** para las pruebas y **retirar** el puente ·
pantalla a tierra solo en el panel + resistencia máxima **35 Ω**. Supplementary: unidades de inicio
(25/20 SU) · resistencia añadida por aislador (0,29 / 0,1 Ω). Y un core notable:
**el manual NO incluye el esquema terminal-a-terminal del aislador; remite a las instrucciones del
propio equipo**.

**2 · Bot** (4029 chars, 74 % visible; el corte se lleva solo el bloque final de cortocircuito y las
fuentes). Los 4 cores. Pero: lista **14,5 / 28,5 / 18,5 / 35,5 Ω** (@1287) como límites de
resistencia de línea y luego **35 Ω** (@2740) como máximo del lazo — **ambos visibles al juez**; y
dibuja un esquema «Aislador (terminales **1 2 3 4**)» presentándolo como el conexionado del módulo.

**3 · Juez.** «Mezcla valores de resistencia potencialmente contradictorios con el límite de 35 Ω,
no incluye las unidades de inicio ni el cálculo de resistencia añadida por tipo de aislador, y **el
detalle terminal-a-terminal queda más afirmado que documentado**.»

**4 · Análisis. Las tres críticas se sostienen**, y la tercera es la importante: el gold tiene un
fact cuyo contenido es *«el manual NO da el terminal-a-terminal»*, y el bot **afirma un
terminal-a-terminal** sin el caveat → el técnico puede creer que tiene el conexionado del aislador
cuando no lo tiene. La mezcla 35,5 vs 35 Ω es incoherencia real de la propia respuesta (no del
gold). Las unidades de inicio y las resistencias por aislador son supplementary (componente B).

**5 · Recomendación [ADJUDICAR-ALBERTO].** **Mantener la barra.** Decisión: ninguna edición de
gold. hp014 refuerza (con hp006) el patrón «el bot rellena lo que el gold marca como
ausente-probado» → es un candidato de lever de conducta, no de retrieval.

---

### hp017 — «Notifier PEARL: cómo se programa el retardo de salida de alarma principal» ‖ **A** + **propuesta de edición de gold ya adjudicada por ti**

**1 · Gold.** 4 cores: el retardo se programa por **causa-efecto** (Apéndice 5), no con un parámetro
suelto · una regla consta de **instrucción de entrada + instrucción de salida** · entrar por «Editar
Configuración» y **borrar la Regla 1** por defecto · asignar uno de los **SEIS tipos de retardo**
(A5.3). Supplementary: retardo de alarma por equipo/zona (240 s) · máx **512 reglas**, «0» = TODOS.

**2 · Bot** (4312 chars, 70 % visible). Acierta el marco (no hay parámetro único; va por
causa-efecto) y clava la **matriz de comportamiento de los tipos de retardo** + la gestión operativa
(anular/habilitar, AMPLIAR RETARDO, FIN RETARDO). Verificado ausente: `Regla 1` = 0 · `512` = 0 ·
`entrada`/anatomía de la regla = 0 · «probar» solo aparece @3644 dentro del bloque anexo de
citas, no en el cuerpo. Y escribe «los **seis** tipos… son:» seguido de **siete** bullets.

**3 · Juez.** «Omite pasos críticos: borrar la Regla 1, crear la regla entrada/salida,
máximo/reglas/lazo 0, pruebas, advertencias EN54 y retardos por equipo/zona; además presenta
inconsistencia al decir seis tipos y listar siete.»

**4 · Análisis.** Todo verificado y **coherente con tu adjudicación s269**: allí marcaste ✅
CORE-REQUIRED las obligaciones de **instrucción de entrada** (`obl_b2043cd4`), **instrucción de
salida** (`obl_7aa72371`), **«evite lógicas contradictorias»** (`obl_16637b93`, con tu ✏️ de merge) y
**«probar rigurosamente todas las reglas»** (`obl_0d6a3094`) — las cuatro **siguen ausentes**. ⇒ A
limpia. **Y el "seis vs siete" es el conflicto de fuente que tú ya adjudicaste** ✅ en s269
(`obl_872c35fb`, SOURCE-CONFLICT → re-spec a **DISCLOSURE**: la prosa de la p44 dice «uno de seis
tipos» y la tabla de la MISMA página tiene **siete** columnas, verificadas al píxel). El bot
reproduce ambos lados **sin declarar** la discrepancia = exactamente la conducta que la re-spec
quiere corregir.

**5 · Recomendación [ADJUDICAR-ALBERTO] — propuesta de edición.** El gold `hp017` **todavía ancla
«SEIS tipos de retardo» como core**, es decir, ancla el lado de un conflicto que tú ya resolviste a
*disclosure*. Propongo editar el fact 4 y el paso 4 de la prosa:

> *«Asignar a la regla un tipo de retardo de salida (sección A5.3 "Tipos de retardo"). **Aviso de
> fuente: la prosa de A5.3 dice "uno de seis tipos" mientras la tabla de la misma página recoge
> SIETE** (Fijo · Estándar · No Silenc. · Est. Ext. · RetExtStd · No Sil. Ext · SinRetExt); la
> conducta correcta es **declarar la discrepancia**, no resolverla en un número. — tipo: core»*

Con esa edición, "listar siete tras decir seis" deja de ser demérito y pasa a serlo **no declararlo**.
(Es la aplicación al `gold_answers_v1` de una marca ✅ tuya que hasta ahora solo vivía en la capa de
obligaciones de s269.)

---

### hp020 — «Notifier INSPIRE: cómo se configuran las contraseñas de nivel 2 y nivel 3» ‖ **B** (scope) + **error del gold verificado en DB**

**1 · Gold.** 4 cores: regla por nivel (en NA2 solo se cambia NA2; en NA3, NA2 o NA3) · ruta
menú → Ajustes → «Cambio del código de acceso» · **4 a 8 dígitos** · re-introducir y mensaje
«Cambio de código de acceso satisfactorio». Supplementary: sincronizar CLSS + copia en la nube ·
**el portal/app/programa CLSS comparten usuario y contraseña**. **Nota del gold:** *«No se
especifican los códigos por defecto de fábrica en los documentos.»*

**2 · Bot** (3473 chars, 86 % visible). Los 4 cores, los dos flujos (desde NA2 y desde NA3), la
sincronización y la copia en la nube, el auto-logout a los 5 min. Y abre con **«Códigos de fábrica —
Nivel 2: `22222222` · Nivel 3: `33333333`» [F3]**.

**3 · Juez.** «Omite la nota de que el portal CLSS, la app y el configurador comparten
usuario/código/contraseña, y el flujo desde Nivel 2 no incluye explícitamente el mensaje de
éxito/aceptación ni la sincronización final.»

**4 · Análisis. Dos cosas, y una es un error del gold.**
- La primera crítica es un **supplementary** (fact 6) → clase B. La segunda es pedante: el bot
  **partió** el procedimiento en dos flujos (más preciso que el gold, que tiene uno solo) y el
  mensaje de éxito + sincronización están en el flujo NA3 (@1908 y @2686, visibles).
- **La nota del gold es FALSA y lo he verificado en DB (SELECT):** los códigos de fábrica **sí están
  documentados**, literalmente, en `HOP-338-9ES issue 4_01-2026_Op` — p48: *«Utilice el código de
  acceso configurado de fábrica "22222222", "33333333" o un código exclusivo si se ha cambiado»* y
  p14 (mismo literal para NA2). El gold se autoró sobre `HOP-138-8/9` (instalación/puesta en marcha)
  y **no miró el manual de operación**, que sí está en el corpus. ⇒ **el bot no inventó nada: aportó
  un dato correcto, citado y operativamente crítico que al gold le falta.**

**5 · Recomendación [ADJUDICAR-ALBERTO] — propuesta de edición (2 marcas).**
- **(a)** **Corregir la nota del gold**: sustituir *«No se especifican los códigos por defecto de
  fábrica en los documentos»* por *«Los códigos de acceso de fábrica SÍ están documentados: NA2 =
  22222222 y NA3 = 33333333 (HOP-338-9ES issue 4, p14 y p48); el manual recomienda cambiarlos por
  uno exclusivo de 4-8 dígitos»*, y añadirlos como fact (propongo **supplementary**: no son el
  procedimiento pedido, pero son la primera cosa que necesita el técnico en campo).
- **(b)** ¿El supplementary «CLSS comparte credenciales» debe ser exigible para el PASS? (si no,
  hp020 debería ser PASS bajo vara cores-only, §1.3).

---

## 3 · TABLA DE DECISIONES PARA LA SENTADA

### 3.1 Transversales (2) — no editan ningún gold, cambian la vara

| # | decisión | evidencia | recomendación | marca |
|---|---|---|---|---|
| T1 | **Quitar el `[:3000]` del juez** (`test_bot_vs_gold.py:163`) y **re-medir el baseline (~$3)**, aceptando que el delta puede ser negativo | 12/20 PARCIAL truncados; 4 PARCIAL con la crítica probada por offset; 6/16 PASS y 2/3 FALLO también truncados | **Sí, arreglar y re-medir**: hoy el contrato del baseline no es el que creemos. Sin promesa de signo | [ ]✅ [ ]✏️ [ ]❌ |
| T2 | **¿El juez debe ver `core` vs `supplementary`?** (a) statu quo · (b) pasar `atomic_facts`+`tipo` al juez · (c) reescribir la prosa de los golds afectados | 4/20 PARCIAL son cores-4/4 con PARCIAL por supplementary; el juez solo recibe `gold_answer` | **(a) + (c) selectivo** (hp003, hp008). (b) NO ahora: cambiar el juez con T1 sin resolver mezcla variables y toca el freeze DEC-021/023 | [ ]✅ [ ]✏️ [ ]❌ |

### 3.2 Ediciones de gold propuestas (5)

| # | qid | edición propuesta | efecto en la clase | marca |
|---|---|---|---|---|
| G1 | **hp017** | fact 4: «SEIS tipos» → **disclosure del conflicto seis-vs-siete** (aplica tu ✅ de s269 `obl_872c35fb` al `gold_answers_v1`) | A se mantiene; cambia QUÉ se exige | [ ]✅ [ ]✏️ [ ]❌ |
| G2 | **hp020** | corregir la nota falsa + añadir los códigos de fábrica **22222222 / 33333333** (DB-verificados, HOP-338-9ES p14/p48) | corrige un error del gold | [ ]✅ [ ]✏️ [ ]❌ |
| G3 | **hp003** | promover **«desconectar el magnetotérmico bipolar antes de manipular»** a `core` (consistencia con tu criterio de gates de seguridad, s269 hp002) | B → **A** | [ ]✅ [ ]✏️ [ ]❌ |
| G4 | **hp008** | promover **LPB500 / LPB-700-700T** a `core` (pregunta de enumeración: la lista completa ES el hecho) | B → **A** | [ ]✅ [ ]✏️ [ ]❌ |
| G5 | **cat011** | (a) mantener candidatos = catálogo gobernado, o (b) permitir candidatos documentados-en-corpus con cita (las 8 variantes del bot están DB-verificadas) | (b) convierte la crítica en no-defecto | [ ]✅(a) [ ]✅(b) [ ]✏️ |

### 3.3 Decisiones de rumbo derivadas (4)

| # | decisión | caso-testigo | marca |
|---|---|---|---|
| R1 | **cat009 + hp012 como criterio de aceptación de la campaña H0** (lineage/supersedes): con T2/T3 aplicados, cat009 debe resolver a 6K8 sin hedge y hp012 debe atribuir ES vs US | cat009 (DB: v.04 con 5×4K7 y v.05 con 5×6K8 conviviendo sin marca), hp012 | [ ]✅ [ ]✏️ [ ]❌ |
| R2 | **Conducta: la respuesta directa va primero** (anti lede-burial) y **multi-rama cierra pidiendo confirmación** | hp009 (titula con la RFL de sirenas), hp004 (da ambas versiones sin pedir confirmación) | [ ]✅ [ ]✏️ [ ]❌ |
| R3 | **Conducta: si el gold declara un core `ausente-probado`, no rellenarlo** con un procedimiento ensamblado | hp006 (construye localización tras declarar que no existe), hp014 (afirma terminal-a-terminal que el manual no da) | [ ]✅ [ ]✏️ [ ]❌ |
| R4 | **¿Re-scope por facet del gate s174** (`access_prerequisite`) para atacar el prerequisito de acceso? Riesgo declarado: gate-shopping | hp010 (Nivel 3 + desbloqueo de memoria, chunk `155a90fe` con `pool_position=null`) | [ ]✅ [ ]✏️ [ ]❌ |

### 3.4 Sin acción (5)

cat001 · cat017 · cat019 (artefactos de truncado, se resuelven con **T1**) · cat022 · hp012
(techos DEC-158/159, esperan datos ya en tu lote).

---

## 4 · QUÉ PASA TRAS TU ADJUDICACIÓN

1. Las ✅/✏️ de §3.2 se aplican **vía `gold_store`** (la puerta valida `metodo`+`verificado_por`;
   provenance = adjudicación s284). **Nada se edita sin tu marca.**
2. Si **T1** sale ✅: quitar el `[:3000]` (y decidir qué hacer con el gemelo de
   `test_multiturn_vs_gold.py:611`), re-correr el baseline (~$3) y **estampar el delta honesto** en
   `docs/FACTLEVEL_ASSESSMENT.md` + `DECISIONS`/`LEVER_DIGEST`, sea cual sea el signo. El baseline v2
   (16/20/3) quedaría como **medido-con-truncado** en la traza, no borrado.
3. Los 10 casos **A** no necesitan nada tuyo para seguir siendo válidos: son la cola de calidad real
   y quedan repartidos entre síntesis (cat010, hp002, hp009, hp017), conducta (hp004, hp006, hp014),
   retrieval documentado (hp005, hp010) y datos/linaje (cat009).
