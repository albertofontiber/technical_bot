# s331 — Residuo E1: las 3 preguntas delegadas + atestación TI-007 + baja FR (PROPUESTA para dúo)

**Encargo (Alberto, 20-ago-2026, sesión s331):** las 3 preguntas ⏳ de
`evals/s320_e1_packet_adjudicacion_v2.md` (MADT015_01, MNDT600, MNDT701) pasan a ser decisión mía
(«las 3 preguntas son para ti»); además pide atacar los no-bloqueantes (VSN2-PLUS, OCR TI-007) y
pregunta si queda algo en §1.A. La baja del fragmento FR `996-130` ya la adjudicó él en el packet
(«ALBERTO: baja del corpus.», fila §1.A).

**NADA APLICADO aún.** Este documento es la propuesta que el dúo ataca ANTES de cablear
(Protocolo 3: impacto MEDIO en zona de dolor corpus/retrieval → Sol xhigh + Fable).

---

## D1 — `MADT015_01` (18 chunks, pm `MADT-015`) → pm **`NFS 2-8`** + doc_map `notifier:nfs-2-8`

**Pregunta original de Alberto:** «¿puede estar asociado a los modelos de la serie FS, i.e. FS2-1,
FS2-2 y FS2-4, en base al esquema de bornes?»

**Evidencia leída de la FUENTE (PDF del bucket, 4 págs):**
- `MADT015_01` es la guía rápida de instalación (MA-DT-015_01_C, 997-502, 27/07/04, NOTIFIER
  ESPAÑA) de una central convencional de **8 zonas** (leds «Zona 1..8»), 2 salidas de sirena
  supervisadas 4K7, 2 entradas digitales (Cambio clase I/P1, Modo Retardo I/P2), EFL resistencia
  4k7 / condensador 0,47µF con cantidades **«(x2, x4, x8)»** (= variantes de 2/4/8 zonas),
  retardos principal/secundario, coincidencia 1-2;3-4;5-6;7-8. No imprime ningún modelo comercial.
- Su hermana `MADT015_03` (997-522, 20/07/05) se titula **«Anexo al manual de instalación de la
  central NFS 2-8, ref.: MI-DT-015»** y su árbol de configuración de Nivel 3 (pág. 2) es
  **idéntico** al de la guía rápida `_01` (mismos menús General/Zonas/Salidas/Entradas
  digitales/Retardos, mismas opciones, mismos leds).
- `MADT015_02` (otra hermana) es del **NFS8REL**; doc_map hoy: `MADT015_02 → notifier:nfs8rel`,
  `MADT015_03 → notifier:nfs-2-8`. `MADT015_01` es la ÚNICA de la familia MA-DT-015 sin mapa.
- Las gemelas `needs_review` del portal (`MADT015_01_1`, `MADT015_01_2`) ya llegan con pm
  `NFS2-8`.
- El catálogo ya enlaza la referencia del manual: alias **«MI-DT-015» → `notifier:nfs-2-8`**
  (provenance s83:MADT015_03), junto a «997-522», «la NFS 2-8», «MA-DT-015_03».
- **Serie FS2: no existe** ni en corpus ni en catálogo: 0 documentos con pm `*FS2*` (solo la
  familia MADT015/MIDT015 con pm NFS2-8), 0 productos `fs2-*` en `products.jsonl` (solo
  `unresolved:fs20x/fs24x`, que son los detectores de llama Fire Sentry, otra cosa). El esquema de
  bornes de `_01` (zonas con EFL 4k7/0,47µF, 2 sirenas supervisadas, TB8) es el de la NFS 2-8
  documentada por `_03`.

**Propuesta:** retag `documents.pm` + `chunks_v2.pm` de `MADT015_01`: `MADT-015` → **`NFS 2-8`**
(misma grafía que la hermana `_03`); alta de doc_map `MADT015_01 → notifier:nfs-2-8` con
`provenance: "s331 adjudicado (delegado por Alberto): anexo hermano MADT015_03 nombra el manual
MI-DT-015 de la NFS 2-8 + árbol de config idéntico"`. **Gap declarado:** el contenido de `_01` no
imprime «NFS 2-8» (por eso su pm era el artefacto), así que la cita de esta fila de doc_map es
DOCUMENTAL (hermana `_03` verbatim), no full-text del propio doc — la clase ya usada en s324c para
`MADT731_06 → laserstar-hssd-2` (adjudicación con URL). Si el dúo lo tumba, fallback: retag pm
solo, sin fila de doc_map.

**Respuesta a la hipótesis FS2:** no la sostiene ninguna evidencia interna; si algún día entra un
manual FS2-x al corpus, será una alta nueva con su propia cita (R3: OEM/lookalike no amplía nada).

## D2 — `MNDT600` (16 chunks, pm `MNDT-600`) → pm **`unknown`** (sin doc_map)

