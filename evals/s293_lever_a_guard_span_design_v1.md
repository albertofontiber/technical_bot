# s293 · Lever A — precisión del conflict-guard: reparación por SPAN antes que por BLOQUE

**Objetivo + MÉTRICA de hoy.** Que el hecho `hp017#2` (ruta «menú Editar Configuración» →
pantalla «Causa y Efecto» + borrar la Regla 1) y los pasos co-localizados sobrevivan al
conflict-guard **sin tocar la garantía de seguridad**. Métrica: *conveyed* per-fact
(instrumento v3.2) sobre `hp017`, más el control de que el aviso de conflicto sigue emitido y
la validación final sigue limpia. NO es una métrica de PASS.

**Impacto: MEDIO en zona sensible** (guard de seguridad numérica, always-on en el pipeline)
⇒ dúo completo (sub-agente Opus 5 + cross-model GPT-5.6 Sol xhigh), flag default-off, A/B.

---

## 1. Hecho medido que motiva el lever (recibos en `s293_levers_measurement_v1.md`)

- La fuente pone el dato del gold y el valor en conflicto en la MISMA frase, a 12 caracteres
  (`997-671-005-3_Configuration_ES` p.45, chunk `a95f8659`, F11).
- `apply_answer_conflict_guard` repara **por bloque** (`re.split(r"(\n[ \t]*\n)")`) ⇒
  sustituye el párrafo ENTERO por el aviso.
- 3 turnos reales: `surgical_repair` 3/3 · ruta PRE-guard 3/3 · ruta POST-guard **0/3**.
  El bloque borrado contenía **3 pasos numerados**, no solo el hecho del gold.
- El conflicto es REAL e intra-documento (`7` en prosa p.45 · `8:Causa y Efecto` en el árbol
  de menú pp.15/26/41, 7 chunks). **El criterio del guard es correcto; el defecto es la
  granularidad de la reparación.**
- Huella del guard en el FULL v3.2: **1/39 golds**.

## 2. Conducta actual (código, `src/rag/answer_planner.py:2745-2870`)

```
conflicts = build_answer_conflicts(query, chunks)
initial   = validate_answer_conflicts(answer, conflicts)
si no hay conflictos            -> not_applicable  (answer intacto)
si initial no es unsafe         -> pass            (answer intacto)
para cada bloque (split \n\n):
    si el bloque es unsafe -> parts[i] = aviso(es)      # BLOQUE ENTERO
final = validate_answer_conflicts(revised, conflicts)
si final unsafe -> fail_closed (mensaje + avisos) -> si aún unsafe -> mensaje mínimo
```

## 3. Cambio propuesto — escalera de reparación, de menos a más destructivo

Flag **`ANSWER_CONFLICT_SPAN_REPAIR`** (default `off`). Con flag off: **passthrough
byte-idéntico**, misma traza. Con flag on, para cada bloque unsafe se intenta, EN ORDEN:

1. **Redacción del valor** — se neutraliza la aserción conservando la frase: las
   ocurrencias de la forma `«N: <etiqueta de operación>»` pierden el `N:`
   («7: Causa y Efecto» → «Causa y Efecto»). El aviso se emite igualmente como párrafo
   propio inmediatamente después del bloque.
2. **Sustitución por línea** — si (1) no basta, se sustituyen SOLO las líneas unsafe del
   bloque (unidad natural en listas numeradas y viñetas markdown), conservando el resto.
3. **Sustitución por bloque** — conducta ACTUAL, sin cambios.

**Regla de aceptación de cada peldaño:** el resultado se re-valida con
`validate_answer_conflicts` a nivel de bloque; solo se acepta si deja de ser unsafe. Si no,
se escala al siguiente peldaño. La validación **whole-answer** y la escalera **fail-closed**
posteriores quedan EXACTAMENTE como están.

**Por qué es seguro por construcción:** el criterio de aceptación no cambia — es el mismo
validador, aplicado con la misma severidad. Lo único que cambia es que sobrevive texto que
ese mismo validador declara seguro. Ningún peldaño puede producir una salida que la conducta
actual habría rechazado.

**Traza nueva** (para el gate y observabilidad): por bloque reparado,
`{"stage": "redaction"|"line"|"block", "accepted": bool}` + contadores agregados. Con flag
off la traza es la de hoy, sin campos nuevos.

## 4. Invariantes (se testean, no se prometen)

