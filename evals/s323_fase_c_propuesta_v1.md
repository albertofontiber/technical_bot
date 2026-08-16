# s323 FASE C — GATE de coherencia de identidad corpus↔catálogo (diff para el dúo)

Implementado y con tests; se somete el DIFF **antes de commitear** (Protocolo 3). Cierra
lo que las fases A (datos) y B (raíz de la ingesta) dejaron abierto: **detectar** las
referencias rotas, no solo repararlas o prevenirlas.

## Los invariantes, y por qué NO usan el nombre
El dúo r32 fue explícito: usar `source_file` como clave de identidad **contradice el
contrato canónico** — el nombre solo corrobora una identidad ya ligada por `document_id`.
Así que los cinco invariantes se formulan sobre el PUNTERO:

| | Comprueba | Clase que caza |
|---|---|---|
| I1 | todo `doc_map.document_id` existe en `documents` | puntero a la nada |
| I2 | …y su fila está **activa** | **#80** (las 60) |
| I3 | …y ese documento tiene **≥1 chunk** | el fantasma: puntero a ficha vacía |
| I4 | `document_id` es **único** en el doc_map | duplicado que el validador rechaza |
| I5 | no hay chunks con `document_id` NULL | **#81** (los 61 huérfanos) |

`source_file` aparece SOLO en el informe, para que un humano reconozca la fila.

## Estado vivo medido (tras la fase A)
`I1 0 · I2 11 · I3 0 · I4 0 · I5 61` → **72 violaciones, todas conocidas**: las 11 filas
no-activas con rivales y los 61 huérfanos. **Las 49 de #80 ya no aparecen** — confirmación
independiente de que la fase A funcionó.

## FALSO POSITIVO PROPIO, cazado antes de reportarlo
La primera versión del gate dijo **I3 = 211**. Era mío: consultaba los chunks por lotes de
50 ids con `limit=2000`, y eso **trunca**. Verifiqué cuatro de esos «documentos sin chunks»
uno a uno: tenían 30, 134, 50 y 29. Corregido a censo EXACTO por paginación del universo
completo (26.215 chunks, 27 peticiones). Es la cuarta vez esta sesión que produzco una
medición por muestreo y la cuarta que hay que cazarla: queda anotado en el propio código
para que nadie lo repita ahí dentro.

## Excepciones GOBERNADAS (lo que el dúo pidió diseñar)
`data/catalog/identidad_excepciones.json`, versionado: las 72 preexistentes con su
**identidad exacta** (document_id o chunk_id — nunca el nombre), su motivo y su fecha de
sellado. **El gate falla por lo NUEVO.** Si fallara por lo preexistente estaría rojo
siempre y nadie lo miraría, que es la forma de tener un gate y no tenerlo. Sellar el
manifiesto es un acto deliberado (`--sellar`), jamás un efecto colateral de ejecutarlo.

## Contrato CI↔DB (la pregunta que ambos revisores dejaron abierta)
Declarado explícitamente: **el gate consulta la DB de producción viva, no un snapshot** —
su veredicto es sobre lo que el bot sirve AHORA. Por eso **NO va en la CI de GitHub**, que
no tiene credenciales ni debe tenerlas. Se ejecuta: (a) **automáticamente al final de toda
ingesta** (`pipeline.run()`), que es donde importa y donde las credenciales ya existen; y
(b) a demanda. Un gate contra snapshot podría pasar con datos viejos: peor que no tenerlo.

## Tests (5)
La clave de una violación es el puntero y no el nombre · sin violaciones pasa · una
preexistente NO tiñe de rojo · una NUEVA rompe el gate · **un huérfano nuevo en un fichero
que ya tenía huérfanos gobernados se detecta** (por eso la clave es el chunk).

## Alternativas descartadas
- **Invariante por `source_file`**: contradice el contrato de identidad y puede pasar
  estando ambos lados coherentemente equivocados.
- **Gate en la CI de GitHub**: exigiría credenciales de producción en CI.
- **Gate sin manifiesto**: rojo perpetuo por 72 casos conocidos ⇒ gate ignorado.
- **Fallar la ingesta ya hecha**: los chunks ya están escritos; abortar no los borra. Avisa
  fuerte, deja el veredicto en el resumen y lo persiste el log.

## Gaps declarados
- El gate **detecta y no repara**: las 72 siguen ahí. Repararlas es trabajo de packet
  (las 11) y de censo por documento (los 61, bloqueados a propósito sin sha exacto).
