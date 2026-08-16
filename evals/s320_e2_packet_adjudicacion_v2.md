# s320 E2 — Packet de ADJUDICACIÓN **v2 (encogido)** · 20260815T163607Z

<!-- s324-estado:inicio -->
> ## 🟡 ESTADO s324 (2026-08-16 20:19Z)
> El bloque de altas seguras y los lotes por riesgo esperan tu sí. El catálogo gobernado cambió en s324 (+13 productos, +7 confirmaciones, +3 paraguas, −2 etiquetas), así que el snapshot candidato se **re-derivó** (`s320_e2_snapshot_derivado.py`) y el split por riesgo se refrescó (`s322f_e2_altas_split_v1.json`): **1.326 altas = 596 en bloque + 730 individuales** (antes 1.235 = 562 + 669; las +91 son en su mayoría lo confirmado/dado de alta hoy). Gates: la variante **conservadora** (equivalencia con el snapshot vivo) **PASS** (0 pérdidas, voz idéntica); la completa sigue con las mismas 6 pérdidas conocidas de golds (VESDA-E-VEP, CCD-103, NFS-Supra, 40/40, MAD-472 — bajas que este packet adjudica). Los conteos del cuerpo de este fichero son del 15-ago; el bloque/lotes se regenerarán al aplicar tu sí.
<!-- s324-estado:fin -->










**SUPERSEDE a `evals/s320_e2_packet_adjudicacion_v1.md`.**
Aquel packet listaba **1235 altas** del detector en 25 lotes de 50, todas con el mismo
peso. Una pasada hermana las ha refrescado contra el estado de HOY (catálogo `b74d92c`,
1667 términos resolubles, 1068 docs activos, 26215 chunks leídos) y las ha separado por RIESGO
de contaminación del detector, no por orden alfabético.

> ### De **1235 casillas** → **20 decisiones**
> - **1 sí en bloque** cubre **562 altas SEGURAS** (§0).
> - El residuo (**669**) va en **19 lotes por regla de riesgo** (§1): puedes asentir por
>   lote, o bajar fila a fila al recibo — cada término está listado aquí.
> - **4 obsoletas** (§2) se cayeron solas. No decides nada.

> **Cuenta honesta de casillas** (la escribe el verificador adversarial, no el optimismo del autor): este fichero imprime **94 casillas `- [ ]`** en total — §0.A: 44 · §0.B: 11 · §1.0: 20 · §1.1: 19. Las de §0 están ahí para que PUEDAS bajar a grano fino y desmarcar lo que quieras, no porque haya que marcarlas una a una: el «sí en bloque» las cubre todas de golpe. Si solo asientes a los bloques, tu trabajo real son las decisiones del titular.

**NADA APLICADO.** Ni catálogo (`data/catalog/*.jsonl`), ni Supabase, ni el
snapshot del detector (`data/model_catalog.json`). Todo lo de aquí es PROPUESTA:
marca ✓/✗ y se aplica después por la puerta gobernada, con recibo.

> ⚠ **Aviso de drift entre el encargo y los recibos** (no se ha corregido nada,
> se declara):
> - DRIFT en candidates · bloque: esperado 50, en el recibo 49
> - DRIFT en candidates · individual: esperado 83, en el recibo 84
> - DRIFT en confirmar · bloque: esperado 327, en el recibo 326
> - DRIFT en confirmar · individual: esperado 32, en el recibo 33

**Por qué el riesgo importa aquí y no en los otros packets** — el patrón del detector es \b(core)(?!\d) sin \b de cierre y _base_aliases() ensancha solo: un término corto o común contamina TODAS las consultas (caso FUEGO)

**Qué compra realmente este sí** (del recibo, sin adornar): 518/562 filas del bloque tienen chunk_count=0 hoy. all_models() ordena por chunk_count desc y el hint de Whisper está capado a ~1000 chars, así que estas altas NO llegan al dictado: mejoran la query ESCRITA (y el imatch posterior), no la transcripción de voz.

---

## SECCIÓN 0 — Aplicables EN BLOQUE si asientes (562)

Regla SEGURO: mezcla letras+dígitos, >=5 caracteres útiles, sin palabra común/jerga, no es norma ni certificado, es un CÓDIGO (<=4 tokens, <=24 chars, sin conectores), no colisiona con el snapshot vivo ni genera un alias-base ancho

Vías de resolución en el catálogo gobernado: exact=376, alias=185, paraguas=1

### §0.A — Con presencia en el corpus HOY (44) — las que más pesan

Estas sí mueven el `all_models()` ordenado por `chunk_count` y pueden llegar al hint
de Whisper. Una línea por alta.

- [ ] `IBOX-BAC-NID3000` · vía exact · **85 chunks** (packet decía 0) · ids `notifier:ibox-bac-nid3000`
- [ ] `IBOX-MBS-NID3000` · vía exact · **79 chunks** (packet decía 0) · ids `notifier:ibox-mbs-nid3000`
- [ ] `CPU-5000` · vía exact · **50 chunks** (packet decía 50) · ids `notifier:cpu-5000`
- [ ] `DH500ACDC-E` · vía exact · **46 chunks** (packet decía 0) · ids `systemsensor:dh500acdc-e`
- [ ] `NRX-SMT3` · vía exact · **19 chunks** (packet decía 0) · ids `notifier:nrx-smt3`
- [ ] `NRX-M711` · vía exact · **15 chunks** (packet decía 0) · ids `notifier:nrx-m711`
- [ ] `SD-851TE` · vía exact · **13 chunks** (packet decía 13) · ids `notifier:sd-851te`
- [ ] `SDX-751EM` · vía exact · **13 chunks** (packet decía 0) · ids `notifier:sdx-751em`
- [ ] `CR-6EA` · vía exact · **12 chunks** (packet decía 0) · ids `systemsensor:cr-6ea`
- [ ] `SENTOX-4` · vía exact · **12 chunks** (packet decía 12) · ids `notifier:sentox-4`
- [ ] `SGFI200-S` · vía exact · **12 chunks** (packet decía 12) · ids `argus:sgfi200-s`
- [ ] `IM-10EA` · vía exact · **11 chunks** (packet decía 0) · ids `systemsensor:im-10ea`
- [ ] `M701E-240` · vía exact · **10 chunks** (packet decía 0) · ids `notifier:m701e-240`
- [ ] `M710-CZR` · vía exact · **10 chunks** (packet decía 0) · ids `notifier:m710-czr`
- [ ] `NFXI-MM10` · vía exact · **10 chunks** (packet decía 10) · ids `notifier:nfxi-mm10`
- [ ] `PIBV2` · vía exact · **10 chunks** (packet decía 10) · ids `systemsensor:pibv2`
- [ ] `FDX-551REM` · vía exact · **9 chunks** (packet decía 9) · ids `notifier:fdx-551rem`
- [ ] `M701E` · vía exact · **9 chunks** (packet decía 0) · ids `notifier:m701e`
- [ ] `NFXI-RM6` · vía exact · **9 chunks** (packet decía 9) · ids `notifier:nfxi-rm6`
- [ ] `1151EIS` · vía exact · **8 chunks** (packet decía 8) · ids `systemsensor:1151eis`
- [ ] `FDX-551EM` · vía exact · **8 chunks** (packet decía 8) · ids `notifier:fdx-551em`
- [ ] `FDX-551HTEM` · vía exact · **8 chunks** (packet decía 8) · ids `notifier:fdx-551htem`
- [ ] `5451EIS` · vía exact · **7 chunks** (packet decía 7) · ids `systemsensor:5451eis`
- [ ] `MI-D240CMOE` · vía exact · **7 chunks** (packet decía 7) · ids `morley:mi-d240cmoe`
- [ ] `PA-RZ1` · vía exact · **7 chunks** (packet decía 7) · ids `morley:pa-rz1`
- [ ] `KE-AS3110W` · vía exact · **6 chunks** (packet decía 6) · ids `kidde:ke-as3110w`
- [ ] `KE-AS3111W` · vía exact · **6 chunks** (packet decía 6) · ids `kidde:ke-as3111w`
- [ ] `MI-CR6` · vía exact · **6 chunks** (packet decía 6) · ids `morley:mi-cr6`
- [ ] `W*A-*C-I02` · vía exact · **6 chunks** (packet decía 0) · ids `notifier:wa-c-i02`
- [ ] `KE-AS3010R` · vía exact · **5 chunks** (packet decía 5) · ids `kidde:ke-as3010r`
- [ ] `KE-AS3110R` · vía exact · **5 chunks** (packet decía 5) · ids `kidde:ke-as3110r`
- [ ] `KE-AS3111R` · vía exact · **5 chunks** (packet decía 5) · ids `kidde:ke-as3111r`
- [ ] `KE-AS3010W` · vía exact · **4 chunks** (packet decía 4) · ids `kidde:ke-as3010w`
- [ ] `KE-AS3011R` · vía exact · **4 chunks** (packet decía 4) · ids `kidde:ke-as3011r`
- [ ] `KE-AS3011W` · vía exact · **4 chunks** (packet decía 4) · ids `kidde:ke-as3011w`
- [ ] `NFX-MM1M` · vía exact · **4 chunks** (packet decía 4) · ids `notifier:nfx-mm1m`
- [ ] `ZMX-1E` · vía exact · **4 chunks** (packet decía 4) · ids `notifier:zmx-1e`
- [ ] `KE-DB3010B` · vía exact · **3 chunks** (packet decía 3) · ids `kidde:ke-db3010b`
- [ ] `M700X` · vía exact · **3 chunks** (packet decía 3) · ids `notifier:m700x`
- [ ] `MS3-RS485` · vía exact · **3 chunks** (packet decía 3) · ids `fidegas:ms3-rs485`
- [ ] `NSRE24` · vía exact · **3 chunks** (packet decía 3) · ids `ada:nsre24`
- [ ] `Z728.H` · vía exact · **3 chunks** (packet decía 0) · ids `pepperl-fuchs:z728.h`
- [ ] `MPS-24AE` · vía exact · **1 chunk** (packet decía 0) · ids `notifier:mps-24ae`
- [ ] `TED-151-CL` · vía exact · **1 chunk** (packet decía 1) · ids `detnov:ted-151-cl` · alias-base que genera: `TED-151`

