# s91 · F1 bulk — QA de RIESGO (pre-filtrado para Alberto)

products: 1614 (742 candidate) · aliases: 1748 · umbrellas: 15 · **homonyms: 42** (2 gt + 40 candidate auto) · doc_map: 861 · docrel: 1 ⚠ (esperados ~9 pares ES/EN por DEC-066 — la heurística stem+language-DB es conservadora; GAP DECLARADO, mejora en follow-up)

## Namespaces (top): notifier:663, unresolved:200, kidde:152, morley:140, systemsensor:98, pepperl-fuchs:67, xtralis:56, detnov:40, securiton:38, lda:24, aritech:18, menvier:13, patrol:12, kac:12, argus:12

## ⚡ PAQUETE DE DECISIÓN (~25, por blast-radius: homónimos cross-brand con más docs)
Por cada uno: ¿mismo producto rebrandeado (→relación rebrand-of + merge de namespace) o productos distintos (→homónimo con política)?
- `UCIP-GPRS` → ['morley:ucip-gprs', 'notifier:ucip-gprs'] (10 docs)
- `B501AP` → ['morley:b501ap', 'notifier:b501ap', 'systemsensor:b501ap'] (7 docs)
- `VSN-4REL` → ['morley:vsn-4rel', 'notifier:vsn-4rel'] (7 docs)
- `VSN 4 PLUS` → ['morley:vsn-4-plus', 'notifier:vsn4-plus'] (4 docs)
- `REFL20` → ['notifier:refl20', 'systemsensor:refl20'] (4 docs)
- `REFL30` → ['notifier:refl30', 'systemsensor:refl30'] (4 docs)
- `REFL40` → ['notifier:refl40', 'systemsensor:refl40'] (4 docs)
- `REFL50` → ['notifier:refl50', 'systemsensor:refl50'] (4 docs)
- `REFL60` → ['notifier:refl60', 'systemsensor:refl60'] (4 docs)
- `FL2011EI-HS` → ['notifier:fl2011ei-hs', 'systemsensor:fl2011ei-hs'] (3 docs)
- `FL2012EI-HS` → ['notifier:fl2012ei-hs', 'systemsensor:fl2012ei-hs'] (3 docs)
- `FL2022EI-HS` → ['notifier:fl2022ei-hs', 'systemsensor:fl2022ei-hs'] (3 docs)
- `140KIT160` → ['detnov:140kit160', 'firebeam:140kit160'] (3 docs)
- `70KIT140` → ['detnov:70kit140', 'firebeam:70kit140'] (3 docs)
- `VSN12-2Plus` → ['morley:vsn12-2plus', 'notifier:vsn12-2plus'] (3 docs)
- `6500R` → ['notifier:6500r', 'systemsensor:6500r'] (3 docs)
- `6500RS` → ['notifier:6500rs', 'systemsensor:6500rs'] (3 docs)
- `IDR-6A` → ['morley:idr6a', 'notifier:idr-6a'] (3 docs)
- `SMART 2` → ['notifier:smart-2', 'sensitron:smart-2'] (3 docs)
- `Z978` → ['notifier:z978', 'pepperl-fuchs:z978'] (3 docs)
- `APIC` → ['aritech:apic', 'notifier:apic'] (2 docs)
- `2010-2-PAK-RMSDK` → ['edwards:2010-2-pak-rmsdk', 'kidde:2010-2-pak-rmsdk'] (2 docs)
- `MI-DCZM` → ['morley:mi-dczm', 'notifier:mi-dczm'] (2 docs)
- `M710` → ['morley:m710', 'notifier:m710'] (2 docs)
- `M700KAC` → ['kac:m700kac', 'notifier:m700kac'] (2 docs)

---
# BACKLOG (no bloquea F2; se adjudica por lotes)

## brand SIN mapear (añadir a BRAND_MAP) (19)
- `Fire Fighting Enterprises` (doc 0044-033-01 Guia F5000)
- `Golmar` (doc 55348101 Manual Modulo 1 Rele 240VAC MAD-481 )
- `COELBO` (doc AC1460R - CESI 03 ATEX 050)
- `FAAST (Honeywell)` (doc ASD Cold Environments_SP)
- `ENScape` (doc D 1101-7 Sounder Beacon)
- `DELTA` (doc D391 Issue 3 WR2001 )
- `EFS` (doc FS8)
- `FAAST (System Sensor Europe)` (doc I56-6574-005_EN-HS-Stand-Alone-FAAST-LT-200-Q)
- `Calectro` (doc Installation manual_conduct detector)
- `Fire-Lite Alarms` (doc MNDT080)
- `AVOTEC` (doc Manual Rotulo REXD-103_EN)
- `FUEGO` (doc NSRE24)
- `AVOTEC` (doc PAN AVD2_SPANISH)
- `Cranford Controls` (doc SFD-220_Manual_EN)
- `Honeywell Life Safety` (doc Solicitud-asistencia-curso-de-formacion-puest)
- `Desarrollo de Sistemas Integrados de Control, S.L.` (doc TG-1020-TEC)
- `DESICO` (doc TG-1020-USU)
- `Detectortesters` (doc sds0098es_solo_a10_iss_2.1)
- `DXc Connexion` (doc DXc_Connexion Averia-de-resistencia-de-bateri)

