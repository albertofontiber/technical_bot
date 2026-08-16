# s324 — Propuesta: aplicar el LOTE FIRMADO por Alberto (§0.B s323 + reglas R1–R7) con puertas que prueban

**Estado: NADA APLICADO en catálogo ni Supabase** (solo la baja de 7 documentos ya adjudicada:
`scripts/s324_retirar_docs.py`, recibo `evals/s324_retirar_docs_aplicar_20260816T105639Z.json`).
Todo lo demás vive en un PLAN verificado + un DRY-RUN sobre copia + un CENSO del radio de explosión.
Pido al dúo que ataque el plan ANTES de que el writer escriba una fila.

## 1. Qué firmó Alberto (16-ago-2026) — `evals/s324_reglas_residuo_adjudicacion_v1.json`
El residuo §1 de los packets E1/E1b (911 filas «una a una») cayó del bloque por FALTA DE REGLA o por
hechos mecánicos, no por variación del juez. En vez de firmar filas, Alberto adjudicó REGLAS:
- **R1** serie × categoría se aplica también al residuo de doc_map (manuales/FAQ que nombran una
  FAMILIA atestan a los productos de esa serie Y esa categoría). — OK
- **R2** un doc_map puede confirmar un candidate SOLO si es un MODELO CONCRETO nombrado como sujeto
  con cita verificada; las etiquetas de familia (2X-AT, VSN-Plus) nunca son producto: paraguas. — OK
  («la lógica valida los 3 puntos»: DX1e/2e/4e concretos; 2X-AT sub-familia táctil de 2X-A →
  apunta a sus modelos; VSN PLUS = VSN 4/8/12 PLUS según MIEMI130).
- **R3** OEM: un documento no crea ni amplía `vendido_bajo`; el mapa solo apunta a ids existentes bajo
  ese namespace. Resuelto desde el repo (gt FAAST/VESDA de s78–s91): nada que corregir. — OK
- **R4** token de portada sin id + cita verificada → alta + doc_map; la ficha sola nunca da un alta.
  Alberto: KE-DP3120W/KE-DP3121B son «mini-familias» (base + variantes SN/SNV); el dato: la base es
  además SKU con hoja propia. — OK
- **R5** → convertido: 6 fragmentos PT con hermano ES → BAJA (aplicada); HLSI-TI-007 (47 chars) →
  Alberto: «el modelo es VSN-4REL» → atestación por ficha + re-ingesta OCR pendiente. — OK
- **R6** candidate cuya única fuente está retirada → no se da de alta. — OK
- **R7** grafía concatenada A/B → A y B SOLO si cada uno tiene cita propia. — OK
- Además, del packet s323 §0.B: 38 limpias (serie × categoría), 4 «piden tu ojo» adjudicadas
  (DX Connexion; Excellence × detector; RP1r + «VSN-RP1r+»; guía 2X-A → FAMILIA), ampliar ZX en dos
  FAQ de DXc, mndt1160 → ExitPoint, ds_kidde_2x_at_fr_s → repetidor 2X-AT-FR-S.

## 2. Qué escribe el plan (`evals/s324_lote_firmado_plan_v1.json`, `scripts/s324_lote_firmado_plan.py`)
Cada fila lleva verificación contra el TEXTO COMPLETO del documento en `chunks_v2` (espacios
normalizados): la cita debe ser subcadena; cada producto nuevo/confirmado debe aparecer como TOKEN
EXACTO en el documento que lo sustenta (`autocheck_citas_altas`/`_confirmar` = true).

| Colección | Filas | Detalle |
|---|---|---|
| doc_map (altas, 1 fila por documento) | **63** | §0.B 34 + §0.B+Alberto 4 + §0.B.2 4 + §1.A por reglas (R1 6, R1+R2 1, R4 2, R5 1) + docs sustentantes de R7/R4 |
| doc_map (modificaciones) | 2 | la QOG «2X-AT Series» apuntaba a la etiqueta `kidde:2x-at` → 11 miembros; la FAQ RP1R pierde la etiqueta `vsn-plus` (+1 entry duplicada) |
| products ALTA | **15** | R4: KE-DP3120W-SN/-SNV, KE-DP3121B(-SNV), KE-DP3121W(-SN/-SNV) (familia KE-DP312x); R7: KE-DBA-ADPW-KIL/-ZIT, KE-IU3111-ZME, N-IO-MBX-1/-2, N-IO-SBX-1G, NX2/R/R, NX5/R/R |
| products CONFIRMAR (candidate→false) | **7** | R2: morley:dx1e/dx2e/dx4e + cajas dx1e-20s/dx2e-40m/dx4e-40l (MIE-MP-520rv04 §1.1/§3.1) + morley:vsn-12-plus (MIEMI130) |
| products RETIRAR | 2 | etiquetas `kidde:2x-at`, `notifier:vsn-plus` (exact sombrearía al paraguas en `resolve()`) |
| aliases quitar | 1 | «Visión VSN-Plus» → etiqueta retirada |
| umbrellas | 3 (+1 diferido) | «2X-AT» (serie, 11), «2X-A Táctil» (sinónimo, 11), «VSN PLUS» (familia, 3); **«2X-A» DIFERIDO** (ver §4) |
| retags DB (documents + chunks_v2 CAS) | 2 | 4188-1132-ES Qref: `CLSS-10` → `INSPIRE E10/E15` (18/18 chunks); MI_KIDDE_KE_IO3144: `KE-IO3144/KE-IU3110` → `KE-IO3122/KE-IO3144` (33/33) |
| NO aplicar (con motivo) | 57 | R6 (7); nombres CON barra que no son concatenación (DOA FJ/CPD, EFS/EM 8, PUL-D/EXT…) → pendientes del sí de Alberto (clase §0.C); acrónimos cortos (17) → Puerta A; confianza media (14) → K=5; componentes sin token (KE-DBA-LABW-LxS, N-IO-SBX-2G, ZLSM-ME/MR) |