### §0.B — Sin chunks hoy (518) — mejoran la query escrita, no el dictado

`chunk_count_hoy = 0` en las 518: no llegan al hint de Whisper (capado a ~1000 chars),
pero sí al `imatch` posterior sobre texto escrito. Riesgo de contaminación: **ninguna**
cumple la regla SEGURO por accidente — todas mezclan letras+dígitos, ≥5 chars útiles y
no generan alias-base ancho. En lotes por vía; **cada término listado** (Ctrl-F).

- [ ] vía **exact** — lote 1/6 (60 altas)
      `140KIT160` · `1470 SA` · `1555 SS` · `2X-AE1` · `2X-AE2` · `2X-AE2-P` · `2X-AF1-FB` · `2X-AF1-SCFB`
      `2X-AF1-SCFB-S` · `2X-AF2-FB-PRT-P` · `2X-AF2-P` · `2X-AF2-PRT` · `2X-AF2-PRT-P` · `2X-AF2-S`
      `2X-AF2-SCFB-P` · `2X-AFR` · `2X-AFR-FB` · `2X-AFR-FB-S` · `2X-AFR-S` · `4000TA` · `40KIT80` · `4XRFI-KIT`
      `5055 SS` · `5555 SS` · `6200R` · `6424A` · `6500RS` · `70KIT140` · `80KIT100` · `AA-100` · `AA-100E`
      `AA-120` · `AA-120E` · `AA-30E` · `ACM-16AT` · `ACM-32A` · `ACM-8R` · `AD105` · `AD105N` · `AD105P`
      `AD105SS` · `AD185N` · `AD185SS` · `AD218` · `AD218SS` · `AD68N` · `AD68P` · `AD68SS` · `AD88N` · `AD88P`
      `AD88SS` · `ADP-N3E` · `ADW 535-1 ATEX` · `ADW 535-2` · `AEM-16AT` · `AEM-32A` · `AIS-GALD1` · `AIS-GALS1`
      `AM-8200BB` · `AM2-AL`
- [ ] vía **exact** — lote 2/6 (60 altas)
      `AM82-2S2C` · `AM82-BST-C` · `AMB 32` · `APS-6R` · `AS2363W` · `AS2364W` · `AS2366` · `AS2367` · `ASC2366`
      `ASC2367` · `ASC2367W` · `ASD 533-1` · `ASD 535-1` · `ASD 535-2` · `ASD 535-3` · `ASD 535-4` · `ASW2367W`
      `AVPS-24` · `AVPS-24E` · `B312NL` · `B312RL` · `B324RL` · `B401DG` · `B401DGR` · `B401DGR1000` · `B401DGSD`
      `B401R` · `B401R1000` · `B401RSD` · `B401SD` · `B501DG` · `B501RF` · `B524HTR` · `B524IEFT-1` · `BA-2250`
      `BA-2500` · `BE-5000` · `BE-5000AA` · `BE-600A` · `BE3000` · `BGX-101L` · `BPS-600` · `BREL12L` · `BREL12NL`
      `BREL24L` · `CAB-IDA1` · `CAB-IDB2` · `CAD-150-1` · `CAD-150-2` · `CAD-150-2-MB` · `CAD-150-4`
      `CAD-150-8-PLUS` · `CAD-201-PLUS` · `CAD-201-Z` · `CAD-201-ZPLUS` · `CAD-250-P` · `CFA457` · `CHG-120`
      `CHS-4L` · `CHS-4M`
- [ ] vía **exact** — lote 3/6 (60 altas)
      `CPU-2020` · `CPU-300` · `CPU-400` · `CRP2000` · `DGD-620` · `DSE3-23 HQ` · `DSE3-23 HW` · `DX1e-40M`
      `ECO1004T` · `ECO1005T` · `EMA24ALR` · `EMA24ALW` · `EPS10-1` · `EPS10-2` · `EPS120-1` · `EPS120-2`
      `EPS40-1` · `EPS40-2` · `ESS-2Plus` · `FA457` · `FD-851HTE` · `FD-851RE` · `FDKM2100X` · `FFT-7S`
      `FKAC2100R` · `FL0111E-HS` · `FL0112E-HS` · `FL0122E-HS` · `FL2011EI-HS` · `FL2012EI-HS` · `FL2022EI-HS`
      `FLX-020` · `FRM2100` · `FS-1200` · `Fireray 100R` · `HEF20RL` · `HOP-402-100` · `HOP-404-100`
      `HOP-405-100` · `HOP-406-100` · `HOP-407-200` · `HOP-431-100` · `HOP-433-100` · `HOP-608-200`
      `HOP-631-100` · `ICA-4L` · `ICM-4CC` · `ID1002` · `ID1004` · `ID3004-001` · `ID3008-001` · `IDR-2A`
      `IDR-2P` · `IDR-6A` · `INSPIRE E15` · `KE-DM3110R` · `KE-IO3001` · `KE-IO3044` · `LCR3 CO` · `LCR3 VB`
