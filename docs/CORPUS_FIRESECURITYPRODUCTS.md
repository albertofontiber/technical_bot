# Corpus — Portal Fire Security Products (Kidde / Aritech / Ziton / GST)

> **Qué es.** Método reproducible para descargar manuales del portal
> `firesecurityproducts.com` (Carrier Fire Security; aloja varias marcas:
> **Kidde**, Aritech, Ziton, GST…). Reverse-engineered en s52 (8 jun 2026),
> validado bajando 31 PDFs de paneles Kidde "Control". Canónico de DEC-027.
>
> **Inerte al corpus.** Produce PDFs en `Manuales_<Marca>/` → LlamaParse
> (`src/reingest/extract.py`) → `data/extraction/`. La **ingesta a `chunks_v2`
> es un paso aparte** (gate RULER + Protocolo 3); descargar y parsear NO la tocan.

## Arquitectura del portal
SPA Angular sobre una **API PIM REST** (`https://pim.firesecurityproducts.com/rest/front/1/`).
El HTML del producto NO trae los documentos (los pinta JS tras llamar a la API) →
**scrapear el DOM NO sirve**; hay que llamar a la API. (Los services y las rutas se
leen del bundle `main.*.js`.)

## 1. Autenticación — OAuth2 password grant
`POST https://pim.firesecurityproducts.com/oauth2/token` (form-urlencoded):
- `grant_type=password`
- `username=$KIDDE_USER`, `password=$KIDDE_PASSWORD` — en `.env`, **NUNCA commitear**.
- `client_id=local_angular_client`
- `client_secret=<dummyClientSecret del bundle; grep "dummyClientSecret" en main.*.js — p.ej. "1NgsscHYb1oYUcS5">` (secret **público** de la SPA).
- `scope=default_scope`

Devuelve `access_token` (Bearer, TTL 3600s).

## 2. El gate REAL = headers `Origin`/`Referer`
La API devuelve **400 `"No access"`** sin ellos, AUNQUE el Bearer sea válido. Manda
siempre: `Origin: https://es.firesecurityproducts.com` + `Referer: https://es.firesecurityproducts.com/`.
(De hecho la lista de descargas funciona hasta sin token con solo estos headers; el
token desbloquea documentos restringidos en algunos productos.)

## 3. Enumerar productos
`GET /rest/front/1/product_group?domain=es&language=es&page=<n>&category=<slug>&sort=recommended&<filtros>`
- **`sort=recommended` es OBLIGATORIO** — un sort inválido → `503 "Technical
  Difficulties"` (excepción de Drupal, **NO** rate-limit).
- **Filtros** = pares `field_v_X=<machine_name>`. Los `filters=...` que pone el
  navegador en la URL **rompen con 503 — NO replicarlos**. Ej. paneles Kidde
  "Control": `category=panels&field_v_product_brand=17316&field_v_fir_pan_function=6691`.
  - `field_v_product_brand=17316` = **Kidde** (lee las opciones en `results.filters`).
  - ⚠️ El navegador AGRUPA por SERIE — lo que ves como "17 productos" puede ser 17
    series o 17 SKUs. La API plana devuelve SKUs; agrupa por `products[].series.series_id`.
  - El filtro de FUNCIÓN no siempre aplica vía API (encoding no descifrado). Si el
    conteo no cuadra con tu vista del navegador, **pide la lista exacta de SKUs**.
- Respuesta: `results.products[]` (`sku`, `product_id`, `series`, `product_brand`,
  `product_is_obsolete`…) + `results.next_page` (paginación) + `results.filters` (facetas).

## 4. Documentos de un producto
`GET /rest/front/1/product_downloads?domain=es&language=es&product_id=<id>&ignore_language=false&preview=off`
- `results.download_categories[]` = lista de `{parent: <SECCIÓN>, downloads: [...]}`.
- Secciones útiles: **Ficha de datos**, **Documentación técnica**, **Documentación
  para el usuario** (Certificados se excluyen salvo que se pidan).
