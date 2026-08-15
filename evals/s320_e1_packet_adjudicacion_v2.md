# s320 E1 — Packet de ADJUDICACIÓN **v2 (encogido)** · 20260815T163607Z

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

### §0.A — Colisiones de identidad: **repuntar `doc_map`** (49)

Las 49 son la MISMA clase: `fantasma_ya_retirado`. La fila del mapa apunta a un `document_id`
**retirado y con CERO filas** en `chunks_v2`/`chunks`/`enunciados`/`visual_assets`/
`group_members`, su `sha` es pseudo-backfill y su nota apunta al id vivo: es una ficha
fantasma de s65, no un duplicado real. **No hay supersede que hacer** (una ficha de 0
chunks nunca fue una revisión) y **`documents` no se toca**.

- Impacto MEDIDO (no teorizado): la atestación del anexo `must_preserve` (join por
  `document_id`) **falla hoy en 49 docs** con el id servido y **atestaría con el id
  fantasma en 49**. `allowed_sources`: INTACTO — catalog_resolver indexa por source_file y el del doc_map coincide exactamente con el de los chunks del activo en las 49
- Entradas del catálogo afectadas: **191**.
- Acción por fila: `doc_map` → repuntar `document_id` (mapa → actual). `source_file` intacto.

**Los 9 gates dan lo mismo en las 49 filas** (comprobado al ensamblar, no supuesto),
así que se declaran UNA vez en vez de repetirlos en cada línea:

  - `actual_sirve_chunks_v2` = **True**
  - `actual_status` = **active**
  - `doc_map_source_file_coincide_con_chunks_del_actual` = **True**
  - `id_mapa_en_otros_ficheros_del_catalogo` = **False**
  - `mapa_sin_filas_en_ninguna_satelite` = **True**
  - `mapa_status` = **retired**
  - `mismo_blob_por_nombre` = **True**
  - `nota_apunta_al_actual` = **True**
  - `sha_mapa_es_pseudo_backfill` = **True**
  - seam medible en las 49: atesta con el id **fantasma**=True, con el id
    **servido**=False → repuntar arregla la atestación.

Lo único que cambia por fila es el par de ids y la sonda que lo demuestra:

**tier_a (16)**

- [ ] `mndt150` · 16 entradas · mapa 3e7328bf… → actual d917a95d… · sonda `notifier:id-200`
- [ ] `mndt250` · 4 entradas · mapa 309b9f8a… → actual ee4a01b8… · sonda `notifier:am-6000`
- [ ] `mndt255` · 1 entrada · mapa 8595c7c4… → actual afacdf35… · sonda `notifier:lcd-6000`
- [ ] `mndt260` · 2 entradas · mapa cf07a74d… → actual 446da5f5… · sonda `notifier:am-2000`
- [ ] `mndt390` · 1 entrada · mapa 609f0e11… → actual 49a08cd1… · sonda `notifier:udact`
- [ ] `mndt440` · 1 entrada · mapa 351ff649… → actual 79869dab… · sonda `notifier:nib-96`
- [ ] `mndt530p` · 5 entradas · mapa a3845c17… → actual 754f1b80… · sonda `notifier:park-2000`
- [ ] `mndt744i_b` · 1 entrada · mapa 80789d8b… → actual 7cb57a84… · sonda `notifier:nas-1u`
- [ ] `mndt960i` · 1 entrada · mapa 18429c41… → actual c295d7f9… · sonda `notifier:pol-1`
- [ ] `mpdt170` · 2 entradas · mapa 890d5cf6… → actual 80b23534… · sonda `notifier:afp-300`
- [ ] `mpdt230` · 2 entradas · mapa 6d46b4a2… → actual 3e4bd0bb… · sonda `notifier:afp4000`
- [ ] `mpdt281` · 2 entradas · mapa 3a7e439f… → actual 932ac246… · sonda `notifier:afp1010`
- [ ] `nco-10-multinglingual` · 1 entrada · mapa b7cb94d1… → actual c2ae8cae… · sonda `notifier:nco-10`
- [ ] `smart 2_mt251_ita-eng` · 2 entradas · mapa 2f3536bc… → actual 0d4e7b1a… · sonda `sensitron:smart-2`
- [ ] `tidt104` · 1 entrada · mapa c39c0456… → actual 2c8e62dd… · sonda `unresolved:id3000`
- [ ] `tidt108` · 1 entrada · mapa 3737c7f5… → actual 2b925c7b… · sonda `unresolved:id3000`

**tier_b (9)**

- [ ] `33976_13_vesda-e_vep-a00-p_product_guide_a4_spanish_lores` · 3 entradas · mapa 23ff1fcf… → actual b22fdb7f… · sonda `xtralis:vep-a00-1p`
- [ ] `mndt500` · 6 entradas · mapa 643e3377… → actual 90787236… · sonda `notifier:g-500-s-32`
- [ ] `mndt503` · 5 entradas · mapa 9ccb9c98… → actual acf63276… · sonda `notifier:g-100-4`
- [ ] `mndt506` · 6 entradas · mapa 1cd40961… → actual f2a27fb6… · sonda `notifier:g-100-r-12`
- [ ] `mndt515` · 3 entradas · mapa b6169b43… → actual bfb0fed7… · sonda `notifier:pl4`
- [ ] `mndt615` · 1 entrada · mapa 700af1a7… → actual c4f3d893… · sonda `notifier:smart-2`
- [ ] `rp1r - man ita r.a2` · 1 entrada · mapa 6972bec7… → actual 03cf3cca… · sonda `notifier:rp1r`
- [ ] `tg-1020-tec` · 1 entrada · mapa 4682b6f7… → actual 288e3202… · sonda `unresolved:tg-1020`
- [ ] `tg-1020-usu` · 1 entrada · mapa abb55e52… → actual 2ad4e69f… · sonda `unresolved:tg-1020`

**tier_c (24)**

- [ ] `mndt1300_e` · 2 entradas · mapa 7268b1ad… → actual d61cc3d7… · sonda `notifier:ps3`
- [ ] `mndt1300i_e` · 2 entradas · mapa a05f27f7… → actual a9a45a96… · sonda `notifier:ps3`
- [ ] `mndt350` · 23 entradas · mapa 0b90a14c… → actual 2d7f3a79… · sonda `notifier:transponder-serie-xp`
- [ ] `mndt400` · 4 entradas · mapa 996551c8… → actual c604426a… · sonda `notifier:lcd-80`
- [ ] `mndt402` · 1 entrada · mapa 83763f33… → actual 3a58b47d… · sonda `notifier:lcd-80tm`
- [ ] `mndt410` · 15 entradas · mapa 65a37e17… → actual 5403c7ed… · sonda `notifier:acm-16at`
- [ ] `mndt520` · 4 entradas · mapa 621aa70f… → actual 3493f571… · sonda `notifier:g-mtslb1`
- [ ] `mndt575` · 1 entrada · mapa 7e554fdb… → actual 6c784967… · sonda `notifier:securnet-plus`
- [ ] `mndt605` · 4 entradas · mapa 12d9af3e… → actual c54c20a4… · sonda `notifier:ga-500-ep`
- [ ] `mndt607` · 1 entrada · mapa 9c69590f… → actual f478ca19… · sonda `notifier:smart-1`
- [ ] `mndt625` · 2 entradas · mapa a798da74… → actual 7601da55… · sonda `notifier:smart-3-cc`
- [ ] `mndt626` · 15 entradas · mapa 25b925bd… → actual 0ef10ac7… · sonda `notifier:s2138sd`
- [ ] `mndt635` · 2 entradas · mapa 89b21f27… → actual 359934f9… · sonda `notifier:lisa-2-eex-d`
- [ ] `mndt646_smart3g toxic_sp-en` · 16 entradas · mapa 43436831… → actual eb4f831e… · sonda `notifier:s2138sd`
- [ ] `mndt650` · 3 entradas · mapa c84ca057… → actual be99c95b… · sonda `notifier:smart-2`
- [ ] `mndt655` · 4 entradas · mapa 537879d2… → actual 12278b1f… · sonda `notifier:catalix-12`
- [ ] `mndt741` · 1 entrada · mapa 2fc17b63… → actual 53dc8e94… · sonda `notifier:nas`
- [ ] `mndt742p_f` · 1 entrada · mapa 9c595e46… → actual 16aa7584… · sonda `notifier:nas-2`
- [ ] `mndt951i_v7-1` · 1 entrada · mapa 0beb5d94… → actual 9600e30e… · sonda `notifier:tg-notifier`
- [ ] `mndt954` · 1 entrada · mapa 48a64d46… → actual a8bb21cf… · sonda `notifier:tg-6000`
- [ ] `mpdt212` · 6 entradas · mapa 3413c8ee… → actual ef245515… · sonda `notifier:id1002`
- [ ] `mpdt280` · 9 entradas · mapa 228a47c5… → actual e6ccaa2e… · sonda `notifier:afp1010`
- [ ] `mpdt951_v5-87` · 1 entrada · mapa 7c2bdff2… → actual 0903db56… · sonda `notifier:tg-notifier`
- [ ] `pan_avd1` · 2 entradas · mapa bb36bddd… → actual 7966c099… · sonda `notifier:pan-avd1`

### §0.B — `doc_map` tier B: **altas de entrada** (42)

Docs cuyo `product_model` resolvía a varios ids y quedaba ambiguo. Gate de bloque
(los 7 se cumplen en las 42):
  1. la fila sigue viva tras el refresco contra el estado de hoy
  2. veredicto accionable (IDS_CORRECTOS|OTROS_IDS|MULTI) con ids != []
  3. confianza alta DESPUÉS de degradar por cita no verificada
  4. cita verificada a TEXTO COMPLETO del documento (espacios normalizados)
  5. todos los ids en el menú cerrado y consumibles (activo, no-candidate)
  6. ningún token del pm clasificado como «producto real que falta»
  7. acuerdo K=2 en veredicto y en conjunto de ids (sin temperature el muestreo no es determinista: una pasada no distingue convicción de azar)

Juez `claude-fable-5`. Veredictos del lote completo: IDS_CORRECTOS:alta=43, MULTI:media=4, MULTI:alta=4, OTROS_IDS:alta=2, IDS_CORRECTOS:media=1, OTROS_IDS:media=1

