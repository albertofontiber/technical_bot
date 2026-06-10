# s51 — Dossier de SELECCIÓN de golds #2-6 (GATE del dúo, ANTES de autorar)

**Qué se revisa:** la SELECCIÓN (no la autoría) de los próximos golds del ruler, en el paso 0
de `RULER_DESIGN §2` (no-duplicado + dimensión-de-fallo desde la FUENTE + chunks_v2 JAMÁS
criterio de selección). **Impacto:** MEDIO en zona de dolor (corpus / idiomas ES-EN / esquema
del ruler) → exige sub-agente Claude + cross-model GPT-5.5. **Ataca el FRAMING y el alcance,
no me ratifiques.** Decisión rectora previa: `DEC-025(f)` — mix #2-5 = **mayoría estratos-A/B
autorables (es-en / conflicto / síntesis) + 1 conducta barata (clarify)**; admit/refuse-inference
DIFERIDOS al "contrato de ausencia". Alberto pidió además hacer conflicto **A (revisión) Y B
(es-us)** → el batch sube a #2-6.

## Las 5 conductas (RULER §1)
answer · answer-con-conflicto (ES-vs-US: surfacear ambas) · clarify (near-name → candidatos del
catálogo) · admit (corpus no cubre) · refuse-inference. **conflicto-revisión (mismo idioma,
rev N vs N+1) = answer "latest-wins", NO answer-con-conflicto** (RULER §1:67).

## Censo de los 23 golds EXISTENTES (para verificar NO-DUPLICADO)
hp001 CAD-250 menú prog avanzada (answer) · hp002 ASD535 flujo bajo (answer, oem) · hp003 CAD-150
baterías 24V (answer) · hp004 DGD-600 tensión/consumo 2 versiones (**clarify**) · hp005 ID3000 zona
coincidencia 2 detectores (answer, tabla) · hp006 AFP-400 aviso Tierra (answer) · hp007 VESDA-E VEP
test anual (answer, tabla) · hp008 ID3000 detectores humo compatibles (answer, tabla, content-pobre) ·
hp009 Morley ZXe RFL lazos (answer, diagrama) · hp010 Morley DXc añadir detector (answer) · hp011
Morley RP1r tras extinción no resetea (answer, scan-ocr+oem) · hp012 AM2020/AFP1010 nº lazos+disp
(**answer-con-conflicto**, conflicto-es-us) · hp013 ADW535 batería tampón (answer, oem) · hp014 ID2000
módulo aislamiento (answer) · hp015 CCD-103 desactivar detector (answer) · hp017 Notifier PEARL retardo
salida alarma (answer) · hp018 Morley ZXe sirena convencional (answer) · hp019 ASD535 rango temp (answer,
oem) · hp020 INSPIRE contraseñas N2/N3 (answer) · cat001 PEARL equipos por lazo SLC (answer) · cat005
Fidegas CS4 características (answer, tabla) · cat007 FAAST LT-200 relés/sirena (answer, **es-en**) ·
cat008 M710/MI-DMMI cableado+resistencias (answer, diagrama+oem).
**Cobertura de estratos AUTORABLES:** multi-doc 10 · oem-relabel 5 · tabla-matriz 4 · diagrama 2 ·
**es-en 1 (cat007)** · **conflicto-es-us 1 (hp012)** · scan-ocr 1 · **familia-ambigua 0** ·
síntesis-intra-manual / conflicto-revisión / mezcla-cross-product **0** (las 3 dims que DEC-025(c)
sacó a la luz). Conductas: 21 answer · 1 clarify · 1 conflicto · **0 admit · 0 refuse**.

## SELECCIÓN PROPUESTA (todo source-first; NINGÚN criterio vino de chunks_v2)

### #2 — es-en (refuerza n=1) · conducta answer
- **Candidato:** `WFDEN` (detector de flujo de agua, `Manuales_*/WFDEN_Manual_I56-4051.pdf`,
  ES~4 / EN~193 = **EN-only real**). Alt: `FS-1100` (TM380002, ES~0).
- **Dimensión-de-fallo (desde la fuente):** el dato vive solo en manual EN → un técnico ES
  obliga a puentear ES→EN (recall/term-mismatch). No-dup: ningún gold cubre WFD; cat007 (es-en)
  era bilingüe ES+EN → este es EN-only, distinto sub-caso.

