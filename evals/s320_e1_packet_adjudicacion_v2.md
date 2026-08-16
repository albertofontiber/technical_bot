# s320 E1 — Packet de ADJUDICACIÓN **v2 (encogido)** · 20260815T163607Z

<!-- s324-estado:inicio -->
> ## 🟢 ESTADO s324 (2026-08-16 22:07Z) — lo que ya NO tienes que decidir, y lo que sí
> **Aplicado con recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`** (dúo r32 Sol+Fable antes de escribir; verificación posterior en censo PASS):
> - **§0.A** (49) ✅ · **§0.B** (38 limpias + 4 «tu ojo» + tus anotaciones) ✅ **APLICADO** — 41 filas doc_map.
> - **§1.A** (13): 13/13 resueltas por tus REGLAS R1/R1'/R2/R4/R5 (`evals/s324_reglas_residuo_adjudicacion_v1.json`).
> - **§1.B** (84): las de R6 (7) y R7 (23+4) están RESUELTAS con prueba (altas aplicadas o descartadas); acrónimos cortos (17) y confianza media (14) siguen en cuarentena; todo marcado fila a fila.
> - Retirados del corpus: MA-DT-1160 (tu adjudicación) + 6 fragmentos PT con hermano ES.
>
> **PENDIENTE DE TI (lo único que queda en este fichero):**
> 1. ~~**R1'**~~ — **firmada («R1' OK», 16-ago) y APLICADA**: 3 docs, 62 entries (recibo `s324b_r1prima_aplicar_*.json`).
> 2b. ~~**§0.D**~~ ~~**§0.E**~~ — **REVISADOS por ti y APLICADOS** (16-ago): 17 artefactos no creados; 5 documentos retirados del corpus (ETDT312/314, MADT742, MNDT1202, ASD Rail); altas S/3-2, S/3-IR, S/2-IR, EMA1224B4R/W; TG confirmado como software; MADT731_06 → HSSD-2; 5 retags de pm sucio. Quedan 3 preguntas tuyas (MADT015_01, MNDT600, MNDT701 — marcadas ⏳ en sus filas).
> 2. ~~**§0.C**~~ — **REVISADO por ti y APLICADO** (16-ago; tus 10 notas consolidadas bajo cada fila con mi respuesta `↳ s324b`; revisor Fable 6 hallazgos aplicados): 21 altas + 7 alias + 26 filas doc_map + 2 bajas de corpus (Vision Supra idiomas, MADT190P PT), recibo `s324b_lote_0c_aplicar_*.json`. Quedan DOS preguntas tuyas de §0.C (paraguas «2X-A» y STRATOS, marcadas ⏳ en sus filas) y **§0.D** (17 retirar) · **§0.E** (3).
> 3. Nombres reales con barra (DOA FJ/CPD, EFS/EM 8, CONV232/485, PUL-D/EXT, PUL-P/EXT, STS/CKD+, 20/20MI, 20/20R, NX2/R/R, NX5/R/R): un «sí» = alta.
> 4. Paraguas «2X-A» (familia): el gate léxico lo frenó (core «2·x·a» dispara en «2 x a»); lo adjudicado (guía → familia) ya está cubierto vía doc_map. ¿Lo quieres igualmente?
> 5. Baja del fragmento FR `996-130-000-3 manuel d'utilisation ZX` (1 chunk) — ¿sí?
> 6. Abiertos no bloqueantes: VSN2-PLUS / «Plus2» (solo en docs NFS-SUPRA/UCIP); OCR de HLSI-TI-007.
>
> Marcas fila a fila: `↳ s324:` bajo cada casilla (✅ = no decides nada · ⏳ = tuya).
<!-- s324-estado:fin -->











**SUPERSEDE a `evals/s320_e1_packet_adjudicacion_v1.md`.**
Aquel packet te pedía **253 casillas** una a una (§1 colisiones, §2 tier B,
§3 candidates, §4 product_model sucio). Cuatro pasadas hermanas han refrescado cada
fila contra el estado de HOY, la han juzgado con cita verificada a texto completo y
la han separado en dos: lo que aguanta un solo «sí», y el residuo real.

> ### De **253 casillas** → **99 decisiones**
> - **1 sí en bloque** cubre **143 filas** (§0, en 5 sub-bloques por si prefieres
>   asentir por partes).
> - **98 una a una** (§1) — el residuo con la evidencia junta.
> - **12 ya no aplican** (§2): se cayeron solas al refrescar. No decides nada.

> **Cuenta honesta de casillas** (la escribe el verificador adversarial, no el optimismo del autor): este fichero imprime **241 casillas `- [ ]`** en total — §0.A: 49 · §0.B: 42 · §0.C: 32 · §0.D: 17 · §0.E: 3 · §1.A: 13 · §1.B: 84 · §1.C: 1. Las de §0 están ahí para que PUEDAS bajar a grano fino y desmarcar lo que quieras, no porque haya que marcarlas una a una: el «sí en bloque» las cubre todas de golpe. Si solo asientes a los bloques, tu trabajo real son las decisiones del titular.

**NADA APLICADO.** Ni catálogo (`data/catalog/*.jsonl`), ni Supabase, ni el
snapshot del detector (`data/model_catalog.json`). Todo lo de aquí es PROPUESTA:
marca ✓/✗ y se aplica después por la puerta gobernada, con recibo.

> ⚠ **Aviso de drift entre el encargo y los recibos** (no se ha corregido nada,
> se declara):
> - DRIFT en candidates · bloque: esperado 50, en el recibo 49
> - DRIFT en candidates · individual: esperado 83, en el recibo 84
> - DRIFT en confirmar · bloque: esperado 327, en el recibo 326
> - DRIFT en confirmar · individual: esperado 32, en el recibo 33

---

## SECCIÓN 0 — Aplicables EN BLOQUE si asientes (143)

Criterio, idéntico en las cuatro pasadas: **veredicto claro + confianza alta +
cita verificada contra el CONTENIDO COMPLETO del documento (≤200 chars, espacios
normalizados) + sin ambigüedad estructural**. Una confianza alta cuya cita no
verifica se degradó a media y cayó a la §1: por eso el bloque es asentible de una vez.

### §0.A — Colisiones de identidad (49) · ✅ **YA APLICADO, no firmes nada**

Era la avería del anexo `must_preserve`: el mapa apuntaba a fichas vacías. Se
reparó en la fase A del mismo día y está **medido**: de **0/191 a 191/191**
entradas atestando. Recibo: `evals/s323_fase_a_repunte_aplicar_*.json`.

### §0.B — `doc_map` tier B, REHECHO con la regla **serie × categoría** (38 limpias + 4 a tu criterio)

**Por qué se rehizo** (lo viste tú): la guía de la serie 2X-A se asignaba a 2
productos de los 40 de esa serie. El documento no nombra ni un modelo. La regla
buena no es «la serie» (mezcla interfaces distintas) sino **serie × categoría**:
«centrales de la serie NC», no «la serie NC».

#### §0.B.1 — LIMPIAS: un solo «sí» las cubre todas

- [ ] `averia-de-resistencia-de-baterias-en-central-dxc`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «Tengo avería de resistencia de baterías en central DXc»

- [ ] `con-que-sistema-operativo-es-compatible-el-programa-de-la-`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «¿Con que Sistema Operativo es compatible el programa de la DXc Connexión?»
      ALBERTO: este archivo habla también de la ZX-A, ZX-E, ZX-2/5e, ZX2/5SE

- [ ] `ds_kidde_2x_at_fr_fb_s_202602_es_4276`
      ↳ **s324:** ✅ APLICADO (§0.B) → 1 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `kidde:2x-at-fr-fb-s`
      cita: «# 2X-AT-FR-FB-S **Repetidor de central de incendios direccionable con pantalla táctil y controles de»

- [ ] `ds_kidde_2x_at_fr_s_202602_es_904a`
      ↳ **s324:** ✅ APLICADO (§0.B) → 1 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `kidde:2x-at-fr-s`
      cita: «# 2X-AT-FR-S **Repetidor de central de incendios direccionable con pantalla táctil, caja pequeña**»

- [ ] `ds_kidde_2x_at_fr_s_98dc`
      ↳ **s324:** ✅ APLICADO (§0.B) → 1 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `kidde:2x-at-fr-s`
      cita: «KIDDE COMMERCIAL # 2X-AT-FR-S **Addressable fire panel repeater w touchscreen, small cabinet**»

- [ ] `dxc-connexion-ajuste-contraste-display`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «# DXC / Connexion - Ajuste contraste display **Question** Ajuste contraste display DXc»

- [ ] `dxc-connexion-averia-f-alimentacion-externa`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «# DXC Connexion - Avería F. Alimentación externa **Question** La central DXC Connexión indica **"FAL»

- [ ] `dxc-connexion-averia-nueva-f-alimentacion-externa`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «La central DXC Connexión indica "*NUEVA F.A. EXT.*"»

- [ ] `dxc-connexion-compatibilidad-de-programas-con-versiones`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «No todas las versiones del software de configuración **MK-DXC Configuration Tools** se pueden usar c»

- [ ] `dxc-no-puedo-comunicar-con-la-central`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «Para comunicar con las centrales DXC Connexión necesita:»

- [ ] `dxc-porque-al-activan-elementos-en-alarma-no-se-enciende-s`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «En la central DXC Connexión con el fin de aprovechar al máximo la corriente del lazo, solo **las cua»

- [ ] `dxc-puedo-anular-la-clave-de-usuario-y-acceder-directament`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «# DXC ¿Puedo anular la clave de usuario y acceder directamente al teclado?»

- [ ] `dxc-referencias-repuestos`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «# DXC - Referencias repuestos **Question** ¿Necesito saber la referencia de un determinado repuesto »

- [ ] `dxc-puedo-cambiar-la-clave-de-nivel-3`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «La clave de acceso a centrales Morley modelo DXc por defecto es **9898 y NO** puede ser modificada»

- [ ] `dxc-conexion-como-solucionar-la-averia-de-estado-inconsist`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «# DXc/Conexion ¿Como solucionar la avería de Estado Inconsistente Anulado?»

- [ ] `dxc-configuracion-de-la-tarjeta-232-aislada-para-comunicar`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «Para que la central DXc, comunique con el TG, deberá activar el protocolo de comunicaciones en las o»

- [ ] `dxc-connexion-como-solucionar-la-averia-de-ent-placa-1-o-2`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «¿Como poder solucionar las averías de Entrada de Placa 1 o 2 en la DXc / Conexion?»

- [ ] `dxc-opciones-de-disparo-de-programas-matrices`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «Las opciones de disparo de programas y sus funciones en la central DXc son:»

- [ ] `dxc-tipos-abreviaturas-de-equipos`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «Principales abreviaturas / tipos de equipos en la central DXc»

- [ ] `dxc-tipos-de-accion-para-entradas`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «Los tipos de acción para entradas y sus funciones para la central DXc son:»

- [ ] `dxc_connexion averia-de-resistencia-de-baterias`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «Tengo avería de resistencia de baterías en central DXc»

