# Packet de adquisición documental — s294

**Fecha:** 6 ago 2026 · **Origen:** barrido `evals/s294_citation_gap_v1.json` (git `67bf46f`; 25.088 chunks, 1.012 `source_file`, 44 códigos candidatos, 77 citas) + 4 lotes de adjudicación humana/agente + investigación de vías de descarga.

**Resultado de cabecera:** de los **44 candidatos** del barrido, **7 son documentos realmente ausentes** (16 %) y **37 son falsos positivos**. Uno más — **`997-412`** — es un hueco REAL que el barrido **no vio** (falso negativo del instrumento). Total accionable: **8 documentos**, de los cuales **3 valen de verdad** y **1 no es descargable**.

> **Aviso de método (Protocolo 1).** Todo lo marcado ✅ está verificado en esta sesión (PDF abierto, HTTP con código de estado, o fichero del repo citado). Todo lo marcado ⚠️ es inferencia declarada. **No hay ninguna URL inventada**: solo aparecen rutas que devolvieron 200 en la investigación.

---

## 0. Lo que me pidieron poner arriba del todo: la «Guía Avanzada de Configuración» de la CAD-171

**Me pidieron encabezar el packet con este documento. Lo he verificado antes de escribirlo y el resultado es el contrario del esperado: NO es un hueco de corpus. Ya lo tenemos, y además ya está mapeado a la CAD-171.**

Qué dice el corpus (verificado, PDF abierto):
- `Manual_CAD-171-MI-716-es.pdf` **p.25**: «Si desea información detallada de utilización y configuración de la central consulte la **Guía Avanzada de Configuración**». Y **p.32**: «Consulte la **Guía de Configuración Avanzada** para más detalles». Cita **por nombre, sin código** → invisible para el barrido (punto ciego correctamente declarado en `evals/s294_cad171_menu_avanzado_v1.md`).
- El documento al que remite es **`CAD-250_Manual-Configuracion-MC-380-es-2026-c.pdf`**, cuya **portada** dice «GUIA DE CONFIGURACION — CENTRALES VESTA» y cuyo **control de revisiones p.2** dice literalmente: «**c · Adaptación para CAD-171 y CAD-201 · 23/04/2026**». Menciona CAD-171 en 5 páginas (2, 6, 10, 11, 26).
- **Y contiene exactamente lo que el bot falló en responder.** §5.4, **p.29**: «**AJUSTES (Menú principal) > AVANZADO (Submenú)** … Dispone de 3 pestañas de configuración en este nivel, SISTEMA, OTROS y REINICIAR.»
- **Está vivo en el corpus**: `CAD-250_Manual-Configuracion-MC-380-es-2026-c` aparece en `C:\dev\technical_bot\evals\s174_prerequisite_corpus_census_v1.json` y en `C:\dev\technical_bot\data\catalog\doc_map.jsonl` con **`detnov:cad-171` como `role: primary`**.

**Consecuencia para el DEC-176 (primer fallo orgánico del bot).** El diagnóstico de fallo de SELECCIÓN («responde con el elemento vecino»: dio `AJUSTES > GENERAL` teniendo `AVANZADO` delante) **se refuerza, no se ablanda**: la ruta correcta no solo estaba en la evidencia servida del MI-716, es que además el corpus tiene un manual entero que la documenta explícitamente y que está correctamente asociado a la CAD-171. **Este caso no se arregla comprando nada.** Se arregla en retrieval/síntesis, y el gold candidato de la sentada B2 sigue siendo la acción correcta (lo firma Alberto, DEC-025).

**Incertidumbre residual honesta ⚠️:** el título literal citado («Guía **Avanzada** de Configuración») no coincide palabra por palabra con la portada del MC-380 («Guía de Configuración — Centrales Vesta»). No puedo demostrar al 100 % que Detnov no publique además un documento distinto con ese título exacto. Dos cosas lo hacen improbable: (1) el contenido pedido está en el MC-380; (2) según DEC-030, la página de producto de la CAD-171 en `detnov.com` (WordPress, enlaces PDF directos, sin auth) enlaza **exactamente los 5 PDFs que ya tenemos**. **Coste de cerrarlo del todo: un correo al comercial de Detnov preguntando si existe un documento con ese título para la serie Vesta.** No lo pondría por delante de nada de la tabla de abajo.

---

## 1. Tabla priorizada — documentos REALES a conseguir

**Criterio de prioridad aplicado:** (a) manuales de **programación/configuración** de familias que ya tenemos a medias pesan más — el técnico pregunta por configuración; (b) **más citas = más veces que nuestro propio corpus remite fuera**; (c) penaliza la redundancia (si el contenido ya está servido por otro doc) y la no-adquiribilidad.

**Columna «citas»:** número del ranking del barrido, salvo donde se indica «(verificadas)» = recuento propio por ILIKE sobre `chunks_v2`.

