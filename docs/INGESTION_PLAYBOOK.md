# Playbook de ingesta de un fabricante nuevo

Este documento describe el proceso end-to-end para añadir los manuales de un
fabricante nuevo al bot RAG. Está escrito para ser **replicable**: si dentro de
3 meses un técnico (o yo mismo) tiene que ingestar un fabricante adicional,
debería poder seguir estos pasos sin tener que reconstruir el contexto.

> **Nota de contexto**: este playbook cristaliza el proceso que ejecutamos para
> Notifier en abril 2026 (357 PDFs privados). Incluye las lecciones aprendidas
> de los errores que cometimos en el camino.

---

## Filosofía del proceso

Cuatro principios que justifican por qué el playbook es largo:

1. **Precisión > velocidad.** Es preferible tardar 2 días y tener 99.7% de
   cobertura correcta, que tardar 2 horas y tener 70% con errores que no
   sabemos dónde están. El coste de un chunk mal clasificado es que el bot no
   lo encuentra cuando el técnico lo necesita.
2. **Mide antes de ingestar.** Nunca lanzamos la ingesta real sin haber hecho
   un "dry-run" (procesamiento en memoria sin tocar la base de datos). Eso
   permite detectar ficheros rotos, modelos mal identificados y PDFs escaneados
   antes de pagar por embeddings.
3. **Cada paso tiene un criterio de éxito cuantitativo.** Si no se cumple, se
   para y se investiga. No se pasa al siguiente paso "a ver si cuela".
4. **Cada decisión manual se automatiza la próxima vez.** Si tienes que hacer
   lo mismo dos veces a mano, la segunda vez lo conviertes en script.

---

## Visión general de los 9 pasos

```
1. Scrape           → Descargar PDFs del sitio del fabricante
2. Filtrado         → Excluir idiomas no-ES/EN, deduplicar, descartar revs antiguas
3. Dry-run parse    → Procesar en memoria, medir cobertura
4. Regex pass       → Añadir patrones para modelos detectables por filename
5. LLM pass 1       → Usar Claude para clasificar los que quedan unknown
6. Vision rescue    → Recuperar PDFs escaneados con Claude Vision
7. LLM pass 2       → Clasificar los modelos de los PDFs rescatados
8. Ingesta real     → Lanzar el pipeline completo contra Supabase
9. Eval             → Verificar con preguntas de regresión que el bot responde bien
```

Duración total aproximada para ~350 PDFs: **1-2 días de trabajo**, de los
cuales quizá 2-3 horas son código/interacción y el resto son esperas de
procesos batch.

Coste de infraestructura (por fabricante, ~350 PDFs):
- Embeddings OpenAI: ~$15-25 (depende del tamaño de los chunks)
- LLM pass 1 (Claude Sonnet, texto): ~$1
- Vision rescue (Claude Sonnet, imagen): ~$2-3
- LLM pass 2: ~$0.20
- **Total: ~$20-30 por fabricante**

---

## Paso 1. Scrape (descarga de PDFs)

**Objetivo**: traerte todos los PDFs del fabricante a una carpeta local,
idealmente con el nombre de fichero original que usa su CMS.

**Qué hace técnicamente**: un script en Python se loguea en la web del
fabricante (si requiere login) y recorre sistemáticamente el índice de manuales
descargando cada PDF que encuentra.

**Script de referencia**: `scripts/scrape_notifier_auth.py` — **80%
reutilizable** para cualquier fabricante que use CMS Joomla (lo que usan
Notifier, Morley y la mayoría de marcas de Honeywell). Los cambios entre
fabricantes son sólo URLs base y las secciones a crawlear.

**Patrones de CMS que hemos visto**:
- **Joomla** (Notifier, Morley): login con formulario, CSRF token de 32 caracteres hex, cookie `joomla_user_state=logged_in`
- **WordPress + membership plugin**: típicamente nonce-based, cookie `wordpress_logged_in_*`
- **SAP Commerce / custom**: caso a caso

**Para una web que no conoces todavía**:
1. Entra manualmente con el navegador y navega hasta un PDF
2. Abre la pestaña Network de DevTools, recarga la descarga
3. Copia el request como cURL → te da headers y cookies
4. Pega en ChatGPT/Claude: "dame el equivalente en httpx de este cURL" → tienes el primer script mínimo
5. Iteras hasta cubrir todas las páginas del índice