### #3A — conflicto-revisión (NUEVA dim, n=0) · conducta answer (latest-wins)
- **VERIFICADO POR MÍ (regla C):** NFS Supra (Morley/Honeywell, `HLSI-MN-025-I`), dos ediciones EN
  digital-native: **v.04 (Feb 2015)** `Manuales_Morley/HLSI-MN-025-I_NFS Supra Series.pdf` vs
  **v.05 (Abr 2015)** `Manuales_Notifier/EN_unico/HLSI-MN-025-I_NFS Supra Series v05.pdf`.
- **Valor que cambió (diff de tokens numéricos):** resistencia de fin de línea (RFL): **`4K7 Ω`
  (v.04) → `6K8 Ω` (v.05)**, consistente en p27/28/29/30/43 (5×, no es ruido OCR); + consumo máx.
  detectores **`3 mA (3000 µA)` → `4 mA (4000 µA)`** (p29). Latest-wins → respuesta = **6K8 Ω / 4 mA**.
- NFS Supra no está en ningún gold (no-dup ✅). Requiere +1 línea `conflicto-revision` a
  `gold_store.ESTRATOS_AUTORIA` (cambio sancionado por la nota `gold_store.py:59`, "NO es la
  consolidación diferida").
- **Caveat declarado:** un conflicto-revisión "muerde" sólo si el corpus contiene la rev vieja;
  si chunks_v2 sólo tiene v.05, el bot acierta trivialmente. Sigue siendo válido (testea
  latest-wins, RULER §1:71). **Si la rev vieja está en chunks_v2 = diagnóstico POST-hoc, NO
  criterio de selección** (no lo miro para elegir).

### #3B — conflicto-es-us (refuerza n=1) · conducta answer-con-conflicto · **BLOQUEADO**
- **2 búsquedas independientes + verificación regla-C:** el corpus es español (Notifier España /
  Detnov / Honeywell Iberia / Morley). Los ÚNICOS manuales US reales son `15088SP` (AM2020/AFP1010
  → ya en hp012) y `50253SP` (AFP-300/400 → ya en hp006). Los demás SP (`15037`=pantalla LCD,
  `15090/15092`=anunciador red INA, `15888`=transpondedor XP, `50257`=NOTIFIRENET) son **accesorios
  US-only (Fire-Lite/Notifier US, Northford CT) SIN contraparte España** → no hay conflicto posible,
  y su texto sale corrupto (PDFs cifrados 1994-98).
- **No hay es-us fresco limpio.** Recomendación (Pregunta cero): **NO fabricarlo** (RULER §0 / DEC-025
  "no forzar el caso"). Opciones: (a) mantener 4 golds + **diferir es-us** hasta que entren manuales
  US al corpus (escala a 30+); (b) reusar familia cubierta (AM2020/AFP1010) con una pregunta de un
  parámetro DISTINTO al de hp012 (declarando el solape de producto). **Pido veredicto del dúo.**

### #4 — síntesis-completitud intra-manual (NUEVA dim, n=0) · conducta answer
- **Candidato:** `AM-8200N` (panel Detnov/Notifier, `Manuales_*/AM-8200N manual ... rev 3 ...pdf`,
  75 pp, 63 hits de "lazo"). Pregunta = capacidad de lazo / autonomía de baterías que exige FUSIONAR
  varias secciones de UN manual (consumo + Ah + límite de lazo), no ≥2 manuales (eso es multi-doc).
- No-dup: AM-8200N no está en golds. Requiere +1 línea `sintesis-completitud` a `ESTRATOS_AUTORIA`.
  **El hecho concreto se fijará en autoría** (localización exhaustiva); aquí sólo se confirma que el
  producto soporta una síntesis intra-manual.

### #5 — familia-ambigua (NUEVA dim, n=0) · conducta clarify (la "barata" del mix)
- **Candidato:** familia `"751"` = `CPX-751E` (`I56-0790-003`, analógico direccionable ionización) /
  `IDX-751` (`I56-3383-002`, ionización T4/T5) / `SDX-751EM` (`I56-1306-002`, óptico) — **tipos
  DISTINTOS, mismo sufijo**. Todos en `model_catalog.json` (fuente única, D6). Pregunta tipo "el
  detector 751" → clarify con candidatos acotados del catálogo.
- No-dup parcial: hp008 LISTA detectores 751 como compatibles con ID3000 (answer-lista); esto es
  DESAMBIGUACIÓN (clarify) → conducta y pregunta distintas. **Solape de producto declarado.**

## Decisiones a DESAFIAR (no me ratifiques)
1. ¿Alguna dimensión se apoya, aunque sea de refilón, en chunks_v2 (el vicio s50)? (Mi claim: NO.)
2. ¿Algún DUPLICADO real con los 23 (más allá de los solapes declarados de #5/hp008 y cat007/#2)?
3. ¿#3A es conflicto-revisión genuino o lo fuerzo? ¿el cambio 4K7→6K8 es real (no artefacto)?
   ¿el caveat "muerde sólo si la rev vieja está en chunks_v2" invalida el gold?
4. ¿#3B está legítimamente bloqueado o me rindo pronto? ¿la opción (b) reusar-familia es un
   duplicado encubierto de hp012?
5. ¿El mix sigue cumpliendo DEC-025(f) si #3B cae (queda 3 A/B + 1 clarify)? ¿desbalanceado?
6. ¿Añadir 2 tags (`conflicto-revision`, `sintesis-completitud`) a `ESTRATOS_AUTORIA` es el
   cambio-de-1-línea sancionado, o es la **consolidación diferida disfrazada** (mi sesgo de
   empaquetar rumbo)?
7. ¿WFDEN / AM-8200N / familia-751 representan BIEN su dimensión, o hay candidato más limpio?

## Gaps auto-declarados (Protocolo 2)
- #3B bloqueado (sin fuente fresca). #4: el hecho de síntesis aún no fact-verificado (se hace en
  autoría). #2: el "WFD sin manual ES" no 100% confirmado (se confirma en localización). #5: solapa
  productos con hp008. #3A: el "bite" depende de qué edición tenga chunks_v2 (post-hoc).

---

## POST-GATE (dúo s51, 2026-06-07) — veredicto NO-SÓLIDA → correcciones aplicadas
Dúo convergente (cross-model GPT-5.5 6/6 + sub-agente Claude 4/4, **0 FP**), verificado regla C:
- **#5 CAMBIADO de familia 751 → familia MMX/MM** (módulos monitores): (a) `SDX-751EM`/`SDX-751` NO
  están en `model_catalog.json` (el clarify ancla en el catálogo, D6) + (b) hp008 ya enumera TODA la
  familia 751 en sus `atomic_facts` (solape total). `MMX-10/MM-10/MMX-102E/MMX-10M` están en el
  catálogo, NO en ningún gold, near-names confusables → clarify limpio. (Specs distintas a confirmar
  en autoría.)
- **#4 → PROVISIONAL:** AM-8200N es candidato; confirmar en autoría que el hecho EXIGE síntesis
  intra-manual (si no, pivotar). No es gold "seleccionado" hasta verificarlo.
- **#3A:** se mantiene (genuino, verificado al píxel). Framing honesto: muerde si ambas revs están en
  el índice evaluado; v04 SÍ está en el filesystem → probable; confirmar post-hoc, NO como criterio.
  Anclar el latest-wins (6K8 Ω) en página limpia (p27/28/29/43; v05 tiene un 4K7 residual en p30).
- **#3B:** bloqueo confirmado; retirado el sub-claim FALSO "PDFs cifrados" (no encriptados; extracción
  con glifos corruptos por codificación de fuente). Framing → "no localizado con búsqueda exhaustiva".
  Opción (b) reusar AM2020/AFP1010 = duplicado encubierto de hp012 → DESCARTADA. **es-us DIFERIDO**
  hasta que entren manuales US al corpus (escala a 30+).
- **#2:** "EN-only real" → "probable EN-only" (confirmar en localización; no hay PDF ES de WFD visible).
- **Tags:** añadir `conflicto-revision` + `sintesis-completitud` a `ESTRATOS_AUTORIA` **con su def**
  (1-2 líneas cada uno) — cambio sancionado (`gold_store.py:58-61`), NO la consolidación diferida.

**Selección final post-gate = batch #2-5 (4 golds):** #2 es-en (WFDEN) · #3A conflicto-revisión
(NFS Supra, ✅verificado) · #4 síntesis (AM-8200N, provisional) · #5 familia-ambigua (MMX/MM, clarify).
es-us DIFERIDO. Mix DEC-025(f): 3 A/B + 1 clarify ✅.
