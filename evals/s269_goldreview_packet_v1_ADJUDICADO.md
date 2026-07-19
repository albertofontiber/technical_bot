# s269 — Packet de adjudicación GOLD-REVIEW al píxel · 12 synthesis-miss · para tus marcas en lote

> **Cómo usarlo (~20-25 min):** cada sección trae la pregunta, lo que la respuesta congelada SÍ dice,
> la **cita literal de la fuente** (verificada al píxel sobre el render adjunto) y el **veredicto
> propuesto** del triage s269 (verificado adversarialmente 12/12). Marca por fila:
> `[ ] ✅ acepto · [ ] ✏️ editar (anota el matiz) · [ ] ❌ rechazo`.
> YO aplico después las ✅/✏️ vía `gold_store` (la puerta valida; DEC-025: el gold es tuyo).
> **NADA se edita sin tu marca.**

**Qué se adjudica y por qué.** Los 12 residuales de síntesis del funnel vigente (143 OK / 12 synth /
2 retrieval = 157) fueron triados en s269 (`evals/s269_triage_12misses_v1.yaml`: 4 analistas
independientes + audit del instrumento 0 INSTRUMENT-FN + verificador adversarial, acuerdo 12/12). El
resultado propuesto: **3 demotes a SUPPLEMENTARY + 1 re-spec a disclosure (conflicto documental) +
confirmación de 8 CORE-REQUIRED**. Esos veredictos eran PROPUESTA de sesión, no gold-review canónico:
este packet es el paso al píxel (RULER_DESIGN §2, pasos 2-4: render de página + vecinas + cita
literal) previo a tocar ningún gold. **Proyección si aceptas:** denominador 157 → **154**; objetivo
98% = **151/154** (= +8 conversiones sobre los 8 CORE restantes). Los 2 retrieval-miss van en el
Apéndice (informativo, sin adjudicación ahora).

## Verificación de renders (provenance + hallazgos)

Los renders JPEG canónicos de Supabase Storage (bridge `s269_visual_assets_bridge_dump_v1.jsonl`)
solo cubrían 2 de las 8 páginas fuente únicas (AM-8200 p21; 997-671 p42 — este existía en Storage
aunque no está en el bridge). Las 6 restantes (ASD535 p28/p121, HLSI-MN-103 p56/p63, 997-671 p44,
AM-8200 p70) y la vecina AM-8200 p69 **NO existen en Storage** (probadas las URLs exactas: 400) → se
renderizaron **en local
desde los PDF fuente del proyecto** (patrón canónico `scripts/render_pdf_page.py` / PyMuPDF 170 dpi;
rutas en la tabla). TODAS las páginas de este packet fueron **leídas y verificadas**: cada cita
literal es visible en su render. Mapeo página-chunk ↔ página-PDF declarado por fila (hay 2
off-by-one: 997-671 F12 chunk-p41 → PDF p42; AM-8200 F8 chunk-p69 → PDF p70).

**Hallazgos del píxel que la cadena texto-solo (s113/s163/s235/triage) NO vio:**
1. **`t.Fi` no existe** (hp011, obl_2f5d): en la fila `r.i` del render p63, los DOS iconos 7-seg del
   paréntesis leen **`t.A`** (zoom 500 dpi adjunto; mismo glifo que el `t.A` "Duración de la descarga"
   de §5.3.1 p56). El "parámetro t.Fi (t.A → 0 seg.)" de los artefactos es transliteración errónea de
   extracción (clase 7-seg, `feedback_7segment_reading`). Si se edita el gold: anclar **t.A**.
2. Menor (hp002, obl_a5d9): el chunk marca "~~y con el conducto de aspiración intacto~~" como
   tachado; al píxel está **subrayado** (énfasis, no supresión). No cambia el veredicto; confirma la
   regla D4 (render > texto extraído).

## Tabla-resumen

