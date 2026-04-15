# Technical Bot PCI — Detnov

Bot de Telegram RAG para técnicos PCI que resuelve dudas técnicas sobre equipos Detnov.
Los técnicos preguntan desde el móvil y esperan respuestas con pasos claros + diagramas cuando son relevantes.

## Stack

- **Python 3.14** con PyMuPDF, pdfplumber, FastAPI, python-telegram-bot
- **LLM**: Claude API (Sonnet 4, model: claude-sonnet-4-20250514) via Anthropic SDK
- **Embeddings**: OpenAI text-embedding-3-small (1536 dims)
- **Vector DB**: Supabase pgvector
- **Storage**: Supabase Storage (imágenes de diagramas)
- **Bot**: Telegram via python-telegram-bot v20+
- **Hosting**: Railway (pendiente)

## Estructura del proyecto

```
Technical Bot/
├── Manuales_ES/              # 119 PDFs fuente (177 MB, 8 categorías)
├── src/
│   ├── ingestion/
│   │   ├── pdf_parser.py     # Extrae texto + imágenes con PyMuPDF + enriquecimiento
│   │   ├── table_extractor.py # Extrae tablas con pdfplumber (complemento a PyMuPDF)
│   │   ├── vision_describer.py # Claude Vision para páginas con tablas/diagramas gráficos
│   │   ├── language_filter.py # Filtra solo secciones en español (ES/FR/EN/IT → solo ES)
│   │   ├── chunker.py        # Chunking por sección con metadata + clasificación automática
│   │   ├── image_extractor.py # Extrae diagramas como JPEG comprimidos
│   │   ├── embedder.py       # Genera embeddings con OpenAI (lazy imports para dry-run)
│   │   └── ingest.py         # Pipeline completo orquestado
│   ├── rag/
│   │   ├── retriever.py      # Búsqueda híbrida 4 capas + category search + sinónimos
│   │   ├── reranker.py       # Reranking con Claude Sonnet (prioriza modelo preguntado)
│   │   └── generator.py      # Generación de respuesta + conversación dinámica + urgencia
│   ├── bot/
│   │   └── telegram_bot.py   # Bot Telegram funcional (corre local)
│   ├── api/
│   │   └── main.py           # FastAPI endpoints [PENDIENTE]
│   └── config.py             # Configuración centralizada (modelos, dimensiones, top-k, etc.)
├── scripts/
│   ├── run_ingestion.py      # Script CLI para ejecutar ingesta
│   ├── re_ingest.py          # Re-ingesta completa (borra + re-ingesta con pdfplumber + Vision)
│   ├── re_embed.py           # Re-embedding con metadata enriquecida
│   └── structural_fixes.py   # Limpieza de chunks basura + arreglo de modelos
├── tests/
│   └── test_queries.py       # Preguntas de test [PENDIENTE]
├── supabase_schema.sql       # Schema SQL con pgvector + función RPC match_chunks
├── .env.example              # Template de variables de entorno
├── requirements.txt          # Dependencias Python
└── instructions.md           # Este archivo
```

## Datos

- **119 PDFs** de Detnov en `Manuales_ES/` (177 MB)
- **8 categorías**: Detección analógica, convencional, gas, monóxido, detectores especiales, PA/VA evacuación, extinción, accesorios
- **Multilingüe**: muchos manuales tienen ES/FR/EN/IT — solo se indexa español
- **Ingesta real completada (sesión 4)**: 17,698 chunks en Supabase, embeddings enriquecidos, 0 errores
- **Pipeline mejorado**: PyMuPDF + pdfplumber (tablas) + Claude Vision (fallback gráficos)

## Comandos