- [ ] vía **exact** — lote 4/6 (60 altas)
      `LDM-32` · `LDM-E32` · `LDM-R32` · `LIB-200` · `LIB-200A` · `LIB-400` · `LIB-8200G` · `LIB-8200N`
      `LIB3000M` · `LIB3000S` · `LIB600` · `LPB-700T` · `LT-ACC-ERO-16` · `LT-ACC-ETS-16` · `LT-ACC-ETS-5`
      `LT-ACC-ETS-8` · `LT-ACC-POE-24` · `LT-ACC-POE-4` · `LT-ACC-PWR-12` · `LT-ACC-PWR-48` · `LT-SEN-M3`
      `LT-SEN-R3` · `M700KAC` · `M700KACI` · `M701-240` · `M701-240-DIN` · `M701-240-KO` · `M710E` · `M720E`
      `M721E` · `MAD-450-I` · `MAD-450-IW` · `MAD-451-I` · `MCM 35` · `MCP1A` · `MCP1B` · `MCP2A` · `MCP2B`
      `MCP4A` · `MCP5A-P05` · `MCP5A-P06` · `MI-D2ICMO` · `MI-D2ICMOE` · `MI-DMM2I` · `MI-DMM2IE` · `MI-FL2011EI`
      `MI-FL2012EI` · `MI-FL2022EI` · `MI-FLX-020` · `MMX-101` · `MPS-24` · `MPS-24A` · `MPS-24B` · `MPS-24BE`
      `MPS-24BPCA` · `MPS-400` · `MPS-8K` · `MPS50` · `MTC-4Q2` · `NAM-232F`
- [ ] vía **exact** — lote 5/6 (60 altas)
      `NAM-232W` · `NCO-100` · `NEO4250E` · `NEO4500E` · `NEO4500LE` · `NEO8060` · `NEO8250E` · `NFG-16REL`
      `NFX-SMT2` · `NFXI-ASD11-HS` · `NFXI-ASD12-HS` · `NFXI-ASD22-HS` · `NFXI-FLX-010` · `NFXI-FLX-020`
      `NFXI-SMT2` · `NFXI-SMT3` · `NIB-96` · `NR45-24` · `ONE-LOOP04` · `ONE-LOOP10` · `PARK 5000` · `PF24V`
      `PRL-D-1` · `PRL-D-2` · `PRL-P2P` · `PY X-M-10` · `PY X-MA-05` · `PY X-MA-10` · `REFL20` · `REFL30`
      `REFL40` · `REFL50` · `REFL60` · `RIM 35` · `RIM 36` · `RPT-485WF` · `S1869ND` · `S290O2GP` · `S300SAT`
      `S313HSAP` · `S319HSAP` · `SDX-751` · `SIB-2048` · `SIB-2S` · `SIB5485` · `SIM 35` · `SK-2SP` · `SLM 35`
      `SMART3G-C3` · `SMART3G-D3` · `SSD 532-1` · `SSD 532-2` · `SSD 532-3` · `SSD 535-1` · `SSD 535-2`
      `SSD 535-3` · `TCS-3000` · `TF-BE3000` · `TFS-3000` · `TG-IP-10`
- [ ] vía **exact** — lote 6/6 (32 altas)
      `TG-IP-100` · `UZC-256` · `VEA-040-A00` · `VEA-040-A10` · `VEP-A10-P` · `VER-A40-40-STX` · `VES-A00-P`
      `VES-A10-P` · `VEU-A00` · `VEU-A10` · `VLF-250` · `VLF-500` · `VLI-885` · `VP-100` · `VP-200` · `VRAM-1`
      `VSN12-2Plus` · `VSN12-LT` · `VSN2-LT` · `VSN4-LT` · `VSN8-LT` · `VTCC-1` · `VTCC-2` · `WW4001` · `XLM 35`
      `XPM-8L` · `XRAM-1` · `Y72221` · `ZX10Se` · `ZX1Se` · `ZX2Se` · `ZX5Se`
- [ ] vía **alias** — lote 1/4 (60 altas)
      `10-5106-501-55NC-05` · `2ESna` · `2IOni` · `30320-004p` · `4ESna` · `4IOni` · `5251HTME` · `6500S`
      `8100E` · `ADP-N3E-U` · `AM82-2S2C-A` · `AM82-2S2C-B` · `ASAT-1u` · `ASD 532-1` · `AW28PCa` · `AW28PCb`
      `AW28TC` · `AW70L0` · `AW70LO` · `B501AP-BK` · `B501AP-IV` · `B501BHT` · `B524EFT-1` · `BRH-PC-I05`
      `BRS-PC-I05` · `C159-14-T02` · `CPU-AM-8200` · `CPU-AM8200BB` · `D500-08-00` · `DH500ACDC` · `DH500ACDCs`
      `DIA 6M-S` · `DOP-ASP015` · `DOP-ASP016` · `DOP-ASP017` · `DOP-IOD076` · `DOP-IOD077` · `DOP-IOD078`
      `DOP-IOD082` · `DOP-IOD083` · `DOP-IOD084` · `DOP-IRF016` · `DOP-IRF017` · `DOP-IRF020` · `DOP-IRF026`
      `DoC-SG08` · `ECO1000BREL12L` · `ECO1000BREL12NL` · `ECO1000BREL24L` · `EPSA10-1` · `EPSA10-2` · `EPSA120-1`
      `EPSA120-2` · `EPSA40-1` · `EPSA40-2` · `ESS-RP1r-Supra` · `EXP-060` · `Expansion StaX 1`
      `Expansion StaX 2` · `F100R`
- [ ] vía **alias** — lote 2/4 (60 altas)
      `FD2000D` · `FIRERAY 2000` · `FL0111E` · `FL0112E` · `FL0122E` · `FL2011EI` · `FL2012EI` · `FL2022EI`
      `G217100` · `G218006` · `HFA20RL` · `HOP-4O4-100` · `HSSD-2` · `I56-3674-000` · `INSPIRE E10 65`
      `KE-DM3010` · `KE-DM3110` · `KFDO-CS-Ex 1.51P` · `L20-SG1IS-0001` · `L20-SG2IS-0001` · `L20-SG3IS-0001`
      `L20-SGCP1IS-0001` · `L20-SGCWE-0001` · `L20-SGFI2S-0001` · `L20-SGMCB2X-0001` · `L20-SGMI2X-0001`
      `LCR3 NO2` · `LDA RCD-21R` · `LDAA1S02` · `LDAAT25S01` · `LDAAT60S02` · `LDAONELOOP04S0` · `LDAONELOOP04S01`
      `LDAONELOOP10S01` · `LDARCD21RS03` · `LDATFL2S01` · `LDAZES22S02` · `M200.1-UDS-ENG` · `M500RFE`
      `MA-DT-765` · `MCP1A-R470SF` · `MCP1A-X` · `MCP1B-X` · `MCP2A-X` · `MCP2B-X` · `MCP4A-X` · `MCP5A-RP05SG`
      `MI-DT-015` · `MICRA25` · `MN-DT-110` · `MN-DT-521` · `MPS-24BRB` · `MS3-RS485 V1` · `MT2620E` · `MT876`
      `Micra100` · `Moxa Nport 5110` · `Moxa Nport 5210` · `Multisystem++S1` · `NFG-16R`
- [ ] vía **alias** — lote 3/4 (60 altas)
      `NFXI-ASD11` · `NFXI-ASD12` · `NFXI-ASD22` · `PCM602IDI` · `PCM616` · `REFLEX 20` · `REFLEX 30`
      `REFLEX 40` · `REFLEX 50` · `REFLEX 60` · `RPT-485WFs` · `RPT-485Ws` · `S1604VB` · `S1606CO` · `S300STU`
      `SETOX-4` · `SG1910CPR` · `SGMCB2` · `SLP-001` · `SMK400` · `SPNK-754431-120` · `SSD 532` · `SSD 535`
      `Stratos 2` · `Stratos Micra 100` · `TCF-142-S-SC` · `TCF-142-S-ST` · `TDS-SCP1IS-0002` · `TDS-SGFI200-X`
      `TDS-SGMCB2` · `TDS-SGMI2` · `TFL2S01` · `TUL500` · `TX1TR` · `VAP1S0x` · `VCC-63` · `VES-A10`
      `VLF-250-00` · `VLF-250-01` · `VLF-250-02` · `VLF-250-03` · `VLF-250-04` · `VLF-500-00` · `VLF-500-01`
      `VLF-500-02` · `VLF-500-03` · `VLF-500-04` · `VROM-101` · `VROM-109` · `VSN 2-4-8-12` · `VSN LT 12`
      `VSN LT 2` · `VSN LT 4` · `VSN LT 8` · `VSN-100` · `VSN-200` · `VSN-CRA-GSM v2.0.5` · `VSN-Plus2`
      `VSN-RP1r-PLUS` · `WRA-PC-I02`