| # | obligación | qid | hecho perdido (corto) | veredicto propuesto | conf | fuente (píxel) | render | marca |
|---|---|---|---|---|---|---|---|---|
| 1 | obl_7bba8d03d496 | cat018 | sub-paso "Pestaña Programa" (campos Zona/CBE) | **CORE-REQUIRED** | media | AM-8200-manu-prog-spa PDF p21 | `..._7bba8d03_p21.jpg` | [ ]✅ [ ]✏️ [ ]❌ |
| 2 | obl_015f9b9aaa3a | cat018 | relación TONOS (tono+volumen→sirenas SND por zonas) | **SUPPLEMENTARY** (demote) | media | íd. PDF p70 (chunk p69) | `..._015f9b9a_p70.jpg` | [ ]✅ [ ]✏️ [ ]❌ |
| 3 | obl_b6f6211be439 | hp002 | aislar controles/alertas/extinción ANTES de mantenimiento | **CORE-REQUIRED** | alta | ASD535_TD PDF p121 | `..._b6f6211b_p121.jpg` | [ ]✅ [ ]✏️ [ ]❌ |
| 4 | obl_a5d9fa1f9253 | hp002 | 100% = valores nominales registrados en reset inicial | **CORE-REQUIRED** (borde) | media | íd. PDF p28 | `..._a5d9fa1f_p28.jpg` | [ ]✅ [ ]✏️ [ ]❌ |
| 5 | obl_07eee3300535 | hp002 | literales "120 %" y "A11 a C32" | **SUPPLEMENTARY** (demote parcial) | media | íd. PDF p28 | `..._07eee330_p28.jpg` | [ ]✅ [ ]✏️ [ ]❌ |
| 6 | obl_161564ff41bf | hp011 | granularidad "intervalos de 5 seg" (t.A) | **SUPPLEMENTARY** (demote) | alta | HLSI-MN-103 PDF p56 | `..._161564ff_p56.jpg` | [ ]✅ [ ]✏️ [ ]❌ |
| 7 | obl_2f5d79e354b9 | hp011 | r.i = "- -": rearme inhibido hasta fin extinción/t.A | **CORE-REQUIRED** | alta | íd. PDF p63 (+zoom) | `..._2f5d79e3_p63.jpg` | [ ]✅ [ ]✏️ [ ]❌ |
| 8 | obl_872c35fb41d7 | hp017 | prosa "seis" vs tabla con 7 tipos de retardo | **SOURCE-CONFLICT → re-spec disclosure** | alta | 997-671-005-3 PDF p44 (ambos en la misma página) | `..._872c35fb_p44.jpg` | [ ]✅ [ ]✏️ [ ]❌ |
| 9 | obl_b2043cd4379b | hp017 | instrucción de ENTRADA (anatomía de la regla) | **CORE-REQUIRED** | media | íd. PDF p42 (chunk p41) | `..._b2043cd4_p42.jpg` | [ ]✅ [ ]✏️ [ ]❌ |
| 10 | obl_7aa723717412 | hp017 | instrucción de SALIDA (equipos asignados: sirenas/relés) | **CORE-REQUIRED** | media | íd. PDF p42 | `..._7aa72371_p42.jpg` | [ ]✅ [ ]✏️ [ ]❌ |
| 11 | obl_16637b935bd4 | hp017 | warning "evite las lógicas contradictorias" | **CORE-REQUIRED** | media | íd. PDF p42 | `..._16637b93_p42.jpg` | [ ]✅ [ ]✏️ [ ]❌ |
| 12 | obl_0d6a30948dfd | hp017 | "probar rigurosamente todas las reglas en puesta en marcha" | **CORE-REQUIRED** | alta | íd. PDF p42 | `..._0d6a3094_p42.jpg` | [ ]✅ [ ]✏️ [ ]❌ |

Renders en `s269_goldreview_renders/` (rutas relativas a `evals/`). Respuestas congeladas y
obligaciones: `evals/s235_direct_clause_bound_score_packet_v1.json`; fragmentos fuente:
`evals/s113_full_contexts_freeze_v1.json`.

---

## cat018 — «¿Cómo se programa una ecuación causa-efecto (CBE) en la Notifier AM-8200 para que un evento active una salida?»

### 1 · obl_7bba8d03d496 — el sub-paso de PESTAÑA (dónde viven Zona/CBE) ‖ CORE-REQUIRED · conf media

**Lo que la respuesta SÍ dice:** paso 1 «Navega en el menú a la programación del módulo de salida:
`MENU PROGRAMMAZIONE \ Punti \ Sensori` [F3]» + paso 2 «Usa las teclas ▲▼ para seleccionar el
parámetro CBE… longitud máxima 64 caracteres» + paso 4 «Pulsa Enter». Cero menciones de «pestaña»
(probe normalizado = 0); el campo Zona del punto tampoco aparece.

**Cita literal de la fuente** (AM-8200-manu-prog-spa, PDF p21 = PÁGINA-18, chunk 8514e83a):
> «**Pestaña Programa** (Programación ecuaciones CBE, asociación zona)» — mock de pantalla:
> `MENU PROGRAMMAZIONE\Punti\Sensori` → fila de pestañas `Principale | Programmazione | Opzioni |
> Edit` → campos `Zona 2` / `CBE (G1)` — «**Zona** - número de zona asignada» · «**CBE** - ecuación
> CBE del punto» · «Para modificar el campo «CBE» **en esta pestaña** se debe seleccionar el
> parámetro con las teclas flecha ▲▼, y después pulsar la tecla de confirmación ☑».

**Render:** `s269_goldreview_renders/cat018_obl_7bba8d03_p21.jpg` (fuente, Storage bridge; chunk p21
= PDF p21, verificado) · vecina +1 `cat018_obl_7bba8d03_p22_vecina.jpg` (PÁGINA-19: teclado CBE de
64 caracteres con Enter — continuación de la misma pantalla).

