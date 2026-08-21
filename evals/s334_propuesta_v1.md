# s334 · Los dos GO de la conversación de la tarde — propuesta v1 (21-ago-2026)

> **GO doble de Alberto** tras el diagnóstico de 13:26-13:29Z (5 filas leídas en query_logs):
> (1) fuzzy ACOTADO al slot de marca del turno de corrección; (2) R8 — el atajo de catálogo
> refresca el estado conversacional. Estado: PROPUESTA (pre-dúo). Flags default-off.

## 0 · Evidencia (verificada, no de memoria)

- **`044c584a`** «Quería decir de KIDE.»: cue válido del léxico + marca CORRUPTA por ASR
  («KIDE» ∉ BRAND_TOKENS) ⇒ `matched_brands=[]` ⇒ la rama B entera inalcanzable — ni
  plantilla ni clasificador. Plantilla vacía. **5 corrupciones distintas de «Kidde» en un
  día** (BQide/ID/ITIDE/KIDE + el precedente Death-Knob de Detnov): la tabla por observación
  no converge sola — la clase-nueva que re-abre el fuzzy (el NO de DEC-233/s332-v2-§3.6
  midió fuzzy GENERAL sobre miles de códigos de MODELO; esto es otra población y otra métrica).
- **`9bd568cc`** «Ahora quiero Morley» tras el listado-atajo de KIDDE: el clasificador se
  invocó (1ª vez en producción: `invoked/nuevo/1121ms`, trace estampado — mecánica perfecta)
  pero razonó contra `last_query`=«Quería decir de KIDE.» (13:27) porque **el atajo de
  catálogo NO refresca el estado** (R8, declarada s332 v2 §4). Con estado fresco, la frase es
  la clase P13/P14 que Alberto adjudicó ⇒ rebuild ⇒ centrales Morley.
- **Auditoría fuzzy**: 25 tokens de marca gobernados, **CERO pares a distancia≤1 entre sí**
  (medido, script en §2.A) — el espacio de resolución no tiene ambigüedad interna.
- **`_aplicar_estado` (telegram_bot:173) es el ÚNICO punto de escritura de
  `mt_working_state`** (invariante fase B) — cualquier fix de R8 pasa por ahí.
- **Hueco adicional confirmado**: la ruta de atajo tampoco CONSUME/limpia un
  `pending_mention` vivo — «ciclo máximo 1» (s331 B3) hoy es violable cruzando un atajo.

## 1 · Fix 1 — fuzzy acotado al slot de marca (flag `F1_CORRECCION_FUZZY`)

**Población** (todas): la rama de corrección YA activa (`correction_enabled()`, sin modelo,
sin pending, `last_query` viva) · `matched_brands` VACÍO · un cue de corrección presente
(`_match_phrase` sobre el léxico — el chequeo barato que hoy va implícito en la plantilla) ·
exactamente UN token candidato del turno (alfabético, ≥4 chars, no-gobernado, no stopword del
propio cue) a **distancia de edición ≤1 de exactamente UNA marca** de BRAND_TOKENS.

**Resolución**: la marca fuzzy entra a la MISMA maquinaria (plantilla primero con la marca
sustituida; si no casa, clasificador con `marca` = la resuelta) + **disclosure OBLIGATORIO**:
`Asuncion(kind="marca_fuzzy", detectado="KIDE", asumido="Kidde", modo="reescrito")` → sufijo
«Entiendo que te refieres a *Kidde* (llegó «KIDE»). Si no es así, dímelo.» — el fuzzy sin
disclosure NO existe (la visibilidad ES el control; un falso positivo se autodelata).

**Acotaciones que lo separan del fuzzy prohibido**: espacio = 25 marcas (no miles de códigos),
distancia ≤1 (no fonético), solo turnos-de-corrección (no toda query), colisión-interna CERO
medida, y disclosure siempre. Enum `Asuncion.kind` gana `marca_fuzzy` (+ trace allowlist).

## 2 · Fix 2 — R8: el atajo refresca el estado (flag `F1_ESTADO_ATAJOS`)

