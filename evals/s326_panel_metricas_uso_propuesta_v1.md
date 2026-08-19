# s326 — Métricas de USO y CALIDAD en el panel: propuesta v1

> **Estado (actualizado 19-ago tarde)**: **ADJUDICADA ENTERA por Alberto en el hilo** —
> (1) drill-down con prosa = **OPCIÓN (a)** completa (pregunta + comentario; gate nuevo:
> addendum al paquete del abogado); (2) taxonomía v1 OK; (3) por-usuario con **alias de
> allowlist** OK; (4) coste OK. **Cableada en la rama del PR de cableado** (migración 021 +
> `src/clasificacion.py` + seam `CLASIFICADOR_PREGUNTAS` off + Explorador). Sin aplicar en
> producción: falta aplicar la 021 (Alberto/conector) + backfill con gate de acuerdo.
>
> _Texto original de la propuesta (pre-adjudicación) a continuación, sin retocar:_
> **Origen**: petición de Alberto (19-ago-2026): tipología de pregunta · fabricantes · modelos ·
> feedback por pregunta (con sub-feedback y motivo en texto) · preguntas por usuario; tabla
> por-pregunta + «pivot» de agregados + gráficas + filtros. Diagnóstico suyo: «las métricas que
> tenemos ahora son puramente de telemetría y no tanto de usabilidad y calidad».
> **Impacto si se cablea**: MEDIO-ALTO (esquema nuevo + superficie del panel expuesto) →
> Protocolo 3 con dúo Sol+Fable sobre el diff, innegociable.

## 0. La corrección al diagnóstico (importa para dimensionar el trabajo)

El diagnóstico es correcto en la EXPOSICIÓN pero no en la CAPTURA: la mitad de lo pedido ya se
está guardando por pregunta desde s286/s294 y no se ve en el panel. `query_logs` ES la «tabla que
liste toda la información para cada pregunta» que pide la propuesta — le faltan dos dimensiones
(tipología, fabricante) y las vistas encima. Consecuencia práctica: **el único dato NUEVO a
capturar es la tipología; todo lo demás es derivación + exposición**, y no hay que tocar el bot
en ninguna pieza (cero riesgo sobre la ruta de respuesta).

## 1. Estado MEDIDO en producción (19-ago-2026, agregados vía Supabase; sin volcar prosa)

- `query_logs`: **109 filas** (7-abr → 18-ago), **2 usuarios** — volumen pre-piloto.
- `product_models` relleno en **76/109 (70 %)**. Top medido: CAD-250 ×20 · CAD-150 ×10 · ZXE ×8 ·
  NC-PF2 ×8 · ASD535 ×6 · Pearl/ID3000/CAD-171/AFP-400 ×4…
- `query_logs.category`: **1/109** — es la heurística legacy `CATEGORY_TERMS` (categoría de
  CHUNKS, no tipología de pregunta). Columna efectivamente muerta; NO reutilizarla (semántica
  contaminada y consumidores legacy).
- `route`: 72 NULL (pre-s301, eran RAG/error) · 26 `rag` · 10 `catalog_shortcut` ·
  1 `manufacturer_mismatch`.
- `answer_feedback`: **9 votos (8 👎)** · `reason_class` en 3 · `comment` en 4. La captura
  s294 está COMPLETA: 👍/👎 + sub-feedback en clases cerradas `{info, wrong, scope, other}` +
  «✍️ Te lo explico» → `comment` texto libre + marca de `utilidad` (s296).
- `feedback` (prosa espontánea): 161 filas — mezcla épocas y pruebas; es cola de LECTURA, no
  métrica graficable sin curar.
- Panel vivo (DEC-239→244, Vercel propio): 7 vistas agregadas declaradas en
  `dashboard/datos.py` (`VISTAS`), páginas `resumen / metricas / errores / acceso`. Las vistas
  actuales son deliberadamente «ni ids ni prosa» (LIA s301).
- Retención (s295/s296, aplicadas): a 24 meses NO se borra la pregunta — se **seudonimiza** el
  autor (`persona_seudonimo`, estable). El texto sobrevive ⇒ el backfill «hacia atrás» de la
  tipología es viable sobre TODO el histórico, siempre.

## 2. Mapa punto a punto: pedido → existe → falta