**Veredicto propuesto: CORE-REQUIRED (conf media).** La cabecera de menú que la respuesta sí da y la
pestaña que omite salen del MISMO mock: no hay ruta alternativa. La pregunta es procedimental y la
localización del campo ES el payload: sin el sub-paso de pestaña, el paso 2 no es ejecutable tal
cual si el panel abre el punto en `Principale`. Agravante: el paso 1 etiqueta `Punti\Sensori` como
programación del módulo de salida. Caveat anti-CORE declarado: severidad práctica moderada (4
pestañas visibles; sin componente de seguridad).

**TU MARCA: [ ] ✅ [X] ✏️ [ ] ❌** — notas: Lo que no entiendo es por qué estamos utilizando texto en italiano, cuando creía que solo utilizábamos texto en inglés y español. no se si esto ha sido un cambio de GPT 5.6 Sol o que, pero me gustaría entenderlo. Si está en italiano, seguro que está en español también. estoy de acuerdo con el veredicto que propones.
**Nota de riesgo:** en el mock la pestaña se llama `Programmazione` (UI en italiano); la sección la
llama «Pestaña Programa». Si se edita el gold, reflejar ambas denominaciones para no fallar contra
el panel real.

---

### 2 · obl_015f9b9aaa3a — la relación TONOS (tono+volumen → sirenas SND) ‖ SUPPLEMENTARY (demote) · conf media — el demote MÁS DÉBIL

**Lo que la respuesta SÍ dice:** el mecanismo completo con el ejemplo canónico del MISMO p70 — «El
manual describe **tres opciones equivalentes** para activar el módulo de salida C1L1M1 desde el
detector C1L1S1 [F8]: Opción A/B/C» — + 6 familias de operadores con ejemplos + «afecta a todos los
módulos de salida programados con tipo-SW **SND** [F11]» (la relación SND viaja vía la obligación
cubierta obl_5784). NO contiene «TONE», «tono», «volumen» ni «sirenas» (probes = 0; miss real).

**Cita literal de la fuente** (AM-8200-manu-prog-spa, PDF p70 = PÁGINA-67; chunk 0c6cc5e0 declara
p69 → off-by-one declarado, la parte TONOS está al píxel en p70):
> «Programando las siguientes CBE: **TONOS (10 2 Z2:Z4 (Z10 G20))** — En la activación de la Zona 10
> o del Grupo 20 se configura el tono 10 y el volumen 2 para las sirenas (con tipo software SND) de
> las zonas Z2, Z3 y Z4.»
Y en la MISMA página, el ejemplo que la respuesta sí usó: «OPCIONES — El ejemplo siguiente ilustra
tres modos de realización de una programación simple, es decir, **la activación del módulo de salida
en respuesta a una alarma en un detector**» (= la pregunta literal).

**Render:** `s269_goldreview_renders/cat018_obl_015f9b9a_p70.jpg` (fuente) · vecina −1
`cat018_obl_015f9b9a_p69_vecina.jpg` (PDF p69 = PÁGINA-66: definición del operador — «Es el operador
el que permite introducir tono y volumen para grupos de zonas a través de la CBE», sintaxis
`TONO (Tono Volumen Rangos_de_Zonas (Condición))`, rangos 1÷33 / 1÷4). En p22 (render de la fila 1)
se ve la tecla TONE en el teclado CBE.

**Veredicto propuesto: SUPPLEMENTARY (conf media).** La pregunta pide el mecanismo genérico
evento→salida y la respuesta sirve el ejemplo canónico A/B/C del propio manual + operadores; TONE es
un operador más de la misma clase que DEL/SDEL/TIM (también omitidos y ofrecidos como follow-up), y
el qualifier SND ya viaja vía [F11]. **Declarado honesto:** es el demote más débil de los tres — el
rationale del analista solo demuestra que el miss es real; el argumento del demote lo aportó el
verificador. Contra-argumento en dirección CORE: es el ÚNICO átomo servido que liga
activación-de-zona/grupo + tono/volumen + sirenas-SND + rango-de-zonas (la salida PCI arquetípica).

**TU MARCA: [ ] ✅ [ ] ✏️ [X] ❌** — notas: Tiendo a ser más coservador, por lo que creo que sí lo incluiría.
**Nota de riesgo:** si tu vara de dominio es que «activar una salida» en PCI incluye canónicamente
sirenas con patrón (tono/volumen), este demote sería discutible — es tu llamada, no la nuestra.

---

## hp002 — «El detector ASD535 de Detnov está dando una alarma intermitente de flujo bajo. ¿Cuál es la causa más probable y cómo se diagnostica?»

### 3 · obl_b6f6211be439 — aislar controles/alertas/extinción ANTES de intervenir ‖ CORE-REQUIRED · conf alta