- [ ] `00-3280-508-4009-03_r003_2x-a_series_quick_operation_guide_es` (Aritech · 7 chunks · pm «2X-A/2X-AT-F2/2X-AT-F2-FB»)
      → **IDS_CORRECTOS** · `kidde:2x-at-f2`, `kidde:2x-at-f2-fb` · cita ✓ «Guía de funcionamiento rápido de la serie 2X-A»
      ⚑ OEM/reventa: documento de **Aritech**, ids bajo **kidde**
      tokens del pm sin id (familia/serie, no se dan de alta): `2X-A`
- [ ] `averia-de-resistencia-de-baterias-en-central-dxc` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «Tengo avería de resistencia de baterías en central DXc»
- [ ] `bcn-3100019-es_r002_nc_series_fire_alarm_control_panel_quick_installation_guide` (Kidde · 8 chunks · pm «NC/NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4-SC/NC-PF8-SC»)
      → **IDS_CORRECTOS** · `kidde:nc-pf2`, `kidde:nc-pf4`, `kidde:nc-pf8`, `kidde:nc-pf2-sc`, `kidde:nc-pf4-sc`, `kidde:nc-pf8-sc` · cita ✓ «Guía de instalación rápida de las centrales de incendio convencionales de la Serie NC»
      tokens del pm sin id (familia/serie, no se dan de alta): `NC`
- [ ] `bcn-3100020-es_r002_nc_series_fire_alarm_control_panel_quick_operation_guide` (Kidde · 4 chunks · pm «NC/NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4-SC/NC-PF8-SC»)
      → **IDS_CORRECTOS** · `kidde:nc-pf2`, `kidde:nc-pf4`, `kidde:nc-pf8`, `kidde:nc-pf2-sc`, `kidde:nc-pf4-sc`, `kidde:nc-pf8-sc` · cita ✓ «Manual de funcionamiento rápido de las centrales de incendio convencionales de la Serie NC»
      tokens del pm sin id (familia/serie, no se dan de alta): `NC`
- [ ] `con-que-sistema-operativo-es-compatible-el-programa-de-la-dxc-connexion` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «¿Con que Sistema Operativo es compatible el programa de la DXc Connexión?»
- [ ] `ds_kidde_2x_at_fr_fb_s_202602_es_4276` (Aritech · 5 chunks · pm «2X-AT-FR-FB-S»)
      → **IDS_CORRECTOS** · `kidde:2x-at-fr-fb-s` · cita ✓ «# 2X-AT-FR-FB-S **Repetidor de central de incendios direccionable con pantalla táctil y controles de bomberos…»
      ⚑ OEM/reventa: documento de **Aritech**, ids bajo **kidde**
- [ ] `ds_kidde_2x_at_fr_s_202602_es_904a` (Aritech · 5 chunks · pm «2X-AT-FR-S»)
      → **IDS_CORRECTOS** · `kidde:2x-at-fr-s` · cita ✓ «# 2X-AT-FR-S **Repetidor de central de incendios direccionable con pantalla táctil, caja pequeña**»
      ⚑ OEM/reventa: documento de **Aritech**, ids bajo **kidde**
- [ ] `ds_kidde_2x_at_fr_s_98dc` (Aritech · 4 chunks · pm «2X-AT-FR-S»)
      → **IDS_CORRECTOS** · `kidde:2x-at-fr-s` · cita ✓ «KIDDE COMMERCIAL # 2X-AT-FR-S **Addressable fire panel repeater w touchscreen, small cabinet**»
      ⚑ OEM/reventa: documento de **Aritech**, ids bajo **kidde**