**Credenciales**: van al fichero `.env` en la raíz del proyecto. Convención
para las variables: `<NOMBRE_FABRICANTE>_USER`, `<NOMBRE_FABRICANTE>_PASSWORD`.
Por ejemplo:
```
NOTIFIER_USER=...
NOTIFIER_PASSWORD=...
MORLEY_USER=...
MORLEY_PASSWORD=...
```

**Carpeta de salida**: `Manuales_<Fabricante>_Privado/`. El sufijo `_Privado`
distingue el contenido del área de clientes (el bueno) del área pública.

**Criterios de éxito del paso 1**:
- [ ] Todos los PDFs se abren sin corrupción (verificable con `file *.pdf`)
- [ ] No hay ficheros < 1KB (downloads fallidos)
- [ ] El total descargado coincide aproximadamente con lo que dice el índice
      del fabricante (tolerancia ±5% por enlaces rotos)

**Trampas conocidas**:
- **Rate limiting**: poner `time.sleep(1.0)` entre requests. Si te bloquean,
  subir a 2-3s.
- **Sesión que expira a media descarga**: el script debe re-loguearse si detecta
  una redirección a la página de login.
- **Filenames con caracteres ilegales en Windows**: sanitizar `/`, `\`, `:`,
  `*`, `?`, `"`, `<`, `>`, `|`.

---

## Paso 2. Filtrado pre-ingesta

**Objetivo**: quitar de la carpeta todo lo que **no queremos** que acabe en la
base de datos, antes de gastar tiempo y dinero procesándolo.

**Qué filtramos**:

1. **Idiomas no soportados.** Regla actual: nos quedamos sólo con PDFs en
   español o inglés. Nada de francés, alemán, italiano, etc. Un PDF en italiano
   que el bot recupera y el LLM le pasa a un técnico español es inútil (y
   potencialmente peligroso si el técnico interpreta algo a medias).

   **Cómo detectamos el idioma**: regex sobre el filename buscando sufijos como
   `_DE`, `_FR`, `_IT`, `_Ita`, con un enforcement de separadores muy estricto
   (case-sensitive, requiere guion bajo/guion/punto alrededor). Aprendimos por
   las malas que un regex case-insensitive hace matching de `DE` contra la
   palabra española "de" y te carga en la basura todos los manuales en español
   con "manual de usuario" en el nombre. Cuidado.

2. **Documentos no-técnicos.** Excluimos por keyword: catálogos comerciales,
   certificados ATEX/CE, hojas técnicas comerciales, fichas de datos, formularios.
   El bot no debe responder dudas técnicas con el catálogo de marketing.

3. **Duplicados exactos por filename.** Si el scrape devuelve el mismo fichero
   dos veces (porque aparece en dos secciones del índice), dedup por hash.

