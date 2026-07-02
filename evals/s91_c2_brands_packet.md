# Packet C2 — 19 marcas sin mapear → desbloquean 196 productos `unresolved:*` (~5 min)

> Regla de clase (plan v2.2 S3): tú adjudicas la FILA (marca→namespace), yo aplico por la puerta
> (BRAND_MAP + re-namespace de sus productos con provenance `gt-s91-alberto-c2`). Los dudosos
> quedan candidate igual que hoy — marcar "✏️/dudosa" no rompe nada (fail-open).
> **2ª pasada (petición Alberto): FAAST revisado contra el gt s80 (filas 4-5) + 6 dudosas verificadas en web.**
> **3ª pasada (corrección de Alberto: hosting ≠ OEM): filas 8/12 re-verificadas con la lente OEM — la 12 CAMBIÓ (`ada`, OEM al píxel en portada); la 8 se re-fundamentó con evidencia interna (numeración 997-* de Notifier, 5 hermanos en corpus). Solo la 7 (DELTA) queda dudosa.**

| # | marca en el doc | propuesta namespace | nota |
|---|---|---|---|
| 1 | Fire Fighting Enterprises (F5000) | `ffe` | fabricante UK de detectores de haz (Fireray) |
| 2 | Golmar (MAD-481, doc 55348101) | `detnov` **(verificado web)** | el 55348101 es el manual PROPIO de Detnov (alojado en detnov.com); MAD-481 = módulo direccionable Detnov; Golmar = distribuidor (su tarifa lo lista) → vendido_bajo +Golmar |
| 3 | COELBO (AC1460R ATEX) | `coelbo` **(verificado web)** | COELBO s.r.l. (Brugherio, Italia), antideflagrantes ATEX/CESI; la serie EFD/1460 tiene declaración de conformidad en Honeywell-EDAM bajo notifier-it → vendido_bajo +Notifier (It) |
| 4 | FAAST (Honeywell) | `notifier` **(revisado vs gt s80)** | GT FAAST: LT-200=System Sensor, FLEX=Xtralis (tu adjudicación s55/s80); el catálogo ya tiene la línea en `notifier:*` CON oem=System Sensor (D3 pragmático s80) → misma casa, sin segunda copia. El doc es marketing sin productos |
| 5 | FAAST (System Sensor Europe) | `notifier` **(revisado vs gt s80)** | mismo criterio que #4 (los FL0111E-HS del 6574 YA viven en notifier:* con oem=SS). ⚠ Nota de coherencia: el patrón G1 de ayer (canonical=OEM) sugeriría re-domiciliar los FL* a systemsensor — si lo quieres, es un follow-up aparte, no esta fila |
| 6 | ENScape (D 1101 Sounder Beacon) | `kac` **(verificado web)** | ENscape CWSS = línea de notificación Honeywell VENDIDA COMO KAC (retail 'KAC CWSS-WW-W5 ENScape'); D-numbering = KAC (D716/D1036/D1101) |
| 7 | DELTA (D391, WR2001) | `kac` (dudosa-media) | web no concluyente para WR2001, pero D391 = numeración KAC (patrón 3/3 confirmado: D716/D1036/D1101) y KAC fabrica campanas; 'DELTA' = probable nombre de serie — ✏️ si conoces la marca real |
| 8 | EFS (FS8) | `notifier` **(evidencia INTERNA, no hosting)** | doc-number 997-201-103 = numeración PROPIA de Notifier — 5 hermanos 997-* en el corpus, todos Notifier (Pearl 997-669/670/671, NAS-2 997-528) → el panel EFS/EM 8 es producto Notifier; 'EFS' = familia, no marca |
| 9 | Calectro (conduct detector) | `calectro` | sueco, detectores de conducto |
| 10 | Fire-Lite Alarms (MNDT080) | `firelite` | marca US del grupo Honeywell (doc servido por Notifier ES) |
| 11 | AVOTEC (REXD-103, PAN AVD2) | `avotec` | rótulos/señalización — 2 docs |
| 12 | FUEGO (NSRE24) | `ada` **(OEM al PÍXEL — corrección de Alberto aplicada)** | la portada lleva el logo del FABRICANTE: **'ADA Componentes Electrónicos, S.L.'** (OEM español); doc dual 'Sirena exterior ROBO 12V / FUEGO 24V' ('FUEGO' era el rótulo de la lente, no marca); notifier.es solo la ALOJA/vende → vendido_bajo=[ADA, Notifier] |
| 13 | Cranford Controls (SFD-220) | `cranford` | sirenas UK |
| 14 | Honeywell Life Safety (doc de formación) | GRUPO → contextual | como GRUPO_BRANDS (no namespace propio); el doc es administrativo |
| 15 | Desarrollo de Sistemas Integrados de Control S.L. (TG-1020-TEC) | `desico` | = DESICO (el acrónimo de la razón social) |
| 16 | DESICO (TG-1020-USU) | `desico` | mismo fabricante que #15 |
| 17 | Detectortesters (Solo A10) | `detectortesters` | No Climb Products (equipos de prueba) |
| 18 | DXc Connexion | `morley` | NO es marca: es el panel DXc + Connexion de Morley |

**ADJUDICADO PARCIAL s91 (Alberto, en sesión): filas 2✅detnov · 3✅coelbo · 6✅kac · 7✅kac · 8✅notifier · 12✅ada — APLICADAS** (`scripts/s91_apply_c2.py`: 19 productos re-domiciliados + 15 alias re-apuntados; validate + 411 tests).
**PENDIENTES tus marcas (12 filas): 1 (FFE) · 4-5 (FAAST→notifier) · 9 (Calectro) · 10 (Fire-Lite) · 11 (AVOTEC) · 13 (Cranford) · 14 (HLS→contextual) · 15-16 (DESICO) · 17 (Detectortesters) · 18 (DXc→morley).**
**TU MARCA resto: [ ] ✅ tal cual [ ] ✏️** — notas: __________
(#15+#16 son la misma decisión → 18 filas, 17 decisiones reales)