| # | Métrica pedida | Ya existe (capturado) | Falta |
|---|---|---|---|
| 1 | Tipología de pregunta | NADA (la `category` es otra cosa y está muerta) | **Captura nueva**: clasificador batch + taxonomía versionada |
| 2 | Fabricantes más preguntados | `product_models` por fila + catálogo modelo→marca + ruta `manufacturer_mismatch` | Dimensión estructurada `marcas[]` (derivable offline) + vista + gráfica |
| 3 | Modelos más preguntados | `product_models` (70 % fill, runtime truth) | Canonicalizar vía catálogo (CAD-150 vs CAD-150-8, grafías) + vista |
| 4 | Feedback + sub-feedback + motivo texto | **TODO capturado** (s294): `verdict` + `reason_class` + `comment`; agregados semanales ya en panel | Verlo **por pregunta** (prosa ⇒ gate RGPD, §5) y cruzarlo con tipología/marca |
| 5 | Preguntas por usuario | `telegram_user_id` en cada fila; seudónimo s296 | Vista + **decisión de identidad en pantalla** (§5) |

## 3. Recomendación (arquitectura en 3 piezas; derivado, nunca hot-path)

### A. Migración `021_query_clasificacion.sql` — la dimensión que falta, como dato DERIVADO

```sql
CREATE TABLE query_clasificacion (
    query_log_id      UUID PRIMARY KEY REFERENCES query_logs(id) ON DELETE CASCADE,
    categoria         TEXT NOT NULL CHECK (categoria IN (…taxonomía v1…, 'otros')),
    taxonomia_version SMALLINT NOT NULL,
    marcas            TEXT[] NOT NULL DEFAULT '{}',  -- canónicas (documents.manufacturer, 30 limpias — regla DEC-232: listar ≠ buscar)
    modelos           TEXT[] NOT NULL DEFAULT '{}',  -- canónicos vía catálogo
    origen            TEXT NOT NULL CHECK (origen IN ('regla','llm')),
    modelo_llm        TEXT,                          -- NULL si origen='regla'
    clasificado_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- **PK = query_log_id (1:1)**: re-clasificar = UPSERT que sobrescribe con la versión nueva —
  como el LEVER_DIGEST, una fila vigente, nunca apilar; la traza histórica vive en los recibos
  del job.
- **CASCADE**: la supresión RGPD documentada (`DELETE FROM query_logs WHERE telegram_user_id=X`)
  sigue funcionando sin pasos extra. La tabla NO lleva id de persona ⇒ no añade dato personal
  nuevo ni entra en el job de seudonimización (declararla igualmente en la matriz de retención).
- ACL enumerada (patrón 019/020): INSERT/UPDATE de columna al rol del job; SELECT a las vistas.
  `query_logs` NO se toca (la 018 acaba de endurecerla; la `category` muerta ahí es el
  precedente de por qué no se añaden columnas derivadas al hot-path).

### B. Job clasificador batch — determinista primero, LLM solo donde paga

`scripts/clasificar_preguntas.py`, idempotente, con recibo JSONL y cap de filas/coste por corrida:

1. **Rutas ≠ rag → categoría por REGLA, $0**: `catalog_shortcut`/`manufacturer_no_model` →
   `catalogo_documentacion`; `manufacturer_mismatch` → ídem + marca pedida extraída (ver bonus);
   `clarify`/`decline` → bucket propio o clasificación por texto (decidir en diseño fino).
2. **Marcas/modelos, deterministas**: `product_models` (lo que el bot RESOLVIÓ — runtime truth)
   canonicalizado vía catálogo; marca por join modelo→fabricante; más alias-scan del texto con
   las MISMAS fuentes del runtime para preguntas marca-sin-modelo. Un solo code path sirve
   histórico y filas nuevas ⇒ el bot no se toca.
3. **Categoría de filas `rag` → LLM (Haiku 4.5)**, salida JSON forzada sobre taxonomía CERRADA
   (enumerada + `otros`), prompt y taxonomía versionados en `config/taxonomia_preguntas_v1.yaml`.
4. **Corrida**: tarea diaria en el worker con aislamiento fail-open TOTAL (patrón INTENT_LLM:
   try/except-wall, timeout, jitter, cap) + invocación manual para backfill y re-taxonomía.
   Si el volumen del piloto lo pide, promover a servicio cron de Railway (upgrade declarado).
5. **Gate de calidad ANTES de fiarse** (que la gráfica no mienta en silencio): ~30 preguntas
   etiquetadas a mano vs clasificador; umbral de acuerdo ≥85 % o se revisa la taxonomía/prompt.
   Coste céntimos.

**El ciclo del «otros» que propone Alberto queda exactamente así**: el panel muestra el % de
`otros`; cuando engorde, se revisan muestras (Supabase), se extiende la taxonomía → `v(n+1)` →
re-run GLOBAL (no solo `otros`: una taxonomía nueva puede re-rutar categorías existentes). A
volumen actual el re-run cuesta ~$0,10; a 100 preguntas/día, ~$0,07/día. La `taxonomia_version`
en cada fila y en las vistas evita mezclar dos taxonomías en una gráfica sin decirlo.

### C. Panel — vistas nuevas + página «Explorador» con filtros fijos

Vistas SQL versionadas (patrón s301: `security_invoker`, REVOKE `anon`, select explícito
declarado en `VISTAS`):

- `bot_tipologia_semanal` (semana × categoría × n) — barra por tipo de pregunta.
- `bot_marcas_semanal` (semana × marca × n) — barra de fabricantes + línea temporal.
- `bot_modelos_semanal` (semana × modelo × n).
- `bot_feedback_por_dimension` (semana × categoría/marca × votos up/down) — cruza calidad con
  tipología: «¿en qué TIPO de pregunta falla el bot?» es la métrica accionable que hoy no existe.
- `bot_preguntas_por_usuario_semanal` — GATED por decisión de identidad (§5).
- **Bonus con valor M&A/corpus**: `bot_marcas_sin_corpus` — marcas pedidas por rutas
  `manufacturer_mismatch` + 👎 `reason_class='scope'` = demanda NO cubierta (el `query_gaps`
  que TECH_DEBT #8 dejó pendiente, servido con datos que ya se capturan).

Página nueva del panel con **filtros fijos server-side** (periodo · marca · categoría), valores
whitelisteados contra el catálogo/taxonomía (nada de parámetros libres a PostgREST). El
**drill-down por pregunta** (texto + verdict + reason + comment) va en esta página, GATED (§5).

**Pivot libre NO se reconstruye en el panel**: para cortes ad-hoc están el SQL de Supabase
(Alberto) y, si el piloto lo pide, un export CSV seudonimizado (v2, gated — regla s296: al
fichero solo sale el seudónimo).

## 4. Taxonomía v1 (HIPÓTESIS — la adjudica Alberto; anclada en las preguntas gold reales)

| Categoría | Forma de pregunta (ejemplos de la clase, del gold set) |
|---|---|
| `especificaciones` | tensión/consumo DGD-600 · EOL de la ZXe · nº lazos AM2020 · cálculo Ah AM-8200 · rango temperatura ASD535 |
| `instalacion_cableado` | conectar baterías CAD-150 · cablear módulo M710 · alimentar IS-mA1 en zona ATEX · alinear FD2705R |
| `configuracion_programacion` | menú programación CAD-250 · causa-efecto AM-8200 · contraseñas INSPIRE · alta de detector en el lazo |
| `averias_diagnostico` | «Tierra» en AFP-400 · alarma intermitente ASD535 · no vuelve a normal tras extinción · rearme tras alarma |
| `mantenimiento_pruebas` | test anual VESDA · cambiar batería sin perder config · actualizar firmware CAD-150 |
| `compatibilidad_sustitucion` | detectores compatibles ID3000 · «me sobró un detector Notifier, ¿vale en la CAD-150?» · ampliar 2X-AF2 con 2X-A-LB |
| `normativa` | EN 54-13 · niveles alarma/prealarma en España (cuando es la intención DOMINANTE) |
| `catalogo_documentacion` | «¿qué fabricantes/manuales tienes?» · pedir un manual · selección de producto («necesito un 751») |
| `otros` | el cajón a limpiar y re-taxonomizar |

Nota: los 9 arquetipos de `evidence_coverage_facets_v5` son evidencia-side y más finos
(intrinsic_safety, loop_eol_topology, battery_sizing…) — se usaron como INSUMO del diseño, no se
reutilizan tal cual (propósito distinto: cobertura de evidencia ≠ tipología de demanda).

## 5. RGPD / gates de EXPONER (declarados de entrada, no tras pushback)

1. **El drill-down con prosa es LITERALMENTE el «fuera de v1» de DEC-231** («leer las
   conversaciones de los DGs… entra cuando el piloto lo pida y con su propia vuelta de RGPD»).
   Alberto pidiéndolo ES el gatillo previsto, pero entra solo con: decisión explícita suya +
   addendum al paquete del abogado (el panel ya está dentro) + valorar truncado de prosa.
2. **Por-usuario**: las vistas actuales son «ni ids ni prosa» a conciencia (LIA s301). Exponer
   conteos por persona exige elegir la identidad en pantalla — recomendación: **alias de la nota
   de allowlist** para usuarios activos (el panel de gestión ya muestra ids+notas, no es
   exposición nueva) y **seudónimo s296** para históricos. Decide Alberto.
3. `query_clasificacion` no lleva id de persona; muere en CASCADE; se declara en la matriz.
4. **El aviso v7 no se toca**: la cortesía sigue sin registrarse; el bot no cambia ni un byte.
5. Clasificar envía la pregunta a la API de Anthropic — el MISMO tratamiento ya declarado (el
   bot entero genera con Claude). Gap a confirmar con el abogado: si el fin «analítica interna»
   necesita mención aparte en el aviso.

## 6. Gaps y riesgos conocidos (de entrada)

1. **Marcas por voz destrozadas** (DEC-233; workstream abierto «no te he entendido»): el ASR
   rompe nombres de marca ⇒ infraconteo de fabricantes en preguntas de voz hasta que existan las
   variantes de las 30 marcas. La métrica lo HEREDA y no lo arregla; se declara en el panel.
2. `product_models`/marcas = **lo que el bot ENTENDIÓ**, no siempre lo que el técnico quiso: una
   marca no resuelta cae al bucket «sin marca detectada», VISIBLE en la vista (es señal de gap de
   resolución/corpus, no se esconde bajo la alfombra).
3. **N diminuto hoy** (109 preguntas, 2 usuarios, 9 votos): las celdas semanales serán n=1-3
   hasta que el piloto traiga tráfico. Construirlo AHORA es correcto (que el día 1 del piloto ya
   mida); LEERLO como tendencia todavía no.
4. El sub-feedback solo se pide en 👎 (diseño s294). Si se quiere sub-feedback de 👍, es cambio
   de UX del bot — fuera de este alcance.
5. Retención: a 24 m el por-usuario REAL se corta por seudonimización — por diseño, no es bug.
6. `feedback` libre (161 filas) mezcla épocas/pruebas: curar antes de graficar; mientras, cola
   de lectura.
7. Clasificador LLM puede errar: mitigado con taxonomía cerrada + gate de acuerdo ≥85 % + `otros`.

## 7. Alternativas consideradas y descartadas

- **Clasificar EN el turno** (como INTENT_LLM): latencia + superficie de fallo en la ruta de
  respuesta para un dato que nadie necesita en tiempo real. INTENT_LLM está en-turno porque
  DECIDE el retrieval; una métrica no decide nada en el turno. Batch con un solo code path
  (live = backfill = re-taxonomía) domina.
- **Columnas nuevas en `query_logs`**: acopla derivados al hot-path recién endurecido (018);
  `category` muerta ahí es el precedente. Tabla derivada + CASCADE domina.
- **Reutilizar `query_logs.category`**: semántica de otra época (categoría de chunks), 1/109
  filas, consumidores legacy.
- **Herramienta BI (Metabase/Grafana/dashboard Supabase para DGs)**: proveedor + superficie de
  auth nuevos justo tras sellar la v9 para dos lectores; DEC-183/162f ya lo descartó y DEC-231
  eligió panel propio. Si el hambre de pivot crece de verdad, se reevalúa como pieza estructural
  — leería las MISMAS vistas, el trabajo no se tira.
- **Pivot-UI genérico hand-rolled en el panel**: sobre-ingeniería (contra convención); Excel/SQL
  ya existen para cortes ad-hoc.
- **pg_cron para el job**: no puede llamar a un LLM; quedaría un job cojo de su mitad.

## 8. Por qué BP + estructural + escalable

- **BP**: tabla de enriquecimiento derivada sobre event-log + clasificador versionado + vistas
  agregadas = patrón analytics-on-events de libro; determinista-primero y LLM solo en el residuo.
- **Estructural**: ataca la raíz (faltan DIMENSIONES de análisis, no gráficas); no toca síntoma
  ninguno del bot; un solo code path para histórico y futuro; taxonomía con versión explícita en
  el dato (reconstruible por construcción).
- **Escalable a 30+ fabricantes**: marca/modelo salen del CATÁLOGO CANÓNICO (el cimiento que ya
  escala — cabalga el workstream DEC-074, no lo duplica); coste LLM lineal y despreciable
  (~$0,07/día a 100 preguntas/día); las vistas agregan sin límite de fabricantes.

## 9. Protocolo y próximos pasos

1. **Adjudicación de Alberto** (4 decisiones): (a) alcance — ¿entra el drill-down con prosa
   (gate DEC-231 §5.1)?; (b) taxonomía v1 — renombrar/añadir/quitar categorías; (c) identidad
   en pantalla del por-usuario (§5.2); (d) OK al coste (céntimos de LLM + dúo del cableado).
2. **Dúo Sol+Fable** sobre el diseño fino y sobre el diff al cablear (esquema + panel expuesto =
   zona de dolor; innegociable).
3. Cableado flag-off / no-op sin migración aplicada (patrón `tabla_ausente` del panel: la vista
   que falta se declara, no rompe); tests + gate pg si la ACL lo pide; PR, no push a main.
4. Migración por Alberto/conector (021), backfill con recibo, gate de acuerdo del clasificador
   estampado, smoke del panel en producción.

**Coste estimado total**: backfill 109 filas ≈ $0,10 · piloto ≈ $0,07/día · dúo del cableado
≈ $10-20 · el resto, $0.
