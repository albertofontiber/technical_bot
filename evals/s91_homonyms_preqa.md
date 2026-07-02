# s91 — PRE-QA de los 25 homónimos cross-brand · agrupados por patrón (~10 min)

> Evidencia = corpus (docs + categoría + family_scope) **+ revisión web exhaustiva (6 búsquedas dirigidas; 2 propuestas corregidas: 6424→G1, PAK→kidde; APIC confirmado B; VSN multi-mercado; M710 sin vendido-Morley)**. El patrón dominante es
> **A: mismo producto, OEM + marca(s) que lo venden** — el grupo Honeywell operando. Marca por GRUPO
> (✅ = todo el grupo tal cual; ✏️ = di qué ítem cambia). Al aprobar: el OEM/naming-owner queda
> canonical, los otros ids → redirect, `vendido_bajo` = unión, relación rebrand-of, homónimo retirado.

## G1 · OEM System Sensor → vendido por Notifier (y Morley) — 12 ítems (+6424), propongo A
La firma en corpus: doc PROPIO System Sensor (I56-*) + docs Notifier/Morley que venden el mismo equipo
con idéntica categoría.
| token | evidencia |
|---|---|
| `B501AP` | doc propio I56-2668 (base de detector B500); Morley/Notifier la citan en sus sirenas/estrobos |
| `B501` | I56-2055 B500 Series vs Notifier MNDT150 (base para ID-200) |
| `REFL20/30/40/50/60` (×5) | reflectores compartidos del 6200R (I56-1726, SS) y del LPB-620 Notifier (I56-1671) — **ambos docs llevan numeración I56-* de System Sensor** (señal OEM); el rebrand completo LPB↔6200 no está probado en web, pero los REFL* son el mismo accesorio |
| `6500R` / `6500RS` | detector de haz 6500 (I56-2081, SS) vs doc Notifier MADT780 que lo lista |
| `6424` ⬅ movido de G3 | **web-confirmado OEM System Sensor** ([datasheet SS 6424](https://www.systemsensor.com/en-us/Documents/6424_DataSheet_A05-0217.pdf)); vendido Notifier (MIDT750) y Morley (MIE-MI-140) |
| `DH500` / `DH500ACDC-E` | carcasas de conducto DH500 (I56-512/I56-2166, SS) vs Notifier MIDT1040/1041 |

**Canonical → `systemsensor:*` (OEM), redirect desde notifier/morley, vendido_bajo=[System Sensor, Notifier, Morley-IAS].**
**TU MARCA G1: [ ] ✅ [ ] ✏️** — notas: __________

## G2 · OEM tercero → vendido por Notifier/Detnov — 7 ítems, propongo A
| token | OEM (doc propio) | quién lo vende |
|---|---|---|
| `SMART 2` | **Sensitron** (MT251) — ¡el doc Notifier MNDT615 dice literalmente "SMART 2 (Sensitron)"! | Notifier |
| `Z978` | **Pepperl+Fuchs** (barrera Zener serie Z, manual Z728) | Notifier (TIDT089) |
| `777163` | **Spectrex** (accesorio intemperie SharpEye 40/40) | Notifier (S40/40 = el rebrand de cat022) |
| `140KIT160` / `70KIT140` | **Firebeam** (kits reflector del haz Xtra) | Detnov (MI 546) |
| `M700KAC` / `M700KACI` | **KAC** (pulsadores) | Notifier |

**Canonical → el OEM, redirect desde el vendedor, vendido_bajo=unión.**
**TU MARCA G2: [ ] ✅ [ ] ✏️** — notas: __________

## G3 · Intra-Honeywell (naming Vision/Supra/CMX/UCIP…) — 11 ítems (6424→G1), propongo A con canonical en la marca de los docs PROPIOS
| token | propuesta canonical | evidencia |
|---|---|---|
| `UCIP` / `UCIP-GPRS` | notifier (docs propios HLSI-MN/MA-192) | la mención morley = referencia en el manual de la NFS Supra (accesorio) |
| `VSN-4REL` | **morley** (naming VSN=Vision=Morley, tu gt) | tarjeta 4 relés de Vision/Supra; vendido_bajo +Notifier (Supra) |
| `VSN 4 PLUS` / `VSN12-2Plus` / `VSN-CO` | **morley** (centrales Vision Plus; tu gt Vision=Morley) | **web: la familia VSN es multi-marca POR MERCADO** — [notifier.it la lista en su catálogo](https://www.notifier.it/catalogo.asp?id=2) (incl. el bundle VSN4-PLUS+VSN-4REL) y el doc ITA vive en morley-ias.es → vendido_bajo=[Morley-IAS (ES), Notifier (IT)] |
| `IDR-6A` | notifier (docs propios MNDT200/MCDT191, repetidores IDR) | la mención morley = FAQ de CONNEXION que lo cita |
| `CMX-10RM` | notifier (MNDT1004) | tarjeta 10 relés idéntica en Morley MIE-MI-470 → +Morley |
| `MI-DCZM` | **morley** (prefijo MI- = Morley-IAS naming) | la mención notifier = doc compat |
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