| # | Prio | Código | Título | Fabricante | Familia | Citas | Tipo | Por qué importa |
|---|---|---|---|---|---|---|---|---|
| 1 | **P1** | **997-340-005** | Manual de Usuario del software de **Carga/Descarga (Upload/Download)** ID1000 | Notifier España | Serie ID1000 / Serie 1000 | 1 (citado por **2 documentos independientes**) | **Programación** (software de PC) | Es **la programación por PC** de una familia de la que ya tenemos los otros tres manuales (`MPDT212` programación, `MIDT212` instalación, `MFDT212` funcionamiento). Cubre la carga/descarga de configuración y los procedimientos de actualización/compatibilidad de firmware: **contenido que ningún documento nuestro aporta**. Es el caso de libro del criterio «familia a medias + programación» |
| 2 | **P1** | **997-415** | «Instrucciones de actualización — panel de un solo lazo» (ID50 / ID60 / ZX50) | Notifier + rebrand **Morley-IAS** (mismo hardware OEM) | ID50 / ID60 / ZX50 | **6** — el 2.º código más citado de todo el barrido; citado por **3 manuales y 2 marcas** (`MIDT155`, `MIDT156`, `MIE-MI-300rv02`) | Instalación / mantenimiento (firmware) | Es el **único procedimiento** que el corpus remite fuera repetidamente en la familia de 1 lazo. Hoy el bot puede responder al puente J4 (está en `MIDT155`/`MIDT156` p.30) pero **no al procedimiento de actualización**. Un mismo PDF cubre dos marcas → doble rendimiento por descarga |
| 3 | **P1** | **997-412** | Manual de instalación, puesta en marcha, configuración y funcionamiento del **Sinóptico IDR** | Notifier | Accesorio de ID50 / ID60 | **4 (verificadas)** — `MIDT155` p.21/p.82, `MIDT156` p.22/p.105 | Instalación + **configuración** | ⚠️ **NO estaba en la lista del barrido.** Es un **falso negativo del instrumento** (`MAX_GAP=100` + `break`: en toda cita doble se pierde el segundo código). Documento real, ausente, con 4 citas y con contenido de configuración. Justo la clase que el criterio prioriza |
| 4 | **P2** | **997-677-000** | Documentación de usuario del repetidor **PRL-IDR6A** | Notifier | **Pearl** (PRL-D-1 / D-2) | 1 | Accesorio (repetidor) | Único hueco funcional real del bloque Pearl: la cita pide el **ajuste del puente JP3** en la instalación. Cobertura hoy solo **indirecta** vía `MNDT200` (IDR-6A) y `MCDT191`, **sin equivalencia probada** entre `PRL-IDR6A` e `IDR-6A` ⚠️ |
| 5 | **P2** | **996-137** | Guía de instalación de la **tarjeta de ampliación (LEDs de zona)** serie ZXSe | Morley-IAS (Honeywell Life Safety Iberia) | ZXSe (ZX1Se/2Se/5Se/10Se) | 1 | Instalación (accesorio) | Único hueco genuino del lote Morley. En el corpus, `996-1xx` es namespace **de documentos** HLSI (p.ej. `996-130-000-3`), mientras las tarjetas ZXSe usan `795-xxx`/`709-xxx`/`797-xxx` → lo más probable es que sea la guía y no la pieza. ⚠️ **No descartado al 100 %** que `996-137` sea la referencia de la tarjeta |
| 6 | **P3** | **997-449-000** | Instrucciones del módulo de enlace de red **NGM ISO-IDRED/W** | Notifier | ID²net (ID3000) | 1 | Accesorio (hoja de instrucciones) | Ausente, **pero funcionalmente redundante**: la necesidad que motiva la cita (ajuste de puentes) ya está servida por `MADT190_01`, donde ISO-IDRED/W es `covered_model` **primary** con apéndice propio y tablas de puentes literales (p.15/19/23). Solo por completitud documental |
| 7 | **P3** | **S00-368-000** | Especificaciones del **aislador de cortocircuito** | Notifier (Honeywell) | Pulsadores M700KAC / M700KACI | 1 | Especificación técnica | Real, pero la propia fuente dice «**disponible previa solicitud**» → **no descargable**. Solo vía comercial, y con poco retorno |
| 8 | **P3 / NO-GO** | **74-06200-005** (el barrido lo emitió truncado como `06200-005`) | Manual **NOTI-FIRE 911A / 911AC** | Notifier US (legacy) | RP-1001 / RP-1002E / AFP-200 | 2 | Instalación (comunicador) | Producto **US de los años 90**, citado solo como equipo de terceros por manuales legacy. El 911A/911AC solo aparece como `mentioned_not_covered`. **No lo perseguiría.** Además, buscar el string `06200-005` no encontrará nada — el código real lleva el prefijo `74-` |

### Zona gris — 3 códigos que NO son huecos probados pero tampoco cierre limpio

No los pongo en la tabla de adquisición porque el contenido ya está cubierto; los dejo anotados para que nadie los reabra sin leer esto.

| Código | Situación | Recomendación |
|---|---|---|
| **997-320-003** / **997-320-001** | Manual de **programación** / **funcionamiento** «Serie 1000». El contenido lo cubren `MPDT212` (997-340-003 v8, 1999) y `MFDT212` (997-340-001 v8, 1999) — el propio `MADT212` usa «Serie ID1000» y «Serie 1000» **para el mismo panel en la misma portada**. ⚠️ **Gap declarado:** no se pudo determinar si `997-320-00x` es una **edición anterior** o una **variante de otro idioma/mercado** (el sufijo «/013», «/011» sugiere par de numeración) | Prioridad **baja**. Si aparecen gratis en un barrido, se bajan y se comparan; no se piden |
| **997-187** | «Manual de Instalación y Puesta en Marcha» de la Serie 800/CFP-800. En corpus está `MIDT020` con **título literal idéntico y misma familia**, pero **su portada NO imprime `997-187`** → equivalencia por título+familia, no por código ⚠️. Podría ser una edición anterior | Prioridad **nula/baja** |

---

## 2. Falsos positivos descartados — no volver a perseguirlos

**37 códigos.** Motivo en una línea cada uno. La causa dominante (verificada en `C:\dev\technical_bot\scripts\s294_citation_gap.py`, líneas ~66 `norm()` y ~88-128 `known_norm`): **el barrido casa el código citado contra el NOMBRE DE FICHERO**, y Honeywell/Notifier España guardan los ficheros con su código editorial (`MPDT212`, `MIDT155`) imprimiendo el número `997-xxx` **solo en la portada**.

