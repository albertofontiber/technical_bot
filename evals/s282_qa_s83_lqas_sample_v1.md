# s282 QA-s83 — LQAS n=59, aceptación 0-defectos — verificación manual (v1)

**Estándar `batch_attested_v1`** (`evals/s281_h0t3_authority_contract_proposal_v1.md` §2 Pieza 3): muestra n=59, aceptar el lote SOLO con **0 defectos** ⇒ garantiza tasa de defecto real <5% con 95% de confianza.

- Cohorte auto-apply muestreada: **548** filas (`corroborate_noop` 423 + `fill_language_doctype` 125).
- Muestra: **n=59**, determinista (seed 282), estratificada por marca (largest-remainder).
- Método: cada fila verificada A MANO leyendo el CONTENIDO real de chunks (PostgREST GET SELECT, read-only), comprobando 3 ejes: (1) identidad `product_model` (corroborate_noop = pm gobernado == contenido; family = variante s83 ∈ familia gobernada), (2) `doc_type` del fill, (3) `language` del fill.

## Resultado por eje (mandato: 0-defectos)

| eje | operación auto-apply | defectos / 59 |
|---|---|---:|
| `product_model` | NO-OP (corroborate_noop) / conservar (family) | **0 / 59** |
| `doc_type` | fill (DB NULL → s83) | **0 / 59** |
| `language` | fill (DB NULL → s83) | **1 / 59** |

**VEREDICTO: la cohorte AS-SCOPED (pm-noop + doc_type + language COMPLETO) NO PASA el listón 0-defectos (1 defecto / 59).** El defecto está LOCALIZADO en el eje `language`, clase **fill-MULTI** (array de >1 idioma). Los ejes `product_model` y `doc_type` — los que el Tramo 2 existe para poblar (census: doc_type NULL=970, language NULL=902) — son **0-defecto / 59**.

**Causa raíz:** el array `languages` de s83 es "idiomas de los tokens presentes", no "idioma(s) de redacción": marca `en` cuando aparecen tokens ingleses (nombres de producto, UI de software, nomenclatura química) aunque el documento esté redactado en español. Único caso claro en la muestra: NAP-100 (MADT609). Contra-ejemplos que SÍ son multi legítimo: manuales Detnov "ES FR GB IT" (idioma en el propio filename), System Sensor 4-idiomas (CR-6EA, NRX-WCP), MFDT170 (bilingüe EN/ES verificado).

**Remedio recall-safe (aplicado a la PROPUESTA v2 + SQL, NO a DB):** `language` fill-MULTI → ADVISORY (Alberto / verificar-contenido); auto-apply = `pm-noop` + `doc_type` + `language`-SINGLETON. Esos tres ejes fueron 0-defecto en esta muestra → un re-draw LQAS confirmatorio sobre la cohorte re-scoped es el paso previo a la firma.

## Detalle fila a fila (59)

Verdict: OK = los 3 ejes correctos vs contenido; DEFECTO = ≥1 eje escribiría un valor incorrecto. `ML`=language fill-multi (advisory en v2), `SG`=singleton, `—`=sin fill de ese eje.

