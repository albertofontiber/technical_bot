# Packet C2 — 19 marcas sin mapear → desbloquean 196 productos `unresolved:*` (~5 min)

> Regla de clase (plan v2.2 S3): tú adjudicas la FILA (marca→namespace), yo aplico por la puerta
> (BRAND_MAP + re-namespace de sus productos con provenance `gt-s91-alberto-c2`). Los dudosos
> quedan candidate igual que hoy — marcar "✏️/dudosa" no rompe nada (fail-open).

| # | marca en el doc | propuesta namespace | nota |
|---|---|---|---|
| 1 | Fire Fighting Enterprises (F5000) | `ffe` | fabricante UK de detectores de haz (Fireray) |
| 2 | Golmar (MAD-481, doc 55348101) | `golmar` | ⚠ el doc-number 553* es numeración DETNOV → ¿OEM Detnov vendido por Golmar? nota si lo sabes |
| 3 | COELBO (AC1460R ATEX) | `coelbo` | equipos ATEX |
| 4 | FAAST (Honeywell) | `systemsensor` | FAAST = línea de SS (tu gt); "Honeywell"=grupo. Coherente con s80 (serie→Notifier NO cambia: eso es producto, esto es la marca del doc) |
| 5 | FAAST (System Sensor Europe) | `systemsensor` | doc I56-6574 (el 6574 standalone) |
| 6 | ENScape (D 1101 Sounder Beacon) | `systemsensor` (dudosa) | línea de sirenas EN54; numeración D-* estilo grupo — ✏️ si sabes el dueño real |
| 7 | DELTA (D391, WR2001) | `delta` (dudosa) | campana intemperie WR2001 |
| 8 | EFS (FS8) | `efs` (dudosa) | sin más señal en el doc |
| 9 | Calectro (conduct detector) | `calectro` | sueco, detectores de conducto |
| 10 | Fire-Lite Alarms (MNDT080) | `firelite` | marca US del grupo Honeywell (doc servido por Notifier ES) |
| 11 | AVOTEC (REXD-103, PAN AVD2) | `avotec` | rótulos/señalización — 2 docs |
| 12 | FUEGO (NSRE24) | `fuego` (dudosa) | sin más señal |
| 13 | Cranford Controls (SFD-220) | `cranford` | sirenas UK |
| 14 | Honeywell Life Safety (doc de formación) | GRUPO → contextual | como GRUPO_BRANDS (no namespace propio); el doc es administrativo |
| 15 | Desarrollo de Sistemas Integrados de Control S.L. (TG-1020-TEC) | `desico` | = DESICO (el acrónimo de la razón social) |
| 16 | DESICO (TG-1020-USU) | `desico` | mismo fabricante que #15 |
| 17 | Detectortesters (Solo A10) | `detectortesters` | No Climb Products (equipos de prueba) |
| 18 | DXc Connexion | `morley` | NO es marca: es el panel DXc + Connexion de Morley |

**TU MARCA C2: [ ] ✅ todo tal cual [ ] ✏️** — notas: __________
(#15+#16 son la misma decisión → 18 filas, 17 decisiones reales)