**Refinamiento R1' (nacido del censo, no de la teoría):** si el documento NOMBRA modelos de la serie,
la atestación se ciñe a los nombrados; la lista derivada de serie × categoría solo cuando no nombra
ninguno. Efecto medido: los manuales 2X-A (MI/MU) atestan 26/38 (los 11 táctiles 2X-AT tienen manual
propio y 0 menciones; 2X-AF2-09 0), la QSG 2X-AT 10/11. `hlsi-ti-001` exento (adjudicación explícita
de Alberto; «RP1r» ahí es el nombre de la serie).

**Lo que el gate cazó antes de escribir:** (a) `fidegas:s3-t1`/`s2-t1` ya existían con la misma grafía
normalizada → solo doc_map, no duplicado (el validador `canonical_model DUPLICADO` lo paró);
(b) «ExitPoint» ya es alias de `systemsensor:pf24v` y I56-2961-000R prueba «EXITPOINT — PF24V
Directional Sounder» (línea = ExitPoint, modelo = PF24V) → mndt1160 apunta a pf24v, no se crea producto.

## 3. Censo del radio de explosión (`evals/s324_radio_explosion_v1.json`, writer en dry-run sobre COPIA)
- Detector del resolver (`catalog_resolver._resolvable_terms`): **1.667 → 1.697 (+30 / −0)**.
- 51 preguntas gold: **0 detecciones perdidas**; 1 nueva («central táctil 2X-AT de Kidde» → `2x-at`).
- 36 negativos (frases de técnico sin los productos del lote): **0 disparos** del patrón nuevo.
- Alias que se ACTIVAN al confirmar (r30): `DX2`→dx2e (variante tipográfica), `DX2e-40MP`, `FACP MODEL
  DX1e-20S/2e-40M/4e-40L` (nombre-largo con dígitos) — todos entran; ninguno dispara negativos.
- Regla mecánica del veredicto: STOP si pierde gold, si un término nuevo dispara en un negativo, o si
  es palabra común; `muy_corto`/`sin_digitos` = AVISO (hoy ya hay 43 términos con normkey ≤3: DX1, DX4,
  DXc, E10…). **Veredicto: PASS.**
- Mecánica T3 del writer: `--aplicar` exige un dry-run PASS del MISMO plan (sha); backup de los 4 .jsonl;
  escritura por `catalog_store.write_jsonl` (validador sobre el conjunto); retags con CAS por chunk y
  `documents.product_model`; censo posterior; recibo con instrucciones de reversión.

## 4. Diferido / abierto
- **Paraguas «2X-A»** (familia, 38 miembros por regla prefijo × categoría): el core «2·x·a» disparó en el
  negativo sintético «2 x a» (normkey 3 chars). Lo adjudicado (la guía → familia) ya lo cubre R1 vía
  doc_map a los miembros; el paraguas era modelado del autor → **el writer lo salta**; lo decide el dúo.
- `996-130-000-3 manuel d'utilisation ZX` (FR, 1 chunk = páginas finales): misma clase que los PT
  retirados (política de idiomas s65) pero sin sí de Alberto para FR → se atesta por R1 (7 ZX
  centrales) y se propone baja aparte.
- VSN2-PLUS / «Plus2» aparecen solo en docs NFS-SUPRA/UCIP/RP1R; quedan candidate (pregunta abierta a
  Alberto: ¿4º miembro o gama hermana?).
- HLSI-TI-007 (47 chars): re-ingesta con OCR pendiente; hoy solo atestación por ficha (Alberto).

## 5. Riesgos y gaps declarados
1. **R1 atesta miembros no nombrados** por diseño (guías de familia sin tabla de modelos: FAAST 13,
   ZX FR 7, QOG 2X-A 38): es la regla de Alberto, con R1' como freno evidencial. Riesgo: un doc de
   familia «entra» como allowed_source de un modelo que no cubre; efecto = ampliar el pool permitido,
   no fabricar hechos.
2. Citas de las altas KE-DP312x salen de la tabla de modelos multilingüe del MI (filas en polaco): son
   verbatim y verificadas, pero no son «frases de portada».