**Lo que la respuesta SÍ dice:** ordena intervención física en un detector vivo — abrir la caja
(paso del checklist §9.3), inspeccionar/limpiar conducto y filtro, «mide la tensión en los bornes
1 (+) y 2 (-) [F9]: 12,3–13,8 V-CC / 21,6–27,6 V-CC» (ítem 6 del MISMO checklist), lectura en
posición V. Cero menciones de bloquear/desconectar/inhibir (probes = 0).

**Cita literal de la fuente** (ASD535_TD_T131192es_h, PDF p121 = impresa 121/134, chunk 5b6a3a19,
§9.3 «Comprobaciones de mantenimiento y funcionamiento» — la Indicación ENCABEZA el checklist):
> «**Indicación** — Para evitar que los controles de incendios, las alertas remotas y las zonas de
> extinción se disparen al llevar a cabo los trabajos de mantenimiento, es **imprescindible**
> bloquearlos o desconectarlos previamente.»
> Ítem 1 del checklist: «Bloquear o desconectar el control de incendios y la alerta remota en la CDI
> de orden superior.»

**Render:** `s269_goldreview_renders/hp002_obl_b6f6211b_p121.jpg` (fuente, render local del PDF;
chunk p121 = PDF p121, verificado). La Indicación y el ítem 6 (bornes) que la respuesta cita son
visibles en la misma página.

**Veredicto propuesto: CORE-REQUIRED (conf alta).** La respuesta saca su paso 5 del ítem 6 de este
checklist y poda el gate de seguridad que lo encabeza. Un ASD conectado a una CDI puede disparar
extinción/alerta remota durante el diagnóstico: clase mandatory_safety_or_verification_omission
(s243). s156: Sol CON contexto completo SÍ lo incluyó → no es «dato que ningún experto incluiría».
En la vara técnico-PCI es lo primero que se hace antes de tocar el equipo.

**TU MARCA: [X] ✅ [ ] ✏️ [ ] ❌** — notas: ______________________

---

### 4 · obl_a5d9fa1f9253 — «100 % = valores nominales registrados en el reset inicial» ‖ CORE-REQUIRED · conf media — el CORE MÁS BORDERLINE

**Lo que la respuesta SÍ dice:** usa <100%/80%/90% como números pelados; «Compara el valor leído con
el registrado en el protocolo de puesta en funcionamiento [F9]» (sustituto operativo parcial); y la
advertencia de reset [F7] («Realizar un reset inicial con orificios obstruidos puede impedir que el
ASD535 dispare la alarma») — que sin este hecho queda sin mecanismo. «Valores nominales» = 0 hits
(los 2 «nominal» de la respuesta son de TENSIÓN, no de flujo).

**Cita literal de la fuente** (ASD535_TD, PDF p28 = impresa 28/134, chunk 414ce99c, §2.2.10):
> «Al realizar un reset inicial del dispositivo, <u>y con el conducto de aspiración intacto</u>, se
> registrarán los valores de la medición del flujo de aire y se guardarán como **valores nominales
> (100 %)**. Para ello, el sistema colocará los valores en el centro de una ventana de monitorización
> creada electrónicamente.»

**Render:** `s269_goldreview_renders/hp002_obl_a5d9fa1f_p28.jpg` (fuente, render local; chunk p28 =
PDF p28, verificado; la frase subrayada aparece como «tachado» en el texto extraído — artefacto).

**Veredicto propuesto: CORE-REQUIRED (conf media).** Es el marco que da significado a toda la escala
del diagnóstico para una alarma INTERMITENTE (lecturas fluctuantes contra referencia); el gold v1 lo
tiene dentro de un fact CORE (`gold_answers_v1.yaml:169-175`); la propia advertencia de reset de la
respuesta es ininteligible sin él; s156: Fable con contexto completo lo incluyó. **Borde declarado:**
existe el sustituto del protocolo de puesta en funcionamiento — con vara de accionabilidad estricta
pura bajaría a SUPPLEMENTARY. Es la frontera «dato operativo vs glosa»: tu llamada.

**TU MARCA: [X] ✅ [ ] ✏️ [ ] ❌** — notas: ______________________

---

### 5 · obl_07eee3300535 — los literales «120 %» y «A11 a C32» ‖ SUPPLEMENTARY (demote PARCIAL) · conf media

**Lo que la respuesta SÍ dice:** umbral bajo **80 %**, ventana **±20 %**, retardo **300 s** (los 3
anchors presentes); el diferencial direccional «Valor > 100 % → rotura de tubo [F1][F9]» + código
002; y el scope cualitativo «si la sensibilidad LS-Ü configurada es ±20 % (estándar)» + advertencia
W01-W48/EN 54-20 [F6]. Ausentes SOLO los literales «120 %» y «A11 a C32».

**Cita literal de la fuente** (ASD535_TD, PDF p28, mismo chunk 414ce99c):
> «En las posiciones de conmutador **A11 a C32**, cualquier variación de este valor que supere el
> ±20 % – es decir, por debajo del 80 % (suciedad/obstrucción) o por encima del **120 %** (rotura de
> tubo) – disparará un aviso «fallo flujo de aire» una vez transcurrido el tiempo de retardo de
> **300 s** de la LS-Ü.»

