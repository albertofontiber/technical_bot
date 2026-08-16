# s324c — E1b: censo del radio de explosión POR BLOQUE (dry-run) · 20260816T220541Z

> ## NADA APLICADO — para el «sí» de Alberto, bloque a bloque
> **Ojo con la nomenclatura:** las «R1…R6» de ESTE fichero son las reglas del CLASIFICADOR DE ALIAS DESCRIPTIVOS (qué alias se retiran antes de confirmar), NO las reglas de adjudicación R1–R7 del residuo (`evals/s324_reglas_residuo_adjudicacion_v1.json`). Verificado por el autor de la sesión (17-ago 00:xx): `plan_sha` de los 11 recibos = sha del plan en disco (método del writer), catálogo `data/catalog/*` intacto, totales 422 confirmar / 40 no_aplicar / 125 alias a retirar / 4 retirar.
> Un plan por bloque (`evals/s324c_e1b_bloque_<nombre>_plan_v1.json`) + su gate (`…_v1_radio_explosion.json`, dry-run del writer, nunca `--aplicar`); sin LLM ($0). El bloque detnov (§0.A) ya se aplicó y no está aquí. Fila confirmable = token literal ≥1 + cita verbatim verificada full-text en su documento; lo que no verifica, ya estaba aplicado o colisiona (canonical duplicado / alias ajeno / paraguas: la puerta lo rechaza) va a `no_aplicar` con motivo. Alias descriptivos de los ids confirmados → `aliases_quitar` (R1 multipalabra sin token de modelo · R2 «N zonas» · R3 panel/central/detector/módulo/software sin modelo · R4 OCR O/0 · R6 truncación ambigua de familia — nace del gate: «VSN12» disparó «vsn 12»); los model-shaped se conservan; los sin dígito no entran hoy en el detector (se retiran por higiene: filtra `entra_en_detector=false` para conservarlos).

| bloque | filas | confirmables | no_aplicar | alias a retirar (entran en detector) | +términos | gold perdidas | negativos | tráfico real | VEREDICTO |
|---|---|---|---|---|---|---|---|---|---|
| 0a_notifier | 83 | 81 | 2 | 14 (2) | 134 | 0/0 | 0/36 | 0/96 | **PASS** |
| 0a_unresolved | 51 | 46 | 5 | 19 (8) | 82 | 0/0 | 0/36 | 0/96 | **PASS** |
| 0a_kidde | 16 | 16 | 0 | 0 (0) | 16 | 0/0 | 0/36 | 0/96 | **PASS** |
| 0a_morley | 16 | 13 | 3 | 0 (0) | 13 | 0/0 | 0/36 | 0/96 | **PASS** |
| 0a_systemsensor | 16 | 16 | 0 | 0 (0) | 20 | 0/0 | 0/36 | 0/96 | **PASS** |
| 0a_xtralis | 5 | 5 | 0 | 6 (1) | 7 | 0/0 | 0/36 | 0/96 | **PASS** |
| 0a_fidegas | 1 | 1 | 0 | 0 (0) | 0 | 0/0 | 0/36 | 0/96 | **PASS** |
| 0a_spectrex | 1 | 1 | 0 | 1 (0) | 0 | 0/0 | 0/36 | 0/96 | **PASS** |
| 0b | 129 | 105 | 24 | 40 (7) | 161 | 0/0 | 0/36 | 2/96 | **PASS** |
| 0c | 144 | 138 | 6 | 45 (15) | 164 | 0/0 | 0/36 | 0/96 | **PASS** |
| 0d | 4 | 4 (retirar) | 0 | 0 (0) | 0 | 0/0 | 0/36 | 0/96 | **PASS** |

gold perdidas = patrón/resolver (51 gold) · negativos = frases sintéticas del writer · tráfico real = consultas de `query_logs` con detección nueva.

## Por bloque: filas más arriesgadas léxicamente y señales del gate