3. Confirmar 7 productos activa 5 alias existentes; medido: 0 disparos en negativos, pero el conjunto
   de negativos es sintético (36 frases del autor), no tráfico real.
4. Los retags cambian `product_model` de 51 chunks: findability positiva del doc_map (los ids del mapa
   son los mismos que el pm nuevo nombra); el snapshot legacy `data/model_catalog.json` NO se toca (E2
   sigue pendiente de Alberto).
5. Reversibilidad: backup de los 4 .jsonl + backup por chunk (`retags.backup`) + git.

## 6. Qué pido al dúo
Atacar: (a) si alguna regla se aplica más allá de lo firmado (sobre todo R1/R1' y la exención de
hlsi-ti-001); (b) filas concretas del plan cuya evidencia no sostenga la escritura; (c) el gate del
radio de explosión (regla del veredicto, negativos, alias activados) — ¿qué no mide?; (d) la mecánica
del writer (CAS, orden de escritura, backup, reversión); (e) la decisión de diferir «2X-A» y de NO
crear ExitPoint.

---

## ADENDA post-dúo r32 (Sol xhigh 6 hallazgos · Fable 5 6 hallazgos) — VERIFICADOS y aplicados antes de escribir

**Sol (3 críticos, 2 medios, 1 menor — 6/6 confirmados contra el código):**
1. *Freeze solo con `plan_sha`* → ahora el dry-run estampa `freeze` = sha de los 4 .jsonl + fingerprint del
   corpus + sha del snapshot de los chunks/documents a retaguear; `--aplicar` lo recalcula y ABORTA si difiere.
2. *Escritura no atómica* → se construye y VALIDA en tmp; backup; SOLO ENTONCES se sustituyen los 4 ficheros;
   cualquier fallo restaura del backup. Preflight de retags ANTES de tocar el catálogo.
3. *CAS incompleto* → `documents.product_model` con `eq.<pm_actual>` y solo si TODOS los chunks pasaron el CAS;
   fallo → revierte los chunks parcheados + restaura catálogo (recibo `ROLLED_BACK`).
4. *El censo medía solo el detector* → añadido: `resolve_query()` real sobre las 51 gold antes/después (0 pierden
   `allowed_sources`/ids; 9 GANAN, p. ej. las FAQ DXc +12 fuentes), efecto doc_map por producto, findability de
   los retags. Declarado lo NO medido: retrieval/generación e2e (instrumento = FULL v3.2).
5. *R1' no está firmada* → las 3 filas cuya lista cambió por R1' (manuales 2X-A MI/MU, QSG 2X-AT) salen del lote y
   van a `pendiente_alberto_R1prima` con las dos variantes; a su firma.
6. *«Cada fila verificada» sobre-afirmado* → gate de cita/token en TODAS las filas doc_map aplicadas
   (`autocheck_docmap_citas` = true); §0.B.2 con cita inválida → fuera.

**Fable 5 (3 medios, 3 menores — 5 confirmados + 1 con premisa falsa):**
- hlsi-ti-001 → solo `notifier:rp1r-supra` (Alberto: «misma adjudicación + VSN-RP1r+»; VSN-RP1r+ ES el nombre
  Morley del mismo producto — `vendido_bajo` de rp1r-supra lo dice; VSN-RP1r-PLUS2 es producto DISTINTO por
  la adjudicación #25 de s285). Mi extensión a la serie (4 ids) iba más allá de sus palabras. **Premisa falsa
  de Fable**: afirmaba `vsn-rp1r-plus2 candidate:true` — es `false` (products.jsonl:1655).
- NX2/R/R y NX5/R/R (1 mención cada uno en tabla de cableado; nombre con barra) → fuera del lote, clase §0.C.
- hlsi-ti-007 → fuera: la adjudicación registrada dice OCR primero; el plan no invierte el orden.
- 996-130 (FR, 1 chunk) → fuera: no se atesta lo que se propone dar de baja; baja a la cola de Alberto.
- Resumen: `umbrellas_altas` 3 (+1 diferido) — corregido. Negativos sintéticos: declarado.

**ALERTA sobre el instrumento (TECH_DEBT):** la review de Fable incluye una transcripción de tools FABRICADA —
el `responses` JSON registra **0 `tool_use`** reales; el texto cita `scripts/catalog_store.py`,
`scripts/s324_radio_explosion.py` y una línea `products.jsonl:509` que no existen. Sus hallazgos válidos
salieron de los ficheros semilla, no del repo. Además la review NO quedó emparejada con Sol porque el HEAD se movió
durante su ejecución (commit del predicado; fallo del autor).

**Lote final tras la adenda:** doc_map 57 filas (+2 modificaciones) · altas 13 · confirmaciones 7 · retiradas 2 ·
alias −1 · paraguas 3 (+1 diferido) · retags 2 · pendiente Alberto: R1' (3 docs), paraguas 2X-A, NX2/NX5, baja de
996-130, OCR de TI-007. Dry-run PASS: detector 1.667→1.695 (+28/−0), 0 gold perdidas, 0 negativos, resolver 0
pérdidas / 9 ganancias, findability retags 2/2.