### Presentes en el corpus bajo otro nombre de fichero (18)

| Código | Motivo (una línea) |
|---|---|
| **997-340-003** (11 citas — **el nº1 del ranking era ruido**) | Es `MPDT212.pdf`, portada «Ref.: 997-340-003; Versión: 8» — ya ingestado |
| 997-340-000 | Es `MIDT212.pdf`, portada «Ref.: 997-340-000; Versión: 8» |
| 997-340-001 | Es `MFDT212.pdf`, portada «Ref.: 997-340-001; Versión: 8» |
| 997-263 | Es `MIDT155` («Doc. 997-263») **y** su revisión posterior `MIDT156` («Doc. 997-263 Rev. 10») |
| 997-263-XXX | **Duplicado de 997-263**: el propio corpus explica que «XXX es el código específico para cada país» |
| 997-264 | Es `MFDT155` («Doc. 997-264») + `MFDT156` («Issue 9») — ojo: `997-264-001` es otro doc (NF30/NF50 FR) y también lo tenemos |
| 997-405 | Es `MCDT155` + `MCDT156_A`; gemelo Morley `MIE-MC-300` lo lleva como alias literal |
| 997-411 | Es `MNDT200` («Doc. 997-411_7», repetidores IDR-2P/-2A/-6A) |
| 997-198 | Es `MNDT1025` («doc. 997-198», Aplicaciones del VIEW™) |
| 997-670-00X | Manual de funcionamiento Pearl: `00X` es **comodín de idioma**; tenemos `997-670-005-3` (ES) y `-007-3` (PT) |
| 997-670-000 | Misma doc, edición máster/EN (`000`=EN, `005`=ES) |
| 997-669-000 | Instalación Pearl: tenemos `997-669-005-3` — que es **el propio documento citante** |
| 997-671-000 | Configuración Pearl: tenemos `997-671-005-3` (ES) y `-007-3` (PT) |
| 4188-1125-EN | Guía de licenciamiento INSPIRE/CLSS: tenemos la edición **ES** del mismo número |
| 996-202-005 | Es `DXc_Manual de usuario.pdf` — su colofón dice `doc.996-202-005-2 \| Rev.03 \| 08/16` |
| 996-220-205 | Es `DXc_Manual variaciones de mercado.pdf` — colofón `996-220-205-1 \| Rev 02` |
| 997-509-000 | Es `MIDT1500_A.pdf` (IDP-LB1) — pie «Doc. 997-509-000-1 issue 1» |
| MIE-MP-300 | Es `MIE-MC-300.pdf` — la extracción s83 registra `MIE-MP-300` y `997-405` como **alias del propio manual** |

### Renumeración de editor Notifier España → Honeywell Life Safety Iberia (2)

| Código | Motivo |
|---|---|
| MN-DT-601 | Es `HLSI-MN-601.pdf` (pauta de calibración KIT-GAS). Renumerado sistemático `MN-DT-NNN` → `HLSI-MN-NNN` |
| MN-DT-627 | Es `HLSI-MN-627.pdf` («Manual de usuario del KIT-GAS», HLSI-MN-627_B / MT1195 Rev.3) |

### No son documentos: referencias de **pieza**, producto o rango (10)

| Código | Motivo |
|---|---|
| 795-080 | Pieza: cable de comunicaciones serie MIAS |
| 795-102 | Pieza: placa de LEDs de 40 zonas |
| 795-104 | Pieza: kit de recambio puerta con display y teclado DXc1/2/4 |
| 795-106 | Pieza: módulo de fuente de alimentación DXc1 |
| 795-124 | Pieza: placa de LEDs de 80 zonas |
| 004-100 | Pieza: panel de rack para la fuente de alimentación (en serie con 004-098 y 004-111) |
| 124-292 | Pieza/producto: alias de pedido de la placa `LIB3000` |
| BAC-NID3000 | **Producto** (`IBOX-BAC-NID3000`, pasarela OEM Intesis) + código truncado; su manual ya está en corpus |
| 001-127 | **Rango de direcciones** de lazo (1–127), no un código de documento |
| 001-240 | **Rango de direcciones de nodo** Noti·Fire·Net (1–240) |

> ⚠️ Regla general que sale de aquí: en Morley/Notifier-Iberia los prefijos `795-`, `797-`, `709-`, `020-`, `082-`, `002-`, `004-`, `124-`, `236-` son **hardware**; `996-`, `997-`, `MIE-M*-`, `MN-DT-`, `HLSI-` son **documentos**.

### Erratas de imprenta y contaminación de encabezado/pie (5)

| Código | Motivo |
|---|---|
| 997-300-003 | **Errata impresa** en `MFDT212` de `997-340-003` (el mismo PDF comete la errata gemela `997-340-0003`) |
| 997-679-00X | **Errata `5`→`7` del fabricante**: la guía existe en corpus y lleva impreso `997-659-005-1`; el mismo manual la cita 2× como `997-659` |
| PK-ID3000 | **Nombre de producto software** + **encabezado corriente** de `MCDT191` (aparece **128 veces**, una por página); el doc real es `997-291` y ya lo tenemos |
| 300-020 | **Pie de página del propio documento citante** (`SS-300-020 \| pág \| I56-3536-003R`), no una remisión externa |
| — | *(agrupado)* |

### Deuda de instrumento derivada (no bloquea el packet, pero conviene arreglarla antes de re-correr el barrido)