- **I1 · inercia**: flag off ⇒ salida y traza byte-idénticas (las 53 pruebas de
  `tests/test_answer_planner.py` pasan sin tocarlas).
- **I2 · fail-closed intacto**: validación whole-answer y sus dos peldaños, sin cambios.
- **I3 · nunca peor**: ningún peldaño se acepta sin re-validación limpia del bloque.
- **I4 · aviso**: cada conflicto emite su aviso **una** vez (semántica `rendered_conflicts`
  actual) también cuando el peldaño aceptado es (1) o (2).
- **I5 · no vacíos**: ningún peldaño deja el bloque vacío ni borra el aviso.
- **I6 · idempotencia**: aplicar el guard a su propia salida no la cambia.

## 5. Gate PRE-REGISTRADO (antes de construir)

| id | qué mide | cómo | expectativa declarada |
|---|---|---|---|
| **G1** | inercia flag-off | suite completa + replay determinista del guard sobre los 39 answers del recibo con sus contextos servidos | 100% byte-idéntico; 3427/0 |
| **G2** | recuperación | A/B `hp017`, N=6 por brazo, ruta presente en la respuesta FINAL | off: 0/6 (hoy 0/3) · on: ≥5/6 |
| **G3** | seguridad | batería adversarial escrita a mano: asevera 7 · asevera 8 · directiva «selecciona 7» · directiva relativa «la primera opción» · forma de disclosure · bloque con ambos valores · valor en cita [F7] | flag on: `validate_answer_conflicts(salida)` limpio en **100%**, y aviso presente siempre que hubo conflicto |
| **G4** | no-desplazamiento corpus-wide | replay $0 del guard flag-on sobre los 38 golds restantes | 0 cambios (el guard no dispara ahí: huella medida 1/39) |

**Criterio de NO-GO:** cualquier fallo de G1/G3, o G2 con `on < 5/6`. G3 es el que manda: un
solo caso donde la salida flag-on quede unsafe mata el lever.

## 6. Alternativas consideradas y por qué se descartan

- **Servir el otro lado del conflicto (brazo serving-side)**: roza fila settled del
  diagnóstico s291c y, medido, **no quita el colateral** — con ambos valores servidos el
  bloque se sustituye igual salvo que el modelo escriba justo la forma de disclosure.
- **Relajar el registro `KNOWN_ANSWER_CONFLICTS` o el umbral del validador**: debilita la
  garantía. Además el conflicto está VERIFICADO en corpus (intra-documento), no es un falso
  positivo del registro.
- **Solo granularidad de línea (sin peldaño de redacción)**: recupera los pasos 2-3 pero
  **no** el hecho del gold, que vive en la línea infractora. Medido, no supuesto.
- **Reescritura por modelo del bloque conflictivo**: introduce llamada de modelo en un guard
  determinista always-on (coste, latencia y no-determinismo en el borde de seguridad).
- **No hacer nada (techo declarado)**: defendible por conteo (≤1 hecho de 131), pero hoy el
  bot BORRA un procedimiento de 3 pasos por un número dudoso; el coste de usuario es mayor
  que el punto de eval.

## 7. Riesgos declarados de entrada

1. **El validador define la seguridad.** Si es incompleto, el lever deja pasar texto que él
   no sabe leer. No se debilita nada, pero tampoco se refuerza: es un riesgo heredado que
   este cambio AMPLÍA en superficie (sobrevive más texto).
2. **Redacción determinista sobre prosa del modelo**: riesgo de artefactos («selecciona
   «Causa y Efecto»» puede quedar cojo si el modelo escribió otra construcción). Mitigación:
   la redacción solo actúa sobre la forma `N: <etiqueta>`, y cualquier otra forma escala al
   peldaño 2.
3. **Población medida = 1 gold**: el retorno en eval es ≤1 hecho. El argumento fuerte es
   cualitativo (procedimiento borrado), y debe declararse como tal, no vestirse de métrica.
4. **Superficie always-on**: el guard corre en todas las respuestas. La inercia flag-off
   (G1) es la red; el default se queda en `off` hasta que Alberto decida el ON.
5. **Registro de un solo elemento**: hoy solo existe el conflicto Pearl 7-vs-8. Si el
   registro crece, la escalera se aplica a más casos sin re-medir — el gate G3 debe
   re-correrse al añadir entradas al registro (queda escrito en el código).