```bash
# IMPORTANTE: siempre usar -X utf8 por los paths con acentos (OneDrive + Windows)
py -3.14 -X utf8 scripts/run_ingestion.py --dry-run
py -3.14 -X utf8 scripts/run_ingestion.py --dry-run --single "Manuales_ES/..."
py -3.14 -X utf8 scripts/run_ingestion.py --use-vision  # Con Claude Vision para tablas gráficas
py -3.14 -X utf8 scripts/re_ingest.py --dry-run         # Preview de re-ingesta completa
py -3.14 -X utf8 scripts/re_ingest.py --use-vision      # Re-ingesta real con Vision
```

## Setup

1. Copiar `.env.example` a `.env` y rellenar las API keys
2. Ejecutar `supabase_schema.sql` en Supabase SQL Editor
3. Crear bucket `manual-images` en Supabase Storage (público)
4. `py -3.14 -m pip install -r requirements.txt`
5. `py -3.14 -X utf8 scripts/run_ingestion.py`

---

## ROADMAP Y ESTADO DE AVANCE

### Fase 1: Setup + Ingesta de PDFs ✅ COMPLETADA (sesión 1, 1 abril 2026)

**Objetivo:** Pipeline de ingesta que procesa PDFs → chunks con metadata → listo para vectorizar.

**Completado:**
1. ✅ Estructura del proyecto, requirements.txt, .env.example, config.py
2. ✅ `pdf_parser.py` — extrae texto con estructura jerárquica (font size, bold) + imágenes
   - Probado con CAD-250: 1,142 bloques de texto, 227 imágenes, 58 páginas
   - Header detection refinada: filtra noise (ESP, números de página, bloques cortos)
   - Requiere `.resolve()` en paths por OneDrive/Windows
3. ✅ `language_filter.py` — detecta idioma por page-level markers (ES/FR/GB/IT headers)
   - CCD-100 (138 páginas, 4 idiomas): detecta 36 páginas ES correctamente (74% reducción)
   - FAD-905 (52 páginas): 14 páginas ES (73% reducción)
   - Fallback a detección por contenido para documentos sin markers
4. ✅ `chunker.py` — chunking por sección/subsección con:
   - Detección automática de modelo de producto (regex: CAD-250, MAD-402, etc.)
   - Detección de categoría por carpeta del filesystem
   - Clasificación de content_type: procedure, specification, troubleshooting, wiring, general
   - Split de secciones grandes en sub-chunks con título preservado
5. ✅ `image_extractor.py` — renderiza páginas con diagramas como JPEG (200dpi, max 1200px, 80% quality)
6. ✅ `embedder.py` — wrapper de OpenAI embeddings con batching y rate limiting
7. ✅ `ingest.py` — pipeline completo: parse → filter → chunk → extract images → embed → upload
8. ✅ `supabase_schema.sql` — tabla chunks con pgvector, índices, función RPC match_chunks
9. ✅ Dry-run de 119 PDFs exitoso: 1,883 páginas ES, ~13,700 chunks, 0 errores

**Problemas conocidos:**
- Manuales Securiton (ASD531-535, ADW535) generan demasiados chunks (1,000-2,000 cada uno) por ser muy extensos. Son ~7,000 de los 13,700 chunks totales. Posible optimización: aumentar max_chunk_chars para esos documentos.
- Muchos modelos detectados como "unknown" — los regex de detección no cubren todos los modelos (especialmente productos no-Detnov como Pfannenberg, Securiton, Spectrex, LDA).
- Algunos PDFs muy cortos (1-2 páginas) generan 0 chunks por estar por debajo del min_chunk_chars.

**Completado:**
- ✅ Supabase project creado (izooestgffgscdirkfia, región Europe)
- ✅ Schema SQL ejecutado (pgvector, tabla chunks, función match_chunks)
- ✅ Bucket manual-images creado (público)
- ✅ Bot Telegram creado (@PCI_Soporte_tecnico_bot)
- ✅ Ingesta real: 13,835 chunks subidos a Supabase

### Fase 2: Pipeline RAG ✅ COMPLETADA (sesiones 2-3, 3-6 abril 2026)

**Objetivo:** Dado una pregunta del técnico, recuperar chunks relevantes y generar respuesta precisa.