4. **Revisiones obsoletas** *(a implementar — ver TECH_DEBT #4)*. Cuando haya
   `AM-8100 rev 3.pdf` y `AM-8100 rev 4.pdf`, sólo queremos la rev 4 en la DB
   y la rev 3 marcada como `superseded`. Hoy lo detectamos a ojo; el plan es
   automatizarlo con un parser heurístico de revisiones.

**Script de referencia**: la lógica está embebida en el scraper. Para Notifier
hicimos los filtros dentro del mismo `scrape_notifier_auth.py`. Para
fabricantes nuevos podemos mover la lógica a un módulo `scripts/filter_pdfs.py`
compartido.

**Criterios de éxito del paso 2**:
- [ ] La carpeta `Manuales_<Fabricante>_Privado/` contiene sólo lo que quieres
      ingestar
- [ ] Un muestreo aleatorio de 10 PDFs confirma que 10/10 están en ES o EN y
      son técnicos (manuales, guías, notas técnicas)
- [ ] El número de ficheros después del filtrado vs. antes está documentado
      (ej: "660 descargados → 397 tras filtrado → 357 tras dedup")

---

## Paso 3. Dry-run parse

**Objetivo**: procesar todos los PDFs en memoria (parseo + chunking) pero **sin
generar embeddings ni escribir en la base de datos**. Esto nos da un informe
completo de coverage en pocos minutos sin gastar un euro.

**Qué medimos**:
- ¿Cuántos PDFs producen 0 chunks? (indicador de scanned PDFs que pdfplumber no
  puede leer — van a necesitar Vision)
- ¿Cuántos PDFs tienen `product_model = "unknown"`? (indicador de que necesitan
  overrides o mejor detección por keyword)
- ¿Cuántos tienen `manufacturer` distinto del esperado? (bug en los keyword
  patterns — a arreglar antes de ingestar)
- ¿Cuál es la distribución de categorías? (detecta fallbacks sospechosos como
  "General")
- ¿Cuántos chunks totales esperamos?

**Script**: `python scripts/dry_run_parse.py Manuales_<Fabricante>_Privado <Fabricante>`

**Salida**:
- En pantalla: tabla por fichero con flags `[!MFR]`, `[!MODEL]`, `[!CAT]` +
  informe agregado
- En disco: `Manuales_<Fabricante>_Privado/_dry_run_results.json` — lo usan
  los pasos siguientes

**Criterios de éxito del paso 3**:
- [ ] 0 errores de parse (un error aquí significa PDF corrupto — investigar)
- [ ] `manufacturer != expected` == 0 (si hay mismatch, arreglar los keyword
      patterns antes de seguir)
- [ ] Ratio de zero-chunks < 15% (normal es 5-12%; si es más alto puede indicar
      un problema sistemático con el parser)

**Qué hacer si no se cumple**:
- Ratio alto de unknown models → pasar al paso 4 (regex)
- Ratio alto de zero-chunks → saltar al paso 6 (Vision rescue) tras el LLM pass
- Errores de parse → abrir los ficheros a mano, confirmar si son corruptos o
  si hay un bug en pdf_parser

---

## Paso 4. Regex pass (modelos detectables por filename)

**Objetivo**: muchos fabricantes usan una convención interna de código de
documento (ej: `I56-0788-003 - CP-651E.pdf`), donde el modelo real del producto
aparece después del código. Una expresión regular bien hecha recupera muchos
modelos gratis, sin LLM.

**Qué hacer**:
1. Ordena los `_dry_run_results.json` por `product_model == "unknown"`
2. Mira los filenames a mano y busca patrones repetidos
3. Añade la regex a `<FABRICANTE>_MODEL_PATTERNS` en `src/ingestion/chunker.py`
4. Re-ejecuta el dry-run y confirma que los unknowns bajan

**Ejemplo real para Notifier**: los ficheros tipo `I56-1730-002_FD-851RE.pdf`
llevan el modelo (`FD-851RE`) pegado al código interno. Añadimos:
```python
re.compile(r"I56[- ]\d{2,5}[- ]\d{2,3}[A-Z]?[\s_\-]+([A-Z][A-Z0-9\-]*\d[A-Z0-9\-]*)", re.IGNORECASE)
```

**Detalle importante**: requiere al menos un dígito en el capture para evitar
que capture tokens espurios como `Sp`, `Manual`, `pdf`. Los modelos reales
siempre tienen números.

**Criterio de éxito**: la ejecución del dry-run post-regex debe reducir
unknowns en al menos un 5-10% del total antes de pasar al LLM. Si no aporta
nada, salta directamente al paso 5.

---

## Paso 5. LLM pass 1 (clasificación automática de unknowns con Claude)

**Objetivo**: para los PDFs que no se clasifican por filename, usamos Claude
Sonnet leyendo las 2 primeras páginas del texto extraído para identificar el
modelo.

**Por qué 2 páginas**: normalmente la portada tiene el nombre del producto, y
la primera página interna tiene un título repetido. Más páginas no aportan
información adicional para la clasificación y triplican el coste.

**Script**: `python scripts/llm_classify_unknowns.py Manuales_<Fabricante>_Privado <Fabricante>`

**Qué hace internamente**:
1. Lee `_dry_run_results.json`, filtra los unknowns
2. Para cada uno, abre el PDF, extrae las 2 primeras páginas como texto
3. Manda a Claude Sonnet con un prompt JSON-only: "identifícame el modelo, con
   tu confianza del 0 al 1, y una frase explicando tu evidencia"
4. Escribe los resultados con `confidence >= 0.7` a un fichero `_llm_overrides.json`
   listo para pegar en el diccionario de overrides
5. Los de baja confianza van a `_llm_unknowns_review.json` para revisión manual

**Merge en el código**: los contenidos de `_llm_overrides.json` se añaden como
entradas nuevas al diccionario `<FABRICANTE>_SOURCE_FILE_TO_MODEL` en
`src/ingestion/chunker.py`. Se puede hacer con un script automatizado (como el
que usamos para Notifier).

**Coste típico**: ~$1 por 200 unknowns.

**Criterio de éxito**: ≥95% de los unknowns quedan clasificados con alta
confianza. Si queda una cola significativa (>5%), investigar patrones comunes
en esa cola — posible que sean PDFs escaneados (→ paso 6) o docs genéricos
sin modelo identificable (→ review manual).

---

## Paso 6. Vision rescue (recuperar PDFs escaneados)

**Objetivo**: algunos PDFs no tienen texto extraíble. Son escaneos — cada página
es una imagen rasterizada y `pdfplumber` no puede leer su contenido. Sin
rescate, estos PDFs generan 0 chunks y quedan fuera del RAG.

**Solución**: Claude Vision. Mandamos cada página como imagen y le pedimos que
extraiga el contenido técnico estructurado (tablas, especificaciones, conexionado).

**Arquitectura importante**: el módulo `src/ingestion/pdf_parser.py` detecta
automáticamente ahora mismo si un PDF tiene `< 50 caracteres por página` de
media. Si es así, lo marca como "fully-scanned" y fuerza Vision en todas las
páginas durante la ingesta, sin que haya que hacer nada manual. Esta detección
está integrada en `enrich_with_vision()`.

**Pero para el dry-run hay que rescatarlos manualmente** porque el dry-run
intencionadamente no llama al Vision (costaría dinero cada vez que lo corres).
Para esto tenemos:

**Script**: `python scripts/vision_rescue_zerochunks.py Manuales_<Fabricante>_Privado <Fabricante>`

**Qué hace**:
1. Lee los ficheros zero-chunk del dry-run
2. Para cada uno, fuerza Vision en todas las páginas (típicamente 1-4 páginas por fichero)
3. Re-chunk con el contenido extraído por Vision
4. Escribe `_vision_rescue_results.json` con los resultados

**Coste típico**: ~$0.06 por página (200 dpi, imagen + texto pequeño). Para
~40 ficheros con 4 páginas cada uno = ~$10. En la práctica con Notifier pagamos
$2 porque la mayoría eran 1-2 páginas.

**Criterio de éxito**: ≥90% de los zero-chunks se convierten en "chunks
recuperados". El ~10% restante son ficheros genuinamente irrecuperables (páginas
en blanco, escaneos de muy baja resolución) — documentados en el review JSON.