- [ ] vía **alias** — lote 4/4 (5 altas)
      `WRA-RC-I02` · `WWA-PC-I02` · `WWA-RC-I02` · `ZES22S02` · `iBox-BACnet-NID3000`
- [ ] vía **paraguas** — lote 1/1 (1 alta)
      `ZX2e/ZX5e`

---

## SECCIÓN 1 — Una a una (669), agrupadas en lotes por regla de riesgo

Clases: NO-PRODUCTO=3, RIESGO=666

**Los 20 más peligrosos** (medidos: menciones reales en el contenido × documentos
distintos). Si uno de éstos entra mal, contamina TODAS las consultas — es la clase
del caso FUEGO. Van con casilla propia:

### §1.0 — Top peligrosos (20) — decisión individual

- [ ] `B501` · reglas: demasiado-corto · **134 menciones** en 70 docs · vía exact · ids `systemsensor:b501`
      alias-base que generaría: ninguno
- [ ] `S6` · reglas: demasiado-corto · **89 menciones** en 59 docs · vía exact · ids `notifier:s6`
      alias-base que generaría: ninguno
- [ ] `MMX-1` · reglas: demasiado-corto · **172 menciones** en 52 docs · vía exact · ids `notifier:mmx-1`
      alias-base que generaría: ninguno
- [ ] `CMX-2` · reglas: demasiado-corto · **78 menciones** en 36 docs · vía exact · ids `notifier:cmx-2`
      alias-base que generaría: ninguno
- [ ] `A10` · reglas: demasiado-corto · **453 menciones** en 33 docs · vía alias · ids `xtralis:veu-a10`
      alias-base que generaría: ninguno
- [ ] `M710` · reglas: demasiado-corto · **76 menciones** en 32 docs · vía exact · ids `notifier:m710`
      alias-base que generaría: ninguno
- [ ] `-2A` · reglas: demasiado-corto · **96 menciones** en 29 docs · vía alias · ids `notifier:idr-2a`
      alias-base que generaría: ninguno
- [ ] `MMX-2` · reglas: demasiado-corto · **74 menciones** en 26 docs · vía exact · ids `notifier:mmx-2`
      alias-base que generaría: ninguno
- [ ] `M701` · reglas: demasiado-corto · **56 menciones** en 25 docs · vía exact · ids `notifier:m701`
      alias-base que generaría: ninguno
- [ ] `-2P` · reglas: demasiado-corto · **62 menciones** en 20 docs · vía alias · ids `notifier:idr-2p`
      alias-base que generaría: ninguno
- [ ] `M721` · reglas: demasiado-corto · **50 menciones** en 20 docs · vía exact · ids `notifier:m721`
      alias-base que generaría: ninguno
- [ ] `AMG-1` · reglas: demasiado-corto · **161 menciones** en 18 docs · vía exact · ids `notifier:amg-1`
      alias-base que generaría: ninguno
- [ ] `ISO-X` · reglas: solo-letras-sin-digitos, demasiado-corto · **68 menciones** en 18 docs · vía exact · ids `notifier:iso-x`
      alias-base que generaría: ninguno
- [ ] `B401` · reglas: demasiado-corto · **33 menciones** en 17 docs · vía exact · ids `systemsensor:b401`
      alias-base que generaría: ninguno
- [ ] `ICM-4` · reglas: demasiado-corto · **94 menciones** en 16 docs · vía exact · ids `notifier:icm-4`
      alias-base que generaría: ninguno
- [ ] `ZXe` · reglas: solo-letras-sin-digitos, demasiado-corto · **134 menciones** en 15 docs · vía paraguas · ids `morley:zx1e`, `morley:zx2e`, `morley:zx5e`
      alias-base que generaría: ninguno
- [ ] `CHS-4` · reglas: demasiado-corto · **112 menciones** en 15 docs · vía exact · ids `notifier:chs-4`
      alias-base que generaría: ninguno
- [ ] `M720` · reglas: demasiado-corto · **28 menciones** en 15 docs · vía exact · ids `notifier:m720`
      alias-base que generaría: ninguno
- [ ] `VSN2` · reglas: demasiado-corto, colision-con-alias-base-vivo · **21 menciones** en 13 docs · vía exact · ids `morley:vsn2`
      alias-base que generaría: ninguno
- [ ] `FFT-7` · reglas: demasiado-corto · **97 menciones** en 12 docs · vía exact · ids `notifier:fft-7`
      alias-base que generaría: ninguno

> Los 20 de arriba **también** aparecen en su lote de regla abajo (para que cada lote
> esté completo). No los cuentes dos veces: el total de la §1 es 669.

### §1.1 — Lotes por regla (669 altas)

Cada alta se asigna a **su primera regla** (el recibo trae todas las reglas de cada
fila). Formato: `MODELO` o `MODELO(chunks)` si tiene presencia en corpus.