| # | source_file | write_op | doc_pm / s83 | doc_type fill | language fill | verdict |
|---:|---|---|---|---|---|---|
| 1 | `00-3280-501-4009-05_r005_2x-a_series` | fill language doctype | 2X-A / 2X-AE1 | instalacion | SG ['es'] | OK |
| 2 | `156-0393-008R - OSY2_Eng` | corroborate noop | OSY2 / OSY2 | instalacion | SG ['en'] | OK |
| 3 | `2x-af2-fb-s-161721-es` | corroborate noop | 2X-AF2-FB-S / 2X-AF2-FB-S | datasheet | ML ['en', 'es'] | OK |
| 4 | `2x-at-f2-fb-161721-es` | corroborate noop | 2X-AT-F2-FB / 2X-AT-F2-FB | datasheet | SG ['es'] | OK |
| 5 | `3103267-en_r001_2x-a_series_kuwait_m` | fill language doctype | 2X-A Táctil / 2X-AE1 | instalacion | SG ['en'] | OK |
| 6 | `55312000 SCD-120_Manual_ES` | corroborate noop | SCD-120 / SCD-120 | instalacion | SG ['es'] | OK |
| 7 | `55320002 Manual Programador PGD-200 ` | corroborate noop | PGD-200 / PGD-200 | guia_usuario | ML ['en', 'es', 'fr', 'it'] | OK |
| 8 | `55341101 Manual Modulo 1-2 Reles lib` | corroborate noop | MAD-412 / MAD-412 | instalacion | ML ['en', 'es', 'fr', 'it'] | OK |
| 9 | `55345103 Manual Pulsador Analogico M` | corroborate noop | MAD-450 / MAD-450 | instalacion | ML ['en', 'es', 'fr', 'it'] | OK |
| 10 | `9-30781-kid-en-161721-es` | corroborate noop | 9-30781-KID-EN / 9-30781-KID-EN | datasheet | ML ['en', 'es'] | OK |
| 11 | `ASD532_TD_T140421es_a` | corroborate noop | ASD532 / ASD 532 | datasheet | SG ['es'] | OK |
| 12 | `HLSI-MN-103I_V04 FR` | fill language doctype | RP1r / RP1r-Supra | instalacion | SG ['fr'] | OK |
| 13 | `I56-2055-000 B500 Series_Eng` | fill language doctype | B500 / B501 | instalacion | SG ['en'] | OK |
| 14 | `I56-3920-001 CR-6EA_multi` | corroborate noop | CR-6EA / CR-6EA | instalacion | ML ['de', 'en', 'es', 'it'] | OK |
| 15 | `I56-3956-201_PT Morley Loop FAAST LT` | corroborate noop | FAAST LT / FAAST LT | — | — | OK |
| 16 | `I56-3976-001 NFXI-MM10` | corroborate noop | NFXI-MM10 / NFXI-MM10 | instalacion | ML ['en', 'es', 'it'] | OK |
| 17 | `I56-4209-001 NRX-WCP Call Point Web` | corroborate noop | NRX-WCP / NRX-WCP | instalacion | ML ['de', 'en', 'es', 'it'] | OK |
| 18 | `I56-512-07R DH500` | corroborate noop | DH500 / DH500 | instalacion | SG ['en'] | OK |
| 19 | `Instruction Manual SGMI200` | corroborate noop | SGMI200 / SGMI200 | instalacion | SG ['en'] | OK |
| 20 | `MADT120_01` | corroborate noop | AFP-200 / AFP200 | operacion | SG ['es'] | OK |
| 21 | `MADT190_13` | corroborate noop | ID3000 / ID3000 | boletin | SG ['es'] | OK |
| 22 | `MADT230_01` | corroborate noop | AFP4000 / AFP4000 | mantenimiento | SG ['es'] | OK |
| 23 | `MADT233` | corroborate noop | AFP4000 / AFP4000 | operacion | SG ['es'] | OK |
| 24 | `MADT236` | fill language doctype | AFP4000 / Impresora AFP4000 (020-407) | instalacion | SG ['es'] | OK |
| 25 | `MADT380_01` | corroborate noop | NAM-232 / NAM-232 | instalacion | SG ['es'] | OK |
| 26 | `MADT609` | corroborate noop | NAP-100 / NAP-100 | otro | ML ['en', 'es'] | **DEFECTO** |
| 27 | `MADT765` | corroborate noop | FR2000EX / FR2000EX | instalacion | SG ['es'] | OK |
| 28 | `MADT951_03` | corroborate noop | ID3000 / ID3000 | configuracion | SG ['es'] | OK |
| 29 | `MCDT156_A` | fill language doctype | ID50/60 / ID50 | configuracion | SG ['es'] | OK |
| 30 | `MFDT112P` | corroborate noop | UDS-2N / UDS-2N | guia_usuario | ML ['es', 'pt'] | OK |
| 31 | `MFDT170` | fill language doctype | AFP-300/AFP-400 / AFP-300 | operacion | ML ['en', 'es'] | OK |
| 32 | `MIDT1041` | fill language doctype | DH500AC/DC / DH500ACDC-E | instalacion | SG ['es'] | OK |
| 33 | `MIDT1452_Inst_via radio` | corroborate noop | VW2W100 / VW2W100 | instalacion | SG ['es'] | OK |
| 34 | `MIDT192_ID3004-001_Instal_esp` | fill language doctype | ID3004 / ID3004-001 | instalacion | SG ['es'] | OK |
| 35 | `MIDT212` | corroborate noop | ID1000 / ID1000 | instalacion | SG ['es'] | OK |
| 36 | `MIDT730` | corroborate noop | LaserStar / LASERSTAR MÁSTER | instalacion | SG ['es'] | OK |
| 37 | `MIDT760_C` | corroborate noop | F2000D / F2000D | instalacion | SG ['es'] | OK |
| 38 | `MIEMN570I` | fill language doctype | RP1r / VSN-RP1r | guia_usuario | SG ['en'] | OK |
| 39 | `MNDT100` | corroborate noop | RP-1001 / RP-1001 | instalacion | SG ['es'] | OK |
| 40 | `MNDT1006` | corroborate noop | MMX-10M / MMX-10M | datasheet | SG ['es'] | OK |
| 41 | `MNDT102I_D FR` | corroborate noop | RP1R / RP1r | operacion | SG ['fr'] | OK |
| 42 | `MNDT102P` | corroborate noop | RP1r / RP1r | guia_usuario | ML ['es', 'pt'] | OK |
| 43 | `MNDT213` | fill language doctype | Serie 1000 / Repetidor Serie 1000 | instalacion | SG ['es'] | OK |
| 44 | `MNDT617` | corroborate noop | S613AMFP / S613AMFP | mantenimiento | SG ['es'] | OK |
| 45 | `MNDT720` | fill language doctype | 20/20L, 20/20LB / 20/20L | instalacion | SG ['es'] | OK |
| 46 | `MNDT724_40-40R` | fill language doctype | 40-40R / S40/40R | instalacion | SG ['es'] | OK |
| 47 | `MNDT741I` | corroborate noop | NAS / NAS | instalacion | SG ['en'] | OK |
| 48 | `MNDT742_G` | corroborate noop | NAS-2 / NAS-2 | instalacion | SG ['es'] | OK |
| 49 | `MNDT747` | corroborate noop | NAS-10 / NAS-10 | guia_usuario | SG ['es'] | OK |
| 50 | `MPDT230` | corroborate noop | AFP4000 / AFP4000 | configuracion | SG ['es'] | OK |
| 51 | `Manual_Firebeam_XTRA_ES` | corroborate noop | Firebeam XTRA / Firebeam Xtra | guia_usuario | SG ['es'] | OK |
| 52 | `NFS-SUPRA-VISION-PLUS-2-Como-solucio` | corroborate noop | NFS-SUPRA / NFS Supra | mantenimiento | — | OK |
| 53 | `TG-IP-1-SEC-Que-direccion-IP-tiene-p` | corroborate noop | TG-IP-1-SEC / TG-IP-1-SEC | otro | — | OK |
| 54 | `UCIP MODBUS AM8200 V5.1` | corroborate noop | AM8200 / AM-8200 | configuracion | ML ['en', 'es'] | OK |
| 55 | `UCIP-Borrar-datos-de-CRA1-o-2` | corroborate noop | UCIP / UCIP | configuracion | — | OK |
| 56 | `UCIP-Cambio-de-puerto-TCP-en-GPRS` | corroborate noop | UCIP / UCIP | configuracion | — | OK |
| 57 | `ke-dba-auxw-161721-es` | corroborate noop | KE-DBA-AUXW / KE-DBA-AUXW | datasheet | SG ['es'] | OK |
| 58 | `ke-dm3010r-kit-161721-es` | corroborate noop | KE-DM3010R-KIT / KE-DM3010R-KIT | datasheet | SG ['es'] | OK |
| 59 | `nc-mc-0-g-161721-es` | corroborate noop | NC-MC-0-G / NC-MC-0-G | datasheet | ML ['en', 'es'] | OK |

