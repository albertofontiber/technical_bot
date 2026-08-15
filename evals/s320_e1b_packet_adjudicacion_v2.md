# s320 E1b — Packet de ADJUDICACIÓN **v2 (encogido)** · 20260815T105757Z

**SUPERSEDE a `evals/s320_e1_packet_adjudicacion_v1.md (§5 «confirmar»/«revisar» del E1b)`.**
Los dos lotes del E1b (**359** «confirmar» + **261** «revisar» = **620 casillas**) venían
de una atestación `ilike` **sin fronteras de palabra**: contaba «CAD-250» dentro de
«CAD-250-BLED» y «adaptador» dentro de «adaptadores». Dos pasadas hermanas han
re-medido cada término con **token exacto** y han juzgado sólo lo que la medida no
zanja.

> ### De **620 casillas** → **146 decisiones**
> - **1 sí en bloque** cubre **475 filas** (§0, en 4 sub-bloques).
> - **145 una a una** (§1).

> **Cuenta honesta de casillas** (la escribe el verificador adversarial, no el optimismo del autor): este fichero imprime **432 casillas `- [ ]`** en total — §0.A: 9 · §0.B: 130 · §0.C: 144 · §0.D: 4 · §1.A: 32 · §1.B: 113. Las de §0 están ahí para que PUEDAS bajar a grano fino y desmarcar lo que quieras, no porque haya que marcarlas una a una: el «sí en bloque» las cubre todas de golpe. Si solo asientes a los bloques, tu trabajo real son las decisiones del titular.

**NADA APLICADO.** Ni catálogo (`data/catalog/*.jsonl`), ni Supabase, ni el
snapshot del detector (`data/model_catalog.json`). Todo lo de aquí es PROPUESTA:
marca ✓/✗ y se aplica después por la puerta gobernada, con recibo.

---

## SECCIÓN 0 — Aplicables EN BLOQUE si asientes (475)

Puerta del bloque «confirmar» (las 5 condiciones, todas):
  1. n_ilike_hoy >= 3 (sigue atestado hoy)
  2. n_chunks_token_exacto >= 2 (token completo, no subcadena)
  3. sin banderas léxicas de artefacto
  4. fragmento de evidencia verbatim extraído del corpus
  5. vía LLM: veredicto=confirmar + confianza=alta + cita verificada a texto completo

Puerta del bloque «revisar»: n_frontera_hoy>=1 ∧ veredicto claro ∧ confianza alta ∧ cita verificada a texto COMPLETO (hasta 200 chars, espacios normalizados) ∧ sin colisión de catálogo. El bloque de RETIRAR va en lista aparte: un «sí» de confirmar no puede arrastrar borrados.

> **Avisos del bloque** (no bloquean nada; señalan los puntos más finos del bloque para que el «sí» sea informado):
> - **colisiones de nombre: 14** — confirmar los dos ids crea DOS productos para un
>   mismo nombre (posible duplicado o alias, no alta separada):
>     - `apic` → `aritech:apic` / `notifier:apic`
>     - `ess122plus` → `morley:ess12-2plus` / `unresolved:ess12-2plus`
>     - `ess42plus` → `morley:ess4-2plus` / `unresolved:ess4-2plus`
>     - `ess82plus` → `morley:ess8-2plus` / `unresolved:ess8-2plus`
>     - `hgtwn` → `notifier:h-gtw-n` / `unresolved:h-gtw-n`
>     - `mcx55m` → `morley:mcx-55m` / `notifier:mcx-55m`
>     - `milzr` → `morley:mi-lzr` / `unresolved:mi-lzr`
>     - `mmx10m` → `morley:mmx-10m` / `notifier:mmx-10m`
>     - `nfs12supra` → `morley:nfs12-supra` / `unresolved:nfs12-supra`
>     - `nfs4supra` → `morley:nfs4-supra` / `unresolved:nfs4-supra`
>     - `nfs8rel` → `morley:nfs8rel` / `notifier:nfs8rel`
>     - `nfs8supra` → `morley:nfs8-supra` / `unresolved:nfs8-supra`
>     - `visionplus` → `notifier:vision-plus` / `unresolved:vision-plus`
>     - `vsnll` → `morley:vsn-ll` / `notifier:vsn-ll`
> - **evidencia mínima (1 solo chunk con token exacto): 2** — `notifier:vs4095`, `pepperl-fuchs:z705`
> - **fabricante del manual distinto al del id: 109** filas. No es un fallo (OEM/reventa
>   es la norma en PCI), pero si te importa la marca de origen, mira el recibo.

Deriva de conteo desde el 12-ago (subió/bajó/igual/cayó bajo umbral): subio=0, bajo=0, igual=359, cayo_bajo_umbral=0
Del lote «revisar»: filas medidas hoy **261**, con conteo cambiado desde el 12-ago **0**,
mencionadas **sólo por subcadena** (o sea, no atestadas) **0**.

### §0.A — «confirmar» por **medida determinista, sin juez** (197)

Aquí no opinó ningún modelo: el término aparece como **token completo** en ≥2 chunks
y en varios documentos. La medida ES el veredicto. Formato: `MODELO(chunks·docs)`.
Se agrupan por marca en lotes para que quepan; **cada término está listado** (Ctrl-F)
y el detalle fila a fila —chunk_id, página, sección, fragmento verbatim— está en el recibo.

- [ ] **notifier** — 83 confirmaciones deterministas
      `AFM-16AT`(21·8) · `AFM-32A`(17·6) · `AIM-200`(39·7) · `AM-200`(9·3) · `AM-8200N`(40·3) · `AMG-X4`(5·1)
      `AW70PC0`(13·2) · `BE-1010N`(4·1) · `BE-2020N`(5·1) · `BE-400`(2·2) · `BX-501`(20·5) · `CAB-400AA`(39·3)
      `CAB-A3`(28·10) · `CAB-B3`(25·11) · `CAB-C3`(27·10) · `CAB-D3`(25·9) · `CMX-10`(9·9) · `CMX-10R`(11·10)
      `CPX-551`(25·15) · `CPX-751`(21·9) · `DIA-1010`(19·7) · `DIA-2020`(18·6) · `EIA-485`(40·14) · `FAT3000`(8·1)
      `FDX-551`(21·13) · `FDX-551R`(13·9) · `FIL-NAS-2`(3·2) · `HOP-131-206`(4·4) · `HOP-134-412`(3·3)
      `HOP-208-111`(3·2) · `HSP-121B`(3·1) · `ID-3000`(37·19) · `ID1000`(34·8) · `IDX-751`(10·5)
      `IPX-751`(27·14) · `IRX-751CTEM-W`(4·4) · `LCD-80`(39·15) · `LCD-80TM`(16·4) · `LCD-8200`(32·6)
      `LIB-8200`(17·2) · `LPX-751`(20·13) · `LTS-240`(4·3) · `M710-CZ`(19·11) · `MCX-55M`(5·5) · `MMX-10M`(9·9)
      `MON-17B`(2·2) · `MON-21`(2·2) · `NFS8REL`(4·2) · `NR45-24E`(8·3) · `NRT-586T`(9·1) · `PAN-AVD1`(3·1)
      `PCLB-5`(3·1) · `PK-8200`(21·4) · `PK-ID3000`(40·4) · `PRN2000`(13·5) · `PRN80`(4·4) · `PSU3A`(21·3)
      `RTU01`(4·3) · `S2138SD`(3·2) · `S2139SD`(3·2) · `S2140ND`(3·2) · `S2141ND`(3·2) · `S2142CL`(3·2)
      `S2143CL`(3·2) · `S2147HC`(3·2) · `S2170SD`(3·2) · `S2171SD`(3·2) · `S2172ND`(3·2) · `S2173ND`(3·2)
      `S2174CL`(3·2) · `S2175CL`(3·2) · `S2311HC`(3·2) · `SDX-551`(19·13) · `SMART3G-D`(2·1) · `SMART4`(7·4)
      `STPL4`(2·1) · `TG-1020`(40·15) · `TG-6000`(14·6) · `TR-500`(6·3) · `UDS-3N`(7·3) · `UPDL-1020`(6·1)
      `UPDL-2020`(4·1) · `VSN-2PLUS`(5·5)
- [ ] **unresolved** — 51 confirmaciones deterministas
      `AM8200`(4·4) · `CCD-103`(12·9) · `DOD-220`(2·1) · `DOD-220A`(7·6) · `DOD-220A-I`(12·10) · `DOTD-230`(2·1)
      `DOTD-230A`(7·6) · `DOTD-230A-I`(11·10) · `DTD-210`(2·1) · `DTD-210A`(7·6) · `DTD-210A-I`(7·6)
      `DTD-215`(2·1) · `DTD-215A`(7·6) · `DTD-215A-I`(7·6) · `ECO1000`(37·23) · `ESS12-2Plus`(3·3)
      `ESS4-2Plus`(3·3) · `ESS8-2Plus`(3·3) · `FS20X`(39·3) · `FS24X`(38·3) · `FS24X-9`(6·2) · `FSL100-IR3`(6·1)
      `FSL100-SM21`(6·1) · `FSL100-TL`(10·1) · `FSL100-TLX`(9·1) · `FSL100-UV`(7·1) · `FSL100-UVIR`(7·1)
      `H-GTW-1`(4·2) · `M710-CZR`(11·5) · `MAD-402`(5·5) · `MAD-412`(7·5) · `MAD-422`(11·9) · `MAD-442`(7·5)
      `MAD-450`(13·10) · `MAD-464-I`(7·6) · `MAD-465-I`(7·6) · `MAD-472`(5·5) · `MAD-564-I`(8·5)
      `MAD-565-I`(10·5) · `MAD-567-I`(4·1) · `MAD-569-I`(4·1) · `NFS12-Supra`(4·3) · `NFS4-Supra`(4·3)
      `NFS8-Supra`(4·3) · `PGD-200`(14·6) · `POL-200-TS`(39·5) · `S300ZDU`(8·1) · `TL-1055`(6·2) · `TL-2055`(5·2)
      `VSN12-2Plus`(3·3) · `VW2W100`(3·2)
- [ ] **kidde** — 16 confirmaciones deterministas
      `2010-1-SB`(13·3) · `KE-DM3010RS06`(7·3) · `KE-DM3010RS18`(7·3) · `KE-DM3010RS27`(7·3)
      `KE-DM3010RSCH`(7·3) · `KE-DM3010RSCL`(7·3) · `KE-DM3110RS06`(7·3) · `KE-DM3110RS18`(7·3)
      `KE-DM3110RS27`(7·3) · `KE-DM3110RSCH`(7·3) · `KE-DM3110RSCL`(7·3) · `NC-MC-0-O`(3·1) · `NC-MC-0-U`(3·1)
      `NC-MC-0-W`(3·1) · `NC-MC-0-Y`(3·1) · `NC-MC-560-U`(3·1)
- [ ] **morley** — 16 confirmaciones deterministas
      `DX1e-20S`(10·2) · `DX2e-40M`(6·2) · `DX4e-40L`(7·2) · `ESS12-2Plus`(3·3) · `ESS4-2Plus`(3·3)
      `ESS8-2Plus`(3·3) · `EXP-004`(3·2) · `EXP-004B`(3·2) · `EXP-005`(3·2) · `MCX-55M`(5·5) · `MI-200`(3·1)
      `MMX-10M`(9·9) · `NFS12-Supra`(4·3) · `NFS4-Supra`(4·3) · `NFS8-Supra`(4·3) · `NFS8REL`(4·2)
- [ ] **systemsensor** — 16 confirmaciones deterministas
      `ECO1000B`(3·3) · `ECO1000BRELx`(3·3) · `ECO1000BRx`(3·3) · `ECO1000BRxSD`(3·3) · `ECO1000BSD`(3·3)
      `ECO1000DB`(3·3) · `ECO1000DBRx`(3·3) · `ECO1000DBRxSD`(3·3) · `ECO1000DBSD`(3·3) · `RTS451KEY`(9·6)
      `WFD20EN`(3·2) · `WFD25EN`(3·2) · `WFD30EN`(3·2) · `WFD40EN`(3·2) · `WFD60EN`(3·2) · `WFD80EN`(3·2)
- [ ] **detnov** — 8 confirmaciones deterministas
      `CAD-250-BLED`(6·4) · `CAD-250B`(5·4) · `CCD-102`(5·5) · `CCD-104`(5·5) · `CCD-108`(5·5) · `CCD-112`(5·5)
      `SCD-250`(8·4) · `SGD-151`(22·5)
- [ ] **xtralis** — 5 confirmaciones deterministas
      `9-30441`(3·2) · `IFT-15`(4·1) · `LT-ACC-POE-24-ADR`(3·1) · `VLI-880`(3·1) · `VSP-961`(14·6)
- [ ] **fidegas** — 1 confirmación determinista
      `00051`(3·2)
- [ ] **spectrex** — 1 confirmación determinista
      `777650`(4·2)

### §0.B — «confirmar» por **juez, alta + cita verificada** (130)

Formas sospechosas (cortas, sin dígitos, multipalabra) que la medida sola no zanja.
Banderas léxicas del lote completo: muy_corto=77, sin_digitos=69, palabra_generica=23, multipalabra=55, unidad_o_norma=2, parece_fichero=1, medida_en_contexto=4

- [ ] `aritech:apic` (APIC) · 35 chunks token exacto en 11 docs · banderas: muy_corto,sin_digitos
      cita ✓ «Es posible usar una tarjeta interfaz de protocolo direccionable (APIC) para descifrar la informació…»
      por qué: La evidencia describe APIC como una tarjeta interfaz de protocolo direccionable concreta, instalable en un puerto de ampliación, lo que confirma que es un prod…
- [ ] `fidegas:cs4` (CS4) · 10 chunks token exacto en 5 docs · banderas: muy_corto
      cita ✓ «# MANUAL DE USUARIO ## CENTRAL DE ALARMAS # CS4 ## (Analógica o Digital)»
      por qué: CS4 es el título de un manual de usuario propio como central de alarmas y aparece listado como producto compatible ('Centrales Ref. CS4'), lo que confirma que…
- [ ] `firebeam:firebeam-xtra` (Firebeam Xtra) · 4 chunks token exacto en 3 docs · banderas: multipalabra,sin_digitos
      cita ✓ «Power up the unit and you will see `the Firebeam Xtra` the screen will default to Fault or Fire»
      por qué: El nombre aparece como token completo en manuales de puesta en marcha en varios idiomas, mostrado en pantalla al encender el equipo, lo que confirma que Firebe…
- [ ] `kidde:2x-at` (2X-AT) · 28 chunks token exacto en 3 docs · banderas: muy_corto
      cita ✓ «This is a supplementary publication to introduce the 2X-AT Series control panels.»
      por qué: La evidencia muestra que 2X-AT designa una serie de centrales de incendio del fabricante, mencionada como tal en guías y manuales, con 28 menciones como token…