- [ ] regla **contiene-palabra-generica** — 267 altas
      `1 tuberia independiente FAAST FLEX direccionable (Morley)` · `1 tubería independiente FAAST FLEX`
      `1 tubería independiente FAAST FLEX direccionable`
      `1 tubería independiente FAAST FLEX direccionable (Notifier)`
      `1151EIS Intrinsically-safe Plug-in Ionization Smoke Detector` · `1151EIS ion detector`
      `124-429 LOOP SPLITTER PCB` · `140KIT160 Long Range Reflector`
      `2 tuberias independientes FAAST FLEX direccionable (Morley)` · `2 tuberías independientes FAAST FLEX`
      `2 tuberías independientes FAAST FLEX direccionable`
      `2 tuberías independientes FAAST FLEX direccionable (Notifier)`
      `2000 Series Addressable Loop Powered Sounder-Beacons` · `2010−2-PAK-RMSDK Panel Activation Key (PAK)`
      `2010−2A-PAK-HPL Panel Activation Key` · `2010−2A-PAK-HPL Panel Activation Key (PAK)`
      `2010−2A-PAK-HPL Panel Etkinleştirme Anahtarı` · `2X-LB Loop Expansion Board` · `3247-029 LOOP SPLITTER PCB`
      `4-relay boards` · `5451EIS detector` · `5451EIS detectors` · `5451EIS heat detector`
      `ADW 535 con dos tubos sensores` · `ADW 535 con un tubo sensor` · `AM2BRCA (serigrafia placa)`
      `AM82BCA (serigrafia placa)` · `ART 535 reference temperature-sensor` · `AS2300 Series`
      `Addressable Detector Base Sounder Strobe EN54-23 C Category`
      `Alarmline II Digital Sensor Cable – 105°C (221°F) Nylon`
      `Alarmline II Digital Sensor Cable – 105°C (221°F) PVC`
      `Alarmline II Digital Sensor Cable – 105°C (221°F) Polypropylene`
      `Alarmline II Digital Sensor Cable – 105°C (221°F) Stainless Steel over PVC`
      `Alarmline II Digital Sensor Cable – 185°C (365°F) Nylon`
      `Alarmline II Digital Sensor Cable – 185°C (365°F) Stainless steel over Nylon`
      `Alarmline II Digital Sensor Cable – 218°C (424°F) Silicone`
      `Alarmline II Digital Sensor Cable – 218°C (424°F) Stainless steel over Silicone`
      `Alarmline II Digital Sensor Cable – 68°C (155°F) Nylon`
      `Alarmline II Digital Sensor Cable – 68°C (155°F) PVC`
      `Alarmline II Digital Sensor Cable – 68°C (155°F) Polypropylene`
      `Alarmline II Digital Sensor Cable – 68°C (155°F) Stainless Steel over PVC`
      `Alarmline II Digital Sensor Cable – 88°C (190°F) Nylon`
      `Alarmline II Digital Sensor Cable – 88°C (190°F) PVC`
      `Alarmline II Digital Sensor Cable – 88°C (190°F) Polypropylene`
      `Alarmline II Digital Sensor Cable – 88°C (190°F) Stainless Steel over PVC` · `Alimentación, 12 V CC`
      `Alimentación, 12 V CC (LT-ACC-PWR-12)` · `Alimentación, 48 V CC` · `Alimentación, 48 V CC (LT-ACC-PWR-48)`
      `Ampliación LIB600` · `Aux. relay modules VSN-4REL` · `B500 bases` · `B501 STANDARD BASE`
      `B524HTR HEATED BASE` · `CARCASA DEL DETECTOR ANALÓGICO DE HUMO POR CONDUCTO DE AIRE DH500`
      `CHS-4L de bajo perfil` · `CR-6EA Six Relay Control Module` · `CR-6EA module` · `Canal dual (FLX-020)`
      `Canal único (FLX-010)` · `Carcasas de Detectores de Conducto de Aire DH500` · `Cargador NR45-24`
      `Cargador Remoto de Batería CHG-120` · `Centro de Control de Audio VCC-1`
      `Centro de Control de Audio VCC-2` · `Centro de Control de Audio VTCC-1`
      `Centro de Control de Telefonía TCC-1` · `Chasis CHS-4` · `Chasis CHS-4L`
      `Codificador Universal de Zona UZC-256` · `Concentrador, PoE, Gen 3`
      `Concentrador, energía directa, Gen 3` · `Conector de llamadas remoto RPJ-1`
      `Conmutador Ethernet, 16 puertos` · `Conmutador Ethernet, 16 puertos (LT-ACC-ETS-16)`
      `Conmutador Ethernet, 5 puertos` · `Conmutador Ethernet, 5 puertos (LT-ACC-ETS-5)`
      `Conmutador Ethernet, 8 puertos` · `Conmutador Ethernet, 8 puertos (LT-ACC-ETS-8)`
      `Conmutador Ethernet, PoE, 24 puertos` · `Conmutador Ethernet, PoE, 24 puertos (LT-ACC-POE-24)`
      `Conmutador Ethernet, PoE, 4 puertos` · `Conmutador Ethernet, PoE, 4 puertos (LT-ACC-POE-4)`
      `Conmutador PoE de 24 puertos` · `Controlador Li-ion Tamer GEN 3` · `Controlador, GEN 3`
      `Controller, GEN 3` · `Convertidor de alimentación (CFA457)` · `D2E Duct Smoke Detector` · `D2E model`
      `DH500 Air Duct Detector Housings` · `DH500 Intelligent Air Duct Smoke Detector Housing`
      `DH500 duct detector` · `Doc. M-040.1-NFG8-PORT` · `ECO1003 PHOTO-ELECTRONIC SENSORS`
      `EQUIPO DE PRUEBA SATÉLITE S300SAT` · `El Cargador de Batería CHG-120` · `El Detector VESDA-E VEU-A00`
      `El Módulo XPC-8` · `El Módulo XPM-8` · `El Módulo XPM-8L` · `El Módulo XPR-8` · `Equipo Básico (BE-5000)`
      `Equipo Básico-5000AA` · `Equipo Satelite S300SAT` · `Expansora con 6 circuitos de Salida S6`
      `Expansora de sirena S6` · `FAAST FLEX direccionable de 1 canal` · `FAAST FLEX direccionable de 1 tuberia`
      `FAAST FLEX direccionable de 2 canales` · `FAAST FLEX direccionable de 2 tuberias` · `FACP MODEL DX1e-40M`
      `FS-1100 Triple IR3 Flame Simulator` · `Flame Simulator Model FS1200` · `Flame Simulators FS-1300`
      `ID del módulo de red²Net` · `ID-200 Central Analógica` · `IM-10EA Ten Input Monitor Module`
      `IS-mA1 Sounder` · `IS-mA1 minialarm sounder` · `IS-mA1 sounders`
      `IU2055NC Conventional Zone Monitor Unit` · `IU2055NC Conventional Zone Monitor Unit Installation Sheet`
      `Interface de terminales universal MTC-4Q2` · `Interfaz analógico vía radio FLG2100` · `LAZO OPAL X2`
      `Line type heat detector SecuriSens® ADW 535-1 ATEX` · `M700X Short Circuit Isolator Module`
      `M701E Single Output Module with Supervised Output` · `M701E Single Output Module with Unsupervised Output`
      `MCP5A models` · `MI-CR6 Module` · `MI-CR6 Six Relay Control Module` · `MI-IM10 Módulo Monitor`
      `MI-IM10 Módulo Monitor con diez circuitos de entrada` · `MI-IM10 Ten Input Monitor Module`
      `MI-MM3E-S2 Monitor Module` · `MI-SC6 Six Supervised Control Module` · `MMX-10. Tarjeta de 10 entradas`
      `MMX-102E Monitor Module` · `MMX-102E Stand Alone Micro Module` · `MODEL EPS10-1` · `MODEL EPS10-2`
      `MODEL LPB-620` · `MODEL SD-651E` · `MODEL SD-851E` · `Main Board AMB 32` · `Model 1151EIS`
      `Model 1151EIS detector` · `Model 5451EIS` · `Model D2E Duct Smoke Detector` · `Modelo FAAST: 8100E`
      `NAS-1u Aspirating Smoke Detector` · `NAS-1u aspirating system` · `NAS-1u detector`
      `NFXI-RM6 Six Relay Control Module` · `NFXI-RM6 module` · `OSY2 Gate Valve Supervisory Switch`
      `OSY2 Supervisory Switch` · `PCB de 2 lazos TX` · `PF24V Directional Sounder with Voice Messaging`
      `PRL-D-1 de 1 lazo` · `PRL-D-2 de 2 lazos` · `PRL-D-2 de dos lazos` · `PYRA Xenon beacons PY X-L-15`
      `PYRA Xenon beacons PY X-S-05` · `Paquete de Equipo Básico BE-5000` · `Procesador XPP-1` · `RED ID2NET`
      `RIM 36 Módulo de interfaz de relé con 5 relés` · `RZA-4X Remote Annunciator` · `Ref. kit: 020-478`
      `Ref. kit: 020-643` · `Ref. placa: 124-300` · `Ref. placa: 124-319` · `Ref.: 124-065-XXX`
      `Ref.: IBOX-BAC-NID3000` · `Reflector de largo alcance 140KIT160` · `Reflector de medio alcance 70KIT140`
      `S300SAT Satellite Relay Device` · `S300SAT Satellite Test Unit` · `S6 -Tarjeta expansora de 6 sirenas`
      `S876xx → PARA SENSORES ALIMENTADOS A 230Vca` · `S877xx → PARA SENSORES ALIMENTADOS A 12Vcc`
      `SD-651E smoke detector` · `SD-851E Optical Smoke Detector` · `SD-851TE Photo-Thermal detector`
      `SENSOR SMART 2` · `SENSOR SMART 2 PARA DETECCIÓN DE AMONIACO S317AMDP` · `SIM 35 Módulo de interfaz serial`
      `SMART 3G versión display` · `STRATOS (TM) Interface de terminales universal Versión 1.0`
      `STRATOS Interface de terminales universal Versión 1.0` · `Sensor de monitorización (LT-SEN-M3)`
      `Sensor de monitorización, Gen 3` · `Sensor de referencia (LT-SEN-R3)` · `Sensor de referencia, Gen 3`
      `Sensor de temp. ext. ART 535` · `Sensor de temperatura externo ART 535` · `Series 300 RPTU`
      `Series 300 RPTU v.1.2` · `SharpEye Flame Simulator FS-1200` · `TCD-100 Card` · `TCD-100 family`
      `TCD-100 module` · `Testifire de la serie 1000` · `Testifire de la serie 2000` · `Testifire serie 1000`
      `Testifire serie 2000` · `Transformador 4000TA` · `Transformador de Acoplamiento de Audio ACT-1`
      `Triple IR3 Flame Simulator` · `Type: ADW 535-2` · `Unidad de extinción Modelo UDS-1N`
      `VEP-A10-P (4 tuberías)` · `VES-A00-P (4 Tuberías)` · `VES-A10-P (4 Tuberías)`
      `VESDA-E VEP-A10-P smoke detector` · `VESDA-E VES-A10-P (4 Tuberías)` · `VSN-232 card`
      `VSN-232 communication card` · `VSN-4REL card`
      `WB-1 Detector Adapter Base Enclosure for Humid Environments` · `WRP Series 01` · `WRP Series 02`
      `WRP Series 11` · `Waterproof ReSet 11` · `Waterproof ReSet Call Point 01`
      `Waterproof ReSet Call Point 02` · `Waterproof ReSet Call Point 11`
      `Waterproof ReSet Call Point Series 01` · `Waterproof ReSet Call Point Series 02`
      `Waterproof ReSet Call Point Series 11` · `Waterproof ReSet Series 01` · `Waterproof ReSet Series 02`
      `Waterproof ReSet Series 11` · `XLM 35 Módulo SecuriLine`
      `aplicación de comprobación de equipos analógicos POL-1` · `cards of 4 relays` · `interfaz FLG2100`
      `long range 140 to 160m kit` · `línea SMART2` · `mid range 70 to 140m kit` · `modelo SD-651E`
      `modelo SD-851E` · `modelo canadiense 6424A` · `modelo de central CAD-250-P`
      `optional RS-232 communication card` · `protector de intemperie, referencia 777163` · `pulsador FKAC2100R`
      `referencia de PEPPER, KFDO-CS-Ex 1.51P` · `repetidores CRP2000`
      `sensor para detección de amoniaco S317AMDP` · `sensores remotos NCO-100` · `serie ID2000` · `serie ID3000`
      `serie SMART2` · `serie SMART3G` · `sistema CAD-250` · `sistema de aspiración de humos NAS 10`
      `sistema de aspiración de humos NAS 20` · `subcentral UDS-1N` · `tarjetas ISO-RS232`
      `tarjetas aisladas ISO-RS232` · `unidad de control SCU 2000`
      `unidad de monitor de zona convencional IU2055NC`
      qué significa: código + sustantivo genérico suelto (['detector']): probablemente el catálogo deba guardarlo sin la coletilla
      recomendación del recibo: **decidir una a una**

