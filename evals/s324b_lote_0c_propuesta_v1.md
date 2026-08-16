# s324b — Propuesta: aplicar el lote §0.C del packet E1 (32 filas «candidates → ALTA» REVISADAS por Alberto) con las mismas puertas que el lote de la mañana

**Estado: NADA aplicado en catálogo** (sí dos bajas de corpus ya ejecutadas con recibo, adjudicadas por
Alberto: la hoja «30012012 TARJETAS IDIOMAS VISION SUPRA rev A» y el PT `MADT190P_01_C` cuyo ES es `MADT190_01`).
El plan (`evals/s324b_lote_0c_plan_v1.json`, `scripts/s324b_lote_0c_plan.py`) y el dry-run con censo
(`evals/s324b_lote_0c_v1_radio_explosion.json`, `scripts/s324_lote_firmado_writer.py --plan …`) están hechos.

## Qué firmó Alberto (16-ago, tercer turno)
§0.C revisado fila a fila en su copia del packet: **aceptado salvo 10 notas**, consolidadas en
`evals/s320_e1_packet_adjudicacion_v2.md` bajo cada fila (con la respuesta del autor `↳ s324b`):
2X-A y «DXc Connexion» son FAMILIAS (no producto) · KE-DM3110R-KIT fila duplicada · Vision Supra → baja del doc
(confirmada) · dos docs PT → baja · «el software entra como producto» (ID²net, CLSS Configuration Tool) ·
Spectrex con la S: S40/40M, S40/40R, S40/40U + S40/40UB.

## Qué escribe el plan (verificado token exacto + cita verbatim ≤200 chars en el TEXTO COMPLETO del doc)
| Colección | Filas | Detalle |
|---|---|---|
| products ALTA | **22** | 11 accesorios/pulsadores/detectores Kidde Excellence (KE-ASA-AUXR, KE-DBA-CAPW/IPW/RECW/TAGW, KE-DM3110R-IP/-KIT, KE-DP3021B/W, KE-IU3110, N-IO-SBX-2G) · Morley MOD.RS-232 / MOD.RS-485 · Notifier KIT-GAS, STRATOS, NFXI-BSF-WC · **software** ID²NET y CLSS Configuration Tool (`clasificacion.categoria=software`, precedente MK-VSN/MK-ZX/MK50/MKDX, OPC-RP1r) · Spectrex S40/40M, S40/40R, S40/40U, S40/40UB |
| aliases ALTA | 4 | `40/40M`→S40/40M, `40/40R`, `40/40U`, `40/40UB` (variante tipográfica: la forma de las etiquetas del corpus y de los golds «SharpEye 40/40») |
| umbrellas | **1** | **«2X-A»** familia, 38 miembros por regla (prefijo 2X-A × {central, repetidor}) — adjudicado 2× por Alberto (s323 + hoy) |
| doc_map (altas, 1 fila/doc) | 27 | docs sustentantes de cada alta + la FAQ «No-puedo-hacer-rearmes…» → dxc1/dxc2/dxc4 (familia) + los ya existentes (KE-DBA-ADPW-KIL/ZIT, N-IO-MBX-2: doc_map desde sus DS) |
| bajas de corpus (YA aplicadas) | 2 | Vision Supra tarjetas idiomas · MADT190P_01_C |
| no aplicar | 0 | — |

Sustituciones de documento (declaradas en `avisos`): CLSS Configuration Tool se sustenta en `4188-1124-ES` (el
PT del draft se retiró esta mañana); ID²NET en `MADT190_01` (ES); **NFXI-BSF-WC**: la ficha del draft (`D 1147-1
BRH`) dice «NFXI-BSF-WCH» pero su texto no lo nombra; el corpus (AM-8200/8100/8200N/G, 997-669) escribe
**NFXI-BSF-WC** en tablas de dispositivos → alta con la grafía verificada, sustentada por la tabla del AM-8200 y
**sin doc_map** (el manual de la central no es SOBRE la base). Si «WCH» es código real, alias a posteriori.

## Censo del radio de explosión (dry-run sobre copia)
Detector del resolver **1.695 → 1.722 (+27/−0)** · 51 gold: 0 pérdidas (detector y `resolve_query`); **4 ganan**
(las 2 FAQ DXc +1 fuente; 2 golds sobre 2X-A resuelven ahora a la familia: +12 fuentes cada uno) · **tráfico
real** (`query_logs`, 96 consultas): 0 detecciones nuevas · negativos sintéticos: 1 disparo («2 x a» ← «2X-A»),
**declarado como aviso** porque el término está adjudicado 2× por Alberto (`adjudicados_por_alberto_para_el_gate`).
**Cambio en la regla del gate respecto a r32** (declarado): un disparo en negativo SINTÉTICO de un término
adjudicado explícitamente por Alberto no es STOP; sí lo sigue siendo para cualquier término no adjudicado, y se
añade el conjunto de negativos de TRÁFICO REAL. Veredicto: **PASS**. Mecánica T3 idéntica a la mañana (freeze,
build→validar→backup→swap, verificación posterior en censo).

## Riesgos y gaps declarados
1. Riesgo léxico del paraguas «2X-A» (normkey 3 chars): medido en 96 consultas reales (0) y en 51 gold (0
   pérdidas, 2 ganancias legítimas); el conjunto real es pequeño. Reversible (git).
2. Cinco altas con n_token 1-2 (MOD.RS-232/485, KE-DM3110R-IP, KE-DP3021B/W, KE-ASA-AUXR): son títulos de
   manual/hoja de producto (rol TITULO en el juez), verificados verbatim; la evidencia es la portada del doc.
3. STRATOS (sin dígitos) entra en el detector: es el nombre de la gama AirSense/Kidde de aspiración (MADT731,
   18 chunks) — no palabra común en castellano; aceptado por Alberto sin nota.
4. NFXI-BSF-WC nace sin doc_map: su ficha (D 1147-1) queda sin atestar hasta que un doc lo nombre.

## Qué pido al revisor
Atacar (a) filas cuya evidencia no sostenga la escritura; (b) la excepción del gate para términos adjudicados y el
uso del tráfico real; (c) los dos software como productos; (d) las sustituciones de documento sustentante.