**Pregunta original:** «aplica a los detectores de gas smart (sensitron)… ¿puedes revisar en el
corpus si tenemos el documento [Smart3 GD3 / SMART3 GD2]?»

**Evidencia leída de la FUENTE (PDF, 12 págs):** «Notas generales para la calibración,
mantenimiento e instalación de los detectores de GAS» (MN-DT-600_A, 06-abr-2011, HLSI). Contenido
GENÉRICO (ubicación de sensores, EN54-tipo guías, registro de instalación, reglas de calibración).
Los únicos tokens de modelo del texto: sensores «Combustible S1096/ 2096… S1097.2097…» (células
Sensitron, tabla §4.4.3). Ni «SMART», ni «GD2», ni «GD3» aparecen en el TEXTO (las fotos de
portada sí son detectores SMART de Sensitron — pero foto = ficha, no cita).

**Censo del corpus (chunks_v2, docs con pm SMART\*):** ningún doc contiene `SMART3G-D2`/`GD2`.
La familia SMART sí está: SMART 1 (MNDT607), SMART 2 (MNDT615/618, MT251), SMART TWIN (MNDT606),
SMART 3 (MNDT625/626), SMART3G (MNDT646 tóxicos, MTEX 4446 explosivos, MTEX 4749 tóxicos).
En catálogo: `notifier:smart3g-d3` y `notifier:smart3g-c3` (no-candidate, provenance
`s83:SMART 3G ZONA 2 MTEX4805__SP Rev 3`), `smart3g-d`/`smart-3g`/`smart-3-cc`/`smart-3-cd`/
`smart-3-cc-cd`/`smart-1`/`smart4` (candidates), `sensitron:smart-2` (no-candidate).

**Propuesta:** retag pm `MNDT-600` → **`unknown`** (misma clase que la FAQ
`compatibilidad-entre-equipos-notifier-y-morley`, §0.E MANTENER-unknown: doc genérico servible por
retrieval, sin producto citable). SIN doc_map (R4: jamás por ficha; el doc no nombra ni un
modelo SMART). **Respuesta al sub-encargo:** el doc del «SMART3 GD2» NO está en el corpus con
ninguna grafía; el GD3 = `SMART3G-D3` sí está atestado por el doc MTEX4805 (Zona 2). **Opción
declarada, NO incluida:** un paraguas «SMART 3» con los miembros del catálogo es una decisión
aparte (mezcla candidates pendientes de QA y no hace falta para limpiar este artefacto); si
Alberto lo quiere, va con su propio censo/gate.

## D3 — `MNDT701` (6 chunks, pm `MNDT-701`) → pm **`unknown`** (doc_map DIFERIDO al ítem 3)

**Evidencia leída de la FUENTE (PDF, 5 págs):** «Guía de usuario — Software del detector de llamas
Triple IR» (SPECTRONIX, MN-DT-701, 13-oct-1997). La foto de portada es un **SharpEye™ IR³**; el
texto habla de «detectores IR3» (hasta 64 en bus RS-485) pero NO imprime ningún modelo comercial
ni un nombre del software (a diferencia del TG, que sí tiene nombre y entró como producto-software
en s324b).

**Propuesta:** retag pm `MNDT-701` → **`unknown`**. El destino bueno (doc_map a la familia
SharpEye 20/20) está BLOQUEADO a propósito: los ids no existen aún — `20/20MI` y `20/20R` están en
tu lista pendiente de «nombres reales con barra» (ítem 3 del bloque 🟢; la grafía verbatim del
corpus es «S20/20MI», MNDT696, coherente con las altas Spectrex `S40/40x` de s324b que firmaste
con la S). Cuando firmes el ítem 3, la atestación de MNDT701 va en ese lote con su mecánica
(paraguas/familia «IR3»-«Triple IR» si procede, con su gate léxico — «IR3» como término tiene
riesgo de disparo bajo pero se mide entonces, no se presupone).

## D4 — TI-007: alinear chunks (pm `TI-007` → **`VSN-4REL`**) + doc_map `notifier:vsn-4rel`

**Estado real verificado HOY:** la re-ingesta del 17-ago (recibo
`s324d_reingesta_ti007_aplicar_20260817T093621Z.json`, TECH_DEBT #87: la raíz NO era OCR) dejó el
doc con 2 chunks (2.520 + 1.080 chars) y `documents.pm` = `VSN-4REL`, pero los CHUNKS nuevos
llevan pm **`TI-007`** (artefacto re-introducido por el parse). El contenido ahora SÍ nombra el
modelo: cita full-text **«Instalación del módulo VSN-4REL»** (+ 7 menciones más).

**Propuesta:** (a) retag SOLO-CHUNKS `chunks_v2.pm` `TI-007` → `VSN-4REL` en los 2 chunks
(documents.pm ya está bien — CAS por capa, el writer lo contempla); (b) alta de doc_map
`HLSI-TI-007_VSN-4REL → notifier:vsn-4rel` con la cita de arriba (R4 limpio) — ejecuta la
adjudicación que Alberto dejó registrada en #87/§1.A («modelo VSN-4REL; atestar DESPUÉS de la
re-ingesta»). Cierra la fila ⏳ de §1.A y el flanco TI-007 del punto 6 del bloque 🟢.