**Completado:**
1. ✅ `retriever.py` — **búsqueda híbrida de 4 capas** (best practice):
   - Búsqueda vectorial via RPC `match_chunks` (cosine similarity, top-15)
   - Detección automática de modelos de producto en la query (regex extenso)
   - Keyword search por product_model (sim=0.65)
   - Content search por keywords de la query dentro del modelo (sim=0.80)
   - Sinónimos técnicos (e.g. "fallo" → busca "averías", "condiciones ambientales" → busca "temperatura")
   - Búsqueda por categoría (e.g. "monóxido" → filtra "Detección de monóxido")
   - Full-text search con PostgreSQL tsvector + stemming español
   - Boost de sinónimos (sim=0.85) para priorizar chunks de troubleshooting/specs
2. ✅ `reranker.py` — reranking con Claude Sonnet:
   - Recibe 15 candidatos del retriever
   - Claude evalúa relevancia real con 600 chars de preview
   - Prioriza chunks del modelo preguntado (instrucción explícita)
   - Devuelve top-5 ordenados, fallback a orden original si falla
3. ✅ `generator.py` — generación de respuesta con Claude Sonnet:
   - System prompt de experto PCI, formato para técnicos en campo
   - Formato: pasos numerados, datos técnicos precisos, viñetas (no tablas markdown)
   - Diagramas inteligentes: Claude decide cuáles son relevantes (DIAGRAMAS_RELEVANTES tag)
   - Filtro: no envía portadas/índices, solo conexionado/instalación/specs
   - Filtro de relevancia: chunks con similarity < 0.4 se descartan
4. ✅ Embeddings enriquecidos (re-embed con metadata):
   - Texto embedido incluye: Fabricante, Producto, Categoría, Sección, Tipo
   - Script: `scripts/re_embed.py`
5. ✅ Mejoras estructurales (sesión 3):
   - 55 chunks basura eliminados (revisiones, metadatos, portadas)
   - 119+ modelos arreglados (product_model "unknown" → modelo correcto)
   - Regex de detección de modelos arreglado (filenames con _ y .)
   - Full-text search con tsvector español + índice GIN + trigger auto-update
   - Función RPC `search_chunks_text` para búsqueda textual nativa
   - Script: `scripts/structural_fixes.py`

**Pipeline completo:**
```
Pregunta del técnico
       │
       ▼
  ① Búsqueda híbrida (vector + keyword + content + full-text)  → 15 candidatos
       │
       ▼
  ② Reranking con Claude (prioriza modelo preguntado)          → 5 mejores
       │
       ▼
  ③ Generación de respuesta con Claude                         → respuesta + diagramas
```

**Scoring system:**
- Keyword search genérico (primeros N chunks de un modelo): 0.65
- Content search (keyword match dentro del modelo): 0.80
- Synonym search (sinónimos técnicos): 0.85
- Vector search: score real de cosine similarity

### Fase 3: Bot Telegram ✅ COMPLETADA (sesión 2, 3 abril 2026)

**Objetivo:** Interfaz Telegram funcional con texto formateado + imágenes de diagramas.

