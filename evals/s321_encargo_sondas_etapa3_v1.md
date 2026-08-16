# ENCARGO — Sondar los 8 hechos «servido y omitido» sin medir · etapa 3 / población de lever B

> **Para la sesión que lo ejecute.** Escrito en s321 (16-ago-2026) con el FULL recién corrido y la
> sonda endurecida. Arranque canónico normal (PLAN → DECISIONS → digest inyectado) **y además leer
> `DEC-175` antes de nada**: es la decisión a la que sirve esta medición.

---

## 1 · Qué decisión sirve (la pregunta cero, ya pasada)

`DEC-175` cerró el lever B por **POBLACIÓN**: 1 gold de 39. En s321 se reabrió la puerta —la cota
inferior subió a **≥2**— pero **sin medir**: 8 de los 12 `synthesis-miss` del FULL nunca se han
sondado. Los dos desenlaces cambian algo, y por eso el gasto está justificado:

- **≥3-4 alcanzables** → la población deja de ser el bloqueador; el lever de etapa 3 vuelve a ser
  **diseñable** (con dúo, flag-off y gate — no antes).
- **0-1 alcanzables** → la etapa 3 se **cierra con evidencia**, no por cansancio. Y `DEC-175` pasa
  de «reabierta sin medir» a «reabierta y medida: sigue sin población».

**No hay tercer desenlace en el que el resultado no mueva nada.** Si en algún momento la sesión se
descubre midiendo «para tener el dato», parar: eso es rigor mal dirigido.

**Coste**: ~$1 y minutos por hecho ⇒ **~$8 y ~1 h** de reloj. Regla del Protocolo 4: ningún lever de
serving/síntesis se diseña sin esta sonda antes.

---

## 2 · Los 8 (fuente: `evals/s100_factlevel_full_v3_20260816.yaml`, FULL del 16-ago)

Los 12 `synthesis-miss` menos los 4 ya sondados (`hp017#2` ✅ · `hp003#4` ✅ · `hp011#2` ❌ ·
`cat017#2` ya OK). Los 8 restantes son **todos submotivo `omitted`** salvo donde se indique:

| # | hecho | `valor` | raw · srv · pool · →gen | modo propuesto | `--span-grep` propuesto |
|---|---|---|---|---|---|
| 1 | `cat001#3` (PEARL, equipos por lazo) | `32 / 25 / 20` | 2 · 1 · sí · sí | `appendix` | `25 equipos\|20 equipos\|32 equipos` |
| 2 | `cat008#3` (M710/MI-DMMI, terminales) | `1/2/3/4 lazo; 6-7 entrada A` | 1 · 1 · sí · sí | `appendix` | `Entrada del lazo\|Salida del lazo` |
| 3 | `cat016#1` (CAD-150, alta de detector) | `menu ZONA + ELEMENTO` | 1 · 1 · sí · sí | `appendix` | `ELEMENTO\|men[úu] ZONA` |
| 4 | `hp005#3` (ID3000, salida de sirena) | `CIRCUITO SIRENA` | 5 · 1 · sí · sí | `appendix` | `CIRCUITO SIRENA` |
| 5 | `hp009#0` (Morley ZXe, fin de línea) | `Retorno` | 1 · 1 · sí · sí | `appendix` | `Retorno\|bucle cerrado\|Inicio Lazo` |
| 6 | `hp015#0` (CCD-103, desactivar detector) | `convencional` | 3 · 1 · sí · sí | `appendix` | `convencional` |
| 7 | `hp015#2` (misma pregunta) | `32` | 3 · 2 · sí · sí | `appendix` | `32 detectores\|32 equipos` |
| 8 | `hp017#1` (PEARL, retardo) | `instruccion de entrada` | **0** · 1 · **no** · sí | `appendix`, y si falla `serve` | `[Ii]nstrucci[óo]n de [Ee]ntrada` |

**Nota sobre el 8**: `hp017#1` es el atípico — `raw=0` y `in_pool=False`, y sin embargo `srv=1`:
llega **solo por fila apendizada de coverage** (`same_blob_structural_neighbor_coverage_v1`). Su
carrier no está donde se le busca por léxico. Si `appendix` no construye, hay que resolver el chunk
apendizado a mano (los ids del `appended_lane` del gold están en el YAML del FULL) y usar `serve`.

**Ojo con 6 y 7**: son del **mismo gold** (`hp015`). Si los dos salen igual, cuentan como **una**
observación de la clase para efectos de población, no dos — declararlo al agregar.

---

## 3 · Trampas concretas (las tres me costaron tiempo en s321)