- [ ] regla **demasiado-corto** — 93 altas
      `-2A` · `-2P` · `100R` · `12-LT` · `12L` · `12NL` · `1CH` · `2-LT` · `24L` · `2CH` · `4-LT` · `4ESn`
      `4IOn` · `4XLM` · `4XMM` · `4XTM` · `4XZM` · `50R` · `8-LT` · `A10` · `AA-30` · `ACT-1` · `AD68` · `AD88`
      `AMG-1` · `ARM-4` · `AT-25` · `AT-6` · `AT6.0` · `ATG-2` · `B401` · `B501` · `CHS-4` · `CMX-2` · `CPU-2`
      `CR-6`(5) · `CRT-2` · `D2E`(19) · `DCM-4` · `DIA-6` · `DXc1` · `DXc2` · `DXc4` · `EXP 1` · `F50R` · `FFT-7`
      `FPJ-1` · `HG4` · `I.S.28` · `ICE-4` · `ICM-4` · `ICM-8` · `IZM-8` · `M701` · `M710` · `M720` · `M721`
      `MCP1....` · `MCP2....` · `MCP4....` · `MK50` · `MMX-1` · `MMX-2` · `MPM-2` · `MPS 5` · `NAS-1` · `OM-R2`
      `P-100` · `PA 10` · `PA X 5` · `PRN-3` · `PRN-4` · `RPJ-1` · `S6` · `SC-6`(18) · `SIB2` · `TCC-1`
      `TFL-2`(2) · `VCC-1` · `VCC-2` · `VCE-4` · `VCM-4` · `VNS-2` · `VP-10` · `VP-2` · `VS2` · `VSN2` · `XPC-8`
      `XPM-8` · `XPP-1` · `XPR-8` · `Z978` · `ZX1e`
      qué significa: 2 caracteres útiles ('2a')
      recomendación del recibo: **decidir una a una**

- [ ] regla **solo-letras-sin-digitos** — 83 altas
      `AMG-E` · `BE-XP` · `CAB-AA` · `DX Connexion` · `E-SIB-S` · `FIRECONTROL`(8) · `Firebeam Blue`(28) · `ISO-X`
      `IZE-A` · `LT-ACC-HUB-POE` · `LT-ACC-HUB-PWR` · `LT-ACC-TST` · `LT-CTR-C` · `LT-CTR-SML` · `LT-SEN-M`
      `LT-SEN-R` · `LocatorPlus-EN`(19) · `Loop Splitter` · `MI-BGL-PC-I`(7) · `MI-DCMOE`(7) · `MI-DCZM`(10)
      `MI-DMMI` · `MI-DMMIE` · `MI-GATE`(13) · `MI-PTSE`(10) · `MIB-F` · `MIB-W` · `MIB-WF` · `MIW-CMO`
      `MIW-EXP` · `MIW-MCP` · `MIW-MMI` · `MIW-PSE` · `MIW-PTSE` · `MIW-RHSE` · `MIW-SND` · `MIW-SS` · `MPS-TR`
      `N-MC-BB-O` · `N-MC-BB-R` · `N-MC-BB-U` · `N-MC-BB-W` · `N-MC-BB-Y` · `NFX-OPT` · `NFXI-BEAM-T`
      `NFXI-BF-WCH`(4) · `NFXI-BSF-WCS`(8) · `NFXI-OPT` · `NFXI-OSI-RIE`(41) · `NFXI-VIEW`(9) · `NRT-NET`
      `NRX-OPT`(12) · `NRX-REP`(12) · `NRX-TDIFF` · `NRX-WCP`(12) · `NRX-WS-RR` · `NRX-WS-WW` · `NRXI-GATE`(12)
      `ONE-BC` · `PRL-BOX` · `PRL-COM` · `PRL-VDS` · `RPT-F` · `RPT-W` · `RPT-WF` · `SENTOX IDI+`(49) · `SIB-NET`
      `Serie MPS` · `Signaline LocatorPlus`(16) · `TBUD-NG` · `TLED-NG` · `VGN-CO` · `VGN-VB` · `VGS DU`
      `VGS-AD` · `VROM-(n)` · `VSN-CRA-GSM` · `VTCC-AVL` · `Vision LT` · `ZXR` · `ZXSe`(88) · `ZXe`(207)
      `ZXr-A`(1)
      qué significa: no es un código alfanumérico (la mezcla letras+dígitos es lo que hace inequívoco a un modelo); puede ser prefijo de palabra
      recomendación del recibo: **decidir una a una**