- [ ] `kidde:standard-display-module` (Standard Display Module) · 4 chunks token exacto en 3 docs · banderas: multipalabra,palabra_generica,sin_digitos
      cita ✓ «Dispositivo de detección | 9-30781 | AirSense Stratos ModuLaser, Standard display module»
      por qué: El nombre designa una variante real del sistema ModuLaser de Kidde, asociada a la referencia comercial 9-30781 y diferenciada de otros módulos (Minimum, Comman…
- [ ] `morley:dx1e` (DX1e) · 11 chunks token exacto en 3 docs · banderas: muy_corto
      cita ✓ «Los paneles de control de incendios DX1e, DX2e y DX4e disponen de 1, 2 y 4 lazos, para instalar dis…»
      por qué: DX1e se menciona repetidamente como panel de control de incendios de la serie DX, con descripción funcional propia (1 lazo). Las variantes DX1e-20S/40M son con…
- [ ] `morley:dx2e` (DX2e) · 15 chunks token exacto en 3 docs · banderas: muy_corto
      cita ✓ «Los paneles de control de incendios DX1e, DX2e y DX4e disponen de 1, 2 y 4 lazos, para instalar dis…»
      por qué: DX2e se describe explícitamente como un panel de control de incendios de 2 lazos dentro de la familia DX1e/DX2e/DX4e, con múltiples menciones como token comple…
- [ ] `morley:dx4e` (DX4e) · 16 chunks token exacto en 3 docs · banderas: muy_corto
      cita ✓ «Los paneles de control de incendios DX1e, DX2e y DX4e disponen de 1, 2 y 4 lazos, para instalar dis…»
      por qué: DX4e se describe explícitamente como un panel de control de incendios de 4 lazos, con especificaciones propias (hasta 800 dispositivos analógicos), lo que conf…
- [ ] `morley:mi-lzr` (MI-LZR) · 36 chunks token exacto en 10 docs · banderas: sin_digitos
      cita ✓ «MI-LZR Det Laser de Humo (Alta sensibilidad)»
      por qué: MI-LZR aparece como detector láser de humo de alta sensibilidad, descrito con especificaciones técnicas (sensibilidad 0.1% obs/m) y como componente suministrad…
- [ ] `morley:vsn-12-plus` (VSN 12 PLUS) · 3 chunks token exacto en 3 docs · banderas: multipalabra,palabra_generica
      cita ✓ «VSN 4 PLUS ; VSN 8 PLUS ; VSN 12 PLUS»
      por qué: El modelo VSN 12 PLUS aparece como token completo en portadas de manuales oficiales de instalación de Morley-IAS/Honeywell en tres idiomas, junto a sus variant…
- [ ] `morley:vsn-ll` (VSN-LL) · 9 chunks token exacto en 5 docs · banderas: sin_digitos
      cita ✓ «Requiere llave externa opcional VSN-LL»
      por qué: La evidencia describe VSN-LL como una llave externa opcional (optional keyswitch) para acceder al nivel 2 del panel, es decir, un accesorio comercial real del…
- [ ] `morley:vsn4` (VSN4) · 8 chunks token exacto en 3 docs · banderas: muy_corto
      cita ✓ «Las centrales VSN2 y VSN4 se han diseñado para que cumplan con los requisitos de la norma EN 54, pa…»
      por qué: La evidencia describe explícitamente la VSN4 como una central de detección de incendios del fabricante, con especificaciones propias (zonas, sirenas, cumplimie…
- [ ] `notifier:911a` (911A) · 15 chunks token exacto en 3 docs · banderas: muy_corto
      cita ✓ «NOTI-FIRE 911A DACT* - para la conexión a la Estación Receptora Central o a Unidades Receptoras.»
      por qué: El 911A aparece como producto concreto del fabricante (comunicador digital DACT NOTI-FIRE 911A) descrito con función y requisitos de instalación, no como medid…
- [ ] `notifier:am-lcd` (AM-LCD) · 24 chunks token exacto en 5 docs · banderas: sin_digitos
      cita ✓ «Condición con evento de zona en alarma (AM-LCD programado como Global)»
      por qué: AM-LCD es un anunciador LCD real de Notifier: la evidencia muestra que se programa (Global/Parcial) y aparece listado como periférico configurable junto a CPU,…
- [ ] `notifier:apic` (APIC) · 35 chunks token exacto en 11 docs · banderas: muy_corto,sin_digitos
      cita ✓ «Es posible usar una tarjeta interfaz de protocolo direccionable (APIC) para descifrar la informació…»
      por qué: APIC designa una tarjeta interfaz de protocolo direccionable, un producto real instalable descrito con función y modo de instalación en el manual. Los tokens p…
- [ ] `notifier:bm-1` (BM-1) · 5 chunks token exacto en 3 docs · banderas: muy_corto
      cita ✓ «BM-1 | Módulo vacío para cubrir un módulo o panel no utilizado»
      por qué: BM-1 aparece en varias tablas de productos del fabricante como módulo en blanco para cubrir posiciones no utilizadas, con descripción de producto consistente e…
- [ ] `notifier:bp-1` (BP-1) · 7 chunks token exacto en 2 docs · banderas: muy_corto
      cita ✓ «Panel de Revestimiento de Batería BP-1 Cubre la MPS (FAP, Fuente de Alimentación Principal) y las b…»
      por qué: BP-1 aparece en varios documentos como un producto concreto del fabricante (Panel de Revestimiento/Embellecedor de Batería), listado junto a otras referencias…
- [ ] `notifier:bp-3` (BP-3) · 15 chunks token exacto en 5 docs · banderas: muy_corto
      cita ✓ «Panel Embellecedor de la Batería BP-3»
      por qué: BP-3 designa un producto real del fabricante: el Panel Embellecedor de la Batería, mencionado consistentemente como accesorio junto a otras referencias del sis…
- [ ] `notifier:ccm-1` (CCM-1) · 29 chunks token exacto en 13 docs · banderas: muy_corto
      cita ✓ «DOCUMENTO INSTALACIÓN DEL PRODUCTO (CCM-1) | 15328»
      por qué: CCM-1 aparece con documento de instalación propio y listado junto a otros módulos del sistema (CPU-2, SIB-64, AMG-1), lo que confirma que es una referencia com…
- [ ] `notifier:cmx` (CMX) · 31 chunks token exacto en 17 docs · banderas: muy_corto,sin_digitos
      cita ✓ «2 circuitos lógicos que simulan módulos CMX (para programarse con TIPO ID = supervisado o forma rel…»
      por qué: CMX es un módulo de control real de Notifier: la evidencia lo trata como dispositivo físico con terminales, alimentación supervisada y variantes (CMX-1, CMX-2)…
- [ ] `notifier:cmx-1` (CMX-1) · 20 chunks token exacto en 10 docs · banderas: muy_corto
      cita ✓ «El CMX-1 y el CMX-2 son idénticos excepto que el CMX-2 tiene un parámetro de tensión más alto (70.7…»
      por qué: La evidencia describe el CMX-1 como un módulo analógico direccionable con especificaciones técnicas propias y aparece listado en tablas de producto, lo que con…
- [ ] `notifier:cre-4` (CRE-4) · 31 chunks token exacto en 6 docs · banderas: muy_corto
      cita ✓ «Expansor del Relé de Control (CRE-4)»
      por qué: CRE-4 aparece en varios manuales como módulo con nombre y función propios (Expansor del Relé de Control), junto a otros módulos reales de la familia (CRM-4, IC…
- [ ] `notifier:crm-4` (CRM-4) · 34 chunks token exacto en 7 docs · banderas: muy_corto
      cita ✓ «Módulo de Relé de Control (CRM-4)»
      por qué: La evidencia muestra CRM-4 listado explícitamente como 'Módulo de Relé de Control' junto a otros módulos reales de Notifier (ICM-4, CRE-4, ARM-4), y aparece co…
- [ ] `notifier:crt-1` (CRT-1) · 27 chunks token exacto en 10 docs · banderas: muy_corto
      cita ✓ «Indica que existe un terminal local (CRT-1, CRT-2) conectado y desde el cual se pueden realizar Ace…»
      por qué: CRT-1 es un terminal anunciador real de Notifier: la evidencia lo describe como equipo conectado con teclado y funciones propias (READ STATUS), y el LCD-80 lo…
- [ ] `notifier:dp-1` (DP-1) · 13 chunks token exacto en 6 docs · banderas: muy_corto
      cita ✓ «El **Panel Embellecedor (DP-1)** cubre los ensambles adicionales del ICA-4L o el CHS-4/4L en el gab…»
      por qué: DP-1 aparece descrito explícitamente como un producto (Panel Embellecedor) con función definida en el manual, además de figurar en el índice y junto a otros ac…
- [ ] `notifier:dts-240` (DTS 240) · 40 chunks token exacto en 3 docs · banderas: multipalabra
      cita ✓ «El cable sensor se instala en el área que se va a proteger y también se conecta a la unidad optoele…»
      por qué: La evidencia describe el DTS 240 como una unidad optoelectrónica física a la que se conecta el cable sensor, con número de serie propio y post-procesadores, lo…
- [ ] `notifier:e-sib` (E-SIB) · 8 chunks token exacto en 5 docs · banderas: muy_corto,sin_digitos
      cita ✓ «E-SIB (mochila que habilita la comunicación serie)»
      por qué: La evidencia describe E-SIB como una tarjeta/mochila de interfaz serie configurable en centrales Notifier AM, con función y conexión propias; es una referencia…
- [ ] `notifier:e10` (E10) · 11 chunks token exacto en 6 docs · banderas: muy_corto
      cita ✓ «E10 | Central INSPIRE cabina pequeña»
      por qué: La evidencia define explícitamente E10 como la central INSPIRE de cabina pequeña, un producto real del fabricante, corroborado por menciones de baterías y envo…
- [ ] `notifier:e15` (E15) · 10 chunks token exacto en 5 docs · banderas: muy_corto
      cita ✓ «| E15 | Central INSPIRE cabina grande |»
      por qué: La evidencia muestra E15 como modelo real de central INSPIRE de NOTIFIER (cabina grande), distinguido del E10 (cabina pequeña) en varios documentos, incluyendo…
- [ ] `notifier:fa30` (FA30) · 13 chunks token exacto en 2 docs · banderas: muy_corto
      cita ✓ «kit de fuente de alimentación FA30 (3 A) en el chasis principal»
      por qué: FA30 aparece de forma consistente como una fuente de alimentación concreta del fabricante, con especificación técnica (3 A) e instrucciones de instalación y ma…
- [ ] `notifier:g-10` (G-10) · 4 chunks token exacto en 2 docs · banderas: muy_corto,unidad_o_norma
      cita ✓ «the NCO-10 carbon monoxide (CO) detector is designed for use with the G-10 CO detection system in c…»
      por qué: La evidencia describe explícitamente el G-10 como un sistema de detección de CO del fabricante, con variantes de central de control (G-10 1/2 y G-10-1/5), lo q…
- [ ] `notifier:h-gtw` (H-GTW) · 24 chunks token exacto en 3 docs · banderas: muy_corto,sin_digitos
      cita ✓ «## Central ID-3000 | H-GTW | ID-3000 (ISO-RS232) | | ----- | ------------------- | | GND | 0v | | T…»
      por qué: H-GTW aparece como equipo físico con tabla de conexionado (GND, TX/RX) a la central ID-3000 y con versión propia de manual ('H-GTW v 2.26'), lo que indica una…
- [ ] `notifier:h-gtw-n` (H-GTW-N) · 5 chunks token exacto en 3 docs · banderas: sin_digitos
      cita ✓ «El modelo **H-GTW-N** permite realizar la integración igualmente a cualquiera de las centrales indi…»
      por qué: El corpus lo denomina explícitamente 'modelo' y describe su función de integración con centrales, apareciendo además en tablas junto a la variante H-GTW-1, lo…
- [ ] `notifier:idx-751-ae` (IDX-751 AE) · 3 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «**Product:** IDX-751 AE **Mounting Bases:** B501, B501AP **Description:** Intrinsically safe analog…»
      por qué: La evidencia identifica explícitamente IDX-751 AE como producto del fabricante (detector óptico de humo direccionable intrínsecamente seguro), con fabricante,…
- [ ] `notifier:inspire` (INSPIRE) · 40 chunks token exacto en 9 docs · banderas: sin_digitos
      cita ✓ «Notifier INSPIRE E10/E15 Central de alarmas de detección de incendios Instrucciones de usuario»
      por qué: INSPIRE es la denominación comercial de la central de alarmas de incendio de Notifier (variantes E10/E15), citada como producto en sus propias instrucciones de…
- [ ] `notifier:laserstar` (LaserStar) · 30 chunks token exacto en 6 docs · banderas: sin_digitos
      cita ✓ «La gama de detectores LaserStar es única en su capacidad de proporcionar un nivel constante de prot…»
      por qué: La evidencia describe LaserStar como una gama de detectores de NOTIFIER con capacidades específicas de protección, lo que confirma que es una referencia comerc…
- [ ] `notifier:lisa-2` (LISA 2) · 6 chunks token exacto en 2 docs · banderas: multipalabra
      cita ✓ «Para el detector LISA 2, SENSITRON Srl dispone de un kit de calibración especial en campo con trans…»
      por qué: LISA 2 aparece como detector de gas del fabricante SENSITRON Srl, con accesorios propios y esquema de conexión documentado; es claramente una referencia comerc…
- [ ] `notifier:lnk-boxmb` (LNK-BoxMB) · 11 chunks token exacto en 1 doc · banderas: sin_digitos
      cita ✓ «Seleccione en LNK-BoxMB el puerto serie del PC usado para la conexión con iBox ModBus.»
      por qué: LNK-BoxMB aparece consistentemente como nombre propio de la herramienta software de configuración del iBox Modbus Server, con instrucciones de uso específicas…
- [ ] `notifier:lp-2` (LP-2) · 3 chunks token exacto en 1 doc · banderas: muy_corto
      cita ✓ «Si hay un bolígrafo tipo luz (LP-2) conectado a la NRT-586T que no esta respondiendo»
      por qué: LP-2 designa un accesorio real del fabricante: un bolígrafo tipo luz (light pen) opcional que se conecta a la estación NRT-586T, mencionado consistentemente co…
- [ ] `notifier:mini-vista` (Mini Vista) · 5 chunks token exacto en 1 doc · banderas: multipalabra,sin_digitos
      cita ✓ «**M**ini **V**ista es un **repetidor** basado en una Pantalla táctil de 7"»
      por qué: La evidencia describe Mini Vista como un producto concreto (repetidor con pantalla táctil de 7") con guía rápida de instalación y manual propio, lo que confirm…
- [ ] `notifier:mmx` (MMX) · 24 chunks token exacto en 15 docs · banderas: muy_corto,sin_digitos
      cita ✓ «El módulo MMX es un módulo direccionable que monitorea a los dispositivos»
      por qué: MMX es una referencia real de módulo monitor direccionable de Notifier, usada como token completo en el manual y como familia de las variantes MMX-1, MMX-2 y M…
- [ ] `notifier:mod-1` (MOD-1) · 4 chunks token exacto en 1 doc · banderas: muy_corto
      cita ✓ «Montaje de la Placa del Módulo MOD-1»
      por qué: El corpus documenta instrucciones de montaje e instalación del módulo MOD-1 dentro del chasis del panel AM2020/AFP1010, lo que indica que es un producto real d…
- [ ] `notifier:mp-1` (MP-1) · 4 chunks token exacto en 3 docs · banderas: muy_corto
      cita ✓ «El CHS-4M incluye el Chasis CHS-4, el Panel del Módulo MP-1, y la Cinta expansora.»
      por qué: MP-1 aparece como componente nombrado (Panel de Revestimiento/Embellecedor de Módulo) incluido en el kit CHS-4M en varios manuales, lo que confirma que es una…
- [ ] `notifier:n-elr` (N-ELR) · 34 chunks token exacto en 7 docs · banderas: muy_corto,sin_digitos
      cita ✓ «Par Canadá, se requiere el Ensamblaje de Resistencia de Fin de Línea modela N-ELR»
      por qué: N-ELR es una referencia real de Notifier: un ensamblaje de resistencia de fin de línea requerido en instalaciones de Canadá, mencionado como producto en varios…
- [ ] `notifier:nas` (NAS) · 2 chunks token exacto en 2 docs · banderas: muy_corto,palabra_generica,sin_digitos
      cita ✓ «MN-DT-741I Nas Installation and User Guide»
      por qué: La evidencia muestra un manual propio del producto ('Nas Installation and User Guide') y una referencia a su panel frontal ('at the NAS front panel'), lo que c…
- [ ] `notifier:nas-2` (NAS-2) · 39 chunks token exacto en 4 docs · banderas: muy_corto
      cita ✓ «The NAS-2 draws air from the protected area using a network of sampling pipes.»
      por qué: NAS-2 es un equipo de aspiración real de Notifier: tiene manual propio de usuario e instalación y se describe su funcionamiento como detector por aspiración co…
- [ ] `notifier:nfs-supra` (NFS Supra) · 40 chunks token exacto en 8 docs · banderas: multipalabra,sin_digitos
      cita ✓ «the Honeywell Fire Alarm Panels: Notifier:ID3000, ID50, NFS Supra»
      por qué: El modelo aparece listado explícitamente como panel de alarma de incendios de Notifier junto a otras referencias reales (ID3000, ID50), lo que confirma que es…
- [ ] `notifier:nfs4` (NFS4) · 2 chunks token exacto en 2 docs · banderas: muy_corto
      cita ✓ «NFS4 (Zones 1 to 4); NFS8 (Zones 1 to 8) and NFS12 (Zones 1 to 12)»
      por qué: La evidencia muestra NFS4 como modelo de central con 4 zonas, dentro de una familia de paneles (NFS4/NFS8/NFS12); es una referencia comercial real, no un artef…
- [ ] `notifier:notifier-inspire-e10` (Notifier INSPIRE E10) · 5 chunks token exacto en 3 docs · banderas: multipalabra
      cita ✓ «Central Notifier INSPIRE E10 con:<br/>PSU de 240 W»
      por qué: La evidencia muestra que Notifier INSPIRE E10 es una central de alarmas de detección de incendios real del fabricante Notifier by Honeywell, mencionada como pr…
- [ ] `notifier:notifier-inspire-e15` (Notifier INSPIRE E15) · 6 chunks token exacto en 2 docs · banderas: multipalabra
      cita ✓ «480 W para un rango de centrales Notifier INSPIRE E15»
      por qué: El modelo aparece de forma consistente como central de incendios del fabricante Notifier, con especificaciones técnicas propias (PSU de 480 W) e imágenes de pr…
- [ ] `notifier:nport-5210` (NPort 5210) · 6 chunks token exacto en 2 docs · banderas: multipalabra
      cita ✓ «Model Name<br/>NPort 5210»
      por qué: La evidencia muestra 'NPort 5210' explícitamente como Model Name junto a MAC Address, número de serie y versión de firmware, lo que confirma que es un producto…
- [ ] `notifier:ntg-24` (NTG 24) · 3 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «13 - ESQUEMA DE LA TARJETA NTG 24»
      por qué: NTG 24 designa una tarjeta/placa concreta del fabricante, con capítulo propio en el manual, esquema y conectores (CN0, CN1) documentados; no es una medida ni u…
- [ ] `notifier:prn-id` (PRN-ID) · 10 chunks token exacto en 4 docs · banderas: sin_digitos
      cita ✓ «la impresora opcional PRN-ID»
      por qué: La evidencia describe PRN-ID de forma consistente como una impresora opcional del fabricante para centrales, con instrucciones de instalación propias, lo que c…
- [ ] `notifier:rtm-8` (RTM-8) · 13 chunks token exacto en 3 docs · banderas: muy_corto
      cita ✓ «El módulo de Relé/Transmisor (RTM-8) proporciona ocho contactos de relés conmutados (contactos de 5…»
      por qué: RTM-8 se describe explícitamente como el Módulo de Relé/Transmisor opcional para la central AFP-200, con especificaciones técnicas propias. Es una referencia c…
- [ ] `notifier:securnet-plus` (Securnet Plus) · 27 chunks token exacto en 3 docs · banderas: multipalabra,palabra_generica,sin_digitos
      cita ✓ «Puerto serie utilizado por Securnet Plus para establecer las comunicaciones con la central»
      por qué: Securnet Plus es un producto real de Notifier: un software de gestión que se comunica con la central, documentado con manual propio y addendum oficial del fabr…
- [ ] `notifier:sensortube` (SensorTube) · 8 chunks token exacto en 2 docs · banderas: sin_digitos
      cita ✓ «El *SensorTube* consta de una o más fibras ópticas incorporadas en un tubo de acero inoxidable sell…»
      por qué: La evidencia describe el SensorTube como un componente físico concreto del sistema (tubo de acero inoxidable con fibras ópticas), con sección propia en el manu…
- [ ] `notifier:serie-800` (Serie 800) · 31 chunks token exacto en 14 docs · banderas: multipalabra,palabra_generica
      cita ✓ «La serie 800 es una gama de paneles de alarma contra incendios basados en microprocesador con capac…»
      por qué: La evidencia describe explícitamente la Serie 800 como una gama de centrales de alarma contra incendios del fabricante, con especificaciones técnicas propias.…
- [ ] `notifier:sistema-5000` (Sistema 5000) · 37 chunks token exacto en 8 docs · banderas: multipalabra,palabra_generica
      cita ✓ «Pueden utilizarse comunicadores digitales con el Sistema 5000 para formar Sistemas de Señalización…»
      por qué: El Sistema 5000 es un panel de control de incendios real de Notifier, documentado en manuales con especificaciones técnicas propias (baterías, fuente de alimen…
- [ ] `notifier:smart-3-cc-cd` (SMART 3 CC-CD) · 4 chunks token exacto en 2 docs · banderas: multipalabra,palabra_generica
      cita ✓ «# DETECTORES PARA GAS *TÓXICO* # SMART 3 CC-CD (ST/x) # *Manual de Usuario*»
      por qué: El modelo aparece como título de su propio manual de usuario y se describe su uso como detector de gas independiente, lo que confirma que es una referencia com…
- [ ] `notifier:smart-3g` (SMART 3G) · 20 chunks token exacto en 5 docs · banderas: multipalabra,palabra_generica
      cita ✓ «Para utilizar detectores SMART 3G en buses RS485, la tarjeta STS/IDI RS485 debe montarse en los det…»
      por qué: SMART 3G aparece consistentemente como nombre de un detector de gas concreto, con instrucciones de conexión y configuración propias de un producto real del fab…
- [ ] `notifier:system-5000` (System 5000) · 22 chunks token exacto en 4 docs · banderas: multipalabra,palabra_generica
      cita ✓ «Equipo de Alarma con Voz del System 5000»
      por qué: System 5000 es un panel de alarma contra incendios real de Notifier; la evidencia muestra menciones consistentes como producto con equipos asociados (AVPS-24,…
- [ ] `notifier:tcm-2` (TCM-2) · 16 chunks token exacto en 6 docs · banderas: muy_corto
      cita ✓ «ICM-4, TCM-2, TCM-4, VCM-4»
      por qué: TCM-2 aparece listado junto a otros módulos reales del fabricante (ICM-4, TCM-4, VCM-4, DCM-4) en tablas de circuitos, lo que confirma que es una referencia co…
- [ ] `notifier:tcm-4` (TCM-4) · 15 chunks token exacto en 6 docs · banderas: muy_corto
      cita ✓ «ICM-4, TCM-2, TCM-4, VCM-4»
      por qué: TCM-4 aparece listado como token completo junto a otros módulos reales de la misma familia (TCM-2, ICM-4, VCM-4, DCM-4) en tablas de circuitos y compatibilidad…
- [ ] `notifier:tg-notifier` (TG-NOTIFIER) · 40 chunks token exacto en 15 docs · banderas: sin_digitos
      cita ✓ «el uso del sistema de Supervisión y Control **TG-NOTIFIER.**»
      por qué: TG-NOTIFIER es el software de supervisión y control gráfica de Notifier, mencionado como producto en su propio manual de usuario. No presenta rasgos de artefac…
- [ ] `notifier:transponder-serie-xp` (Transponder serie XP) · 6 chunks token exacto en 6 docs · banderas: multipalabra,palabra_generica,sin_digitos
      cita ✓ «El Transponder Serie XP Para las Centrales AM2020/AFP1010»
      por qué: Aparece como título de un documento técnico de Notifier describiendo el producto para las centrales AM2020/AFP1010, y además figura en listados de catálogo con…
- [ ] `notifier:vision-plus` (Vision Plus) · 36 chunks token exacto en 11 docs · banderas: multipalabra,palabra_generica,sin_digitos
      cita ✓ «La central VISION PLUS incorpora un zumbador interno para aviso de incidencias»
      por qué: La evidencia describe la Vision Plus como una central de incendios con funciones propias, y aparece listada junto a otros paneles del fabricante (NFS Supra, ID…
- [ ] `notifier:vp-1` (VP-1) · 4 chunks token exacto en 2 docs · banderas: muy_corto
      cita ✓ «Panel de Revestimiento con ventilación VP-1»
      por qué: VP-1 designa un producto concreto del fabricante (panel de revestimiento con ventilación del sistema BE-5000/5000), citado como token completo en listas de com…
- [ ] `notifier:vs4095` (VS4095) · 1 chunk token exacto en 1 doc
      cita ✓ «Impresora Remota Keltron (Modelo VS4095)»
      por qué: La evidencia identifica explícitamente VS4095 como el modelo de una impresora remota Keltron de 24 VDC y 40 columnas, es decir, un producto real y no un artefa…
- [ ] `notifier:vsn-ll` (VSN-LL) · 9 chunks token exacto en 5 docs · banderas: sin_digitos
      cita ✓ «Requiere llave externa opcional VSN-LL»
      por qué: La evidencia muestra que VSN-LL designa un accesorio concreto del fabricante (llave/keyswitch externa opcional), citado de forma consistente en versiones en es…
- [ ] `notifier:vsn-plus` (VSN-Plus) · 3 chunks token exacto en 3 docs · banderas: sin_digitos
      cita ✓ «Este artículo afecta a las centrales RP1R, RP1R-Supra, VSN-RP1R-PLUS2, VSN-Plus y VSN-2PLUS»
      por qué: VSN-Plus aparece nombrada explícitamente como una central del fabricante junto a otras referencias reales, y en [3] se dan instrucciones de instalación específ…
- [ ] `notifier:xp5-c` (XP5-C) · 14 chunks token exacto en 1 doc · banderas: muy_corto
      cita ✓ «Transponder XP5-M & XP5-C | Transponder de la Serie XP5»
      por qué: XP5-C aparece como producto identificado (transponder de la Serie XP5 de Notifier) con contexto técnico coherente: diagramas de alambrado y circuito telefónico…
- [ ] `notifier:xp5-m` (XP5-M) · 10 chunks token exacto en 1 doc · banderas: muy_corto
      cita ✓ «Transponder XP5-M & XP5-C | Transponder de la Serie XP5»
      por qué: XP5-M aparece identificado explícitamente como transpondedor de la Serie XP5 de Notifier y listado entre los componentes del sistema (junto a XP5-C, SDX-751, e…
- [ ] `notifier:xpdp` (XPDP) · 13 chunks token exacto en 5 docs · banderas: muy_corto,sin_digitos
      cita ✓ «**XPDP** Panel Embellecedor del Transponder»
      por qué: XPDP aparece en una lista de productos del fabricante con su descripción propia (Panel Embellecedor del Transponder) y en otro fragmento como componente físico…
- [ ] `notifier:ze4` (ZE4) · 6 chunks token exacto en 2 docs · banderas: muy_corto
      cita ✓ «El módulo ZE4 proporciona cuatro zonas adicionales.»
      por qué: ZE4 es una tarjeta expansora de 4 zonas real del fabricante, descrita como producto con función propia y listada como opción instalable junto a su variante ZS4.
- [ ] `notifier:zs4` (ZS4) · 16 chunks token exacto en 3 docs · banderas: muy_corto
      cita ✓ «ZS4 - Tarjeta expansora de 4 Zonas y 4 Sirenas (incluye tarjeta de LEDS de zona para instalarla en…»
      por qué: ZS4 es un módulo expansor de zonas real de Notifier, descrito consistentemente en varios documentos como tarjeta de 4 zonas con circuitos de sirena, distinguid…
- [ ] `pepperl-fuchs:z705` (Z705) · 1 chunk token exacto en 1 doc · banderas: muy_corto
      cita ✓ «Barrera Zener Z040, Z041, Z042 Z705, Z710, Z713, Z715»
      por qué: Z705 aparece como token completo en la lista oficial de barreras Zener del manual de Pepperl+Fuchs, junto a otras referencias de la misma familia. Es una refer…
- [ ] `securiton:acb-35` (ACB 35) · 11 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «BCB 35 en el ASD 535-1 y -2** o **ACB 35 en el ASD 535-3 y -4»
      por qué: ACB 35 es una placa de circuito impreso real del panel de visualización del ASD 535 de Securiton, mencionada como componente sustituible con variante según mod…
- [ ] `securiton:afs-32` (AFS 32) · 3 chunks token exacto en 2 docs · banderas: multipalabra
      cita ✓ «Sensor de flujo de aire AFS 32 | 11-2200007-01-XX»
      por qué: AFS 32 aparece como componente real (sensor de flujo de aire) con número de artículo del fabricante y figura en la lista de componentes eléctricos del sistema…
- [ ] `securiton:afu-32` (AFU 32) · 8 chunks token exacto en 2 docs · banderas: multipalabra
      cita ✓ «Unidad de ventilación completa para la aspiración AFU 32 | 11-2200008-01-XX»
      por qué: AFU 32 aparece como referencia comercial real con número de artículo propio (11-2200008-01-XX) y se cita en listas de componentes e instrucciones de mantenimie…
- [ ] `securiton:amb-31` (AMB 31) · 36 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «Cap. 5.2.10 Asignación de terminales del AMB 31, XLM 35 y RIM 36»
      por qué: AMB 31 aparece como módulo/placa concreta del fabricante junto a otros módulos reales (XLM 35, RIM 36), con capítulo propio de asignación de terminales y etiqu…
- [ ] `securiton:amb-33` (AMB 33) · 38 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «AMB 33 | = ASD Main Board»
      por qué: AMB 33 designa la placa principal (Main Board) del detector de aspiración ASD de Securiton, con asignación de terminales e instrucciones de puesta en marcha pr…
- [ ] `securiton:amb-35` (AMB 35) · 39 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «el Main Board AMB 35 del interior del dispositivo incluye una indicación alfanumérica y dos visuali…»
      por qué: AMB 35 designa la placa principal (Main Board) del detector de aspiración ASD 535 de Securiton, mencionada consistentemente como componente sustituible y con f…
- [ ] `securiton:bcb-35` (BCB 35) · 21 chunks token exacto en 2 docs · banderas: multipalabra
      cita ✓ «BCB 35 | = Circuito impreso sin indicación del nivel de humo «Basic Control Board»»
      por qué: BCB 35 es una placa de circuito impreso real («Basic Control Board») del fabricante, usada en los detectores ASD 535, con definición explícita y procedimientos…
- [ ] `securiton:leb-35` (LEB 35) · 26 chunks token exacto en 3 docs · banderas: multipalabra
      cita ✓ «LEB 35 | = Módulo de ampliación para un segundo tubo sensor (LTHD Extension Board)»
      por qué: LEB 35 es una placa de expansión real del detector térmico lineal SecuriSens ADW 535 de Securiton, descrita explícitamente como módulo de ampliación en el manu…
- [ ] `securiton:lmb-35` (LMB 35) · 38 chunks token exacto en 3 docs · banderas: multipalabra
      cita ✓ «La conexión se realiza directamente a la placa base LMB 35 o a la placa de expansión LEB 35 del det…»
      por qué: LMB 35 es la placa base (Main Board) del detector térmico lineal SecuriSens ADW 535 de Securiton, descrita como componente real con funciones y conexiones prop…
- [ ] `securiton:lsu-35` (LSU 35) · 17 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «El LSU 35 consta de un sensor de presión diferencial totalmente electrónico, una bomba de presión y…»
      por qué: LSU 35 es un componente real del sistema ADW 535 de Securiton (LTHD Supervising Unit), descrito con composición física y materiales propios, no un artefacto de…
- [ ] `securiton:smm-535` (SMM 535) · 34 chunks token exacto en 4 docs · banderas: multipalabra
      cita ✓ «El módulo maestro de la red ASD es el SMM 535, a través del cual se realiza la conexión a un PC.»
      por qué: La evidencia describe el SMM 535 como el módulo maestro de la red ASD de Securiton, con función y contexto técnico claros, lo que confirma que es una referenci…
- [ ] `securiton:ssd-31` (SSD 31) · 4 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «Sensor de humo SSD 31 en embalaje de protección»
      por qué: SSD 31 aparece de forma consistente como el sensor de humo del sistema ASD 531, listado como componente eléctrico y como pieza suministrada, lo que confirma qu…
- [ ] `securiton:ssd-533` (SSD 533) · 14 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «En el ASD 533, el **sensor de humo SSD 533** está incluido por el fabricante.»
      por qué: SSD 533 se identifica repetidamente como el sensor de humo incluido en el aspirador ASD 533, con material propio (Lexan PC) y aparece siempre como token comple…
- [ ] `sense-ware:sm21` (SM21) · 6 chunks token exacto en 2 docs · banderas: muy_corto
      cita ✓ «Montar el detector con la ayuda del pivote de montaje opcional SM21 (consulte el manual de SM21)»
      por qué: SM21 es un accesorio real del fabricante: un kit de pivote/montaje giratorio opcional para detectores de llama, con manual propio y figura de dimensiones. Las…
- [ ] `sensitron:pl4+` (PL4+) · 40 chunks token exacto en 2 docs · banderas: muy_corto
      cita ✓ «El software de la central PL4+ está programado para realizar, periódicamente una prueba automática»
      por qué: PL4+ aparece consistentemente como el nombre de una central de detección en su propio manual de usuario e instalación, con 40 menciones como token completo y s…
- [ ] `spectrex:winhost` (WinHost) · 9 chunks token exacto en 1 doc · banderas: sin_digitos
      cita ✓ «WinHost Configuration and Diagnostic Software ## 40/40 Flame Detectors # User Guide SPECTREX»
      por qué: WinHost es el software oficial de configuración y diagnóstico de Spectrex para los detectores de llama 40/40, con guía de usuario propia; es un producto real d…
- [ ] `systemsensor:8100e-faast` (8100E FAAST) · 4 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «# 8100E FAAST # Fire Alarm Aspiration Sensing Technology® SYSTEM SENSOR»
      por qué: El modelo 8100E FAAST aparece como título de producto en instrucciones de instalación y mantenimiento de System Sensor, correspondiendo a un detector de humo p…
- [ ] `systemsensor:agileiq` (AgileIQ) · 40 chunks token exacto en 4 docs · banderas: sin_digitos
      cita ✓ «El software AgileIQ™ dispone de la prestación de generar automáticamente un informe de configuració…»
      por qué: AgileIQ es una aplicación de software real de System Sensor, mencionada con marca registrada (™) y descrita funcionalmente en el manual como herramienta de con…
- [ ] `systemsensor:st-1.5` (ST-1.5) · 4 chunks token exacto en 4 docs · banderas: muy_corto
      cita ✓ «| ST-1.5 | 1 to 2 ft. (0.3 to 0.6 m) | | ST-3 | 2 to 4 ft. (0.6 to 1.2 m) |»
      por qué: ST-1.5 aparece en varias tablas de tubos de muestreo junto a otras referencias de la misma serie (ST-3, ST-5), asociado a rangos de anchura de conducto; es un…
- [ ] `systemsensor:st-10` (ST-10) · 8 chunks token exacto en 4 docs · banderas: medida_en_contexto,muy_corto
      cita ✓ «Sampling of air in ducts wider than 8 feet is accomplished by using the ST-10 inlet sampling tube.»
      por qué: ST-10 es un tubo de muestreo de entrada real de System Sensor para detectores de conducto, con longitud especificada (8 a 12 pies) dentro de una familia de pro…
- [ ] `systemsensor:st-3` (ST-3) · 4 chunks token exacto en 4 docs · banderas: medida_en_contexto,muy_corto
      cita ✓ «| ST-3 | 2 to 4 ft. | (0.6 to 1.2 m) |»
      por qué: ST-3 aparece en tablas de selección junto a otras referencias de la misma familia (ST-1.5, ST-5, ST-10), cada una asociada a un rango de anchura de conducto; e…
- [ ] `systemsensor:st-5` (ST-5) · 8 chunks token exacto en 4 docs · banderas: medida_en_contexto,muy_corto
      cita ✓ «An alternate method to using the ST-10 is to use two ST-5 inlet tubes.»
      por qué: ST-5 designa un tubo de muestreo (inlet tube) de System Sensor, referenciado explícitamente como componente instalable junto a otras variantes de la misma fami…
- [ ] `testifire:solo-760` (Solo 760) · 3 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «Solo 760 Battery Baton: 920 millas»
      por qué: Solo 760 es una batería Baton real del fabricante, usada para alimentar el equipo Testifire; aparece como producto identificable en instrucciones y tablas de e…
- [ ] `testifire:tc3` (TC3) · 6 chunks token exacto en 2 docs · banderas: muy_corto
      cita ✓ «Las unidades principales Testifire se suministran con una cápsula de humo TS3 y una cápsula de CO T…»
      por qué: TC3 designa consistentemente la cápsula de CO de Testifire en múltiples documentos, apareciendo como token completo junto a otros productos del catálogo (TS3,…
- [ ] `testifire:ts3` (TS3) · 6 chunks token exacto en 2 docs · banderas: muy_corto
      cita ✓ «Cápsulas de repuesto Cápsula de humo TS3 Cápsula de CO TC3»
      por qué: TS3 es la referencia comercial real de la cápsula de humo de repuesto para los equipos Testifire, mencionada de forma consistente como producto en varios docum…
- [ ] `unresolved:autosat-10` (AutoSAT 10) · 24 chunks token exacto en 2 docs · banderas: multipalabra
      cita ✓ «Manual de AutoSAT 10 Honeywell Life Safety Iberia»
      por qué: El modelo aparece como título de un manual oficial del fabricante Honeywell Life Safety Iberia, y se describe una instalación del equipo con tubo de aspiración…
- [ ] `unresolved:autosat-20` (AutoSAT 20) · 24 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «El AutoSAT 20 se suministra de serie con dos detectores MI-LZR»
      por qué: El corpus incluye un manual dedicado al AutoSAT 20 y describe su dotación de serie con detectores, lo que confirma que es un producto real del fabricante (Hone…
- [ ] `unresolved:calypso-ii` (CALYPSO-II) · 5 chunks token exacto en 2 docs · banderas: sin_digitos
      cita ✓ «El detector de humo Calypso-II cuenta con una función que permite neutralizar la señal de alarma»
      por qué: La evidencia muestra que Calypso-II designa un detector de humo concreto del fabricante, con menciones como token completo en contexto de producto. La variante…
- [ ] `unresolved:calypso-ii-r` (Calypso-II-R) · 3 chunks token exacto en 1 doc · banderas: sin_digitos
      cita ✓ «CALYPSO-II-R Detector autónomo de humo vía radio»
      por qué: El modelo aparece como título de producto con descripción funcional clara (detector autónomo de humo vía radio) y se usa consistentemente como token completo e…
- [ ] `unresolved:ds-10` (DS 10) · 6 chunks token exacto en 1 doc · banderas: multipalabra,muy_corto
      cita ✓ «DS 5 + DS 10 -GL-Version These sounders have been designed and certified in accordance with the Gui…»
      por qué: La evidencia muestra que DS 10 es una sirena (sounder) real del fabricante, con versiones especiales certificadas y diagramas de nivel sonoro propios, lo que c…
- [ ] `unresolved:ds-5` (DS 5) · 4 chunks token exacto en 1 doc · banderas: multipalabra,muy_corto
      cita ✓ «8.1 DS 5 + DS 10 -GL-Version These sounders have been designed and certified in accordance with the…»
      por qué: DS 5 aparece como designación de producto (sirena/sounder) con versiones especiales, opciones de control de volumen y selección de tonos, típico de una referen…
- [ ] `unresolved:ess-rp1r-plus` (ESS RP1r Plus) · 3 chunks token exacto en 2 docs · banderas: multipalabra,palabra_generica
      cita ✓ «RP1r Supra / Vision Rp1r Plus / ESS RP1r Plus Honeywell»
      por qué: El modelo aparece como token completo en la portada de guías rápidas de montaje de Honeywell, listado junto a otras variantes reales de la familia RP1r (Supra,…
- [ ] `unresolved:h-gtw-n` (H-GTW-N) · 5 chunks token exacto en 3 docs · banderas: sin_digitos
      cita ✓ «El modelo **H-GTW-N** permite realizar la integración igualmente a cualquiera de las centrales indi…»
      por qué: La evidencia describe H-GTW-N explícitamente como un modelo de pasarela para integración de centrales, junto a su variante H-GTW-1 en tabla de modos y tensione…
- [ ] `unresolved:hls-ps25` (HLS PS25) · 23 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «HLS PS25 & HLS PS50 User Manual»
      por qué: El modelo aparece como token completo en el título del manual de usuario del fabricante junto a su producto hermano HLS PS50, y se menciona la 'HLS PS Series',…
- [ ] `unresolved:hls-ps50` (HLS PS50) · 23 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «HLS PS25 & HLS PS50 User Manual ## Pre-installation check list Before selecting the location for th…»
      por qué: HLS PS50 aparece como modelo en el título del manual de usuario del fabricante, junto a su variante HLS PS25 y dentro de la serie HLS PS, lo que confirma que e…
- [ ] `unresolved:id50` (ID50) · 26 chunks token exacto en 14 docs · banderas: muy_corto
      cita ✓ «Panel ID50 - Manual de funcionamiento»
      por qué: ID50 es un panel de incendios real de Notifier (Honeywell), citado como producto en su propio manual de funcionamiento y en listas de compatibilidad junto a ID…
- [ ] `unresolved:id60` (ID60) · 24 chunks token exacto en 10 docs · banderas: muy_corto
      cita ✓ «Dos detectores de humo, recomendables 2 sensores VIEW (solo con centrales ID60, ID3000, AFP400).»
      por qué: ID60 es una central de detección de incendios real de Notifier, mencionada como producto junto a otras centrales (ID3000, AFP400) y con manual propio (Centrale…
- [ ] `unresolved:itac-2.0` (ITAC 2.0) · 3 chunks token exacto en 1 doc · banderas: multipalabra
      cita ✓ «La pasarela ITAC 2.0 permite comunicar las incidencias de las centrales de Extinción Serie RP»
      por qué: La evidencia describe ITAC 2.0 como una pasarela de comunicación con guía técnica propia de Honeywell (GT-HLSI-1102), lo que confirma que es un producto comerc…
- [ ] `unresolved:mi-lzr` (MI-LZR) · 36 chunks token exacto en 10 docs · banderas: sin_digitos
      cita ✓ «MI-LZR Det Laser de Humo (Alta sensibilidad)»
      por qué: El modelo aparece como token completo en 36 menciones, descrito explícitamente como un detector láser de humo de alta sensibilidad y citado como componente de…
- [ ] `unresolved:s-hsf` (S-HSF) · 17 chunks token exacto en 1 doc · banderas: muy_corto,sin_digitos
      cita ✓ «S-HSF MANUAL DE CONFIGURACIÓN Y FUNCIONAMIENTO»
      por qué: S-HSF es un producto software real de Honeywell Life Safety Iberia, con manual propio de configuración, ejecutable (S-HSF.exe) y versión (V2.8.0) documentados…
- [ ] `unresolved:simei` (SIMEI) · 5 chunks token exacto en 1 doc · banderas: sin_digitos
      cita ✓ «Honeywell ## Caja estanca SIMEI ## Waterproof Box SIMEI»
      por qué: SIMEI aparece como nombre de producto propio (caja estanca/waterproof box) de Honeywell, con descripción de instalación y características físicas, siempre como…
- [ ] `unresolved:tg-gsm` (TG-GSM) · 10 chunks token exacto en 2 docs · banderas: sin_digitos
      cita ✓ «# COMPONENTES DEL TG-GSM»
      por qué: El modelo aparece como token completo en un manual con sección de componentes, planos técnicos y una FAQ sobre su funcionamiento (envío de SMS), lo que indica…
- [ ] `unresolved:tg-hlsi` (TG HLSI) · 17 chunks token exacto en 1 doc · banderas: multipalabra,sin_digitos
      cita ✓ «Para configurar el software de Terminal Gráfico TG HLSI»
      por qué: TG HLSI es el nombre comercial del software de Terminal Gráfico (Sistema de Gestión Gráfica) de Honeywell Life Safety Iberia, con guía rápida de instalación pr…
- [ ] `unresolved:tg-honeywell` (TG-HONEYWELL) · 38 chunks token exacto en 9 docs · banderas: sin_digitos
      cita ✓ «Al arrancar el software **TG-HONEYWELL** se presenta el plano principal»
      por qué: TG-HONEYWELL aparece en tres documentos distintos como nombre propio de un software/sistema de gestión gráfica del fabricante, siempre como token completo y en…
- [ ] `unresolved:tg-modbus` (TG MODBUS) · 5 chunks token exacto en 2 docs · banderas: multipalabra,sin_digitos
      cita ✓ «Configuración TG MODBUS ## *Características* MODBUS-RTU –Serie / IP Servidor de registros esclavo d…»
      por qué: TG MODBUS es una pasarela/servidor Modbus real de Honeywell Life Safety Iberia, con documento técnico propio (HLSI-TI-006) que describe su configuración, carac…
- [ ] `unresolved:vision-plus` (VISION PLUS) · 36 chunks token exacto en 11 docs · banderas: multipalabra,palabra_generica,sin_digitos
      cita ✓ «La central VISION PLUS incorpora un zumbador interno para aviso de incidencias»
      por qué: La evidencia describe VISION PLUS explícitamente como una central de incendios de Honeywell Life Safety Iberia, con manual propio y aparición en listas de pane…
- [ ] `unresolved:vision-rp1r-plus` (Vision RP1r Plus) · 3 chunks token exacto en 2 docs · banderas: multipalabra,palabra_generica
      cita ✓ «RP1r Supra / Vision Rp1r Plus / ESS RP1r Plus Honeywell»
      por qué: El modelo aparece como token completo en el título de manuales oficiales de Honeywell, listado junto a otras variantes de la familia RP1r (Supra, ESS), lo que…
- [ ] `unresolved:vsn-co` (VSN-CO) · 12 chunks token exacto en 3 docs · banderas: sin_digitos
      cita ✓ «El detector VSN-CO es el dispositivo puntual de medida de concentración de monóxido de carbono.»
      por qué: La evidencia describe explícitamente el VSN-CO como un detector de CO del sistema VSN PARK, con contexto técnico coherente (hasta 16 detectores por zona). Es u…
- [ ] `xtralis:honeywell-smartconfig-app` (Honeywell SmartConfig App) · 6 chunks token exacto en 1 doc · banderas: multipalabra,palabra_generica,sin_digitos
      cita ✓ «se muestra una lista de dispositivos en los que se ha probado y verificado la aplicación Honeywell…»
      por qué: La evidencia muestra que Honeywell SmartConfig App es una aplicación móvil real del fabricante, usada para configurar y supervisar detectores, mencionada de fo…
- [ ] `xtralis:icam-ias` (ICAM IAS) · 4 chunks token exacto en 1 doc · banderas: multipalabra,sin_digitos
      cita ✓ «Se recomienda configurar todos los detectores ICAM (excepto los detectores ICAM IAS) con el softwar…»
      por qué: La evidencia muestra que ICAM IAS designa un detector concreto del fabricante Xtralis, con sección propia de configuración en el manual y mención diferenciada…
- [ ] `xtralis:icam-ift` (ICAM IFT) · 6 chunks token exacto en 1 doc · banderas: multipalabra,sin_digitos
      cita ✓ «La capacidad de los detectores ICAM IFT puede probarse mediante una prueba diagnóstica»
      por qué: ICAM IFT es una serie real de detectores de humo por aspiración de Xtralis; la evidencia lo menciona como detector configurable y con guía de producto propia,…
- [ ] `xtralis:icam-ils` (ICAM ILS) · 4 chunks token exacto en 1 doc · banderas: multipalabra,sin_digitos
      cita ✓ «Configuración del detector ICAM ILS En este apartado se identifican algunas funciones clave que el…»
      por qué: ICAM ILS aparece como un detector concreto del fabricante Xtralis, con apartado propio de configuración y mencionado junto a otros modelos de la misma serie (I…
- [ ] `xtralis:lt-acc-dcl` (LT-ACC-DCL) · 3 chunks token exacto en 1 doc · banderas: sin_digitos
      cita ✓ «| LT-ACC-DCL | 10' Digital Output Cable | Digital output cable for all Li-ion»
      por qué: El modelo aparece en una tabla de accesorios del fabricante con descripción propia (cable de salida digital de 10 pies) y se menciona funcionalmente en el manu…
- [ ] `xtralis:vesda-vli` (VESDA VLI) · 40 chunks token exacto en 2 docs · banderas: multipalabra,sin_digitos
      cita ✓ «VESDA VLI Product Guide»
      por qué: VESDA VLI es un detector de humo por aspiración real de Xtralis; la evidencia muestra su guía de producto oficial ('VESDA VLI Product Guide') con 40 menciones…

### §0.C — «revisar» → **CONFIRMAR** (144)

Candidates ya presentes en el catálogo, atestados **con frontera de palabra** en el
contenido de `chunks_v2` + cita verificada a texto completo + sin colisión de catálogo.
Clases del lote completo: atestado_en_contenido=216, sin_atestacion_doc_presente=31, sin_atestacion_doc_presente_renombrado=14

- [ ] `detnov:cad-171-r` (CAD-171 (R) · Detnov) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `Manual_CAD-171-MI-716-es`
      cita ✓ «**1. Product identification** Identificación producto Model Modelos CAD-171, CAD-171 (R)»
- [ ] `detnov:pad-20` (PAD-20 · edelnov) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `Manual_PAD-20 (MU 591 m 2024 a)`
      cita ✓ «# PILOTO INDICADOR DE ACCIÓN ## PAD-20»
- [ ] `fidegas:cs4-digital` (CS4 Digital · FIDEGAS) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `Manual-de-Usuario-CS4`
      cita ✓ «**CENTRAL DE ALARMAS** CE **CS4 Digital Firmware 1.2** **Tensión: 110-230 Vac 50/60Hz**»
- [ ] `kidde:2010-1-nb` (2010-1-NB · Kidde Commercial) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `bcn-3100017-es_r002_nc_series_fire_alarm_co…`
      cita ✓ «Consulte la Hoja de instalación de la tarjeta de red 2010-1-NB para obtener información detallada acerca…»
- [ ] `lda:ldaneotfl` (LDANEOTFL · LDA) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `NEO8060S02-MU - MANUAL DE USUARIO SERIE NEO…`
      cita ✓ «* LDANEOTFL. Terminador de línea de altavoces»
- [ ] `morley:mi-cmo` (MI-CMO · Morley-IAS) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `Rearme-remoto-en-central-DXc-Connexion`
      cita ✓ «Utilizar un módulo de salida MI-CMO, configurado como libre de tensión para que se active con cualquier…»
- [ ] `morley:vsn-12-plus2` (VSN-12 Plus2 · Honeywell Life Safety Iberia) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `HLSI-MN-025_NFS Supra`
      cita ✓ «Este manual es válido para las centrales convencionales de alarma y detección de incendios con las sigui…»
- [ ] `morley:vsn-4-plus2` (VSN-4 Plus2 · Honeywell Life Safety Iberia) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `HLSI-MN-025_NFS Supra`
      cita ✓ «Este manual es válido para las centrales convencionales de alarma y detección de incendios con las sigui…»
- [ ] `morley:vsn-8-plus2` (VSN-8 Plus2 · Honeywell Life Safety Iberia) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `HLSI-MN-025_NFS Supra`
      cita ✓ «Este manual es válido para las centrales convencionales de alarma y detección de incendios con las sigui…»
- [ ] `morley:vsn4-2plus` (VSN4-2Plus · Honeywell) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `HLSI-MN-025-I_NFS Supra Series`
      cita ✓ «This manual is valid for the following control panel models: * **NFS-Supra** - **NFS4-Supra** - **NFS8-S…»
- [ ] `morley:vsn8-2plus` (VSN8-2Plus · Honeywell) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `HLSI-MN-025-I_NFS Supra Series`
      cita ✓ «This manual is valid for the following control panel models: * **NFS-Supra** * **NFS4-Supra** * **NFS8-S…»
- [ ] `notifier:am-82-top` (AM-82-TOP · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `AM-8200 Manual Instalacion`
      cita ✓ «# 2 - Instalación AM-8200 y AM-8200-BB con AM-82-TOP Estructura metálica para la instalación fija de cab…»
- [ ] `notifier:avd-evj` (AVD EVJ · Notifier) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `PAN_AVD1`
      cita ✓ «350g Versión AVD EVJ<br/>500g Versión AVD EVJ /A<br/>1200g Versión AVD EVJ /A/230»
- [ ] `notifier:cab-sa1` (CAB-SA1 · Notifier) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `MIDT190`
      cita ✓ «| Cajas de prolongación: | CAB-SA1 | 2 |»
- [ ] `notifier:cab-sb2` (CAB-SB2 · Notifier) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `MIDT190`
      cita ✓ «| Cajas de prolongación: | CAB-SA1 | 2 | | | CAB-SB2 | 2 |»
- [ ] `notifier:cfp-ze4` (CFP-ZE4 · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MADT020 (brand-tier=mecanico) | alias-canon…`
      cita ✓ «# Módulos expansores de salida y de zona # CFP-ZE4/CFP-ZS4»
- [ ] `notifier:cfp-zs4` (CFP-ZS4 · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MADT020 (brand-tier=mecanico) | alias-canon…`
      cita ✓ «# CFP-ZE4/CFP-ZS4»
- [ ] `notifier:dp-aa` (DP-AA · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MNDT060`
      cita ✓ «**DP-AA:** El Panel de Revestimiento Interno cubre el área de la caja que rodea a los módulos.»
- [ ] `notifier:e-sib-m` (E-SIB-M · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `AM 8200G manual instalacion Rv 3 (brand-tie…`
      cita ✓ «E-SIB-M - Mochila VERDE para habilitar la salida Ethernet con protocolo MODBUS.»
- [ ] `notifier:hon-cgw-mbb` (HON-CGW-MBB · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `4188-1122-ES issue 4_04-2025_Cyb`
      cita ✓ «## 1.2 Productos NOTIFIER aplicables * HOP-131-206 * HOP-133-206 * HOP-134-412 * HOP-136-412 * HON-CGW-M…»
- [ ] `notifier:hop-133-206` (HOP-133-206 · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `4188-1122-ES issue 4_04-2025_Cyb`
      cita ✓ «## 1.2 Productos NOTIFIER aplicables * HOP-131-206 * HOP-133-206 * HOP-134-412»
- [ ] `notifier:hop-136-412` (HOP-136-412 · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `4188-1122-ES issue 4_04-2025_Cyb`
      cita ✓ «## 1.2 Productos NOTIFIER aplicables * HOP-131-206 * HOP-133-206 * HOP-134-412 * HOP-136-412»
- [ ] `notifier:hop-238-110` (HOP-238-110 · Notifier) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `HOP-138-9ES issue 5_11-2025_In`
      cita ✓ «HOP-238-110 Kit de montaje semi empotrado para la central E10 (opcional)»
- [ ] `notifier:hop-238-115` (HOP-238-115 · Notifier) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `HOP-138-9ES issue 5_11-2025_In`
      cita ✓ «HOP-238-115 Kit de montaje semi empotrado para la central E15 (opcional)»
- [ ] `notifier:hssd-2a` (HSSD-2A · Notifier) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `MIDT731`
      cita ✓ «permite controlar el estado de hasta 99 equipos de aspiración HSSD-2A conectados en bus RS485»
- [ ] `notifier:hssd-2n` (HSSD-2N · Notifier) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `MIDT731`
      cita ✓ «La APIC dispone de dos modos de funcionamiento, con una dirección (HSSD-2A/Minilaser) y con varias direc…»
- [ ] `notifier:keltron-90` (Keltron 90 · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MNDT120`
      cita ✓ «IMPRESORA KELTRON 90 MODELO #VS4095/5 S2»
- [ ] `notifier:n-gas-100` (N-GAS-100 · Honeywell Life Safety Iberia) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `MNDT530P`
      cita ✓ «del módulo de zona P-100 y de los sensores remotos NCO-100 y N-GAS-100»
- [ ] `notifier:np12-12fr` (NP12-12FR · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `HOP-138-9ES issue 5_11-2025_In`
      cita ✓ «NP12-12FR Batería YUASA 12 AH-12V Ignífuga (solo para cajas E10)»
- [ ] `notifier:np24-12fr` (NP24-12FR · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `HOP-138-9ES issue 5_11-2025_In`
      cita ✓ «NP24-12FR Batería YUASA NP 24 AH-12V Ignífuga (para cajas E10 y E15)»
- [ ] `notifier:np38-12fr` (NP38-12FR · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `HOP-138-9ES issue 5_11-2025_In`
      cita ✓ «NP38-12FR Batería YUASA NP 38 AH-12V Ignífuga (solo para una caja E15)»
- [ ] `notifier:nrt-586tf` (NRT-586TF · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `15090SP`
      cita ✓ «Enlace de fibra óptica de la NRT (NRT-586TF) 115/230 VCA»
- [ ] `notifier:nrt-586twf` (NRT-586TWF · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `15090SP`
      cita ✓ «Enlace de fibra óptica y cable de la NRT (NRT-586TWF) 115/230 VCA»
- [ ] `notifier:nxfi-copt22` (NXFI-COPT22 · FAAST) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `ASD in Custodial Applications_ES`
      cita ✓ «la unidad FAAST LT™ ha sido reconfigurada y homologada como NXFI-COPT22 para su uso específico en celdas…»
- [ ] `notifier:pan-2` (PAN-2 · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MNDT1117`
      cita ✓ «## ART. 5554 (PAN-2) ### PANEL LUMINOSO IMPERMEABLE»
- [ ] `notifier:pinnacle-7251` (PINNACLE 7251 · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `AM-8200-manu-prog-spa`
      cita ✓ «Ejemplo de programación de un sensor CLIP con Tipo-HW «PINN» PINNACLE 7251 (Detector láser)»
- [ ] `notifier:pk-afp200e` (PK-AFP200E · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MCDT120`
      cita ✓ «# PK-AFP200E ## PARA PROGRAMACIÓN FUERA DE LÍNEA DE CENTRALES ANALÓGICAS AFP200»
- [ ] `notifier:pkid200e` (PKID200E · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MCDT150`
      cita ✓ «Programación Fuera de Línea PKID200E para la Central Analógica contra Incendios ID200»
- [ ] `notifier:rp1001e` (RP1001E · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MADT100_01`
      cita ✓ «Protección contra RFI en las centrales RP1001E y RP1002E»
- [ ] `notifier:sdx-751-tem` (SDX-751-TEM · Notifier) · frontera hoy 26 · id-provenance (NO es la fuente de la cita) `AM-8200-manu-prog-spa (brand-tier=mecanico)…`
      cita ✓ «b. Optiplex (Comb. térmico/humo) SDX-751TEM»
- [ ] `notifier:smart-1` (SMART 1 · Notifier) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `MNDT607`
      cita ✓ «Esta pauta se aplica a los detectores de gases o vapores de la marca SENSITRON del tipo SMART 1»
- [ ] `notifier:st.pl4+` (ST.PL4+ · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MNDT516 (brand-tier=mecanico) | alias-canon…`
      cita ✓ «# ST.PL4+ ## MANUAL DE USUARIO E INSTALACIÓN»
- [ ] `notifier:tg-6000-net` (TG-6000 Net · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MNDT955`
      cita ✓ «# TG-6000 Net *PROGRAMA DE GRÁFICOS Y GESTIÓN PARA CENTRALES ANALÓGICAS AM6000 DE NOTIFIER* ## Manual de…»
- [ ] `notifier:ucip-modbus-e20m` (UCIP-MODBUS E20M · Honeywell) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `UCIP MODBUS AM8200 V5.1`
      cita ✓ «El módulo UCIP-MODBUS E20M, se conecta a las centrales por puerto RS232 (modo impresora)»
- [ ] `notifier:verifire-1020` (VERIFIRE 1020 · Notifier) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `MADT285_01`
      cita ✓ «| VeriFire 1020 | No | No | Sí»
- [ ] `pepperl-fuchs:z040` (Z040 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Barrera Zener Z040, Z041, Z042»
- [ ] `pepperl-fuchs:z041` (Z041 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Barrera Zener Z040, Z041, Z042»
- [ ] `pepperl-fuchs:z042` (Z042 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Barrera Zener Z040, Z041, Z042»
- [ ] `pepperl-fuchs:z710` (Z710 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Barrera Zener Z040, Z041, Z042 Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755,…»
- [ ] `pepperl-fuchs:z713` (Z713 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Barrera Zener Z040, Z041, Z042 Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728»
- [ ] `pepperl-fuchs:z715.1k` (Z715.1K · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Barrera Zener Z040, Z041, Z042 Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL»
- [ ] `pepperl-fuchs:z722` (Z722 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Barrera Zener Z040, Z041, Z042 Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755,…»
- [ ] `pepperl-fuchs:z728.cl` (Z728.CL · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757»
- [ ] `pepperl-fuchs:z731` (Z731 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z765»
- [ ] `pepperl-fuchs:z755` (Z755 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Barrera Zener Z040, Z041, Z042 Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755,…»
- [ ] `pepperl-fuchs:z757` (Z757 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z765»
- [ ] `pepperl-fuchs:z763` (Z763 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z765, Z772,…»
- [ ] `pepperl-fuchs:z764` (Z764 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z765, Z772,…»
- [ ] `pepperl-fuchs:z765` (Z765 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z765, Z772,…»
- [ ] `pepperl-fuchs:z772` (Z772 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z765, Z772,…»
- [ ] `pepperl-fuchs:z778` (Z778 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Barrera Zener Z040, Z041, Z042 Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755,…»
- [ ] `pepperl-fuchs:z779.h` (Z779.H · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z765, Z772,…»
- [ ] `pepperl-fuchs:z786` (Z786 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z765, Z772,…»
- [ ] `pepperl-fuchs:z787.h` (Z787.H · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z765, Z772,…»
- [ ] `pepperl-fuchs:z788.h` (Z788.H · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z765, Z772,…»
- [ ] `pepperl-fuchs:z788.r` (Z788.R · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z786, Z787, Z787.H, Z788, Z788.R, Z788.H, Z789, Z796»
- [ ] `pepperl-fuchs:z789` (Z789 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z731, Z755, Z757, Z763, Z764, Z765, Z772, Z778, Z779, Z779.H, Z786, Z787, Z787.H, Z788, Z788.R, Z788.H,…»
- [ ] `pepperl-fuchs:z796` (Z796 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z765, Z772,…»
- [ ] `pepperl-fuchs:z810.cl` (Z810.CL · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z813` (Z813 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z822` (Z822 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z828.h` (Z828.H · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z857` (Z857 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z864` (Z864 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z865` (Z865 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z872` (Z872 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z878` (Z878 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z886` (Z886 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z887` (Z887 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z888.h` (Z888.H · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z896` (Z896 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.H, Z896»
- [ ] `pepperl-fuchs:z905` (Z905 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z910` (Z910 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z915.1k` (Z915.1K · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z922` (Z922 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z928` (Z928 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z954` (Z954 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z955` (Z955 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z960` (Z960 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z961.h` (Z961.H · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z964` (Z964 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z965` (Z965 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z966.h` (Z966.H · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z967` (Z967 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z969` (Z969 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pepperl-fuchs:z972` (Z972 · Pepperl+Fuchs) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728`
      cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.H, Z967, Z…»
- [ ] `pyra:py-x-m-05-ssm` (PY X-M-05-SSM · PYRA) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `085501987j_PY X-M-05_10_Installation_manual…`
      cita ✓ «PY X-M-05-SSM + PY X-M-10-SSM: VdS 0786-CPD-21499»
- [ ] `pyra:py-x-m-10-ssm` (PY X-M-10-SSM · PYRA) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `085501987j_PY X-M-05_10_Installation_manual…`
      cita ✓ «PY X-M-05-SSM + PY X-M-10-SSM: VdS 0786-CPD-21499»
- [ ] `spectrex:380114-2` (380114-2 · Spectrex) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual-spectrex-sharpeye-20-20ml-user-manua…`
      cita ✓ «The P/N of the Flame Simulator Kit is 380114-2.»
- [ ] `spectrex:777670` (777670 · Spectrex) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `guide-40-40r-single-ir-flame-detector-spect…`
      cita ✓ «The duct mount (P/N 777670) is suitable for use with the SharpEye 40/40 Series Optical Flame Detector 40…»
- [ ] `spectrex:model-787640` (Model 787640 · Spectrex) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `manual-spectrex-sharpeye-20-20ml-user-manua…`
      cita ✓ «or preferably with the optional tilt mount, Model 787640 (Item 1, Figure 6)»
- [ ] `systemsensor:1551` (1551 · System Sensor) · frontera hoy 4 · id-provenance (NO es la fuente de la cita) `I56-512-07R DH500`
      cita ✓ «The DH500 Air Duct Detector Housings are used with System Sensor's intelligent model 1551 ionization det…»
- [ ] `systemsensor:2551` (2551 · System Sensor) · frontera hoy 4 · id-provenance (NO es la fuente de la cita) `I56-512-07R DH500`
      cita ✓ «The DH500 Air Duct Detector Housings are used with System Sensor's intelligent model 1551 ionization det…»
- [ ] `systemsensor:wfd20n` (WFD20N · System Sensor) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `WFDN_i56-4052-000r_ES (brand-tier=mecanico)…`
      cita ✓ «| WFD20N | 50 (2) | 60,3»
- [ ] `systemsensor:wfd25n` (WFD25N · System Sensor) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `WFDN_i56-4052-000r_ES (brand-tier=mecanico)…`
      cita ✓ «| WFD25N | 66 (2,5) | 76,1»
- [ ] `systemsensor:wfd30n` (WFD30N · System Sensor) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `WFDN_i56-4052-000r_ES (brand-tier=mecanico)…`
      cita ✓ «| WFD30N | 80 (3) | 88,9 | 2,9/3,2»
- [ ] `systemsensor:wfd40n` (WFD40N · System Sensor) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `WFDN_i56-4052-000r_ES (brand-tier=mecanico)…`
      cita ✓ «| WFD40N | 100 (4) | 114,3»
- [ ] `systemsensor:wfd60n` (WFD60N · System Sensor) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `WFDN_i56-4052-000r_ES (brand-tier=mecanico)…`
      cita ✓ «| WFD60N | 150 (6) | 168,3»
- [ ] `systemsensor:wfd80n` (WFD80N · System Sensor) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `WFDN_i56-4052-000r_ES (brand-tier=mecanico)…`
      cita ✓ «| WFD80N | 200 (8) | 219,1»
- [ ] `testifire:solo-725` (Solo 725 · Testifire (detectortesters)) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `Manual Testifire_Spanish`
      cita ✓ «Únicamente puede utilizarse el cargador Solo 725 para cargar las Solo 760 Batterías Baton»
- [ ] `unresolved:020-590` (020-590 · unknown) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MADT190_10`
      cita ✓ «**Kit 020-590 Kit para el equipo básico 6U**»
- [ ] `unresolved:020-591` (020-591 · unknown) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MADT190_10`
      cita ✓ «**Kit 020-591 6U para impresora/ chasis de ampliación**»
- [ ] `unresolved:020-592` (020-592 · unknown) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MADT190_10`
      cita ✓ «> **Kit 020-592** > **Panel 6U para ampliación de zonas 1-128/129-256**»
- [ ] `unresolved:020-593` (020-593 · unknown) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MADT190_10`
      cita ✓ «**Kit 020-593** > **Panel ciego (para impresora) 6U**»
- [ ] `unresolved:020-594` (020-594 · unknown) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MADT190_10`
      cita ✓ «**Kit 020-594** **Panel ciego 6U** **(sencillo)**»
- [ ] `unresolved:3466` (3466 · unknown) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `S3466R_Eng_ital`
      cita ✓ «## <ins>Model 3466</ins>»
- [ ] `unresolved:esense` (e²sense · Honeywell) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `12484_Ezsense_Ops Manual_EN`
      cita ✓ «# e²sense # Flammable Gas Detector»
- [ ] `unresolved:fl01xx-e-hs` (FL01XX E-HS · Honeywell) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `FAAST-LT-No-puedo-comunicar-con-el-equipo`
      cita ✓ «Este artículo es válido para los equipos FAAST LT, FAAST LT 200 (HS) autónomos o de lazo: **MI-FL20XXXX…»
- [ ] `unresolved:fvr-01` (FVR-01 · Honeywell) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `1998M0901_FS24X_ES-AR54-10_ES-AR_RevB_17Jul…`
      cita ✓ «El limitador del campo de visión modelo FVR-01 se puede modificar fácilmente in situ»
- [ ] `unresolved:itac-supra` (ITAC Supra · Honeywell) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `HLSI-MA-103_01_Itac`
      cita ✓ «Configuración ITAC Supra con RP1r-Supra / VSN-RP1r+ / ESS-RP1r-Supra»
- [ ] `unresolved:mad-464-i-w` (MAD-464-I-W · unknown) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `Manual_MAD-465-I (55346500 MI 620 m 2024 c)`
      cita ✓ «MAD-464-I-W | MAD-465-I-W [Product images showing white and red dome-shaped sounders: MAD-464-I-W and MA…»
- [ ] `unresolved:mad-465-i-w` (MAD-465-I-W · unknown) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `Manual_MAD-465-I (55346500 MI 620 m 2024 c)`
      cita ✓ «MAD-464-I-W | MAD-465-I-W [Product images showing white and red dome-shaped sounders: MAD-464-I-W and MA…»
- [ ] `unresolved:mad-564-i-w` (MAD-564-I-W · unknown) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `55356500-Manual-Sirena-Analogica-MAD565-I_E…`
      cita ✓ «## ref. MAD-564-I-W | ref. MAD-564-I»
- [ ] `unresolved:mad-565-i-w` (MAD-565-I-W · unknown) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `55356500-Manual-Sirena-Analogica-MAD565-I_E…`
      cita ✓ «## ref. MAD-565-I-W | ref. MAD-565-I»
- [ ] `unresolved:mi-dczrm` (MI-DCZRM · Honeywell) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `Conexionado-del-modulo-M710-CZR-MI-DCZRM`
      cita ✓ «Para conectar el modulo M710-CZR ó MI-DCZRM siga las indicaciones de la figura.»
- [ ] `unresolved:tg-ip-1-sec` (TG-IP-1-SEC · Honeywell) · frontera hoy 25 · id-provenance (NO es la fuente de la cita) `TG-IP-1-SEC-Que-direccion-IP-tiene-por-defe…`
      cita ✓ «# Serial Device Server TG-IP1-SEC»
- [ ] `unresolved:vision-supra` (VISION SUPRA · unresolved) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `27012012 ETIQUETA INSTRUCCIONES VISION SUPR…`
      cita ✓ «321XXX TARJETAS INSTRUCCIONES VISION SUPRA»
- [ ] `unresolved:vsn-rp1r-2plus` (VSN-RP1r-2PLUS · Honeywell) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `RP1r-Supra-VSNRP1r-2Plus-Sirena-sin-sonido-…`
      cita ✓ «Este artículo resuelve las incidencias de funcionamiento surgidas con las centrales RP1r-Supra y VSN-RP1…»
- [ ] `unresolved:vsn4-2plus` (VSN4-2Plus · Honeywell) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `HLSI-MN-025-I_NFS Supra Series v05`
      cita ✓ «This manual is valid for the following control panel models: * **NFS-Supra** * **NFS4-Supra**»
- [ ] `unresolved:vsn8-2plus` (VSN8-2Plus · Honeywell) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `HLSI-MN-025-I_NFS Supra Series v05`
      cita ✓ «This manual is valid for the following control panel models: * **NFS-Supra** * **NFS4-Supra** * **NFS8-S…»
- [ ] `xtralis:9-10900` (9-10900 · AirSense) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `9-10900-62576-es`
      cita ✓ «# 9-10900 **Tubería de 27mm, color rojo, 3m.**»
- [ ] `xtralis:9-10906` (9-10906 · AirSense) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `9-10906-62576-es`
      cita ✓ «# 9-10906 ## Codo 90° - Rojo - Tubería 27mm ### Descripción Codo de 90 grados para uso con sistemas de a…»
- [ ] `xtralis:9-10908` (9-10908 · AirSense) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `9-10908-62576-es`
      cita ✓ «# 9-10908 ## Unión directa para tuberia de 27mm - Roja ## Descripción Uniones directas para uso en siste…»
- [ ] `xtralis:9-10909` (9-10909 · AirSense) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `9-10909-62576-es`
      cita ✓ «# 9-10909 ## Unión T - Rojo - Tubería 27mm ## Descripción Unión en T para uso en sistemas de aspiración»
- [ ] `xtralis:9-10927` (9-10927 · AirSense) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `9-10927-62576-es`
      cita ✓ «# 9-10927 **Adaptador de fin de línea para tubo de 27mm..**»
- [ ] `xtralis:9-10954-100` (9-10954-100 · AirSense) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `9-10954-100-62576-es`
      cita ✓ «# 9-10954-100 **Grapa de sujeción para tubería. Montaje para techo o pared. 100 ud.**»
- [ ] `xtralis:lt-acc-ipa` (LT-ACC-IPA · Honeywell / Xtralis) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `Li-ion_Tamer_User_Manual`
      cita ✓ «| LT-ACC-IPA | MODBUS TCP/IP Adapter | Adapter for changing the native MODBUS RTU output from the Li-ion…»
- [ ] `xtralis:lt-acc-pcl` (LT-ACC-PCL · Honeywell / Xtralis) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `Li-ion_Tamer_User_Manual`
      cita ✓ «| LT-ACC-PCL | 10' Power Cable | Power cable for all Li-ion Tamer controllers»
- [ ] `xtralis:lt-acc-rly` (LT-ACC-RLY · Honeywell / Xtralis) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `Li-ion_Tamer_User_Manual`
      cita ✓ «| LT-ACC-RLY | Form C Relay | Standard dry-contact Form C relay»
- [ ] `xtralis:lt-acc-scl` (LT-ACC-SCL · Honeywell / Xtralis) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `Li-ion_Tamer_User_Manual`
      cita ✓ «| LT-ACC-SCL | 6' Female-Female Serial Cable | MODBUS DB9 RS232 cable to connect the serial output to th…»
- [ ] `xtralis:vrt-q00` (VRT-Q00 · VESDA by Xtralis) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `18500_A4_VESDA_VLI_Product_Guide_A4_IE_lores`
      cita ✓ «| VESDA VLI Remote Display with RTC7 | VRT-Q00 |»
- [ ] `xtralis:vrt-t00` (VRT-T00 · VESDA by Xtralis) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `18500_A4_VESDA_VLI_Product_Guide_A4_IE_lores`
      cita ✓ «| VESDA VLI Remote Display with RTC0 | VRT-T00 |»
- [ ] `zareba:2306b1000` (2306B1000 · Zellweger Analytics / Zareba) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `Manual Unipoint Esp`
      cita ✓ «Controlador Unipoint (versión entrada mA) 2306B1000»
- [ ] `zareba:2306b2000` (2306B2000 · Zellweger Analytics / Zareba) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `Manual Unipoint Esp`
      cita ✓ «Controlador Unipoint (versión entrada mV) 2306B2000»

### §0.D — «revisar» → **RETIRAR** (4)

Evidencia POSITIVA de que el término no es un modelo comercial. Van en lista aparte
porque retirar es destructivo: un «sí» al §0.C no arrastra al §0.D si no quieres.

- [ ] `notifier:1.5ke51ca` (1.5KE51CA · Notifier) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `MADT100_01`
      cita ✓ «Reductor de transitorios bipolar 1.5KE51CA ref.: 210-5033»
      razón: La evidencia muestra que 1.5KE51CA es la denominación genérica de un diodo supresor de transitorios incluido como componente en el kit del producto RP1001E; la referencia comercial real del ítem es 2…
- [ ] `notifier:ad-pe` (AD-PE · Notifier) · frontera hoy 3 · id-provenance (NO es la fuente de la cita) `MNDT650`
      cita ✓ «Versión Exd (AD-PE) (Antideflagrante)»
      razón: AD-PE no es un modelo: es la designación de la versión/ejecución antideflagrante (a prueba de explosión) del detector SMART 2; el otro chunk lo usa como clasificación de instalación («impianti ADPE»)…
- [ ] `notifier:c-160-14-to1a` (C-160-14-TO1A · Notifier) · frontera hoy 2 · id-provenance (NO es la fuente de la cita) `MNDT040P`
      cita ✓ «## Tarjeta Principal C-160-14-TO1A Rev.01»
      razón: El término aparece como identificador serigrafiado de la placa de circuito impreso (con «Rev.01») dentro del manual de la central CFP-600-E, no como modelo comercial ni en tablas de pedido o referenc…
- [ ] `unresolved:34115311` (34115311 · unknown) · frontera hoy 1 · id-provenance (NO es la fuente de la cita) `55310600 Manual TCD-106 kit_ES`
      cita ✓ «a white component labeled "34115311"»
      razón: El número solo aparece como marcado de un componente blanco en una placa de circuito impreso dentro de un diagrama del manual del TCD-106, no como modelo de producto ni referencia de pedido.

---

## SECCIÓN 1 — Una a una (145)

### §1.A — «confirmar», residuo (32)

Desglose: retirar=19, confirmar=8, dudoso=5

**propuesta del juez: retirar (19)**

- [ ] `firebeam:adaptador` (ADAPTADOR)
      medida: `ilike` 226 → token exacto **38** en 32 docs · sólo-parásito 2 · parásitos: adaptadores×4, Adaptadores×1
      banderas: palabra_generica, sin_digitos · fabricante: distinto · forma sospechosa: palabra_generica, sin_digitos
      juez: **retirar** · confianza alta · cita ✓ «Este campo muestra la se defina la MAC (Media Access Control) del adaptador de red de la centr…»
      por qué: «Adaptador» es una palabra genérica del español usada de forma descriptiva (adaptador de red, adaptador de escape, Módulo Adaptador NAM-232), no una referencia comercial por…
      evidencia (pág 25 · 4 Instalación): «…oporte de montaje * Plantilla de montaje para instalar el detector directamente en la superficie de montaje * Adaptador de escap…»
- [ ] `notifier:cdi` (CDI)
      medida: `ilike` 243 → token exacto **39** en 8 docs · sólo-parásito 1 · parásitos: CDI-LMS×1
      banderas: muy_corto, sin_digitos · fabricante: distinto · forma sospechosa: muy_corto, sin_digitos
      juez: **retirar** · confianza alta · cita ✓ «Comprobación del disparo de fallo y alarma, y de la alerta correcta a la CDI según el cap. 7.7.»
      por qué: En los fragmentos, «CDI» se usa como sigla genérica de Central de Detección de Incendios (siempre con artículo: «la CDI», «hasta la CDI»), no como referencia comercial de un…
      evidencia (pág 96 · 8.5.4.3 Códigos de evento dentr…): «…esconectado tubo sensor II (servicio normal) | | G26, prueba disparos tubo sensor II desde EasyConfig hasta CDI (véase G28) |…»
- [ ] `notifier:dia` (DIA)
      medida: `ilike` 9238 → token exacto **0** en 0 docs · sólo-parásito 40 · parásitos: mediante×16, diagram×9, Diagram×6, inmediatamente×5, media×4
      banderas: muy_corto, palabra_generica, sin_digitos · fabricante: sin_dato · solo 0 chunk(s) con el modelo como token completo (el resto son subcadenas de otros tokens); forma sospechosa: muy_corto, palabra_generica, sin_digitos
      juez: **retirar** · confianza baja · cita ✗ sin cita en el recibo
      por qué: Con 0 menciones como token completo en 40 chunks, 'DIA' solo aparece como subcadena de palabras comunes ('mediante', 'diagram', 'inmediatamente'), lo que indica un artefacto…
- [ ] `notifier:dib` (DIB)
      medida: `ilike` 784 → token exacto **0** en 0 docs · sólo-parásito 40 · parásitos: imprescindible×12, dibujo×8, audibles×7, dibujos×7, audible×5
      banderas: muy_corto, sin_digitos · fabricante: sin_dato · solo 0 chunk(s) con el modelo como token completo (el resto son subcadenas de otros tokens); forma sospechosa: muy_corto, sin_digitos
      juez: **retirar** · confianza media · cita ✗ sin cita en el recibo
      por qué: Ninguna de las 784 menciones es un token completo: todas son subcadenas de palabras genéricas del español como 'imprescindible', 'dibujo' o 'audible'. 'DIB' no designa un pro…
- [ ] `notifier:dust` (DUST)
      medida: `ilike` 524 → token exacto **9** en 8 docs · sólo-parásito 31 · parásitos: INDUSTRIAL×10, Industria×9, Industrial×7, industrial×6, industria×4
      banderas: muy_corto, palabra_generica, sin_digitos · fabricante: coincide · forma sospechosa: muy_corto, palabra_generica, sin_digitos
      juez: **retirar** · confianza alta · cita ✓ «Dust covers help to protect units during shipping and when first installed.»
      por qué: «DUST» es una palabra genérica del inglés usada en contextos descriptivos (dust covers, dust filter, dust contamination), no una referencia comercial de producto.
      evidencia (pág 1 · CAUTION): «### CAUTION **Dust covers help to protect units during shipping and when first installed. They are not intended to provide compl…»
- [ ] `notifier:fs-1` (FS-1)
      medida: `ilike` 22 → token exacto **0** en 0 docs · sólo-parásito 22 · parásitos: FS-1300×23, FS-1100×12, FS-1200×11
      banderas: muy_corto · fabricante: sin_dato · solo 0 chunk(s) con el modelo como token completo (el resto son subcadenas de otros tokens); forma sospechosa: muy_corto
      juez: **retirar** · confianza media · cita ✗ sin cita en el recibo
      por qué: FS-1 nunca aparece como token completo en el corpus: sus 22 menciones son subcadenas de referencias más largas (FS-1300, FS-1100, FS-1200), lo que indica que es un fragmento…
- [ ] `notifier:lib` (LIB)
      medida: `ilike` 1806 → token exacto **2** en 2 docs · sólo-parásito 38 · parásitos: libres×19, libro×17, libre×12, calibraci×8, LIB-400×7
      banderas: muy_corto, palabra_generica, sin_digitos · fabricante: coincide · forma sospechosa: muy_corto, palabra_generica, sin_digitos
      juez: **retirar** · confianza media · cita ✓ «Las siguientes características están solamente presentes en el LIB-200A y el LIB-400»
      por qué: «LIB» aparece casi siempre como fragmento de referencias más largas (LIB-200A, LIB-400) o dentro de palabras comunes (libres, libro, calibración); como token aislado designa…
      evidencia (pág 59 · Apéndice 1): «…verías de lazo **Hardware de la tarjeta de lazo** **Avería de sistema - Avería de LIB-CPU Avería del driver LIB Avería central 5…»
- [ ] `notifier:lpm` (LPM)
      medida: `ilike` 9 → token exacto **8** en 5 docs · sólo-parásito 1 · parásitos: PRECAUSMSPANISHLPM65×1
      banderas: muy_corto, sin_digitos, unidad_o_norma · fabricante: distinto · forma sospechosa: muy_corto, sin_digitos, unidad_o_norma
      juez: **retirar** · confianza alta · cita ✓ «El flujo a través del detector previsto por ASPIRE2 debe encontrarse en un rango de 12 a 54 lpm»
      por qué: «lpm» es la unidad de caudal (litros por minuto) usada en las especificaciones de flujo del detector, no una referencia comercial de producto.
      evidencia (pág 6 · Advertencias y requisitos legal…): «…espectivamente. * El flujo a través del detector previsto por ASPIRE2 debe encontrarse en un rango de 12 a 54 lpm. Estos límites…»
- [ ] `notifier:lpx` (LPX)
      medida: `ilike` 38 → token exacto **18** en 8 docs · sólo-parásito 20 · parásitos: LPX-751×23, LPX-751E×2, LPX-7×1, SDX-551LPX-751FDX-551×1, LPX751×1
      banderas: muy_corto, sin_digitos · fabricante: coincide · forma sospechosa: muy_corto, sin_digitos
      juez: **retirar** · confianza media · cita ✓ «LPX (VIEW, solo ID60 - véase el **Apéndice 2**), PUL (pulsador manual), MON (módulo monitor)»
      por qué: LPX aparece como código de tipo de detector (láser/VIEW) en listados y filtros del panel, no como referencia comercial; el producto real es el LPX-751, del cual LPX es un fra…
      evidencia (pág 3 · DETECTORS): «## DETECTORS | ☒ Heat<br/>☒ Ion<br/>☒ Photo<br/>☒ Omni IPX<br/>☒ Laser LPX | Heat = Blue<br/>Ion = Red<br/>Photo/Optical = Dark g…»
- [ ] `notifier:rhistorico.exe` (RHistorico.exe)
      medida: `ilike` 3 → token exacto **3** en 2 docs · sólo-parásito 0
      banderas: parece_fichero, sin_digitos · fabricante: coincide · forma sospechosa: parece_fichero, sin_digitos
      juez: **retirar** · confianza alta · cita ✓ «debe acceder a la utilidad que acompaña al software gráfico TG, **"RHistorico.exe"**»
      por qué: Es el nombre de un fichero ejecutable (utilidad de reparación de históricos que acompaña al software gráfico), no una referencia comercial de producto del fabricante.
      evidencia (pág 1 · Utilidad de Reparación de Histó…): «…n se encuentra en el directorio de instalación, dentro del subdirectorio *Util*, por ejemplo C:\NOTIFIER\Util\RHistorico.exe. Un…»
- [ ] `notifier:tmp` (TMP)
      medida: `ilike` 41 → token exacto **10** en 9 docs · sólo-parásito 30 · parásitos: TMPO×29, Tmpo×12, TMP2×7, TRC_TMPF1×6, MB_TRC_TMPF1×2
      banderas: muy_corto, palabra_generica, sin_digitos · fabricante: coincide · forma sospechosa: muy_corto, palabra_generica, sin_digitos
      juez: **retirar** · confianza media · cita ✓ «WATCHDOG.TMP, en él se almacena información para el control de funcionamiento del sistema»
      por qué: La mayoría de menciones corresponden a extensiones de fichero (.TMP) y la única aparición como token es en una tabla de abreviaturas de tipos de dispositivo ('TMP | Detector…
      evidencia (pág 19 · 3.2. Estructura de datos): «…fichero HISSYS.DAT almacenará los eventos producidos en la instalación del histórico de sistema. - WATCHDOG.TMP, en él se almace…»
- [ ] `notifier:view` (VIEW)
      medida: `ilike` 1648 → token exacto **35** en 31 docs · sólo-parásito 5 · parásitos: views×10, SensorVIEW1×3, SensorVIEW2×3, Overview×2, Viewing×1
      banderas: muy_corto, palabra_generica, sin_digitos · fabricante: coincide · forma sospechosa: muy_corto, palabra_generica, sin_digitos
      juez: **retirar** · confianza alta · cita ✓ «Utilice la opción *View > Zones* desde la ventana principal de *Sensor Manager*»
      por qué: Todas las menciones corresponden a la palabra genérica inglesa 'view' (vistas de diagramas, opciones de menú), no a una referencia comercial de producto.
      evidencia (pág 8 · Montaje de la UDS-1N): «…ior como guía cuando taladre los agujeros!** [Technical diagram showing two views of the mounting box: Left view (side profile):…»
- [ ] `patrol:ssm` (-SSM)
      medida: `ilike` 26 → token exacto **20** en 4 docs · sólo-parásito 6 · parásitos: 20-SSM×8, X-M-05-SSM×8, X-M-10-SSM×8, 10-SSM×4, PA10-SSM×4
      banderas: muy_corto, sin_digitos · fabricante: distinto · forma sospechosa: muy_corto, sin_digitos
      juez: **retirar** · confianza alta · cita ✓ «for all DC versions except for option -SSM»
      por qué: -SSM es un sufijo de opción que se añade a referencias completas (20-SSM, X-M-05-SSM), no una referencia comercial autónoma. La evidencia lo describe explícitamente como «Опц…
      evidencia (pág 17 · Технические данные): «…| | | | Опции | -SSM (см. стр. 21)…»
- [ ] `sensitron:pl4` (PL4)
      medida: `ilike` 96 → token exacto **35** en 11 docs · sólo-parásito 5 · parásitos: PL4E×10, STPL4/ESP×5, PL4-E×1, STPL4×1
      banderas: muy_corto · fabricante: distinto · forma sospechosa: muy_corto
      juez: **retirar** · confianza media · cita ✓ «Manual de usuario e instalación / Installation and user manual PL4+»
      por qué: Toda la evidencia del corpus se refiere a la central PL4+, no a 'PL4' a secas; el candidato parece un fragmento de la referencia más larga PL4+ (y de parásitos como PL4E o ST…
      evidencia (pág 15 · 2.5 Prueba automática (Self-Tes…): «## 2.5 Prueba automática (Self-Test) El software de la central PL4+ está programado para realizar, periódicamente una prueba auto…»
- [ ] `unresolved:fs24x-2` (FS24X-2)
      medida: `ilike` 3 → token exacto **1** en 1 doc · sólo-parásito 2 · parásitos: FS24X-211×1, FS24X-211-221×1
      banderas: ninguna · fabricante: distinto · solo 1 chunk(s) con el modelo como token completo (el resto son subcadenas de otros tokens)
      juez: **retirar** · confianza media · cita ✓ «**All FS24X-2 Detectors**»
      por qué: La única mención completa usa 'All FS24X-2 Detectors' como prefijo de familia que agrupa modelos reales como FS24X-211; parece un fragmento de referencias más largas, no una…
      evidencia (pág 6 · 1.2.5 Clasificaciones de áreas…): «…ors** T4: Ta = -60°C to +110°C<sup>3</sup> T5: Ta = -60°C to +75°C<sup>3</sup> T6: Ta = -60°C to +60°C **All FS24X-2 Detectors**…»
- [ ] `unresolved:indicator` (INDICATOR)
      medida: `ilike` 1421 → token exacto **25** en 23 docs · sólo-parásito 15 · parásitos: indicators×31, Indicators×7, INDICATORS×1, buttons/indicators×1, dot/indicator×1
      banderas: sin_digitos · fabricante: distinto · forma sospechosa: sin_digitos
      juez: **retirar** · confianza alta · cita ✓ «The remote indicator of the sensor activates the fire alarm in an aspirating system»
      por qué: «Indicator» es una palabra genérica del inglés usada para describir luces y elementos de señalización en paneles, no una referencia comercial de producto. Todas las menciones…
      evidencia (pág 10 · 3.3.4- Selección de Idioma): «…ubicaciones están señalizadas con las letras A, B, C y D. [Control panel diagram showing: Left section with indicator lights and…»
- [ ] `unresolved:itac` (ITAC)
      medida: `ilike` 806 → token exacto **0** en 0 docs · sólo-parásito 40 · parásitos: limitaciones×19, Limitaciones×6, LIMITACIONES×5, Inhabilitaci×4, habitaci×4
      banderas: muy_corto, sin_digitos · fabricante: sin_dato · solo 0 chunk(s) con el modelo como token completo (el resto son subcadenas de otros tokens); forma sospechosa: muy_corto, sin_digitos
      juez: **retirar** · confianza media · cita ✗ «limitaciones×19, Limitaciones×6, LIMITACIONES×5»
      por qué: ‘ITAC’ nunca aparece como token completo: todas las coincidencias son subcadenas de palabras genéricas como ‘limitaciones’ o ‘habitación’, un artefacto de extracción, no una…
- [ ] `unresolved:mad-461` (MAD-461)
      medida: `ilike` 5 → token exacto **0** en 0 docs · sólo-parásito 5 · parásitos: MAD-461-I×5
      banderas: ninguna · fabricante: sin_dato · solo 0 chunk(s) con el modelo como token completo (el resto son subcadenas de otros tokens)
      juez: **retirar** · confianza media · cita ✗ «MAD-461-I×5»
      por qué: MAD-461 nunca aparece como token completo: sus 5 menciones son subcadenas de la referencia más larga MAD-461-I, lo que indica que es un fragmento de otra referencia y no un p…
- [ ] `unresolved:vsn-2p` (VSN-2P)
      medida: `ilike` 9 → token exacto **0** en 0 docs · sólo-parásito 9 · parásitos: VSN-2Plus×6, VSN-2P/NFSx-Supra×6, VSN-2PLUS×1, VSN-2Plus/NFS×1
      banderas: ninguna · fabricante: sin_dato · solo 0 chunk(s) con el modelo como token completo (el resto son subcadenas de otros tokens)
      juez: **retirar** · confianza media · cita ✗ «sin ninguna mención como token completo: todas las coincidencias son subcadenas de tokens más…»
      por qué: VSN-2P nunca aparece como token completo (0 de 9): todas las menciones son fragmentos de referencias más largas como VSN-2Plus o VSN-2P/NFSx-Supra. Es un truncamiento, no un…

**propuesta del juez: confirmar (8)**

- [ ] `hosiden:ls-28` (LS 28)
      medida: `ilike` 3 → token exacto **3** en 1 doc · sólo-parásito 0
      banderas: multipalabra, muy_corto · fabricante: coincide · forma sospechosa: multipalabra, muy_corto
      juez: **confirmar** · confianza media · cita ✓ «SOLENOID DRIVER<br/>MTL 2027 TO LS 28»
      por qué: LS 28 aparece como unidad de equipo en diagramas de circuito ('I.S. UNITS ONE PER CHANNEL') y conectado a un driver MTL 2027, lo que indica que designa un aparato real y no u…
      evidencia (pág 3 · HAZARDOUS AREA | SAFE AREA): «…Sheet 4 **CONTROL SWITCHES OR LOGIC SIGNALS** **SAFE AREA APPARATUS** **I.S.28 UNITS ONE PER CHANNEL** **LS 28** **LS 28** **LS…»
- [ ] `notifier:nrt` (NRT)
      medida: `ilike` 165 → token exacto **40** en 8 docs · sólo-parásito 0 · parásitos: NRT-586T×5, NRTs×2, NRTDB9×1, NRT/INA×1, NRTs/INAs×1
      banderas: muy_corto, sin_digitos · fabricante: coincide · forma sospechosa: muy_corto, sin_digitos
      juez: **confirmar** · confianza media · cita ✓ «Para programar un panel anunciador desde la NRT, pulse el botón de anunciador.»
      por qué: La evidencia muestra que NRT designa una herramienta/software real de Notifier con su propio programa e interfaz de sistema, usada para programar paneles. Aunque el token es…
      evidencia (pág 48 · 6. La Ventana del Memo): «…la Ventana Desde el Menú de la Ventana, el usuario puede acezar cualquier otra ventana en el programa de la NRT.»
- [ ] `notifier:sensenet` (SENSENET)
      medida: `ilike` 72 → token exacto **40** en 9 docs · sólo-parásito 0
      banderas: sin_digitos · fabricante: coincide · forma sospechosa: sin_digitos
      juez: **confirmar** · confianza media · cita ✓ «Una señal recibida desde un ordenador externo como el software remoto, APIC o SenseNET»
      por qué: SenseNET es un nombre comercial real del fabricante (red/software de monitorización de detectores por aspiración), citado como producto junto a APIC. No es un artefacto, aunq…
      evidencia (pág 31 · 2. El interior del detector): «…etector MINILÁSER100, la dirección inicial y final es la misma. > *Nota: La dirección del detector en la red SenseNET y la direc…»
- [ ] `notifier:smart-3-cc` (SMART 3 CC)
      medida: `ilike` 6 → token exacto **1** en 1 doc · sólo-parásito 5 · parásitos: SMART 3 CC-CD×5, SMART 3 CC-DC×1
      banderas: multipalabra, palabra_generica · fabricante: coincide · solo 1 chunk(s) con el modelo como token completo (el resto son subcadenas de otros tokens); forma sospechosa: multipalabra, palabra_generica
      juez: **confirmar** · confianza media · cita ✓ «para que el SMART 3 CC y el SMART3 CD [con pantalla *(display)*] se puedan comunicar en el bus…»
      por qué: La evidencia menciona el SMART 3 CC como equipo diferenciado del SMART3 CD que se comunica por bus RS485, lo que indica un producto real. La confianza es media porque la mayo…
      evidencia (pág 12 · 3.5.1 Configuración de la direc…): «…A continuación, se explica cómo montar y configurar las direcciones de la tarjeta serie ST.S/IDI para que el SMART 3 CC y el SMA…»
- [ ] `notifier:smb-t` (SMB-T)
      medida: `ilike` 4 → token exacto **4** en 4 docs · sólo-parásito 0
      banderas: muy_corto, sin_digitos · fabricante: distinto · forma sospechosa: muy_corto, sin_digitos
      juez: **confirmar** · confianza media · cita ✓ «Corte los pasos de cableado necesarios en la caja SMB-T»
      por qué: SMB-T se menciona de forma consistente en varios manuales como la caja/envolvente de montaje del equipo UCIP-GPRS, lo que indica una referencia comercial real de accesorio (c…
      evidencia (pág 29 · Anexo III – Instrucciones de Mo…): «…nstrucciones de Montaje ## 1 Pasos de cableado estándar Realice los pasos de cableado necesarios en la caja SMB-T: 1- Puerto RS-…»
- [ ] `notifier:zmx` (ZMX)
      medida: `ilike` 86 → token exacto **25** en 15 docs · sólo-parásito 15 · parásitos: ZMX-1E×20, ZMX-1×7, 1ZMxi×2, ZMX/9×1
      banderas: muy_corto, sin_digitos · fabricante: distinto · forma sospechosa: muy_corto, sin_digitos
      juez: **confirmar** · confianza media · cita ✓ «utilice un módulo estándar CMX en lugar de un CDI o ZMX»
      por qué: ZMX se menciona como tipo de módulo del fabricante junto a CMX y CDI, y aparece como opción seleccionable en tablas de configuración, lo que indica que es una referencia real…
      evidencia (pág 38 · *10.3.4 Entradas de equipos*): «…| | Equipo Alarma 1 | Sensor ▼ | 3 ⇄ | OPT | | Equipo Alarma 2 | Módulo ▼ | 8 ⇄ | ZMX | | Equipo Alarma 3 | No utilizado ▼ | 1 ⇄…»
- [ ] `unresolved:mad-432` (MAD-432)
      medida: `ilike` 5 → token exacto **5** en 5 docs · sólo-parásito 0 · parásitos: MAD-432-I×5
      banderas: medida_en_contexto · fabricante: distinto · forma sospechosa: medida_en_contexto
      juez: **confirmar** · confianza media · cita ✓ «| MAD-432 | MOD | 0,3 mA | 1,5 mA | No | Sí | 2 | Módulo de cont»
      por qué: Aparece como token completo en filas de tabla de producto con especificaciones eléctricas propias (consumos, aislador) y descripción de módulo de control, consistente en tres…
      evidencia (pág 55 · 10.2. Dispositivos compatibles…): «…nalógico de 1 salida de 24v supervisados con aislador | | MAD-432 | MOD | 0,3 mA | 1,5 mA | No | Sí | 2 | Módulo de cont…»
- [ ] `unresolved:sm4` (SM4)
      medida: `ilike` 20 → token exacto **9** en 5 docs · sólo-parásito 11 · parásitos: VSM4×12
      banderas: muy_corto · fabricante: distinto · forma sospechosa: muy_corto
      juez: **confirmar** · confianza media · cita ✓ «Utilice un ángulo descendente mínimo de treinta grados (30°) con el montaje giratorio SM4 (con…»
      por qué: SM4 designa un accesorio real del fabricante: un montaje giratorio para detectores (típico de detectores de llama como el FS20X). Aunque también aparece como código de tabla…
      evidencia (pág 6 · 1.2.1 Abreviaturas de tipo de e…): «…| | SDH | Salida ( sirena) supervisada. Consumo alto | | SM4\* | Sensor multicriterio SMART\* | | TMP | Detector de temper…»

**propuesta del juez: dudoso (5)**

- [ ] `notifier:cp6` (CP6)
      medida: `ilike` 22 → token exacto **20** en 8 docs · sólo-parásito 2 · parásitos: FACP6×5
      banderas: muy_corto · fabricante: coincide · forma sospechosa: muy_corto
      juez: **dudoso** · confianza baja · cita ✓ «**Fig. CP6**»
      por qué: La evidencia es contradictoria: [3] muestra 'Fig. CP6' como etiqueta de figura (artefacto) y [1] parece un rótulo de esquema, pero [2] lo lista en una tabla de versiones junt…
      evidencia (pág 4 · Instalar/Reemplazar la tarjeta…): «…azo A Conector PL1 Montaje de la tarjeta de lazo TX (Ref. 124-065-XXX) Conectores J1 J2 J3 Montaje de la Cp6 Caja posterior (det…»
- [ ] `notifier:esser-edp` (ESSER EDP)
      medida: `ilike` 13 → token exacto **9** en 3 docs · sólo-parásito 4 · parásitos: TG-ESSER EDP×5, HTG-ESSER EDP×1
      banderas: multipalabra, sin_digitos · fabricante: coincide · forma sospechosa: multipalabra, sin_digitos
      juez: **dudoso** · confianza media · cita ✓ «Nueva ESSER EDP SE\NComunicacion»
      por qué: Las menciones aparecen como nombres de nodos o etiquetas de configuración en un software de gestión ('ESSER EDP Master', 'Nueva ESSER EDP SEI'), no como una referencia comerc…
      evidencia (pág 4 · Mapeo): «…---------------- | -------------------------------- | ---- | ---- | -------- | ------ | ----- | | 1 | ESSER EDP Master | Modo Pa…»
- [ ] `notifier:omni` (OMNI)
      medida: `ilike` 71 → token exacto **21** en 9 docs · sólo-parásito 19 · parásitos: OMNISENSOR×14, Omnisensor×5, omnipolar×2, OmniSensor×2, omnidireccional×1
      banderas: muy_corto, palabra_generica, sin_digitos · fabricante: coincide · forma sospechosa: muy_corto, palabra_generica, sin_digitos
      juez: **dudoso** · confianza media · cita ✓ «sensores con HW de tipo "NFXI-SMT2" y "OMNI"»
      por qué: OMNI aparece como tipo de hardware de sensor, pero en el resto de la evidencia la designación completa es «Omni IPX» y la mayoría de menciones son parásitos (OMNISENSOR), por…
      evidencia (pág 3 · DETECTORS): «## DETECTORS | ☒ Heat<br/>☒ Ion<br/>☒ Photo<br/>☒ Omni IPX<br/>☒ Laser LPX | Heat = Blue<br/>Ion = Red<br/>Photo/Optical = Dark g…»
- [ ] `notifier:pl4` (PL4)
      medida: `ilike` 96 → token exacto **35** en 11 docs · sólo-parásito 5 · parásitos: PL4E×10, STPL4/ESP×5, PL4-E×1, STPL4×1
      banderas: muy_corto · fabricante: coincide · forma sospechosa: muy_corto
      juez: **dudoso** · confianza media · cita ✓ «El software de la central PL4+ está programado para realizar, periódicamente una prueba automá…»
      por qué: Toda la evidencia mostrada se refiere a la central PL4+ (con sufijo '+'), no a 'PL4' a secas; además existen tokens parásitos (PL4E, STPL4) que sugieren que PL4 podría ser un…
      evidencia (pág 15 · 2.5 Prueba automática (Self-Tes…): «## 2.5 Prueba automática (Self-Test) El software de la central PL4+ está programado para realizar, periódicamente una prueba auto…»
- [ ] `unresolved:nfsx-supra` (NFSx-Supra)
      medida: `ilike` 4 → token exacto **0** en 0 docs · sólo-parásito 4 · parásitos: VSN-2P/NFSx-Supra×6, 2Plus/RP1r-Supra/NFSx-Supra×1
      banderas: sin_digitos · fabricante: sin_dato · solo 0 chunk(s) con el modelo como token completo (el resto son subcadenas de otros tokens); forma sospechosa: sin_digitos
      juez: **dudoso** · confianza baja · cita ✗ sin cita en el recibo
      por qué: El modelo solo aparece como subcadena dentro de tokens compuestos como VSN-2P/NFSx-Supra, posiblemente listas de modelos separadas por barras, pero sin ninguna mención como t…

### §1.B — «revisar», residuo (113)

Agrupados por el motivo que los dejó fuera del bloque.

**sin atestación en contenido: NO es prueba de que el producto no exista (posible hueco de manual). No decidible desde el corpus. — 45**

- [ ] `firebeam:thefirebeam-xtra` (thefirebeam Xtra · Firebeam)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 20 · id-provenance (NO es la fuente de la cita) `Manual_Firebeam_XTRA_ES`
- [ ] `notifier:afp1020` (AFP1020 · Honeywell)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Tg-Honeywell_Tecnico`
- [ ] `notifier:interface-rs485-serie-800` (Interface RS485 serie 800 · Notifier)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MNDT021`
- [ ] `notifier:laserstar-repetidor` (LaserStar Repetidor · Notifier)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MIDT730`
- [ ] `notifier:lisa-2-eex-d` (LISA 2 EEx d · Notifier)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MNDT635`
- [ ] `notifier:lisa-2-eex-na` (LISA 2 EEx nA · Notifier)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MNDT635`
- [ ] `notifier:nfs8-2plus` (NFS8-2PLUS · Notifier)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `NFS4_NFS8-2PLUS_MANU_ITA`
- [ ] `notifier:nport-5110` (NPort 5110 · Honeywell / Notifier)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `HLSI_MNDT1410_B` · **colisión**: `Moxa Nport 5110`
- [ ] `sensitron:smart-2-twin` (SMART 2 TWIN · Sensitron)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Smart 2_MT251_Ita-Eng`
- [ ] `testifire:testifire-1001` (Testifire 1001 · Testifire (detectortesters))
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual Testifire_Spanish`
- [ ] `testifire:testifire-2001` (Testifire 2001 · Testifire (detectortesters))
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual Testifire_Spanish`
- [ ] `testifire:testifire-6001` (Testifire 6001 · Testifire (detectortesters))
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual Testifire_Spanish`
- [ ] `testifire:testifire-6201` (Testifire 6201 · Testifire (detectortesters))
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual Testifire_Spanish`
- [ ] `testifire:testifire-9001` (Testifire 9001 · Testifire (detectortesters))
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual Testifire_Spanish`
- [ ] `testifire:testifire-9201` (Testifire 9201 · Testifire (detectortesters))
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual Testifire_Spanish`
- [ ] `unresolved:cmd-500` (CMD-500 · unresolved)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 38 · id-provenance (NO es la fuente de la cita) `55350005 Manual Central Monoxido CMD-50…`
- [ ] `unresolved:d-1100-4-sounder` (D 1100-4 Sounder · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `D 1100-4 Sounder`
- [ ] `unresolved:dmdx-500` (DMDX-500 · M.ZONA)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 4 · id-provenance (NO es la fuente de la cita) `55350008 Manual Detectores Monoxido DMD…`
- [ ] `unresolved:ds-5--gl` (DS 5 -GL · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `085501821n_DS10_Installation_manual_D-G…`
- [ ] `unresolved:ds-5--tas` (DS 5 -TAS · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `085501821n_DS10_Installation_manual_D-G…`
- [ ] `unresolved:ds-5--tav` (DS 5 -TAV · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `085501821n_DS10_Installation_manual_D-G…`
- [ ] `unresolved:f3000m` (F3000M · unresolved)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `F3000M_Spanish User Guide_0044-047-02-ES`
- [ ] `unresolved:f5k` (F5K · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 12 · id-provenance (NO es la fuente de la cita) `F5K-Additional-Information-Spanish` · **colisión**: `F5K-2H`
- [ ] `unresolved:f5k-2h` (F5K-2H · unresolved)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `F5K-2H-UserGuide-SPANISH_Manual F5000`
- [ ] `unresolved:fad-902` (FAD-902 · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `55393002 Manual Fuentes de Alimentacion…`
- [ ] `unresolved:fad-905` (FAD-905 · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 16 · id-provenance (NO es la fuente de la cita) `55393002 Manual Fuentes de Alimentacion…`
- [ ] `unresolved:mad-432-mdulo-1-sirena` (MAD-432 Módulo 1 Sirena · unresolved)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `55343101 Manual Modulo 1-2 Sirenas Conv…`
- [ ] `unresolved:mad-432-mdulo-2-sirenas` (MAD-432 Módulo 2 Sirenas · unresolved)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `55343101 Manual Modulo 1-2 Sirenas Conv…`
- [ ] `unresolved:mad-471` (MAD-471 · unresolved)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 3 · id-provenance (NO es la fuente de la cita) `55347101 Manual Sirena Analogica MAD-47…`
- [ ] `unresolved:mad-491` (MAD-491 · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 3 · id-provenance (NO es la fuente de la cita) `55349102 Manual Modulo Aislador MAD-491…`
- [ ] `unresolved:pad-10a` (PAD-10A · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 14 · id-provenance (NO es la fuente de la cita) `55320102 Manual Buzzer Analogico PAD-10…`
- [ ] `unresolved:scd-100` (SCD-100 · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 3 · id-provenance (NO es la fuente de la cita) `55310401 Manual Sirenas Convencionales…`
- [ ] `unresolved:scd-110` (SCD-110 · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 2 · id-provenance (NO es la fuente de la cita) `55311003 Manual Sirenas Convencionales…` · **colisión**: `SCD-110 con flash`
- [ ] `unresolved:scd-110-con-flash` (SCD-110 con flash · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `55311003 Manual Sirenas Convencionales…`
- [ ] `unresolved:scd-120` (SCD-120 · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 9 · id-provenance (NO es la fuente de la cita) `55312000 SCD-120_Manual_ES`
- [ ] `unresolved:tbud-150` (TBUD-150 · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 2 · id-provenance (NO es la fuente de la cita) `55315012 Manual Tarjeta de bucle TBUD-1…`
- [ ] `unresolved:tcd-106` (TCD-106 · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 10 · id-provenance (NO es la fuente de la cita) `55310600 Manual TCD-106 kit_ES`
- [ ] `unresolved:tmd-100` (TMD-100 · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 2 · id-provenance (NO es la fuente de la cita) `55310008 Manual Tarjeta Modbus TMD-100…`
- [ ] `unresolved:trd-100` (TRD-100 · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 4 · id-provenance (NO es la fuente de la cita) `55310007 Manual Tarjeta Expansion TRD-1…`
- [ ] `unresolved:trmd-50x` (TRMD-50X · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 2 · id-provenance (NO es la fuente de la cita) `55350007 Manual Tarjeta Regulacion Moto…`
- [ ] `unresolved:tsd-100` (TSD-100 · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `55310007 Manual Tarjeta Expansion TRD-1…`
- [ ] `unresolved:z-200-r` (Z-200-R · unknown)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `55320011 Manual zocalo con relé Z-200-R`
- [ ] `xtralis:mgate-mb3270` (MGate MB3270 · Honeywell / Xtralis)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Li-ion_Tamer_User_Manual`
- [ ] `zareba:unipoint-ma` (Unipoint mA · Zellweger Analytics / Zareba)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual Unipoint Esp`
- [ ] `zareba:unipoint-mv` (Unipoint mV · Zellweger Analytics / Zareba)
      **(el recibo no trae este campo)** · confianza (el recibo no trae este campo) · cita ✗ sin cita en el recibo
      frontera hoy 0 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual Unipoint Esp`

**confianza media — 42**

- [ ] `detnov:spr_250` (SPR_250 · Detnov)
      **CONFIRMAR** · confianza media · cita ✓ «Para la correcta instalación de una torre de centrales o tótem necesitará los soportes de pare…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual instalacion CAD-250 (MI_372_es_2…`
- [ ] `fidegas:00052` (00052 · Fidegas)
      **CONFIRMAR** · confianza media · cita ✓ «| Ref. S/3-T2 | Ref. S/2-T2 | Gas | Rango | Ref. Repuesto |»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual-de-Usuario-S3-T2-y-S2-T2`
- [ ] `fidegas:03382` (03382 · Fidegas)
      **CONFIRMAR** · confianza media · cita ✓ «| Ref. S/3-T2 | Ref. S/2-T2 | Gas | Rango | Ref. Repuesto | | ----------- | ----------- | ---…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual-de-Usuario-S3-T2-y-S2-T2`
- [ ] `fidegas:03383` (03383 · Fidegas)
      **CONFIRMAR** · confianza media · cita ✓ «| 00052 | 03383 | O2 | (21-0)% v/v | 00170 |»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual-de-Usuario-S3-T2-y-S2-T2`
- [ ] `fidegas:cs4-analgica` (CS4 Analógica · FIDEGAS)
      **CONFIRMAR** · confianza media · cita ✓ «**CENTRAL DE ALARMAS** CE **CS4 Analógica Firmware 1.2**»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `Manual-de-Usuario-CS4`
- [ ] `kidde:1x-f8-sc` (1X-F8-SC · Kidde)
      **RETIRAR** · confianza media · cita ✓ «The 1X-F8-SC is a conventional fire alarm control panel with Scandinavian key support.»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `nc-pf8-sc-161721-es`
- [ ] `lda:etx-1` (ETX-1 · LDA)
      **CONFIRMAR** · confianza media · cita ✓ «El equipo dispone de una bahía de conexión donde integra un módulo ETX-1, que permite la conex…»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `NEO8060S02-MU - MANUAL DE USUARIO SERIE…`
- [ ] `menvier:1471` (1471 · Menvier CSA)
      **CONFIRMAR** · confianza media · cita ✓ «La rottura del vetro tramite pressione o martelletto (art.1471) provoca immediatamente lo scat…»
      frontera hoy 5 · substring 5 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `RIF_08791_01 - AC1469_It-eng`
- [ ] `morley:sp-200` (SP-200 · Morley IAS)
      **RETIRAR** · confianza media · cita ✓ «## 9.10 Placa de módulo de extinción "SP-200"»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MIE-MI-110 (brand-tier=mecanico) | x-br…`
- [ ] `notifier:124-297` (124-297 · Notifier)
      **CONFIRMAR** · confianza media · cita ✓ «DTP/Booster module with two cables (1 off) PN: 124-297»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `997-267-000-6_Eng`
- [ ] `notifier:210-5033` (210-5033 · Notifier)
      **CONFIRMAR** · confianza media · cita ✓ «Reductor de transitorios bipolar 1.5KE51CA ref.: 210-5033»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MADT100_01`
- [ ] `notifier:29087` (29087 · Notifier)
      **RETIRAR** · confianza media · cita ✓ «Una ferrita, ref.: 29087, para instalar el cableado de la línea CA»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MADT100_01`
- [ ] `notifier:29146` (29146 · Notifier)
      **CONFIRMAR** · confianza media · cita ✓ «Muestra la instalación correcta de la ferrita con ref.: 29146 en cada uno de los circuitos de…»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MADT100_01`
- [ ] `notifier:72051ei` (72051EI · Notifier)
      **CONFIRMAR** · confianza media · cita ✓ «Ejemplo de programación de un sensor con tipo HW "F-SEN-SSE". 72051EI (detector de alta sensib…»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `AM-8100 manual de usuario y programacio…`
- [ ] `notifier:amg-zc` (AMG-ZC · Notifier)
      **CONFIRMAR** · confianza media · cita ✓ «El chip AMG-ZC permite al AMG-1 indicar el punto del anunciador que está en alarma.»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MIDT340`
- [ ] `notifier:bani-g-24` (BANI-G-24 · NOTIFIER)
      **CONFIRMAR** · confianza media · cita ✓ «3- Aislador galvánico para sirena BANI-G-24 (Referencia nuestra AIS-GALS1, referencia de Peppe…»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `TIDT089`
- [ ] `notifier:fs-2` (FS-2 · Notifier)
      **RETIRAR** · confianza media · cita ✓ «el fusible de alimentación (FS1) en el lado izquierdo y el fusible de batería (FS2) en el lado…»
      frontera hoy 17 · substring 0 · chunks con ese product_model 132 · id-provenance (NO es la fuente de la cita) `FS2-1`
- [ ] `notifier:fs-4` (FS-4 · Notifier)
      **RETIRAR** · confianza media · cita ✓ «todas las variaciones de nomenclatura de FSX (como FS2, FS2X, FS3, FS3X, FS4, FS4X, FS5, FS5X»
      frontera hoy 2 · substring 0 · chunks con ese product_model 30 · id-provenance (NO es la fuente de la cita) `FS2-1`
- [ ] `notifier:g10016r` (G10016R · Notifier)
      **CONFIRMAR** · confianza media · cita ✓ «Tarjeta de 16 relés: 100 µA (Sin relés activados). Ref.: G10016R»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MNDT040`
- [ ] `notifier:gc-1` (GC-1 · Notifier)
      **CONFIRMAR** · confianza media · cita ✓ «Este detector está previsto para trabajar conjuntamente con modulos de zona GC-1»
      frontera hoy 2 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `manco-N`
- [ ] `notifier:ica-6` (ICA-6 · Notifier)
      **CONFIRMAR** · confianza media · cita ✓ «* Chasis ampliación ICA 6»
      frontera hoy 3 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MIDT250_A`
- [ ] `notifier:ref.-30752` (Ref.: 30752 · NOTIFIER)
      **CONFIRMAR** · confianza media · cita ✓ «Soporte de sujeción con una única entrada. Ref.: 30752»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MIDT732`
- [ ] `notifier:ref.-30753` (Ref.: 30753 · NOTIFIER)
      **CONFIRMAR** · confianza media · cita ✓ «Soporte de sujeción con tubería de salida para retorno de aire. Ref.: 30753»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MIDT732`
- [ ] `notifier:sp-200` (SP-200 · Notifier)
      **CONFIRMAR** · confianza media · cita ✓ «## 9.10 Placa de módulo de extinción "SP-200"»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MNDT105_A (brand-tier=mecanico) | x-bra…`
- [ ] `notifier:tf-b3000` (TF-B3000 · Notifier)
      **CONFIRMAR** · confianza media · cita ✓ «Todos los tamaños requieren un kit de tapa principal TF-B3000.»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MIDT190`
- [ ] `pyra:py-x-ma-05-ssm` (PY X-MA-05-SSM · PYRA)
      **CONFIRMAR** · confianza media · cita ✓ «24V DC (PY X-MA-05-SSM and PY X-MA-10-SSM)»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `085501987j_PY X-M-05_10_Installation_ma…`
- [ ] `pyra:py-x-ma-10-ssm` (PY X-MA-10-SSM · PYRA)
      **CONFIRMAR** · confianza media · cita ✓ «24V DC (PY X-MA-05-SSM and PY X-MA-10-SSM)»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `085501987j_PY X-M-05_10_Installation_ma…`
- [ ] `unresolved:020-595` (020-595 · unknown)
      **CONFIRMAR** · confianza media · cita ✓ «\*\*Kit 020-595\*\* > \*\*Panel 6U para\*\* > \*\*montar la fuente\*\* > \*\*de alimentación\*…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MADT190_10`
- [ ] `unresolved:020-596` (020-596 · unknown)
      **CONFIRMAR** · confianza media · cita ✓ «**Kit 020-596** **Cuerpo 3U para conexión del cableado**»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MADT190_10`
- [ ] `unresolved:020-598` (020-598 · unknown)
      **CONFIRMAR** · confianza media · cita ✓ «**Kit 020-598**»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MADT190_10`
- [ ] `unresolved:020-606` (020-606 · unknown)
      **CONFIRMAR** · confianza media · cita ✓ «**Kit 020-606** **Cuerpo 6U para conexión del cableado**»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MADT190_10`
- [ ] `unresolved:230-539-009` (230-539-009 · unknown)
      **CONFIRMAR** · confianza media · cita ✓ «**PANEL DE MONTAJE UNIVERSAL** Ref.: 230-539-009»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MADT190_10`
- [ ] `unresolved:34110400` (34110400 · unknown)
      **RETIRAR** · confianza media · cita ✓ «labeled "RS485" with various electronic components, showing part number "34110400"»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `55310600 Manual TCD-106 kit_ES`
- [ ] `unresolved:55320103` (55320103 · unknown)
      **CONFIRMAR** · confianza media · cita ✓ «REF: 55320103»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `55320103 Manual Zocalo Conexion ES FR G…`
- [ ] `unresolved:55350007` (55350007 · unknown)
      **RETIRAR** · confianza media · cita ✓ «REF: 55350007»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `55350007 Manual Tarjeta Regulacion Moto…`
- [ ] `unresolved:ds-10--tas` (DS 10 -TAS · unknown)
      **CONFIRMAR** · confianza media · cita ✓ «Option: External tone selection for sounders Type DS 5/ 10 -TAS and DS 5/ 10 -TAV»
      frontera hoy 1 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `085501821n_DS10_Installation_manual_D-G…`
- [ ] `unresolved:ds-10--tav` (DS 10 -TAV · unknown)
      **CONFIRMAR** · confianza media · cita ✓ «### Version 2 (DS 5 / DS 10 - TAV)»
      frontera hoy 1 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `085501821n_DS10_Installation_manual_D-G…`
- [ ] `unresolved:ds-10-gl` (DS 10-GL · unknown)
      **CONFIRMAR** · confianza media · cita ✓ «## 8.1 DS 5 + DS 10 -GL-Version These sounders have been designed and certified in accordance…»
      frontera hoy 1 · substring 0 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `085501821n_DS10_Installation_manual_D-G…`
- [ ] `unresolved:fl20xx-ei-hs` (FL20XX EI-HS · Honeywell)
      **RETIRAR** · confianza media · cita ✓ «MI-FL20XXXX EI-HS – NFXI-ASD-XXXX-HS – FL20XX EI-HS – FL01XX E-HS y mismos modelos sin HS»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `FAAST-LT-No-puedo-comunicar-con-el-equi…`
- [ ] `unresolved:mi-fl20xxxx-ei-hs` (MI-FL20XXXX EI-HS · Honeywell)
      **RETIRAR** · confianza media · cita ✓ «Este artículo es válido para los equipos FAAST LT, FAAST LT 200 (HS) autónomos o de lazo: **MI…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `FAAST-LT-No-puedo-comunicar-con-el-equi…`
- [ ] `unresolved:nap-100ac` (NAP 100AC · Honeywell)
      **CONFIRMAR** · confianza media · cita ✓ «3.- Determinar el modelo de sonda utilizado, Ejem. NAP 100AC.»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `HLSI-MN-601`
- [ ] `unresolved:nfxi-asd-xxxx-hs` (NFXI-ASD-XXXX-HS · Honeywell)
      **RETIRAR** · confianza media · cita ✓ «MI-FL20XXXX EI-HS – NFXI-ASD-XXXX-HS – FL20XX EI-HS – FL01XX E-HS y mismos modelos sin HS»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `FAAST-LT-No-puedo-comunicar-con-el-equi…`

**colisión de catálogo — 21**

- [ ] `notifier:5554` (5554 · Notifier)
      **CONFIRMAR** · confianza alta · cita ✓ «## ART. 5554 (PAN-2)»
      frontera hoy 1 · substring 1 · chunks con ese product_model 1 · id-provenance (NO es la fuente de la cita) `MNDT1117` · **colisión**: `ART. 5554 (PAN-2)`
- [ ] `notifier:dg` (DG · Notifier)
      **CONFIRMAR** · confianza alta · cita ✓ «INSTRUÇÕES PARA A MONTAGEM DO ADAPTADOR DE TUBO BA1 NA BASE DO DETECTOR *MODELO DG*»
      frontera hoy 12 · substring 433 · chunks con ese product_model 4 · id-provenance (NO es la fuente de la cita) `MNDT1003` · **colisión**: `DGD-600`, `DGD-620`
- [ ] `notifier:nrt-586tw` (NRT-586TW · Notifier)
      **CONFIRMAR** · confianza alta · cita ✓ «Enlace del Cable de datos de la NRT (NRT-586TW) 115/230 VCA»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `15090SP` · **colisión**: `NRT-586TWF`
- [ ] `notifier:pl4-e` (PL4-E · Notifier)
      **RETIRAR** · confianza alta · cita ✓ «ST.PL4E REV.4.1»
      frontera hoy 19 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MNDT515` · **colisión**: `ST.PL4E`
- [ ] `notifier:tg` (TG · Honeywell)
      **RETIRAR** · confianza alta · cita ✓ «sistema de Control y Supervisión **TG-NOTIFIER**»
      frontera hoy 459 · substring 618 · chunks con ese product_model 1100 · id-provenance (NO es la fuente de la cita) `Tg-Honeywell_Tecnico` · **colisión**: `TG-1020`, `TG-6000`, `TG-6000 Net`, `TG-GSM`, `TG-IP-1`, `TG-IP-10`
- [ ] `notifier:tx` (TX · Notifier)
      **RETIRAR** · confianza alta · cita ✓ «Termina 1: GND (0 V) Terminal 2 TX Terminal 4 RX»
      frontera hoy 494 · substring 538 · chunks con ese product_model 3 · id-provenance (NO es la fuente de la cita) `MIDT212` · **colisión**: `PCB de 2 lazos TX`, `TXLTR`
- [ ] `pepperl-fuchs:z715` (Z715 · Pepperl+Fuchs)
      **CONFIRMAR** · confianza alta · cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728` · **colisión**: `Z715.1K`
- [ ] `pepperl-fuchs:z779` (Z779 · Pepperl+Fuchs)
      **CONFIRMAR** · confianza alta · cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z7…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728` · **colisión**: `Z779.H`
- [ ] `pepperl-fuchs:z787` (Z787 · Pepperl+Fuchs)
      **CONFIRMAR** · confianza alta · cita ✓ «Z705, Z710, Z713, Z715, Z715.1K, Z722, Z728, Z728.CL, Z728.H, Z731, Z755, Z757, Z763, Z764, Z7…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728` · **colisión**: `Z787.H`
- [ ] `pepperl-fuchs:z788` (Z788 · Pepperl+Fuchs)
      **CONFIRMAR** · confianza alta · cita ✓ «Z786, Z787, Z787.H, Z788, Z788.R, Z788.H, Z789, Z796»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728` · **colisión**: `Z788.H`, `Z788.R`
- [ ] `pepperl-fuchs:z810` (Z810 · Pepperl+Fuchs)
      **CONFIRMAR** · confianza alta · cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728` · **colisión**: `Z810.CL`
- [ ] `pepperl-fuchs:z828` (Z828 · Pepperl+Fuchs)
      **CONFIRMAR** · confianza alta · cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728` · **colisión**: `Z828.H`
- [ ] `pepperl-fuchs:z888` (Z888 · Pepperl+Fuchs)
      **CONFIRMAR** · confianza alta · cita ✓ «Z810, Z810.CL, Z813, Z822, Z828, Z828.H, Z857, Z864, Z865, Z872, Z878, Z886, Z887, Z888, Z888.…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728` · **colisión**: `Z888.H`
- [ ] `pepperl-fuchs:z915` (Z915 · Pepperl+Fuchs)
      **CONFIRMAR** · confianza alta · cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728` · **colisión**: `Z915.1K`
- [ ] `pepperl-fuchs:z961` (Z961 · Pepperl+Fuchs)
      **CONFIRMAR** · confianza alta · cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728` · **colisión**: `Z961.H`
- [ ] `pepperl-fuchs:z966` (Z966 · Pepperl+Fuchs)
      **CONFIRMAR** · confianza alta · cita ✓ «Z905, Z910, Z915, Z915.1K, Z922, Z928, Z954, Z955, Z960, Z961, Z961.H, Z964, Z965, Z966, Z966.…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `manual instrucciones Z728` · **colisión**: `Z966.H`
- [ ] `unresolved:fsl100-ir3-w` (FSL100-IR3-W · Honeywell)
      **CONFIRMAR** · confianza alta · cita ✓ «FSL100-IR3 (carcasa roja)<br/>FSL100-IR3-W (carcasa blanca) | Detector de llamas de triple inf…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100…` · **colisión**: `FSL100-IR3-W (carcasa blanca)`
- [ ] `unresolved:fsl100-uv-w` (FSL100-UV-W · Honeywell)
      **CONFIRMAR** · confianza alta · cita ✓ «FSL100-UV (carcasa roja)<br/>FSL100-UV-W (carcasa blanca) | Detector de llamas de UV»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100…` · **colisión**: `FSL100-UV-W (carcasa blanca)`
- [ ] `unresolved:fsl100-uvir-w` (FSL100-UVIR-W · Honeywell)
      **CONFIRMAR** · confianza alta · cita ✓ «FSL100-UVIR (carcasa roja)<br/>FSL100-UVIR-W (carcasa blanca) | Detector de llamas infrarrojo/…»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100…` · **colisión**: `FSL100-UVIR-W (carcasa blanca)`
- [ ] `unresolved:tg` (TG · Honeywell)
      **CONFIRMAR** · confianza alta · cita ✓ «**Software Gráfico TG**: Programa de gestión gráfica bidireccional.»
      frontera hoy 459 · substring 618 · chunks con ese product_model 1100 · id-provenance (NO es la fuente de la cita) `Como-configurar-correos-en-un-TG-HONEYW…` · **colisión**: `TG-1020`, `TG-6000`, `TG-6000 Net`, `TG-GSM`, `TG-IP-1`, `TG-IP-10`
- [ ] `unresolved:vsn-2plus` (VSN 2Plus · Honeywell)
      **RETIRAR** · confianza alta · cita ✓ «NFS Supra / VSN-2Plus / ESS-2Plus Conventional Fire Alarm Control Panel»
      frontera hoy 9 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MF_HSF_280_rv004` · **colisión**: `VSN-2PLUS`

**confianza media; veredicto NO_DECIDIBLE — 4**

- [ ] `notifier:eev2` (EEV(2) · Notifier)
      **NO_DECIDIBLE** · confianza media · cita ✓ «# TABLA DE APROXIMACIONES A GAS PATRÓN - EEV(2)»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MADT608`
- [ ] `notifier:iso232-id3000` (ISO232-ID3000 · Honeywell)
      **NO_DECIDIBLE** · confianza media · cita ✓ «Conecte el Negativo de **UART1** a **0v** de la tarjeta **ISO232-ID3000**»
      frontera hoy 3 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `UCIP-Conexionado-con-ID3000`
- [ ] `notifier:laserstar-mster` (LASERSTAR MÁSTER · Notifier)
      **NO_DECIDIBLE** · confianza media · cita ✓ «El LASERSTAR MÁSTER siempre es el Detector número 1.»
      frontera hoy 2 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MIDT730`
- [ ] `notifier:nfs-plus` (NFS-PLUS · Notifier)
      **NO_DECIDIBLE** · confianza media · cita ✓ «**NFS-PLUS** **Installazione e programmazione**»
      frontera hoy 1 · substring 1 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `NFS4_NFS8-2PLUS_MANU_ITA`

**confianza media; colisión de catálogo — 1**

- [ ] `notifier:smart-3-cd` (SMART 3 CD · Notifier)
      **CONFIRMAR** · confianza media · cita ✓ «Si el detector suministrado dispone de pantalla, consulte el manual suministrado junto con el…»
      frontera hoy 3 · substring 2 · chunks con ese product_model 0 · id-provenance (NO es la fuente de la cita) `MNDT625 (brand-tier=mecanico) | alias-c…` · **colisión**: `SMART3 CD Ex d Cl2`, `SMART3 CD Ex d HCl`, `SMART3 CD Ex d NO2`, `SMART3 CD Ex d SO2`, `SMART3 CD Ex n Cl2`, `SMART3 CD Ex n NO2`

---

## Recibos (la traza completa, fila a fila)

- `evals/s322f_e1b_confirmar_encoger_v1.json` — 359 filas (327 bloque / 32 individual)
- `evals/s322_e1b_revisar_qa_v1.json` — 261 filas (148 bloque / 113 individual)
- Ensamblado por `scripts/s322_packets_v2.py` (determinista, sin LLM) el 20260815T105757Z.

## Auto-verificación del encabezado

Filas declaradas arriba vs filas REALMENTE escritas en este fichero:

- **SECCIÓN 0**: declaradas 475 · escritas 475 · casillas 287 — ✓
- **SECCIÓN 1**: declaradas 145 · escritas 145 · casillas 145 — ✓
- **TOTAL**: 620 = 475 + 145 ✓ (cuadra con las 620 casillas de la v1)