- Corre **después** de la ingesta: no impide escribir, avisa de lo escrito. La prevención
  es la fase B (la guarda antes del DELETE); esto es la red de seguridad, no el muro.
- No cubre la coherencia *semántica* (que las entries del doc_map describan al producto
  correcto): eso es adjudicación humana, no invariante.

---

# ADENDA post-dúo r34 (Sol 6/6, 0 FP, **3 CRÍTICOS**) — aplicados antes de commitear
**Aviso honesto**: la captura de **Fable FALLÓ** (BadRequestError de la API), así que esta
ronda corre **solo con Sol** — no está emparejada, y queda dicho en el tally.

1. **CRÍTICO — era un monitor, no un gate.** La integración imprimía la violación y
   `run()` terminaba con éxito. Sol: «la escritura ya realizada no necesita rollback para
   que el gate devuelva código no-cero y bloquee la automatización posterior». Aplicado:
   `SystemExit(3)` con violaciones nuevas y **`SystemExit(4)` si el gate NO puede
   evaluarse** — «no he podido comprobar» no es «todo bien».
2. **CRÍTICO — mi afirmación «automáticamente al final de toda ingesta» era FALSA.**
   `scripts/ingest_new.py`, el driver vivo de altas, llama a `process_file()`
   **directamente**, no a `pipeline.run()`: existía un camino real de escritura que el
   control no observaba. Cableado también ahí, al final de `ejecutar()`.
3. **CRÍTICO — el gate habría roto la CI.** Leía `SUPABASE_*` a nivel de **import**, y
   `conftest.py` no inyecta esas variables: en CI (sin `.env`) el test que lo importa
   habría reventado la **colección de toda la suite**. Credenciales perezosas; **probado**
   ejecutando el import en un subproceso con el entorno despojado de credenciales.
4. **MEDIO — I5 truncaba.** Pedía `Range: 0-999`: con más de 1.000 huérfanos omitiría
   filas. Es **la misma clase de truncado que ya falseó I3 dentro de este mismo gate** —
   la segunda vez en el mismo fichero. Paginado.
5. **MEDIO — whitelist permanente.** Si se repara una violación y el manifiesto la sigue
   autorizando, su reaparición pasaría inadvertida. Ahora `evaluar()` reporta las
   **excepciones RESUELTAS** y marca el manifiesto como *stale* para forzar el re-sellado.

---

# ESTADO REAL tras aplicar el r34 (lo que Fable debe revisar)

Además de los 3 críticos + 2 medios de Sol, **el contrato de imports del repo tumbó mi
cableado dos veces seguidas**, y las dos veces tenía razón:

1. El gate vivía en `scripts/` y lo importaba `src/reingest/pipeline.py`. **`src/` no puede
   importar de `scripts/`** (`tests/test_import_contract.py`). Corregido: el núcleo se
   movió a **`src/rag/identidad_gate.py`** — es lógica de PRODUCCIÓN, la ingesta lo ejecuta
   — y `scripts/gate_identidad_corpus.py` quedó como **CLI fino**.
2. Ya en `src/`, el pipeline lo importaba… y **`reingest → rag` también está prohibido**.
   Corregido aceptando la frontera en vez de forzarla: **el gate se cablea en la CAPA DE
   SCRIPTS**, que es quien orquesta — en `scripts/ingest_new.py`, que además es el driver
   real de altas y justo el camino de escritura que Sol demostró que se me escapaba.
   `pipeline.py` queda con un comentario que explica por qué NO lo invoca.
3. Cifra de control del contrato actualizada 121→122 con su motivo escrito (fricción
   deliberada anti-acreción: añadir un módulo a `src/` exige declararlo).

**Estado vivo del gate**: `I1 0 · I2 11 · I3 0 · I4 0 · I5 61` — 72 preexistentes
gobernadas, 0 nuevas. Las 49 de #80 ya no aparecen (confirmación independiente de la fase A).

**Tests**: 24 verdes entre contrato de imports, gate y resolución tipada. Suite completa en
curso al escribir esto.

**Lo que quiero que ataques**: (a) ¿el gate cableado SOLO en la capa de scripts cumple de
verdad «no depende de que alguien se acuerde», o he cambiado un agujero por otro? (b) ¿los
cinco invariantes cubren la incoherencia que rompió #80, o se me escapa una clase? (c) ¿el
manifiesto de excepciones es auditable, o es una amnistía disfrazada?

---

# REVISIÓN DEL SUPLENTE (Opus 5, fallback adjudicado por Alberto) — **NO SÓLIDO**, 2 críticos