- [ ] `eventos-averias-de-equipos-en-dxc`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «Eventos de equipos en la central DXc (NO RESPONDE, EQUIPO NUEVO, DOBLE DIRECCION, TIPO EQUIPO CAMBIA»

- [ ] `g_inst_kidde_nc_pfx_202502_es_ac3d` · **serie NC × central** (6 ids; la pasada original proponía 6)
      ↳ **s324:** ✅ APLICADO (§0.B) → 6 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `kidde:nc-pf2`, `kidde:nc-pf2-sc`, `kidde:nc-pf4`, `kidde:nc-pf4-sc`, `kidde:nc-pf8`, `kidde:nc-pf8-sc`
      cita: «Guía de instalación rápida de las centrales de incendio convencionales de la Serie NC»

- [ ] `g_uso_kidde_nc_pfx_202502_es_99d2` · **serie NC × central** (6 ids; la pasada original proponía 6)
      ↳ **s324:** ✅ APLICADO (§0.B) → 6 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `kidde:nc-pf2`, `kidde:nc-pf2-sc`, `kidde:nc-pf4`, `kidde:nc-pf4-sc`, `kidde:nc-pf8`, `kidde:nc-pf8-sc`
      cita: «Manual de funcionamiento rápido de las centrales de incendio convencionales de la Serie NC»

- [ ] `inc___doci_141_gu__a_r__pida_kidde_nc_pf__1__fcb9`
      ↳ **s324:** ✅ APLICADO (§0.B) → 6 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `kidde:nc-pf2`, `kidde:nc-pf4`, `kidde:nc-pf8`, `kidde:nc-pf2-sc`, `kidde:nc-pf4-sc`, `kidde:nc-pf8-sc`
      cita: «| **Modelo:** | Central Kidde NC-PF | | **Asunto:** | Guía rápida de usuario |»

- [ ] `ma-dt-1160`
      ↳ **s324:** ✅ RETIRADO del corpus (tu adjudicación s323) — recibo `s324_retirar_docs_aplicar_20260816T105639Z.json`
      → `systemsensor:pf24v`
      cita: «Aplicaciones del *sonido direccional* para la protección de vidas # - ExitPoint™ -»
      ALBERTO: elimina este documento del corpus, porque es una especie de paper hablando sobre un producto de ExitPoint pero no habla de características o de cómo usarlo.

- [ ] `mie-mi-340_1`
      ↳ **s324:** ✅ APLICADO (§0.B) → 1 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:exp-051`
      cita: «IMPRESORA MATRICIAL DE PUERTA MOD.EXP-051 ## MANUAL DE INSTALACIÓN»

- [ ] `mie-mi-431rv2_1`
      ↳ **s324:** ✅ APLICADO (§0.B) → 2 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:zxr-a`, `morley:zxr-p`
      cita: «MANUAL DE INSTALACIÓN Y FUNCIONAMIENTO ZXr-A/ZXr-P»

- [ ] `mi_kidde_nc_pfx_202502_es_62f8` · **serie NC × central** (6 ids; la pasada original proponía 6)
      ↳ **s324:** ✅ APLICADO (§0.B) → 6 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `kidde:nc-pf2`, `kidde:nc-pf2-sc`, `kidde:nc-pf4`, `kidde:nc-pf4-sc`, `kidde:nc-pf8`, `kidde:nc-pf8-sc`
      cita: «Manual de instalación de las centrales de incendio convencionales de la Serie NC»

- [ ] `mndt1160`
      ↳ **s324:** ✅ APLICADO (§0.B+Alberto) → 1 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `systemsensor:pf24v`
      cita: «Sirena Direccional **EXITPOINT** **WITH VOICE MESSAGING** *Guía de Aplicación*»
      ALBERTO: el modelo es ExitPoint

- [ ] `morley-se-pueden-pasar-programaciones-de-zx-y-dimension-a-`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «¿Se pueden pasar programaciones de ZX y Dimensión a Connexion DXC?»
      ALBRETO: también habla de las centrales ZX y DX Dimension (que diría que el modelo es "DX", diferente a DXc), ya que el archivo va sobre como pasar de cualquiera de estas dos a la DXC

- [ ] `niveles-de-control-de-acceso-de-la-central-dxc-conexion`
      ↳ **s324:** ✅ APLICADO (§0.B) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      cita: «Niveles de control de acceso de la central DXC,CONEXION»
      

- [ ] `no-puedo-hacer-rearme-o-silenciar-sirenas-en-la-vsn-lt`
      ↳ **s324:** ✅ APLICADO (§0.B) → 4 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:vsn2-lt`, `morley:vsn4-lt`, `morley:vsn8-lt`, `morley:vsn12-lt`
      cita: «conectando el puente KEY que se encuentra en el canto inferior izquierdo de la tarjeta de las centra»

- [ ] `osid-es-necesario-resetear-la-barrera-de-forma-externa`
      ↳ **s324:** ✅ APLICADO (§0.B) → 1 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `morley:mi-osi-rie`
      cita: «# OSID ¿Es necesario resetear la barrera de forma externa?»

- [ ] `ucip-como-enviar-datos-de-equipos-y-no-solo-eventos-de-zon`
      → `notifier:ucip`
      cita: «# UCIP - Como enviar datos de equipos y no solo eventos de zonas»

- [ ] `ucip-que-datos-necesito-de-la-receptora`
      ↳ **s324:** ✅ APLICADO (§0.B) → 1 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      → `notifier:ucip`
      cita: «# UCIP - ¿Que datos necesito de la receptora?»

- [ ] `bcn-3100019-es_r002_nc_series_fire_alarm_control_panel_qui` · **serie NC × central** (6 ids; la pasada original proponía 6)
      → `kidde:nc-pf2`, `kidde:nc-pf2-sc`, `kidde:nc-pf4`, `kidde:nc-pf4-sc`, `kidde:nc-pf8`, `kidde:nc-pf8-sc`
      cita: «Guía de instalación rápida de las centrales de incendio convencionales de la Serie NC»

- [ ] `bcn-3100020-es_r002_nc_series_fire_alarm_control_panel_qui` · **serie NC × central** (6 ids; la pasada original proponía 6)
      → `kidde:nc-pf2`, `kidde:nc-pf2-sc`, `kidde:nc-pf4`, `kidde:nc-pf4-sc`, `kidde:nc-pf8`, `kidde:nc-pf8-sc`
      cita: «Manual de funcionamiento rápido de las centrales de incendio convencionales de la Serie NC»


#### §0.B.2 — PIDEN TU OJO: la máquina se para y te lo pasa

- [ ] `00-3280-508-4009-03_r003_2x-a_series_quick_operation_guide`
      motivo: **documento de SERIE 2X-A (categoria NO declarada)**
      cita: «Guía de funcionamiento rápido de la serie 2X-A»
      asignación de la pasada original: `kidde:2x-at-f2`, `kidde:2x-at-f2-fb`
      → TU DECISIÓN: 

- [ ] `dxc_guia de usuario_multiling`
      ↳ **s324:** ✅ APLICADO (§0.B.2+Alberto) → 3 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      motivo: **documento de SERIE DX x categoria central**
      cita: «Guía de usuario para centrales de detección de incendios de la serie DX Connexion»
      asignación de la pasada original: `morley:dxc1`, `morley:dxc2`, `morley:dxc4`
      → TU DECISIÓN: OK

- [ ] `hd_ke_dt3101w_hab_202407_es_30e0`
      ↳ **s324:** ✅ APLICADO (§0.B.2+Alberto) → 1 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      motivo: **documento de SERIE EXCELLENCE x categoria detector**
      cita: «KE-DT3101W-HAB ## Detector de calor direccionable inteligente serie Excellence con aislador»
      asignación de la pasada original: `kidde:ke-dt3101w-hab`
      → TU DECISIÓN: OK

- [ ] `hlsi-ti-001`
      ↳ **s324:** ✅ APLICADO (§0.B.2+Alberto) → 1 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      motivo: **documento de SERIE RP1R x categoria central**
      cita: «Centrales de extinción de la Serie RP1r»
      asignación de la pasada original: `notifier:rp1r-supra`
      → TU DECISIÓN: misma adjudicación que el archivo "HLSI-TI-001".diría que también aplica a la "VSN-RP1r+"

### §0.C — Candidates → **ALTA** (32)

Altas `candidate` del draft del detector. Muestreo **dirigido** (dirigido — chunks que MENCIONAN el término (ilike + recorte por regex con frontera de palabra), no los primeros del documento).
Señales duras: menciones estrictas / flexibles(separadores) / en MAYÚSCULAS: la diferencia entre ellas separa producto de artefacto
Degradación: confianza alta sin cita verificada → media → fuera del bloque

Ojo al contar: **32 filas → 27 ids únicos** (una fila es un par id+documento).
Ids propuestos desde MÁS DE UN documento: `kidde:ke-dba-ipw`×2, `kidde:ke-dba-recw`×2, `kidde:ke-dm3110r-kit`×2, `kidde:ke-iu3110`×2, `notifier:id2net`×2.
No son altas duplicadas: es el mismo producto atestado dos veces.
En el lote entero (bloque+residuo) el recibo cuenta 99 ids únicos sobre 133 filas.

- [ ] `aritech:2x-a` (2X-A) → **ALTA** · rol TITULO · doc `00-3280-507-4009-03_r003_2x-a_series_quick_installation_g…`
      ↳ **s324:** ⏳ PENDIENTE DE TI — paraguas «2X-A» (familia): el revisor señaló que tu nota adjudica el ALCANCE, no el riesgo léxico del gate («2 x a» con espacios lo dispararía; 0 casos en 96 consultas reales) ni si incluye la sub-serie táctil 2X-AT (11 de 38). ¿Lo quieres igualmente, con 2X-AT dentro?
      menciones estrictas doc 1 / global 43 en 18 docs · cita ✓ «Guía de instalación rápida de la serie 2X-A»
      ALBERTO: aplica a todos los modelos de la serie 2x-A
      ↳ **s324b:** de acuerdo: NO se crea el producto `aritech:2x-a`; «2X-A» pasa a ser el PARAGUAS de familia (miembros = centrales y repetidores de la serie, derivados por regla; hoy 38). El gate léxico lo había frenado por un negativo SINTÉTICO («2 x a»); medido sobre el tráfico REAL (`query_logs`, 96 consultas): 0 disparos → entra en el lote §0.C con esa medida en el recibo.
- [ ] `kidde:ke-asa-auxr` (KE-ASA-AUXR) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_ASA_AUXR_f28f.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-asa-auxr` · cita verificada en DS_KIDDE_KE_ASA_AUXR_f28f.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 2 / global 8 en 7 docs · cita ✓ «# KE-ASA-AUXR Intelligent addressable notification accessory - deep base (red)»
- [ ] `kidde:ke-dba-adpw-kil` (KE-DBA-ADPW-KIL) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_DBA_ADPW_KIL_202501_ING_c855.pdf`
      ↳ **s324:** ✅ ALTA ya aplicada en s324 (R4/R7, cita verificada) — esta casilla del bloque §0.C queda cubierta
      menciones estrictas doc 3 / global 11 en 2 docs · cita ✓ «# KE-DBA-ADPW-KIL **Intelligent addressable base accessory - Kilsen adapter (White)**»
- [ ] `kidde:ke-dba-adpw-zit` (KE-DBA-ADPW-ZIT) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_DBA_ADPW_ZIT_202501_ING_ed63.pdf`
      ↳ **s324:** ✅ ALTA ya aplicada en s324 (R4/R7, cita verificada) — esta casilla del bloque §0.C queda cubierta
      menciones estrictas doc 3 / global 11 en 2 docs · cita ✓ «The KE-DBA-ADPW-ZIT is an Excellence series base adapter.»
- [ ] `kidde:ke-dba-capw` (KE-DBA-CAPW) → **ALTA** · rol TITULO · doc `HD_KE_DBA_CAPW_202407_ING_d87d.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-dba-capw` · cita verificada en HD_KE_DBA_CAPW_202407_ING_d87d.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 4 / global 5 en 2 docs · cita ✓ «KIDDE COMMERCIAL # KE-DBA-CAPW **Accesorio base direccionable inteligente - Tapa (Blanca)**»
- [ ] `kidde:ke-dba-ipw` (KE-DBA-IPW) → **ALTA** · rol TITULO · doc `HD_KE_DBA_IPW_202407_ING_ffaf.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-dba-ipw` · cita verificada en HD_KE_DBA_IPW_202407_ING_ffaf.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 3 / global 7 en 3 docs · cita ✓ «KIDDE™ COMMERCIAL # KE-DBA-IPW Accesorio base direccionable inteligente - base resistente a la…»
- [ ] `kidde:ke-dba-ipw` (KE-DBA-IPW) → **ALTA** · rol TITULO · doc `MI_KE_DBA_IPW_202407_ES_cc56.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-dba-ipw` · cita verificada en HD_KE_DBA_IPW_202407_ING_ffaf.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 3 / global 7 en 3 docs · cita ✓ «KE-DBA-IPW IP Accessory for Standard Mounting Base Installation Sheet»
- [ ] `kidde:ke-dba-recw` (KE-DBA-RECW) → **ALTA** · rol TITULO · doc `HD_KE_DBA_RECW_202407_ES_bb2b.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-dba-recw` · cita verificada en HD_KE_DBA_RECW_202407_ES_bb2b.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 3 / global 10 en 4 docs · cita ✓ «KE-DBA-RECW Accesorio base direccionable inteligente - base empotrada (blanca)»
- [ ] `kidde:ke-dba-recw` (KE-DBA-RECW) → **ALTA** · rol TITULO · doc `MI_KE_DBA_RECW_202407_ES_aacc.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-dba-recw` · cita verificada en HD_KE_DBA_RECW_202407_ES_bb2b.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 3 / global 10 en 4 docs · cita ✓ «KE-DBA-RECW Recess Accessory for Standard Mounting Base Installation Sheet»
- [ ] `kidde:ke-dba-tagw` (KE-DBA-TAGW) → **ALTA** · rol TITULO · doc `HD_KE_DBA_TAGW_202407_ES_4b26.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-dba-tagw` · cita verificada en HD_KE_DBA_TAGW_202407_ES_4b26.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 5 / global 12 en 8 docs · cita ✓ «KIDDE COMMERCIAL # KE-DBA-TAGW Accesorio base direccionable inteligente - Etiqueta de direcció…»
- [ ] `kidde:ke-dm3110r-ip` (KE-DM3110R-IP) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_DM3110R_IP_202412_ES_8165.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-dm3110r-ip` · cita verificada en DS_KIDDE_KE_DM3110R_IP_202412_ES_8165.pd · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 2 / global 3 en 2 docs · cita ✓ «KE-DM3110R-IP Pulsador direccionable inteligente de la Serie Excellence con aislador - para ex…»
- [ ] `kidde:ke-dm3110r-kit` (KE-DM3110R-KIT) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_DM3110R_KIT_f3b7.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-dm3110r-kit` · cita verificada en DS_KIDDE_KE_DM3110R_KIT_f3b7.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 3 / global 3 en 1 doc · cita ✓ «The KE-DM3110R-KIT is a red, single action indoor MCP with a House-on-Fire functional indicato…»
      ALBERTO: ¿este no es el mismo doc que la fila anterior?
      ↳ **s324b:** sí: es la MISMA fila duplicada en el draft (mismo id `kidde:ke-dm3110r-kit`, mismo doc `DS_KIDDE_KE_DM3110R_KIT_f3b7.pdf`, dos fuentes de extracción). Se aplica UNA sola alta.
- [ ] `kidde:ke-dm3110r-kit` (KE-DM3110R-KIT) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_DM3110R_KIT_f3b7.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-dm3110r-kit` · cita verificada en DS_KIDDE_KE_DM3110R_KIT_f3b7.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 0 / global 3 en 1 doc · cita ✓ «KE-DM3110R-KIT **Excellence Series intelligent addressable manual call point with isolator and…»
- [ ] `kidde:ke-dp3021b` (KE-DP3021B) → **ALTA** · rol TITULO · doc `HD_KE_DP3021B_202407_ES_861a.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-dp3021b` · cita verificada en HD_KE_DP3021B_202407_ES_861a.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 2 / global 6 en 4 docs · cita ✓ «KIDDE COMMERCIAL # KE-DP3021B Detector de calor/óptico dual direccionable inteligente serie Ex…»
- [ ] `kidde:ke-dp3021w` (KE-DP3021W) → **ALTA** · rol TITULO · doc `HD_KE_DP3021W_202407_ES_778e.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-dp3021w` · cita verificada en HD_KE_DP3021W_202407_ES_778e.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 2 / global 9 en 7 docs · cita ✓ «KIDDE™ COMMERCIAL # KE-DP3021W ## Detector de calor/óptico dual direccionable inteligente seri…»
- [ ] `kidde:ke-iu3110` (KE-IU3110) → **ALTA** · rol TITULO · doc `HD_KE_IU3110_202407_ES_42d6.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-iu3110` · cita verificada en HD_KE_IU3110_202407_ES_42d6.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 7 / global 19 en 6 docs · cita ✓ «KE-IU3110 Unidad inteligente direccionable de 1 entrada con aislador»
- [ ] `kidde:ke-iu3110` (KE-IU3110) → **ALTA** · rol REFERENCIA_COMERCIAL · doc `MI_KE_IU3110_202407_ES_5e36.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:ke-iu3110` · cita verificada en HD_KE_IU3110_202407_ES_42d6.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 6 / global 19 en 6 docs · cita ✓ «Product identification | KE-IU3110»
- [ ] `kidde:n-io-mbx-2` (N-IO-MBX-2) → **ALTA** · rol TITULO · doc `DS_KIDDE_N_IO_MBX_2_202505_ES_b34f.pdf`
      ↳ **s324:** ✅ ALTA ya aplicada en s324 (R4/R7, cita verificada) — esta casilla del bloque §0.C queda cubierta
      menciones estrictas doc 3 / global 19 en 7 docs · cita ✓ «La N-IO-MBX-2 es una caja de montaje en superficie diseñada para alojar módulos que requieren…»
- [ ] `kidde:n-io-sbx-2g` (N-IO-SBX-2G) → **ALTA** · rol TITULO · doc `DS_KIDDE_N_IO_SBX_2G_202505_ES_6eb1.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `kidde:n-io-sbx-2g` · cita verificada en DS_KIDDE_N_IO_SBX_2G_202505_ES_6eb1.pdf · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 4 / global 5 en 2 docs · cita ✓ «N-IO-SBX-2G Caja para 1 módulo con carril DIN (grande)»
- [ ] `morley:dxc-connexion` (DXc Connexion) → **ALTA** · rol TITULO · doc `No-puedo-hacer-rearmes-silenciar-sirenas-y-otros-controle…`
      ↳ **s324:** ✅ RESUELTO (tu nota): la FAQ atesta a la familia DXc (dxc1/dxc2/dxc4) en el doc_map; no se crea producto
      menciones estrictas doc 0 / global 21 en 14 docs · cita ✓ «DXC Connexion - Avería F. Alimentación externa»
      ALBERTO: aquí aplicará a todos los modelos de la familia dxc-connexion
      ↳ **s324b:** de acuerdo: NO se crea el producto `morley:dxc-connexion` (es la familia; el paraguas «DXc»/«DX Connexion» ya existe, gt s90). La FAQ pasa al doc_map → `morley:dxc1`, `dxc2`, `dxc4` (regla serie × central, como las demás FAQ DXc).
- [ ] `morley:mod-rs-232` (MOD.RS-232) → **ALTA** · rol TITULO · doc `MIE-MI-330`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `morley:mod-rs-232` · cita verificada en MIE-MI-330 · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 1 / global 1 en 1 doc · cita ✓ «# TARJETA DE COMUNICACIONES RS-232 # MOD.RS-232 # MANUAL DE INSTALACIÓN»
- [ ] `morley:mod-rs-485` (MOD.RS-485) → **ALTA** · rol TITULO · doc `MIE-MI-390`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `morley:mod-rs-485` · cita verificada en MIE-MI-390 · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 1 / global 1 en 1 doc · cita ✓ «# TARJETA DE COMUNICACIONES RS-485 # MOD.RS-485 # MANUAL DE INSTALACIÓN»
- [ ] `morley:vision-supra` (Vision Supra) → **ALTA** · rol TITULO · doc `30012012 TARJETAS IDIOMAS VISION SUPRA rev A`
      ↳ **s324:** ✅ RESUELTO (tu «baja, confirmo»): documento retirado del corpus; sin alta
      menciones estrictas doc 2 / global 4 en 2 docs · cita ✓ «321XXX TARJETAS IDIOMAS VISION SUPRA FECHA: 26/01/2011 REV: A DESCRIPCIÓN: LANZAMIENTO»
      ALBERTO: no estoy seguro, creo que eliminaría este doc.
      ↳ **s324b:** el doc es una hoja de «tarjetas de idiomas» de la Vision Supra (30012012, rev A). Lo dejo ⏳ como BAJA PROPUESTA (no atesto ni doy de alta `morley:vision-supra` desde él). Si confirmas «baja», lo retiro con recibo; si no, lo dejo fuera del lote sin tocar.
- [ ] `notifier:clss-configuration-tool` (CLSS Configuration Tool) → **ALTA** · rol REFERENCIA_COMERCIAL · doc `4188-1124-PT issue 4_01-2026_To.pdf`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `notifier:clss-configuration-tool` · cita verificada en 4188-1124-ES issue 6_01-2026_To · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 4 / global 21 en 6 docs · cita ✓ «Honeywell no recomienda la instalación de más de una instancia del programa CLSS Configuration…»
      ALBERTO: Doc en PT, eliminaría si hay documento similar en ES
      ↳ **s324b:** hecho: `4188-1124-PT` ya está RETIRADO esta mañana (fragmento PT, 6 chunks; el ES `4188-1124-ES issue 6` tiene 116). Esta fila queda sin alta desde ese doc; «CLSS Configuration Tool» es software y se trata como el caso ID²net de abajo (alta desde el doc ES si verifica).
- [ ] `notifier:id2net` (ID²NET) → **ALTA** · rol TITULO · doc `MADT190P_01_C`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `notifier:id2net` · cita verificada en MADT190_01 · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 0 / global 74 en 10 docs · cita ✓ «# RED DIGITAL E INTELIGENTE # ID<sup>2</sup>net»
      ALBERTO: Doc en PT, eliminaría porque el doc "MADT190_01" es la versión en español
      ↳ **s324b:** de acuerdo — misma clase que los 6 PT retirados esta mañana (se me escapó por el nombre `MADT190P_01_C`). Se RETIRA con recibo tras verificar que `MADT190_01` (ES) está activo y con más chunks; sin alta desde el PT.
- [ ] `notifier:id2net` (ID²NET) → **ALTA** · rol TITULO · doc `MADT190_01`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `notifier:id2net` · cita verificada en MADT190_01 · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 61 / global 75 en 13 docs · cita ✓ «# RED DIGITAL E INTELIGENTE # ID²net»
      ALBERTO: ojo que no es un modelo, es un software, y me suena que el software lo teníamos en cuenta de forma diferente, pero dime si no es así.
      ↳ **s324b:** el software SÍ entra en el catálogo como producto con `clasificacion.categoria = software` (precedente: `morley:mk-vsn`/`mk-zx`/`mk50`/`mkdx`, `notifier:opc-rp1r`, `spectrex:winhost`). ID²NET se da de alta como SOFTWARE (no como modelo de hardware), con cita del doc ES `MADT190_01`. Si prefieres otra categoría (p. ej. «pasarela»/red), dilo.
- [ ] `notifier:kit-gas` (KIT-GAS) → **ALTA** · rol TITULO · doc `HLSI-MN-627`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `notifier:kit-gas` · cita verificada en HLSI-MN-627 · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 2 / global 4 en 3 docs · cita ✓ «KIT-GAS ## Teclado de mano para calibración de los detectores de gas de la <ins>serie SMART 3<…»
- [ ] `notifier:nfxi-bsf-wch` (NFXI-BSF-WCH) → **ALTA** · rol TABLA_DE_MODELOS · doc `D 1147-1 BRH Notifier`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `notifier:nfxi-bsf-wch` · cita verificada en HOP-138-9ES issue 5_11-2025_In · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 0 / global 3 en 3 docs · cita ✓ «BRH-PC-102/<br/>NFXI-BSF-WCH | Detector de Base con Sirena y Luz Estroboscópica»
- [ ] `notifier:stratos` (STRATOS) → **ALTA** · rol TITULO · doc `MADT731_02`
      ↳ **s324:** ✅ RESUELTO (tu «este doc es paraguas»): STRATOS = paraguas de familia con sus modelos ya catalogados bajo nombre Notifier (LaserStar-HSSD-2 = Stratos HSSD-2, MINILÁSER25 = Stratos Micra 25, MINILASER 100 = Stratos Micra 100); MADT731_02 → doc_map a los 3; retirados 2 alias erróneos (Stratos-HSSD→SenseNET, Stratos-HSSD detector→MiniLáser25) · recibo `s324b_stratos_aplicar_*.json`
      menciones estrictas doc 18 / global 54 en 11 docs · cita ✓ «Stratos instalado en un almacén o hipermercado»
- [ ] `spectrex:40-40m` (40-40M) → **ALTA** · rol REFERENCIA_COMERCIAL · doc `MNDT725_40-40M`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `spectrex:s40-40m` · cita verificada en MNDT725_40-40M · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 0 / global 0 en 0 docs · cita ✓ «S40/40M XXXXX, donde XXXXX define el modelo según los requisitos anteriores»
      ALBERTO: Modelo S40-40M i.e. con la "S"
      ↳ **s324b:** de acuerdo: canonical `S40/40M` (como lo escribe el doc: «S40/40M XXXXX…») + alias `40/40M` (variante tipográfica; es la forma de las etiquetas del corpus y de los golds «SharpEye 40/40»). Se verifica el token en `MNDT725` antes de escribir.
- [ ] `spectrex:40-40r` (40-40R) → **ALTA** · rol TITULO · doc `MNDT724_40-40R`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `spectrex:s40-40r` · cita verificada en MNDT724_40-40R · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 0 / global 0 en 0 docs · cita ✓ «DETECTOR DE LLAMA INFRARROJO IR # MODELO S40/40R»
      ALBERTO: Modelo S40-40R i.e. con la "S"
      ↳ **s324b:** de acuerdo: canonical `S40/40R` («MODELO S40/40R») + alias `40/40R`. Se verifica el token en `MNDT724`.
- [ ] `spectrex:40-40u` (40-40U) → **ALTA** · rol TABLA_DE_MODELOS · doc `MNDT723_40-40U`
      ↳ **s324:** ✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `spectrex:s40-40u` (+ S40/40UB) · cita verificada en MNDT723_40-40U · recibo `s324b_lote_0c_aplicar_20260816T193507Z.json`
      menciones estrictas doc 0 / global 0 en 0 docs · cita ✓ «| Tipo de combustible | Distancia máxima (metros)<br/>40/40U y UB |»
      ALBERTO: Ojo que son dos modelos, el S40-40U y S40-40UB, el último incluyendo "la función de Prueba incorporada (BIT)"
      ↳ **s324b:** de acuerdo: DOS altas — `S40/40U` y `S40/40UB` (BIT = prueba incorporada), cada una con su cita verificada en `MNDT723`; alias `40/40U`/`40/40UB`. La fila del draft (`spectrex:40-40u`) no se crea tal cual.

### §0.D — Candidates → **RETIRAR** (17)

Términos que el detector propuso como producto y **NO lo son**: son artefactos de
extracción (código del propio documento, nombre de fabricante, frase técnica). La
pasada detectó **48 artefactos** sobre **39 ids únicos**; clases: `codigo_del_propio_documento`, `frase_tecnica_o_corriente`, `nombre_de_fabricante_o_gama`, `no_aparece_en_ningun_sitio`.
Retirar = no darlos de alta. Es la mitad barata del sí: quita ruido del detector.

- [ ] `fidegas:el-11` (EL-11) → **RETIRAR** · ARTEFACTO_EXTRACCION / FRASE_TECNICA · doc `Manual-de-Usuario-S3-2`
      ↳ **s324:** ✅ RESUELTO: EL-11 no se crea (era «el 11/2018»); tus modelos S/3-2 y S/3-IR + S/2-IR DADOS DE ALTA con doc_map y retag del pm · recibo `s324c_lote_0de_aplicar_20260816T201817Z.json`
      estrictas 0 · mayúsculas 0 · como fragmento 1 · cita ✓ «Elaborado y aprobado en Revisión 21 el 11/2018 por Dpto. Calidad.»
      razón: «EL-11» nace de la fecha «el 11/2018»; el producto real del manual es el sensor remoto S/3-2.
      ALBERTO: Modelo S/3-2
- [ ] `fidegas:el-11` (EL-11) → **RETIRAR** · ARTEFACTO_EXTRACCION / FRASE_TECNICA · doc `Manual-de-Usuario-S3-IR-y-S-2-IR`
      ↳ **s324:** ✅ RESUELTO: EL-11 no se crea (era «el 11/2018»); tus modelos S/3-2 y S/3-IR + S/2-IR DADOS DE ALTA con doc_map y retag del pm · recibo `s324c_lote_0de_aplicar_20260816T201817Z.json`
      estrictas 0 · mayúsculas 0 · como fragmento 1 · cita ✓ «Elaborado y aprobado en Revisión 13 el 11/2018 por Dpto. Calidad»
      razón: «EL-11» nace de la fecha «el 11/2018»; el producto real del manual es el sensor remoto S/3-IR y S/2-IR.
      ALBERTO: Modelos S/3-IR y S/2-IR
- [ ] `morley:de-80` (DE-80) → **RETIRAR** · ARTEFACTO_EXTRACCION / FRASE_TECNICA · doc `TG-Cuales-son-los-requisitos-del-PC-para-el-progr…`
      ↳ **s324:** ✅ RESUELTO: DE-80 no se crea; TG confirmado como SOFTWARE (`notifier:tg`, alias TG-HONEYWELL; gate léxico PASS: 0 disparos en 96 consultas reales) · FAQ → doc_map + retag pm
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «Se requiere un disco duro con un mínimo de 80 Gb de espacio libre»
      razón: Nació de la preposición española «de 80» en medidas (80 Gb, 80 columnas, 80 caracteres); nunca aparece como modelo.
      ALBERTO: TG me suena que es el software y que ya ha salido en ocasiones anteriores, pero revísalo por si acaso.
- [ ] `morley:ma120` (MA120) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `HLSI_MA102_bis2.pdf`
      ↳ **s324:** ✅ RETIRADO del draft (artefacto; tu OK del 16-ago): no se crea
      estrictas 2 · mayúsculas 2 · como fragmento 0 · cita ✓ «HLSI_MA120. 16 mayo 2008»
      razón: MA120 solo aparece en el pie de página como código del documento HLSI, junto a la fecha, nunca como producto.
      ALBERTO: OK a retirar
- [ ] `morley:miein-004` (MIEIN-004) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `Relacion-de-producto-obsoleto-de-Morley-IAS-by-Ho…`
      ↳ **s324:** ✅ RETIRADO del draft (artefacto; tu OK del 16-ago): no se crea
      estrictas 0 · mayúsculas 1 · como fragmento 1 · cita ✓ «https://morley-ias.es/documentacion/morley/manualesdes/MIEIN004.pdf»
      razón: MIEIN004 es el nombre del fichero PDF enlazado (código de documento), no un modelo de producto.
      ALBERTO: OK a retirar
- [ ] `notifier:etdt-312` (ETDT-312) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `ETDT312`
      ↳ **s324:** ✅ RETIRADO + documento ETDT312 retirado del corpus (tu nota)
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «NOTIFIER® by Honeywell ET-DT-312 03-01-06 1 de 1»
      razón: «ET-DT-312» es la referencia del documento (patrón tipo MA-DT-015); el contenido trata etiquetas del sistema NAS-2.
      ALBERTO: OK a retirar. retira también el documento del corpus.
- [ ] `notifier:etdt-314` (ETDT-314) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `ETDT314`
      ↳ **s324:** ✅ RETIRADO + documento ETDT314 retirado del corpus (tu nota)
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «by Honeywell ET-DT-314 19-01-07 1 de 1»
      razón: «ET-DT-314» es la referencia del documento en la cabecera; el manual trata de etiquetas del NAS-1u, no de un producto ETDT-314.
      ALBERTO: OK a retirar. retira también el documento del corpus.
- [ ] `notifier:madt-015` (MADT-015) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `MADT015_01`
      ↳ **s324:** ⏳ PENDIENTE DE TI — el texto no nombra el modelo; sus hermanas MADT015_02/_03 ya están mapeadas a NFS8REL/NFS2-8 ⇒ ¿NFS2-8 (no FS2)? FS2-1/2/4 no existen en catálogo
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «MA-DT-015_01_C (997-502) 27/07/04 NOTIFIER ESPAÑA»
      razón: «MADT-015» deriva del código de documento MA-DT-015 en la cabecera del manual; nunca aparece como modelo comercial.
      ALBERTO: ¿puede estar asociado a los modelos de la serie FS" i.e. FS2-1, FS2-2 y FS2-4, en base al esquema de bormes? 
- [ ] `notifier:madt-731` (MADT-731) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `MADT731_06`
      ↳ **s324:** ✅ RETIRADO; MADT731_06 → doc_map `notifier:laserstar-hssd-2` (= HSSD-2, tu adjudicación con URL) + retag pm
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «MA-DT-731_06»
      razón: MADT-731 deriva del código de documento MA-DT-731_06; el manual es una guía genérica de puntos de muestreo capilares, sin tal modelo.
      ALBERTO: Pertenece al modelo HSSD-2, que he visto el mismo doc en esta web: https://www.notifier.es/index.php/component/zoo/category/hssd-2
- [ ] `notifier:madt-742` (MADT-742) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `MADT742`
      ↳ **s324:** ✅ RETIRADO + documento MADT742 retirado del corpus (tu nota)
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «MA-DT-742; 24/12/2007 1 de 1»
      razón: El término deriva del código de documento MA-DT-742, igual que el artefacto conocido MA-DT-015; no aparece como producto.
      ALBERTO: elimina el doc del corpus.
- [ ] `notifier:mndt-1202` (MNDT-1202) → **RETIRAR** · ARTEFACTO_EXTRACCION / NO_APARECE · doc `MNDT1202`
      ↳ **s324:** ✅ RETIRADO + documento MNDT1202 retirado del corpus (tu nota)
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «# Aerosol para limpieza de detectores»
      razón: MNDT-1202 no aparece en el texto; deriva del nombre del fichero MNDT1202, un código de documento como MNDT690.
      ALBERTO: elimína el doc del corpus.
- [ ] `notifier:mndt-600` (MNDT-600) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `MNDT600`
      ↳ **s324:** ⏳ PENDIENTE DE TI — texto genérico (notas de calibración de detectores de gas), sin modelos; en corpus NO hay «SMART3 GD3/GD2» con esa grafía, SÍ la familia SMART 3 (EXPLOSIVOS/TOXICOS/3G ZONA 2, MNDT646) y en catálogo SMART3G-D3 (¿= GD3?). ¿MNDT600 → familia SMART 3 (paraguas nuevo)?
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «**MN-DT-600_A** 06 ABRIL 2011»
      razón: «MNDT-600» deriva del código de manual MN-DT-600_A; es un documento genérico de notas de mantenimiento, no un modelo.
      ALBERTO: aplica a los detectores de gas smart (sensitron). viendo la portada del doc, parece que uno de los modelos es el Smart3 GD3, y el otro "SMART3 GD2", utilizado para Butano. ¿puedes revisar en el corpus si tenemos el documento?
- [ ] `notifier:mndt-701` (MNDT-701) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `MNDT701.pdf`
      ↳ **s324:** ⏳ PENDIENTE — «Software del detector de llamas Triple IR — SPECTRONIX (sharpEye)»: el software no tiene nombre en el texto y la familia SharpEye 20/20 (IR3) no está en catálogo → sin atestar hasta que exista el id
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «**MN-DT-701**<br/>**13 OCTUBRE 1997**<br/>**Versión 1.0**»
      razón: MNDT-701 no aparece verbatim; deriva de MN-DT-701, referencia del manual (como MA-DT-015), no un modelo de producto.
      ALBERTO: parece el software para los detectores de llama Triple IR (también denominado IR3).
- [ ] `notifier:s20` (S20) → **RETIRAR** · ARTEFACTO_EXTRACCION / FRASE_TECNICA · doc `MNDT696`
      ↳ **s324:** ✅ RETIRADO del draft (artefacto; tu OK del 16-ago): no se crea
      estrictas 64 · mayúsculas 64 · como fragmento 64 · cita ✓ «DETECTOR DE LLAMA DE TRIPLE ESPECTRO INFRARROJO IR<sup>3</sup> MODELO S20/20MI»
      razón: Las 64 menciones del documento y 44 del resto van seguidas de más código: «S20» es fragmento del modelo completo S20/20MI.
      Alberto: Modelo S20/20MI
- [ ] `notifier:tidt-060` (TIDT-060) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `TIDT060.pdf`
      ↳ **s324:** ✅ RETIRADO del draft (artefacto; tu OK del 16-ago): no se crea
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «TI-DT-060 05/05/03 1 de 1 # Información Técnica»
      razón: TI-DT-060 es la referencia del documento de Información Técnica, no un modelo; los productos reales son ID50, AM2000, VeriFire, etc.
      alberto: es un documento de compatibilidades de software de carga y descarga con un listado de modelos, por lo que es normal que trate diferentes modelos pero solo lo haga de forma muy tangencial, porque la clave es si el software es o no compatible. 
- [ ] `notifier:tidt-101` (TIDT-101) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `TIDT101.pdf`
      ↳ **s324:** ✅ RETIRADO del draft (artefacto; tu OK del 16-ago): no se crea
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «Información técnica TI-DT-101»
      razón: TIDT-101 deriva del código de documento TI-DT-101; es un procedimiento de actualización de software, no un producto.
      Alberto: parece referirse al software TG, en concreto a la actualización de versión, por lo que parece importante para ese software aunque efectivamente no trata sobre ningún modelo físico concreto.
- [ ] `sound-alert:some-58` (SOME-58) → **RETIRAR** · ARTEFACTO_EXTRACCION / FRASE_TECNICA · doc `ExitPoint- WP ENG`
      ↳ **s324:** ✅ RETIRADO del draft (artefacto; tu OK del 16-ago): no se crea
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «Interdisciplinary research is promoted through some 58 home departments and some 58 resea…»
      razón: Nace de la frase inglesa «some 58» (unos 58 departamentos); nunca aparece como modelo exacto ni en mayúsculas.
      Alberto: ya hemos tratado la versión en Español de este documento y la hemos eliminado del corpus, así que aquí haz lo mismo.

### §0.E — `product_model` sucio: **2 RETAG + 1 MANTENER** (3)

Docs cuyo `product_model` es basura extraída (una fecha, un código). **Ojo: no todos
son RETAG** — 2 RETAG, 1 MANTENER. Un `MANTENER` significa que el valor actual
es correcto y **no hay nada que aplicar**; entra en el bloque para que conste juzgado.

Gates de bloque: `k_unanime`, `citas_verificadas`, `confianza_alta`, `modelos_atestiguados`, `mantener_sin_tapado`
K=3 pasadas del juez `claude-fable-5`, unanimidad exigida.

- [ ] `asd in rail transportation applications_es` · pm actual «MARCH-2011» · Notifier · 2 chunks
      ↳ **s324:** ✅ RETIRADO del corpus (tu nota §0.E)
      veredicto **RETAG** → product_model `FAAST` · confianza alta · cita ✓
      cita: «la tecnología de detección de incendios por aspiración FAAST™ combina técnicas avanzadas de filtraje en tres etapas»
      razón: El valor sucio 'MARCH-2011' es basura extraída de la nota al pie de prensa ('Manchester Evening News, March 2011'). El documento es un folleto de aplicación (transporte ferroviario/metro) de la famil…
      aplicar: documents.pm 'MARCH-2011' → 'FAAST' · chunks_v2.pm 'MARCH-2011' → 'FAAST' en 2 chunks · doc_map: NO se propone alta. El modelo es un PARAGUAS (familia) y resolve() expande 13 miembros qu…
      ⚑ residuo que NO cierra este sí: Al ser FAAST un token paraguas ('divergent': true, 'expand': true), queda pendiente la adjudicación gobernada del doc_map a los 13 miembros del catálogo, o decidir si el folleto aplica a to…
      ALBERTO: elimina documento del corpus.
- [ ] `compatibilidad-entre-equipos-notifier-y-morley` · pm actual «unknown» · Morley · 1 chunk
      ↳ **s324:** ✅ MANTENER (tu nota): sin producto que mapear; la FAQ sigue en el corpus y es servible por retrieval para «¿equipos Notifier en central Morley?»
      veredicto **MANTENER** → product_model `unknown` · confianza alta · cita ✓
      cita: «No, no es posible instalar equipos de Notifier en una central de Morley o equipos de Morley en una central de Notifier, pués los protocolos de comuni…»
      razón: Es una FAQ genérica de compatibilidad marca-a-marca (Notifier vs Morley). El texto completo no imprime ningún modelo de producto: el censo de candidatos por regex está vacío y la respuesta habla de '…
      aplicar: documents.pm SIN CAMBIO · chunks_v2.pm SIN CAMBIO · doc_map: sin fila (correcto: no hay producto que mapear)
      ⚑ residuo que NO cierra este sí: ¿Debería este tipo de FAQ de marca a marca tener una categoría propia (p.ej. product_model='N/A-brand-faq') en vez de 'unknown' para distinguirlo de documentos con modelo aún no identificad…
      Alberto: aquí más que asignar a un modelo, deberías tener en memoria este documento para indicar esto "no es posible instalar equipos de Notifier en una central de Morley o equipos de Morley en una central de Notifier, pués los protocolos de comunicación son distintos y los equipos no comunicarán, además la central indicará una avería, AVERÍA DE TRANSMISIÓN", con referencia al documento.
- [ ] `d686 ema1224b4r_w ns4r` · pm actual «EN-54-3» · Notifier · 1 chunk
      ↳ **s324:** ✅ APLICADO (tu «aplica a EMA1224B4R/W»): alta `notifier:ema1224b4r-w` + doc_map + retag pm EN-54-3 → EMA1224B4R/W · recibo `s324c_lote_0de_aplicar_20260816T201817Z.json`
      veredicto **RETAG** → product_model `EMA1224B4R/W` · confianza alta · cita ✓
      cita: «INSTALLATION INSTRUCTIONS FOR WALL MOUNT SOUNDERS TYPE EMA1224B4R/W»
      razón: El valor actual 'EN-54-3' es una norma (citada dos veces como requisito EN54-3), no un producto. El documento imprime en su título un único modelo, EMA1224B4R/W, y todo el contenido (tonos, especific…
      aplicar: documents.pm 'EN-54-3' → 'EMA1224B4R/W' · chunks_v2.pm 'EN-54-3' → 'EMA1224B4R/W' en 1 chunks · doc_map: alta de fila BLOQUEADA: el modelo no existe en el catálogo gobernado → requiere primero a…
      ⚑ residuo que NO cierra este sí: ¿El catálogo gobernado distingue EMA1224B4R y EMA1224B4W como dos SKUs separados (lo que convertiría esto en MULTI), o acepta el token compuesto EMA1224B4R/W tal como lo imprime KAC?
      Alberto: aplica a EMA1224B4R/W

---

## SECCIÓN 1 — Una a una (98)

El residuo real: nada de aquí pasó el gate. Cada fila trae **toda** la evidencia
junta para decidir sin abrir nada más.

### §1.A — `doc_map` tier B, residuo (13)

Motivos de caída (del recibo, uno por línea):

  - (3×) confianza media
  - (2×) confianza media; cita no verificada full-text; la cita verifica pero NO nombra al sujeto: la entrada se apoyaría sólo en la ficha del documento, no en su contenido
  - (1×) ambigüedad estructural: la entrada atestaría productos de 2 marcas ['morley', 'notifier'] — clase rebrand/OEM, decisión entre marcas
  - (1×) ids CANDIDATE ['notifier:vsn-plus']: el producto existe pero está pendiente de QA humana — atestarlo con un documento es promoverlo de hecho, y esa es una decisión de Alberto, no un efecto…
  - (1×) ids CANDIDATE ['kidde:2x-at']: el producto existe pero está pendiente de QA humana — atestarlo con un documento es promoverlo de hecho, y esa es una decisión de Alberto, no un efecto colate…
  - (1×) posible atribución circular: el id viene de un alias/paraguas AUTO-IMPORTADO de un documento (s83:MIEMI120rev05) y este manual no nombra al sujeto ni una vez
  - (1×) confianza media; ids CANDIDATE ['morley:dx1e', 'morley:dx2e', 'morley:dx4e']: el producto existe pero está pendiente de QA humana — atestarlo con un documento es promoverlo de hecho, y esa…
  - (1×) K=2 sin acuerdo: 2ª pasada dice OTROS_IDS/media con ['kidde:2x-af1', 'kidde:2x-af2', 'kidde:2x-afr', 'kidde:2x-ae1', 'kidde:2x-ae2']
  - (1×) ambigüedad estructural: el token ['KE-DP3120W-SN', 'KE-DP3120W-SNV', 'KE-DP3121B', 'KE-DP3121B-SNV', 'KE-DP3121W', 'KE-DP3121W-SN', 'KE-DP3121W-SNV'] sería un producto que NO está en el cat…
  - (1×) ambigüedad estructural: el token ['KE-IU3110'] sería un producto que NO está en el catálogo (antes que la entrada de doc_map hace falta un ALTA)

- [ ] `4188-1132-pt issue 4_04_2025-qref` (Notifier · 1 chunk · vigente)
      ↳ **s324:** ✅ RETIRADO del corpus (fragmento PT con hermano ES; tu sí del 16-ago)
      pm doc «INSPIRE E10/E15» · pm chunks «INSPIRE E10/E15» · tokens sin id: `E15`
      ids del packet 12-ago `notifier:inspire-e10` → resueltos HOY `notifier:inspire-e10`
      juez: **MULTI** `notifier:inspire-e10`, `notifier:inspire-e15` · confianza media · cita ✗ sin cita en el recibo
      sujeto según el juez: Guía rápida de las centrales de incendio Notifier INSPIRE E10 y E15 (proceso de aprendizaje de dispositivos del lazo)
      menciones máximas del sujeto en el documento: 0
      **por qué NO entra en bloque**: confianza media; cita no verificada full-text; la cita verifica pero NO nombra al sujeto: la entrada se apoyaría sólo en la ficha del documento, no en su contenido
- [ ] `996-130-000-3 manuel d'utilisation zx_hlsi` (Morley · 1 chunk · vigente)
      ↳ **s324:** ⏳ PENDIENTE DE TI — fragmento FR de 1 chunk (mismo caso que los PT retirados): ¿BAJA? (no se atesta hasta decidirlo)
      pm doc «ZX» · pm chunks «ZX» · tokens sin id: —
      ids del packet 12-ago `morley:zx2e`, `morley:zx2se`, `morley:zx50`, `morley:zxae`, `morley:zxce`, `morley:zxhe` → resueltos HOY — · **deriva**
      juez: **MULTI** `morley:zx2e`, `morley:zx2se`, `morley:zx50`, `morley:zxae`, `morley:zxce`, `morley:zxhe` · confianza media · cita ✓ «Manuel d'utilisation MORLEY-IAS Central de détection d’incendie ZX»
      sujeto según el juez: Manual de usuario en francés de la central de detección de incendios Morley-IAS serie ZX (solo páginas finales de notas y contacto)
      menciones máximas del sujeto en el documento: 1
      **por qué NO entra en bloque**: confianza media
      ALBERTO: baja del corpus.
- [ ] `asd harsh environments_sp` (Xtralis · 6 chunks · vigente)
      ↳ **s324:** ✅ APLICADO (R1) → 13 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      pm doc «FAAST» · pm chunks «FAAST» · tokens sin id: —
      ids del packet 12-ago `morley:mi-fl2011ei`, `morley:mi-fl2012ei`, `morley:mi-fl2022ei`, `notifier:faast-8100e`, `notifier:fl0111e-hs`, `notifier:fl0112e-hs` …(+7) → resueltos HOY `morley:mi-fl2011ei`, `morley:mi-fl2012ei`, `morley:mi-fl2022ei`, `notifier:faast-8100e`, `notifier:fl0111e-hs`, `notifier:fl0112e-hs` …(+7)
      juez: **IDS_CORRECTOS** `notifier:fl0111e-hs`, `notifier:fl0112e-hs`, `notifier:fl0122e-hs`, `notifier:fl2011ei-hs`, `notifier:fl2012ei-hs`, `notifier:fl2022ei-hs` …(+7) · confianza alta · cita ✓ «Detección de humo por aspiración en ambientes agresivos FAAST FIRE ALARM ASPIRATION SENSI…»
      sujeto según el juez: Guía de aplicación de la familia de detectores de humo por aspiración FAAST en ambientes agresivos
      menciones máximas del sujeto en el documento: 5
      **por qué NO entra en bloque**: ambigüedad estructural: la entrada atestaría productos de 2 marcas ['morley', 'notifier'] — clase rebrand/OEM, decisión entre marcas
- [ ] `con-que-sistema-operativo-es-compatible-el-programa-de-la-zx-y-dx` (Morley · 1 chunk · vigente)
      ↳ **s324:** ✅ APLICADO (R1) → 10 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      pm doc «ZX/DX» · pm chunks «ZX/DX» · tokens sin id: `DX`
      ids del packet 12-ago `morley:zx2e`, `morley:zx2se`, `morley:zx50`, `morley:zxae`, `morley:zxce`, `morley:zxhe` → resueltos HOY — · **deriva**
      juez: **MULTI** `morley:zx2e`, `morley:zx2se`, `morley:zxae`, `morley:zxhe`, `morley:zxce`, `morley:zx50` · confianza media · cita ✓ «¿Con que Sistema Operativo es compatible el programa de la ZX y DX? **Answers** Los siste…»
      sujeto según el juez: Software de programación (FIRE5/FIRE6/MK-DX) de las centrales de incendio de las familias ZX y DX de Morley
      menciones máximas del sujeto en el documento: 1
      **por qué NO entra en bloque**: confianza media
- [ ] `finales-de-linea-de-las-centrales-convencionales` (Morley · 1 chunk · vigente)
      ↳ **s324:** ✅ APLICADO (R1+R2) → 8 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      pm doc «NFS2/NFS4/NFS8/VSN2-LT/VSN4-LT/VSN8-LT/VSN12-LT/VSN2-P…» · pm chunks «NFS2/NFS4/NFS8/VSN2-LT/VSN4-LT/VSN8-LT/VSN12-LT/VSN2-P…» · tokens sin id: `NFS2`, `NFS4`, `NFS8`, `VSN2-PLUS`, `VSN12-PLUS`
      ids del packet 12-ago `morley:vsn-4-plus`, `morley:vsn-8-plus`, `morley:vsn12-lt`, `morley:vsn2-lt`, `morley:vsn4-lt`, `morley:vsn8-lt` → resueltos HOY `morley:vsn-4-plus`, `morley:vsn-8-plus`, `morley:vsn12-lt`, `morley:vsn2-lt`, `morley:vsn4-lt`, `morley:vsn8-lt`
      juez: **MULTI** `notifier:nfs-2-8`, `morley:vsn2-lt`, `morley:vsn4-lt`, `morley:vsn8-lt`, `morley:vsn12-lt`, `morley:vsn-4-plus` …(+2) · confianza alta · cita ✓ «Los finales de línea para las centrales convencionales son; * **NFS2-8** La central está…»
      sujeto según el juez: FAQ sobre los elementos de final de línea de las centrales convencionales NFS2-8, familia VSN-LT, familia VSN-PLUS y la VSN2-PLUS
      menciones máximas del sujeto en el documento: 1
      **por qué NO entra en bloque**: ids CANDIDATE ['notifier:vsn-plus']: el producto existe pero está pendiente de QA humana — atestarlo con un documento es promoverlo de hecho, y esa es una decisión de Alberto, no un efecto colateral; ambigüedad estructu…
      ids NO consumibles (candidate/retirado): `notifier:vsn-plus`
- [ ] `gr_kidde_2x_at_fr_fb_s_27cf` (Aritech · 29 chunks · vigente)
      ↳ **s324:** ✅ APLICADO (R1' — tu «R1' OK» del 16-ago) → 10 modelos NOMBRADOS de 11 de la serie · recibo `s324b_r1prima_aplicar_*.json`
      pm doc «2X-AT-FR-FB-S/2X-AT-FR-S» · pm chunks «2X-AT-FR-FB-S/2X-AT-FR-S» · tokens sin id: —
      ids del packet 12-ago `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s` → resueltos HOY `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s`
      juez: **MULTI** `kidde:2x-at`, `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s` · confianza alta · cita ✓ «2X-AT Series Quick Start Guide»
      sujeto según el juez: Guía rápida de la serie 2X-AT de centrales y repetidores direccionables de alarma de incendio (Kidde Commercial / Carrier)
      menciones máximas del sujeto en el documento: 1
      **por qué NO entra en bloque**: ids CANDIDATE ['kidde:2x-at']: el producto existe pero está pendiente de QA humana — atestarlo con un documento es promoverlo de hecho, y esa es una decisión de Alberto, no un efecto colateral
      ids NO consumibles (candidate/retirado): `kidde:2x-at`
- [ ] `hlsi-ti-007_vsn-4rel` (Morley · 1 chunk · vigente)
      ↳ **s324:** ⏳ re-ingesta OCR primero (tu adjudicación: modelo VSN-4REL); atestación después
      pm doc «VSN-4REL» · pm chunks «VSN-4REL» · tokens sin id: —
      ids del packet 12-ago `notifier:vsn-4rel` → resueltos HOY `notifier:vsn-4rel`
      juez: **IDS_CORRECTOS** `notifier:vsn-4rel` · confianza media · cita ✗ sin cita en el recibo
      sujeto según el juez: Relé/módulo VSN-4REL (según ficha; el contenido ingestado solo muestra la portada Honeywell Life Safety Iberia)
      menciones máximas del sujeto en el documento: 0
      **por qué NO entra en bloque**: confianza media; cita no verificada full-text; la cita verifica pero NO nombra al sujeto: la entrada se apoyaría sólo en la ficha del documento, no en su contenido
- [ ] `mi_kidde_2x_at_f2_fb_07d4` (Aritech · 212 chunks · vigente)
      ↳ **s324:** ✅ APLICADO (R1' — tu «R1' OK» del 16-ago) → 26 modelos NOMBRADOS de 38 de la serie · recibo `s324b_r1prima_aplicar_*.json`
      pm doc «2X-AT-F2/2X-AT-F2-FB/2X-AT-FR-FB-S/2X-AT-FR-S» · pm chunks «2X-AT-F2/2X-AT-F2-FB/2X-AT-FR-FB-S/2X-AT-FR-S» · tokens sin id: —
      ids del packet 12-ago `kidde:2x-at-f2`, `kidde:2x-at-f2-fb`, `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s` → resueltos HOY `kidde:2x-at-f2`, `kidde:2x-at-f2-fb`, `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s`
      juez: **OTROS_IDS** `kidde:2x-af2`, `kidde:2x-af1`, `kidde:2x-afr`, `kidde:2x-ae2`, `kidde:2x-ae1` · confianza alta · cita ✓ «This is the installation manual for the 2X-A Series fire alarm, repeater, and evacuation…»
      sujeto según el juez: Manual de instalación de las centrales de incendio, repetidores y centrales de evacuación de la serie 2X-A de Kidde (variantes 2X-AF1, 2X-AF2, 2X-AFR…
      K=2 (2ª pasada): **OTROS_IDS** `kidde:2x-af1`, `kidde:2x-af2`, `kidde:2x-afr`, `kidde:2x-ae1`, `kidde:2x-ae2` · confianza media
      menciones máximas del sujeto en el documento: 0
      **por qué NO entra en bloque**: K=2 sin acuerdo: 2ª pasada dice OTROS_IDS/media con ['kidde:2x-af1', 'kidde:2x-af2', 'kidde:2x-afr', 'kidde:2x-ae1', 'kidde:2x-ae2']
- [ ] `mi_kidde_ke_dp312x_snx_202512_es_242d` (Kidde · 45 chunks · vigente)
      ↳ **s324:** ✅ APLICADO (R4) → 6 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      pm doc «KE-DP3120W/KE-DP3120W-SN/KE-DP3120W-SNV/KE-DP3121B/KE-…» · pm chunks «KE-DP3120W/KE-DP3120W-SN/KE-DP3120W-SNV/KE-DP3121B/KE-…» · tokens sin id: `KE-DP3120W-SN`, `KE-DP3120W-SNV`, `KE-DP3121B`, `KE-DP3121B-SNV`, `KE-DP3121W`, `KE-DP3121W-SN`, `KE-DP3121W-SNV`
      ids del packet 12-ago `kidde:ke-dp3120w` → resueltos HOY `kidde:ke-dp3120w`
      juez: **IDS_CORRECTOS** `kidde:ke-dp3120w` · confianza alta · cita ✓ «Excellence Series Intelligent Addressable Dual Optical and Dual Optical/Heat Detectors wi…»
      sujeto según el juez: Hoja de instalación de familia: detectores direccionables inteligentes Excellence Series ópticos duales y ópticos/calor con sirena/VAD integrados (va…
      menciones máximas del sujeto en el documento: 8
      **por qué NO entra en bloque**: ambigüedad estructural: el token ['KE-DP3120W-SN', 'KE-DP3120W-SNV', 'KE-DP3121B', 'KE-DP3121B-SNV', 'KE-DP3121W', 'KE-DP3121W-SN', 'KE-DP3121W-SNV'] sería un producto que NO está en el catálogo (antes que la entrada de…
- [ ] `mi_kidde_ke_io3144_631e` (Kidde · 33 chunks · vigente)
      ↳ **s324:** ✅ APLICADO (R4) → 2 id(s) · recibo `s324_lote_firmado_aplicar_20260816T113215Z.json`
      pm doc «KE-IO3144/KE-IU3110» · pm chunks «KE-IO3144/KE-IU3110» · tokens sin id: `KE-IU3110`
      ids del packet 12-ago `kidde:ke-io3144` → resueltos HOY `kidde:ke-io3144`
      juez: **MULTI** `kidde:ke-io3144`, `kidde:ke-io3122` · confianza alta · cita ✓ «This installation sheet includes information on the following 3000 Series input/output mo…»
      sujeto según el juez: Hoja de instalación de los módulos de entrada/salida direccionables de la serie 3000 (Excellence), cubriendo KE-IO3122 (2 E/S) y KE-IO3144 (4 E/S)
      menciones máximas del sujeto en el documento: 8
      **por qué NO entra en bloque**: ambigüedad estructural: el token ['KE-IU3110'] sería un producto que NO está en el catálogo (antes que la entrada de doc_map hace falta un ALTA)
- [ ] `mie-mi-120p` (Morley · 1 chunk · vigente)
      ↳ **s324:** ✅ RETIRADO del corpus (fragmento PT con hermano ES; tu sí del 16-ago)
      pm doc «VSN 2-4» · pm chunks «VSN 2-4» · tokens sin id: —
      ids del packet 12-ago `morley:vsn2` → resueltos HOY `morley:vsn2`
      juez: **IDS_CORRECTOS** `morley:vsn2` · confianza alta · cita ✓ «● - ● VISION ● BATTERY»
      sujeto según el juez: Central convencional de incendios Morley Vision (VSN 2-4), panel frontal con zonas Z1-Z4
      menciones máximas del sujeto en el documento: 0
      **por qué NO entra en bloque**: posible atribución circular: el id viene de un alias/paraguas AUTO-IMPORTADO de un documento (s83:MIEMI120rev05) y este manual no nombra al sujeto ni una vez
- [ ] `miemu520p` (Morley · 1 chunk · vigente)
      ↳ **s324:** ✅ RETIRADO del corpus (fragmento PT con hermano ES; tu sí del 16-ago)
      pm doc «Dimension» · pm chunks «Dimension» · tokens sin id: `Dimension`
      ids del packet 12-ago — → resueltos HOY —
      juez: **MULTI** `morley:dx1e`, `morley:dx2e`, `morley:dx4e` · confianza media · cita ✓ «MORLEY-IAS Série Dimension»
      sujeto según el juez: Manual de funcionamiento de las centrales de incendio Morley-IAS de la Série Dimension (páginas finales del manual de familia)
      menciones máximas del sujeto en el documento: 1
      **por qué NO entra en bloque**: confianza media; ids CANDIDATE ['morley:dx1e', 'morley:dx2e', 'morley:dx4e']: el producto existe pero está pendiente de QA humana — atestarlo con un documento es promoverlo de hecho, y esa es una decisión de Alberto, no…
      ids NO consumibles (candidate/retirado): `morley:dx1e`, `morley:dx2e`, `morley:dx4e`
- [ ] `mu_kidde_2x_at_fr_fb_s_6c31` (Aritech · 46 chunks · vigente)
      ↳ **s324:** ✅ APLICADO (R1' — tu «R1' OK» del 16-ago) → 26 modelos NOMBRADOS de 38 de la serie · recibo `s324b_r1prima_aplicar_*.json`
      pm doc «2X-AT-FR-FB-S/2X-AT-FR-S» · pm chunks «2X-AT-FR-FB-S/2X-AT-FR-S» · tokens sin id: —
      ids del packet 12-ago `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s` → resueltos HOY `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s`
      juez: **OTROS_IDS** `kidde:2x-af2`, `kidde:2x-af1`, `kidde:2x-afr`, `kidde:2x-ae2`, `kidde:2x-ae1` · confianza media · cita ✓ «KIDDE COMMERCIAL # 2X-A Series Operation Manual P/N 00-3280-505-4003-02»
      sujeto según el juez: Manual de operación de la familia de centrales de incendio Kidde/Carrier serie 2X-A (variantes 2X-AF1, 2X-AF2, 2X-AFR, 2X-AE1, 2X-AE2)
      menciones máximas del sujeto en el documento: 0
      **por qué NO entra en bloque**: confianza media

### §1.B — Candidates, residuo (84)

Agrupados por **su primer motivo de caída** (el recibo trae la lista completa por
fila). Un mismo id puede aparecer con varias grafías: eso es exactamente lo que
hay que adjudicar.

**ambiguedad:termino-multi-modelo** — 23

- [ ] `avotec:doa-fj-cpd` (DOA FJ/CPD)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «**DOA FJ/CPD** – Fire alarm sounding device for fire signalling conform to regulatio…»
      doc `Manual Rotulo REXD-103_EN` · estrictas doc 2 / global 2 en 1 doc
- [ ] `fidegas:s-2-t1-y-s-3-t1` (S/2-T1 y S/3-T1)
      ↳ **s324:** ✅ RESUELTO por R7: partido en sus componentes con cita propia (ver altas / doc_map aplicados); el id concatenado no se crea
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «SENSOR REMOTO # S/3-T1 y S/2-T1 ## TÓXICOS»
      doc `Manual-de-Usuario-S3-T1-y-S-2-T1` · estrictas doc 0 / global 0 en 0 docs · otros motivos: contradiccion:producto-real-sin-mencion-estricta-ni-en-mayusculas; juez:propone-otra-grafia(S/3-T1 y S/2-T1)
      el juez propone otra grafía: `S/3-T1 y S/2-T1`
- [ ] `kidde:ke-dba-adpw-kil-ke-dba-adpw-zit` (KE-DBA-ADPW-KIL/KE-DBA-ADPW-ZIT)
      ↳ **s324:** ✅ RESUELTO por R7: partido en sus componentes con cita propia (ver altas / doc_map aplicados); el id concatenado no se crea
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «| KE-DBA-ADPW-KIL | Adaptor Accessory for Kilsen Mounting Bases |»
      doc `G_INST_KIDDE_KE_DBA_ADPW_202502_ES_70e7.pdf` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `KE-DBA-ADPW-KIL y KE-DBA-ADPW-ZIT (serie KE-DBA-ADPW)`
- [ ] `kidde:ke-dba-labw-l1s-ke-dba-labw-l2s-ke-dba-labw-l3s-ke-dba-labw-l4s` (KE-DBA-LABW-L1S/KE-DBA-LABW-L2S/KE-DBA-LABW-L3S/KE-DBA-LABW-L4S)
      ↳ **s324:** ✅ RESUELTO por R7: ningún componente L1S..L4S aparece como token → no se da de alta (el juez propone KE-DBA-LABW-S: si quieres ese alta, dilo)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «El KE-DBA-LABW-S es un juego de etiquetas adhesivas de la serie Excellence de format…»
      doc `HD_KE_DBA_LABW_LxS_202407_ES_2fc1.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media
      el juez propone otra grafía: `KE-DBA-LABW-S`
- [ ] `kidde:ke-dp3121b-ke-dp3121b-snv` (KE-DP3121B/KE-DP3121B-SNV)
      ↳ **s324:** ✅ RESUELTO por R7: partido en sus componentes con cita propia (ver altas / doc_map aplicados); el id concatenado no se crea
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «KIDDE™ COMMERCIAL # KE-DP3121B-SNV»
      doc `DS_KIDDE_KE_DP3121B_SNV_202503_ES_b5bc.pdf` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `KE-DP3121B-SNV`
- [ ] `kidde:ke-dp3121w-ke-dp3121w-sn` (KE-DP3121W/KE-DP3121W-SN)
      ↳ **s324:** ✅ RESUELTO por R7: partido en sus componentes con cita propia (ver altas / doc_map aplicados); el id concatenado no se crea
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «KIDDE COMMERCIAL # KE-DP3121W-SN Detector de calor/óptico dual direccionable intelig…»
      doc `DS_KIDDE_KE_DP3121W_SN_202503_ES_5938.pdf` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `KE-DP3121W-SN`
- [ ] `kidde:ke-dp3121w-ke-dp3121w-sn-ke-dp3121w-snv` (KE-DP3121W/KE-DP3121W-SN/KE-DP3121W-SNV)
      ↳ **s324:** ✅ RESUELTO por R7: partido en sus componentes con cita propia (ver altas / doc_map aplicados); el id concatenado no se crea
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «KIDDE COMMERCIAL # KE-DP3121W-SNV Detector de calor/óptico dual direccionable inteli…»
      doc `DS_KIDDE_KE_DP3121W_SNV_202503_ES_8699.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media
      el juez propone otra grafía: `KE-DP3121W-SNV`
- [ ] `kidde:ke-iu3111-zme-kit-2x-ae1-09` (KE-IU3111-ZME/KIT 2X-AE1-09)
      ↳ **s324:** ✅ RESUELTO por R7: partido en sus componentes con cita propia (ver altas / doc_map aplicados); el id concatenado no se crea
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «KIDDE™ COMMERCIAL # KE-IU3111-ZME»
      doc `DS_KIDDE_KE_IU3111_ZME_f908.pdf` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `KE-IU3111-ZME`
- [ ] `kidde:ke-iu3111-zme-kit-2x-ae1-09` (KE-IU3111-ZME/KIT 2X-AE1-09)
      ↳ **s324:** ✅ RESUELTO por R7: partido en sus componentes con cita propia (ver altas / doc_map aplicados); el id concatenado no se crea
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «KE-IU3111-ZME Intelligent Addressable Zone Monitoring Unit (device type 1ZMxi)»
      doc `MI_KE_IU3111_ZME_202407_ES_fde1.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media
      el juez propone otra grafía: `KE-IU3111-ZME`
- [ ] `kidde:n-io-mbx-1-n-io-mbx-2` (N-IO-MBX-1/N-IO-MBX-2)
      ↳ **s324:** ✅ RESUELTO por R7: partido en sus componentes con cita propia (ver altas / doc_map aplicados); el id concatenado no se crea
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «KIDDE COMMERCIAL # N-IO-MBX-1 Caja para módulos carril DIN»
      doc `DS_KIDDE_N_IO_MBX_1_202505_ES_07ca.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `N-IO-MBX-1`
- [ ] `kidde:n-io-mbx-1-n-io-mbx-2` (N-IO-MBX-1/N-IO-MBX-2)
      ↳ **s324:** ✅ RESUELTO por R7: partido en sus componentes con cita propia (ver altas / doc_map aplicados); el id concatenado no se crea
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «N-IO-MBX Series DIN Rail Module Box Installation Sheet»
      doc `MI_N_IO_MBX_X_202505_ES__1__1fd1.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: contradiccion:producto-real-sin-mencion-estricta-ni-en-mayusculas; juez:propone-otra-grafia(N-IO-MBX-1 y N-IO-MBX-2 (serie N-IO-MBX)); ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `N-IO-MBX-1 y N-IO-MBX-2 (serie N-IO-MBX)`
- [ ] `kidde:n-io-sbx-1g-n-io-sbx-2g` (N-IO-SBX-1G/N-IO-SBX-2G)
      ↳ **s324:** ✅ RESUELTO por R7: partido en sus componentes con cita propia (ver altas / doc_map aplicados); el id concatenado no se crea
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «KIDDE COMMERCIAL # N-IO-SBX-1G Caja para 1 módulo con carril DIN (pequeño)»
      doc `DS_KIDDE_N_IO_SBX_1G_202505_ES_b086.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: contradiccion:producto-real-sin-mencion-estricta-ni-en-mayusculas; juez:propone-otra-grafia(N-IO-SBX-1G)
      el juez propone otra grafía: `N-IO-SBX-1G`
- [ ] `kidde:zlsm-me-zlsm-mr` (ZLSM-ME/ZLSM-MR)
      ↳ **s324:** ✅ RESUELTO por R7: ZLSM-ME/ZLSM-MR no aparecen como token en sus docs → no se da de alta
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «DS_KIDDE_ZLSM_ME_202604_ES_c3d9.pdf»
      doc `DS_KIDDE_ZLSM_ME_202604_ES_c3d9.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo
      el juez propone otra grafía: `9-30520`
- [ ] `kidde:zlsm-me-zlsm-mr` (ZLSM-ME/ZLSM-MR)
      ↳ **s324:** ✅ RESUELTO por R7: ZLSM-ME/ZLSM-MR no aparecen como token en sus docs → no se da de alta
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «MI_KIDDE_ZLSM_ME_202604_ING_29a1.pdf»
      doc `MI_KIDDE_ZLSM_ME_202604_ING_29a1.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo
      el juez propone otra grafía: `MiniLaser Expansion Housing`
- [ ] `morley:efs-em-8` (EFS/EM 8)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Panel de control de incendios de 8 zonas EFS/EM 8 # Manual de instalación, puesta en…»
      doc `MS8.pdf` · estrictas doc 9 / global 18 en 2 docs · otros motivos: ambiguedad:mismo-termino-propuesto-a-dos-fabricantes
- [ ] `notifier:conv232-485` (CONV232/485)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol REFERENCIA_COMERCIAL · confianza alta · cita ✓ «Convertidor RS232 a RS485/422 para TG a centrales ID3000 - punto a punto. Ref.: CONV…»
      doc `TIDT110.pdf` · estrictas doc 3 / global 4 en 2 docs
- [ ] `notifier:efs-em-8` (EFS/EM 8)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Panel de control de incendios de 8 zonas EFS/EM 8 # Manual de instalación, puesta en…»
      doc `FS8` · estrictas doc 9 / global 18 en 2 docs · otros motivos: ambiguedad:mismo-termino-propuesto-a-dos-fabricantes
- [ ] `notifier:nx2-r-r-y-nx5-r-r` (NX2/R/R y NX5/R/R)
      ↳ **s324:** ⏳ PENDIENTE DE TI — NX2/R/R y NX5/R/R: nombre con barra, 1 sola mención en tabla (dúo r32): ¿alta?
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «| 1 | → | (−) | NX2/R/R y NX5/R/R»
      doc `EMA24RS2R_NX2y5-R-R` · estrictas doc 1 / global 1 en 1 doc · otros motivos: juez:confianza-media; juez:propone-otra-grafia(NX2/R/R; NX5/R/R)
      el juez propone otra grafía: `NX2/R/R; NX5/R/R`
- [ ] `notifier:pul-d-ext` (PUL-D/EXT)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol REFERENCIA_COMERCIAL · confianza media · cita ✗ «PUL-D/EXT 1035 [CE mark logo] Honeywell Life Safety Iberia, SL.»
      doc `PUL-DEXT_Instrucciones multi` · estrictas doc 1 / global 1 en 1 doc · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo
- [ ] `notifier:pul-p-ext` (PUL-P/EXT)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol REFERENCIA_COMERCIAL · confianza alta · cita ✓ «PUL-P/EXT** 1035 CE Honeywell Life Safety Iberia, SL.»
      doc `PUL-PEXT_Instrucciones multi` · estrictas doc 1 / global 1 en 1 doc
- [ ] `sensitron:sts-ckd` (STS/CKD+)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Manual de instrucciones # STS/CKD+»
      doc `MT4508-CKDPLUS REV 0.pdf` · estrictas doc 1 / global 4 en 4 docs
- [ ] `spectrex:20-20mi` (20/20MI)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «CONFIGURACIÓN DEL DETECTOR DE LLAMA 20/20MI»
      doc `MADT696_01` · estrictas doc 5 / global 50 en 3 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `spectrex:20-20r` (20/20R)
      ↳ **s324:** ⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «DETECTOR DE LLAMA DE UN ÚNICO ESPECTRO INFRARROJO ## Modelo «20/20R»»
      doc `MNDT713.pdf` · estrictas doc 2 / global 5 en 2 docs

**riesgo-lexico:acronimo-corto-sin-digitos** — 17

- [ ] `morley:miw` (MIW)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Serie MIW Equipos Vía Radio Analógicos»
      doc `MIW-al-sustituir-las-baterias-de-un-equipo-se…` · estrictas doc 1 / global 70 en 11 docs
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# ACTUALIZACIÓN DE HISTÓRICO DEL TG El programa ActualizaHis.exe es el encargado de…»
      doc `Actulización histórico TG` · estrictas doc 9 / global 164 en 18 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# TG - He cambiado el nombre del plano y ahora el plano y los equipos han desapareci…»
      doc `Al cambiar-el-nombre-del-plano-a desaparecido…` · estrictas doc 6 / global 87 en 11 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «¿Como solucionar la incidencia *"TABLE IS FULL"* en el software gráfico *TG*?»
      doc `Como-solucionar-la-incidencia-TABLE-IS-FULL-e…` · estrictas doc 5 / global 76 en 14 docs
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «Poner la contraseña por defecto del programa de gestión gráfica TG»
      doc `Poner-la-contraseña-por-defecto-del-programa-…` · estrictas doc 4 / global 90 en 3 docs · otros motivos: juez:confianza-media; sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Puedo migrar / actualizar un TG versión 5.XX a versión 7.XX»
      doc `Requisitos-del-PC-para-el-TG-Version-5-XX.pdf` · estrictas doc 3 / global 96 en 4 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «el programa gráfico TG funciona en modo EDITOR y no habrá comunicación con las centr…»
      doc `TG-ATENCION-El-sistema-no-encuentra-la-protec…` · estrictas doc 6 / global 23 en 9 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «¿Como ampliar una/as licencia/s de un TG?»
      doc `TG-Como ampliar-licencias.pdf` · estrictas doc 8 / global 93 en 2 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Acceda al programa TG con una clave que le permita alcanzar al menú de **Configuraci…»
      doc `TG-Como-borrar-elementos-de-un-plano.pdf` · estrictas doc 3 / global 162 en 11 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Después de instalar el programa gráfico (en adelante TG) debe proceder a la generaci…»
      doc `TG-Como-cargar-añadir-planos.pdf` · estrictas doc 9 / global 115 en 4 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «¿Como se debe de hacer una copia de seguridad del proyecto para la versión 7 del TG?»
      doc `TG-Como-hacer-una-copia-de-seguridad-del-proy…` · estrictas doc 7 / global 148 en 20 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Puede realizar estas indicaciones con el TG arrancado, tanto en Modo Editor como en…»
      doc `TG-Como-puedo-ver-los-equipos-que-no-estan-re…` · estrictas doc 3 / global 109 en 14 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «debe acceder a la utilidad que acompaña al software gráfico TG»
      doc `TG-Como-reparar-Historico-Provisional.pdf` · estrictas doc 12 / global 85 en 12 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Cierre el programa gráfico **TG**»
      doc `TG-Que-clave-tiene-si-se-instala-en-idioma-In…` · estrictas doc 7 / global 120 en 9 docs
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# TG - SE HA SUPERADO EL MÁXIMO DE LICENCIAS.»
      doc `TG-SE-HA-SUPERADO-EL-MAXIMO-DE-LICENCIAS.pdf` · estrictas doc 9 / global 53 en 13 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✗ «Programa gráfico de gestión, tipo TG de Notifier»
      doc `TG-como-se-configuran-sonidos-ante-eventos.pdf` · estrictas doc 2 / global 92 en 6 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo; sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:vsn` (VSN)
      ↳ **s324:** ⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza media · cita ✗ «VSN-RP1R-PLUS2, VSN-Plus y VSN-2PLUS»
      doc `No-funcionan-las-teclas-de-la-central-VSN.pdf` · estrictas doc 2 / global 119 en 19 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo; contradiccion:artefacto-con-fuerte-senal-de-sujeto

**juez:confianza-media** — 14

- [ ] `aritech:2x-a-tactil` (2X-A Táctil)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «quick installation information for your 2X-A control panel»
      doc `00-3280-507-4003-03_r003_2x-a_series_quick_in…` · estrictas doc 0 / global 0 en 0 docs · otros motivos: atencion:etiqueta-270-chunks-sin-aparecer-verbatim
      el juez propone otra grafía: `2X-A`
- [ ] `kidde:kit-2x-afr-c-09` (KIT 2X-AFR-C-09)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «KIDDE™ COMMERCIAL # 2X-AFR-C ## Repetidor de incendios direccionable - Compacto»
      doc `DS_KIDDE_KIT_2X_AFR_C_09_202412_ES_c976.pdf` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `2X-AFR-C`
- [ ] `kidde:zlsm-md` (ZLSM-MD)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «## Kidde MiniLaser»
      doc `DS_KIDDE_ZLSM_MD_202604_ES_8d42.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: atencion:etiqueta-87-chunks-sin-aparecer-verbatim
      el juez propone otra grafía: `MiniLaser`
- [ ] `kidde:zlsm-md` (ZLSM-MD)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «MI_KIDDE_ZLSM_MD_202604_ING_1875.pdf»
      doc `MI_KIDDE_ZLSM_MD_202604_ING_1875.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: cita:no-verificada-a-texto-completo; atencion:etiqueta-87-chunks-sin-aparecer-verbatim
      el juez propone otra grafía: `MiniLaser`
- [ ] `kidde:zlsm-mr` (ZLSM-MR)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «MI_KIDDE_ZLSM_MR_202604_ING_252a.pdf»
      doc `MI_KIDDE_ZLSM_MR_202604_ING_252a.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: cita:no-verificada-a-texto-completo; ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `MiniLaser I/O Functional Module`
- [ ] `morley:fl-20` (FL-20)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «La serie LT MI-FL20 forma parte de la familia Fire Alarm Aspiration Sensing Technolo…»
      doc `I56-3956-201_PT Morley Loop FAAST LT QIG.pdf` · estrictas doc 0 / global 0 en 3 docs
      el juez propone otra grafía: `FAAST LT (serie FL20)`
- [ ] `morley:morley-ias-max` (Morley-IAS Max)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «Documentación Morley-IAS Max https://buildings.honeywell.com/gb/en/lp/morleymaxtech»
      doc `Docs Morley-IAS Max - QR` · estrictas doc 1 / global 1 en 1 doc
- [ ] `notifier:hssd` (HSSD)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza media · cita ✓ «Los **detectores HSSD** deben montarse fuera de la cámara frigorífica»
      doc `MADT731_01` · estrictas doc 18 / global 70 en 3 docs · otros motivos: contradiccion:artefacto-con-fuerte-senal-de-sujeto
- [ ] `notifier:madt-606` (MADT-606)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol CODIGO_DE_DOCUMENTO · confianza media · cita ✗ «Documento de origen: MADT606»
      doc `MADT606` · estrictas doc 0 / global 0 en 0 docs · otros motivos: cita:no-verificada-a-texto-completo
- [ ] `notifier:nfs-32-001` (NFS-32-001)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «D1056-1_NFXI-BS-BSF»
      doc `D1056-1_NFXI-BS-BSF` · estrictas doc 0 / global 0 en 0 docs · otros motivos: cita:no-verificada-a-texto-completo; ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `NFXI-BS-BSF`
- [ ] `notifier:repetidor-serie-1000` (REPETIDOR SERIE 1000)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «# Repetidor de la Serie 1000 Fire alarm control panel»
      doc `MNDT213.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: contradiccion:producto-real-sin-mencion-estricta-ni-en-mayusculas; juez:propone-otra-grafia(Repetidor de la Serie 1000)
      el juez propone otra grafía: `Repetidor de la Serie 1000`
- [ ] `notifier:securnet-plus-02` (SECURNET PLUS 02)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol CODIGO_DE_DOCUMENTO · confianza media · cita ✓ «**ADEMDUM** | SECURNET PLUS 02<br/>Fecha: 19 / 03 / 2001»
      doc `MADT575_02` · estrictas doc 1 / global 1 en 1 doc
      el juez propone otra grafía: `SECURNET PLUS`
- [ ] `spectrex:40-40l` (40-40L)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «Modelo S40/40L, LB y S40/40L4, L4B»
      doc `MNDT722_40-40L` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:propone-otra-grafia(S40/40L)
      el juez propone otra grafía: `S40/40L`
- [ ] `xtralis:vesda` (VESDA)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza media · cita ✗ «La Pantalla de reconocimiento inmediato del detector VESDA VLF muestra los niveles d…»
      doc `HSLI_IN_020_Tabla equivalencia TG` · estrictas doc 3 / global 91 en 7 docs · otros motivos: cita:no-verificada-a-texto-completo; contradiccion:artefacto-con-fuerte-senal-de-sujeto
      el juez propone otra grafía: `VESDA-VLF/VLF-250 (y otros modelos de la gama VESDA)`

**obsoleta:doc-fuente-no-activo** — 7

- [ ] `notifier:ir3-s20` (IR³ S20)
      ↳ **s324:** ✅ RESUELTO por R6 (fuente retirada → no se da de alta): no decides nada
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza baja · cita ✗ sin cita en el recibo
      doc `MNDT694` · estrictas doc 0 / global 0 en 0 docs · otros motivos: obsoleta:el-doc-ya-no-declara-ese-product_model; juez:confianza-baja; cita:no-verificada-a-texto-completo
      el juez propone otra grafía: `S20/20SI`
- [ ] `notifier:smart-twin` (SMART TWIN)
      ↳ **s324:** ✅ RESUELTO por R6 (fuente retirada → no se da de alta): no decides nada
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «INSTRUCCIÓN TÉCNICA PARA LOS DETECTORES SMART TWIN»
      doc `MNDT606` · estrictas doc 0 / global 1 en 1 doc
- [ ] `notifier:spectrex` (SPECTREX)
      ↳ **s324:** ✅ RESUELTO por R6 (fuente retirada → no se da de alta): no decides nada
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza alta · cita ✓ «SPECTREX INC. ofrece una garantía al Comprador/Distribuidor sobre los componentes su…»
      doc `MNDT690` · estrictas doc 0 / global 145 en 13 docs · otros motivos: obsoleta:el-doc-ya-no-declara-ese-product_model; contradiccion:artefacto-con-fuerte-senal-de-sujeto
- [ ] `notifier:tg-notifier` (TG-NOTIFIER)
      ↳ **s324:** ✅ RESUELTO por R6 (fuente retirada → no se da de alta): no decides nada
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «TG NOTIFIER VER. 3.2 NOTIFIER ESPAÑA presenta una nueva versión de su programa de gr…»
      doc `MNDT951_v5-87` · estrictas doc 0 / global 42 en 13 docs · otros motivos: obsoleta:el-doc-ya-no-declara-ese-product_model; colision:id-ya-existe-en-el-catalogo-gobernado
- [ ] `spectrex:20-20i` (20/20I)
      ↳ **s324:** ✅ RESUELTO por R6 (fuente retirada → no se da de alta): no decides nada
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «El Modelo 20/20I de Spectrex es un detector de llama de triple espectro infrarrojo d…»
      doc `MNDT700_C` · estrictas doc 0 / global 9 en 4 docs · otros motivos: ambiguedad:termino-multi-modelo; fabricante:discrepa-de-la-ficha-del-documento
- [ ] `spectrex:20-20lb` (20/20LB)
      ↳ **s324:** ✅ RESUELTO por R6 (fuente retirada → no se da de alta): no decides nada
      **PRODUCTO_REAL** · rol TABLA_DE_MODELOS · confianza alta · cita ✓ «el modelo 20/20LB incluye la opción de Prueba Incorporada (BIT), mientras que el 20/…»
      doc `MNDT720` · estrictas doc 0 / global 13 en 3 docs · otros motivos: obsoleta:el-doc-ya-no-declara-ese-product_model; ambiguedad:termino-multi-modelo; fabricante:discrepa-de-la-ficha-del-documento
- [ ] `spectrex:20-20ub` (20/20UB)
      ↳ **s324:** ✅ RESUELTO por R6 (fuente retirada → no se da de alta): no decides nada
      **PRODUCTO_REAL** · rol REFERENCIA_COMERCIAL · confianza alta · cita ✓ «La diferencia entre el modelo 20/20U y 20/20UB es que el Modelo 20/20UB incluye una…»
      doc `MNDT710_B` · estrictas doc 0 / global 12 en 1 doc · otros motivos: obsoleta:el-doc-ya-no-declara-ese-product_model; ambiguedad:termino-multi-modelo; fabricante:discrepa-de-la-ficha-del-documento

**ambiguedad:mismo-id-con-grafias-distintas-en-el-draft** — 4

- [ ] `notifier:airsense` (AIRSENSE)
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza alta · cita ✓ «**AirSense** TECHNOLOGY LTD»
      doc `MADT731_04` · estrictas doc 3 / global 40 en 11 docs · otros motivos: contradiccion:artefacto-con-fuerte-senal-de-sujeto
- [ ] `notifier:airsense` (Airsense)
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza alta · cita ✓ «© Copyright 1996-2002 AirSense Technology Ltd»
      doc `TIDT109.pdf` · estrictas doc 2 / global 40 en 14 docs · otros motivos: contradiccion:artefacto-con-fuerte-senal-de-sujeto
- [ ] `notifier:faast-lt` (FAAST LT)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «## Accesorios de «FAAST LT» A continuación se facilita información sobre los accesor…»
      doc `ASD Cold Environments_SP` · estrictas doc 6 / global 122 en 6 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `notifier:faast-lt` (FAAST-LT)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «QUICK INSTALLATION GUIDE ADDRESSABLE FAAST LT MODELS NFXI-ASD11, NFXI-ASD12, NFXI-AS…»
      doc `FAAST-LT-Como-obtener-el-historico-del-equipo…` · estrictas doc 0 / global 0 en 8 docs
      el juez propone otra grafía: `FAAST LT`

**ambiguedad:mismo-termino-propuesto-a-dos-fabricantes** — 2

- [ ] `notifier:lt-200` (LT-200)
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✗ «FAAST LT-200 MODELOS DIRECCIONABLES»
      doc `FAAST-LT-Como-comunicar-con-el-equipo.pdf` · estrictas doc 2 / global 135 en 6 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo; juez:propone-otra-grafia(FAAST LT-200)
      el juez propone otra grafía: `FAAST LT-200`
- [ ] `xtralis:lt-200` (LT-200)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# FAAST LT-200 ## FIRE ALARM ASPIRATION SENSING TECHNOLOGY® ## ADVANCED SET-UP AND C…»
      doc `I56-3888-010 FAAST LT-200 Adv Guide` · estrictas doc 95 / global 69 en 8 docs · otros motivos: juez:propone-otra-grafia(FAAST LT-200)
      el juez propone otra grafía: `FAAST LT-200`

**ambiguedad:veredictos-discordantes-para-el-mismo-id** — 2

- [ ] `kidde:ke-dba-sktw` (KE-DBA-SKTW)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «KIDDE COMMERCIAL # KE-DBA-SKTW **Intelligent addressable base accessory - trim skirt…»
      doc `HD_KE_DBA_SKTW_202407_ING_2da9.pdf` · estrictas doc 4 / global 8 en 3 docs
- [ ] `notifier:nfs-32-001` (NFS-32-001)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **NORMA_O_CERTIFICACION** · rol FRASE_TECNICA · confianza alta · cita ✓ «French Fire Sound AFNOR<br/>NFS 32-001»
      doc `D838-1_kac sounders` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `NF S 32-001`

**atencion:etiqueta-270-chunks-sin-aparecer-verbatim** — 2

- [ ] `aritech:2x-a-tactil` (2X-A Táctil)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «This document lists the products compatible for use with your 2X-A Series fire alarm…»
      doc `bcn-3100035-en_r006_2x-a_series_addressable_c…` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `2X-A Series`
- [ ] `aritech:2x-a-tactil` (2X-A Táctil)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «2X-A and ZP2-A Series Addressable Control Panel Compatibility List (900 Series Proto…»
      doc `bcn-3100036-en_r002_2x-a_and_zp2-a_series_add…` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `2X-A`

**colision:el-texto-ya-es-alias-de-otro-producto** — 2

- [ ] `notifier:stratos-hssd` (STRATOS HSSD)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «*STRATOS* HSSD® # DETECTOR DE HUMO DE # ALTA SENSIBILIDAD»
      doc `MNDT730.pdf` · estrictas doc 0 / global 0 en 4 docs
      el juez propone otra grafía: `Stratos-HSSD`
      ALBERTO: modelo que propone el juez
- [ ] `notifier:stratos-hssd` (STRATOS HSSD)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Central SENSENET (Stratos-HSSD)»
      doc `MNDT730P.pdf` · estrictas doc 0 / global 0 en 4 docs
      el juez propone otra grafía: `Stratos-HSSD`
      ALBERTO: versión portuguesa, retirar doc.

**contradiccion:artefacto-con-fuerte-senal-de-sujeto** — 2

- [ ] `morley:mie-ma-100` (MIE-MA-100)
      **ARTEFACTO_EXTRACCION** · rol CODIGO_DE_DOCUMENTO · confianza alta · cita ✓ «MIE-MA-100_01_C 27/07/04 Morley-IAS ESPAÑA 1 de 4»
      doc `MIE-MA-100_01.pdf` · estrictas doc 4 / global 8 en 2 docs
- [ ] `xtralis:vesda` (VESDA)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza alta · cita ✓ «Instalación y programación del sistema de aspiración Vesda»
      doc `Cursos formacion_Marzo 2026.pdf` · estrictas doc 8 / global 88 en 11 docs

**juez:propone-otra-grafia(2010-2A-PAK-HPL)** — 2

- [ ] `kidde:2a-pak-hpl` (2A-PAK-HPL)
      **PRODUCTO_REAL** · rol TABLA_DE_MODELOS · confianza alta · cita ✓ «| 2010-2A-PAK-HPL | Enables the high powered loop»
      doc `DS_KIDDE_2A_PAK_HPL_9085.pdf` · estrictas doc 2 / global 59 en 8 docs
      el juez propone otra grafía: `2010-2A-PAK-HPL`
- [ ] `kidde:2a-pak-hpl` (2A-PAK-HPL)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «2010-2A-PAK-HPL Panel Activation Key Registration Guide»
      doc `MI_KIDDE_2A_PAK_HPL_c599.pdf` · estrictas doc 19 / global 60 en 8 docs
      el juez propone otra grafía: `2010-2A-PAK-HPL`

**juez:veredicto-no-bloqueable(ACCESORIO_DE_OTRO)** — 2

- [ ] `kidde:ke-dba-sktw` (KE-DBA-SKTW)
      **ACCESORIO_DE_OTRO** · rol TITULO · confianza alta · cita ✓ «KE-DBA-SKTW Trim Skirt Accessory for Standard Mounting Base Installation Sheet»
      doc `MI_KE_DBA_SKTW_202407_ES_a20b.pdf` · estrictas doc 3 / global 8 en 3 docs · otros motivos: ambiguedad:veredictos-discordantes-para-el-mismo-id
      producto padre propuesto: `KE-DB3010W`
- [ ] `spectrex:40-40-air` (40-40-AIR)
      **ACCESORIO_DE_OTRO** · rol TITULO · confianza alta · cita ✓ «hield, developed for SharpEye 40/40 series optical flame detectors, allows detector…»
      doc `guide-40-40-air-shield-p-n-777650-spectrex-en…` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `40/40 Air Shield (P/N 777650)`
      producto padre propuesto: `SharpEye 40/40 series (detectores ópticos de llama Spectrex)`

**(sin motivo declarado en el recibo)** — 1

- [ ] `notifier:serie-ps` (Serie PS)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# 1. INSTALACIÓN DE LAS FUENTES DE ALIMENTACIÓN DE LA SERIE PS»
      doc `Serie PS.pdf` · estrictas doc 1 / global 6 en 2 docs

**colision:id-ya-existe-en-el-catalogo-gobernado** — 1

- [ ] `notifier:id1000` (ID1000)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# CENTRAL DE ALARMA CONTRA INCENDIOS SERIE ID1000»
      doc `TIDT066_copia.pdf` · estrictas doc 3 / global 60 en 10 docs

**juez:propone-otra-grafia(S40/40I)** — 1

- [ ] `spectrex:40-40i` (40-40I)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Modelo S40/40I»
      doc `MNDT721_40-40I` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `S40/40I`

**juez:veredicto-no-bloqueable(NO_DECIDIBLE)** — 1

- [ ] `kidde:zlsm-mr` (ZLSM-MR)
      ↳ **s324:** ⏳ confianza media: pendiente de re-juicio K=5 o de tu sí
      **NO_DECIDIBLE** · rol NO_APARECE · confianza media · cita ✓ «AIRSENSE # 9-30521 **Módulo funcional de entrada/salida MiniLaser**»
      doc `DS_KIDDE_ZLSM_MR_202604_ES_6a09.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media; ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `9-30521`

**sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo** — 1

- [ ] `kidde:ke-dp3121b` (KE-DP3121B)
      ↳ **s324:** ✅ ALTA aplicada (R4) · cita verificada en HD_KE_DP3121B_202407_ES_8c51.pdf
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «KIDDE COMMERCIAL # KE-DP3121B **Detector de calor/óptico dual direccionable intelige…»
      doc `HD_KE_DP3121B_202407_ES_8c51.pdf` · estrictas doc 2 / global 26 en 7 docs

### §1.C — `product_model` sucio, residuo (1)

- [ ] `997-493-002-2` · pm actual «EN54 2-8 Zone» · Notifier · 27 chunks
      veredicto **NO_DECIDIBLE** · confianza media · cita ✓ «This manual contains operating instructions for the EN54, 2 - 8 zone conventional fire control panel.»
      razón: El documento nunca imprime un modelo comercial: solo se autodescribe como 'EN54 2-8 Zone Conventional Fire Control Panel', donde EN54 es la norma y '2-8 zone' una descripción funcional, no un modelo. El censo regex no extrajo can…
      muestra: documento COMPLETO, 40892 chars, 27 chunks · candidatos impresos: ninguno
      **la pregunta que hay que responder**: ¿Confirma el catálogo gobernado (o el PDF original con portada/contraportada completa) que el panel convencional 2-8 zonas de Notifier con código de documento 997-493 es el NFS 2-8, y debería adjudicarse igual a los hermanos _1 y _2?
      propuesta si no se decide: NADA que aplicar; el valor actual se conserva.

---

## SECCIÓN 2 — Ya no aplican (12) — **no decides nada**

Filas del packet v1 que el refresco contra el estado de HOY dejó sin objeto.
Se listan para que conste que NO se han perdido, no para adjudicar.

**obsoleta (3)** — el documento ya no está activo (status=superseded): su doc_map dejó de ser una pregunta viva

- `mi_kidde_ke_dp312x_snx_202503_es_acf9` (Kidde · 45 chunks)
- `mndt420` (Notifier · 85 chunks)
- `pl4_mt574e_eng` (Sensitron · 24 chunks)

**se_disuelve_con_e1_seccion1 (9)** — ya existe entrada de doc_map para el MISMO source_file bajo otro document_id: es la clase COLISIÓN de §1 — al repuntar §1, este documento hereda la entrada y la pregunta de §2 desaparece

- `33976_13_vesda-e_vep-a00-p_product_guide_a4_spanish_lores` (Xtralis · 120 chunks)
- `mndt500` (Notifier · 51 chunks)
- `mndt503` (Notifier · 46 chunks)
- `mndt506` (Notifier · 53 chunks)
- `mndt515` (Notifier · 29 chunks)
- `mndt615` (Notifier · 7 chunks)
- `rp1r - man ita r.a2` (Notifier · 3 chunks)
- `tg-1020-tec` (Notifier · 63 chunks)
- `tg-1020-usu` (Notifier · 54 chunks)

---

## Recibos (la traza completa, fila a fila)

- `evals/s322f_e1_colisiones_adjudicacion_v1.json` — 49 filas (49 bloque / 0 individual)
- `evals/s322f_e1s2_tierb_docmap_v1.json` — 67 filas (42 bloque / 13 individual)
- `evals/s322g_e1_candidatos_triage_v1.json` — 133 filas (50 bloque / 83 individual)
- `evals/s322g_e1_pm_sucio_v1.json` — 4 filas (3 bloque / 1 individual)
- Ensamblado por `scripts/s322_packets_v2.py` (determinista, sin LLM) el 20260815T163607Z.

## Auto-verificación del encabezado

Filas declaradas arriba vs filas REALMENTE escritas en este fichero:

- **SECCIÓN 0**: declaradas 143 · escritas 143 · casillas 143 — ✓
- **SECCIÓN 1**: declaradas 98 · escritas 98 · casillas 98 — ✓
- **SECCIÓN 2**: declaradas 12 · escritas 12 · casillas 0 — ✓
- **TOTAL**: 253 = 143 + 98 + 12 ✓ (cuadra con las 253 casillas de la v1)