Cuatro bugs concretos, todos verificados en `C:\dev\technical_bot\scripts\s294_citation_gap.py`:
1. **`known` se construye solo con `source_file`** → no ve el código impreso en portada. Ya existe la materia prima para el índice `ref_interna → source_file`: `evals/s83_full_extraction_merged.jsonl` (campos `notes`/`aliases`). **Solo esto habría matado ~18 de los 37 FP.**
2. **Comodín de idioma no normalizado** (línea ~67 y ~125): `997-670-00X` no está contenido en `997-670-005-3_*`. Causó 5 de 6 FP del lote Pearl.
3. **Prefijo truncado** (`RX_DOCCODE`, líneas ~47-49): emite `06200-005` en vez de `74-06200-005`.
4. **`MAX_GAP=100` + `break`** (líneas ~117-118): **pierde el segundo documento de toda cita doble** → así se perdió `997-412`, que es P1 en esta lista.
5. Filtro barato adicional: **descartar el código que aparece ≫N veces en el MISMO `source_file`** (encabezado/pie corriente) — mata `PK-ID3000` en 3 líneas.

---

## 3. Cómo conseguirlos

### 3.0 Descarte previo (para que nadie pierda un día)

❌ **`firesecurityproducts.com` NO sirve para NADA de esta lista.** Verificado en vivo contra su API PIM: las marcas del portal son **Aritech · Edwards · EMS · IFAM · Kidde · Kilsen · Ziton** — cero Honeywell, cero Notifier, cero Morley. Son grupos distintos (Carrier/Kidde Global Solutions vs Honeywell). El runbook `docs/CORPUS_FIRESECURITYPRODUCTS.md` es **inaplicable** aquí.
> *Fix menor pendiente en ese runbook*: §3 dice `page=<n>` empezando en 0, pero **`page=0` devuelve HTTP 400**; la paginación empieza en **`page=1`**. Y convendría añadirle una nota de alcance: «este método NO cubre Honeywell/Notifier/Morley».

---

### 3.1 VÍA A — Portal público, **sin registro** (empezar por aquí: coste cero, hoy) ✅

**El hallazgo operativo:** en `notifier.es` y `morley-ias.es` **el índice está cerrado pero los PDF están abiertos**. Verificado con descargas reales (HTTP 200 + `content-type: application/pdf` + cabecera `%PDF-`), sin cookie ni login.

**Carpetas verificadas:**

| Marca | Carpeta | Contenido |
|---|---|---|
| Notifier | `https://www.notifier.es/documentacion/notifier/manuales/` | Manuales vigentes |
| Notifier | `https://www.notifier.es/documentacion/notifier/manualesobs/` | Manuales obsoletos (legacy: AM-6000, AFP-200E, ID200…) |
| Notifier | `https://www.notifier.es/documentacion/notifier/hojastec/` | Hojas de características |
| Morley | `https://www.morley-ias.es/documentacion/morley/manuales/` | Manuales vigentes |
| Morley | `https://www.morley-ias.es/documentacion/morley/manualesdes/` | ⚠️ «des» = descatalogados (**inferencia, no confirmado**) |

**Regla de nombre (validada con >10 pruebas HTTP):** código **sin guiones** + `.pdf` → `MI-DT-190` ⇒ `MIDT190.pdf`. **Con excepciones reales**: hay ficheros con guiones (`MIE-MI-600.pdf`), con sufijo de revisión (`MIE-MU-520rv02.pdf`, `MIE-MP-530rv001.pdf`) y algún nombre totalmente distinto (`MN-DT-951` se sirve como `TG-Honeywell_Usuario.pdf`). **Adivinar la URL falla a menudo** (`MIE-MI-530.pdf` → 404 en las tres carpetas).

**Dato clave para nuestros P1/P2:** la familia **Pearl SÍ lleva el número 997 dentro del nombre de fichero** — verificado: `997-671-005-3_Configuration_ES.pdf` devuelve **200, 2.617.586 B**. Eso hace que **`997-677`** (ítem 4) sea el candidato con más probabilidad de resolverse por esta vía.

**Pasos verificados:**
1. Para cada código, **resolver el nombre de fichero exacto con un buscador acotado al dominio** (`site:notifier.es <código o modelo> filetype:pdf`, ídem `morley-ias.es`). Verificado que funciona: una consulta acotada devolvió de golpe MN-DT-250/260/120/150/060/110/530/516, MI-DT-156, MIDT155, MIDT170, MIDT190, MIE-MI-230, MIE-MP-210, MIE-MP-530rv001, MIE-MI-600.
2. Descargar por URL directa. Si da 404 en `/manuales/`, **probar la otra carpeta** (`/manualesobs/` o `/manualesdes/`) — los tres P1 son de producto **legacy**, así que la carpeta de obsoletos es la apuesta más probable.
3. Probar variantes de nombre: con y sin guiones, con sufijo `rvNN`, con sufijo de idioma/edición.
4. **No intentar listar el directorio**: devuelve **403**. **No hay `sitemap.xml`** (404 en ambos dominios). `robots.txt` **no** bloquea `/documentacion/`.
5. Validar cada descarga (`%PDF` en cabecera, tamaño > 1 KB) y guardar manifiesto de procedencia — es lo que hace ya el pipeline de scraping del proyecto.
6. **Rate-limit**: `sleep` de 1-2 s entre peticiones. El 403 en el listado indica que no quieren crawling agresivo.

