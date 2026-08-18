# s325b v2 — el CABLEADO ya escrito (segunda ronda del dúo)

Ronda 2. La ronda 1 revisó el DISEÑO y devolvió NO SÓLIDO por ambos lados; esto es
lo que quedó cableado después de aplicar sus hallazgos. Revisad el CÓDIGO, no esta
descripción. Impacto MEDIO en zona de dolor (corpus/ingesta).

## Qué cambió respecto a la ronda 1 (vuestros hallazgos, aplicados)

1. **Faltaba un consumidor** (`src/reingest/pipeline.py:223`, Sol) → cableado.
2. **`ingest_new` es PRODUCTOR** (Sol y Fable, convergente) → **el alcance se acotó a
   CONSUMO por adjudicación de Alberto**: ingestar manuales nuevos sigue siendo local.
   Y como Alberto pidió después garantizar la consistencia, se añadió la PUERTA ÚNICA:
   `ingest_new` publica al bucket en el mismo acto en que escribe el fichero.
3. **La «descarga perezosa» era falsa** porque `_build_sha_map` recorre el store entero
   (ambos) → el manifiesto lleva ahora `source_path` y `sha_pdf`, y `indice()` sale de
   UN GET.
4. **El open real vive en `s94_f1_generate._sha_path`** y busca por PATRÓN (Fable) →
   `buscar_por_sha()`.
5. **El skip de la subida se decidía por tamaño** mientras el manifiesto se regeneraba
   con el sha local (Fable: «manifiesto que miente, `--verificar` en verde») → ahora se
   decide por **sha contra el manifiesto remoto**.
6. **La caché revalidaba por tamaño** (Fable) → se indexa por sha.
7. **`fallos` era global entre configs** (Fable) → por config.
8. **Un fallo del store se degradaba a error por-documento** (Sol) → `StoreError`
   re-lanza y aborta el tramo; el resto de excepciones siguen con su cinturón por-doc.

Además, un bug de plataforma que ninguno pidió pero que el cableado destapó:
`_build_sha_map` hacía `os.path.basename` sobre `source_path` de **Windows**; en Linux
—donde corre una sesión cloud— eso no separa por `\` y el mapa habría salido vacío EN
SILENCIO. Ahora el basename es agnóstico.

## Ficheros a revisar

- `src/extraction_store.py` — resolutor (`listar`/`ruta_de`/`indice`/`buscar_por_sha`)
  + `publicar_al_bucket`.
- `scripts/upload_extraction_store.py` — subida/verificación con manifiesto.
- `scripts/enunciados_pass.py` — `_store_res`, `_build_sha_map`, el `except StoreError`.
- `scripts/s94_f1_generate.py` — `_store`, `_sha_path`.
- `src/reingest/pipeline.py` — `run()`.
- `scripts/ingest_new.py` — `_ingesta_doc` (publicación fail-open).
- `tests/test_extraction_store.py` — 15 contratos.

## Verificación ya hecha (para que la ataquéis, no para que la creáis)

- Subida real: 1.143 + 28 objetos; `--verificar` 0 fallos cruzando SHA.
- Camino cloud contra el bucket REAL, sin disco: `listar()` 1.143 en 1,2 s;
  `_build_sha_map()` **1.136 claves, idénticas a las del disco**, en 0,5 s;
  `store_pages()` descarga y parsea.
- Equivalencia disco: mapa viejo vs nuevo código → **idénticos** (1.136/1.136).
- Guardarraíles del repo actualizados, no silenciados: censo de módulos 126→127 con
  justificación, y registro de flags con `EXTRACTION_CACHE_DIR` + los lectores nuevos.

## Qué quiero que ataquéis ahora

1. ¿Queda algún camino en el que un lote se cierre «completo» habiendo fallado el
   store, o en el que se procese un subconjunto sin que nada avise?
2. La puerta única: ¿el orden objeto→manifiesto y el fail-open dejan algún estado que
   una lectura posterior interprete mal? ¿Y con dos ingestas concurrentes?
3. `buscar_por_sha` vs el `_sha_path` original: ¿hay algún sha que antes resolvía y
   ahora no (o al revés)?
4. La caché por sha: ¿colisiones, basura sin límite, o rutas que rompan en Linux?
5. ¿El resolutor cambia algún comportamiento en LOCAL, donde el disco manda?
