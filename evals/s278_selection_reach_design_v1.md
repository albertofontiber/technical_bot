# s278 — Diseño: alcance de selección del lane document-local (v1, PRE-dúo)

**Estado:** BORRADOR para Protocolo 3 (Sol + Fable). NO cablear antes del dúo.
**Decisión de gobernanza:** Alberto confirma **B** (22-jul): la release C1 se RETIENE hasta cerrar
esta ronda — el overflow por-scope es un defecto sistemático (el lane se auto-apaga en manuales
grandes), no un residual de dos preguntas.
**Insumos:** diagnóstico medido con el path real (agente s278, RPC v3 vivo, solo GETs; scripts
`dl_diag*.py` en scratchpad reproducibles): cat019 muere en overflow→elegibilidad→winner-takes-1;
cat017 moría en datos (CERRADO: data-fix v2 aplicado, receipt `s278_live_poststate_receipt_v2.json`)
y después en ontología de facetas. Métrica objetivo: ítems P1 de cat017/cat019 (4-6 de los 29)
sin regresión de las clases servidas existentes ni del oráculo baseline (27/27+62/62+93/93).

## Compuerta 1 — overflow por-scope (SISTEMÁTICO; necesario para cat019)

**Hoy:** tsquery matchea 81/134 chunks del MC-380 > `CANDIDATE_LIMIT=64` ⇒ el cliente descarta el
scope ENTERO (`document_local_coverage.py:724-726/763-781`). El lane no sirve NADA de manuales
grandes de configuración — la clase de doc donde más paga.

**Diseño:** truncado ACOTADO y VISIBLE (recomendación del diagnóstico, fix de raíz):
- El RPC ya capa `candidate_limit≤64` en SQL; el cliente deja de tratar el overflow como
  descalificación del scope y pasa a consumir los primeros 64 **en orden determinista
  `chunk_index`** (el orden que el RPC ya devuelve), estampando en el trace/receipt:
  `candidate_truncated: true`, `fts_candidate_rows` totales y el corte aplicado.
- Fail-closed se CONSERVA donde protege de verdad: attestation por-fila intacta; el receipt de
  la fila servida sigue exigiendo identidad completa. Lo que cambia es SOLO que "hay demasiados
  candidatos" deja de significar "no sirvas ninguno".
- Alternativa considerada y DESCARTADA: endurecer el need_clause a AND-de-3-grupos (81→30
  matches medido) — estrecha el recall de TODAS las queries para arreglar el cap de una;
  parche, no raíz.
- Riesgo declarado: con truncado, un span más allá del corte 64 sigue fuera (el de cat019 está
  en posición 2 ⇒ dentro); el trace lo hace visible y medible.

## Compuerta 2 — elegibilidad por-faceta (necesario para ambos)

**Hoy:** la puerta única de `_query_card` exige ≥6 hits del vocabulario-UNIÓN de la pregunta en
ventana de 360 chars (`rerank_pool_coverage.py:177`, `MIN_ALIGNMENT_TERMS=6`). Prosa alineada a
UNA sola faceta muere sistemáticamente (medido: span cat019 = 4 hits; chunk config cat017 = 2).

**Diseño:** presupuesto POR FACETA (patrón del precedente hp002/reserve, NO rebajar la puerta
global):
- Las need-groups por faceta YA existen (grupo 3 de cat019 = acción/salida/…). Nueva regla de
  elegibilidad COMPLEMENTARIA: un candidato es elegible-por-faceta si su ventana cubre
  ≥N_FACET (propuesta: 3) términos de UNA MISMA need-group Y esa faceta no está ya cubierta por
  las filas seleccionadas. Presupuesto: máx 1 fila por faceta no-cubierta, dentro del cap global
  existente del lane.
- La puerta global de 6 se mantiene para la selección general (cero cambio de conducta para
  candidatos multi-faceta); la vía por-faceta es aditiva, flag-gated dentro del lane, y su
  receipt declara `facet_eligibility: {facet, terms_hit, window}`.
- Winner-takes-1 pasa a winner-por-faceta bajo la misma vía (la fila ganadora de la faceta
  salidas/acciones de cat019 sería la p10 — única con la frase del ítem — si su ventana cubre
  ≥3 de [accion, salida, seleccionar, aplicar, transferir, circuito]; VERIFICAR en el build con
  el probe real, no asumir).

## Compuerta 3 — ontología de facetas (necesario para cat017)

**Hoy:** `retrieval_facets_v4` es first-match; la pregunta de cat017 (cablear + dar de alta)
cae en `connect_install_wire` y la faceta de alta/configuración aporta CERO vocabulario.

**Diseño (pregunta central para el dúo):** ¿basta MULTI-FACETA sin reordenar?
- Propuesta mínima: v4 se mantiene; se añade arquetipo `commissioning_setup` (alta/configurar/
  puesta en servicio/licencia/autoconfiguración/sitio/edificio…) y el match pasa de first-match
  a **multi-match acotado (máx 2 arquetipos)** SOLO para generar need-groups adicionales — la
  faceta primaria (la actual) no cambia, así que el vocabulario existente de TODAS las queries
  se conserva EXACTO y solo se AÑADEN grupos donde un segundo arquetipo matchea.
- Con la Compuerta 2, esos grupos nuevos dan elegibilidad por-faceta al chunk de configuración
  (sitio/edificio/.bin) sin tocar la selección primaria.
- Si el dúo concluye que multi-match acotado ya es "mover todas las queries" ⇒ Protocolo 4
  exige delta en eval ANTES de shipear: plan = re-run del census de selección offline (pools
  congelados, $0) + pasada harness barata dirigida; declarar la métrica.
- Alternativa descartada de entrada: reordenar first-match de v4 (mueve la faceta primaria de
  queries existentes ⇒ blast-radius máximo).

## Verificación de la ronda

1. Tests unitarios por compuerta (incl. negativos: multi-faceta no roba el cap de la selección
   general; truncado visible; hp009/hp002 controles intactos).
2. Probes offline con el path real (los `dl_diag` del diagnóstico, promovidos a scripts
   versionados) — cat019 span servido vía prosa, cat017 chunk config elegible: ANTES de gastar.
3. Oráculo baseline byte-inerte (los 3 cambios viven en el lane flag-gated; off = idéntico).
4. Smoke dirigido cat017+cat019 (~$0.5) → pasada final completa 13 QIDs+controles (~$3) →
   lectura de Alberto → merge #184 + flip = release.

## Gaps declarados

1. N_FACET=3 es propuesta a validar con el probe real (no tuneado contra el gold: la regla es
   general por need-group).
2. El truncado a 64 deja fuera spans más allá del corte (visible en trace; medible en la pasada).
3. Riesgo de sobre-servicio por-faceta en preguntas amplias: acotado por "máx 1 fila por faceta
   no-cubierta" + cap global del lane; el dúo debe atacar este borde.
4. data-fix v2 APLICADO (Alberto) — la compuerta de datos ya no existe; si el dúo la reabre,
   es señal de drift, no de diseño.