**Bonus del mismo barrido (público, con índice navegable, sin login):**
- Notifier — Catálogos: `https://www.notifier.es/index.php/documentos/catalogos` (18 PDF enlazados en el HTML).
- Notifier — Hojas Técnicas: `https://www.notifier.es/index.php/documentos/hojas-tecnicas` (índice alfabético `/alphaindex/{a..z}`; descarga vía endpoint Joomla `?task=callelement&format=raw&…&method=download`, verificada 200 `application/pdf`).
- Morley — Hojas Técnicas: `https://www.morley-ias.es/index.php/documentos/hojas-tecnicas` (**64 hojas únicas** enumerables por alphaindex).
- Honeywell EDAM (CDN público, sin login): `https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/…` — rutas estructuradas por marca (`morley-ias-uk`, `morley-ias-es`, `notifier-it`…). Buen candidato a recolección sistemática.
- Producto **actual** Morley (no legacy, pero gratis y completo): `https://buildings.honeywell.com/gb/en/lp/morleytech` (98 PDF) y `https://buildings.honeywell.com/gb/en/lp/morleymaxtech` (50 PDF).

⚠️ **Dos caveats honestos sobre esta vía.** (1) **Licencia**: que un PDF sea accesible no equivale a licencia de redistribución. Para uso interno del bot es un tema; publicar el corpus sería otro. **No he revisado los términos legales de `notifier.es`/`morley-ias.es`** — si el corpus va a salir de Fontiber, hay que mirarlo. (2) **Fragilidad**: no sé si que los manuales sean públicos es intencional o un descuido de configuración; puede cerrarse en cualquier momento. Razón práctica para hacer la Vía B **en paralelo**, no después.

---

### 3.2 VÍA B — Área de partner / registro (esto es lo que **de verdad** falta: el ÍNDICE) 🔐

**El cuello de botella no es el acceso, es la descubribilidad.** Los ficheros están abiertos; lo que no tenemos es la lista de qué existe. Por eso el registro merece la pena **aunque la Vía A funcione**.

**Estado verificado del gate:**
- `https://www.notifier.es/index.php/documentos/manuales` → HTTP 200 pero `<title>` = **«CB Login»**; la subcategoría redirige a `<title>` = **«Acceso Clientes»** con **0 enlaces de descarga**. Contraste de control: la misma ruta para hojas técnicas devuelve contenido real. Y **«Manuales» ni siquiera aparece en el menú público** (solo Catálogos, Certificados, Hojas Técnicas, Formularios).
- `https://www.morley-ias.es/index.php/documentos/manuales` → mismo patrón, redirige a **CB Login**.

**Tres altas que pedir (las tres gratuitas, las tres legítimas):**

| Portal | URL de registro (verificada 200) | Qué desbloquea |
|---|---|---|
| **Notifier España** | `https://www.notifier.es/index.php/contactar/registro` | El índice de Manuales `MN-DT-*` / `997-*` → **los P1 nº1 y nº2** |
| **Morley-IAS España** | `https://www.morley-ias.es/index.php/contactos/registro-de-clientes` | El índice de Manuales `MIE-*` |
| **Morley Professional Technical Forum** (UK) | `https://morleyprofessional.co.uk/downloads.php` | **El legacy `996-xxx` completo y organizado** → **el P2 nº5 (996-137)**. Su índice **se puede navegar sin registro** (se ve qué existe); **descargar exige registro** — verificado: la descarga anónima devuelve `text/html` de 26 KB (página de login), no un PDF |

Detalles verificados que ahorran tiempo:
- El registro de `notifier.es` es un **formulario Marketo** (`app-ab25.marketo.com`, form `2616`) = **captación de lead → alta manual por Honeywell**. **No es alta self-service instantánea.**
- `notifierknowledge.com/morley/` es **el mismo sitio** que `morleyprofessional.co.uk` (mismos ficheros byte a byte). No es una segunda fuente.
- En `morleyprofessional` hay un árbol estático que **sí responde anónimo** para rutas exactas ya conocidas (verificado 200 `application/pdf` en `…/downloads/ZX/996-175-000-1_comm.pdf` y `…/downloads/ZX/996-174-000-1.pdf`), **pero no es adivinable**: `996-203-000-2`, `996-148-000-5` y `996-176-000-1` dieron **404**. Sirve si el buscador te da la ruta exacta; no como método de recolección.
- Categorías visibles sin login en ese foro (= el mapa del legacy): Manuals DXc · ZX · Dimension Series · RPS · EVCS · GUI · Ancillaries · Agile Wireless · FAAST/FAAST LT · OSID · Obsolete Dimension Series · Technical Bulletins · firmware y config tools DXc/DX.

⚠️ **Lo que NO pude verificar:** los **criterios de elegibilidad** del alta (¿instalador?, ¿cliente con código?, ¿CIF?) no son públicos en ninguno de los tres; el **plazo de aprobación** tampoco; y **no creé ninguna cuenta** (crear cuentas queda fuera de lo que hago sin ti). Que el índice esté detrás del login es **hecho verificado**; que dentro estén *todos* los manuales es **inferencia razonable, no comprobada**. Con Fontiber en due-diligence, el alta es un riesgo real — **aquí ayuda que TRATEIN PCI sea instalador**: el alta suele ir por el comercial/delegación de zona.

---

### 3.3 VÍA C — Petición comercial (para lo que no salga de A ni B) 📞

Contactos oficiales (decodificados del ofuscado anti-spam de la página de delegaciones de `notifier.es`):

| Canal | Para qué |
|---|---|
| **soporteHLSI@honeywell.com** | Soporte técnico HLSI — **el buzón correcto para pedir documentación** |
| **infohlsiberia@honeywell.com** | General |
| **ofertasHLSI@honeywell.com** / **pedidosHLSI@honeywell.com** | Ofertas / pedidos |
| **Tel. 931 334 760** | Número único nacional (Este/Centro/Norte/Sur/Levante/Noroeste) |
| **C/ Pau Vila 15-19, Badalona (Barcelona)** | Oficinas centrales HLSI (Notifier **y** Morley comparten sede) |
| **technical.support@morleyias.co.uk** | Soporte técnico Morley UK (legacy `996-xxx`) |
| Portugal: Carnaxide, **+351 214 245 000** | — |

