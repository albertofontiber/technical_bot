# s322b — Propuesta r28: zonas + inventario agrupado + datos VESTA/NC-PF (post-#76)

**Estado al escribir esto:** PR #252 (mecanismo #76 + población fase 2) MERGEADA.
Este diff es el CIERRE de #76 sobre esa base + tres adjudicaciones de Alberto del
14-ago (mensajes en vivo):

1. «Ojo que ya había mergeado PR252» → este trabajo va en rama/PR NUEVA.
2. Inventario genérico («¿qué productos Kidde tienes?») debe salir **categorizado
   por tipología y ordenado por familia**, no listado plano infinito; y debe ser
   **generalizable** (no atado a un phrasing).
3. La CAD-250 es **ampliable hasta ~32 lazos con módulos** y CAD-250-32 NO existe
   como modelo; «la CAD-171 y CAD-201 sí deberían tener informados lazos»; y
   «todas las centrales deben llevar asociado un número de lazos — es una
   característica de las centrales».

## Cambios de CÓDIGO en este diff

### a) Clave `zonas` en el esquema de atributos (`src/rag/catalog_store.py`)
- `CLAVES_ATRIBUTO` += `zonas`; validación idéntica a `lazos` ({base:int≥1, max≥base,
  doc, cita}). Motivo: la regla «toda central lleva su dato de capacidad» aplicada a
  las CONVENCIONALES (NC-PF de Kidde) — su dato son ZONAS, no lazos analógicos.
  Modelarlas como `lazos` falsearía el concepto (un técnico que pide «4 lazos» NO
  pregunta por una convencional de 4 zonas).

### b) Léxico del plan (`src/orchestrator/turn_plan.py`)
- `_RX_ZONAS` («N zonas/zones», dígito o palabra) → `filtros["zonas"]`, mismo patrón
  cerrado que `_RX_LAZOS`. Sin LLM en el turno (DEC-200, ya adjudicado en r27).

### c) Consumidor (`src/bot/telegram_bot.py`)
- `_casa`: el bloque de capacidad se generaliza a `("lazos", "zonas")` — misma
  semántica adjudicada («N» = «hasta N», filtro `n ≤ max`, base descriptivo),
  display «hasta X lazos/zonas». Claves separadas: un filtro de lazos sobre una
  convencional sin lazos → sección parcial honesta (no se cuela ni se oculta).
- `_productos_marca(cat, nombre)`: helper extraído (activos ∩ no-candidatos ∩
  marca ∩ doc_map con docs) — compartido por la vista filtrada y la agrupada.
- **`_inventario_agrupado(nombre)` (NUEVO)**: la ruta sin filtros, cuando el
  catálogo tiene clasificación para la marca, agrupa por `clasificacion.categoria`
  en orden canónico (central→…→accesorio), ordena por modelo canónico (las
  familias quedan adyacentes por prefijo), muestra TODA categoría siempre con su
  conteo y trunca modelos con «…y N más» bajo `_PRESUPUESTO_MSG` por construcción.
  Cola honesta de sin-clasificar. `None` (marca sin clasificación / catálogo
  caído) → lista plana de SIEMPRE. Enganchada en `_inventario_fabricante` ANTES
  del backoff de DB (sale del catálogo local, sirve incluso con DB caída), con
  fail-open try/except a la lista plana y caché por la misma clave por-marca.
- `desc` del encabezado filtrado ahora dice «4 lazos»/«2 zonas» (antes el número
  suelto).

### d) RE-CONTRATO de test (gate 3 del r27)
`test_sin_filtro_byte_igual_pre_76` (la ruta sin filtro no toca el catálogo y es
byte-igual) queda SUSTITUIDO por adjudicación directa de Alberto (14-ago, mensaje
2). Lo que se conserva como contrato: marca sin clasificación → lista plana
byte-igual (misma fuente DB/caché/truncado); catálogo caído → lista plana; el
agrupado jamás inventa grupos sin datos. Tests nuevos: zonas (plan+capacidad),
agrupado (orden, conteos, cota, cachés, degradaciones).

## Cambios de DATOS en este diff (todos con cita verbatim verificada contra doc completo)

- `scripts/s322_76_lazos_vesta.py`: CAD-171 {2,2} (MI-716 «**2** lazos»); CAD-201
  {2,8} (MC-380 «versión de 2 lazos ampliable a 8 lazos CAD-201»); CAD-201-PLUS
  {1,8} (MI-715 «Hasta **8** lazos…»; base=1 = suelo descriptivo, el doc del PLUS
  no declara dotación); CAD-250 y CAD-250-P {8,8} (MI-372) **+ {1,32}** (MC-380
  «El sistema CAD-250 soporta hasta 32 lazos en un único NODO») — la ampliación
  modular de Alberto como entrada multi-fuente, sin inventar un modelo -32; +
  tecnología analogica para CAD-250/-P (MI-372 «La CAD-250 es una central
  analógica…»). Todo-o-nada: cita no verbatim → aborta.
- `scripts/s322_76_writer_rescate.py`: 12 filas §0 (alta+citas-verificadas, MISMO
  criterio adjudicado) que el writer saltó por atribuir citas contra los 6
  primeros chunks del doc (la repesca v2 verificó contra secciones profundas);
  re-atribución contra doc COMPLETO. 12/12 rescatadas, 0 relajaciones.
