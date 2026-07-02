# s91 — PRE-QA de los 25 homónimos cross-brand · agrupados por patrón (~10 min)

> Evidencia = corpus + web (6 búsquedas; 2 correcciones) **+ VERIFICACIÓN AL PÍXEL (14 portadas
> renderizadas de los PDFs reales, lección s80)**. Hallazgos del píxel:
> · **CMX-10RM y 6424: manuales GEMELOS Morley/Notifier** (mismo texto/foto, solo cambia el logo) = venta dual REAL, no mera compat.
> · **B501AP/6200R/LPB-620: © System Sensor** en los propios docs (el manual "Notifier" del LPB-620 lleva copyright SS) — aunque LPB-620 (direccionable) ≠ 6200R (convencional): mismo HW óptico, electrónica distinta; los REFL* son el accesorio compartido.
> · **APIC: anfitriones DISTINTOS al píxel** (MIDT731 = LaserStar-HSSD-2/Stratos vs doc Aritech = ModuLaser) → B definitivo.
> · **Z978: el doc Notifier TIDT089 ES la tabla de mapeo OEM↔vendedor** ("referencia de PEPPER KFDO-CS-Ex… = referencia Notifier AIS-GALD1") — el patrón G2 escrito por el propio fabricante.
> · **UCIP: la portada es Honeywell Life Safety Iberia** (ni Notifier ni Morley) → producto de la filial del grupo; vendido_bajo=[HLSI, Notifier, Morley (Supra)] con canonical notifier pragmático.
> · **2ª pasada al píxel (workflow 10 agentes sobre los ítems restantes): 9 A-confirmadas + 1 ajuste (familia Vision = brand-swap ES/IT con 'vision' como marca de línea).** Hallazgos: el pie del doc Notifier del M700KAC firma 'KAC ALARM COMPANY LIMITED'; MI-DCZM lleva '© System Sensor 2005' (OEM real); el doc Notifier del DH500 cita el doc-number SS en su caja. **Todos los 25 ítems verificados en documento real — no te queda ningún PDF por abrir.** El patrón dominante es
> **A: mismo producto, OEM + marca(s) que lo venden** — el grupo Honeywell operando. Marca por GRUPO
> (✅ = todo el grupo tal cual; ✏️ = di qué ítem cambia). Al aprobar: el OEM/naming-owner queda
> canonical, los otros ids → redirect, `vendido_bajo` = unión, relación rebrand-of, homónimo retirado.

