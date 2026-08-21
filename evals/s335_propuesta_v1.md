# s335 · Fraseos de inventario + anafórica adjudicada + «sí» pelado — propuesta v1 (21-ago-2026)

> **GO de Alberto al punto (2)** («es una corrección, i.e. "dime qué centrales de Morley
> tienes"») + su pregunta de opinión sobre (1) el «sí» pelado. Estado: PROPUESTA (pre-dúo).

## 0 · Evidencia (verificada)

- `9e8f650c` «Quiero ver las centrales de Morley.»: `_intencion_inventario(...)` = **False**
  (medido) — `_ENUM_FABRICANTE` solo cubre interrogativas («qué/cuál … tienes») y
  «listado/catálogo de …»; las DESIDERATIVAS no existen. El fraseo canónico de Alberto
  («dime qué centrales de Morley tienes») = True (ya funciona). El clasificador dijo `nuevo`
  CORRECTO (se sostiene sola) y aun así plantilla vacía: el hueco es el parser del atajo.
- `fabef50b` «Y ahora quiero ver las de Morley.» (anafórica, sin sustantivo): el clasificador
  dijo `nuevo`; **Alberto adjudica CORRECCIÓN** («es una corrección») — etiqueta límite
  resuelta por el owner, la vía pre-registrada de las cohortes.
- `2a1e1694` «Sí, a eso me refiero.» → clarify pidiendo modelo: 1ª observación del «sí»
  pelado tras respuesta (la clase `pending_aviso` diseñada s333 §1.E y diferida a
  observación — umbral cumplido). Contexto declarado: T1→T2 tardó ~46 s (latencia percibida
  pudo inducir el turno); la latencia es un tema APARTE, anotado y no construido aquí.

## 1 · Pieza A (GO dado) — fraseos desiderativos del atajo de inventario

Extender `_ENUM_FABRICANTE` (turn_plan) con las formas OBSERVADAS y sus hermanas mínimas:
`(quiero|querría|me gustaría|necesito)\s+(ver|saber)?\s*(el|la|los|las)?\s*
(listado|lista|catálogo|inventario|productos|modelos|centrales|detectores|equipos)…de {marca}`
+ imperativas `(dime|muéstrame|enséñame|dame)\s+(qué|el listado de|las?)…` — acotadas a
frases CON sustantivo de inventario y marca (la anafórica «las de X» NO entra aquí: su vía es
la corrección, pieza B). SIN flag nuevo: es el ensanche de un gatillo de ruta EXISTENTE
(precedente s322 #76, que ensanchó este mismo regex sin flag), protegido por (i) los tests de
equivalencia s316e (todo lo demás byte-idéntico), (ii) tests dirigidos de las formas nuevas y
de NO-disparos (p.ej. «quiero ver el manual del 2X-AF1» — modelo concreto NO es inventario),
y (iii) replay GA de la conversación real. El dúo adjudica si exige flag.

## 2 · Pieza B (GO dado) — la anafórica es corrección: cohorte v2.2

«(y ahora) quiero ver las de {marca}» (sin sustantivo — NO se sostiene sola) = CORRECCIÓN,
adjudicado por Alberto con cita `fabef50b`. Cohorte **v2.2**: + POSITIVA con ese caso (prompt
INTACTO — relabel/alta pura, mismo trato que v2.1) + re-run del gate (barra recalibrada
0 falsas / ≥13/15). Con estado fresco (R8 ya activa) el rebuild sirve las centrales Morley.

## 3 · Pieza C (opinión pedida; build SOLO con GO) — «pregunta pendiente del bot»

**Opinión: SÍ debe existir, y como UN mecanismo, no parches por caso.** Hoy el «sí» pelado ya
funciona en UN sitio (tras el clarify de mención, gramática s331). La generalización correcta:
`WorkingState` gana una **pregunta-pendiente TIPADA del bot** (`pending_q: tipo + referente`),
que se SETea cuando el bot pregunta (clarify de mención — migra; aviso ASR «¿dijiste X?»;
pregunta sí/no del generador si la declara) y que la gramática de afirmación/negación consume
en el turno siguiente («sí» ⇒ resolver el referente; «no» ⇒ su alternativa), con el lifecycle
s331 (SET/CONSUME/CLEAR en todas las salidas, ventana propia, ciclo máx 1). Es cambio de
esquema de estado + espejo MT ⇒ MEDIO-ALTO, diseño fino + dúo propio; NO se cablea en s335
salvo GO explícito — esta sección es el diseño-semilla para ese GO.

## 4 · Gates PRE-REGISTRADOS (piezas A+B)

- GB0 (sin cambios de flags: A no lleva): suite + s316e equivalencia + MT 52/52.
- GB1 replay real: «Quiero ver las centrales de Morley.» ⇒ ruta inventario ⇒ listado gobernado
  Morley; «dime qué centrales de Morley tienes» sigue True; 6 no-disparos dirigidos.
- GB2: gate v2.2 (Sonnet, regla K pinnada) — barra 0 falsas / ≥13/15 positivas; y e2e de
  «Y ahora quiero ver las de Morley.» tras atajo-Kidde ⇒ rebuild ⇒ contenido Morley.

## 5 · Alternativas y riesgos

- Alt: meter la anafórica en el atajo («las de X») — descartada: sin sustantivo no hay
  intención de inventario autosuficiente; su semántica ES corrección (el owner lo adjudicó).
- Alt: LLM para el enrutado de inventario — descartada: el atajo es $0 y el hueco es de
  cobertura léxica finita observada, no de juicio.
- R1: sobre-disparo de las desiderativas (p.ej. «quiero ver el manual del X») — no-disparos
  dirigidos + el sustantivo de inventario obligatorio.
- R2: dos gates en un día sobre la misma cohorte — sin gate-shopping: v2.2 es ALTA adjudicada
  por el owner con cita, prompt intacto, secuencia con SHAs.

## 6 · Traza del dúo

(pendiente — v1 al dúo: Sol xhigh + Fable emparejados, agentes frescos, cero git durante la ronda)