---

## Paso 7. LLM pass 2 (clasificar los rescatados)

**Objetivo**: los ficheros rescatados por Vision tienen contenido, pero a
menudo su `product_model` sigue siendo `unknown` porque la regex de filename no
les aplicó. Un segundo LLM pass sobre el texto Vision-extraído los clasifica.

**Script**: `python scripts/llm_classify_unknowns.py Manuales_<Fabricante>_Privado <Fabricante> --from-rescue`

El flag `--from-rescue` le dice al script que lea `_vision_rescue_results.json`
en lugar del dry-run original. Internamente el script también fuerza Vision
para extraer el texto de las 2 primeras páginas antes de mandárselo a Claude.

**Output**: `_llm_overrides2.json` — mergear en el chunker igual que el primer
pass.

**Coste típico**: ~$0.20 (muy barato, pocos ficheros).

---

## Paso 8. Ingesta real a Supabase

**Objetivo**: ahora sí, correr el pipeline completo contra la base de datos.

**Comando**:
```bash
python -c "
from dotenv import load_dotenv; load_dotenv('.env', override=True)
from src.ingestion.ingest import ingest_all
ingest_all(base_dir='Manuales_<Fabricante>_Privado', use_vision=True)
"
```

**El flag `use_vision=True` es obligatorio** — es lo que activa el auto-detect
de scans y rescata los PDFs escaneados. Sin él, esos PDFs se ingestan vacíos.

**Qué pasa internamente por cada PDF**:
1. Skip si ya hay chunks con el mismo `source_file` en la DB (idempotente)
2. Parse con PyMuPDF (texto normal)
3. Enrich con pdfplumber (tablas)
4. Enrich con Claude Vision (si scanned o si páginas con muchas imágenes)
5. Filtrar páginas ES (o usar todas si no hay ES)
6. Chunk con metadata (manufacturer, product_model, category, protocol, doc_type)
7. Extraer imágenes de diagramas
8. Generar embeddings OpenAI para cada chunk
9. Insertar en Supabase (tabla `chunks`) con retry automático en errores 5xx

**Tiempo típico**: ~7-8 segundos por PDF que no es scan + ~40-60 segundos por
PDF scan. Para 357 PDFs con ~40 scans: ~60 minutos total.

**Errores que hemos visto**:
- **Supabase 500/502 transitorios**: el retry automático (4 intentos con backoff
  exponencial 2-4-8-16s) los absorbe. Si todos fallan, el script levanta
  excepción y ese PDF se cuenta como error.
