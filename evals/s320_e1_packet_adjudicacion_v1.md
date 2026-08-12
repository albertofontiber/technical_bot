# s320 E1 — Packet de ADJUDICACIÓN (sentada; generado 20260812T195105Z)

Lo escrito sin ti (con recibos): 26 altas tier-A + 11 reconciliaciones de
id stale — sonda PRE/POST PASS (26/26 flips esperados), catálogo válido,
109 tests verdes. TODO lo de este packet requiere tu ojo; nada entra solo.

## §1 — COLISIONES de identidad (49) — posibles docs DUPLICADOS

El doc_map apunta a un document_id que SIGUE VIVO en documents, pero el
documento activo actual con ese filename tiene OTRO id → dos filas activas
para el mismo manual (clase nueva; puede exigir supersede o borrado).
Decisión por fila: [mantener ambos / marcar viejo superseded / investigar].

- [ ] `33976_13_vesda-e_vep-a00-p_product_guide_a4_spanish_lores` — id mapa 23ff1fcf… (vivo como: 33976_13_VESDA-E_VEP-A00-P_Product_Guide_A4_Spanish_lores) vs id actual b22fdb7f… · tier b
- [ ] `mndt1300_e` — id mapa 7268b1ad… (vivo como: MNDT1300_E) vs id actual d61cc3d7… · tier c
- [ ] `mndt1300i_e` — id mapa a05f27f7… (vivo como: MNDT1300I_E) vs id actual a9a45a96… · tier c
- [ ] `mndt150` — id mapa 3e7328bf… (vivo como: MNDT150) vs id actual d917a95d… · tier a
- [ ] `mndt250` — id mapa 309b9f8a… (vivo como: MNDT250) vs id actual ee4a01b8… · tier a
- [ ] `mndt255` — id mapa 8595c7c4… (vivo como: MNDT255) vs id actual afacdf35… · tier a
- [ ] `mndt260` — id mapa cf07a74d… (vivo como: MNDT260) vs id actual 446da5f5… · tier a
- [ ] `mndt350` — id mapa 0b90a14c… (vivo como: MNDT350) vs id actual 2d7f3a79… · tier c
- [ ] `mndt390` — id mapa 609f0e11… (vivo como: MNDT390) vs id actual 49a08cd1… · tier a
- [ ] `mndt400` — id mapa 996551c8… (vivo como: MNDT400) vs id actual c604426a… · tier c
- [ ] `mndt402` — id mapa 83763f33… (vivo como: MNDT402) vs id actual 3a58b47d… · tier c
- [ ] `mndt410` — id mapa 65a37e17… (vivo como: MNDT410) vs id actual 5403c7ed… · tier c
- [ ] `mndt440` — id mapa 351ff649… (vivo como: MNDT440) vs id actual 79869dab… · tier a
- [ ] `mndt500` — id mapa 643e3377… (vivo como: MNDT500) vs id actual 90787236… · tier b
- [ ] `mndt503` — id mapa 9ccb9c98… (vivo como: MNDT503) vs id actual acf63276… · tier b
- [ ] `mndt506` — id mapa 1cd40961… (vivo como: MNDT506) vs id actual f2a27fb6… · tier b
- [ ] `mndt515` — id mapa b6169b43… (vivo como: MNDT515) vs id actual bfb0fed7… · tier b
- [ ] `mndt520` — id mapa 621aa70f… (vivo como: MNDT520) vs id actual 3493f571… · tier c
- [ ] `mndt530p` — id mapa a3845c17… (vivo como: MNDT530P) vs id actual 754f1b80… · tier a
- [ ] `mndt575` — id mapa 7e554fdb… (vivo como: MNDT575) vs id actual 6c784967… · tier c
- [ ] `mndt605` — id mapa 12d9af3e… (vivo como: MNDT605) vs id actual c54c20a4… · tier c
- [ ] `mndt607` — id mapa 9c69590f… (vivo como: MNDT607) vs id actual f478ca19… · tier c
- [ ] `mndt615` — id mapa 700af1a7… (vivo como: MNDT615) vs id actual c4f3d893… · tier b
- [ ] `mndt625` — id mapa a798da74… (vivo como: MNDT625) vs id actual 7601da55… · tier c
- [ ] `mndt626` — id mapa 25b925bd… (vivo como: MNDT626) vs id actual 0ef10ac7… · tier c
- [ ] `mndt635` — id mapa 89b21f27… (vivo como: MNDT635) vs id actual 359934f9… · tier c
- [ ] `mndt646_smart3g toxic_sp-en` — id mapa 43436831… (vivo como: MNDT646_SMART3G toxic_SP-EN) vs id actual eb4f831e… · tier c
- [ ] `mndt650` — id mapa c84ca057… (vivo como: MNDT650) vs id actual be99c95b… · tier c
- [ ] `mndt655` — id mapa 537879d2… (vivo como: MNDT655) vs id actual 12278b1f… · tier c
- [ ] `mndt741` — id mapa 2fc17b63… (vivo como: MNDT741) vs id actual 53dc8e94… · tier c
- [ ] `mndt742p_f` — id mapa 9c595e46… (vivo como: MNDT742P_F) vs id actual 16aa7584… · tier c
- [ ] `mndt744i_b` — id mapa 80789d8b… (vivo como: MNDT744I_B) vs id actual 7cb57a84… · tier a
- [ ] `mndt951i_v7-1` — id mapa 0beb5d94… (vivo como: MNDT951I_v7-1) vs id actual 9600e30e… · tier c
- [ ] `mndt954` — id mapa 48a64d46… (vivo como: MNDT954) vs id actual a8bb21cf… · tier c
- [ ] `mndt960i` — id mapa 18429c41… (vivo como: MNDT960I) vs id actual c295d7f9… · tier a
- [ ] `mpdt170` — id mapa 890d5cf6… (vivo como: MPDT170) vs id actual 80b23534… · tier a
- [ ] `mpdt212` — id mapa 3413c8ee… (vivo como: MPDT212) vs id actual ef245515… · tier c
- [ ] `mpdt230` — id mapa 6d46b4a2… (vivo como: MPDT230) vs id actual 3e4bd0bb… · tier a
- [ ] `mpdt280` — id mapa 228a47c5… (vivo como: MPDT280) vs id actual e6ccaa2e… · tier c
- [ ] `mpdt281` — id mapa 3a7e439f… (vivo como: MPDT281) vs id actual 932ac246… · tier a
- [ ] `mpdt951_v5-87` — id mapa 7c2bdff2… (vivo como: MPDT951_v5-87) vs id actual 0903db56… · tier c
- [ ] `nco-10-multinglingual` — id mapa b7cb94d1… (vivo como: NCO-10-multinglingual) vs id actual c2ae8cae… · tier a
- [ ] `pan_avd1` — id mapa bb36bddd… (vivo como: PAN_AVD1) vs id actual 7966c099… · tier c
- [ ] `rp1r - man ita r.a2` — id mapa 6972bec7… (vivo como: RP1R - MAN ITA r.A2) vs id actual 03cf3cca… · tier b
- [ ] `smart 2_mt251_ita-eng` — id mapa 2f3536bc… (vivo como: Smart 2_MT251_Ita-Eng) vs id actual 0d4e7b1a… · tier a
- [ ] `tg-1020-tec` — id mapa 4682b6f7… (vivo como: TG-1020-TEC) vs id actual 288e3202… · tier b
- [ ] `tg-1020-usu` — id mapa abb55e52… (vivo como: TG-1020-USU) vs id actual 2ad4e69f… · tier b
- [ ] `tidt104` — id mapa c39c0456… (vivo como: TIDT104) vs id actual 2c8e62dd… · tier a
- [ ] `tidt108` — id mapa 3737c7f5… (vivo como: TIDT108) vs id actual 2b925c7b… · tier a