- [ ] regla **base-alias-riesgosa** — 76 altas
      `085 501 949p` · `2X-AF1-FB-S` · `2X-AF2-FB-P` · `2X-AF2-FB-PRT` · `2X-AT-F1-FB-S` · `2X-AT-FR-FB`
      `2X-AT-FR-FB-S`(5) · `2X-AT-FR-S`(9) · `AM-82-BBMB` · `AM-82-MB` · `AM-8200-KLCD` · `AM-82N-TOP`
      `AM2-AL V4` · `CR-6EA-MODUL` · `DSE3-23 HQ CUBE` · `DSE3-23 HW WIDE` · `FL8-LT-XP` · `IS 28 Banshee`
      `IS 28 Mk 4` · `IS-mA1 Minialarm` · `KE-AS3005W-CM` · `KE-AS3005W-WM`(4) · `KE-AS3010R-IP` · `KE-AS3010W-IP`
      `KE-AS3011R-IP` · `KE-AS3015R-CM` · `KE-AS3015R-CMIP` · `KE-AS3015R-WM`(5) · `KE-AS3015R-WMIP`
      `KE-AS3015W-CM` · `KE-AS3015W-CMIP` · `KE-AS3015W-WM` · `KE-AS3015W-WMIP` · `KE-AS3105W-CM`
      `KE-AS3105W-WM`(5) · `KE-AS3110R-IP` · `KE-AS3110W-IP` · `KE-AS3111R-IP` · `KE-AS3115R-CM`
      `KE-AS3115R-CMIP` · `KE-AS3115R-CMW` · `KE-AS3115R-CMWIP` · `KE-AS3115R-WMW` · `KE-AS3115R-WMWIP`
      `KE-AS3115W-CM` · `KE-AS3115W-CMIP` · `KE-AS3115W-WM`(6) · `KE-AS3115W-WMIP` · `KE-DT3101W-HAB`(5)
      `KFD2-SD-Ex1 48` · `KFD2-SD-Ex1 48.90A` · `KFD2-SD-Ex1.48` · `KFD2-SD-Ex1.48.90A` · `MI 715 es 2026`
      `MI 716 es 2026` · `MI-LPB2-S2I`(38) · `MI-MM3E-S2`(8) · `NC-MC-0-R` · `NC-MC-100-R` · `NC-MC-470-R`
      `NC-MC-560-R` · `NC-PF2-SC` · `PA 10-SSM` · `PA 20-SSM` · `PA 5-24V DC` · `PA 5-SSM` · `PA X 10-10`
      `PA X 10-15` · `PA X 20-10` · `PA X 20-15` · `PA X 5-05` · `PA X 5-10` · `PY X-L-15-CPR`(21)
      `VSN 4 PLUS`(3) · `VSN 8 PLUS` · `WM-3-601601-X-016-A`
      qué significa: _base_aliases() añadiría '085-501' (6 útiles), que matchea mucho más ancho que el término
      recomendación del recibo: **decidir una a una**

- [ ] regla **palabra-comun-o-jerga** — 39 altas
      `2X-A-LB Loop Board` · `2X-LB Loop Board` · `4-relay board` · `ART 535` · `ART 535-10` · `ART. 1469`
      `Art. 1555` · `Art. 1555 SS` · `Art. 5055` · `Art. 5055 SS` · `Art. 5555 SS` · `FS-1300 Flame Simulator`
      `Flame Simulator FS-1100` · `Flame Simulator FS-1200` · `Model FS-1100` · `ONE 500`(69) · `Ref. 55315015`
      `Ref.: 002-467` · `Ref.: 002-629` · `Ref.: 010-114` · `Ref.: 020-579` · `Ref.: 020-588` · `Ref.: 124-292`
      `Serie 4000` · `Series 01` · `Series 02` · `Series 11` · `Simulator FS-1300` · `WB-1 Enclosure` · `WB-1 kit`
      `art. 1470` · `art. 1470 SA` · `art. 1492` · `art. 1493` · `art. 2493` · `ref.: 90306` · `referencia 73359`
      `referencia 73454` · `serie 2X-AT`
      qué significa: sus únicas palabras sueltas son jerga PCI/común: ['flame', 'simulator'] — clase FUEGO
      recomendación del recibo: **decidir una a una**

- [ ] regla **lleva-marca-delante** — 20 altas
      `ARGUS SECURITY SG350` · `FAAST FLEX FLX-010` · `FAAST FLEX FLX-020` · `Notifier CEI-ABI.AM-2000`
      `Notifier INSPIRE E10` · `Notifier INSPIRE E15` · `Testifire 1000` · `VESDA VLF-250` · `VESDA VLF-500`
      `VESDA-E VEP-A10-P` · `VESDA-E VES-A00-P` · `VESDA-E VES-A10-P` · `VESDA-E VEU-A00` · `VESDA-E VEU-A10`
      `Vision 12 LT` · `Vision 2` · `Vision 2 LT` · `Vision 4 LT` · `Vision 8 LT` · `Vision Plus 2`
      qué significa: empieza por el fabricante ('argus'): el detector debería llevar el código desnudo, no 'marca + modelo'
      recomendación del recibo: **decidir una a una**

- [ ] regla **descripcion-no-codigo** — 19 altas
      `70KIT140 Mid-Range Reflector` · `AMG-1 sin micrófono` · `Adaptador de tubo BA1` · `El Terminal CRT-2`
      `El XRAM-1` · `Galileo Multiscan++ SIL 1` · `ID Serial Phone Communicator D30` · `IS 28 Mk 4 Banshee`(16)
      `IS 28 Mk 4 Banshee Audible Warning Device` · `Inspire E10 65 240W 2-loop` · `La RP-1001`
      `Medidor-2 de Energía Principal` · `PARK2000 o PARK5000` · `SecuriSens ADW 535-1 ATEX`
      `Terminal de la Pantalla del CRT-2` · `la NFS 2-8` · `plaqueta RAM no volátil XRAM-1`
      `plaqueta de RAM no volátil XRAM-1` · `rivelatore di fumo fotoelettronico a basso profilo modello SD-651E`
      qué significa: 3 tokens / 19 chars / conectores de lengua natural ['sin']
      recomendación del recibo: **decidir una a una**

- [ ] regla **puntuacion-de-prosa** — 16 altas
      `6424(A)` · `AM-8200 CPU(AM8200-KLCD)` · `B501AP (-IV, -BK)` · `Dxc1(A1)` · `FAAST: 8100E` · `HG4 (typo)`
      `LT-ACC-ETS-5, -8, -16` · `LT-ACC-POE-4, -24` · `LT-ACC-PWR-12, -48` · `M701-240 ( -KO )` · `NFX(I)-SMT2`
      `NFX(I)-SMT3` · `PN: 020-543` · `S540(539) CODP` · `S540(539) COSP` · `Signaline LocatorPlus (SLP-001)`
      qué significa: lleva coma/dos puntos/paréntesis: es una frase extraída del manual, no un código
      recomendación del recibo: **decidir una a una**

