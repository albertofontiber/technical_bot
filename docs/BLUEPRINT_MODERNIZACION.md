# Blueprint de modernización de `src/` — mapa objetivo + lotes (s300)

> **Qué es.** El destino estructural del código de producto y la secuencia de lotes para
> llegar, SIN reescritura. **La parte ejecutable del contrato NO vive aquí**: vive en
> `tests/test_import_contract.py` (matriz de dependencias, excepciones con trigger de
> retiro, ciclos permitidos, cuarentena de la isla) — este doc es el *porqué* y la
> secuencia; el test es el *qué*, y falla en CI si el árbol se desvía. Si discrepan,
> manda el test (se cambia por PR con dúo, como toda frontera).
>
> **Base de evidencia**: censo de 6 agentes + síntesis + 3 verificaciones adversariales
> (workflow s300) — grafo AST de los 113 módulos, alcanzabilidad desde el `Procfile`,
> censo de sellos C1/P1, censo de ~89 flags, acoplamientos frontera y seams existentes.
> Contrato del proyecto: BP + estructural + escalable a 30+ fabricantes — y la escala
> por fabricante aquí es por DATOS/config, no por código: este blueprint protege eso,
> no lo sustituye.

## 1. Diagnóstico (medido, no sentido)

`src/` = 42.210 líneas / 113 módulos. NO es una bola de barro: 2 ciclos de import
(deliberados y comentados in-situ), ~1% duplicación, seams limpios ya extraídos
(`serving_pipeline` con inyección de dependencias, `coverage_runtime` como fachada,
`src/orchestrator/` extraído con paridad byte a byte — DEC-136→153c→156a — y
`release_profiles` con contrato fail-fast). El problema real es **ACRECIÓN**: ~30% de
`src/` no es alcanzable desde el entrypoint de producción — 35 módulos de «isla harness»
(solo scripts/tests los importan), lanes que el contrato de release prohíbe encender, y
la verdad de configuración viviendo en un script de eval. La causa raíz: los
experimentos sedimentaban dentro de `src/` porque **nada lo impedía**.

## 2. El mecanismo central: la arquitectura como invariante de CI (L0 — HECHO)

`tests/test_import_contract.py` — stdlib `ast` + pytest, sin dependencia nueva. Nace
VERDE sobre el árbol actual con **6 excepciones (8 aristas), verificadas exactas** por
enumeración adversarial independiente. Sus piezas: matriz direccional de paquetes ·
excepciones con ancla y trigger de retiro · 2 ciclos permitidos (ninguno nuevo, y un
ciclo que CRECE también falla) · cuarentena de la lane vetada (`rerank_pool_coverage`,
solo sus 3 deudores E3a-c) · **cuarentena LÓGICA de la isla** (ningún módulo vivo puede
importar los 35 — la garantía estructural contra la acreción llega el día 0, antes de
mover un solo fichero) · precondición de 0 imports dinámicos (lo que hace fiable el
análisis estático, re-verificado por el propio test) · **trinquete**: cada excepción
debe SEGUIR existiendo — retirar la arista obliga a borrar la excepción en el mismo
diff; la lista solo encoge y el retiro queda visible en el PR. El trinquete además hace
al test no-vacuo: prueba que el recolector ve las aristas que dice vigilar.

Matriz (importador → puede importar de):
`raiz→{raiz}` · `ingestion→{raiz,ingestion}` · `rag→{raiz,ingestion,rag}` ·
`reingest→{raiz,ingestion,reingest}` · `orchestrator→{raiz,rag,orchestrator}` ·
`bot→{raiz,rag,orchestrator,bot}` · nadie importa `bot` · `src` no importa
`scripts/tests/evals` · el producto no importa la isla.

## 3. Mapa objetivo (estado final)

- **`src/` = solo producto** (113 → 82 ficheros): raíz transversal (config,
  release_profiles, logging_db, version, +`flags.py`) · `bot/` transporte ·
  `orchestrator/` turno conversacional — `fake_convo_store` se queda por DISEÑO, no
  por alcanzabilidad (el dúo cazó la justificación circular): es el fake first-class
  del trío contrato/fake/real de `convo_store`, parte de la superficie que sus
  consumidores usan para tests herméticos; candidato a reubicar SI el trío se
  re-empaqueta, con trigger propio · `rag/` serving core 69→40 módulos
  (38 vivos + 2 anclados por el probe sellado; +`catalog_store` graduado, + los 2 del
  split L2c) · `ingestion/` frontera de datos compartida (+`embed.py`) · `reingest/`
  pipeline CLI offline.