**Render:** `s269_goldreview_renders/hp002_obl_07eee330_p28.jpg` (misma página que la fila 4; el
párrafo EN 54-20 completo es visible bajo la Indicación).

**Veredicto propuesto: SUPPLEMENTARY (conf media) — demote de los ANCHORS «120 %» y «A11 a C32» (o
split de la obligación), NO de la obligación entera** (80 %/±20 %/300 s siguen required y están
presentes). La pregunta es flujo BAJO: el 120 % es el umbral de disparo del lado contrario (nunca se
ejercita en esta tarea) y el diferencial que sí se necesita (>100 % ⇒ rotura) ya está servido — F9
usa exactamente esa regla de inspección. Contra-evidencia declarada: gold v1 fact CORE 2 incluye el
120 % y Sol con contexto completo cubrió esta obligación (s156). Guard s243 intacto: este demote es
POR-PREGUNTA, no licencia general para podar extremos de rangos.

**TU MARCA: [X] ✅ [ ] ✏️ [ ] ❌** — notas: ______________________

---

## hp011 — «En la Morley RP1r, después de descargar la extinción el sistema no vuelve a estado normal tras resetear. ¿Qué comprobar?»

### 6 · obl_161564ff41bf — la granularidad «intervalos de 5 seg» del t.A ‖ SUPPLEMENTARY (demote) · conf alta — el demote MÁS LIMPIO

**Lo que la respuesta SÍ dice** (§4): «Si el parámetro de duración de extinción está configurado
como **"- -"** (guiones), el circuito de extinción permanece activado **hasta que se rearme la
central** [F11]. Verifica que este parámetro esté configurado con un tiempo en segundos (**05 a 295
seg.**)». Único átomo perdido: «intervalos de 5 seg».

**Cita literal de la fuente** (HLSI-MN-103_RP1r-Supra_lr, PDF p56 = impresa 56, chunk 2d45a70a,
§5.3.1 «Opciones extinción», fila `t.A`):
> «**Valor variable de 05 a 295 seg.** | Tiempo de activación del circuito de extinción, o periodo
> de inundación. **Variable en intervalos de 5 seg.** — **- -** | Circuito activado hasta rearme de
> la central (por defecto)»

**Render:** `s269_goldreview_renders/hp011_obl_161564ff_p56.jpg` (fuente, render local; chunk p56 =
PDF p56 = impresa 56, verificado).

**Veredicto propuesto: SUPPLEMENTARY (conf alta).** La pregunta es diagnóstica («por qué no vuelve a
normal tras reset»), no de programación: la semántica de «- -» y el rango válido YA están servidos;
el paso de 5 s solo se usa al teclear un valor nuevo y la UI del panel lo impone (programar 122 s y
que ajuste a 120 s no tiene consecuencia técnica). Demote del gold DE ESTA PREGUNTA: el bundle
rango+unidad+paso sigue exigible en una pregunta de programación del parámetro.

**TU MARCA: [X] ✅ [] ✏️ [ ] ❌** — notas: Como decisión de diseño, ¿tiene sentido que seamos más conservadores y que también sirvamos estos puntos "supplementary" para que el técnico tenga una visión más completa, siendo consciente de que es supplementary? 

---

### 7 · obl_2f5d79e354b9 — r.i = «- -»: rearme inhibido hasta fin de extinción / t.A ‖ CORE-REQUIRED · conf alta

**Lo que la respuesta SÍ dice** (§1): cubre rI SOLO como 00/01-30 min [F3][F12] («si está entre 01 y
30, la central no permitirá el rearme hasta que transcurra ese tiempo; por defecto 00») — un técnico
que lea `r.i = "- -"` en el panel no sabe interpretarlo, e incluso puede descartar rI como causa al
no ver 01-30. Su único «- -» (§4) habla de OTRO parámetro (duración de extinción, F11). F13 jamás
citado; «finalizar extinción» = 0 hits → source_fragment_selection_loss real (único de los 12).

**Cita literal de la fuente** (HLSI-MN-103_RP1r-Supra_lr, PDF p63 = impresa 63, chunk 475a8f18,
§5.3.5 «Otras opciones», fila `r.i` — leída al píxel, iconos 7-seg resueltos con zoom 500 dpi):
> «[r.i] **Rearme inhibido tras extinción** — De acuerdo con la norma UNE-EN 12094-1:2004, apartado
> 4.12.2… **- - | Rearme inhibido hasta finalizar extinción o cuando agotado tiempo configurado en
> parámetro t.A (t.A → 0 seg.)** · 00 | Rearme permitido en cualquier momento (por defecto) ·
> De 01 a 30 | Rearme inhibido durante intervalo definido (expresado en minutos)»