## §2 — Tier B: resolución ambigua (67)

Paraguas/homónimo/split-parcial/OEM — la traza de resolve por token está
en `evals/s320_e1_docmap_derivacion_v2_detalle.json`. Decisión por fila:
[ids correctos → entrada doc_map / otra cosa].

- [ ] `00-3280-508-4009-03_r003_2x-a_series_quick_operation_guide_e` · pm `2X-A/2X-AT-F2/2X-AT-F2-FB` · vías exact+none · ids kidde:2x-at-f2, kidde:2x-at-f2-fb
- [ ] `33976_13_vesda-e_vep-a00-p_product_guide_a4_spanish_lores` · pm `VESDA-E-VEP/VEP-A00-P/VEP-A00` · vías alias+exact+none · ids xtralis:vep-a00-1p, xtralis:vep-a00-p
- [ ] `4188-1132-pt issue 4_04_2025-qref` · pm `INSPIRE E10/E15` · vías exact+homonimo-candidate · ids notifier:inspire-e10
- [ ] `996-130-000-3 manuel d'utilisation zx_hlsi` · pm `ZX` · vías homonimo · ids morley:zx2e, morley:zx2se, morley:zx50, morley:zxae
- [ ] `asd harsh environments_sp` · pm `FAAST` · vías paraguas · ids morley:mi-fl2011ei, morley:mi-fl2012ei, morley:mi-fl2022ei, notifier:faast-8100e
- [ ] `averia-de-resistencia-de-baterias-en-central-dxc` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `bcn-3100019-es_r002_nc_series_fire_alarm_control_panel_quick` · pm `NC/NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4` · vías exact+none · ids kidde:nc-pf2, kidde:nc-pf2-sc, kidde:nc-pf4, kidde:nc-pf4-sc
- [ ] `bcn-3100020-es_r002_nc_series_fire_alarm_control_panel_quick` · pm `NC/NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4` · vías exact+none · ids kidde:nc-pf2, kidde:nc-pf2-sc, kidde:nc-pf4, kidde:nc-pf4-sc
- [ ] `con-que-sistema-operativo-es-compatible-el-programa-de-la-dx` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `con-que-sistema-operativo-es-compatible-el-programa-de-la-zx` · pm `ZX/DX` · vías homonimo+none · ids morley:zx2e, morley:zx2se, morley:zx50, morley:zxae
- [ ] `ds_kidde_2x_at_fr_fb_s_202602_es_4276` · pm `2X-AT-FR-FB-S` · vías exact · ids kidde:2x-at-fr-fb-s
- [ ] `ds_kidde_2x_at_fr_s_202602_es_904a` · pm `2X-AT-FR-S` · vías exact · ids kidde:2x-at-fr-s
- [ ] `ds_kidde_2x_at_fr_s_98dc` · pm `2X-AT-FR-S` · vías exact · ids kidde:2x-at-fr-s
- [ ] `dxc-conexion-como-solucionar-la-averia-de-estado-inconsisten` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-configuracion-de-la-tarjeta-232-aislada-para-comunicarse` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-connexion-ajuste-contraste-display` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-connexion-averia-f-alimentacion-externa` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-connexion-averia-nueva-f-alimentacion-externa` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-connexion-como-solucionar-la-averia-de-ent-placa-1-o-2` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-connexion-compatibilidad-de-programas-con-versiones` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-no-puedo-comunicar-con-la-central` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-opciones-de-disparo-de-programas-matrices` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-porque-al-activan-elementos-en-alarma-no-se-enciende-su-` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-puedo-anular-la-clave-de-usuario-y-acceder-directamente-` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-puedo-cambiar-la-clave-de-nivel-3` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-referencias-repuestos` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-tipos-abreviaturas-de-equipos` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc-tipos-de-accion-para-entradas` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc_connexion averia-de-resistencia-de-baterias` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `dxc_guia de usuario_multiling` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `eventos-averias-de-equipos-en-dxc` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `finales-de-linea-de-las-centrales-convencionales` · pm `NFS2/NFS4/NFS8/VSN2-LT/VSN4-LT/VSN8-LT/V` · vías exact+none · ids morley:vsn-4-plus, morley:vsn-8-plus, morley:vsn12-lt, morley:vsn2-lt
- [ ] `g_inst_kidde_nc_pfx_202502_es_ac3d` · pm `NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4-SC` · vías exact · ids kidde:nc-pf2, kidde:nc-pf2-sc, kidde:nc-pf4, kidde:nc-pf4-sc
- [ ] `g_uso_kidde_nc_pfx_202502_es_99d2` · pm `NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4-SC` · vías exact · ids kidde:nc-pf2, kidde:nc-pf2-sc, kidde:nc-pf4, kidde:nc-pf4-sc
- [ ] `gr_kidde_2x_at_fr_fb_s_27cf` · pm `2X-AT-FR-FB-S/2X-AT-FR-S` · vías exact · ids kidde:2x-at-fr-fb-s, kidde:2x-at-fr-s
- [ ] `hd_ke_dt3101w_hab_202407_es_30e0` · pm `KE-DT3101W-HAB` · vías exact · ids kidde:ke-dt3101w-hab
- [ ] `hlsi-ti-001` · pm `RP1r` · vías homonimo · ids notifier:rp1r-supra
- [ ] `hlsi-ti-007_vsn-4rel` · pm `VSN-4REL` · vías exact · ids notifier:vsn-4rel
- [ ] `inc___doci_141_gu__a_r__pida_kidde_nc_pf__1__fcb9` · pm `NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4-SC` · vías exact · ids kidde:nc-pf2, kidde:nc-pf2-sc, kidde:nc-pf4, kidde:nc-pf4-sc
- [ ] `ma-dt-1160` · pm `ExitPoint` · vías alias · ids systemsensor:pf24v
- [ ] `mi_kidde_2x_at_f2_fb_07d4` · pm `2X-AT-F2/2X-AT-F2-FB/2X-AT-FR-FB-S/2X-AT` · vías exact · ids kidde:2x-at-f2, kidde:2x-at-f2-fb, kidde:2x-at-fr-fb-s, kidde:2x-at-fr-s
- [ ] `mi_kidde_ke_dp312x_snx_202503_es_acf9` · pm `KE-DP3120W/KE-DP3120W-SN/KE-DP3120W-SNV/` · vías exact+none · ids kidde:ke-dp3120w
- [ ] `mi_kidde_ke_dp312x_snx_202512_es_242d` · pm `KE-DP3120W/KE-DP3120W-SN/KE-DP3120W-SNV/` · vías exact+none · ids kidde:ke-dp3120w
- [ ] `mi_kidde_ke_io3144_631e` · pm `KE-IO3144/KE-IU3110` · vías exact+none · ids kidde:ke-io3144
- [ ] `mi_kidde_nc_pfx_202502_es_62f8` · pm `NC-PF2/NC-PF4/NC-PF8/NC-PF2-SC/NC-PF4-SC` · vías exact · ids kidde:nc-pf2, kidde:nc-pf2-sc, kidde:nc-pf4, kidde:nc-pf4-sc
- [ ] `mie-mi-120p` · pm `VSN 2-4` · vías alias · ids morley:vsn2
- [ ] `mie-mi-340_1` · pm `EXP-051` · vías exact · ids morley:exp-051
- [ ] `mie-mi-431rv2_1` · pm `ZXR50A/ZXR50P` · vías exact · ids morley:zxr50a, morley:zxr50p
- [ ] `miemu520p` · pm `Dimension` · vías paraguas · ids —
- [ ] `mndt1160` · pm `EXITPOINT` · vías alias · ids systemsensor:pf24v
- [ ] `mndt420` · pm `LDM/LDM-32/LDM-E32/LDM-R32/LDM-E32F/LDM-` · vías exact+none · ids firelite:ldm-32f, notifier:ldm-32, notifier:ldm-e32, notifier:ldm-r32
- [ ] `mndt500` · pm `G-500/G-500-S/G-500-2LR` · vías exact+none+paraguas · ids notifier:g-500-2lr, notifier:g-500-s-32, notifier:g-500-s-64
- [ ] `mndt503` · pm `G-100/G-100-R8/G-100-2SE` · vías exact+paraguas · ids notifier:g-100-2se, notifier:g-100-4, notifier:g-100-8, notifier:g-100-r8
- [ ] `mndt506` · pm `G-100-R` · vías paraguas · ids notifier:g-100-r-12, notifier:g-100-r-24, notifier:g-100-r16, notifier:g-100-r8
- [ ] `mndt515` · pm `PL4` · vías homonimo-candidate · ids —
- [ ] `mndt615` · pm `SMART 2` · vías exact · ids sensitron:smart-2
- [ ] `morley-se-pueden-pasar-programaciones-de-zx-y-dimension-a-co` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `mu_kidde_2x_at_fr_fb_s_6c31` · pm `2X-AT-FR-FB-S/2X-AT-FR-S` · vías exact · ids kidde:2x-at-fr-fb-s, kidde:2x-at-fr-s
- [ ] `niveles-de-control-de-acceso-de-la-central-dxc-conexion` · pm `DXc` · vías paraguas · ids morley:dxc1, morley:dxc2, morley:dxc4
- [ ] `no-puedo-hacer-rearme-o-silenciar-sirenas-en-la-vsn-lt` · pm `VSN-LT` · vías paraguas · ids morley:vsn12-lt, morley:vsn2-lt, morley:vsn4-lt, morley:vsn8-lt
- [ ] `osid-es-necesario-resetear-la-barrera-de-forma-externa` · pm `OSID` · vías alias · ids morley:mi-osi-rie
- [ ] `pl4_mt574e_eng` · pm `PL4` · vías homonimo-candidate · ids —
- [ ] `rp1r - man ita r.a2` · pm `RP1r` · vías homonimo · ids notifier:rp1r-supra
- [ ] `tg-1020-tec` · pm `TG-1020` · vías exact · ids desico:tg-1020
- [ ] `tg-1020-usu` · pm `TG-1020` · vías exact · ids desico:tg-1020
- [ ] `ucip-como-enviar-datos-de-equipos-y-no-solo-eventos-de-zonas` · pm `UCIP` · vías exact · ids notifier:ucip
- [ ] `ucip-que-datos-necesito-de-la-receptora` · pm `UCIP` · vías exact · ids notifier:ucip

## §3 — Tier C: productos NUEVOS propuestos como candidate (133)

Draft en `evals/s320_e1_candidates_draft.jsonl` (FUERA del catálogo hasta
tu OK por lotes). candidate=true = no-consumible aunque entren. Por marca:

### Notifier (41)
- [ ] `AIRSENSE` ← `madt731_04`
- [ ] `Airsense` ← `tidt109`
- [ ] `CLSS Configuration Tool` ← `4188-1124-pt issue 4_01-2026_to`
- [ ] `CONV232/485` ← `tidt110`
- [ ] `EFS/EM 8` ← `fs8`
- [ ] `ETDT-312` ← `etdt312`
- [ ] `ETDT-314` ← `etdt314`
- [ ] `FAAST LT` ← `asd cold environments_sp`
- [ ] `FAAST-LT` ← `faast-lt-como-obtener-el-historico-del-equipo`
- [ ] `HSSD` ← `madt731_01`
- [ ] `ID1000` ← `tidt066_copia`
- [ ] `ID²NET` ← `madt190p_01_c`
- [ ] `ID²NET` ← `madt190_01`
- [ ] `IR³ S20` ← `mndt694`
- [ ] `KIT-GAS` ← `hlsi-mn-627`
- [ ] `LT-200` ← `faast-lt-como-comunicar-con-el-equipo`
- [ ] `MADT-015` ← `madt015_01`
- [ ] `MADT-606` ← `madt606`
- [ ] `MADT-731` ← `madt731_06`
- [ ] `MADT-742` ← `madt742`
- [ ] `MNDT-1202` ← `mndt1202`
- [ ] `MNDT-600` ← `mndt600`
- [ ] `MNDT-701` ← `mndt701`
- [ ] `NFS-32-001` ← `d1056-1_nfxi-bs-bsf`
- [ ] `NFS-32-001` ← `d838-1_kac sounders`
- [ ] `NFXI-BSF-WCH` ← `d 1147-1 brh notifier`
- [ ] `NX2/R/R y NX5/R/R` ← `ema24rs2r_nx2y5-r-r`
- [ ] `PUL-D/EXT` ← `pul-dext_instrucciones multi`
- [ ] `PUL-P/EXT` ← `pul-pext_instrucciones multi`
- [ ] `REPETIDOR SERIE 1000` ← `mndt213`
- [ ] `S20` ← `mndt696`
- [ ] `SECURNET PLUS 02` ← `madt575_02`
- [ ] `SMART TWIN` ← `mndt606`
- [ ] `SPECTREX` ← `mndt690`
- [ ] `STRATOS` ← `madt731_02`
- [ ] `STRATOS HSSD` ← `mndt730`
- [ ] `STRATOS HSSD` ← `mndt730p`
- [ ] `Serie PS` ← `serie ps`
- [ ] `TG-NOTIFIER` ← `mndt951_v5-87`
- [ ] `TIDT-060` ← `tidt060`
- [ ] `TIDT-101` ← `tidt101`

### Kidde (40)
- [ ] `2A-PAK-HPL` ← `ds_kidde_2a_pak_hpl_9085`
- [ ] `2A-PAK-HPL` ← `mi_kidde_2a_pak_hpl_c599`
- [ ] `KE-ASA-AUXR` ← `ds_kidde_ke_asa_auxr_f28f`
- [ ] `KE-DBA-ADPW-KIL` ← `ds_kidde_ke_dba_adpw_kil_202501_ing_c855`
- [ ] `KE-DBA-ADPW-KIL/KE-DBA-ADPW-ZIT` ← `g_inst_kidde_ke_dba_adpw_202502_es_70e7`
- [ ] `KE-DBA-ADPW-ZIT` ← `ds_kidde_ke_dba_adpw_zit_202501_ing_ed63`
- [ ] `KE-DBA-CAPW` ← `hd_ke_dba_capw_202407_ing_d87d`
- [ ] `KE-DBA-IPW` ← `hd_ke_dba_ipw_202407_ing_ffaf`
- [ ] `KE-DBA-IPW` ← `mi_ke_dba_ipw_202407_es_cc56`
- [ ] `KE-DBA-LABW-L1S/KE-DBA-LABW-L2S/KE-DBA-LABW-L3S/KE` ← `hd_ke_dba_labw_lxs_202407_es_2fc1`
- [ ] `KE-DBA-RECW` ← `hd_ke_dba_recw_202407_es_bb2b`
- [ ] `KE-DBA-RECW` ← `mi_ke_dba_recw_202407_es_aacc`
- [ ] `KE-DBA-SKTW` ← `hd_ke_dba_sktw_202407_ing_2da9`
- [ ] `KE-DBA-SKTW` ← `mi_ke_dba_sktw_202407_es_a20b`
- [ ] `KE-DBA-TAGW` ← `hd_ke_dba_tagw_202407_es_4b26`
- [ ] `KE-DM3110R-IP` ← `ds_kidde_ke_dm3110r_ip_202412_es_8165`
- [ ] `KE-DM3110R-KIT` ← `ds_kidde_ke_dm3110r_kit_f3b7`
- [ ] `KE-DM3110R-KIT` ← `mi_kidde_ke_dm3110r_kit_28a2`
- [ ] `KE-DP3021B` ← `hd_ke_dp3021b_202407_es_861a`
- [ ] `KE-DP3021W` ← `hd_ke_dp3021w_202407_es_778e`
- [ ] `KE-DP3121B` ← `hd_ke_dp3121b_202407_es_8c51`
- [ ] `KE-DP3121B/KE-DP3121B-SNV` ← `ds_kidde_ke_dp3121b_snv_202503_es_b5bc`
- [ ] `KE-DP3121W/KE-DP3121W-SN` ← `ds_kidde_ke_dp3121w_sn_202503_es_5938`
- [ ] `KE-DP3121W/KE-DP3121W-SN/KE-DP3121W-SNV` ← `ds_kidde_ke_dp3121w_snv_202503_es_8699`
- [ ] `KE-IU3110` ← `hd_ke_iu3110_202407_es_42d6`
- [ ] `KE-IU3110` ← `mi_ke_iu3110_202407_es_5e36`
- [ ] `KE-IU3111-ZME/KIT 2X-AE1-09` ← `ds_kidde_ke_iu3111_zme_f908`
- [ ] `KE-IU3111-ZME/KIT 2X-AE1-09` ← `mi_ke_iu3111_zme_202407_es_fde1`
- [ ] `KIT 2X-AFR-C-09` ← `ds_kidde_kit_2x_afr_c_09_202412_es_c976`
- [ ] `N-IO-MBX-1/N-IO-MBX-2` ← `ds_kidde_n_io_mbx_1_202505_es_07ca`
- [ ] `N-IO-MBX-1/N-IO-MBX-2` ← `mi_n_io_mbx_x_202505_es__1__1fd1`
- [ ] `N-IO-MBX-2` ← `ds_kidde_n_io_mbx_2_202505_es_b34f`
- [ ] `N-IO-SBX-1G/N-IO-SBX-2G` ← `ds_kidde_n_io_sbx_1g_202505_es_b086`
- [ ] `N-IO-SBX-2G` ← `ds_kidde_n_io_sbx_2g_202505_es_6eb1`
- [ ] `ZLSM-MD` ← `ds_kidde_zlsm_md_202604_es_8d42`
- [ ] `ZLSM-MD` ← `mi_kidde_zlsm_md_202604_ing_1875`
- [ ] `ZLSM-ME/ZLSM-MR` ← `ds_kidde_zlsm_me_202604_es_c3d9`
- [ ] `ZLSM-ME/ZLSM-MR` ← `mi_kidde_zlsm_me_202604_ing_29a1`
- [ ] `ZLSM-MR` ← `ds_kidde_zlsm_mr_202604_es_6a09`
- [ ] `ZLSM-MR` ← `mi_kidde_zlsm_mr_202604_ing_252a`

### Morley (28)
- [ ] `DE-80` ← `tg-cuales-son-los-requisitos-del-pc-para-el-programa`
- [ ] `DXc Connexion` ← `no-puedo-hacer-rearmes-silenciar-sirenas-y-otros-controles-d`
- [ ] `EFS/EM 8` ← `ms8`
- [ ] `FL-20` ← `i56-3956-201_pt morley loop faast lt qig`
- [ ] `MA120` ← `hlsi_ma102_bis2`
- [ ] `MIE-MA-100` ← `mie-ma-100_01`
- [ ] `MIEIN-004` ← `relacion-de-producto-obsoleto-de-morley-ias-by-honeywell`
- [ ] `MIW` ← `miw-al-sustituir-las-baterias-de-un-equipo-se-necesita-progr`
- [ ] `MOD.RS-232` ← `mie-mi-330`
- [ ] `MOD.RS-485` ← `mie-mi-390`
- [ ] `Morley-IAS Max` ← `docs morley-ias max - qr`
- [ ] `TG` ← `actulización histórico tg`
- [ ] `TG` ← `al cambiar-el-nombre-del-plano-a desaparecido-el-plano-y-los`
- [ ] `TG` ← `como-solucionar-la-incidencia-table-is-full-en-el-tg`
- [ ] `TG` ← `poner-la-contraseña-por-defecto-del-programa-de-gestion-graf`
- [ ] `TG` ← `requisitos-del-pc-para-el-tg-version-5-xx`
- [ ] `TG` ← `tg-atencion-el-sistema-no-encuentra-la-proteccion-del-tg`
- [ ] `TG` ← `tg-como ampliar-licencias`
- [ ] `TG` ← `tg-como-borrar-elementos-de-un-plano`
- [ ] `TG` ← `tg-como-cargar-añadir-planos`
- [ ] `TG` ← `tg-como-hacer-una-copia-de-seguridad-del-proyecto`
- [ ] `TG` ← `tg-como-puedo-ver-los-equipos-que-no-estan-representados-en-`
- [ ] `TG` ← `tg-como-reparar-historico-provisional`
- [ ] `TG` ← `tg-que-clave-tiene-si-se-instala-en-idioma-ingles`
- [ ] `TG` ← `tg-se-ha-superado-el-maximo-de-licencias`
- [ ] `TG` ← `tg-como-se-configuran-sonidos-ante-eventos`
- [ ] `VSN` ← `no-funcionan-las-teclas-de-la-central-vsn`
- [ ] `Vision Supra` ← `30012012  tarjetas idiomas vision supra rev a`

### Spectrex (11)
- [ ] `20/20I` ← `mndt700_c`
- [ ] `20/20LB` ← `mndt720`
- [ ] `20/20MI` ← `madt696_01`
- [ ] `20/20R` ← `mndt713`
- [ ] `20/20UB` ← `mndt710_b`
- [ ] `40-40-AIR` ← `guide-40-40-air-shield-p-n-777650-spectrex-en-us-1459942`
- [ ] `40-40I` ← `mndt721_40-40i`
- [ ] `40-40L` ← `mndt722_40-40l`
- [ ] `40-40M` ← `mndt725_40-40m`
- [ ] `40-40R` ← `mndt724_40-40r`
- [ ] `40-40U` ← `mndt723_40-40u`

### Aritech (4)
- [ ] `2X-A` ← `00-3280-507-4009-03_r003_2x-a_series_quick_installation_guid`
- [ ] `2X-A Táctil` ← `00-3280-507-4003-03_r003_2x-a_series_quick_installation_guid`
- [ ] `2X-A Táctil` ← `bcn-3100035-en_r006_2x-a_series_addressable_control_panel_co`
- [ ] `2X-A Táctil` ← `bcn-3100036-en_r002_2x-a_and_zp2-a_series_addressable_contro`

### Xtralis (3)
- [ ] `LT-200` ← `i56-3888-010 faast lt-200 adv guide`
- [ ] `VESDA` ← `cursos formacion_marzo 2026`
- [ ] `VESDA` ← `hsli_in_020_tabla equivalencia tg`

### Fidegas (3)
- [ ] `EL-11` ← `manual-de-usuario-s3-2`
- [ ] `EL-11` ← `manual-de-usuario-s3-ir-y-s-2-ir`
- [ ] `S/2-T1 y S/3-T1` ← `manual-de-usuario-s3-t1-y-s-2-t1`

### Sound Alert (1)
- [ ] `SOME-58` ← `exitpoint- wp eng`

### Sensitron (1)
- [ ] `STS/CKD+` ← `mt4508-ckdplus rev 0`

### Avotec (1)
- [ ] `DOA FJ/CPD` ← `manual rotulo rexd-103_en`

## §3b — Tier C bloqueado por colisión (29)

Resuelve primero su fila de §1 (mismo doc).

## §4 — Revisión humana de pm sucio (4)

El filtro léxico los apartó como no-producto, pero un pm-norma sucio puede
tapar un producto real (caso EMA1224B4R con pm «EN-54-3»):

- [ ] `997-493-002-2` · pm `EN54 2-8 Zone` · marca Notifier
- [ ] `asd in rail transportation applications_es` · pm `MARCH-2011` · marca Notifier
- [ ] `compatibilidad-entre-equipos-notifier-y-morley` · pm `unknown` · marca Morley
- [ ] `d686 ema1224b4r_w ns4r` · pm `EN-54-3` · marca Notifier
