# s334 — Ataque autónomo a los MANUALES HUÉRFANOS: 2 lotes firmados (89 ids, 69 manuales)

**Qué se decide aquí:** si aplicar dos lotes `products_confirmar` sobre el catálogo
gobernado que quitan `candidate` a 89 productos, con el efecto medido de sacar **69
manuales de la orfandad** (245 → 176). Nada aplicado todavía: los dos dry-run están
en PASS y esto es lo que va al dúo ANTES del `--aplicar`.

**Encargo de Alberto (21-ago):** «sobre los 535 (aunque lo mejor creo que es
enfocarlo desde el punto de vista de *manuales huérfanos*), ¿puedes atacarlo de forma
autónoma para reducir el número de manuales sin modelo?». El reencuadre es suyo y es
el correcto: un candidate suelto no le sirve a nadie; un manual que no puede servir a
nadie es una pérdida contable.

---

## 1. La recomendación

Aplicar **dos** lotes firmados, en este orden:

| lote | ids | fabricantes | detector | dry-run |
|---|---|---|---|---|
| `pequenos` | 28 | detnov, fidegas, morley, sense-ware, spectrex, systemsensor, xtralis, zareba | 1759 → 1796 (+37/−0) | **PASS** |
| `notifier` | 61 | notifier | 1759 → 1872 (+113/−0) | **PASS** |

Sólo `products_confirmar`. **Cero altas, cero retiradas, cero `doc_map`, cero retags
en la DB.** La operación es la mínima que puede producir el efecto: quitar
`candidate` a filas que ya existen, ya tienen su documento en `doc_map` y ya tienen
cita verificada en ese documento.

Se aplican por separado porque el rollback es por lote: si algo se tuerce, el radio y
la reversión están acotados. No se parte en nueve (uno por fabricante) porque el
riesgo léxico que justificaría trocear se mide **por término**, no por lote, y el
censo ya lo hace término a término en los dos.

### La cadena de filtros, con la cifra que sobrevive a cada uno

```
601 candidates en cuarentena
 └─ 245 MANUALES huérfanos (fila de doc_map sin ningún id consumible)
     └─ 157 pares (id × manual) de clase A: nombrado, con marca, y con CITA
        verificada con frontera de palabra en su PROPIO documento (R4)
         └─ 118 ids DISTINTOS  ← los 157 eran pares, no ids: 39 ids atestan 2+ manuales
             └─ 110 tras apartar 8 con riesgo declarado (prefijo / etiqueta de familia R2)
                 └─ 89 tras la VERIFICACIÓN con el resolver real (G4)
                     → 69 manuales dejan de ser huérfanos
```

**Las dos cifras que corregí midiendo, no razonando** (y que enseño porque son la
misma clase de fallo que las guardas G1–G5 nombran): dije «149 ids limpios» cuando
eran **110** —contaba pares `(id × manual)`, no ids— y dije «89 manuales» cuando el
lote verificado desbloquea **69**, porque varios de los 89 ids caen en el mismo
manual. Ninguna de las dos se ve razonando: salen de contar.

---

## 2. La verificación que mató 21 de mis propios candidatos (guarda G4)

La evidencia de clase A miraba **el texto del documento**. Eso demuestra que el
documento nombra el producto; **no** demuestra que promoverlo haga que el bot alcance
el manual. Son cosas distintas y yo las había juntado.

`scripts/s334_huerfanos_verificacion.py` ejecuta `resolve_query(canónico)` con el
catálogo real, antes y después de la promoción simulada, y exige el cambio en los dos
sentidos: antes NO puede traer su `source_file`, después SÍ. Resultado sobre los 110:

| veredicto | ids | qué significa |
|---|---|---|
| **DESBLOQUEA** | **89** | la consulta por el modelo no traía su manual y ahora sí ← lo único que entra |
| DETECTA_SIN_FUENTE | 14 | el término entra en el detector y el manual **no llega** |
| NI_DETECTA | 5 | el detector no puede ni verlo: promover es inerte |
| YA_ALCANZABLE | 2 | su manual ya salía por otra vía |

Los 21 descartados no son ruido: son **tres fallos con nombre**, y ninguno se ve
desde el texto del documento.

**H · homónimo abierto (10 ids).** `morley:sp-200` y `notifier:sp-200` comparten
token; su fila de `homonyms.jsonl` es `candidate: true, politica: fail-open`, así que
`_cat.resolve()` devuelve `expand: False, ids: []`. Promover el producto deja el
término **en** el detector y el manual **fuera** — riesgo léxico a cambio de nada.
Decidir si el SP-200 de Morley y el de Notifier son el mismo producto rebrandeado es
adjudicación (R8), no mecánica. Afecta a MCX-55M, MMX-10M, NFS8REL, SP-200 (Morley ↔
Notifier) y PL4 (Notifier ↔ Sensitron).