**Qué pedir, exactamente.** No pidas PDFs sueltos: **pide el índice**. «Listado de manuales vigentes y obsoletos por familia de producto (ID1000/Serie 1000, ID50/ID60, Pearl, ZXSe) con su número de documento.» El índice es lo escaso; los ficheros no.

**Documentos que probablemente solo salgan por aquí:**
- **S00-368-000** — la propia fuente dice «disponible previa solicitud». Es la única vía.
- **997-340-005** — software de Carga/Descarga de una central de 1999; puede no estar publicado.
- Y la consulta de cierre del punto 0: **¿existe una «Guía Avanzada de Configuración» de la CAD-171 distinta del MC-380 rev c?** — esa va a **Detnov**, no a Honeywell.

**Ventaja de contexto M&A:** pedir el paquete documental al delegado suele traer además **matrices de compatibilidad y listas de producto descatalogado** que no están en web — material valioso para el bot y para la due-diligence.

---

### 3.4 Plan recomendado: las tres vías **en paralelo**, no en secuencia

No dependen entre sí y tienen latencias muy distintas.

1. **Hoy, coste cero:** Vía A para los 5 documentos con valor real (997-340-005, 997-415, 997-412, 997-677-000, 996-137). Buscador acotado + regla de nombre + las dos carpetas. `997-677` es el de mayor probabilidad (Pearl lleva el 997 en el nombre); los tres de ID1000/ID50 son legacy → probar primero `/manualesobs/`.
2. **Hoy, 15 minutos:** las tres altas de la Vía B. Si entran, dan el **índice**, que es exactamente lo que falta — y el foro Morley es la única fuente organizada del legacy `996-xxx`.
3. **Si (1) y (2) se atascan a la semana:** un correo a `soporteHLSI@honeywell.com` pidiendo **el listado**, no los ficheros. Y uno a Detnov para el cierre del punto 0.

---

## 4. Qué hago yo cuando lleguen los PDFs — flujo de ingesta