### Filas anotadas (borderline / defecto)

- **MADT609** — DEFECTO (eje language, fill-MULTI): doc NOTIFIER "TABLA DE APROXIMACIONES A GAS PATRON" 100% redactado en ES (prosa/cabeceras/leyendas/clasificacion); el unico ingles son nombres quimicos de la tabla (Diethyl ether, Methylene chloride...). s83=[en,es] -> el fill escribiria "en" espurio en un campo NULL. pm=NAP-100 y doc_type=otro CORRECTOS.
- **UCIP MODBUS AM8200 V5.1** — LIMPIO (en defendible): prosa ES + strings ingleses GENUINOS (Firmware Loader, "Loader file: C:\...", FULL DUPLEX). pm AM8200 corroborado, doc_type=configuracion correcto.
- **MFDT170** — LIMPIO: bilingue EN/ES verificado (marcadores de prosa inglesa: "the following", "Refer to", "PLEASE", "must be"). El head mostraba ES; el cuerpo tiene EN.

## Spot-check de calibración original (materializado desde `_cal.jsonl`)

La corrida de calibración (`--judge --calibrate --limit 20`) juzgó **20** filas WEAK estratificadas. De ellas, **5 NO salieron AUTO_CLEAN** (4 CONFLICT + 1 WEAK) — el juez cazó divergencias reales de contenido, lo que validó que el instrumento v1 distinguía señal. Esas 5 (cuáles y qué falló):

| source_file | veredicto juez | product_model_call | qué falló (motivo LLM) |
|---|---|---|---|
| `04-4001-501-2009-12_r012_modulaser_en_54` | CONFLICT | ModuLaser | El documento describe específicamente el detector ModuLaser (aspiración modular), mientras que s83 p |
| `15090SP` | CONFLICT | 15090SP | El contenido menciona 'Terminal de Informe de Red' (Network Report Terminal), identificando el model |
| `15888SP` | WEAK | unknown | Contenido genérico de precauciones e instalación sin identificar modelo específico. Etiqueta goberna |
| `D 1147-1 BRH Notifier` | CONFLICT | B501AP | El contenido menciona explícitamente 'B501' (modelo B501AP gobernado en DB), mientras que s83 propon |
| `D 1148-1 BRS Notifier` | CONFLICT | B501AP | El contenido menciona explícitamente 'NFXI-BSF-WCS' en secciones técnicas (conexiones, dimensiones), |

Las otras 15 salieron AUTO_CLEAN. Nota (finding 7, JUEZ-FABRICA): en el re-gating v2 el juez es SOLO triage de conflictos (dirección segura) — NO otorga auto-apply; la calibración se conserva como evidencia de que la señal CONFLICT del juez es real (p.ej. 15090SP, D1147/D1148 BRH/BRS).