**Render:** `s269_goldreview_renders/hp011_obl_2f5d79e3_p63.jpg` (fuente) + zoom
`hp011_obl_2f5d79e3_p63_zoom_ri_500dpi.jpg` (los dos iconos del paréntesis).

**Veredicto propuesto: CORE-REQUIRED (conf alta).** Es el ÚNICO hecho servido que explica el síntoma
literal de la pregunta: con r.i="- -" el panel RECHAZA el rearme POR DISEÑO hasta fin de extinción o
agotar t.A — no es avería. Sin él, el técnico espera 30 min (tope que la respuesta sí da), concluye
avería y sustituye hardware. NO es source-conflict (F12 VSN-RP1r y F13 RP1r-Supra son manuales de
variantes distintas). Caveat identidad declarado: F13 es del manual RP1r-Supra (=Notifier según
ground-truth s78) y la pregunta dice «Morley RP1r»; el gold congelado ya responde familia-completa
citando F11 del mismo doc Supra sin escopar — dentro de su propio marco, exigible (ideal: incluirlo
ESCOPADO «en RP1r-Supra, r.i…»).

**TU MARCA: [X] ✅ [ ] ✏️ [ ] ❌** — notas: ya tuvimos una conversación sobre si era r.i o r.1 (no me acuerdo qué concluimos), pero seguro que no es t.Fi
**Nota de riesgo (hallazgo del píxel):** los artefactos de la cadena (s113 freeze, s235, s163,
triage) citan «parámetro **t.Fi** (t.A → 0 seg.)». Al píxel NO hay ningún t.Fi: los dos iconos
7-seg leen **t.A** (mismo glifo que el t.A de §5.3.1). Si aceptas y se edita el gold, el ancla debe
ser **t.A** (o declarar la ambigüedad 7-seg); anclar «t.Fi» reproduciría el error de extracción.
El identificador `r.i` es también display 7-seg («r.1» ≈ «r.i») — restricción de dominio aplicada.

---

## hp017 — «¿Cómo se programa el retardo de salida de alarma principal en la Notifier PEARL?»

### 8 · obl_872c35fb41d7 — prosa «seis» vs tabla con SIETE tipos ‖ SOURCE-CONFLICT → re-spec a DISCLOSURE · conf alta

**Lo que la respuesta SÍ dice:** «Hay **6 tipos disponibles** [F1]» seguido de **7 bullets** (Fijo,
Estándar, No Silenc., Est. Ext., RetExtStd, No Sil. Ext, SinRetExt) y 7 bloques de comportamiento
[F2] — reproduce AMBOS lados del conflicto **sin declararlo**.

**Cita literal de la fuente** (997-671-005-3_Configuration_ES, PDF p44 = impresa «Apéndice 5-3»,
chunks 570d9951 + 7e34cb72 — **prosa y tabla en la MISMA página**, un solo render):
> Prosa (A5.3 Tipos de retardo): «Se puede asignar **uno de seis tipos** de retardo de salida a una
> regla, como se explica a continuación.»
> Tabla (misma página): cabecera «**Tipos de retardo**» con **SIETE columnas** — Fijo · Estándar ·
> No Silenc · Est. Ext. · RetExtStd · No Sil. Ext · SinRetExt — verificadas al píxel una a una;
> los 7 vectores de comportamiento son distintos entre sí (sin duplicado OCR). El screenshot LCD
> del margen muestra el desplegable `Ret.Tipo` con la lista scrollable de tipos.

**Render:** `s269_goldreview_renders/hp017_obl_872c35fb_p44.jpg` (fuente, render local; el riesgo
«mostrar AMBOS renders si están en páginas distintas» decae: ambos fragmentos son la misma página).

**Veredicto propuesto: SOURCE-CONFLICT (conf alta) → re-spec de la obligación a DISCLOSURE.** La
fuente es internamente inconsistente en la misma página; la obligación autorada ancla «seis» y es
insatisfacible de forma consistente con la enumeración. Resolver a 6 soltaría un tipo (peligroso);
afirmar 7 tergiversaría la prosa citada. Conducta objetivo (política del proyecto, s243: «disclose
rather than resolve»): DECLARAR la discrepancia («la prosa dice seis; la tabla recoge siete») +
registrar `document_value_conflict` (misma clase que el conf_26f6 «7:Causa y Efecto» vs «8:Causa y
Efecto» ya registrado). Requiere tu marca porque cambia la SPEC de la obligación, no solo su peso.

**TU MARCA: [X] ✅ [ ] ✏️ [ ] ❌** — notas: muy bien identificada esta inconsistencia.
**Nota de riesgo (instrumento):** el check declarado-vs-enumerado del scorer es sensible a formato
(inestable entre réplicas s242); al re-spec, verificar que una frase de disclosure no dispare
igualmente el detector de contradicción.

---

### 9 · obl_b2043cd4379b — instrucción de ENTRADA (anatomía de la regla) ‖ CORE-REQUIRED · conf media