## D5 — Baja de corpus `996-130-000-3 Manuel d'utilisation ZX_hlsi` (1 chunk, pm `ZX`)

**Adjudicación de Alberto ya escrita en el packet** (fila §1.A: «ALBERTO: baja del corpus.»).
Fragmento FR de 1 chunk (páginas finales de notas y contacto del manual de usuario ZX). Mecánica
= `s324_retirar_docs.py`: `documents.status='retired'` + nota, chunks intactos (reversible),
guardas por fila (existe+active, nº chunks censado = 1, sin entradas de doc_map que se pierdan —
verificado: no tiene). **Declarado:** NO hay hermano ES del mismo manual 996-130 en el corpus
(las ZX ES presentes son FAQs y docs de otra generación); la baja descansa en la adjudicación,
clase `adjudicacion` como MA-DT-1160, no en la regla fragmento-con-hermano.

## Lo que NO se escribe hoy (dossier aparte)

**VSN2-PLUS / «Plus2»** → `evals/s331_vsn2plus_censo_v1.md`: censo de 18 grafías en ~20 docs
Supra/UCIP activos (2Plus ×40, Vision Plus2 ×12, ESS-2Plus ×9, VSN-2Plus ×7, VSN2plus ×6,
VSN2-PLUS ×4…). Lectura: la generación Supra existe en TRES pieles de marca (NFS Supra ↔ Vision
«2Plus»/VSN-2Plus ↔ ESS-2Plus) con variantes de zonas (VSN12-2Plus) y repetidor (VSNRP1r-2Plus).
Es la clase **rebrand/OEM entre marcas** + los homónimos cross-bloque que E1b ya declara
(morley↔unresolved ESS*/NFS*-Supra): se adjudica con Alberto en la sentada E1b, NO en seco. Cero
escrituras aquí.

## Mecánica del writer (s331, misma puerta que s324)

`scripts/s331_residuo_writer.py`, plan `evals/s331_residuo_plan_v1.json`:
- **freeze** (sha de los 4 .jsonl del catálogo + snapshot chunk-a-chunk de los pm a tocar + pm
  actual de documents + status del doc a retirar); `--aplicar` exige dry-run PASS del MISMO plan y
  freeze idéntico recalculado.
- **retags con CAS**: chunk a chunk `eq.product_model=<pm_actual>`; `documents.pm` con
  `eq.<pm_actual>` y solo si TODOS los chunks pasaron; rollback de lo parcheado ante fallo.
- **doc_map por la puerta** `catalog_store.write_jsonl` (validador del conjunto) sobre COPIA en
  dry-run; diff del detector del resolver ANTES/DESPUÉS (esperado: **0 términos entran/salen** —
  ni products ni aliases ni umbrellas cambian) + `resolve_query` sobre las 51 gold (esperado: 0
  pérdidas; ganancias solo de fuentes para `nfs-2-8`/`vsn-4rel`).
- **findability de retags**: para pm→modelo real (NFS 2-8, VSN-4REL) exige que el pm nuevo case
  con ≥1 entry primaria del doc_map del doc (las filas nuevas de este mismo plan cuentan: se
  evalúa sobre el catálogo DESPUÉS); para pm→`unknown` la findability es N/A-por-diseño y se
  declara en el recibo (la clase §0.E MANTENER-unknown no tiene doc_map).
- **baja** con las guardas de `s324_retirar_docs.py`; reversible.
- recibo `evals/s331_residuo_{dry-run,aplicar}_<utc>.json` con instrucciones de reversión;
  verificación posterior en el mismo turno (re-lectura de pm/status/doc_map + suite).

## Gaps/riesgos declarados (de entrada)

1. La fila de doc_map de D1 no tiene cita full-text del PROPIO doc (evidencia documental hermana).
   Fallback listo si el dúo la tumba: pm-only.
2. `unknown` en D2/D3 renuncia a vínculo de producto HOY; el vínculo bueno queda nombrado y
   diferido (paraguas SMART 3 aparte; ítem 3 para SharpEye). Riesgo aceptado: menor findability
   por producto para esos 2 docs genéricos; su retrieval es por contenido.
3. La baja D5 no tiene hermano ES: pérdida de las ~líneas FR finales del manual ZX para retrieval
   FR (política de idiomas ya descarta FR en ingesta nueva; DEC-066).
4. Ninguna medición de eval se toca; esto no es un lever medido (no aplica freeze-contract de
   eval). El radio de explosión esperado en el detector es CERO términos; si el dry-run muestra
   otra cosa, se PARA.