**G · gemelo (6 ids).** El token ya resuelve a **otro id**: `ID-3000` →
`notifier:id3000`, `ST.PL4+` → `notifier:stpl4`, y `TG-1020` → **`desico:tg-1020`**,
que ni siquiera es la misma marca. El detector nunca llega al candidate. Es el mismo
patrón de gemelos que DEC-173 encontró en `chunk_index`, ahora en el espacio de ids.
`ST.PL4+` es peor: su gemelo también es `candidate`, así que redirigir tampoco
desbloquearía.

**N · no detectable (5 ids).** `00051`, `00052`, `03382`, `03383` son referencias
puramente numéricas y `_add()` excluye los tokens digit-only **a propósito**;
`EEV(2)` lleva paréntesis y `detect()` devuelve lista vacía.

---

## 3. El hueco del gate que encontré y tapé (seam 1)

El censo de `s324_lote_firmado_writer.py` mide el detector, `allowed_sources` y los
ids de las 51 gold. **No mide `models`** — y `models` es lo que alimenta
`_filter_to_query_models`, el filtro que sí **estrecha** el pool de chunks.

Importa porque en producción el brazo es `IDENTITY_RESOLVE_POLICY=replace` (perfil
C1, fail-fast en `release_profiles.py`), no `add`. Bajo `replace`, resolver un token
lo **retira** de `models`. Ése es literalmente el mecanismo con el que LEVER2 regresó
hp009 (DEC-091b): quitar el token paraguas vetó los genéricos correctos. Un lote de
89 promociones puede reproducirlo sin que el gate lo vea, porque el gate mira
`allowed_sources`, que sólo **añade** (unión-protectora, `retriever.py:2369-2374`),
y no `models`, que **resta**.

`scripts/s334_huerfanos_seam1.py` lo mide: `apply_to_models(extract_product_models(q),
resolve_query(q))` antes y después, bajo la política de producción, sobre 52 gold +
126 consultas reales = **151 únicas**.

```
lote pequenos:  PIERDEN 0 · GANAN 2   (ambas son la misma gold: +cs4)
lote notifier:  PIERDEN 0 · GANAN 0
```

**Cero pérdidas de modelo en las 151 consultas, en los dos lotes.** Es la evidencia
más fuerte que tengo y es la que el gate no daba.

---

## 4. Lo que el censo del gate sí dice

Los dos lotes: **0 gold pierden**, **0 disparos** en los 34 negativos sintéticos, **0
términos que salgan** del detector, findability N/A (no hay retags).

Ganancias reales, no teóricas:
- `pequenos`: una gold gana `fidegas:cs4` + 1 fuente. **CS4 es un fallo documentado**
  — `HISTORY.md:1606` y DEC del FOCO 1: «CS4 es `candidate:true` → ni uno ni otro la
  reconoce». Este lote lo cierra.
- `notifier`: una gold gana `notifier:nfs-supra` y **+9 fuentes**
  (`HLSI-MA-025 Guia Rapida NFS_Supra_ES`, `HLSI-MN-025-I…`, las 4 notas de
  `NFS-SUPRA-VSN…`). La pregunta es «¿qué resistencia de fin de línea hay que
  instalar en las líneas de zona de la central NFS Supra?» — o sea, la consulta de
  técnico exacta para la que existe el manual.

---

## 5. Alternativas consideradas, y por qué se descartan

**(a) Promover los 601 candidates de la cuarentena.** Es lo que Alberto preguntaba de
entrada. NO: 181 son `unresolved:` (sin marca — asignar fabricante es adjudicación),
y el resto no tiene el manual huérfano detrás, así que no paga el riesgo léxico. El
reencuadre a manuales es lo que hace el subconjunto defendible.

**(b) Promover los 118 de clase A sin la verificación G4.** Es lo que yo iba a hacer.
Habría metido 21 términos en el detector con cero beneficio, 10 de ellos rebrands sin
adjudicar. El gate habría dicho PASS: no mide «¿sirvió de algo?».

**(c) Resolver H y G en el mismo lote** (adjudicar rebrands, redirigir gemelos). NO:
son decisiones de datos, no mecánica, y R8 dice que la grafía la manda el fabricante.
Van a `DECISIONES_PENDIENTES_ALBERTO.md` con la evidencia ya reunida.