**Lo que la respuesta SÍ dice:** salta de «Selecciona «8: Causa y Efecto»… elimínalas [las reglas
por defecto]» a «Dentro de cada regla, debes seleccionar el tipo de retardo» sin explicar jamás qué
COMPONE una regla («instrucción de entrada»/«condición de entrada»/«regla consta» = 0 hits, sin
paráfrasis en lectura completa).

**Cita literal de la fuente** (997-671-005-3_Configuration_ES, PDF p42 = «Apéndice 5-1», chunk
d27b1a1b declara p41 → off-by-one declarado; A5.1 verificado al píxel en p42):
> «**Una regla consta de dos instrucciones de acción**, como se explica a continuación: —
> **Instrucción de entrada**: esta parte de la regla es una **condición de entrada**, como una
> alarma, una avería o la detección de un cambio de estado en una determinada categoría de entrada
> (condiciones de regla de coincidencia de zona, entrada de un equipo externo, etc.).»

**Render:** `s269_goldreview_renders/hp017_obl_b2043cd4_p42.jpg` (fuente, Storage — objeto existente
no listado en el bridge; las 4 obligaciones de A5.1 son visibles en esta única página).

**Veredicto propuesto: CORE-REQUIRED (conf media).** La pregunta es «¿cómo se programa…?» y el
retardo es un CAMPO de una regla que el técnico tiene que construir: sin la espina
entrada→salida el procedimiento tiene un agujero entre abrir el editor y elegir el tipo de retardo.
El gold v1 marca exactamente este hecho como tipo:core. El contra-argumento «el fabricante
recomienda el PC-tool» no salva: la anatomía aplica igual en el PC-tool.

**TU MARCA: [X] ✅ [ ] ✏️ [ ] ❌** — notas: ______________________

---

### 10 · obl_7aa723717412 — instrucción de SALIDA (equipos asignados) ‖ CORE-REQUIRED · conf media

**Lo que la respuesta SÍ dice:** nunca conecta «regla» con sirenas/relés ni describe qué hace la
Regla 1 por defecto que ella misma ordena borrar («equipos asignados»/«sirenas o relés»/«regla 1»/
«condiciones de entrada» = 0 hits).

**Cita literal de la fuente** (mismo render PDF p42, A5.1):
> «**Instrucción de salida**: esta parte de la regla **solo puede procesarse cuando se cumplen todas
> las condiciones de entrada** programadas. **La salida se refiere al accionamiento de uno o más
> equipos asignados, como sirenas o relés**, o el cambio de estado de una condición de salida,
> mediante un flag lógico, para realizar una acción de fase secundaria…»

**Render:** `s269_goldreview_renders/hp017_obl_7aa72371_p42.jpg` (fuente) · vecina +1
`hp017_obl_7aa72371_p43_vecina.jpg` (PDF p43 = «Apéndice 5-2», A5.2: «Regla 1: CUALQUIER entrada de
alarma activa TODOS los equipos de salida» + «**Es fundamental borrar la regla 1** si se va a
realizar una programación específica, ya que, si no, esta será **anulada**» — el contexto de las
reglas por defecto que la respuesta manda borrar).

**Veredicto propuesto: CORE-REQUIRED (conf media).** La pregunta es sobre el retardo de la SALIDA de
alarma y la instrucción de salida es donde se ASIGNA el equipo retardado. Kernel core para esta
pregunta; el cualificador AND («todas las condiciones») es exigible sobre todo en reglas
multi-entrada/coincidencia — demote parcial del cualificador (no del kernel) sería defendible si se
re-atomiza: márcalo en ✏️ si es tu preferencia.

**TU MARCA: [X] ✅ [ ] ✏️ [ ] ❌** — notas: ______________________

---

### 11 · obl_16637b935bd4 — «evite las lógicas contradictorias» ‖ CORE-REQUIRED · conf media

**Lo que la respuesta SÍ dice:** ordena borrar las reglas por defecto y crear reglas personalizadas,
pero nunca generaliza el peligro («contradictor» = 0 hits).

**Cita literal de la fuente** (mismo render PDF p42 — recuadro de advertencia «!» al pie de A5.1):
> «**Al programar reglas de causa-efecto evite las lógicas contradictorias.**»

**Render:** `s269_goldreview_renders/hp017_obl_16637b93_p42.jpg`.

**Veredicto propuesto: CORE-REQUIRED (conf media).** Warning explícito del fabricante dentro del
bloque citado; en una central de incendios la lógica contradictoria entre reglas puede anular EN
SILENCIO el retardo o la alarma (una Regla 1 residual pisa la regla retardada). Guard s243: «never
prune explicit warning clauses from an otherwise cited rule block».

