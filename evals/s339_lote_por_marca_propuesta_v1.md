# Propuesta — parametrizar por MARCA el lote de clasificación del catálogo

## Contexto
El lote de clasificación se validó sobre la vista Notifier. Dos hitos que NO hay
que fundir (el revisor lo marcó): **DEC-279** firma el lote — 361 filas, gate
14/14, cobertura 71,9% — y la **adenda del 22-ago** añade la recuperación de los
98 parse-fail: 411 filas, gate 100% n=17, cobertura 81,9%. El contrato de la casa
exige que el método escale a 30+ fabricantes sin fricción por fabricante. Al ir a
parametrizarlo aparecieron DOS fallos latentes que la marca incrustada ocultaba.

## Qué cambia
1. Nuevo `scripts/lib_lote_marca.py`: rutas de recibo por marca, provenance
   DERIVADA, candado de vista, normalización de marca.
2. Los 5 scripts del pipeline aceptan `--marca` (default notifier).
3. `s336_censo_diana.py`: el patrón de familias-panel (`^(NFS|ID\d|AFP|NCA|AM\d|ONYX)`,
   Notifier puro) pasa a `--familias-panel`; sin patrón el proxy baja, el suelo del
   gate de efecto baja y se AVISA por stdout + se estampa en el recibo.
4. `s336_censo_diana.py`: guarda anti-pisado — si el recibo existe, aborta salvo
   `--force` (re-correrlo contra el catálogo ya escrito desploma la diana y pisa
   el artefacto citado por la provenance de las filas).
5. `s336_writer.py`: (a) la constante PROV con los sha de Notifier incrustados se
   sustituye por provenance derivada de los recibos de ESTA corrida; (b) CANDADO:
   antes de escribir, todo id elegible debe pertenecer a `_productos_marca(cat, marca)`
   — si alguno cae fuera, aborta sin tocar nada (recibos cruzados entre marcas);
   (c) conteos y replay de efecto parametrizados (`--replay-categoria`).

## Decisiones con motivo
- Los recibos de Notifier CONSERVAN su nombre histórico (`s336_*_v1.json`) porque
  están citados en DEC-279; las marcas nuevas llevan sufijo. Asimetría deliberada.
- La guarda anti-pisado va sólo donde el artefacto es PRE-REGISTRO (censo: fija el
  suelo antes de ver resultados) o gold (GT). Gate y población son recomputables
  (verificado: re-correr el gate da byte-idéntico salvo fecha).

## Verificación hecha
- 14 tests nuevos (`tests/test_s336_lote_por_marca.py`), incluido guard-test que
  pinea el sha del censo de Notifier (37cc4aa409ab484f) que prometen las 411 filas.
- Gate re-corrido: PASS 100% n=17, 411 elegibles, distribución idéntica.
- Writer dry-run: 0 escribiría / 411 saltadas (idempotencia).

## Gaps declarados
- Una marca sin `--familias-panel` tiene gate de efecto MÁS LAXO. Mitigado por
  visibilidad (aviso + recibo), no por construcción.
- El candado compara contra la vista de HOY: si el catálogo cambia entre el censo
  y la escritura, un id retirado entre medias se leería como intruso (aborta, que
  es el lado seguro, pero es fricción).
- No se ha corrido ninguna marca nueva todavía: el método está parametrizado, no
  probado end-to-end sobre una segunda vista.


---

## Revisión adversarial (Fable 5, standalone) — veredicto **NO SÓLIDO**, 6 hallazgos

Tiering declarado: impacto MEDIO en zona de dolor (catálogo) → revisor de código.
El cross-model (Sol) se reserva para ALTO; esto no toca el bot ni el dato servido.
**Los 6 hallazgos son ciertos** — verificados contra el código antes de actuar
(Regla C), no aceptados por autoridad. Adjudicación (Regla F: decido yo):

| # | hallazgo | verificado | qué hice |
|---|---|---|---|
| 1 | **[crítico]** El recibo de ESCRITURA no tenía guarda, no es recomputable y YA fue pisado: la recuperación del 22-ago machacó el del lote original (361/PASS) | SÍ — el vivo decía `escritas: 50, PARCIAL` con `antes.clasificados: 364` | ACEPTADO. Recuperado de git a `_r1`; el writer ahora ROTA (`_r2`, `_r3`…) en vez de sobrescribir — abortar habría roto su uso incremental legítimo, que es la distinción que faltaba |
| 2 | **[medio]** La cobertura mide la CORRIDA, no el acumulado: una pasada incremental emite «PARCIAL» con el lote real en PASS | SÍ — 50/502 = 10% «PARCIAL» con 411/502 = 81,9% en el catálogo | ACEPTADO. El veredicto se calcula ahora leyendo el catálogo (filas del lote / diana), no el delta. Verificado: **81,9% → PASS** |
| 3 | **[medio]** `normaliza_marca` duplicaba y divergía del `_norm_marca` del join (NFKD + `[^a-z0-9]`) | SÍ — `Pepperl-Fuchs`→`pepperl-fuchs` vs `pepperlfuchs`; también Morley-IAS y acentos | ACEPTADO, fix de RAÍZ: delega en el normalizador del join. Reimplementarlo era la forma cara de tener dos |
| 4 | **[medio]** La propuesta decía «guarda en censo o gold» y sólo existía en el censo | SÍ — sin guarda sobre el GT | ACEPTADO: el gate aborta si no hay GT congelado para la marca |
| 5 | **[menor]** El efecto se mide parseando el RENDER (bullets): acoplado a la UI | SÍ, aunque fail-closed | ACEPTADO PARCIAL: se conserva el conteo sobre el render (es lo que ve el técnico) y se CONTRASTA con el conteo sobre el catálogo; divergencia = instrumento roto. Hoy 46 = 46 |
| 6 | **[menor]** Atribuí a DEC-279 cifras que son de la adenda | SÍ | ACEPTADO: corregido arriba |

**Lo que el revisor confirmó a favor**: provenance derivada y candado con tests
reales; el monkeypatch de `catalogo_cargado` funciona; guarda del censo con test
de subprocess; el gap del suelo laxo, declarado y no escondido.

## Verificación final (tras los arreglos)

- 25 tests (`tests/test_s336_lote_por_marca.py`), incluidos los que pinean lo
  destapado: normalizador idéntico al join para 6 grafías, rotación de recibo,
  guarda de gold, y el recibo del lote original recuperado.
- Writer re-corrido sobre Notifier: 0 escritas (idempotente), **cobertura 81,9%
  → PASS**, 46 servidas = 46 en catálogo, catálogo byte-idéntico.
- Gate re-corrido: PASS 100% n=17, distribución idéntica (sólo cambia la fecha).