> ### ⚠️ ADVERTENCIA OPERATIVA — dónde va cada cosa
>
> **El código vive en `C:\dev\technical_bot`. El corpus (los PDFs) vive en `C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\`, en las carpetas `Manuales_*`.** El checkout **no contiene ni un solo PDF** (están gitignorados).
>
> Esto **rompe la Etapa A1 si se corre desde el sitio equivocado**: `src/reingest/inventory.py` hace `os.chdir(ROOT)` y luego `glob("**/*.pdf")` **relativo a ese ROOT**. Corrido desde `C:\dev\technical_bot` produce un manifiesto **vacío**. Ya hay guardas que lo cortan en seco (s301) — verificadas en el código:
> - `inventory.py`: *«inventario VACÍO: 0 PDFs bajo el directorio actual … El corpus vive en la carpeta OneDrive del proyecto — ejecuta desde allí»*
> - `extract.py`: *«un manifiesto vacío casi siempre significa inventario corrido desde el checkout sin corpus … Re-corre A1 desde el directorio correcto»*
>
> ⚠️ **Punto abierto declarado:** la memoria del proyecto dice que la copia de OneDrive está muerta/corrupta como *checkout de código* (2-ago), pero es donde están los PDFs. Antes de ingestar hay que decidir **una** de estas dos: (a) correr la Etapa A desde una copia de código sana situada junto al corpus; o (b) traer las carpetas `Manuales_*` al lado del checkout de `C:\dev` (copia o enlace). **No lo doy por resuelto y lo confirmaré contigo antes de lanzar nada.**

### Dónde dejar los PDFs

| Documento | Carpeta destino |
|---|---|
| 997-340-005, 997-415, 997-412, 997-677-000 (Notifier) | `…\Manuales_Notifier_Privado\` si vienen del área de clientes; `…\Manuales_Notifier\ES\` si son de descarga pública |
| 996-137 (Morley) | `…\Manuales_Morley_Privado\` o `…\Manuales_Morley\` según origen |
| Cualquier Detnov | `…\Manuales_Detnov\` |

Convención del playbook: el sufijo `_Privado` distingue el material del área de clientes del público. **Es traza de procedencia, no decoración** — se usa en el inventario.

### Los pasos (canónico: `docs/INGESTION_PLAYBOOK.md`)

| # | Etapa | Comando | Qué produce / criterio |
|---|---|---|---|
| 0 | **Filtrado previo** | manual | Descartar idiomas ≠ ES/EN, revisiones antiguas, ficheros < 1 KB (descargas fallidas) y corruptos. **Comprobar SHA contra el store**: si el fichero ya se parseó, se salta solo |
| 1 | **A1 — Inventario + dedup nivel 1** | `python src/reingest/inventory.py` | `logs/reingest_manifest.json` = lista de ficheros ÚNICOS por SHA-256. **Coste 0, sin API.** Es el paso que exige el cwd correcto |
| 2 | **A2/A3 — Extracción (LlamaParse)** | `python src/reingest/extract.py --limit N` (o `--probe` para muestra) | Store duradero en `data/extraction/<config>/`, indexado por SHA + config. **Resumable**: re-ejecutar salta lo ya extraído. Requiere `LLAMAPARSE_API_KEY` en `.env`. Coste ≈ **45 créditos/página ≈ $0,056/pág** → un manual de 100 páginas ≈ **$5-6**. Para 5 documentos, decenas de dólares, no cientos |
| 3 | **Etapa B — Pipeline, en seco** | `python -m src.reingest.pipeline --dry-run` | Trocea, detecta idioma y metadata **sin gastar API de embeddings** ni tocar la BD; vuelca muestra a `logs/reingest_dryrun_sample.json`. **Este paso no se salta** (principio 2 del playbook: mide antes de ingestar) |
| 4 | **Etapa B — Ingesta real** | `python -m src.reingest.pipeline` | Cadena B1-B8: idioma → chunking → metadata → contextual retrieval (Haiku + prompt caching) → embedding Voyage@1024 → dedup semántico → indexación en **`chunks_v2`**. Idempotente (delete-then-insert por `extraction_sha256`); estado en `logs/reingest_pipeline_state.json` |
| 5 | **Inventario Excel** | `python scripts/update_inventario.py --dry-run` y luego sin flag (o `--only Notifier,Morley`) | Reconstruye la hoja del fabricante + la fila de Resumen en `data/Inventario_Manuales.xlsx`; deja backup `.bak.xlsx`. **Verificar a mano la fila de Resumen** (Productos/Documentos cuadran). ⚠️ **Detnov es hoja legacy** (no está en el dict `FABRICANTES`): ahí se **APENDIZA**, no se reconstruye — un rebuild borraría sus 109 productos sin PDF (precedente DEC-030) |
| 6 | **Identidad / catálogo** | — | Comprobar que el doc nuevo queda mapeado en `data/catalog/doc_map.jsonl` con el/los producto(s) correctos. Es lo que hace que el bot encuentre el manual desde el nombre del producto (como el MC-380 → `detnov:cad-171` del punto 0) |
| 7 | **Supersesión** | manual | Si el documento nuevo es **edición posterior** de uno que ya tenemos (caso probable de `997-320-00x`), decidir vigencia. **Lección #33: la vigencia se ancla en el CONTENIDO, no en la tabla de revisiones interna** — Detnov ya nos coló una tabla desactualizada |
| 8 | **Eval / verificación** | `python -m pytest -q` + smoke del path real + preguntas de regresión de la familia tocada | Ningún cambio de calidad se da por bueno sin medir. Y **los golds los firma Alberto** (DEC-025): yo propongo ficha, no creo el gold |

**Lo que NO hago sin ti:** crear cuentas en los portales, aceptar términos, hacer el merge a `main`, y crear golds. También te confirmo antes de lanzar el paso 2 (es el único con coste real de API).

---

## ADENDA s303 (7-ago) — resultado de la búsqueda, y una corrección al propio packet

**Encontrados 2 de los 3 documentos con valor real** (verificados: HTTP 200, `%PDF`,
identidad confirmada abriendo el fichero):

| Doc | Estado | Fichero | Nota |
|---|---|---|---|
| **997-412** | ✅ DESCARGADO | `997-412-000-3_IDR-M_Mimic_installation_and_commissioning_manual.pdf` (2,68 MB, 24 pp., issue 3 jun-2005) | **Solo en INGLÉS** — no existe edición española (verificado) |
| **997-415** | ✅ DESCARGADO | `997-415_4_ID50_Panel_software_upgrade_instruction.pdf` (1,35 MB, 5 pp., issue 4 oct-2002) + la issue 3 de 2001 | **Solo en INGLÉS** |
| **997-340-005** | ❌ NO EXISTE en abierto | — | La categoría ID1000 del portal lista 5 documentos y ninguno es carga/descarga; `MCDT212.pdf` (el prefijo `MC` = carga/descarga) da 404 en ambas carpetas. Requiere cuenta de distribuidor |

Fuente de los dos hallados: un distribuidor holandés (`support.topsecurity.nl`), no los
portales españoles — que **no publican estos dos documentos en ningún idioma**.

**Corrección al punto 3.2 de este packet.** El packet afirmaba: «el cuello de botella no es
el acceso, es la descubribilidad: los ficheros están abiertos, lo que no tenemos es la lista
de qué existe → merece la pena el registro». **La segunda mitad es falsa.** El índice es
PÚBLICO vía el componente ZOO de Joomla (`/component/zoo/alphaindex/…`), que además
devuelve el nombre de fichero real en `Content-Disposition`. Cosechado: **844 entradas
(813 títulos únicos)** de las dos marcas → `data/catalog_portales/s303_portales_notifier_morley_v1.json`.
Método y trampas: `docs/CORPUS_NOTIFIER_MORLEY.md`. **Consecuencia para Alberto: las altas
de partner de Notifier ES y Morley-IAS ES NO hacen falta** para conocer el catálogo (la del
foro Morley UK sigue en pie para el legacy `996-xxx`).

**Trampa operativa registrada** (invalidó la primera pasada): hay un WAF de Akamai delante
de `notifier.es` y responde **403, no 404**, al bloquear — un probe rápido reporta «no
existe» sobre ficheros que sí existen. Barridos futuros: secuenciales, ~3 s, y tratar 403
como «para», nunca como ausencia.

**El «bonus» confirma el packet**: el agente descargó también el `997-411` en español
(`MN-DT-200`), que este packet clasificaba como falso positivo por estar ya en corpus.
Verificado contra `chunks_v2`: **44 chunks bajo `MNDT200`** — en efecto, ya lo teníamos.

**Lo que queda por decidir (Alberto)**: (a) ingerir los 2 documentos, que están en INGLÉS y
el corpus es ES-dominante — coste de extracción ~$2, pero el hueco de vocabulario ES↔EN es
un lever medido (DEC-085), así que conviene ingerir Y MEDIR, no asumir; (b) correr el cruce
catálogo↔corpus (813 títulos vs 705 docs de estas marcas) para tener la lista de adquisición
definitiva — exige resolver nombres de fichero secuencialmente, ~45 min.

## Resumen ejecutivo en cinco líneas

1. **La «Guía Avanzada de Configuración» de la CAD-171 NO hay que comprarla: ya la tenemos** (`MC-380 rev c`, §5.4 p.29, mapeado a `detnov:cad-171`). El primer fallo orgánico del bot es 100 % de selección → se arregla con gold + retrieval, no con corpus.
2. De 44 candidatos del barrido, **solo 7 son huecos reales**; el instrumento tiene 4 bugs identificados que explican casi todo el ruido — y **perdió un hueco real** (`997-412`).
3. **Tres documentos valen la pena de verdad**: `997-340-005` (programación por PC ID1000), `997-415` (actualización ID50/ID60/ZX50, 6 citas, dos marcas) y `997-412` (Sinóptico IDR, 4 citas).
4. **Los PDF de `notifier.es` y `morley-ias.es` se descargan sin login** — lo que está cerrado es el **índice**. Empieza por ahí hoy, y manda las tres altas en paralelo.
5. Nada de esto entra al bot hasta pasar el pipeline de 8 pasos — y **el corpus vive en OneDrive, no en el checkout**: correr la ingesta desde el sitio equivocado produce un inventario vacío (hay guardas que ahora lo cortan).

---

### Ficheros de referencia (rutas absolutas)

- `C:\dev\technical_bot\evals\s294_citation_gap_v1.json` — barrido de origen
- `C:\dev\technical_bot\scripts\s294_citation_gap.py` — instrumento (bugs en ~47-49, ~66-67, ~88-128)
- `C:\dev\technical_bot\evals\s294_cad171_menu_avanzado_v1.md` — recibo del primer fallo orgánico (DEC-176)
- `C:\dev\technical_bot\evals\s83_full_extraction_merged.jsonl` — refs internas `997-xxx` ya extraídas de portada (la materia prima del fix nº1)
- `C:\dev\technical_bot\evals\s174_prerequisite_corpus_census_v1.json` — censo de `chunks_v2`
- `C:\dev\technical_bot\data\catalog\doc_map.jsonl` — mapa documento → productos
- `C:\dev\technical_bot\data\Inventario_Manuales.xlsx` — inventario (8 hojas; legible con openpyxl)
- `C:\dev\technical_bot\docs\INGESTION_PLAYBOOK.md` — playbook canónico de 9 pasos
- `C:\dev\technical_bot\docs\CORPUS_FIRESECURITYPRODUCTS.md` — runbook Carrier (**necesita** el fix `page=1` + nota de alcance «no cubre Honeywell»)
- `C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\Manuales_*\` — **el corpus real**
## ADENDA 2 — s303: los 2 documentos INGERIDOS y su alcanzabilidad MEDIDA

**Ingesta hecha** (7-ago): A1 inventario → A2 extracción LlamaParse (2 docs, 29 páginas,
~2 $) → B dry-run → B real. **36 chunks en `chunks_v2`**, verificados contra la base:

| Documento | source_file | chunks | product_model asignado |
|---|---|---|---|
| 997-412 (Sinóptico IDR-M) | `997-412-000-3_IDR-M_Mimic_installation_and_commissioning_manual` | 32 | `ID-2000` ⚠️ |
| 997-415 (actualización ID50) | `997-415_4_ID50_Panel_software_upgrade_instruction` | 4 | `ID-50` |

**La pregunta que motivó medir: ¿sirve un documento en INGLÉS a un técnico que pregunta en
ESPAÑOL?** Sonda `scripts/s303_alcanzabilidad_es_en.py` (recibo
`evals/s303_alcanzabilidad_es_en_v1.json`): 4 formulaciones en español, cada una con su
gemela inglesa como CONTROL, medidas hasta la evidencia SERVIDA (post-rerank).

| | Español | Inglés (control) |
|---|---|---|
| Documento servido al generador | **3 / 4** | 4 / 4 |

⇒ **La ingesta PAGA, con límite declarado.** El hueco ES↔EN es real pero **parcial**: tres
de cuatro formulaciones españolas traen el documento. La que falla —«conexionado y puesta
en marcha del panel repetidor sinóptico IDR-M»— no lo alcanza **ni siquiera en el pool**,
mientras su gemela inglesa trae 12 chunks: el vocabulario («conexionado», «panel repetidor»
vs *wiring*, *mimic*) es la variable, no el contenido ni la ingesta. Coherente con DEC-085
(el mecanismo que paga contra este hueco es extracción→ENUNCIADOS), y ahora con dos
documentos reales sobre los que medirlo.

### Dos residuos con dueño

1. **Identidad del 997-412 — para adjudicar (Alberto)**: quedó etiquetado `product_model =
   ID-2000`, pero el documento es un sinóptico **multi-panel**: menciona ID50 (×3), ID2000
   (×2), ID3000, ID2008, ID1000, NF3000, NF300. La etiqueta única no representa su alcance.
   No bloquea (las consultas de la sonda no filtraban por modelo), pero una pregunta que
   fije «ID50» podría no verlo. Es material de curación de identidad / `doc_map`.
2. **⚠️ DIVERGENCIA DE CORPUS — acción de Alberto**: los 2 PDF se ingirieron desde
   `C:\dev\technical_bot\data\Manuales_Notifier\` (gitignorado), **no** desde la carpeta
   OneDrive que es el corpus de referencia. La base ya tiene los chunks, pero **el corpus de
   ficheros está incompleto**: si alguien re-corre el inventario desde OneDrive, estos 2 no
   estarán. **Copiar los 2 PDF a `…\OneDrive…\Manuales_Notifier\`** para que el corpus de
   referencia vuelva a ser completo (y, con él, el Inventario Excel).