- **`harness/` = paquete top-level NUEVO fuera de `src/`** con 33 de los 35 módulos
  isla (los 2 anclados por el probe sellado se quedan — ver L2a).
  **Alternativa barata considerada y comparada** (exigencia del veredicto de
  proporcionalidad): la cuarentena lógica del contrato ya da la GARANTÍA sin mover nada
  — y por eso L0 la trae desde hoy. El movimiento físico paga aparte: (a) legibilidad
  (`src/rag/` 69→38: leer el producto deja de exigir saber qué es producto); (b)
  `_implementation_module_index` del gate C1 escanea `scripts/`+`src/` — la isla DENTRO
  de `src/` sigue siendo candidata a colarse en closures; fuera, no; (c) el destino da
  casa a los experimentos futuros (ataca la CAUSA de la acreción, no solo su síntoma).
  Criterio de éxito de L2a, declarado: **suite + contrato + smoke verdes** — NO «los
  540 scripts one-shot importan» (no corren en CI; un import roto en un s2XX histórico
  se descubre al re-ejecutarlo, y es aceptable en instrumentos).
  Destinos descartados: `evals/lib/` (evals/ es registro, no código), `scripts/lib/`
  (scripts/ debe seguir no-importable por producto), sub-paquetes (contra el idioma
  plano del repo; sin colisiones de nombre entre los 35).

## 4. Secuencia de lotes (cada uno: PR + paridad + suite + dúo)