- [ ] regla **comodin-en-el-codigo** — 12 altas
      `11-1000002-10-xx` · `11-2000001-01-XX` · `124-065-XXX`(6) · `50-0500259-01-xx` · `5000623.0104.XXYYZZ`
      `M700KAC-xx` · `M700KACI-xx` · `MCP5A-xP05xx` · `MCP5A-xP06xx` · `PA X 5-xx-SSM` · `S876xx` · `S877xx`
      qué significa: lleva un comodín (xx/nnn/###): el código real varía, así almacenado no identifica una unidad
      recomendación del recibo: **decidir una a una**

- [ ] regla **parece-nombre-de-fichero** — 10 altas
      `AM-8100_manu-prog_SP` · `IBOX-MBS-NID3000_EN` · `IntesisBox_MODBUS_SVR_MID3000`
      `IntesisBox_MODBUS_SVR_NID3000` · `MA-DT-015_03` · `MICRA25.dfs` · `Micra100.dfs` · `NFG-8_manu-inst_PORT`
      `VSN4-PLUS_manu` · `iBox_BACNET_SVR_NID3000`
      qué significa: lleva '_' o extensión de fichero: es el nombre de un PDF/archivo, no el código impreso en el equipo
      recomendación del recibo: **decidir una a una**

- [ ] regla **artefacto-de-extraccion** — 8 altas
      `KFDO-CS- Ex. 1.54-Y72221` · `M700KAC -SG` · `M700KAC -yz` · `M700KACI -yz` · `MCP3A...` · `PA X 10..`
      `PA X 20..` · `iBox Modbus Server - Notifier ID3000`
      qué significa: guion suelto o '..' de código truncado: el término almacenado no es lo que lleva impreso el equipo
      recomendación del recibo: **decidir una a una**

- [ ] regla **colision-con-alias-base-vivo** — 5 altas
      `2X-AF1` · `2X-AF2` · `CAD-150` · `CFP-600` · `TCF-142`
      qué significa: ya se detecta hoy como alias-base de '2X-AF1-S'; darlo de alta cambia la forma canónica devuelta, no añade detección
      recomendación del recibo: **decidir una a una**

- [ ] regla **prefijo-abreviado-de-catalogo** — 5 altas
      `Art.No. 11-1000000-02-XX` · `F.A. PSU7A` · `MOD.REL-2000` · `Mod.HEF20RL` · `Mod.PA-RZ1`
      qué significa: empieza por Mod./Ref./Art./Doc.: el identificador del equipo es lo que va detrás
      recomendación del recibo: **decidir una a una**

- [ ] regla **core-identico-a-otra-alta** — 4 altas
      `MPS 1.5` · `MPS 2.5` · `MPS15` · `MPS25`
      qué significa: mismo core regex que ['MPS15']: dos identidades para una misma detección
      recomendación del recibo: **decidir una a una**

- [ ] regla **sufijo-de-idioma** — 4 altas
      `2X-AT-FR` · `9-30780-KID-EN` · `9-30782-KID-EN` · `M-061.1-VSN4-PLUS-ITA`
      qué significa: acaba en sufijo de idioma: suele identificar la edición de un DOCUMENTO
      recomendación del recibo: **decidir una a una**

- [ ] regla **numero-certificacion** — 3 altas
      `0786-CPD-20644` · `0786-CPD-20645 09` · `VdS 0786-CPR-21563`
      qué significa: patrón NNNN-CPD/CPR-NNNNN (certificado de organismo notificado, no un modelo)
      recomendación del recibo: **NO dar de alta (no es un equipo: es una norma o un número de certificación)**

- [ ] regla **caracter-no-ascii-raro** — 2 altas
      `2010−2-PAK-RMSDK` · `2010−2A-PAK-HPL`
      qué significa: contiene U+2212 (no es una letra acentuada): normkey y _base_aliases se comportan de forma no obvia
      recomendación del recibo: **decidir una a una**

- [ ] regla **core-identico-a-modelo-vivo** — 2 altas
      `ST.S1REL` · `VSN-RP1r+`
      qué significa: mismo core regex que 'STS1REL' del snapshot vivo (los separadores son opcionales): dos identidades para una misma detección
      recomendación del recibo: **decidir una a una**

- [ ] regla **posible-referencia-cpr** — 1 alta
      `SG0110CPR20130901`
      qué significa: lleva CPD/CPR pegado a 4+ dígitos: puede ser DoP/certificado o un código comercial marcado CPR — hay que mirarlo
      recomendación del recibo: **decidir una a una**

---

## SECCIÓN 2 — Obsoletas (4) — **no decides nada**

Estaban en el packet v1 y ya no aplican tras el refresco. Motivos: ya-no-resuelve-en-gobernado=3, sin-atestacion-activa-hoy=1

- `100m Detector` (vía packet alias) — ya-no-resuelve-en-gobernado · el término salió de _resolvable_terms (alias revocado, producto retirado/candidate o renombrado) entre el 12-ago y hoy
- `50m Detector` (vía packet alias) — ya-no-resuelve-en-gobernado · el término salió de _resolvable_terms (alias revocado, producto retirado/candidate o renombrado) entre el 12-ago y hoy
- `FD2705-10R` (vía packet exact) — ya-no-resuelve-en-gobernado · el término salió de _resolvable_terms (alias revocado, producto retirado/candidate o renombrado) entre el 12-ago y hoy
- `ZXr-P` (vía packet (el recibo no trae este campo)) — sin-atestacion-activa-hoy · ningún producto suyo tiene doc_map a documento ACTIVO con chunks servibles y su normkey no aparece como product_model

---

## Apéndice — contexto, no decisiones

**Notas de refresco** (30 cambios de `chunk_count` entre el packet y hoy; no son
decisiones, explican por qué una cifra no cuadra con la v1):

- `CR-6EA` · chunk_count: packet 0 → hoy 12
- `DH500ACDC-E` · chunk_count: packet 0 → hoy 46
- `Firebeam Blue` · chunk_count: packet 0 → hoy 28
- `FIRECONTROL` · chunk_count: packet 0 → hoy 8
- `IBOX-BAC-NID3000` · chunk_count: packet 0 → hoy 85
- `IBOX-MBS-NID3000` · chunk_count: packet 0 → hoy 79
- `IM-10EA` · chunk_count: packet 0 → hoy 11
- `IS 28 Mk 4` · chunk_count: packet 16 → hoy 0
- `IS 28 Mk 4 Banshee` · chunk_count: packet 0 → hoy 16
- `M701E` · chunk_count: packet 0 → hoy 9
- `M701E-240` · chunk_count: packet 0 → hoy 10
- `M710-CZR` · chunk_count: packet 0 → hoy 10
- …y 18 más en el recibo.

**Sub-bloque relajable, si quieres apurar** (52): altas de la §1 marcadas sólo por
`solo-letras-sin-digitos` que el recibo señala como relajables a bloque. **No están**
**incluidas en el sí de la §0** — es una decisión aparte y consciente:

`DX Connexion` · `FIRECONTROL` · `LT-ACC-HUB-POE` · `LT-ACC-HUB-PWR` · `LT-ACC-TST` · `LT-CTR-C`
`LT-CTR-SML` · `LT-SEN-M` · `LT-SEN-R` · `MI-BGL-PC-I` · `MI-DCMOE` · `MI-DCZM` · `MI-DMMI` · `MI-DMMIE`
`MI-GATE` · `MI-PTSE` · `MIW-CMO` · `MIW-EXP` · `MIW-MCP` · `MIW-MMI` · `MIW-PSE` · `MIW-PTSE` · `MIW-RHSE`
`MIW-SND` · `NFXI-BEAM-T` · `NFXI-BF-WCH` · `NFXI-BSF-WCS` · `NFXI-OPT` · `NFXI-OSI-RIE` · `NFXI-VIEW`
`NFX-OPT` · `N-MC-BB-O` · `N-MC-BB-R` · `N-MC-BB-U` · `N-MC-BB-W` · `N-MC-BB-Y` · `NRT-NET` · `NRXI-GATE`
`NRX-OPT` · `NRX-REP` · `NRX-TDIFF` · `NRX-WCP` · `NRX-WS-RR` · `NRX-WS-WW` · `PRL-BOX` · `PRL-COM`
`PRL-VDS` · `SIB-NET` · `TBUD-NG` · `TLED-NG` · `VSN-CRA-GSM` · `VTCC-AVL`

---

## Recibos (la traza completa, fila a fila)

- `evals/s322f_e2_altas_split_v1.json` — 1235 filas (562 bloque / 669 individual)
- Ensamblado por `scripts/s322_packets_v2.py` (determinista, sin LLM) el 20260815T163607Z.

## Auto-verificación del encabezado

Filas declaradas arriba vs filas REALMENTE escritas en este fichero:

- **SECCIÓN 0**: declaradas 562 · escritas 562 · casillas 55 — ✓
- **SECCIÓN 1**: declaradas 669 · escritas 669 · casillas 19 — ✓
- **SECCIÓN 2**: declaradas 4 · escritas 4 · casillas 0 — ✓
- **TOTAL**: 1235 = 562 + 669 + 4 ✓ (cuadra con las 1235 casillas de la v1)
