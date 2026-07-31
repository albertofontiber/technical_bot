# s288b — LEVER TAXONOMÍA/ARQUETIPOS de la lane hyq (post-A-core; spec pre-dúo)

Lever SEPARADO que el spec A-core v3 §4 difirió: ampliar la taxonomía de arquetipos de
`config/retrieval_facets_v1.yaml` (la config que `expand_query_facets` consume por DEFAULT —
query_facets.py:16 — y que gatea la ENTRADA a `doc_scoped_hyq_coverage`). Se mide old-vs-new
config con **corpus y autoridad FIJOS** (post-P-A, censo v4 sha `8ae2060269a1e931`) — el
aislamiento que exigió el dúo A1. La lane sigue OFF: todo es mecanismo, $0, 39 dev only.

## 0. OBJETIVO + MÉTRICA
Que las clases de pregunta AUSENTES de la taxonomía entren a la lane. MÉTRICA = mecanismo
(probe de lane con receipts, patrón F3.2): entrada + parents servidos con facetas de la aguja.
NO outcome (lane OFF; el outcome llega con A3). Diana diagnosticada: **cat010** (F3.2:
resolver OK 2 docs, `archetype: None`). Los settled no colisionan: DEC-163/165 dejan cat010
atribuido EXACTAMENTE a este lever; el eje facetas-de-CANAL (DEC-099/101) es otra config
(retrieval_facets_v3, intocada — test de inertness).

## 1. HECHOS VERIFICADOS (30-jul)
- v1 tiene 5 arquetipos (`replace_without_loss`, `connect_install_wire`, `capacity_quantity`,
  `fault_reset_recovery`, `program_delay_cause_effect`), `policy: first_match`, patrones
  regex de INFINITIVOS mayormente.
- cat010 «¿Cómo se alimenta… parámetros de seguridad intrínseca…?» no matchea ninguno.
- hp013 «¿Cómo se cambia la batería…?» TAMPOCO matchea `\b(cambiar|…)\b` (conjugación
  «se cambia») — la clase conjugaciones de A1 v1; hp013 sigue doble-bloqueado (sin surrogate
  PWR-R) → NO es gate, se declara.
- Las cards de esta lane = STRICT_ALIGNED (evidence v4); arquetipo sin entrada gemela en v4
  → `select_evidence_coverage_cards` vacío → parent no elegible (verificado en s287: la
  clase de desalineamiento match-sin-card).

## 2. PIEZAS (cada una gateada por separado)
**A. Arquetipo nuevo `power_supply_parameters`** (clase desde TAXONOMÍA, no desde la
   cohorte): alimentación/consumo/parámetros eléctricos/seguridad intrínseca. Diseño de
   patrones: sustantivos + formas conjugadas de alimentar (`\b(aliment\w+|se alimenta)\b`,
   `\bconsumo\b`, `\bseguridad intr[ií]nseca\b`, `\bpar[aá]metros? (el[eé]ctricos?|de
   entrada)\b` — el dúo ataca el over-trigger). Needs orientadas a celdas hyq: tensión/
   alimentación · parámetros Ui/Ii/Pi/Ci/Li seguridad intrínseca · zona/barrera/ATEX.
   Posición: ÚLTIMO en la lista (first_match: no puede ensombrecer a los 5 existentes).
**B. Conjugaciones en arquetipos EXISTENTES** (pieza separada, diff propio): extender los
   patrones de infinitivo con formas conjugadas frecuentes («se cambia», «se sustituye»,
   «se conecta» ya está…) SIN tocar needs. Cambio mínimo por-patrón, no stemmer genérico.
**C. Gemelas en evidence v4** para el arquetipo A (facetas de card: power_input_params /
   intrinsic_safety_cell — términos required_any conservadores, lección homógrafo s287) +
   test de paridad por-lane extendido si aplica (la lane no tiene match-config — verificar
   qué exige el test) + **inertness**: v3-retrieval y v2 byte-INTACTOS.

## 3. GATES (todos $0, pre-registrados ANTES de medir la diana — lección STOP s287 ×2)
1. **Diff de asignación PRE-REGISTRADO sobre las 39 dev queries** (old-vs-new config, por
   pieza A y B por separado): tabla query→(archetype_old, archetype_new). Esperado A: cambia
   SOLO la clase declarada (cat010 + miembros legítimos que el diff revele y se adjudiquen
   ANTES del probe). Esperado B: solo queries con conjugación de un verbo ya cubierto.
   Cualquier flip entre arquetipos EXISTENTES = STOP.
2. **Controles negativos de over-trigger**: queries con «alimentación/consumo» en OTRO
   sentido no entran (buscarlas en las 39 + sintéticas); precedencia first_match verificada
   (el nuevo NO captura queries de los 5 previos).
3. **Probe mecanismo diana** (patrón F3.2, receipts): cat010 entra + sirve parents con
   facetas de la aguja + los excerpts de las cards contienen los valores (parámetros IS /
   alimentación del IS-mA1). hp013: se re-corre como baseline, sin gate.
4. **Sweep 39 de entrada a la lane** old-vs-new: status por query; nuevas entradas solo en
   la clase declarada.
5. Suite completa verde + inertness (sha de v3/v2 sin cambio).
Held-out: EMBARGADO de todo (39 dev only).

## 4. FUERA DE SCOPE / DESCARTADAS
Stemmer/lematizador genérico (over-trigger incontrolable; B es extensión mínima explícita) ·
tocar v3 (canal retrieval, DEC-099/101 settled) · tocar cuota/radio/diversify (settled) ·
surrogates nuevos (H5) · perfil/activación (A3) · perseguir hp013 (doble bloqueo declarado).

## 5. RIESGOS
1. Over-trigger de A en queries de capacidad («consumo por lazo»?) → gate 2 + first_match +
   posición última. 2. Facetas v4 con términos que colisionen en otras familias (homógrafo
   s287) → required_any conservador + diff de cards en sweep. 3. El diff de 39 puede revelar
   miembros de clase inesperados → se ADJUDICAN antes del probe (no silent-pass). 4. B puede
   re-rutear una query de un arquetipo a otro si un verbo conjugado pertenece a dos patrones
   → STOP declarado en gate 1.

## 6. PROTOCOLO
MEDIO-en-zona-de-dolor (retrieval/config) → dúo completo (sub-agente Fable fresco +
cross-model Sol xhigh) sobre ESTE brief antes de cablear → reescritura in-place → build →
gates 1-5 → tally regla-C. Stop-lines habituales.