**TU MARCA: [] ✅ [x] ✏️ [ ] ❌** — notas: creo que estoy de acuerdo con el merge, ya que con que lo exijamos una vez es suficiente.
**Nota de riesgo (cardinalidad):** merge-candidate con la fila 12 — ambos salen del MISMO recuadro
de warning; el contenido es exigible UNA vez (diseño + verificación), contarlo como 2 misses infla
el residual. Propuesta: consolidar en 1 obligación de bloque-warning (marca ✏️ si prefieres el
merge; la fila 12 es la formulación más fuerte del par).

---

### 12 · obl_0d6a30948dfd — «probar rigurosamente todas las reglas en la puesta en marcha» ‖ CORE-REQUIRED · conf alta

**Lo que la respuesta SÍ dice:** nada del test de reglas («probar»/«puesta en marcha»/«todas las
reglas» = 0 hits). El gold v1 lo incluye en su procedimiento (paso 5).

**Cita literal de la fuente** (mismo render PDF p42 — mismo recuadro «!»):
> «**Es de vital importancia probar rigurosamente todas las reglas durante la puesta en marcha del
> sistema para verificar que no haya conflictos lógicos entre ellas.**»

**Render:** `s269_goldreview_renders/hp017_obl_0d6a3094_p42.jpg`.

**Veredicto propuesto: CORE-REQUIRED (conf alta).** El fabricante acopla la verificación AL
procedimiento de programación (mismo bloque A5.1) con lenguaje de máxima obligatoriedad — no es
SCOPE-OUT. El test de reglas C&E en puesta en marcha es obligación de oficio y aquí el retardo
cuelga de la salida de alarma PRINCIPAL (riesgo operativo directo). Ver nota de merge en la fila 11.

**TU MARCA: [X] ✅ [ ] ✏️ [ ] ❌** — notas: ______________________

---

## Apéndice (informativo — NO requiere adjudicación ahora): los 2 retrieval-miss

Secuencia vigente (s161/s188/PLAN): tratarlos como residual y atacar los 12 de síntesis primero.
Ambos hechos están píxel-verificados VERBATIM en corpus (chunk_id + sha256 + quote inmutable) →
cero corpus-gap, cero instrument-FN (`feedback_corpus_gap` confirmado otra vez).

**cat017#2 — licencia CLIP POR CIRCUITO DE LAZO (INSPIRE E10/E15).** La respuesta ya dice «CLIP
requiere licencia adicional» pero omite el cuantificador por-lazo (chunk 5bb83899, HOP-138-9ES p5:
«se requiere una licencia para cada circuito de lazo CLIP»; pool_position=null, ni entra al pool-50).
Ya intentado: lane determinista s114 (GO local / NO-GO integración por overfit, heldout 0/24) ·
gates s126/s174 (facet quantified_entitlement NO_GO: 3 TPs, todos Notifier — single-manufacturer).
Vías restantes: canal hyq/DEC-099 (fila ya generada para el chunk exacto; pendiente de cuota/re-carga
DEC-102, pairing no medido) o aceptarlo como residual.

**hp010#1 — clave Nivel 3 + desbloqueo de memoria antes de la Autobúsqueda (Morley DXc).** Miss
parcial multi-span en el MISMO manual: el span de autobúsqueda se sirve (p48, posición 1) pero el
prerequisito de acceso no (chunk 155a90fe, p37, pool_position=null). Peor: la respuesta congelada
dice «Nivel 2, clave por defecto 1234» — en campo = quedarse bloqueado delante de la central. ES el
más convertible de los dos: en la adjudicación ciega s174 su facet (access_prerequisite) PASÓ solo
sus umbrales de independencia (8 TPs / 7 fabricantes); el NO_GO global vino del facet hermano.
Camino: re-scope del gate s174 POR FACET (decisión explícita, riesgo gate-shopping) → validación
runtime → cascada default-off estilo s188; ~$0/query. Todo crédito sería diagnóstico
(official_fact_delta=0 con flags off).

---

## Qué pasa tras tu adjudicación

1. Aplico las ✅/✏️ **vía `gold_store`** (la puerta valida `metodo`+`verificado_por`; provenance =
   tu adjudicación s269; DEC-025). Los renders de este packet son la evidencia al píxel de cada
   edición. **NADA se edita sin el ✅.**
2. **El denominador del funnel pasa a 154** (3 demotes fuera del required-set) y obl_872c se
   re-registra como `document_value_conflict` con obligación de DISCLOSURE. Foto objetivo:
   **151/154 (98 %)** = convertir los 8 CORE confirmados (los 2 retrieval quedan residual, Apéndice).
3. Re-score dirigido SOLO de los golds tocados con el instrumento determinista (s163/answer_planner,
   0 llamadas a modelo) — sin re-correr nada global; delta honesto a DECISIONS/LEVER_DIGEST
   (recordatorio s242: la foto 143/12 tiene swing documentado de ±1-2 hechos por qid entre réplicas).
4. Los hallazgos de extracción del píxel (t.Fi→t.A; subrayado→tachado) se anotan en los golds/
   obligaciones que toquen — no se re-litiga el pipeline de extracción aquí.