## token en VARIOS namespaces (¿rebrand/OEM?) → candidate+homónimo, adjudicar (40)
- `apic` → ['aritech:apic', 'notifier:apic']
- `20102pakrmsdk` → ['edwards:2010-2-pak-rmsdk', 'kidde:2010-2-pak-rmsdk']
- `fl2011eihs` → ['notifier:fl2011ei-hs', 'systemsensor:fl2011ei-hs']
- `fl2012eihs` → ['notifier:fl2012ei-hs', 'systemsensor:fl2012ei-hs']
- `fl2022eihs` → ['notifier:fl2022ei-hs', 'systemsensor:fl2022ei-hs']
- `vsnco` → ['morley:vsn-co', 'notifier:vsn-co']
- `midczm` → ['morley:mi-dczm', 'notifier:mi-dczm']
- `m710` → ['morley:m710', 'notifier:m710']
- `m700kac` → ['kac:m700kac', 'notifier:m700kac']
- `m700kaci` → ['kac:m700kaci', 'notifier:m700kaci']
- `b501ap` → ['morley:b501ap', 'notifier:b501ap', 'systemsensor:b501ap']
- `140kit160` → ['detnov:140kit160', 'firebeam:140kit160']
- `70kit140` → ['detnov:70kit140', 'firebeam:70kit140']
- `vsn4rel` → ['morley:vsn-4rel', 'notifier:vsn-4rel']
- `ucipgprs` → ['morley:ucip-gprs', 'notifier:ucip-gprs']
- `ucip` → ['morley:ucip', 'notifier:ucip']
- `vsn4plus` → ['morley:vsn-4-plus', 'notifier:vsn4-plus']
- `vsn122plus` → ['morley:vsn12-2plus', 'notifier:vsn12-2plus']
- `refl20` → ['notifier:refl20', 'systemsensor:refl20']
- `refl30` → ['notifier:refl30', 'systemsensor:refl30']
- `refl40` → ['notifier:refl40', 'systemsensor:refl40']
- `refl50` → ['notifier:refl50', 'systemsensor:refl50']
- `refl60` → ['notifier:refl60', 'systemsensor:refl60']
- `b501` → ['notifier:b501', 'systemsensor:b501']
- `6500r` → ['notifier:6500r', 'systemsensor:6500r']
- `6500rs` → ['notifier:6500rs', 'systemsensor:6500rs']
- `dh500acdce` → ['notifier:dh500acdc-e', 'systemsensor:dh500acdc-e']
- `dh500` → ['notifier:dh500', 'systemsensor:dh500']
- `nfs8rel` → ['morley:nfs8rel', 'notifier:nfs8rel']
- `idr6a` → ['morley:idr6a', 'notifier:idr-6a']
- … (+10)

## colisión alias↔canonical (¿mismo producto? adjudicar) (77)
- alias `9-30441`→aritech:apic vs canonical de `xtralis:9-30441`
- alias `NRT`→notifier:nrt-586t vs canonical de `notifier:nrt`
- alias `CRE-4`→notifier:crm-4 vs canonical de `notifier:cre-4`
- alias `Sistema 5000`→notifier:system-5000 vs canonical de `notifier:sistema-5000`
- alias `VESDA VLI`→xtralis:vli-880 vs canonical de `xtralis:vesda-vli`
- alias `SM21`→unresolved:fsl100-sm21 vs canonical de `sense-ware:sm21`
- alias `INSPIRE E10`→notifier:e10 vs canonical de `notifier:inspire-e10`
- alias `INSPIRE E15`→notifier:e15 vs canonical de `notifier:inspire-e15`
- alias `HOP-131-206`→notifier:inspire-e10 vs canonical de `notifier:hop-131-206`
- alias `APIC`→xtralis:9-30441 vs canonical de `notifier:apic`
- alias `NAS`→notifier:nas-2 vs canonical de `notifier:nas`
- alias `E-SIB`→notifier:e-sib-m vs canonical de `notifier:e-sib`
- alias `AM-8200`→notifier:am-8200n vs canonical de `unresolved:am8200`
- alias `LIB`→notifier:lib-8200 vs canonical de `notifier:lib`
- alias `FL2011EI`→notifier:fl2011ei-hs vs canonical de `notifier:fl2011ei`
- alias `FL2012EI`→notifier:fl2012ei-hs vs canonical de `notifier:fl2012ei`
- alias `SMART 4`→notifier:irx-751ctem-w vs canonical de `notifier:smart4`
- alias `OMNI`→notifier:sdx-751-tem vs canonical de `notifier:omni`
- alias `AM-LCD`→notifier:lcd-8200 vs canonical de `notifier:am-lcd`
- alias `L.S.28`→hosiden:is-28-mk-4-banshee vs canonical de `hosiden:ls-28`
- alias `MI-DCZM`→notifier:m710-cz vs canonical de `morley:mi-dczm`
- alias `Calypso-II`→unresolved:calypso-ii-r vs canonical de `unresolved:calypso-ii`
- alias `TG-HONEYWELL`→unresolved:tg vs canonical de `unresolved:tg-honeywell`
- alias `F5000`→unresolved:f5k-2h vs canonical de `unresolved:f5000`
- alias `the Firebeam Xtra`→firebeam:firebeam-xtra vs canonical de `firebeam:thefirebeam-xtra`
- alias `ITAC`→unresolved:itac-2.0 vs canonical de `unresolved:itac`
- alias `ID3000`→notifier:id-3000 vs canonical de `unresolved:id3000`
- alias `UCIP GPRS`→notifier:ucip-gprs vs canonical de `morley:ucip-gprs`
- alias `VSN PLUS`→morley:vsn-12-plus vs canonical de `notifier:vsn-plus`
- alias `ESS-2Plus`→morley:ess12-2plus vs canonical de `notifier:ess-2plus`
- … (+47)