- **Unicode en stdout** (Windows): envolver stdout en `io.TextIOWrapper(...,
  encoding='utf-8', errors='replace')` al principio del script de lanzamiento.
- **PDF con estructura inesperada**: pdfplumber puede tirar excepciones raras
  en PDFs antiguos. La ingesta las captura y continúa con el siguiente.

**Criterios de éxito del paso 8**:
- [ ] `PDFs processed` >= 95% del input (errores < 5%)
- [ ] Total chunks en la DB tras la ingesta coincide (±2%) con lo estimado
      en el dry-run
- [ ] Un muestreo aleatorio de 10 chunks muestra metadata correcta
      (`product_model`, `category`, `manufacturer`)

---

## Paso 9. Eval de regresión

**Objetivo**: verificar que el bot responde correctamente preguntas reales del
fabricante. Sin eval, no sabes si la ingesta fue útil.

**Qué necesitas antes de ingestar un fabricante nuevo**:
- Una lista de **al menos 3 preguntas** cuya respuesta correcta esté en los
  manuales de ese fabricante
- La respuesta "oro" (ground truth) para cada pregunta
- Idealmente, una pregunta-trampa cuya respuesta dependa específicamente de la
  versión más reciente de un manual (esto atrapará regresiones de revisiones)

**Dónde viven**: el eval set está en `tests/` — añadir al fichero existente
un bloque por fabricante.

**Cómo se ejecuta**: (pendiente formalizar — actualmente se corre con el
script de eval que usa `retriever.py` + `generator.py` contra la DB real)

**Criterios de éxito**:
- [ ] Las 3+ preguntas del fabricante nuevo pasan
- [ ] Las preguntas de fabricantes ya ingestados siguen pasando (no regresión)
- [ ] Al menos 9/10 en el eval general

---

## Apéndice A — Diagnóstico de fallos comunes

### "Todos los PDFs dan `manufacturer = unknown`"
→ Los keyword patterns del fabricante no están registrados en chunker.py.
Abrir `src/ingestion/chunker.py`, buscar `detect_manufacturer`, añadir el
fabricante.

### "La tasa de `product_model = unknown` es del 80%"
→ No hay overrides ni patterns para este fabricante. Proceder con los pasos
4-5-7 (regex + LLM passes).

### "Muchos PDFs son scans pero el pipeline no los detecta"
→ Verificar que `parse_pdf.py` tiene el bloque `is_scanned_doc` en
`enrich_with_vision()` (añadido abril 2026 durante la ingesta de Notifier).

### "Errores 500 constantes de Supabase durante la ingesta"
→ Pro Plan de Supabase: casi siempre es un incidente transitorio. Los retries
suelen absorberlos. Si la tasa no baja tras 10-15 min, consultar
status.supabase.com y considerar reducir `batch_size` de 50 a 20 en
`ingest.py`.

### "El eval post-ingesta cae en 2-3 preguntas que antes pasaban"
→ Regresión silenciosa. Posibles causas:
- Un rename de filename en el fabricante nuevo hizo que un override no aplique
  (ver TECH_DEBT #2)
- El retriever híbrido está priorizando el fabricante nuevo y desplazando
  resultados del antiguo
- Cambio en el chunker que cambió los embeddings generados

---

## Apéndice B — Adaptación específica por fabricante

### Notifier (ya ingestado, abril 2026)
- Scraper: `scripts/scrape_notifier_auth.py`
- Carpeta: `Manuales_Notifier_Privado/`
- Credenciales: `NOTIFIER_USER`, `NOTIFIER_PASSWORD`
- Overrides: 245 entradas en `NOTIFIER_SOURCE_FILE_TO_MODEL`
- Notas: CMS Joomla, tiene área pública + privada. La privada coincide
  contenido-a-contenido con la pública pero incluye extras (manuales
  descatalogados, comunicaciones técnicas). El scrape autenticado recupera
  ambas.

### Morley (pendiente)
- Credenciales: **las mismas que Notifier** — son ambas marcas de Honeywell y
  comparten cuenta de cliente. Verificar antes de ejecutar.
- Probable CMS: Joomla (mismo stack que Notifier). Primera tarea: verificar la
  URL de login y el patrón del índice. Si coincide, copiar `scrape_notifier_auth.py`
  a `scrape_morley_auth.py` y cambiar `BASE_URL` + `SECTIONS`.
- Overrides existentes: `MORLEY_SOURCE_FILE_TO_MODEL` + `MORLEY_SOURCE_FILE_TO_CATEGORY`
  (ingestados antes, aún sin cobertura del área privada).
