# s91 — PRE-QA de los 25 homónimos cross-brand · agrupados por patrón (~10 min)

> Evidencia = corpus (docs de cada lado + categoría extraída + family_scope). El patrón dominante es
> **A: mismo producto, OEM + marca(s) que lo venden** — el grupo Honeywell operando. Marca por GRUPO
> (✅ = todo el grupo tal cual; ✏️ = di qué ítem cambia). Al aprobar: el OEM/naming-owner queda
> canonical, los otros ids → redirect, `vendido_bajo` = unión, relación rebrand-of, homónimo retirado.

## G1 · OEM System Sensor → vendido por Notifier (y Morley) — 11 ítems, propongo A
La firma en corpus: doc PROPIO System Sensor (I56-*) + docs Notifier/Morley que venden el mismo equipo
con idéntica categoría.
| token | evidencia |
|---|---|
| `B501AP` | doc propio I56-2668 (base de detector B500); Morley/Notifier la citan en sus sirenas/estrobos |
| `B501` | I56-2055 B500 Series vs Notifier MNDT150 (base para ID-200) |
| `REFL20/30/40/50/60` (×5) | reflectores del 6200R (I56-1726, SS) ≡ los del LPB-620 Notifier (I56-1671) — el LPB-620 ES el 6200 rebrandeado |
| `6500R` / `6500RS` | detector de haz 6500 (I56-2081, SS) vs doc Notifier MADT780 que lo lista |
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

## G3 · Intra-Honeywell (naming Vision/Supra/CMX/UCIP…) — 12 ítems, propongo A con canonical en la marca de los docs PROPIOS
| token | propuesta canonical | evidencia |
|---|---|---|
| `UCIP` / `UCIP-GPRS` | notifier (docs propios HLSI-MN/MA-192) | la mención morley = referencia en el manual de la NFS Supra (accesorio) |
| `VSN-4REL` | **morley** (naming VSN=Vision=Morley, tu gt) | tarjeta 4 relés de Vision/Supra; vendido_bajo +Notifier (Supra) |
| `VSN 4 PLUS` / `VSN12-2Plus` / `VSN-CO` | **morley** (centrales Vision Plus) | vendido_bajo +Notifier (doc ITA VSN4-PLUS) |
| `IDR-6A` | notifier (docs propios MNDT200/MCDT191, repetidores IDR) | la mención morley = FAQ de CONNEXION que lo cita |
| `6424` | notifier (MIDT750) | detector lineal IR idéntico en Morley MIE-MI-140 → vendido_bajo +Morley |
| `CMX-10RM` | notifier (MNDT1004) | tarjeta 10 relés idéntica en Morley MIE-MI-470 → +Morley |
| `MI-DCZM` | **morley** (prefijo MI- = Morley-IAS naming) | la mención notifier = doc compat |
| `M710` | notifier | módulo del protocolo compartido; +Morley |
| `2010-2-PAK-RMSDK` | edwards (doc bcn-*) | mismo dongle PAK bajo Kidde Commercial (grupo Kidde/Edwards, DEC-035) → +Kidde |

**TU MARCA G3: [ ] ✅ [ ] ✏️** — notas: __________

## G4 · El único DUDOSO — propongo B (homónimo clarify), 1 ítem
| token | por qué B |
|---|---|
| `APIC` | "Addressable Protocol Interface Card" = tarjeta de interfaz en productos anfitriones DISTINTOS: Aritech APIC para **ModuLaser** vs Notifier APIC para **LaserStar HSSD-2 (Stratos)**. Podría ser el mismo HW de aspiración compartido, pero el corpus no lo prueba → clarify (preguntar "¿para ModuLaser o para LaserStar?") es lo seguro. |

**TU MARCA G4: [ ] ✅ B-clarify [ ] ✏️ (es el mismo HW → A)** — notas: __________

## Qué pasa tras tus marcas
Aplico por la puerta: canonical+redirects+rebrand-of+vendido_bajo (provenance `gt-s91-alberto-homonyms`);
los homónimos-candidate adjudicados se retiran (el token resuelve limpio); re-valido + smoke + tests.
Los 12 homónimos restantes de la cola (menos docs) quedan fail-open para un 2º lote cuando quieras.