**(d) Un lote por fabricante (nueve).** NO: el riesgo léxico se mide por término y el
censo ya lo hace término a término. Nueve censos son 9× el coste para el mismo dato.
Dos lotes bastan para acotar el rollback.

**(e) Multimodal para recuperar los nombres perdidos.** Aparcado: la sonda s334 quedó
**inconclusa** y el dúo r41 tumbó sus dos lecturas. No se apoya nada en ella.

---

## 6. Gaps y riesgos, declarados de entrada

1. **No hay medición end-to-end de retrieval/generación.** El censo lo declara
   (`no_medido`). Los instrumentos son las 51 gold (0 pérdidas) y el seam 1 (0
   pérdidas en 151), no un FULL. **Los 89 productos nuevos no tienen gold propia**:
   sé que no rompen lo medido, no que respondan bien.
2. **19 términos entran con `sin_digitos`** (`ICAM IAS`, `VESDA VLI`, `WinHost`,
   `AgileIQ`, `Mini Vista`, `SensorTube`, `Securnet Plus`, `RHistorico.exe`…). El
   gate sólo hace STOP con `palabra_comun` y ninguno lo es, pero son nombres de
   producto multi-palabra y el riesgo de disparo en prosa es mayor que con un
   `MAD-491`. **`RHistorico.exe` y `SensorTube` son los dos que menos me gustan.**
3. **Los 34 negativos sintéticos los escribí yo.** Miden disparo léxico, no
   cobertura de tráfico. El contrapeso real son las 126 consultas de `query_logs`,
   donde la única detección nueva de cada lote es un **verdadero positivo**.
4. **19 términos entran con sombra de otros existentes** (`AM-200`/`AM-2000`,
   `NAS-2`/`NAS-20`, `PL4-E`/`PL4`, `SMART 3G`/`SMART 3 GD3`). Creo que el
   `(?![a-z0-9])` del core los separa —en «SMART 3 GD2» el match de `SMART 3G` muere
   en la D— pero **es un razonamiento mío sobre una regex, no una medida**. Es el
   punto donde más quiero que el dúo me contradiga.
5. **2 de los 68 documentos implicados no están `active`** en `documents`. Sus ids
   siguen en el lote: promoverlos no daña, pero el manual no se «desbloquea» de
   verdad. Están declarados en `G3_documentos.no_active`.
6. **89 productos entrarán sin `clasificacion`**, así que salen en la Wiki como «(sin
   clasificar)». No es regresión —856 de los 1.024 consumibles actuales tampoco la
   tienen— pero empeora la proporción.
7. **176 manuales siguen huérfanos** después de los dos lotes. 53 no tienen ningún
   candidate (sus ids están retirados o son redirect: otro problema), 181 pares son
   `unresolved:`, y el resto cae en H/G/N/E/B.

---

## 7. Por qué es BP + estructural + escalable

**Estructural**: no toca el resolver, ni el retriever, ni añade una regla especial.
Corrige el **dato** —el estado `candidate` de 89 filas— por la puerta que ya existe
(`catalog_store.write_jsonl` → validador del conjunto) y con el gate que ya existe
(freeze sha×4 + fingerprint, build-validar-backup-swap, rollback). Cero código nuevo
en el path de producción.

**BP**: la unidad de decisión es la evidencia por fila (cita verificada en su propio
documento, R4) y la unidad de aceptación es el efecto medido (`resolve_query` antes y
después). Ninguna fila entra porque «parece un modelo».

**Escalable a 30+ fabricantes**: los tres filtros nuevos (H, G, N) y la verificación
G4 son **mecánicos y agnósticos de marca** — se ejecutan igual sobre el fabricante 31
sin escribir una línea. Y el patrón queda como procedimiento: *toda promoción masiva
se verifica con el resolver antes de escribirse*, que es lo que faltaba.

**Lo que NO es**: no es un lever de retrieval ni de síntesis, así que no le aplica el
digest de levers ni ningún «settled». Es reparación de datos con efecto medido en el
seam 1 y el seam 2.

---

## 8. Qué le pido al dúo

1. ¿La verificación G4 mide lo que digo, o hay una vía por la que un
   `DESBLOQUEA` no se traduzca en que el técnico reciba el manual?
2. El gap 4 (sombras y el `(?![a-z0-9])`): ¿aguanta, o hay un token del lote que
   pisa a uno existente?
3. ¿Hay un tercer seam que no estoy mirando, como no miraba `models` hasta hoy?
4. ¿Los 21 descartados están bien descartados, o alguno es promovible con una
   operación distinta que no he considerado?
5. `sin_digitos` (gap 2): ¿es `palabra_comun` el umbral correcto para el STOP, o el
   gate debería endurecerse antes de este lote?