- Cada doc: `file` (URL PDF directa), `language_codes`, `major_version`, `size`, `category`.
- `language=es` + `ignore_language=false` → solo ES; `ignore_language=true` → todos los idiomas.

## 5. Política de idioma + dedup
- **ES primario, EN de fallback** si una sección no tiene ES.
- Los **manuales son por SERIE** (mismos PDFs para todos los SKU de la serie); solo
  la *Ficha de datos* es por-SKU. Dedup por nombre de fichero (o SHA-256 vía
  `src/reingest/inventory.py`) → ~decenas de PDFs únicos, no SKU×5.

## 6. Pipeline completo de un lote nuevo
1. **Descargar** a `Manuales_<Marca>/` (headers Origin + Bearer; validar `%PDF`;
   guardar `_download_manifest.json` con provenance: sku/serie/categoría/idioma/url).
2. **Sidecar** `Manuales_<Marca>/_metadata.json` desde el manifiesto (`local_filename`,
   `equipo`, `tipo`, `idioma`) para que el inventario salga exacto, no por regex.
3. **Inventario**: registrar en `scripts/update_inventario.py` (`FABRICANTES`, con
   `metadata_sidecar`) + `python scripts/update_inventario.py --only <Marca>`.
4. **Parse**: `python src/reingest/inventory.py` (refresca manifiesto, dedup SHA) →
   `python src/reingest/extract.py` (LlamaParse agentic = config `agent_anthropic-sonnet-45`,
   **el mismo que el corpus** → consistencia; resumable, salta lo ya extraído).
5. **PARAR**: la ingesta a `chunks_v2` (embed + upsert) es paso aparte → gate RULER + Protocolo 3.

## Notas
- `Manuales_<Marca>/` va a `.gitignore` (PDFs grandes, como los demás `Manuales_*`).
  El xlsx de inventario se **versiona** vía excepción `!data/Inventario_Manuales.xlsx`
  (precedente: `!Guia Tecnica Morley.xlsx`).
- **s52**: brand `17316`=Kidde; 17 SKUs "Control" (series NC, 2X-A, 2X-A Táctil) →
  31 PDFs / ~696 pp; parse 31/31 OK (~$42); ingesta DIFERIDA.

## 7. Variante: lote desde pedidos (`/my-orders`) — base instalada del cliente
En vez de filtrar el catálogo por marca/función, se pueden bajar los manuales de los
productos **realmente comprados** por la cuenta (la base instalada del instalador) —
más relevantes para el técnico. La cuenta `KIDDE_USER` es de un instalador (TRATEIN PCI).

- **Listar pedidos**: `GET /rest/front/1/orders?domain=es&language=es` (Bearer + Origin) →
  `results.orders[]` (`drupal_order_number`, `oracle_order_id`, `number_of_items`…).
- **Líneas de un pedido**: `GET /rest/front/1/order_details?domain=es&language=es&order_number=<EESxxxx>` →
  `results.line_items[]`, cada uno con **`product_id`** (directo, no hace falta resolver SKU→ID),
  `sku`, `bu`, `description` (+ comerciales `unit_price`/`quantity` que se **IGNORAN**).
- **Dedup** los `product_id` across pedidos → set de productos comprados → de ahí, el pipeline
  de §4–6 (`product_downloads` → 3 categorías → descarga → inventario → parse).

**Notas:**
- **Multi-marca**: los pedidos abarcan todo el portfolio fire (Kidde + Aritech + Edwards +
  genéricos), no una marca. Agrupa por la marca **REAL** (`product_details.product_brand`;
  `None` = genérico → carpeta "Otros"), NO por la marca-marketing del filtro de catálogo
  (un 2X-A sale **Aritech** aquí vs **Kidde** en el filtro de §3 — el portal cross-brandea).
- **Privacidad**: usar los pedidos SOLO para identificar productos; nunca almacenar/commitear
  dato comercial.
- **s53**: 10 pedidos TRATEIN → 41 productos → 76 PDFs (Kidde/Aritech/Edwards/Otros) →
  parse 66 nuevos/~$50; ingesta DIFERIDA.