El pin Fable no pudo correr: la cuenta de Anthropic devuelve `400 credit balance is too low`
(sonda mínima de 64 tokens: falla igual ⇒ no es tamaño de prompt). Alberto adjudicó el
fallback temporal a Opus 5 (precedente s292); **restaurar `claude-fable-5` al recargar**.

**CRÍTICO 1 — el gate destruye el recibo justo cuando hace falta.** Se invoca DENTRO de
`ejecutar()`, y `SystemExit(3|4)` aborta **antes de que `main()` escriba el log JSON del
lote**. Es decir: cuando algo va mal, se pierde la traza de qué se escribió. Contradice
literalmente mi propia propuesta («deja el veredicto en el resumen y lo persiste el log»).
**Arreglo**: el gate corre al FINAL y su veredicto se propaga como código de salida
DESPUÉS de persistir el recibo.

**CRÍTICO 2 — sí cambié un agujero por otro** (respuesta a mi propia pregunta (a)).
`pipeline.py` tiene **CLI propia** (`main()`/argparse) y es un camino de escritura
ejecutable directamente; mi comentario delega en «cualquier runner de este pipeline», que
es exactamente el «alguien se acuerde» que decía haber eliminado. **Arreglo**: que ese
`main()` invoque el gate, o que el pipeline deje de ser ejecutable directamente.

**Medios**: (a) las filas de doc_map **sin `document_id`** se saltan en silencio; (b) falta
el invariante **DB→catálogo** (un documento activo con chunks y sin entrada en el doc_map es
invisible: es la mitad simétrica de #80); (c) **códigos de salida inconsistentes** — la CLI
devuelve 1 tanto en violación como en excepción, borrando justo la distinción que el crítico
del r34 introdujo; (d) `manifiesto_stale` no afecta a `ok`: es informativo, no ejecutivo;
(e) mi «consulta la DB viva» **sobre-afirma** — un lado ES un snapshot local (el
`doc_map.jsonl` del working copy, quizá sin commitear); (f) el censo pagina el universo
COMPLETO de chunks en cada ingesta: no escala a 30+ fabricantes.

**Menores**: la docstring de `_censo` quedó suelta tras `_credenciales()` (la función se
quedó sin docstring), y I1/I2/I3 son excluyentes (`elif`), así que «72» cuenta FILAS, no
incumplimientos — la tabla de arriba sugiere conjunción y es cascada.

**Sobre el manifiesto (pregunta (c))**: el suplente lo da por **auditable** — identidad
exacta, motivo, fecha, sellado deliberado y resueltas reportadas. Su punto débil real:
`motivo` es una constante genérica en vez de adjudicación por caso, y las claves de I5
dependen de `chunk_id`, que es volátil si esos huérfanos se re-escriben.

**ESTADO: la fase C NO está lista.** Los dos críticos son de raíz.

---

# CIERRE DE LOS 2 CRÍTICOS (para la revisión de Fable, ya con el pin restaurado)

**Crítico 1 — el gate destruía el recibo**: retirado de `ejecutar()` y movido a `main()`,
**después** de escribir `logs/ingest_new_*.json`. Ahora el veredicto llega con la traza ya
persistida; si el gate aborta, el recibo del lote existe.

**Crítico 2 — el write-path sin control**: resuelto por **INYECCIÓN DE DEPENDENCIA**, que
respeta la frontera en vez de forzarla. `run()` acepta `gate=None` y lo ejecuta si se le
pasa; el runner gobernado nuevo (`scripts/reingest_run.py`, capa que SÍ puede ver `rag` y
`reingest`) lo inyecta. Y la CLI directa de `pipeline.py` **deja de indexar**: ahora aborta
redirigiendo al runner gobernado, porque escribir sin gate «es como entraron #80/#81».
Así el gate no depende de que nadie se acuerde: el único camino que escribe lo lleva puesto.

**Pin del revisor**: `claude-fable-5` **restaurado** tras la recarga de crédito de Alberto
(el fallback a Opus 5 fue temporal y adjudicado; la nota queda en el código).

**Lo que sigue ABIERTO y declarado** (medios del suplente, no cerrados aquí): filas de
doc_map sin `document_id` saltadas en silencio · falta el invariante DB→catálogo (la mitad
simétrica de #80) · códigos de salida inconsistentes entre CLI (1) y driver (3/4) ·
`manifiesto_stale` informativo y no ejecutivo · el «consulta la DB viva» sobre-afirma (un
lado es el `doc_map.jsonl` del working copy) · el censo pagina el universo completo en cada
corrida y no escala a 30+ fabricantes.