En la ruta `inventario` de `_ejecutar_plan` (la única de atajo CON contenido; cortesías
quedan FUERA — no cambian de tema), tras servir la respuesta: escribir estado vía
**`_aplicar_estado`** (el único escritor) con la semántica de la rama-de-RESPUESTA de
`advance_working_state`: `last_target_models=()` (el atajo no bindea modelos),
`last_query=query`, `last_answer_excerpt=respuesta[:500]`, `last_turn_at=now`,
**pending CONSUMIDO/limpiado** (cierra de paso el hueco «ciclo máximo 1» del §0). La función
vive en `conversation_policy_impl` (`advance_after_shortcut(ws, query, excerpt, now)`) para
que las transiciones sigan centralizadas y el espejo MT la importe si algún día ejercita
atajos. S99 intacto: un atajo ES un turno respondido de verdad (no un clarify) — refrescar
`last_turn_at` es legítimo y es exactamente lo que el incidente demuestra que falta.

## 3 · Gates PRE-REGISTRADOS

- **GA0 byte-idéntico** (ambos flags off): replay de la conversación de HOY (5 turnos) —
  conducta actual exacta; suite completa; MT 52/52.
- **GA1 replay ON**: (a) «Quería decir de KIDE.» tras plantilla-vacía ⇒ fuzzy resuelve Kidde
  ⇒ rebuild con sufijo de disclosure, sin plantilla vacía; (b) atajo KIDDE → «Ahora quiero
  Morley» ⇒ clasificador con `last_query` FRESCA ⇒ CORRECCION ⇒ rebuild ⇒ contenido Morley;
  (c) controles: «quería decir de la CAD-150» (modelo, rama A intacta), token a distancia >1
  («BQide» NO fuzzy — lo cubre su fila), turno sin cue NO fuzzy, pending vivo se limpia tras
  atajo (test dirigido).
- **GA2**: cohorte-mini de fuzzy (12 casos: 6 positivos typo-1 de marcas distintas, 6
  negativos — palabras reales a distancia 1 de nada, token a distancia 2, dos marcas
  candidatas) — determinista, sin LLM, $0.
- Ship: PR → merge → 2 vars (`F1_CORRECCION_FUZZY=on`, `F1_ESTADO_ATAJOS=on`) → verificación
  DEC-099: repetir la conversación de HOY por voz.

## 4 · Alternativas descartadas

1. Fuzzy fonético/metaphone o distancia ≥2: espacio de falsos positivos crece sin evidencia
   que lo pida (KIDE=1; ITIDE=2 pero YA tiene fila observada — el fuzzy no es para lo ya
   tabulado).
2. Fuzzy en TODO turno (no solo corrección): re-abre el prohibido de verdad (cualquier typo
   en cualquier query se «corregiría» a una marca) — sin población de corrección no hay
   ancla de intención ni disclosure natural.
3. R8 vía duplicar la transición en el bot (sin pasar por impl): rompe la centralización de
   mutaciones (B3 s331) y el único-escritor de fase B.
4. Refrescar estado también en cortesías: no cambian de tema; ampliar sin evidencia.

## 5 · Riesgos declarados

- R1: falso positivo fuzzy (palabra real a distancia 1 de una marca en un turno-corrección):
  población minúscula + GA2 lo mide + disclosure lo hace visible y corregible.
- R2: `advance_after_shortcut` diverge de `advance_working_state` con el tiempo: una sola
  fuente por construcción (misma rama de código o test de lock-step).
- R3: el clasificador con `last_query` de atajo (listado largo) — el prompt recibe la QUERY
  del atajo («¿Qué centrales de KIDDE tienes?»), no la respuesta: sin cambio de payload.
- R4: dos flags más en Railway (van 9): mismo compromiso — graduación DEC-210/211 tras asentar.

## 6 · Traza del dúo

(pendiente — v1 al dúo: Sol xhigh + Fable emparejados, agentes frescos, cero git durante la ronda)