Método transversal: el del orquestador (DEC-153c/MT-0a) — nunca seam paralelo, siempre
reuso; byte-invariante; los ajustes de sello **enumerados ANTES de mover** (los sellos
históricos jamás se reescriben — DEC-147 «version, don't relax»). El sello son 53
entradas (42 de `src/` + 11 de `scripts/` — la cifra completa importa: dos hallazgos
ALTOS del veredicto vinieron de mirar solo los 42).

- **L0 — el contrato (HECHO, este PR).** Sello intocado. El censo convertido en
  invariante ejecutable antes de mover nada.
- **L1 — graduación de `catalog_store` (retira E1).** `git mv` a `src/rag/` +
  `from . import catalog_store` (preserva `R.catalog_store.*` de ~20 asserts). Sin
  shim (dos copias crean ambigüedad real en `_implementation_module_index`). Migran los
  6 scripts importadores + 2 tests **+ el literal de ruta
  `tests/test_s274_bloquesCD_prereg.py:156`** (lee el fichero VIVO — se actualiza; el
  assert `:152` sobre el prereg histórico NO se toca: el YAML es registro). Sello:
  entrada `:295` → ruta nueva, ELIMINAR la entrada dinámica `:403`, regen release
  config. **⚠ `ci.yml:61` invoca `scripts/catalog_store.py` por ruta — se actualiza en
  el MISMO PR** (hallazgo del veredicto: sin esto, L1 rompe su propio CI). Assessment:
  `pipe_sha` cambia → smoke + fila nueva en el scoreboard.
- **L2a — isla → `harness/` (mueve 33 de los 35; 2 se quedan ANCLADOS).**
  Hallazgo ALTO del dúo, en dos tiempos: (1) `scripts/s270_etapa2_probe.py` (SELLADO,
  dynamic-import del scorer) importa `visual_gold` (:159, :806) y `omission_correction`
  (:336) en function-local — invisibles al verify; y (2) NO se pueden re-declarar esas
  aristas apuntando a `harness/`: el MECANISMO del gate rechaza todo path fuera de
  `scripts/`|`src/` (`_implementation_module_name`, `s277_c1_p1.py:1211-1216`, HOLD) —
  y tocar el mecanismo es línea roja de este blueprint. Resolución: **`visual_gold` y
  `omission_correction` NO se mueven** — quedan en `src/` bajo la cuarentena lógica de
  `ISLA` (que sigue siendo de 35), con trigger declarado: se moverán si el probe se
  re-sella/versiona o el gate C1 se retira. `src/rag/` queda 69→40 (38 vivos + 2
  anclados). Más anclas de ruta del movimiento: `test_s117_m28` (`:17/:29/:36-39/:103`
  — el `:103` es un sha de RUTA literal), `test_s210:87`, y el monkeypatch por string
  dotted de `test_frontier_visual_runtime_v3:64`. El PR corre `verify_release_config`
  para PROBAR el closure, no para suponerlo. El contrato L0 ya prohíbe importar
  `harness.*` desde `src/` SIN lista de excepciones posible — la regla nació cerrada
  antes de que `harness/` exista.
- **L2b — `src/flags.py` (RECORTADO por proporcionalidad).** Registro declarativo de
  los ~89 flags + `snapshot()` sin secretos + test de completitud + pin de `DEMO_FLAGS`
  contra el registro. **Alcance honesto de esas garantías** (dúo): el test de
  completitud es NOMINAL — grep de `os.getenv`/`os.environ` en `src/` contra el
  registro: garantiza que no hay call-site textual sin registrar, NO equivalencia
  semántica de defaults/parsing entre lectores no migrados; y el pin de `DEMO_FLAGS`
  detecta NOMBRES no registrados (pins fantasma por nombre), no valores erróneos.
  **SIN migrar lectores sellados al accessor** (0 regen de sello): los lectores migran
  oportunistamente cuando otro lote ya toque su fichero. La divergencia harness↔Railway
  detectada (p. ej. `OBLIGATION_WARNING_APPENDIX` pineado off en el harness, shipped
  on) queda visible en el pin, no corregida a ciegas.
- **L2c — split del doble-inquilino (retira E3a-c).** `rerank_pool_coverage` →
  `pool_selection.py` (motor compartido) + `obligation_warning.py` (reserva VIVA en
  v3/v4) + residual = la lane vetada. **Pendiente-de-diseño declarado**: la partición
  se hace a nivel SÍMBOLO (~20 símbolos; E3b importa 8 nombres, no 4 — incluidos
  `LANE as POOL_LANE` y `WINDOW_CHARS`) y el residual será en la práctica re-exports
  para los monkeypatch de sus tests — un shim, y se declara como tal (asimetría con L1
  justificada: aquí el shim es intra-`src/` y temporal hasta que la lane vetada muera o
  nazca). Sello: +2 entradas, **−1 obligatoria** (`:330` sale del manifest o el gate
  revienta por igualdad exacta). Diseño fino en su PR, con dúo.
- **L3 — `embed.py` → `src/ingestion/` (retira E2, el más caro en sellos, el último).**
  Cierra que cada query de producción ejecute un módulo del pipeline offline. Sello:
  entrada `:346` + las DOS dinámicas `:391/:402` + **el propio
  `s277_c1_p1_product_adapter.py` (SELLADO) importa `src.reingest.embed` en `:1204` y
  se edita también** (hallazgo ALTO) + `test_s277_c1_p1_runner.py:1854/:1951-1953/:4135-4143`
  + `test_s277_c1_p1_product_adapter.py:133` + `test_s117_m28:57-59` + **~13 scripts
  vivos** que importan `src.reingest.embed` (gate.py, enunciados_pass.py, …) migran en
  el mismo PR. Nota: el símbolo de `pipeline.py:47` es `embed_chunks`. Assessment:
  `pipe_sha` nuevo → smoke + fila.

## 5. Lo que NO se hace (declarado)

Empaquetado Fase-E · microservicios · mover `evals/` (registros; pins 2C exigen
historia) · tocar el MECANISMO del gate C1 (solo las listas que su diseño prevé
editar) · partir `retriever.py` (2.906 LOC) o `answer_planner.py` en estos lotes —
`retriever` es el god-module que duele (churn×tamaño) pero se parte, si se parte, en un
lote propio POSTERIOR con su medición · lazificar las lanes flag-off del closure (2.219
LOC inertes: el perfil ya las gobierna; churn de sello sin cambio de conducta) ·
resolver E4/E5/E6 (triggers declarados en el contrato, sin lote asignado) · converger
los 4 dialectos de parser booleano en L2b (byte-compat primero).

## 6. Incertidumbres declaradas

(1) Importabilidad de `harness/` desde CI/pytest rootdir — se comprueba en el PR de
L2a. (2) La lista de ~200 scripts importadores de la isla es estimación; el cierre es
trinquete + suite, no el conteo. (3) `extraction_derivation`/`superscript_overlay` son
builder-side de un asset que una lane sellada consume: si ese flujo se formaliza,
reclasificarían a `src/reingest/` (reversible, no sellados). (4) E6 (retiro por
inyección) pasa por dúo propio: zona telemetría/RGPD. (5) Cada lote L1-L3 requiere su
revisión adversarial (zona de dolor legacy ⇒ cross-model innegociable) y el desbloqueo
de Alberto antes de mover el primer fichero.