- `scripts/s322_76_zonas_ncpf.py`: NC-PF2/-SC {2,2}, NC-PF4/-SC {4,4},
  NC-PF8/-SC {8,8} con citas de sus datasheets/manual de familia. 6/6.
- Auditoría regla-de-dominio: 36 centrales clasificadas → 36 con dato de
  capacidad (30 lazos + 6 zonas) tras estos writes.

## Alternativas consideradas y descartadas
- **Zonas como `lazos`**: falsea conceptos distintos; un filtro «4 lazos» colaría
  convencionales. Descartada.
- **Filtrado/agrupado por LLM orquestador**: re-litigado — ya adjudicado en r27
  (léxico cerrado $0 determinista primero; LLM al margen si la métrica lo pide).
- **Agrupar desde los pm de la DB**: los pm son strings de FAMILIA (T3/s285); la
  fuente gobernada es catálogo ∩ doc_map. Descartada.
- **Colapsar familias con nombre inventado («KE-AS31xx»)**: inventaría taxonomía
  no gobernada; el orden alfabético ya adyacenta familias y el conteo por
  categoría acota el mensaje. Diferida (si Alberto quiere umbrella-familias, es
  dato de catálogo, no heurística de render).

## Gaps declarados
- El agrupado pierde el conteo de documentos por referencia que la lista plana
  mostraba («— 3 documentos»). Deliberado (ruido en vista de 100+ productos).
- Solo Detnov+Kidde tienen clasificación hoy → las otras ~28 marcas siguen en
  lista plana (correcto por diseño: degradación honesta, población por packets).
- Los 21 sin-clasificar de Kidde y 3 de Detnov quedan como cola contada (son
  filas §1 pendientes de adjudicación de Alberto — no se inventan).
- `base` en entradas de capacidad «hasta N» usa 1 como suelo descriptivo cuando
  el doc no declara dotación de serie (CAD-201-PLUS, CAD-250 {1,32}) — el filtro
  solo usa `max`, pero un consumidor futuro de `base` debe saber esto.
- La caché por-proceso del inventario agrupado no se invalida al recargar el
  catálogo en caliente (igual que la vista filtrada — ya aceptado en r27).

## ADENDA post-dúo r28 (Sol 7/7 + Fable 5/5 confirmados, 0 FP — 14-ago)

**CORRECCIÓN del claim «Cambios de DATOS… todos con cita verbatim» (S3/F1,
crítico Fable):** FALSO como estaba escrito. Este diff incluye un CUARTO
script de datos no declarado arriba: `scripts/s322_76_sufijo_cad150.py`
(lazos de CAD-150-4/-8/-8-PLUS por DERIVACIÓN DE REGLA adjudicada por Alberto,
declarada como tal en la propia cita — no verbatim). La auditoría «36/36
centrales con dato» incluye esas 3 filas derivadas y 3 más ({1,32} etc.) — sin
ellas sería 33/36 verbatim. El sesgo de framing del autor, cazado de nuevo.

Correcciones aplicadas en este mismo diff tras el dúo:
- **S2**: `base` OPCIONAL en el esquema; migración retiró los 6 `base=1`
  inventados (recibo `s322_76_migra_base_opcional_v1.json`).
- **S4 (materializado)**: re-verificación FULL-TEXT de las 296 citas
  almacenadas → 292 OK, 3 derivadas-declaradas, **1 invención real cazada y
  retirada** (tecnología «analogica» de kidde:2010-2-pak-rmsdk — cola
  parafraseada; el doc no contiene addressable/direccionable/analog). Método
  corregido: se verifica la cita completa almacenada, no 50 chars.
- **S5**: orden por `familia` GOBERNADA (campo existente, 22 filas) con
  fallback modelo-como-familia; **F5**: orden natural (CAD-150-4 < CAD-150-12).
- **S7/F2**: cota por construcción también para encabezados de categoría
  (línea compacta «…y N categorías más»); test endurecido a <3700.
- **F3**: inaplicable ≠ faltante — capacidad hermana anclada o tecnología
  incompatible ⇒ EXCLUSIÓN, no sección parcial.
- **F4**: «zonas de extinción» excluido del léxico por lookahead.
- **S1 (crítico)**: confirmado como gap LATENTE, no vivo — el único max
  divergente hoy es CAD-250 8-serie/32-nodo (intra-mercado, correcto bajo
  capacidad). La clase AFP1010 (ES-2/US-4) no está poblada. Disposición
  estructural en TECH_DEBT #76b: marcador de alcance/mercado adjudicable +
  flag de divergencia en el gate de población ANTES de poblar Notifier.
- **S6**: alcance declarado — la ruta de inventario es determinista y se mide
  por contrato (tests) + smoke con recibo, no por juez LLM; no se reclama
  ningún lever medido.

## Por qué BP + estructural + escalable
Raíz, no parche: la capacidad es un ATRIBUTO tipado del catálogo gobernado con
cita, no un regex sobre respuestas; el render agrupado vive en la RUTA de
inventario (cualquier phrasing que despache ahí lo hereda); `zonas` reutiliza
la maquinaria completa de `lazos` (validación, semántica, filtro, display) sin
duplicar; y a 30+ fabricantes escala por datos (packets), no por código.