- **0a_notifier** (§0.A) — **PASS** · no_aplicar 2 colisión (notifier:id-3000, notifier:tg-1020) · más arriesgadas: `notifier:am-8200n` [sin banderas; +5 alias]; `notifier:pk-8200` [sin banderas; +3 alias]; `notifier:smart4` [sin banderas; +3 alias]; `notifier:am-200` [sin banderas; +2 alias]; `notifier:amg-x4` [sin banderas; +2 alias] · cross-bloque: 3 (aplicar uno o adjudicar) · homónimos (sin efecto en resolución): MCX-55M, MMX-10M, NFS8REL
- **0a_unresolved** (§0.A) — **PASS** · no_aplicar 4 colisión, 1 ya aplicado (unresolved:am8200, unresolved:m710-czr, unresolved:mad-450, unresolved:vsn12-2plus) · más arriesgadas: `unresolved:fs24x` [sin banderas; +4 alias]; `unresolved:fs24x-9` [sin banderas; +4 alias]; `unresolved:fs20x` [sin banderas; +3 alias]; `unresolved:fsl100-ir3` [sin banderas; +3 alias]; `unresolved:fsl100-uv` [sin banderas; +2 alias] · gold con detección nueva: 1 (['mad-472']) · cross-bloque: 6 (aplicar uno o adjudicar)
- **0a_kidde** (§0.A) — **PASS** · sin banderas léxicas
- **0a_morley** (§0.A) — **PASS** · no_aplicar 3 ya aplicado · más arriesgadas: `morley:mcx-55m` [sin banderas; +1 alias]; `morley:nfs12-supra` [sin banderas; +1 alias]; `morley:nfs8-supra` [sin banderas; +1 alias] · cross-bloque: 9 (aplicar uno o adjudicar) · homónimos (sin efecto en resolución): MCX-55M, MMX-10M, NFS8REL
- **0a_systemsensor** (§0.A) — **PASS** · más arriesgadas: `systemsensor:eco1000b` [sin banderas; +2 alias]; `systemsensor:eco1000brx` [sin banderas; +1 alias]; `systemsensor:eco1000brxsd` [sin banderas; +1 alias]
- **0a_xtralis** (§0.A) — **PASS** · más arriesgadas: `xtralis:lt-acc-poe-24-adr` [sin banderas; +2 alias]; `xtralis:ift-15` [sin banderas; +1 alias]
- **0a_fidegas** (§0.A) — **PASS** · sin banderas léxicas
- **0a_spectrex** (§0.A) — **PASS** · sin banderas léxicas
- **0b** (§0.B) — **PASS** · no_aplicar 6 ya aplicado, 18 colisión (notifier:inspire, notifier:notifier-inspire-e10, notifier:notifier-inspire-e15, unresolved:id50, unresolved:id60, unresolved:tg-gsm, unresolved:tg-honeywell, unresolved:vsn-co…) · más arriesgadas: `notifier:nas` [muy_corto, sin_digitos, acronimo_corto, palabra_comun:nas]; `notifier:securnet-plus` [sin_digitos, multipalabra, palabra_comun:plus; +1 alias]; `notifier:mini-vista` [sin_digitos, multipalabra, palabra_comun:mini/vista]; `notifier:transponder-serie-xp` [sin_digitos, multipalabra, palabra_comun:transponder/serie]; `xtralis:honeywell-smartconfig-app` [sin_digitos, multipalabra, palabra_comun:honeywell/app] · tráfico real: «¿Cuáles son las características técnicas de la central »→cs4: probable TP; «¿Qué resistencia de fin de línea hay que instalar en la»→nfs supra: probable TP · gold con detección nueva: 2 (['cs4']; ['nfs supra']) · muy cortos: BM-1, BP-1, BP-3, CMX, CS4, DP-1, DS 5, G-10 · homónimos (sin efecto en resolución): E10, E15
- **0c** (§0.C) — **PASS** · no_aplicar 2 sin token literal, 4 colisión (notifier:sdx-751-tem, unresolved:tg-ip-1-sec, morley:vsn4-2plus, unresolved:vsn4-2plus, morley:vsn8-2plus, unresolved:vsn8-2plus) · más arriesgadas: `unresolved:vision-supra` [sin_digitos, multipalabra, palabra_comun:vision; +2 alias]; `testifire:solo-725` [multipalabra, palabra_comun:solo; +1 alias]; `notifier:smart-1` [multipalabra, palabra_comun:smart]; `notifier:tg-6000-net` [multipalabra, palabra_comun:net]; `notifier:ucip-modbus-e20m` [multipalabra; +6 alias]
- **0d** (§0.D) — **PASS**

## No medido

- Retrieval/generación end-to-end (instrumento: FULL v3.2). El «TP» del tráfico real es heurístico (modelo literal en la consulta), no juzgado. El efecto sobre `must_preserve` (alias de una palabra como token distintivo D2) no se mide. Cada bloque se midió contra el catálogo de HOY: aplicar varios cambia el punto de partida (colisiones cross-bloque en cada plan).