1. **`appendix` puede no ser construible.** Pasó con `hp013#1`: «*span no encontrado en los 12
   servidos con /PWR-R/ — el oráculo no es construible*». No es un fallo de la sonda: es que el
   carrier ya no se sirve. **Fallback**: localizar los carriers y correr `serve`.
2. **`like` sobre la columna `id` (uuid) NO funciona** — devuelve error, no vacío. Para resolver un
   id corto a uuid completo: consultar por `source_file` + `chunk_index`. La sonda **exige uuids
   completos** en `--inject` («ids no resolubles desde el pool del recibo»).
3. **Verificar el carrier ANTES de inyectar** (Protocolo 4): los `chunk_index` pueden estar
   **duplicados** y un censo previo puede señalar el gemelo sin el dato. Leer el `content` del chunk
   y comprobar que contiene el valor *y* el predicado, no solo el número.

**Y la guarda que hay que respetar, no rodear**: para emitir un **NO_ALCANZABLE** la sonda exige
`--cobertura-verificada '<cómo verificaste que el carrier cubre el hecho>'`. Sin eso devuelve
`INCONCLUYENTE_SIN_COBERTURA_ATESTADA`, que es su trabajo. No inventar la atestación: si no se puede
verificar la cobertura, el veredicto honesto es INCONCLUYENTE.

---

## 4 · Cómo se corre

```bash
python scripts/s293_reachability_probe.py <qid> <qid>#<idx> appendix --span-grep "<regex>" 3
python scripts/s293_reachability_probe.py <qid> <qid>#<idx> serve --inject <uuid>[,<uuid>] 3 \
    --cobertura-verificada "leído chunk <id> (<doc> p<N>): '<cita>' — cubre <valor> y el predicado <...>"
```
Salida: `evals/s293_reachability_<qid>_<fact>.json` (uno por hecho). Juez canónico
`judge_conveyed21` K=5, `THRESH_FIRM=4` — no tocar la vara.

**Lectura del veredicto** (`scripts/reachability_verdict.py`): `ALCANZABLE` si alguna rep ≥4/5 en el
brazo oráculo. Un `NO_ALCANZABLE` solo es emitible con **prueba de entrega + cobertura atestada**;
cualquier otra cosa es `INCONCLUYENTE_*` y **no cuenta como negativo** en el agregado.

---

## 5 · Qué producir

1. **Un recibo por hecho** (los 8 JSON).
2. **Un agregado** `evals/s321_poblacion_etapa3_v1.md`: alcanzables / no / inconcluyentes, con el
   ajuste de `hp015` (dos hechos, un gold) y la **cota inferior de población** resultante.
3. **Fila en `DEC-175`**: hoy dice «cota inferior = 3 … falta sondar `hp013#1`» y ya está actualizada
   a ≥2 con el resultado de `hp013#1`. Añadir el nuevo número **con su fecha y recibo**.
4. **`docs/LEVER_DIGEST.md` fila «Etapa 3 / síntesis»**: se **sobrescribe in-place** si el veredicto
   cambia (cierre de sesión, paso 2 del CLAUDE.md). Hoy dice «REABIERTA EN LA PUERTA DE POBLACIÓN».
5. **Si el resultado es ≥3-4 alcanzables**: **NO diseñar el lever en esa misma sesión**. El diseño es
   otro trabajo (dúo completo, flag-off, gate pre-registrado). Dejarlo como recomendación con la
   población medida delante.

---

## 6 · Lo que este encargo NO es

- **No** es re-abrir DEC-173 ni re-litigar el lever B: es medir su población, que es la única pata
  que quedó sin medir.
- **No** es tocar el instrumento. Si aparece un defecto de la sonda, se anota como deuda y se sigue
  (o se para y se arregla con dúo, pero no se parchea de paso).
- **No** incluye `hp001#2` ni `cat011#1` ni `cat013×2`: son otras clases (retrieval `within-doc`,
  control sin modelo, y FN family-scoped verificada 10 veces). Ver
  `evals/s321_full_analisis_fallos_v1.md` §5.

---

## 7 · Contexto mínimo para arrancar

- Análisis que origina el encargo: `evals/s321_full_analisis_fallos_v1.md`
- Recibo del FULL: `evals/s100_factlevel_full_v3_20260816.yaml` (fila `2026-08-16b` del scoreboard)
- Sondas ya hechas: `evals/s293_reachability_{cat017_cat017_2,hp003_hp003_4,hp011_hp011_2,hp013_hp013_1,hp017_hp017_2}.json`
- Decisiones: `DEC-173` (la sonda como puerta) · `DEC-175` (la población) · `DEC-186` (en revisión,
  **no citar su cifra**) · `TECH_DEBT #75` (el bug del juez que la originó)