## G1 · OEM System Sensor → vendido por Notifier (y Morley) — 12 ítems (+6424), propongo A
La firma en corpus: doc PROPIO System Sensor (I56-*) + docs Notifier/Morley que venden el mismo equipo
con idéntica categoría.
| token | evidencia |
|---|---|
| `B501AP` | doc propio I56-2668 (base de detector B500); Morley/Notifier la citan en sus sirenas/estrobos |
| `B501` | **PÍXEL: tabla 'B500 SERIES BASE OPTIONS' con la fila B501 en el manual propio SS** (© System Sensor 2004, Pittway Trieste); MNDT150 = manual de la central ID-200 que la usa |
| `REFL20/30/40/50/60` (×5) | reflectores compartidos del 6200R (I56-1726, SS) y del LPB-620 Notifier (I56-1671) — **ambos docs llevan numeración I56-* de System Sensor** (señal OEM); el rebrand completo LPB↔6200 no está probado en web, pero los REFL* son el mismo accesorio |
| `6500R` / `6500RS` | detector de haz 6500 (I56-2081, SS) vs doc Notifier MADT780 que lo lista |
| `6424` ⬅ movido de G3 | **web+PÍXEL: OEM System Sensor** ([datasheet](https://www.systemsensor.com/en-us/Documents/6424_DataSheet_A05-0217.pdf)); manuales GEMELOS Morley (MIE-MI-140) y Notifier (MIDT750) = venta dual real |
| `DH500` / `DH500ACDC-E` | **PÍXEL: el doc Notifier MIDT1040 CITA en su propia caja el doc SS '156-512-07R'** — es la localización ES del manual OEM; SS propio confirmado (St. Charles, Illinois) |

**Canonical → `systemsensor:*` (OEM), redirect desde notifier/morley, vendido_bajo=[System Sensor, Notifier, Morley-IAS].**
**TU MARCA G1: [ ] ✅ [ ] ✏️** — notas: __________

## G2 · OEM tercero → vendido por Notifier/Detnov — 7 ítems, propongo A
| token | OEM (doc propio) | quién lo vende |
|---|---|---|
| `SMART 2` | **Sensitron** (MT251) — ¡el doc Notifier MNDT615 dice literalmente "SMART 2 (Sensitron)"! | Notifier |
| `Z978` | **Pepperl+Fuchs** (barrera Zener serie Z, manual Z728) | Notifier (TIDT089) |
| `777163` | **Spectrex** (accesorio intemperie SharpEye 40/40) | Notifier (S40/40 = el rebrand de cat022) |
| `140KIT160` / `70KIT140` | **Firebeam** — **PÍXEL: co-branding 'thefirebeam + detnov' EN LA MISMA PORTADA** del manual ES (MI 546); el user guide Xtra es Firebeam puro | Detnov |
| `M700KAC` / `M700KACI` | **KAC** — **PÍXEL: el pie del doc Notifier D1036 dice 'KAC ALARM COMPANY LIMITED… www.kac.co.uk'** (el OEM firmado en el doc del vendedor); modelos 'System Sensor Protocol' | Notifier |

**Canonical → el OEM, redirect desde el vendedor, vendido_bajo=unión.**
**TU MARCA G2: [ ] ✅ [ ] ✏️** — notas: __________

## G3 · Intra-Honeywell (naming Vision/Supra/CMX/UCIP…) — 11 ítems (6424→G1), propongo A con canonical en la marca de los docs PROPIOS
| token | propuesta canonical | evidencia |
|---|---|---|
| `UCIP` / `UCIP-GPRS` | notifier (pragmático) | **PÍXEL: la portada del HLSI-MN-192 es Honeywell Life Safety Iberia** (filial del grupo, ni N ni M) → vendido_bajo=[HLSI, Notifier, Morley (Supra)] |
| `VSN-4REL` | **morley** (naming VSN=Vision=Morley, tu gt) | tarjeta 4 relés de Vision/Supra; vendido_bajo +Notifier (Supra) |
| `VSN 4 PLUS` / `VSN12-2Plus` / `VSN-CO` | **morley** (confirmado) | **PÍXEL (ajuste): brand-swap por mercado** — MIE-MI-130 (ES, Morley) y HLSI-MI-130I (EN, firmado solo 'vision') son EL MISMO manual (mismo nº MI-130); el doc ITA lleva logo Notifier PERO la etiqueta física del panel fotografiado dice 'vision' → **Vision = marca de línea/HLSI subyacente**; vendido_bajo=[Morley-IAS (ES), Notifier (IT), Vision/HLSI]. VSN-CO caveat: la portada MIE-MI-591 dice 'VSN Park / Detección CO' — el string 'VSN-CO' exigiría página interior |
| `IDR-6A` | notifier (docs propios MNDT200/MCDT191, repetidores IDR) | la mención morley = FAQ de CONNEXION que lo cita |
| `CMX-10RM` | notifier (MNDT1004) | **PÍXEL: manuales GEMELOS** (Morley: 'módulos MI-CME'; Notifier: 'módulos CMX-2' — mismo HW, naming interno por marca) → vendido_bajo=[Notifier, Morley-IAS] |
| `MI-DCZM` | **morley** (canonical confirmado al píxel: portada Morley-IAS) | **PÍXEL: '© System Sensor 2005' + hardware serie M200E** → registrar oem=System Sensor (mismo patrón FAAST); mención notifier=compat |
| `M710` | notifier | **web-confirmado Notifier** ([datasheet](https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/literature-and-specs/datasheets/notifier-it/HBT-Fire-201710270924-M710-M720-dep-eng.pdf)); el equivalente Morley es el MI/DMMIE (línea SEPARADA) → la mención morley = compat/secondary, NO vendido_bajo |
| `2010-2-PAK-RMSDK` | **kidde** (corregido tras web: se vende como Kidde/Ziton/Kilsen/UTC — todo el grupo Carrier; [ficha](https://www.ibdglobal.com/en/slides/slide/2010-2-pak-rmsdk-ficha-tecnica-kidde-commercial-7326/datas)) | vendido_bajo +Edwards (doc bcn-*), +Ziton |

**TU MARCA G3: [ ] ✅ [ ] ✏️** — notas: __________

## G4 · El único DUDOSO — propongo B (homónimo clarify), 1 ítem
| token | por qué B |
|---|---|
| `APIC` | "Addressable Protocol Interface Card" = tarjeta de interfaz en productos anfitriones DISTINTOS: Aritech APIC para **ModuLaser** vs Notifier APIC para **LaserStar HSSD-2 (Stratos)**. **Web-CONFIRMADO que son tarjetas DISTINTAS**: el APIC AirSense/Aritech para ModuLaser declara literalmente "NOT compatible for installation in Stratos range aspirating devices" ([installation sheet](https://www.manualslib.com/manual/3481648/Airsense-Aritech-Apic.html)) — incompatibles entre sí → clarify. |

**TU MARCA G4: [ ] ✅ B-clarify [ ] ✏️ (es el mismo HW → A)** — notas: __________

## Qué pasa tras tus marcas
Aplico por la puerta: canonical+redirects+rebrand-of+vendido_bajo (provenance `gt-s91-alberto-homonyms`);
los homónimos-candidate adjudicados se retiran (el token resuelve limpio); re-valido + smoke + tests.
Los 12 homónimos restantes de la cola (menos docs) quedan fail-open para un 2º lote cuando quieras.