- [ ] `dxc-conexion-como-solucionar-la-averia-de-estado-inconsistente-anulado` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «# DXc/Conexion ¿Como solucionar la avería de Estado Inconsistente Anulado?»
- [ ] `dxc-configuracion-de-la-tarjeta-232-aislada-para-comunicarse-con-el-tg` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «Para que la central DXc, comunique con el TG, deberá activar el protocolo de comunicaciones en las opciones g…»
- [ ] `dxc-connexion-ajuste-contraste-display` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «# DXC / Connexion - Ajuste contraste display **Question** Ajuste contraste display DXc»
- [ ] `dxc-connexion-averia-f-alimentacion-externa` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «# DXC Connexion - Avería F. Alimentación externa **Question** La central DXC Connexión indica **"FALLO F.A. E…»
- [ ] `dxc-connexion-averia-nueva-f-alimentacion-externa` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «La central DXC Connexión indica "*NUEVA F.A. EXT.*"»
- [ ] `dxc-connexion-como-solucionar-la-averia-de-ent-placa-1-o-2` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «¿Como poder solucionar las averías de Entrada de Placa 1 o 2 en la DXc / Conexion?»
- [ ] `dxc-connexion-compatibilidad-de-programas-con-versiones` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «No todas las versiones del software de configuración **MK-DXC Configuration Tools** se pueden usar con cualqu…»
- [ ] `dxc-no-puedo-comunicar-con-la-central` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «Para comunicar con las centrales DXC Connexión necesita:»
- [ ] `dxc-opciones-de-disparo-de-programas-matrices` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «Las opciones de disparo de programas y sus funciones en la central DXc son:»
- [ ] `dxc-porque-al-activan-elementos-en-alarma-no-se-enciende-su-led` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «En la central DXC Connexión con el fin de aprovechar al máximo la corriente del lazo, solo **las cuatro prime…»
- [ ] `dxc-puedo-anular-la-clave-de-usuario-y-acceder-directamente-al-teclado` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «# DXC ¿Puedo anular la clave de usuario y acceder directamente al teclado?»
- [ ] `dxc-puedo-cambiar-la-clave-de-nivel-3` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «La clave de acceso a centrales Morley modelo DXc por defecto es **9898 y NO** puede ser modificada»
- [ ] `dxc-referencias-repuestos` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «# DXC - Referencias repuestos **Question** ¿Necesito saber la referencia de un determinado repuesto para la D…»
- [ ] `dxc-tipos-abreviaturas-de-equipos` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «Principales abreviaturas / tipos de equipos en la central DXc»
- [ ] `dxc-tipos-de-accion-para-entradas` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «Los tipos de acción para entradas y sus funciones para la central DXc son:»
- [ ] `dxc_connexion averia-de-resistencia-de-baterias` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «Tengo avería de resistencia de baterías en central DXc»
- [ ] `dxc_guia de usuario_multiling` (Morley · 6 chunks · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «Guía de usuario para centrales de detección de incendios de la serie DX Connexion»
- [ ] `eventos-averias-de-equipos-en-dxc` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «Eventos de equipos en la central DXc (NO RESPONDE, EQUIPO NUEVO, DOBLE DIRECCION, TIPO EQUIPO CAMBIADO)»
- [ ] `g_inst_kidde_nc_pfx_202502_es_ac3d` (Kidde · 9 chunks · pm «NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4-SC/NC-PF8-SC»)
      → **IDS_CORRECTOS** · `kidde:nc-pf2`, `kidde:nc-pf4`, `kidde:nc-pf8`, `kidde:nc-pf2-sc`, `kidde:nc-pf4-sc`, `kidde:nc-pf8-sc` · cita ✓ «Guía de instalación rápida de las centrales de incendio convencionales de la Serie NC»
- [ ] `g_uso_kidde_nc_pfx_202502_es_99d2` (Kidde · 4 chunks · pm «NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4-SC/NC-PF8-SC»)
      → **MULTI** · `kidde:nc-pf2`, `kidde:nc-pf4`, `kidde:nc-pf8`, `kidde:nc-pf2-sc`, `kidde:nc-pf4-sc`, `kidde:nc-pf8-sc` · cita ✓ «Manual de funcionamiento rápido de las centrales de incendio convencionales de la Serie NC»
- [ ] `hd_ke_dt3101w_hab_202407_es_30e0` (Kidde · 5 chunks · pm «KE-DT3101W-HAB»)
      → **IDS_CORRECTOS** · `kidde:ke-dt3101w-hab` · cita ✓ «KE-DT3101W-HAB ## Detector de calor direccionable inteligente serie Excellence con aislador»
- [ ] `hlsi-ti-001` (Notifier · 1 chunk · pm «RP1r»)
      → **IDS_CORRECTOS** · `notifier:rp1r-supra` · cita ✓ «Centrales de extinción de la Serie RP1r»
- [ ] `inc___doci_141_gu__a_r__pida_kidde_nc_pf__1__fcb9` (Kidde · 2 chunks · pm «NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4-SC/NC-PF8-SC»)
      → **IDS_CORRECTOS** · `kidde:nc-pf2`, `kidde:nc-pf4`, `kidde:nc-pf8`, `kidde:nc-pf2-sc`, `kidde:nc-pf4-sc`, `kidde:nc-pf8-sc` · cita ✓ «| **Modelo:** | Central Kidde NC-PF | | **Asunto:** | Guía rápida de usuario |»
- [ ] `ma-dt-1160` (Notifier · 14 chunks · pm «ExitPoint»)
      → **IDS_CORRECTOS** · `systemsensor:pf24v` · cita ✓ «Aplicaciones del *sonido direccional* para la protección de vidas # - ExitPoint™ -»
      ⚑ OEM/reventa: documento de **Notifier**, ids bajo **systemsensor**
- [ ] `mi_kidde_nc_pfx_202502_es_62f8` (Kidde · 133 chunks · pm «NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4-SC/NC-PF8-SC»)
      → **IDS_CORRECTOS** · `kidde:nc-pf2`, `kidde:nc-pf2-sc`, `kidde:nc-pf4`, `kidde:nc-pf4-sc`, `kidde:nc-pf8`, `kidde:nc-pf8-sc` · cita ✓ «Manual de instalación de las centrales de incendio convencionales de la Serie NC»
- [ ] `mie-mi-340_1` (Morley · 2 chunks · pm «EXP-051»)
      → **IDS_CORRECTOS** · `morley:exp-051` · cita ✓ «IMPRESORA MATRICIAL DE PUERTA MOD.EXP-051 ## MANUAL DE INSTALACIÓN»
- [ ] `mie-mi-431rv2_1` (Morley · 18 chunks · pm «ZXR50A/ZXR50P»)
      → **OTROS_IDS** · `morley:zxr-a`, `morley:zxr-p` · cita ✓ «MANUAL DE INSTALACIÓN Y FUNCIONAMIENTO ZXr-A/ZXr-P»
- [ ] `mndt1160` (Notifier · 51 chunks · pm «EXITPOINT»)
      → **IDS_CORRECTOS** · `systemsensor:pf24v` · cita ✓ «Sirena Direccional **EXITPOINT** **WITH VOICE MESSAGING** *Guía de Aplicación*»
      ⚑ OEM/reventa: documento de **Notifier**, ids bajo **systemsensor**
- [ ] `morley-se-pueden-pasar-programaciones-de-zx-y-dimension-a-connexion-dxc` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «¿Se pueden pasar programaciones de ZX y Dimensión a Connexion DXC?»
- [ ] `niveles-de-control-de-acceso-de-la-central-dxc-conexion` (Morley · 1 chunk · pm «DXc»)
      → **IDS_CORRECTOS** · `morley:dxc1`, `morley:dxc2`, `morley:dxc4` · cita ✓ «Niveles de control de acceso de la central DXC,CONEXION»
- [ ] `no-puedo-hacer-rearme-o-silenciar-sirenas-en-la-vsn-lt` (Morley · 1 chunk · pm «VSN-LT»)
      → **IDS_CORRECTOS** · `morley:vsn2-lt`, `morley:vsn4-lt`, `morley:vsn8-lt`, `morley:vsn12-lt` · cita ✓ «conectando el puente KEY que se encuentra en el canto inferior izquierdo de la tarjeta de las centrales VSN-LT»
- [ ] `osid-es-necesario-resetear-la-barrera-de-forma-externa` (Morley · 1 chunk · pm «OSID»)
      → **IDS_CORRECTOS** · `morley:mi-osi-rie` · cita ✓ «# OSID ¿Es necesario resetear la barrera de forma externa?»
- [ ] `ucip-como-enviar-datos-de-equipos-y-no-solo-eventos-de-zonas` (Morley · 1 chunk · pm «UCIP»)
      → **IDS_CORRECTOS** · `notifier:ucip` · cita ✓ «# UCIP - Como enviar datos de equipos y no solo eventos de zonas»
      ⚑ OEM/reventa: documento de **Morley**, ids bajo **notifier**
- [ ] `ucip-que-datos-necesito-de-la-receptora` (Morley · 1 chunk · pm «UCIP»)
      → **IDS_CORRECTOS** · `notifier:ucip` · cita ✓ «# UCIP - ¿Que datos necesito de la receptora?»
      ⚑ OEM/reventa: documento de **Morley**, ids bajo **notifier**

### §0.C — Candidates → **ALTA** (32)

Altas `candidate` del draft del detector. Muestreo **dirigido** (dirigido — chunks que MENCIONAN el término (ilike + recorte por regex con frontera de palabra), no los primeros del documento).
Señales duras: menciones estrictas / flexibles(separadores) / en MAYÚSCULAS: la diferencia entre ellas separa producto de artefacto
Degradación: confianza alta sin cita verificada → media → fuera del bloque

Ojo al contar: **32 filas → 27 ids únicos** (una fila es un par id+documento).
Ids propuestos desde MÁS DE UN documento: `kidde:ke-dba-ipw`×2, `kidde:ke-dba-recw`×2, `kidde:ke-dm3110r-kit`×2, `kidde:ke-iu3110`×2, `notifier:id2net`×2.
No son altas duplicadas: es el mismo producto atestado dos veces.
En el lote entero (bloque+residuo) el recibo cuenta 99 ids únicos sobre 133 filas.

- [ ] `aritech:2x-a` (2X-A) → **ALTA** · rol TITULO · doc `00-3280-507-4009-03_r003_2x-a_series_quick_installation_g…`
      menciones estrictas doc 1 / global 43 en 18 docs · cita ✓ «Guía de instalación rápida de la serie 2X-A»
- [ ] `kidde:ke-asa-auxr` (KE-ASA-AUXR) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_ASA_AUXR_f28f.pdf`
      menciones estrictas doc 2 / global 8 en 7 docs · cita ✓ «# KE-ASA-AUXR Intelligent addressable notification accessory - deep base (red)»
- [ ] `kidde:ke-dba-adpw-kil` (KE-DBA-ADPW-KIL) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_DBA_ADPW_KIL_202501_ING_c855.pdf`
      menciones estrictas doc 3 / global 11 en 2 docs · cita ✓ «# KE-DBA-ADPW-KIL **Intelligent addressable base accessory - Kilsen adapter (White)**»
- [ ] `kidde:ke-dba-adpw-zit` (KE-DBA-ADPW-ZIT) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_DBA_ADPW_ZIT_202501_ING_ed63.pdf`
      menciones estrictas doc 3 / global 11 en 2 docs · cita ✓ «The KE-DBA-ADPW-ZIT is an Excellence series base adapter.»
- [ ] `kidde:ke-dba-capw` (KE-DBA-CAPW) → **ALTA** · rol TITULO · doc `HD_KE_DBA_CAPW_202407_ING_d87d.pdf`
      menciones estrictas doc 4 / global 5 en 2 docs · cita ✓ «KIDDE COMMERCIAL # KE-DBA-CAPW **Accesorio base direccionable inteligente - Tapa (Blanca)**»
- [ ] `kidde:ke-dba-ipw` (KE-DBA-IPW) → **ALTA** · rol TITULO · doc `HD_KE_DBA_IPW_202407_ING_ffaf.pdf`
      menciones estrictas doc 3 / global 7 en 3 docs · cita ✓ «KIDDE™ COMMERCIAL # KE-DBA-IPW Accesorio base direccionable inteligente - base resistente a la…»
- [ ] `kidde:ke-dba-ipw` (KE-DBA-IPW) → **ALTA** · rol TITULO · doc `MI_KE_DBA_IPW_202407_ES_cc56.pdf`
      menciones estrictas doc 3 / global 7 en 3 docs · cita ✓ «KE-DBA-IPW IP Accessory for Standard Mounting Base Installation Sheet»
- [ ] `kidde:ke-dba-recw` (KE-DBA-RECW) → **ALTA** · rol TITULO · doc `HD_KE_DBA_RECW_202407_ES_bb2b.pdf`
      menciones estrictas doc 3 / global 10 en 4 docs · cita ✓ «KE-DBA-RECW Accesorio base direccionable inteligente - base empotrada (blanca)»
- [ ] `kidde:ke-dba-recw` (KE-DBA-RECW) → **ALTA** · rol TITULO · doc `MI_KE_DBA_RECW_202407_ES_aacc.pdf`
      menciones estrictas doc 3 / global 10 en 4 docs · cita ✓ «KE-DBA-RECW Recess Accessory for Standard Mounting Base Installation Sheet»
- [ ] `kidde:ke-dba-tagw` (KE-DBA-TAGW) → **ALTA** · rol TITULO · doc `HD_KE_DBA_TAGW_202407_ES_4b26.pdf`
      menciones estrictas doc 5 / global 12 en 8 docs · cita ✓ «KIDDE COMMERCIAL # KE-DBA-TAGW Accesorio base direccionable inteligente - Etiqueta de direcció…»
- [ ] `kidde:ke-dm3110r-ip` (KE-DM3110R-IP) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_DM3110R_IP_202412_ES_8165.pdf`
      menciones estrictas doc 2 / global 3 en 2 docs · cita ✓ «KE-DM3110R-IP Pulsador direccionable inteligente de la Serie Excellence con aislador - para ex…»
- [ ] `kidde:ke-dm3110r-kit` (KE-DM3110R-KIT) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_DM3110R_KIT_f3b7.pdf`
      menciones estrictas doc 3 / global 3 en 1 doc · cita ✓ «The KE-DM3110R-KIT is a red, single action indoor MCP with a House-on-Fire functional indicato…»
- [ ] `kidde:ke-dm3110r-kit` (KE-DM3110R-KIT) → **ALTA** · rol TITULO · doc `DS_KIDDE_KE_DM3110R_KIT_f3b7.pdf`
      menciones estrictas doc 0 / global 3 en 1 doc · cita ✓ «KE-DM3110R-KIT **Excellence Series intelligent addressable manual call point with isolator and…»
- [ ] `kidde:ke-dp3021b` (KE-DP3021B) → **ALTA** · rol TITULO · doc `HD_KE_DP3021B_202407_ES_861a.pdf`
      menciones estrictas doc 2 / global 6 en 4 docs · cita ✓ «KIDDE COMMERCIAL # KE-DP3021B Detector de calor/óptico dual direccionable inteligente serie Ex…»
- [ ] `kidde:ke-dp3021w` (KE-DP3021W) → **ALTA** · rol TITULO · doc `HD_KE_DP3021W_202407_ES_778e.pdf`
      menciones estrictas doc 2 / global 9 en 7 docs · cita ✓ «KIDDE™ COMMERCIAL # KE-DP3021W ## Detector de calor/óptico dual direccionable inteligente seri…»
- [ ] `kidde:ke-iu3110` (KE-IU3110) → **ALTA** · rol TITULO · doc `HD_KE_IU3110_202407_ES_42d6.pdf`
      menciones estrictas doc 7 / global 19 en 6 docs · cita ✓ «KE-IU3110 Unidad inteligente direccionable de 1 entrada con aislador»
- [ ] `kidde:ke-iu3110` (KE-IU3110) → **ALTA** · rol REFERENCIA_COMERCIAL · doc `MI_KE_IU3110_202407_ES_5e36.pdf`
      menciones estrictas doc 6 / global 19 en 6 docs · cita ✓ «Product identification | KE-IU3110»
- [ ] `kidde:n-io-mbx-2` (N-IO-MBX-2) → **ALTA** · rol TITULO · doc `DS_KIDDE_N_IO_MBX_2_202505_ES_b34f.pdf`
      menciones estrictas doc 3 / global 19 en 7 docs · cita ✓ «La N-IO-MBX-2 es una caja de montaje en superficie diseñada para alojar módulos que requieren…»
- [ ] `kidde:n-io-sbx-2g` (N-IO-SBX-2G) → **ALTA** · rol TITULO · doc `DS_KIDDE_N_IO_SBX_2G_202505_ES_6eb1.pdf`
      menciones estrictas doc 4 / global 5 en 2 docs · cita ✓ «N-IO-SBX-2G Caja para 1 módulo con carril DIN (grande)»
- [ ] `morley:dxc-connexion` (DXc Connexion) → **ALTA** · rol TITULO · doc `No-puedo-hacer-rearmes-silenciar-sirenas-y-otros-controle…`
      menciones estrictas doc 0 / global 21 en 14 docs · cita ✓ «DXC Connexion - Avería F. Alimentación externa»
- [ ] `morley:mod-rs-232` (MOD.RS-232) → **ALTA** · rol TITULO · doc `MIE-MI-330`
      menciones estrictas doc 1 / global 1 en 1 doc · cita ✓ «# TARJETA DE COMUNICACIONES RS-232 # MOD.RS-232 # MANUAL DE INSTALACIÓN»
- [ ] `morley:mod-rs-485` (MOD.RS-485) → **ALTA** · rol TITULO · doc `MIE-MI-390`
      menciones estrictas doc 1 / global 1 en 1 doc · cita ✓ «# TARJETA DE COMUNICACIONES RS-485 # MOD.RS-485 # MANUAL DE INSTALACIÓN»
- [ ] `morley:vision-supra` (Vision Supra) → **ALTA** · rol TITULO · doc `30012012 TARJETAS IDIOMAS VISION SUPRA rev A`
      menciones estrictas doc 2 / global 4 en 2 docs · cita ✓ «321XXX TARJETAS IDIOMAS VISION SUPRA FECHA: 26/01/2011 REV: A DESCRIPCIÓN: LANZAMIENTO»
- [ ] `notifier:clss-configuration-tool` (CLSS Configuration Tool) → **ALTA** · rol REFERENCIA_COMERCIAL · doc `4188-1124-PT issue 4_01-2026_To.pdf`
      menciones estrictas doc 4 / global 21 en 6 docs · cita ✓ «Honeywell no recomienda la instalación de más de una instancia del programa CLSS Configuration…»
- [ ] `notifier:id2net` (ID²NET) → **ALTA** · rol TITULO · doc `MADT190P_01_C`
      menciones estrictas doc 0 / global 74 en 10 docs · cita ✓ «# RED DIGITAL E INTELIGENTE # ID<sup>2</sup>net»
- [ ] `notifier:id2net` (ID²NET) → **ALTA** · rol TITULO · doc `MADT190_01`
      menciones estrictas doc 61 / global 75 en 13 docs · cita ✓ «# RED DIGITAL E INTELIGENTE # ID²net»
- [ ] `notifier:kit-gas` (KIT-GAS) → **ALTA** · rol TITULO · doc `HLSI-MN-627`
      menciones estrictas doc 2 / global 4 en 3 docs · cita ✓ «KIT-GAS ## Teclado de mano para calibración de los detectores de gas de la <ins>serie SMART 3<…»
- [ ] `notifier:nfxi-bsf-wch` (NFXI-BSF-WCH) → **ALTA** · rol TABLA_DE_MODELOS · doc `D 1147-1 BRH Notifier`
      menciones estrictas doc 0 / global 3 en 3 docs · cita ✓ «BRH-PC-102/<br/>NFXI-BSF-WCH | Detector de Base con Sirena y Luz Estroboscópica»
- [ ] `notifier:stratos` (STRATOS) → **ALTA** · rol TITULO · doc `MADT731_02`
      menciones estrictas doc 18 / global 54 en 11 docs · cita ✓ «Stratos instalado en un almacén o hipermercado»
- [ ] `spectrex:40-40m` (40-40M) → **ALTA** · rol REFERENCIA_COMERCIAL · doc `MNDT725_40-40M`
      menciones estrictas doc 0 / global 0 en 0 docs · cita ✓ «S40/40M XXXXX, donde XXXXX define el modelo según los requisitos anteriores»
- [ ] `spectrex:40-40r` (40-40R) → **ALTA** · rol TITULO · doc `MNDT724_40-40R`
      menciones estrictas doc 0 / global 0 en 0 docs · cita ✓ «DETECTOR DE LLAMA INFRARROJO IR # MODELO S40/40R»
- [ ] `spectrex:40-40u` (40-40U) → **ALTA** · rol TABLA_DE_MODELOS · doc `MNDT723_40-40U`
      menciones estrictas doc 0 / global 0 en 0 docs · cita ✓ «| Tipo de combustible | Distancia máxima (metros)<br/>40/40U y UB |»

### §0.D — Candidates → **RETIRAR** (17)

Términos que el detector propuso como producto y **NO lo son**: son artefactos de
extracción (código del propio documento, nombre de fabricante, frase técnica). La
pasada detectó **48 artefactos** sobre **39 ids únicos**; clases: `codigo_del_propio_documento`, `frase_tecnica_o_corriente`, `nombre_de_fabricante_o_gama`, `no_aparece_en_ningun_sitio`.
Retirar = no darlos de alta. Es la mitad barata del sí: quita ruido del detector.

- [ ] `fidegas:el-11` (EL-11) → **RETIRAR** · ARTEFACTO_EXTRACCION / FRASE_TECNICA · doc `Manual-de-Usuario-S3-2`
      estrictas 0 · mayúsculas 0 · como fragmento 1 · cita ✓ «Elaborado y aprobado en Revisión 21 el 11/2018 por Dpto. Calidad.»
      razón: «EL-11» nace de la fecha «el 11/2018»; el producto real del manual es el sensor remoto S/3-2.
- [ ] `fidegas:el-11` (EL-11) → **RETIRAR** · ARTEFACTO_EXTRACCION / FRASE_TECNICA · doc `Manual-de-Usuario-S3-IR-y-S-2-IR`
      estrictas 0 · mayúsculas 0 · como fragmento 1 · cita ✓ «Elaborado y aprobado en Revisión 13 el 11/2018 por Dpto. Calidad»
      razón: «EL-11» nace de la fecha «el 11/2018»; el producto real del manual es el sensor remoto S/3-IR y S/2-IR.
- [ ] `morley:de-80` (DE-80) → **RETIRAR** · ARTEFACTO_EXTRACCION / FRASE_TECNICA · doc `TG-Cuales-son-los-requisitos-del-PC-para-el-progr…`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «Se requiere un disco duro con un mínimo de 80 Gb de espacio libre»
      razón: Nació de la preposición española «de 80» en medidas (80 Gb, 80 columnas, 80 caracteres); nunca aparece como modelo.
- [ ] `morley:ma120` (MA120) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `HLSI_MA102_bis2.pdf`
      estrictas 2 · mayúsculas 2 · como fragmento 0 · cita ✓ «HLSI_MA120. 16 mayo 2008»
      razón: MA120 solo aparece en el pie de página como código del documento HLSI, junto a la fecha, nunca como producto.
- [ ] `morley:miein-004` (MIEIN-004) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `Relacion-de-producto-obsoleto-de-Morley-IAS-by-Ho…`
      estrictas 0 · mayúsculas 1 · como fragmento 1 · cita ✓ «https://morley-ias.es/documentacion/morley/manualesdes/MIEIN004.pdf»
      razón: MIEIN004 es el nombre del fichero PDF enlazado (código de documento), no un modelo de producto.
- [ ] `notifier:etdt-312` (ETDT-312) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `ETDT312`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «NOTIFIER® by Honeywell ET-DT-312 03-01-06 1 de 1»
      razón: «ET-DT-312» es la referencia del documento (patrón tipo MA-DT-015); el contenido trata etiquetas del sistema NAS-2.
- [ ] `notifier:etdt-314` (ETDT-314) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `ETDT314`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «by Honeywell ET-DT-314 19-01-07 1 de 1»
      razón: «ET-DT-314» es la referencia del documento en la cabecera; el manual trata de etiquetas del NAS-1u, no de un producto ETDT-314.
- [ ] `notifier:madt-015` (MADT-015) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `MADT015_01`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «MA-DT-015_01_C (997-502) 27/07/04 NOTIFIER ESPAÑA»
      razón: «MADT-015» deriva del código de documento MA-DT-015 en la cabecera del manual; nunca aparece como modelo comercial.
- [ ] `notifier:madt-731` (MADT-731) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `MADT731_06`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «MA-DT-731_06»
      razón: MADT-731 deriva del código de documento MA-DT-731_06; el manual es una guía genérica de puntos de muestreo capilares, sin tal modelo.
- [ ] `notifier:madt-742` (MADT-742) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `MADT742`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «MA-DT-742; 24/12/2007 1 de 1»
      razón: El término deriva del código de documento MA-DT-742, igual que el artefacto conocido MA-DT-015; no aparece como producto.
- [ ] `notifier:mndt-1202` (MNDT-1202) → **RETIRAR** · ARTEFACTO_EXTRACCION / NO_APARECE · doc `MNDT1202`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «# Aerosol para limpieza de detectores»
      razón: MNDT-1202 no aparece en el texto; deriva del nombre del fichero MNDT1202, un código de documento como MNDT690.
- [ ] `notifier:mndt-600` (MNDT-600) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `MNDT600`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «**MN-DT-600_A** 06 ABRIL 2011»
      razón: «MNDT-600» deriva del código de manual MN-DT-600_A; es un documento genérico de notas de mantenimiento, no un modelo.
- [ ] `notifier:mndt-701` (MNDT-701) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `MNDT701.pdf`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «**MN-DT-701**<br/>**13 OCTUBRE 1997**<br/>**Versión 1.0**»
      razón: MNDT-701 no aparece verbatim; deriva de MN-DT-701, referencia del manual (como MA-DT-015), no un modelo de producto.
- [ ] `notifier:s20` (S20) → **RETIRAR** · ARTEFACTO_EXTRACCION / FRASE_TECNICA · doc `MNDT696`
      estrictas 64 · mayúsculas 64 · como fragmento 64 · cita ✓ «DETECTOR DE LLAMA DE TRIPLE ESPECTRO INFRARROJO IR<sup>3</sup> MODELO S20/20MI»
      razón: Las 64 menciones del documento y 44 del resto van seguidas de más código: «S20» es fragmento del modelo completo S20/20MI.
- [ ] `notifier:tidt-060` (TIDT-060) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `TIDT060.pdf`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «TI-DT-060 05/05/03 1 de 1 # Información Técnica»
      razón: TI-DT-060 es la referencia del documento de Información Técnica, no un modelo; los productos reales son ID50, AM2000, VeriFire, etc.
- [ ] `notifier:tidt-101` (TIDT-101) → **RETIRAR** · ARTEFACTO_EXTRACCION / CODIGO_DE_DOCUMENTO · doc `TIDT101.pdf`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «Información técnica TI-DT-101»
      razón: TIDT-101 deriva del código de documento TI-DT-101; es un procedimiento de actualización de software, no un producto.
- [ ] `sound-alert:some-58` (SOME-58) → **RETIRAR** · ARTEFACTO_EXTRACCION / FRASE_TECNICA · doc `ExitPoint- WP ENG`
      estrictas 0 · mayúsculas 0 · como fragmento 0 · cita ✓ «Interdisciplinary research is promoted through some 58 home departments and some 58 resea…»
      razón: Nace de la frase inglesa «some 58» (unos 58 departamentos); nunca aparece como modelo exacto ni en mayúsculas.

### §0.E — `product_model` sucio: **2 RETAG + 1 MANTENER** (3)

Docs cuyo `product_model` es basura extraída (una fecha, un código). **Ojo: no todos
son RETAG** — 2 RETAG, 1 MANTENER. Un `MANTENER` significa que el valor actual
es correcto y **no hay nada que aplicar**; entra en el bloque para que conste juzgado.

Gates de bloque: `k_unanime`, `citas_verificadas`, `confianza_alta`, `modelos_atestiguados`, `mantener_sin_tapado`
K=3 pasadas del juez `claude-fable-5`, unanimidad exigida.

- [ ] `asd in rail transportation applications_es` · pm actual «MARCH-2011» · Notifier · 2 chunks
      veredicto **RETAG** → product_model `FAAST` · confianza alta · cita ✓
      cita: «la tecnología de detección de incendios por aspiración FAAST™ combina técnicas avanzadas de filtraje en tres etapas»
      razón: El valor sucio 'MARCH-2011' es basura extraída de la nota al pie de prensa ('Manchester Evening News, March 2011'). El documento es un folleto de aplicación (transporte ferroviario/metro) de la famil…
      aplicar: documents.pm 'MARCH-2011' → 'FAAST' · chunks_v2.pm 'MARCH-2011' → 'FAAST' en 2 chunks · doc_map: NO se propone alta. El modelo es un PARAGUAS (familia) y resolve() expande 13 miembros qu…
      ⚑ residuo que NO cierra este sí: Al ser FAAST un token paraguas ('divergent': true, 'expand': true), queda pendiente la adjudicación gobernada del doc_map a los 13 miembros del catálogo, o decidir si el folleto aplica a to…
- [ ] `compatibilidad-entre-equipos-notifier-y-morley` · pm actual «unknown» · Morley · 1 chunk
      veredicto **MANTENER** → product_model `unknown` · confianza alta · cita ✓
      cita: «No, no es posible instalar equipos de Notifier en una central de Morley o equipos de Morley en una central de Notifier, pués los protocolos de comuni…»
      razón: Es una FAQ genérica de compatibilidad marca-a-marca (Notifier vs Morley). El texto completo no imprime ningún modelo de producto: el censo de candidatos por regex está vacío y la respuesta habla de '…
      aplicar: documents.pm SIN CAMBIO · chunks_v2.pm SIN CAMBIO · doc_map: sin fila (correcto: no hay producto que mapear)
      ⚑ residuo que NO cierra este sí: ¿Debería este tipo de FAQ de marca a marca tener una categoría propia (p.ej. product_model='N/A-brand-faq') en vez de 'unknown' para distinguirlo de documentos con modelo aún no identificad…
- [ ] `d686 ema1224b4r_w ns4r` · pm actual «EN-54-3» · Notifier · 1 chunk
      veredicto **RETAG** → product_model `EMA1224B4R/W` · confianza alta · cita ✓
      cita: «INSTALLATION INSTRUCTIONS FOR WALL MOUNT SOUNDERS TYPE EMA1224B4R/W»
      razón: El valor actual 'EN-54-3' es una norma (citada dos veces como requisito EN54-3), no un producto. El documento imprime en su título un único modelo, EMA1224B4R/W, y todo el contenido (tonos, especific…
      aplicar: documents.pm 'EN-54-3' → 'EMA1224B4R/W' · chunks_v2.pm 'EN-54-3' → 'EMA1224B4R/W' en 1 chunks · doc_map: alta de fila BLOQUEADA: el modelo no existe en el catálogo gobernado → requiere primero a…
      ⚑ residuo que NO cierra este sí: ¿El catálogo gobernado distingue EMA1224B4R y EMA1224B4W como dos SKUs separados (lo que convertiría esto en MULTI), o acepta el token compuesto EMA1224B4R/W tal como lo imprime KAC?

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
      pm doc «INSPIRE E10/E15» · pm chunks «INSPIRE E10/E15» · tokens sin id: `E15`
      ids del packet 12-ago `notifier:inspire-e10` → resueltos HOY `notifier:inspire-e10`
      juez: **MULTI** `notifier:inspire-e10`, `notifier:inspire-e15` · confianza media · cita ✗ sin cita en el recibo
      sujeto según el juez: Guía rápida de las centrales de incendio Notifier INSPIRE E10 y E15 (proceso de aprendizaje de dispositivos del lazo)
      menciones máximas del sujeto en el documento: 0
      **por qué NO entra en bloque**: confianza media; cita no verificada full-text; la cita verifica pero NO nombra al sujeto: la entrada se apoyaría sólo en la ficha del documento, no en su contenido
- [ ] `996-130-000-3 manuel d'utilisation zx_hlsi` (Morley · 1 chunk · vigente)
      pm doc «ZX» · pm chunks «ZX» · tokens sin id: —
      ids del packet 12-ago `morley:zx2e`, `morley:zx2se`, `morley:zx50`, `morley:zxae`, `morley:zxce`, `morley:zxhe` → resueltos HOY — · **deriva**
      juez: **MULTI** `morley:zx2e`, `morley:zx2se`, `morley:zx50`, `morley:zxae`, `morley:zxce`, `morley:zxhe` · confianza media · cita ✓ «Manuel d'utilisation MORLEY-IAS Central de détection d’incendie ZX»
      sujeto según el juez: Manual de usuario en francés de la central de detección de incendios Morley-IAS serie ZX (solo páginas finales de notas y contacto)
      menciones máximas del sujeto en el documento: 1
      **por qué NO entra en bloque**: confianza media
- [ ] `asd harsh environments_sp` (Xtralis · 6 chunks · vigente)
      pm doc «FAAST» · pm chunks «FAAST» · tokens sin id: —
      ids del packet 12-ago `morley:mi-fl2011ei`, `morley:mi-fl2012ei`, `morley:mi-fl2022ei`, `notifier:faast-8100e`, `notifier:fl0111e-hs`, `notifier:fl0112e-hs` …(+7) → resueltos HOY `morley:mi-fl2011ei`, `morley:mi-fl2012ei`, `morley:mi-fl2022ei`, `notifier:faast-8100e`, `notifier:fl0111e-hs`, `notifier:fl0112e-hs` …(+7)
      juez: **IDS_CORRECTOS** `notifier:fl0111e-hs`, `notifier:fl0112e-hs`, `notifier:fl0122e-hs`, `notifier:fl2011ei-hs`, `notifier:fl2012ei-hs`, `notifier:fl2022ei-hs` …(+7) · confianza alta · cita ✓ «Detección de humo por aspiración en ambientes agresivos FAAST FIRE ALARM ASPIRATION SENSI…»
      sujeto según el juez: Guía de aplicación de la familia de detectores de humo por aspiración FAAST en ambientes agresivos
      menciones máximas del sujeto en el documento: 5
      **por qué NO entra en bloque**: ambigüedad estructural: la entrada atestaría productos de 2 marcas ['morley', 'notifier'] — clase rebrand/OEM, decisión entre marcas
- [ ] `con-que-sistema-operativo-es-compatible-el-programa-de-la-zx-y-dx` (Morley · 1 chunk · vigente)
      pm doc «ZX/DX» · pm chunks «ZX/DX» · tokens sin id: `DX`
      ids del packet 12-ago `morley:zx2e`, `morley:zx2se`, `morley:zx50`, `morley:zxae`, `morley:zxce`, `morley:zxhe` → resueltos HOY — · **deriva**
      juez: **MULTI** `morley:zx2e`, `morley:zx2se`, `morley:zxae`, `morley:zxhe`, `morley:zxce`, `morley:zx50` · confianza media · cita ✓ «¿Con que Sistema Operativo es compatible el programa de la ZX y DX? **Answers** Los siste…»
      sujeto según el juez: Software de programación (FIRE5/FIRE6/MK-DX) de las centrales de incendio de las familias ZX y DX de Morley
      menciones máximas del sujeto en el documento: 1
      **por qué NO entra en bloque**: confianza media
- [ ] `finales-de-linea-de-las-centrales-convencionales` (Morley · 1 chunk · vigente)
      pm doc «NFS2/NFS4/NFS8/VSN2-LT/VSN4-LT/VSN8-LT/VSN12-LT/VSN2-P…» · pm chunks «NFS2/NFS4/NFS8/VSN2-LT/VSN4-LT/VSN8-LT/VSN12-LT/VSN2-P…» · tokens sin id: `NFS2`, `NFS4`, `NFS8`, `VSN2-PLUS`, `VSN12-PLUS`
      ids del packet 12-ago `morley:vsn-4-plus`, `morley:vsn-8-plus`, `morley:vsn12-lt`, `morley:vsn2-lt`, `morley:vsn4-lt`, `morley:vsn8-lt` → resueltos HOY `morley:vsn-4-plus`, `morley:vsn-8-plus`, `morley:vsn12-lt`, `morley:vsn2-lt`, `morley:vsn4-lt`, `morley:vsn8-lt`
      juez: **MULTI** `notifier:nfs-2-8`, `morley:vsn2-lt`, `morley:vsn4-lt`, `morley:vsn8-lt`, `morley:vsn12-lt`, `morley:vsn-4-plus` …(+2) · confianza alta · cita ✓ «Los finales de línea para las centrales convencionales son; * **NFS2-8** La central está…»
      sujeto según el juez: FAQ sobre los elementos de final de línea de las centrales convencionales NFS2-8, familia VSN-LT, familia VSN-PLUS y la VSN2-PLUS
      menciones máximas del sujeto en el documento: 1
      **por qué NO entra en bloque**: ids CANDIDATE ['notifier:vsn-plus']: el producto existe pero está pendiente de QA humana — atestarlo con un documento es promoverlo de hecho, y esa es una decisión de Alberto, no un efecto colateral; ambigüedad estructu…
      ids NO consumibles (candidate/retirado): `notifier:vsn-plus`
- [ ] `gr_kidde_2x_at_fr_fb_s_27cf` (Aritech · 29 chunks · vigente)
      pm doc «2X-AT-FR-FB-S/2X-AT-FR-S» · pm chunks «2X-AT-FR-FB-S/2X-AT-FR-S» · tokens sin id: —
      ids del packet 12-ago `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s` → resueltos HOY `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s`
      juez: **MULTI** `kidde:2x-at`, `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s` · confianza alta · cita ✓ «2X-AT Series Quick Start Guide»
      sujeto según el juez: Guía rápida de la serie 2X-AT de centrales y repetidores direccionables de alarma de incendio (Kidde Commercial / Carrier)
      menciones máximas del sujeto en el documento: 1
      **por qué NO entra en bloque**: ids CANDIDATE ['kidde:2x-at']: el producto existe pero está pendiente de QA humana — atestarlo con un documento es promoverlo de hecho, y esa es una decisión de Alberto, no un efecto colateral
      ids NO consumibles (candidate/retirado): `kidde:2x-at`
- [ ] `hlsi-ti-007_vsn-4rel` (Morley · 1 chunk · vigente)
      pm doc «VSN-4REL» · pm chunks «VSN-4REL» · tokens sin id: —
      ids del packet 12-ago `notifier:vsn-4rel` → resueltos HOY `notifier:vsn-4rel`
      juez: **IDS_CORRECTOS** `notifier:vsn-4rel` · confianza media · cita ✗ sin cita en el recibo
      sujeto según el juez: Relé/módulo VSN-4REL (según ficha; el contenido ingestado solo muestra la portada Honeywell Life Safety Iberia)
      menciones máximas del sujeto en el documento: 0
      **por qué NO entra en bloque**: confianza media; cita no verificada full-text; la cita verifica pero NO nombra al sujeto: la entrada se apoyaría sólo en la ficha del documento, no en su contenido
- [ ] `mi_kidde_2x_at_f2_fb_07d4` (Aritech · 212 chunks · vigente)
      pm doc «2X-AT-F2/2X-AT-F2-FB/2X-AT-FR-FB-S/2X-AT-FR-S» · pm chunks «2X-AT-F2/2X-AT-F2-FB/2X-AT-FR-FB-S/2X-AT-FR-S» · tokens sin id: —
      ids del packet 12-ago `kidde:2x-at-f2`, `kidde:2x-at-f2-fb`, `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s` → resueltos HOY `kidde:2x-at-f2`, `kidde:2x-at-f2-fb`, `kidde:2x-at-fr-fb-s`, `kidde:2x-at-fr-s`
      juez: **OTROS_IDS** `kidde:2x-af2`, `kidde:2x-af1`, `kidde:2x-afr`, `kidde:2x-ae2`, `kidde:2x-ae1` · confianza alta · cita ✓ «This is the installation manual for the 2X-A Series fire alarm, repeater, and evacuation…»
      sujeto según el juez: Manual de instalación de las centrales de incendio, repetidores y centrales de evacuación de la serie 2X-A de Kidde (variantes 2X-AF1, 2X-AF2, 2X-AFR…
      K=2 (2ª pasada): **OTROS_IDS** `kidde:2x-af1`, `kidde:2x-af2`, `kidde:2x-afr`, `kidde:2x-ae1`, `kidde:2x-ae2` · confianza media
      menciones máximas del sujeto en el documento: 0
      **por qué NO entra en bloque**: K=2 sin acuerdo: 2ª pasada dice OTROS_IDS/media con ['kidde:2x-af1', 'kidde:2x-af2', 'kidde:2x-afr', 'kidde:2x-ae1', 'kidde:2x-ae2']
- [ ] `mi_kidde_ke_dp312x_snx_202512_es_242d` (Kidde · 45 chunks · vigente)
      pm doc «KE-DP3120W/KE-DP3120W-SN/KE-DP3120W-SNV/KE-DP3121B/KE-…» · pm chunks «KE-DP3120W/KE-DP3120W-SN/KE-DP3120W-SNV/KE-DP3121B/KE-…» · tokens sin id: `KE-DP3120W-SN`, `KE-DP3120W-SNV`, `KE-DP3121B`, `KE-DP3121B-SNV`, `KE-DP3121W`, `KE-DP3121W-SN`, `KE-DP3121W-SNV`
      ids del packet 12-ago `kidde:ke-dp3120w` → resueltos HOY `kidde:ke-dp3120w`
      juez: **IDS_CORRECTOS** `kidde:ke-dp3120w` · confianza alta · cita ✓ «Excellence Series Intelligent Addressable Dual Optical and Dual Optical/Heat Detectors wi…»
      sujeto según el juez: Hoja de instalación de familia: detectores direccionables inteligentes Excellence Series ópticos duales y ópticos/calor con sirena/VAD integrados (va…
      menciones máximas del sujeto en el documento: 8
      **por qué NO entra en bloque**: ambigüedad estructural: el token ['KE-DP3120W-SN', 'KE-DP3120W-SNV', 'KE-DP3121B', 'KE-DP3121B-SNV', 'KE-DP3121W', 'KE-DP3121W-SN', 'KE-DP3121W-SNV'] sería un producto que NO está en el catálogo (antes que la entrada de…
- [ ] `mi_kidde_ke_io3144_631e` (Kidde · 33 chunks · vigente)
      pm doc «KE-IO3144/KE-IU3110» · pm chunks «KE-IO3144/KE-IU3110» · tokens sin id: `KE-IU3110`
      ids del packet 12-ago `kidde:ke-io3144` → resueltos HOY `kidde:ke-io3144`
      juez: **MULTI** `kidde:ke-io3144`, `kidde:ke-io3122` · confianza alta · cita ✓ «This installation sheet includes information on the following 3000 Series input/output mo…»
      sujeto según el juez: Hoja de instalación de los módulos de entrada/salida direccionables de la serie 3000 (Excellence), cubriendo KE-IO3122 (2 E/S) y KE-IO3144 (4 E/S)
      menciones máximas del sujeto en el documento: 8
      **por qué NO entra en bloque**: ambigüedad estructural: el token ['KE-IU3110'] sería un producto que NO está en el catálogo (antes que la entrada de doc_map hace falta un ALTA)
- [ ] `mie-mi-120p` (Morley · 1 chunk · vigente)
      pm doc «VSN 2-4» · pm chunks «VSN 2-4» · tokens sin id: —
      ids del packet 12-ago `morley:vsn2` → resueltos HOY `morley:vsn2`
      juez: **IDS_CORRECTOS** `morley:vsn2` · confianza alta · cita ✓ «● - ● VISION ● BATTERY»
      sujeto según el juez: Central convencional de incendios Morley Vision (VSN 2-4), panel frontal con zonas Z1-Z4
      menciones máximas del sujeto en el documento: 0
      **por qué NO entra en bloque**: posible atribución circular: el id viene de un alias/paraguas AUTO-IMPORTADO de un documento (s83:MIEMI120rev05) y este manual no nombra al sujeto ni una vez
- [ ] `miemu520p` (Morley · 1 chunk · vigente)
      pm doc «Dimension» · pm chunks «Dimension» · tokens sin id: `Dimension`
      ids del packet 12-ago — → resueltos HOY —
      juez: **MULTI** `morley:dx1e`, `morley:dx2e`, `morley:dx4e` · confianza media · cita ✓ «MORLEY-IAS Série Dimension»
      sujeto según el juez: Manual de funcionamiento de las centrales de incendio Morley-IAS de la Série Dimension (páginas finales del manual de familia)
      menciones máximas del sujeto en el documento: 1
      **por qué NO entra en bloque**: confianza media; ids CANDIDATE ['morley:dx1e', 'morley:dx2e', 'morley:dx4e']: el producto existe pero está pendiente de QA humana — atestarlo con un documento es promoverlo de hecho, y esa es una decisión de Alberto, no…
      ids NO consumibles (candidate/retirado): `morley:dx1e`, `morley:dx2e`, `morley:dx4e`
- [ ] `mu_kidde_2x_at_fr_fb_s_6c31` (Aritech · 46 chunks · vigente)
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
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «**DOA FJ/CPD** – Fire alarm sounding device for fire signalling conform to regulatio…»
      doc `Manual Rotulo REXD-103_EN` · estrictas doc 2 / global 2 en 1 doc
- [ ] `fidegas:s-2-t1-y-s-3-t1` (S/2-T1 y S/3-T1)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «SENSOR REMOTO # S/3-T1 y S/2-T1 ## TÓXICOS»
      doc `Manual-de-Usuario-S3-T1-y-S-2-T1` · estrictas doc 0 / global 0 en 0 docs · otros motivos: contradiccion:producto-real-sin-mencion-estricta-ni-en-mayusculas; juez:propone-otra-grafia(S/3-T1 y S/2-T1)
      el juez propone otra grafía: `S/3-T1 y S/2-T1`
- [ ] `kidde:ke-dba-adpw-kil-ke-dba-adpw-zit` (KE-DBA-ADPW-KIL/KE-DBA-ADPW-ZIT)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «| KE-DBA-ADPW-KIL | Adaptor Accessory for Kilsen Mounting Bases |»
      doc `G_INST_KIDDE_KE_DBA_ADPW_202502_ES_70e7.pdf` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `KE-DBA-ADPW-KIL y KE-DBA-ADPW-ZIT (serie KE-DBA-ADPW)`
- [ ] `kidde:ke-dba-labw-l1s-ke-dba-labw-l2s-ke-dba-labw-l3s-ke-dba-labw-l4s` (KE-DBA-LABW-L1S/KE-DBA-LABW-L2S/KE-DBA-LABW-L3S/KE-DBA-LABW-L4S)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «El KE-DBA-LABW-S es un juego de etiquetas adhesivas de la serie Excellence de format…»
      doc `HD_KE_DBA_LABW_LxS_202407_ES_2fc1.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media
      el juez propone otra grafía: `KE-DBA-LABW-S`
- [ ] `kidde:ke-dp3121b-ke-dp3121b-snv` (KE-DP3121B/KE-DP3121B-SNV)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «KIDDE™ COMMERCIAL # KE-DP3121B-SNV»
      doc `DS_KIDDE_KE_DP3121B_SNV_202503_ES_b5bc.pdf` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `KE-DP3121B-SNV`
- [ ] `kidde:ke-dp3121w-ke-dp3121w-sn` (KE-DP3121W/KE-DP3121W-SN)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «KIDDE COMMERCIAL # KE-DP3121W-SN Detector de calor/óptico dual direccionable intelig…»
      doc `DS_KIDDE_KE_DP3121W_SN_202503_ES_5938.pdf` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `KE-DP3121W-SN`
- [ ] `kidde:ke-dp3121w-ke-dp3121w-sn-ke-dp3121w-snv` (KE-DP3121W/KE-DP3121W-SN/KE-DP3121W-SNV)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «KIDDE COMMERCIAL # KE-DP3121W-SNV Detector de calor/óptico dual direccionable inteli…»
      doc `DS_KIDDE_KE_DP3121W_SNV_202503_ES_8699.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media
      el juez propone otra grafía: `KE-DP3121W-SNV`
- [ ] `kidde:ke-iu3111-zme-kit-2x-ae1-09` (KE-IU3111-ZME/KIT 2X-AE1-09)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «KIDDE™ COMMERCIAL # KE-IU3111-ZME»
      doc `DS_KIDDE_KE_IU3111_ZME_f908.pdf` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `KE-IU3111-ZME`
- [ ] `kidde:ke-iu3111-zme-kit-2x-ae1-09` (KE-IU3111-ZME/KIT 2X-AE1-09)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «KE-IU3111-ZME Intelligent Addressable Zone Monitoring Unit (device type 1ZMxi)»
      doc `MI_KE_IU3111_ZME_202407_ES_fde1.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media
      el juez propone otra grafía: `KE-IU3111-ZME`
- [ ] `kidde:n-io-mbx-1-n-io-mbx-2` (N-IO-MBX-1/N-IO-MBX-2)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «KIDDE COMMERCIAL # N-IO-MBX-1 Caja para módulos carril DIN»
      doc `DS_KIDDE_N_IO_MBX_1_202505_ES_07ca.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `N-IO-MBX-1`
- [ ] `kidde:n-io-mbx-1-n-io-mbx-2` (N-IO-MBX-1/N-IO-MBX-2)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «N-IO-MBX Series DIN Rail Module Box Installation Sheet»
      doc `MI_N_IO_MBX_X_202505_ES__1__1fd1.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: contradiccion:producto-real-sin-mencion-estricta-ni-en-mayusculas; juez:propone-otra-grafia(N-IO-MBX-1 y N-IO-MBX-2 (serie N-IO-MBX)); ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `N-IO-MBX-1 y N-IO-MBX-2 (serie N-IO-MBX)`
- [ ] `kidde:n-io-sbx-1g-n-io-sbx-2g` (N-IO-SBX-1G/N-IO-SBX-2G)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «KIDDE COMMERCIAL # N-IO-SBX-1G Caja para 1 módulo con carril DIN (pequeño)»
      doc `DS_KIDDE_N_IO_SBX_1G_202505_ES_b086.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: contradiccion:producto-real-sin-mencion-estricta-ni-en-mayusculas; juez:propone-otra-grafia(N-IO-SBX-1G)
      el juez propone otra grafía: `N-IO-SBX-1G`
- [ ] `kidde:zlsm-me-zlsm-mr` (ZLSM-ME/ZLSM-MR)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «DS_KIDDE_ZLSM_ME_202604_ES_c3d9.pdf»
      doc `DS_KIDDE_ZLSM_ME_202604_ES_c3d9.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo
      el juez propone otra grafía: `9-30520`
- [ ] `kidde:zlsm-me-zlsm-mr` (ZLSM-ME/ZLSM-MR)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «MI_KIDDE_ZLSM_ME_202604_ING_29a1.pdf»
      doc `MI_KIDDE_ZLSM_ME_202604_ING_29a1.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo
      el juez propone otra grafía: `MiniLaser Expansion Housing`
- [ ] `morley:efs-em-8` (EFS/EM 8)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Panel de control de incendios de 8 zonas EFS/EM 8 # Manual de instalación, puesta en…»
      doc `MS8.pdf` · estrictas doc 9 / global 18 en 2 docs · otros motivos: ambiguedad:mismo-termino-propuesto-a-dos-fabricantes
- [ ] `notifier:conv232-485` (CONV232/485)
      **PRODUCTO_REAL** · rol REFERENCIA_COMERCIAL · confianza alta · cita ✓ «Convertidor RS232 a RS485/422 para TG a centrales ID3000 - punto a punto. Ref.: CONV…»
      doc `TIDT110.pdf` · estrictas doc 3 / global 4 en 2 docs
- [ ] `notifier:efs-em-8` (EFS/EM 8)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Panel de control de incendios de 8 zonas EFS/EM 8 # Manual de instalación, puesta en…»
      doc `FS8` · estrictas doc 9 / global 18 en 2 docs · otros motivos: ambiguedad:mismo-termino-propuesto-a-dos-fabricantes
- [ ] `notifier:nx2-r-r-y-nx5-r-r` (NX2/R/R y NX5/R/R)
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «| 1 | → | (−) | NX2/R/R y NX5/R/R»
      doc `EMA24RS2R_NX2y5-R-R` · estrictas doc 1 / global 1 en 1 doc · otros motivos: juez:confianza-media; juez:propone-otra-grafia(NX2/R/R; NX5/R/R)
      el juez propone otra grafía: `NX2/R/R; NX5/R/R`
- [ ] `notifier:pul-d-ext` (PUL-D/EXT)
      **PRODUCTO_REAL** · rol REFERENCIA_COMERCIAL · confianza media · cita ✗ «PUL-D/EXT 1035 [CE mark logo] Honeywell Life Safety Iberia, SL.»
      doc `PUL-DEXT_Instrucciones multi` · estrictas doc 1 / global 1 en 1 doc · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo
- [ ] `notifier:pul-p-ext` (PUL-P/EXT)
      **PRODUCTO_REAL** · rol REFERENCIA_COMERCIAL · confianza alta · cita ✓ «PUL-P/EXT** 1035 CE Honeywell Life Safety Iberia, SL.»
      doc `PUL-PEXT_Instrucciones multi` · estrictas doc 1 / global 1 en 1 doc
- [ ] `sensitron:sts-ckd` (STS/CKD+)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Manual de instrucciones # STS/CKD+»
      doc `MT4508-CKDPLUS REV 0.pdf` · estrictas doc 1 / global 4 en 4 docs
- [ ] `spectrex:20-20mi` (20/20MI)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «CONFIGURACIÓN DEL DETECTOR DE LLAMA 20/20MI»
      doc `MADT696_01` · estrictas doc 5 / global 50 en 3 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `spectrex:20-20r` (20/20R)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «DETECTOR DE LLAMA DE UN ÚNICO ESPECTRO INFRARROJO ## Modelo «20/20R»»
      doc `MNDT713.pdf` · estrictas doc 2 / global 5 en 2 docs

**riesgo-lexico:acronimo-corto-sin-digitos** — 17

- [ ] `morley:miw` (MIW)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Serie MIW Equipos Vía Radio Analógicos»
      doc `MIW-al-sustituir-las-baterias-de-un-equipo-se…` · estrictas doc 1 / global 70 en 11 docs
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# ACTUALIZACIÓN DE HISTÓRICO DEL TG El programa ActualizaHis.exe es el encargado de…»
      doc `Actulización histórico TG` · estrictas doc 9 / global 164 en 18 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# TG - He cambiado el nombre del plano y ahora el plano y los equipos han desapareci…»
      doc `Al cambiar-el-nombre-del-plano-a desaparecido…` · estrictas doc 6 / global 87 en 11 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «¿Como solucionar la incidencia *"TABLE IS FULL"* en el software gráfico *TG*?»
      doc `Como-solucionar-la-incidencia-TABLE-IS-FULL-e…` · estrictas doc 5 / global 76 en 14 docs
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «Poner la contraseña por defecto del programa de gestión gráfica TG»
      doc `Poner-la-contraseña-por-defecto-del-programa-…` · estrictas doc 4 / global 90 en 3 docs · otros motivos: juez:confianza-media; sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Puedo migrar / actualizar un TG versión 5.XX a versión 7.XX»
      doc `Requisitos-del-PC-para-el-TG-Version-5-XX.pdf` · estrictas doc 3 / global 96 en 4 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «el programa gráfico TG funciona en modo EDITOR y no habrá comunicación con las centr…»
      doc `TG-ATENCION-El-sistema-no-encuentra-la-protec…` · estrictas doc 6 / global 23 en 9 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «¿Como ampliar una/as licencia/s de un TG?»
      doc `TG-Como ampliar-licencias.pdf` · estrictas doc 8 / global 93 en 2 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Acceda al programa TG con una clave que le permita alcanzar al menú de **Configuraci…»
      doc `TG-Como-borrar-elementos-de-un-plano.pdf` · estrictas doc 3 / global 162 en 11 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Después de instalar el programa gráfico (en adelante TG) debe proceder a la generaci…»
      doc `TG-Como-cargar-añadir-planos.pdf` · estrictas doc 9 / global 115 en 4 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «¿Como se debe de hacer una copia de seguridad del proyecto para la versión 7 del TG?»
      doc `TG-Como-hacer-una-copia-de-seguridad-del-proy…` · estrictas doc 7 / global 148 en 20 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Puede realizar estas indicaciones con el TG arrancado, tanto en Modo Editor como en…»
      doc `TG-Como-puedo-ver-los-equipos-que-no-estan-re…` · estrictas doc 3 / global 109 en 14 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «debe acceder a la utilidad que acompaña al software gráfico TG»
      doc `TG-Como-reparar-Historico-Provisional.pdf` · estrictas doc 12 / global 85 en 12 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Cierre el programa gráfico **TG**»
      doc `TG-Que-clave-tiene-si-se-instala-en-idioma-In…` · estrictas doc 7 / global 120 en 9 docs
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «# TG - SE HA SUPERADO EL MÁXIMO DE LICENCIAS.»
      doc `TG-SE-HA-SUPERADO-EL-MAXIMO-DE-LICENCIAS.pdf` · estrictas doc 9 / global 53 en 13 docs · otros motivos: sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:tg` (TG)
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✗ «Programa gráfico de gestión, tipo TG de Notifier»
      doc `TG-como-se-configuran-sonidos-ante-eventos.pdf` · estrictas doc 2 / global 92 en 6 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo; sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo
- [ ] `morley:vsn` (VSN)
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza media · cita ✗ «VSN-RP1R-PLUS2, VSN-Plus y VSN-2PLUS»
      doc `No-funcionan-las-teclas-de-la-central-VSN.pdf` · estrictas doc 2 / global 119 en 19 docs · otros motivos: juez:confianza-media; cita:no-verificada-a-texto-completo; contradiccion:artefacto-con-fuerte-senal-de-sujeto

**juez:confianza-media** — 14

- [ ] `aritech:2x-a-tactil` (2X-A Táctil)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «quick installation information for your 2X-A control panel»
      doc `00-3280-507-4003-03_r003_2x-a_series_quick_in…` · estrictas doc 0 / global 0 en 0 docs · otros motivos: atencion:etiqueta-270-chunks-sin-aparecer-verbatim
      el juez propone otra grafía: `2X-A`
- [ ] `kidde:kit-2x-afr-c-09` (KIT 2X-AFR-C-09)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «KIDDE™ COMMERCIAL # 2X-AFR-C ## Repetidor de incendios direccionable - Compacto»
      doc `DS_KIDDE_KIT_2X_AFR_C_09_202412_ES_c976.pdf` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `2X-AFR-C`
- [ ] `kidde:zlsm-md` (ZLSM-MD)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «## Kidde MiniLaser»
      doc `DS_KIDDE_ZLSM_MD_202604_ES_8d42.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: atencion:etiqueta-87-chunks-sin-aparecer-verbatim
      el juez propone otra grafía: `MiniLaser`
- [ ] `kidde:zlsm-md` (ZLSM-MD)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «MI_KIDDE_ZLSM_MD_202604_ING_1875.pdf»
      doc `MI_KIDDE_ZLSM_MD_202604_ING_1875.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: cita:no-verificada-a-texto-completo; atencion:etiqueta-87-chunks-sin-aparecer-verbatim
      el juez propone otra grafía: `MiniLaser`
- [ ] `kidde:zlsm-mr` (ZLSM-MR)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «MI_KIDDE_ZLSM_MR_202604_ING_252a.pdf»
      doc `MI_KIDDE_ZLSM_MR_202604_ING_252a.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: cita:no-verificada-a-texto-completo; ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `MiniLaser I/O Functional Module`
- [ ] `morley:fl-20` (FL-20)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✓ «La serie LT MI-FL20 forma parte de la familia Fire Alarm Aspiration Sensing Technolo…»
      doc `I56-3956-201_PT Morley Loop FAAST LT QIG.pdf` · estrictas doc 0 / global 0 en 3 docs
      el juez propone otra grafía: `FAAST LT (serie FL20)`
- [ ] `morley:morley-ias-max` (Morley-IAS Max)
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «Documentación Morley-IAS Max https://buildings.honeywell.com/gb/en/lp/morleymaxtech»
      doc `Docs Morley-IAS Max - QR` · estrictas doc 1 / global 1 en 1 doc
- [ ] `notifier:hssd` (HSSD)
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza media · cita ✓ «Los **detectores HSSD** deben montarse fuera de la cámara frigorífica»
      doc `MADT731_01` · estrictas doc 18 / global 70 en 3 docs · otros motivos: contradiccion:artefacto-con-fuerte-senal-de-sujeto
- [ ] `notifier:madt-606` (MADT-606)
      **ARTEFACTO_EXTRACCION** · rol CODIGO_DE_DOCUMENTO · confianza media · cita ✗ «Documento de origen: MADT606»
      doc `MADT606` · estrictas doc 0 / global 0 en 0 docs · otros motivos: cita:no-verificada-a-texto-completo
- [ ] `notifier:nfs-32-001` (NFS-32-001)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza media · cita ✗ «D1056-1_NFXI-BS-BSF»
      doc `D1056-1_NFXI-BS-BSF` · estrictas doc 0 / global 0 en 0 docs · otros motivos: cita:no-verificada-a-texto-completo; ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `NFXI-BS-BSF`
- [ ] `notifier:repetidor-serie-1000` (REPETIDOR SERIE 1000)
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «# Repetidor de la Serie 1000 Fire alarm control panel»
      doc `MNDT213.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: contradiccion:producto-real-sin-mencion-estricta-ni-en-mayusculas; juez:propone-otra-grafia(Repetidor de la Serie 1000)
      el juez propone otra grafía: `Repetidor de la Serie 1000`
- [ ] `notifier:securnet-plus-02` (SECURNET PLUS 02)
      **ARTEFACTO_EXTRACCION** · rol CODIGO_DE_DOCUMENTO · confianza media · cita ✓ «**ADEMDUM** | SECURNET PLUS 02<br/>Fecha: 19 / 03 / 2001»
      doc `MADT575_02` · estrictas doc 1 / global 1 en 1 doc
      el juez propone otra grafía: `SECURNET PLUS`
- [ ] `spectrex:40-40l` (40-40L)
      **PRODUCTO_REAL** · rol TITULO · confianza media · cita ✓ «Modelo S40/40L, LB y S40/40L4, L4B»
      doc `MNDT722_40-40L` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:propone-otra-grafia(S40/40L)
      el juez propone otra grafía: `S40/40L`
- [ ] `xtralis:vesda` (VESDA)
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza media · cita ✗ «La Pantalla de reconocimiento inmediato del detector VESDA VLF muestra los niveles d…»
      doc `HSLI_IN_020_Tabla equivalencia TG` · estrictas doc 3 / global 91 en 7 docs · otros motivos: cita:no-verificada-a-texto-completo; contradiccion:artefacto-con-fuerte-senal-de-sujeto
      el juez propone otra grafía: `VESDA-VLF/VLF-250 (y otros modelos de la gama VESDA)`

**obsoleta:doc-fuente-no-activo** — 7

- [ ] `notifier:ir3-s20` (IR³ S20)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza baja · cita ✗ sin cita en el recibo
      doc `MNDT694` · estrictas doc 0 / global 0 en 0 docs · otros motivos: obsoleta:el-doc-ya-no-declara-ese-product_model; juez:confianza-baja; cita:no-verificada-a-texto-completo
      el juez propone otra grafía: `S20/20SI`
- [ ] `notifier:smart-twin` (SMART TWIN)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «INSTRUCCIÓN TÉCNICA PARA LOS DETECTORES SMART TWIN»
      doc `MNDT606` · estrictas doc 0 / global 1 en 1 doc
- [ ] `notifier:spectrex` (SPECTREX)
      **ARTEFACTO_EXTRACCION** · rol NOMBRE_DE_FABRICANTE_O_GAMA · confianza alta · cita ✓ «SPECTREX INC. ofrece una garantía al Comprador/Distribuidor sobre los componentes su…»
      doc `MNDT690` · estrictas doc 0 / global 145 en 13 docs · otros motivos: obsoleta:el-doc-ya-no-declara-ese-product_model; contradiccion:artefacto-con-fuerte-senal-de-sujeto
- [ ] `notifier:tg-notifier` (TG-NOTIFIER)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «TG NOTIFIER VER. 3.2 NOTIFIER ESPAÑA presenta una nueva versión de su programa de gr…»
      doc `MNDT951_v5-87` · estrictas doc 0 / global 42 en 13 docs · otros motivos: obsoleta:el-doc-ya-no-declara-ese-product_model; colision:id-ya-existe-en-el-catalogo-gobernado
- [ ] `spectrex:20-20i` (20/20I)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «El Modelo 20/20I de Spectrex es un detector de llama de triple espectro infrarrojo d…»
      doc `MNDT700_C` · estrictas doc 0 / global 9 en 4 docs · otros motivos: ambiguedad:termino-multi-modelo; fabricante:discrepa-de-la-ficha-del-documento
- [ ] `spectrex:20-20lb` (20/20LB)
      **PRODUCTO_REAL** · rol TABLA_DE_MODELOS · confianza alta · cita ✓ «el modelo 20/20LB incluye la opción de Prueba Incorporada (BIT), mientras que el 20/…»
      doc `MNDT720` · estrictas doc 0 / global 13 en 3 docs · otros motivos: obsoleta:el-doc-ya-no-declara-ese-product_model; ambiguedad:termino-multi-modelo; fabricante:discrepa-de-la-ficha-del-documento
- [ ] `spectrex:20-20ub` (20/20UB)
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
      **NORMA_O_CERTIFICACION** · rol FRASE_TECNICA · confianza alta · cita ✓ «French Fire Sound AFNOR<br/>NFS 32-001»
      doc `D838-1_kac sounders` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `NF S 32-001`

**atencion:etiqueta-270-chunks-sin-aparecer-verbatim** — 2

- [ ] `aritech:2x-a-tactil` (2X-A Táctil)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «This document lists the products compatible for use with your 2X-A Series fire alarm…»
      doc `bcn-3100035-en_r006_2x-a_series_addressable_c…` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `2X-A Series`
- [ ] `aritech:2x-a-tactil` (2X-A Táctil)
      **ARTEFACTO_EXTRACCION** · rol NO_APARECE · confianza alta · cita ✓ «2X-A and ZP2-A Series Addressable Control Panel Compatibility List (900 Series Proto…»
      doc `bcn-3100036-en_r002_2x-a_and_zp2-a_series_add…` · estrictas doc 0 / global 0 en 0 docs
      el juez propone otra grafía: `2X-A`

**colision:el-texto-ya-es-alias-de-otro-producto** — 2

- [ ] `notifier:stratos-hssd` (STRATOS HSSD)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «*STRATOS* HSSD® # DETECTOR DE HUMO DE # ALTA SENSIBILIDAD»
      doc `MNDT730.pdf` · estrictas doc 0 / global 0 en 4 docs
      el juez propone otra grafía: `Stratos-HSSD`
- [ ] `notifier:stratos-hssd` (STRATOS HSSD)
      **PRODUCTO_REAL** · rol TITULO · confianza alta · cita ✓ «Central SENSENET (Stratos-HSSD)»
      doc `MNDT730P.pdf` · estrictas doc 0 / global 0 en 4 docs
      el juez propone otra grafía: `Stratos-HSSD`

**contradiccion:artefacto-con-fuerte-senal-de-sujeto** — 2

- [ ] `morley:mie-ma-100` (MIE-MA-100)
      **ARTEFACTO_EXTRACCION** · rol CODIGO_DE_DOCUMENTO · confianza alta · cita ✓ «MIE-MA-100_01_C 27/07/04 Morley-IAS ESPAÑA 1 de 4»
      doc `MIE-MA-100_01.pdf` · estrictas doc 4 / global 8 en 2 docs
- [ ] `xtralis:vesda` (VESDA)
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
      **NO_DECIDIBLE** · rol NO_APARECE · confianza media · cita ✓ «AIRSENSE # 9-30521 **Módulo funcional de entrada/salida MiniLaser**»
      doc `DS_KIDDE_ZLSM_MR_202604_ES_6a09.pdf` · estrictas doc 0 / global 0 en 0 docs · otros motivos: juez:confianza-media; ambiguedad:veredictos-discordantes-para-el-mismo-id
      el juez propone otra grafía: `9-30521`

**sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo** — 1

- [ ] `kidde:ke-dp3121b` (KE-DP3121B)
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