**Completado:**
1. ✅ `telegram_bot.py` — comandos /start, /help, handler de mensajes
2. ✅ Formateador Telegram: convierte Markdown de Claude a formato compatible
   - Headers (#) → negritas, tablas → viñetas, blockquotes → 💡, --- → línea
   - Conversión automática de tablas markdown a listas con viñetas
3. ✅ Diagramas con captions descriptivas (producto + sección)
   - No envía portadas, índices o diagramas irrelevantes
4. ✅ Split de mensajes largos (>4096 chars)
5. ✅ Fallback si Markdown parsing falla (envía sin formato)
6. ⏳ Deploy en Railway (pendiente — ahora corre local en PC de Alberto)

### Fase 4: Estabilización y deploy [EN CURSO]

**Objetivo:** Bot funcionando 24/7, desacoplado del PC de Alberto.

**Completado (testing sesión 3, 6 abril 2026):**
- ✅ Test 1 - Consumos MAD-461: datos correctos del manual propio (< 300 µA / < 10 mA)
- ✅ Test 2 - MAD-491 aislador: respuesta completa con especificaciones técnicas
- ✅ Test 3 - Sistema monóxido CMD-500: encontró CMD-500 + DMDX-500 + aplicaciones
- ✅ Test 4 - Tarjetas bucle CAD-250: 4 tarjetas TBUD-250, 2 lazos cada una, 8 total
- ✅ Test 5 - Rearme PCD-100: procedimiento paso a paso correcto + diagrama
- ✅ Test 6 - Resistencia fin línea CCD-103: 4K7, datos del manual CCD-103 directamente
- ✅ Test 7 - Condiciones ambientales CAD-250: -5°C a +40°C, 5-95% HR, IP30, 3K5
- ✅ Test 8 - LED fallo alimentación CAD-250: respuesta completa (ámbar fijo, avería eléctrica, diferenciación con otros LEDs) — CORREGIDO tras re-ingesta con pdfplumber + Vision
- ✅ Test 9 - Resistencia EOL convencionales (sin modelo): 4K7 ohms + lista modelos disponibles + invita a profundizar — CORREGIDO con retriever mejorado + conversación dinámica

**Mejoras de conversación (sesión 4):**
- ✅ Conversación dinámica: pregunta de vuelta cuando falta modelo, síntoma vago, acción ambigua
- ✅ Detección de urgencia: respuestas directas con acción inmediata para situaciones críticas
- ✅ Sugerencias de follow-up: 2-3 preguntas relacionadas al final de cada respuesta
- ✅ Retriever mejorado: content search por categoría + sinónimos cuando no hay modelo específico
- ✅ Modelos disponibles por categoría: get_category_models() ofrece opciones al técnico
- ⚠️ Test 10 - Config dirección detector CAD-150: parcial — consulta menú sí, programación física del detector no (info en manual del detector, no de la central)

**Re-ingesta completada (sesión 4, 6 abril 2026):**
1. ✅ `table_extractor.py` — pdfplumber extrae tablas estructuradas (81/119 PDFs, 1,121 páginas)
2. ✅ `vision_describer.py` — Claude Vision (claude-sonnet-4-20250514) fallback para tablas gráficas
   - Heurística: páginas con ≥2 imágenes grandes y <1000 chars de texto → Vision
3. ✅ Re-ingesta real: 17,698 chunks (vs 13,780 anterior, +29%), 0 errores
4. ✅ Re-embed con metadata enriquecida: 17,698/17,698 actualizados
5. ✅ Structural fixes: 51 chunks basura eliminados, 8 modelos corregidos
6. ✅ Retriever mejorado: content search por categoría + sinónimos sin modelo
7. ✅ Conversación dinámica: preguntas de vuelta, urgencia, follow-ups
8. ✅ get_category_models(): ofrece modelos disponibles cuando pregunta es genérica

**Gaps conversacionales cubiertos (sesión 4):**
- ✅ Preguntas de catálogo: get_all_models_by_category() → lista por categoría sin RAG
- ✅ Saludos/no técnicos: respuesta directa sin pipeline (ahorro API)
- ✅ Fuera de alcance: detecta otros fabricantes (Notifier, Honeywell, etc.) → rechaza amablemente
- ✅ Feedback del técnico: detecta correcciones → registra en tabla feedback
- ✅ Comparativas: reranker equilibra modelos + generator estructura lado a lado
- ✅ Logging: tabla query_logs en Supabase (user, query, source, models, category, response_time)
- ✅ Audio/voz: Whisper transcribe → muestra transcripción → pipeline RAG
- ✅ Clasificador content_type mejorado: SPEC_KEYWORDS ampliados + boost 1.5x + reclasificación 5,334 chunks (specification: 2,009 → 7,333)

**Pendiente Fase 4:**
- ⏳ Añadir más manuales (Alberto los proporcionará) + traducción EN→ES si son 100% inglés
- ⏳ Deploy en Railway (Dockerfile + servicio 24/7)
- ⏳ Dar acceso a 2-3 técnicos beta

### Fase 5: Multi-fabricante + Traducción [PLANIFICADA]

**Objetivo:** Añadir fabricante nuevo = copiar PDFs + ejecutar un comando. Soportar manuales en inglés.

- Pipeline de ingesta con flag `--manufacturer`
- Traducción automática EN→ES con Claude Sonnet para manuales 100% en inglés
  - REGLA: si el manual es multilingüe CON sección española, NO traducir el resto (usar solo ES)
  - REGLA: solo traducir automáticamente inglés. Otros idiomas (FR, IT, DE) → caso a caso
  - Módulo: `src/ingestion/translator.py` (pendiente de implementar)
- Detección automática de fabricante en la pregunta
- Filtro de fabricante en retriever (ya soportado en RPC)
- Regex de modelos extensible (JSON config)
- Ingesta incremental

### Fase 6: Enriquecimiento por técnicos [PLANIFICADA]

**Objetivo:** Técnicos aportan experiencias de campo; admin valida; bot las integra.

- Comando `/aportar` → tabla `field_experiences` con validación
- Flujo admin: `/aprobar`, `/rechazar`, `/pendientes`
- Respuestas diferencian "manual" vs "experiencia de campo"

### Fase 7: Memoria conversacional [PLANIFICADA]

- Historial de últimos 5 mensajes por usuario
- Follow-ups inteligentes (Claude sugiere ampliar)
- Reset semanal

### Fase 8: Escala 100+ técnicos [PLANIFICADA]

- Autenticación intransferible por Telegram ID
- Admin invita/revoca acceso (`/invitar`, `/revocar`)
- Rate limiting, roles, caché, monitorización
- Índice IVFFlat optimizado (lists=500)

**Roadmap detallado completo:** ver `C:\Users\Admin\.claude\plans\fancy-hugging-bunny.md`

---

## Notas técnicas

- PyMuPDF requiere paths resueltos (`.resolve()`) para OneDrive en Windows
- Python 3.14 necesita flag `-X utf8` para manejar paths con caracteres españoles
- Los manuales de Securiton (ASD/ADW) son muy extensos (>100 páginas) y generan muchos chunks
- Los modelos de producto se detectan por regex en el nombre de archivo y contenido
- El embedding cuesta ~$0.02/1M tokens. Con ~17,700 chunks el coste estimado es < $1.50
- Claude Vision para re-ingesta: ~$0.50-$1.00 (solo páginas candidatas)
- Dependencias core instaladas: PyMuPDF, pdfplumber, Pillow, python-dotenv, langdetect

## Decisiones técnicas tomadas

| Decisión | Opción elegida | Alternativas descartadas | Motivo |
|---|---|---|---|
| Canal | Telegram | WhatsApp | WhatsApp Business API requiere aprobación Meta, coste por mensaje |
| LLM | Claude API (Sonnet) | OpenAI GPT-4o | Preferencia de Alberto |
| Embeddings | OpenAI text-embedding-3-small | Cohere, Voyage | Barato, bueno en español, 1536 dims |
| Vector DB | Supabase pgvector | Pinecone, ChromaDB | Alberto ya usa Supabase en war room |
| Idiomas | Solo español (traducción EN→ES para manuales 100% inglés) | Indexar multilingüe | Reduce ruido; manuales multilingüe con ES no se traducen; solo inglés se traduce con Sonnet |
| Diagramas | Extraer y enviar imagen por Telegram | Solo texto / Vision descriptions | Los técnicos necesitan ver los esquemas |
| PDF parsing | PyMuPDF + pdfplumber + Claude Vision | unstructured | PyMuPDF para texto/imágenes, pdfplumber para tablas, Vision como fallback para tablas gráficas |
