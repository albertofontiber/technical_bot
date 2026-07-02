# Packet C2 · v4 — SOLO PENDIENTES (10 filas, ~3 min)

> **Ya adjudicado y APLICADO** (tus marcas, 2 tandas): FFE→`ffe` · Golmar/MAD-481→`detnov` ·
> COELBO→`coelbo` · ENScape→`kac` · DELTA/D391→`kac` · FS8→`notifier` · FUEGO/NSRE24→`ada`
> (OEM al píxel) — 20 productos re-domiciliados vía `scripts/s91_apply_c2.py`, suite verde.
> **Lente aplicada a TODAS las filas (tu corrección): hosting ≠ OEM — la evidencia es lo que
> hay EN el doc/producto** (logo, copyright, numeración propia, part-numbers).

| # | marca en el doc | propuesta | evidencia (lente OEM) | desbloquea |
|---|---|---|---|---|
| 4 | FAAST (Honeywell) | `notifier` | tu gt s80: LT-200=SS, FLEX=Xtralis; la línea YA vive en `notifier:*` con `oem=System Sensor` → misma casa. Doc = marketing | 0 productos (solo BRAND_MAP) |
| 5 | FAAST (System Sensor Europe) | `notifier` | mismo criterio; los FL* del doc 6574 ya existen. ⚠ opcional aparte: re-domiciliar FL* a `systemsensor` por coherencia G1 (canonical=OEM) — di si lo quieres | 0 productos |
| 9 | Calectro | `calectro` | fabricante sueco de detectores de conducto; UG-3 = SU serie, doc = manual propio (OEM-side) | 2 (UG-3-A4O/A5O) |
| 10 | Fire-Lite Alarms | `firelite` | **la fila más gorda**: los 14 part-numbers son TODOS Fire-Lite US (panel MS-5210UD, ACM-8RF, FCPS-24F…) = catálogo del OEM; Notifier ES solo aloja el doc → vendido_bajo +Notifier | **14** (ACM-8RF, AFM-16A*, CAC-10F, FCPS-24F/E, LDM-32F, LED-10/IM, MS-5210UD/E, NAC-REM, PRT-24) |
| 11 | AVOTEC | `avotec` | rótulos/señalización, 2 docs propios (REXD-103, PAN AVD2) | 1 (PAN AVD2) |
| 13 | Cranford Controls | `cranford` | fabricante UK de sirenas/bases; doc SFD-220 propio | 1 (VTB-32E) |
| 14 | Honeywell Life Safety | GRUPO → contextual | doc administrativo (formación); sin namespace propio (patrón GRUPO_BRANDS) | 0 |
| 15-16 | DESICO / Desarrollo de Sistemas Integrados de Control S.L. | `desico` | misma empresa (acrónimo de la razón social); docs TG-1020-TEC/USU propios | 1 (TG-1020) |
| 17 | Detectortesters | `detectortesters` | línea Solo de No Climb Products (OEM); datasheet propio ES | 2 (Solo A10/A3) |
| 18 | DXc Connexion | `morley` | NO es marca (panel DXc + Connexion de Morley); **el producto desbloqueado es `795-122` = numeración 795-* de tarjetas Morley** (tu pantallazo s90: 795-072/068-100) | 1 (795-122) |

**ADJUDICADO COMPLETO s91 (Alberto, 3 tandas) — PACKET CERRADO:**
- Filas 9/10/11/13/15-16/17/18 ✅ → APLICADAS (22 productos más; total C2 = 42 re-domiciliados).
- Fila 14 (HLS-formación) = **ruido** (doc administrativo; sin acción de catálogo).
- Filas 4-5 (FAAST) — **CORRECCIÓN FINAL de Alberto: "FAAST (…)" NO es marca — es FAMILIA de productos** (el extractor la clasificó mal como marca). Materializado como PARAGUAS por la puerta: `FAAST` (familia, 13 miembros, divergent=true) + `FAAST LT-200` adjudicado (divergent=true, 12 miembros incl. los 3 SKUs MI-FL* de Morley — antes estaba unknown/fail-open). Ambos tokens ahora EXPANDEN en retrieval; comercialización en vendido_bajo (Morley/Notifier), OEM per-modelo en `oem_manufacturer_marca` (SS hoy; Xtralis si entra el FLEX). NADA entra a BRAND_MAP.
- TODO (no bloquea): trasladar los strings adjudicados a BRAND_MAP en `catalog_gt.py` para re-runs del loader (tier adjudicado); 'DELTA'/'Golmar'/'FUEGO' NO se generalizan (genéricos/artefacto-de-título).
